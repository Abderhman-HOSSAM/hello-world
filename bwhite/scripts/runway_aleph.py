#!/usr/bin/env python3
"""Runway Aleph 2.0 video-to-video. Reads the key from $RUNWAYML_API_SECRET — never hard-code it.

Cost guard: Aleph 2.0 bills 28 credits/sec at $0.01/credit = $0.28/sec.
An 8 s generation costs ~$2.24. This script refuses to spend without --confirm
and refuses to exceed MAX_GENERATIONS without --override.
"""
import argparse, base64, json, mimetypes, os, sys, time, urllib.request, urllib.error

API   = "https://api.dev.runwayml.com/v1"
VER   = "2024-11-06"
RATE  = 0.28                      # USD per second of output
MAX_GENERATIONS = 4               # hard stop; budget is $10
LEDGER = os.path.join(os.path.dirname(__file__), "..", "work", "spend_ledger.json")


def key():
    k = os.environ.get("RUNWAYML_API_SECRET")
    if not k:
        sys.exit("RUNWAYML_API_SECRET is not set. Add it to the environment, do not paste it into a file.")
    return k


def data_uri(path, cap_mb=5.0):
    raw = open(path, "rb").read()
    enc = base64.b64encode(raw).decode()
    mb = len(enc) / 1048576
    if mb > cap_mb:
        sys.exit(f"{path}: {mb:.2f} MB base64 exceeds the {cap_mb} MB data-URI cap. Re-compress it.")
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    print(f"  {os.path.basename(path):46s} {mb:5.2f} MB base64  ({mime})")
    return f"data:{mime};base64,{enc}"


def req(method, url, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"Bearer {key()}",
        "X-Runway-Version": VER,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {url}\n{e.read().decode()[:900]}")


def ledger():
    try:
        return json.load(open(LEDGER))
    except Exception:
        return {"runs": []}


def record(task_id, seconds, cost):
    d = ledger()
    d["runs"].append({"task": task_id, "seconds": seconds, "usd": round(cost, 2), "ts": time.time()})
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(d, open(LEDGER, "w"), indent=2)
    return d


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True, help="source clip (data-URI inlined, <=5MB base64)")
    p.add_argument("--ref", help="reference/style image, optional (1 max)")
    p.add_argument("--prompt-file", required=True)
    p.add_argument("--seconds", type=float, default=8.0)
    p.add_argument("--ratio", default="720:1280")
    p.add_argument("--out", default="work/aleph_out.mp4")
    p.add_argument("--confirm", action="store_true", help="required — this spends real credits")
    p.add_argument("--override", action="store_true", help="allow exceeding MAX_GENERATIONS")
    a = p.parse_args()

    spent = ledger()
    n = len(spent["runs"])
    total = sum(r["usd"] for r in spent["runs"])
    cost = a.seconds * RATE

    print(f"Aleph 2.0  |  {a.seconds:.2f}s x ${RATE}/s = ${cost:.2f}")
    print(f"prior runs: {n}  spent so far: ${total:.2f}")
    if n >= MAX_GENERATIONS and not a.override:
        sys.exit(f"STOP: {n} generations already run (limit {MAX_GENERATIONS}). Ask the user before --override.")
    if not a.confirm:
        sys.exit("Dry run. Re-run with --confirm to actually spend.")

    print("encoding inputs:")
    payload = {
        "model": "aleph2",
        "videoUri": data_uri(a.video),
        "promptText": open(a.prompt_file).read().strip(),
        "ratio": a.ratio,
    }
    if a.ref:
        payload["references"] = [{"type": "image", "uri": data_uri(a.ref)}]

    task = req("POST", f"{API}/video_to_video", payload)
    tid = task["id"]
    print("task:", tid)

    while True:
        time.sleep(6)
        t = req("GET", f"{API}/tasks/{tid}")
        st = t.get("status")
        print("  ", st, t.get("progress", ""), flush=True)
        if st in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
    if st != "SUCCEEDED":
        record(tid, a.seconds, cost)
        sys.exit(f"generation {st}: {json.dumps(t)[:600]}")

    url = t["output"][0]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    urllib.request.urlretrieve(url, a.out)
    d = record(tid, a.seconds, cost)
    print(f"saved {a.out}  |  runs={len(d['runs'])}  total=${sum(r['usd'] for r in d['runs']):.2f}")


if __name__ == "__main__":
    main()
