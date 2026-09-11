# B.WHITE — Mini Aesthetic Clinic

Resumable toolkit for turning the miniature-spa clip into a miniature Botox/filler clinic
via Runway Aleph 2.0, then finishing it to B.WHITE spec locally.

Everything here is safe to commit. No keys, no footage.

## Why Aleph 2.0

It is the only shortlisted model built for *localized* video edits that leave the rest of the
clip stable — which is the whole requirement here (swap the figurines, keep the woman, the
lighting and the camera move). Luma Modify Video is ~3.5x cheaper but restyles globally and
drifts on identity.

`POST https://api.dev.runwayml.com/v1/video_to_video` · model `aleph2` · ratio `720:1280`
· 2-30 s supported · 1 reference image · inputs inlined as data URIs (5 MB cap each).

## Budget rules — $10 balance

Aleph 2.0 = 28 credits/sec, $0.01/credit = **$0.28/sec → ~$2.24 per 8 s run**.

* ONE generation first, then inspect before spending again.
* Never run generations in parallel.
* Hard stop at **4 generations** ($8.96). `runway_aleph.py` enforces this and refuses to spend
  without `--confirm`. Ask the user before `--override`.
* Spend is tracked in `work/spend_ledger.json` (gitignored).

## To resume in a new session

Re-attach these two files — they are the user's own uploads and are deliberately NOT in git:

| file | what it is |
|---|---|
| `ORIGINAL_minispa_720x1280_24fps.mp4` | the source clip, 8.13 s, 192 f @ 24 fps, HE-AAC 48 kHz |
| `TARGET_keyart.png` | the approved target look (also fine: the 1080x1920 seed-frame version) |

Then:

    export RUNWAYML_API_SECRET=...        # set on the environment, never in a file

    # 1) dry run - prints cost, spends nothing
    python3 bwhite/scripts/runway_aleph.py \
        --video ORIGINAL_minispa_720x1280_24fps.mp4 \
        --ref   TARGET_keyart.png \
        --prompt-file bwhite/prompt_aleph.txt \
        --seconds 8 --out work/aleph_01.mp4

    # 2) same command + --confirm  to actually generate (~$2.24)

    # 3) inspect work/aleph_01.mp4 before spending again

    # 4) finish: logo + original audio + Reels encode
    python3 bwhite/scripts/finish.py \
        --video work/aleph_01.mp4 \
        --audio-from ORIGINAL_minispa_720x1280_24fps.mp4 \
        --logo-width-pct 7.8 \
        --out work/BWHITE_MiniAesthetic_FINAL.mp4

`finish.py` pads to 1080x1920 without distorting, composites the official logo top-left with
aspect preserved, and re-marries the original audio with `-c:a copy` so the music stays
bit-identical. Verify with:

    ffmpeg -i ORIGINAL...mp4 -map 0:a:0 -f md5 -
    ffmpeg -i work/BWHITE_MiniAesthetic_FINAL.mp4 -map 0:a:0 -f md5 -    # must match

## Logo

`assets/bwhite_logo_vertical_alpha.png` is the official vertical lockup, vector-traced from the
identity PDF, white + alpha so it tints to any brand colour. `finish.py` tints it to #A57777.
Never let a generative model draw the logo.

Sizes used so far: 7.8% of width (84 px) as specified; 15.7% (170 px) was preferred on the
Franklin cut. Pass `--logo-width-pct`.

## QC before delivery

woman's identity unchanged · face not warped · practitioners genuinely moving and consistent
· no floating characters · max 3 syringes · no blood/wounds/swelling · no ECLADO branding
· no captions · logo small, fixed, top-left, inside the IG safe zone · original music preserved
· no end card · ends naturally.
