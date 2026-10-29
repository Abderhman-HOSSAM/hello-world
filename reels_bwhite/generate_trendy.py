"""Trendy reel variants: beat-synced, glitch, light leaks, text-message reveal, half-face hook."""
import math, random, subprocess, sys, os, wave, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance
import gen
from gen import (W, H, FPS, BEFORE, AFTER, CREAM, MAUVE, MAUVE_D, GOLD, DARK, WHITE, F, AR_B, AR_M, AR_R, LAT,
                 text, para, badge, rrect, ease, ease_out, clamp, compose, GRAD, flash, brand, label_tag)

OUT = gen.OUT
BPM = 120
BEAT = 60 / BPM          # 0.5 s
random.seed(7)
def CAIRO(s): return F("Cairo-Black.ttf", s)

# ------------------------------------------------------------------ audio (placeholder beat, replace with trending sound)
def make_beat(path, dur, bpm=BPM, sr=44100, pops=None, hard=True):
    n = int(dur * sr); t = np.arange(n) / sr
    out = np.zeros(n)
    beat = 60 / bpm
    k = 0
    while k * beat < dur:
        s = int(k * beat * sr)
        if k % 2 == 0 and hard:   # kick on 1,3
            tt = np.arange(0, int(0.25 * sr)) / sr
            kick = np.sin(2 * np.pi * (60 + 80 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12)
            e = min(n, s + len(kick)); out[s:e] += kick[:e - s] * 0.9
        if k % 2 == 1:   # clap/snare
            tt = np.arange(0, int(0.18 * sr)) / sr
            snare = (np.random.rand(len(tt)) * 2 - 1) * np.exp(-tt * 28) * 0.5
            e = min(n, s + len(snare)); out[s:e] += snare[:e - s]
        for h in (0, 0.5):   # hats on 8ths
            hs = int((k + h) * beat * sr)
            tt = np.arange(0, int(0.05 * sr)) / sr
            hat = (np.random.rand(len(tt)) * 2 - 1) * np.exp(-tt * 90) * 0.18
            e = min(n, hs + len(hat)); out[hs:e] += hat[:e - hs]
        k += 1
    # bass pulse
    out += 0.12 * np.sin(2 * np.pi * 55 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * t / (beat * 2)))
    for p in (pops or []):   # message pops
        s = int(p * sr); tt = np.arange(0, int(0.12 * sr)) / sr
        pop = np.sin(2 * np.pi * 900 * tt) * np.exp(-tt * 45) * 0.6
        e = min(n, s + len(pop)); out[s:e] += pop[:e - s]
    out = np.clip(out / max(1e-6, np.abs(out).max()) * 0.85, -1, 1)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((out * 32767).astype("<i2").tobytes())

class Writer(gen.Writer):
    def __init__(self, name, dur, audio=None):
        self.n = int(dur * FPS); self.name = name; self.final = OUT + name
        self.tmp = OUT + "_tmp_" + name
        self.audio = audio
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
             "-crf", "23", self.tmp], stdin=subprocess.PIPE)
    def close(self):
        self.p.stdin.close(); self.p.wait()
        if self.audio:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", self.tmp, "-i", self.audio, "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", self.final], check=True)
            os.remove(self.tmp)
        else:
            os.replace(self.tmp, self.final)
        print("done", self.name, flush=True)

# ------------------------------------------------------------------ effects
def zoom(img, z, cx=0.5, cy=0.42):
    if abs(z - 1) < 1e-3: return img
    w, h = img.size
    cw, ch = int(w / z), int(h / z)
    x0 = int(cx * w - cw / 2); y0 = int(cy * h - ch / 2)
    x0 = max(0, min(w - cw, x0)); y0 = max(0, min(h - ch, y0))
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR)

def shake(img, amp):
    if amp <= 0: return img
    dx, dy = random.randint(-amp, amp), random.randint(-amp, amp)
    return ImageChops.offset(zoom(img, 1 + amp / 400), dx, dy)

def rgb_split(img, k):
    if k <= 0: return img
    r, g, b = img.split()
    r = ImageChops.offset(r, -k, 0); b = ImageChops.offset(b, k, 0)
    return Image.merge("RGB", (r, g, b))

def _leak(color, size=(W, H)):
    g = Image.new("L", (size[0] // 8, size[1] // 8), 0)
    d = ImageDraw.Draw(g)
    d.ellipse((-20, -20, size[0] // 8 * 0.9, size[1] // 8 * 0.5), fill=255)
    g = g.filter(ImageFilter.GaussianBlur(28)).resize(size, Image.BILINEAR)
    ov = Image.new("RGB", size, color)
    return ov, g
LEAKS = [_leak((255, 140, 90)), _leak((255, 90, 150)), _leak((255, 210, 120))]

def light_leak(img, i, a, pos=0.0):
    ov, g = LEAKS[i % len(LEAKS)]
    g2 = ImageChops.offset(g, int(pos * W), int(pos * H * 0.3))
    g2 = g2.point(lambda v: int(v * a))
    base = img.copy(); base.paste(ov, (0, 0), g2)   # screen-ish via paste with mask
    return ImageChops.screen(img, Image.composite(ov, Image.new("RGB", img.size, 0), g2))

GRAINS = [Image.fromarray((np.random.rand(H // 2, W // 2) * 255).astype("uint8")).resize((W, H)).convert("RGB") for _ in range(4)]
def grain(img, a, i):
    if a <= 0: return img
    return Image.blend(img, ImageChops.overlay(img, GRAINS[i % 4]), a)

def star(d, cx, cy, r, col):
    pts = []
    for k in range(8):
        ang = k * math.pi / 4; rr = r if k % 2 == 0 else r * 0.25
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=col)

SPARKS = [(random.random(), random.random(), random.uniform(10, 40), random.random() * 6) for _ in range(40)]
def sparkles(d, t, a=1.0, n=40, region=None):
    for (x, y, r, ph) in SPARKS[:n]:
        tw = 0.5 + 0.5 * math.sin(t * 7 + ph)
        if tw < 0.35: continue
        X, Y = x * W, y * H
        if region and not (region[0] <= X <= region[2] and region[1] <= Y <= region[3]): continue
        star(d, X, Y, r * tw, (255, 250, 230, int(255 * a * tw)))

def whip(img, dx, blur):
    im = ImageChops.offset(img, int(dx), 0)
    return im.filter(ImageFilter.BoxBlur((blur, 0))) if blur > 0 else im

def spin(img, ang, z, blur):
    im = zoom(img, z).rotate(ang, resample=Image.BILINEAR)
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur > 0 else im

def letterbox(d, h=120):
    d.rectangle((0, 0, W, h), fill=(0, 0, 0)); d.rectangle((0, H - h, W, H), fill=(0, 0, 0))

def big_text(d, cx, cy, s, size, fill=WHITE, stroke=(0, 0, 0), lat=False, sw=8):
    s = gen.EMO.sub("", s).strip()
    f = LAT(size) if lat else CAIRO(size)
    kw = {} if lat else dict(direction="rtl", language="ar")
    d.text((cx, cy), s, font=f, fill=fill, anchor="mm", stroke_width=sw, stroke_fill=stroke, **kw)

def beat_phase(t): return (t % BEAT) / BEAT
def beat_idx(t): return int(t // BEAT)

# ------------------------------------------------------------------ T1 beat-sync glow up
def t1_beat_sync():
    dur = 8.0
    make_beat(OUT + "_beat1.wav", dur)
    w = Writer("T1_beat_sync_glowup.mp4", dur, OUT + "_beat1.wav")
    for i, t in w.frames():
        b = beat_idx(t); ph = beat_phase(t)
        punch = 1 + 0.10 * (1 - ease_out(ph * 1.6))  # zoom punch on each beat
        if t < 2.0:                                   # intro: before, slow zoom, building text
            im = zoom(BEFORE, 1 + 0.04 * t / 2)
            im = grain(im, 0.15, i)
            d = ImageDraw.Draw(im, "RGBA")
            letterbox(d)
            big_text(d, W // 2, 1560, "قبل", 110)
            if b >= 1: big_text(d, W // 2, 1700, "استني للبيت 🔊", 52, CREAM, sw=5)
        elif t < 5.0:                                 # rapid alternation on 8ths with glitch
            eighth = int((t - 2.0) // (BEAT / 2))
            src = AFTER if eighth % 2 else BEFORE
            im = zoom(src, punch * (1.06 if eighth % 2 else 1.0))
            im = rgb_split(im, 14 if ph < 0.15 else 3)
            im = shake(im, 10 if ph < 0.2 else 0)
            im = light_leak(im, eighth, 0.55 if ph < 0.3 else 0.2, pos=(eighth % 3 - 1) * 0.3)
            im = grain(im, 0.25, i)
            d = ImageDraw.Draw(im, "RGBA")
            letterbox(d)
            big_text(d, W // 2, 1560, "بعد" if eighth % 2 else "قبل", 120, GOLD if eighth % 2 else WHITE)
            if ph < 0.12: im = flash(im, 0.6)
        else:                                         # drop: after, hero
            tt = t - 5.0
            im = zoom(AFTER, 1.12 - 0.08 * ease_out(tt / 1.5) + 0.05 * (1 - ease_out(ph * 2)))
            im = light_leak(im, 2, 0.35, pos=-0.2 + 0.1 * math.sin(tt))
            im = grain(im, 0.12, i)
            d = ImageDraw.Draw(im, "RGBA")
            letterbox(d)
            sparkles(d, t, 0.9)
            big_text(d, W // 2, 1480, "GLOW UP", 120, GOLD, lat=True)
            big_text(d, W // 2, 1610, "جلسة واحدة.. فيلر + نضارة", 56, WHITE, sw=5)
            text(d, (W // 2, 1730), "B.WHITE", LAT(40), GOLD, "mm", shadow=False, lat=True)
            if tt < 0.2: im = flash(im, 1 - tt / 0.2)
        w.put(im)
    w.close()

# ------------------------------------------------------------------ T2 text-message reveal
def t2_text_message():
    dur = 10.0
    msgs = [  # (time, side, text)  side 'f' = friend (left, grey), 'm' = me (right, mauve)
        (0.6, "f", "انتي عملتي حاجة في وشك؟ 👀"),
        (1.8, "m", "لا والله 😇"),
        (2.9, "f", "طب إيه الجمال ده!! بشرتك منورة"),
        (4.1, "m", "طيب هقولك بس متقوليش لحد 🤫"),
        (5.3, "m", "بي وايت.. فيلر + نضارة"),
        (6.3, "f", "ابعتي الصورة حالاً!!"),
    ]
    make_beat(OUT + "_beat2.wav", dur, pops=[m[0] for m in msgs], hard=False)
    w = Writer("T2_text_message_reveal.mp4", dur, OUT + "_beat2.wav")
    fnt = AR_M(40)
    for i, t in w.frames():
        if t < 7.3:
            base = zoom(BEFORE, 1 + 0.03 * t / 7.3)
            base = Image.blend(base, Image.new("RGB", (W, H), (20, 15, 18)), 0.45)
            im = base.filter(ImageFilter.GaussianBlur(6)) if t < 7.0 else base
            d = ImageDraw.Draw(im, "RGBA")
            # phone chat header
            rrect(d, (60, 160, W - 60, 300), 40, (255, 255, 255, 235))
            d.ellipse((100, 185, 190, 275), fill=MAUVE)
            text(d, (145, 230), "ص", AR_B(44), WHITE, "mm", shadow=False)
            text(d, (220, 215), "صاحبتي 💕", AR_B(36), DARK, "la", shadow=False)
            text(d, (220, 262), "متصلة الآن", AR_R(26), (120, 120, 120), "la", shadow=False)
            y = 380
            for (t0, side, s) in msgs:
                if t < t0: break
                a = ease_out((t - t0) / 0.3)
                lines = gen.wrap(s, fnt, 640)
                bw = max(gen.tw(l, fnt) for l in lines) + 70
                bh = len(lines) * 54 + 40
                if side == "m":
                    x1 = W - 70; x0 = x1 - bw; col = (*MAUVE, int(255 * a)); tc = WHITE
                else:
                    x0 = 70; x1 = x0 + bw; col = (245, 245, 245, int(255 * a)); tc = DARK
                yy = y + (1 - a) * 25
                rrect(d, (x0, yy, x1, yy + bh), 34, col)
                for k, l in enumerate(lines):
                    text(d, (x1 - 35, yy + 20 + k * 54), l, fnt, (*tc[:3], int(255 * a)), "ra", shadow=False)
                y += bh + 22
            # typing indicator
            nxt = [m for m in msgs if m[0] > t]
            if nxt and nxt[0][0] - t < 0.6:
                side = nxt[0][1]
                x0 = (W - 70 - 170) if side == "m" else 70
                rrect(d, (x0, y, x0 + 170, y + 80), 34, (*MAUVE, 255) if side == "m" else (245, 245, 245, 255))
                for k in range(3):
                    r = 9 + 4 * max(0, math.sin(t * 9 + k))
                    d.ellipse((x0 + 45 + k * 40 - r, y + 40 - r, x0 + 45 + k * 40 + r, y + 40 + r), fill=WHITE if side == "m" else (150, 150, 150))
            if t > 6.9:
                big_text(d, W // 2, 1650, "📸 الصورة اللي بعتتها 👇", 50, WHITE, sw=5)
            if t > 7.1: im = flash(im, (t - 7.1) / 0.2)
        else:
            tt = t - 7.3
            ph = beat_phase(t)
            im = zoom(AFTER, 1.08 - 0.05 * ease_out(tt / 1.2))
            im = light_leak(im, 1, 0.3, pos=-0.15)
            d = ImageDraw.Draw(im, "RGBA")
            sparkles(d, t, 0.8, 30)
            label_tag(d, W - 150, 120, "بعد", GOLD)
            # polaroid-ish 'before' inset
            ins = BEFORE.resize((270, 480));
            a = ease_out((tt - 0.4) / 0.4)
            if a > 0:
                fr = Image.new("RGB", (300, 560), WHITE); fr.paste(ins, (15, 15))
                fr = fr.rotate(-8, expand=True, fillcolor=None)
                mask = Image.new("L", fr.size, 0); ImageDraw.Draw(mask).rectangle((0, 0, *fr.size), fill=int(255 * a))
                mask = ImageChops.multiply(mask, fr.convert("L").point(lambda v: 255 if v > 0 else 0))
                im.paste(fr, (60, 1150 + int((1 - a) * 60)), mask)
                d = ImageDraw.Draw(im, "RGBA")
                text(d, (210, 1680), "قبل", AR_B(36), DARK, "mm", shadow=False)
            big_text(d, W // 2 + 120, 1500, "«لا والله مش عاملة حاجة» 😇", 46, WHITE, sw=5)
            text(d, (W // 2, 1790), "B.WHITE", LAT(40), GOLD, "mm", shadow=False, lat=True)
            if tt < 0.2: im = flash(im, 1 - tt / 0.2)
        w.put(im)
    w.close()

# ------------------------------------------------------------------ T3 wait for it + whip/spin transition
def t3_wait_for_it():
    dur = 7.0
    make_beat(OUT + "_beat3.wav", dur)
    w = Writer("T3_wait_for_it_whip.mp4", dur, OUT + "_beat3.wav")
    for i, t in w.frames():
        if t < 3.5:
            z = 1 + 0.25 * ease(t / 3.5)
            im = zoom(BEFORE, z, 0.5, 0.40)
            im = grain(im, 0.15, i)
            d = ImageDraw.Draw(im, "RGBA")
            letterbox(d, 100)
            pulse = 1 + 0.06 * math.sin(t * 8)
            big_text(d, W // 2, 1560, "استني لآخر الفيديو", int(64 * pulse), WHITE, sw=6)
            dots = "." * (int(t * 3) % 4)
            big_text(d, W // 2, 1660, "wait for it" + dots, 40, CREAM, lat=True, sw=4)
            if t > 3.2: im = whip(im, -(t - 3.2) / 0.3 * 700, int((t - 3.2) / 0.3 * 40))
        elif t < 3.9:
            k = (t - 3.5) / 0.4
            im = spin(AFTER, 25 * (1 - ease_out(k)), 1.3 - 0.2 * ease_out(k), 12 * (1 - k))
            im = whip(im, (1 - ease_out(k)) * 500, int((1 - k) * 40))
            im = light_leak(im, 0, 0.8 * (1 - k) + 0.2, pos=0.1)
            im = flash(im, 0.7 * (1 - k))
        else:
            tt = t - 3.9; ph = beat_phase(t)
            im = zoom(AFTER, 1.10 - 0.06 * ease_out(tt / 1.5) + 0.04 * (1 - ease_out(ph * 2)))
            im = light_leak(im, 2, 0.3, pos=-0.1 + 0.08 * math.sin(tt * 2))
            im = grain(im, 0.1, i)
            d = ImageDraw.Draw(im, "RGBA")
            letterbox(d, 100)
            sparkles(d, t, 0.9)
            big_text(d, W // 2, 1540, "✨ بعد ✨", 110, GOLD)
            big_text(d, W // 2, 1660, "فيلر شفايف + نضارة في جلسة واحدة", 46, WHITE, sw=5)
            text(d, (W // 2, 1760), "B.WHITE", LAT(40), GOLD, "mm", shadow=False, lat=True)
        w.put(im)
    w.close()

# ------------------------------------------------------------------ T4 half-face hook (sound-off friendly)
AFTER_AL = ImageChops.offset(AFTER, -22, 0)
def t4_half_face():
    dur = 7.0
    make_beat(OUT + "_beat4.wav", dur)
    w = Writer("T4_half_face_hook.mp4", dur, OUT + "_beat4.wav")
    for i, t in w.frames():
        ph = beat_phase(t); b = beat_idx(t)
        if t < 3.0:
            # static split from frame 1 (strong hook), split line pulses on beat
            im = AFTER_AL.copy(); im.paste(BEFORE.crop((0, 0, W // 2, H)), (0, 0))
            im = zoom(im, 1 + 0.03 * (1 - ease_out(ph * 1.5)))
            d = ImageDraw.Draw(im, "RGBA")
            d.rectangle((W // 2 - 4, 0, W // 2 + 4, H), fill=WHITE)
            big_text(d, W // 4, 160, "قبل", 72, WHITE)
            big_text(d, 3 * W // 4, 160, "بعد", 72, GOLD)
            big_text(d, W // 2, 1560, "نفس الوش.. جلسة واحدة", 64, WHITE, sw=6)
            big_text(d, W // 2, 1660, "👈 بص على الشفايف وتحت العين", 44, CREAM, sw=4)
        elif t < 5.0:
            # wipe sweeps on beats: reveal full after then full before then after
            k = (t - 3.0) / 2.0
            seq = [0.5, 1.0, 0.0, 1.0]
            seg = min(3, int(k * 4)); f = (k * 4) % 1
            p0 = seq[seg]; p1 = seq[min(3, seg + 1)]
            p = p0 + (p1 - p0) * ease(f)
            x = int(p * W)
            im = AFTER_AL.copy()
            if x > 0: im.paste(BEFORE.crop((0, 0, x, H)), (0, 0))
            im = rgb_split(im, int(10 * abs(math.sin(f * math.pi))))
            d = ImageDraw.Draw(im, "RGBA")
            if 0 < x < W: d.rectangle((x - 4, 0, x + 4, H), fill=WHITE)
            big_text(d, W // 2, 1560, "شوفي الفرق 👀", 72, WHITE, sw=6)
            if f < 0.1: im = flash(im, 0.4)
        else:
            tt = t - 5.0
            im = zoom(AFTER, 1.08 - 0.05 * ease_out(tt / 1.5) + 0.04 * (1 - ease_out(ph * 2)))
            im = light_leak(im, 1, 0.3, pos=-0.1)
            d = ImageDraw.Draw(im, "RGBA")
            sparkles(d, t, 0.8, 30)
            big_text(d, W // 2, 1540, "بعد", 110, GOLD)
            big_text(d, W // 2, 1660, "احجزي استشارتك من اللينك في البايو", 44, WHITE, sw=5)
            text(d, (W // 2, 1770), "B.WHITE", LAT(40), GOLD, "mm", shadow=False, lat=True)
        w.put(im)
    w.close()

# ------------------------------------------------------------------ T5 meme format: nobody / me after
def t5_meme():
    dur = 6.5
    make_beat(OUT + "_beat5.wav", dur)
    w = Writer("T5_meme_nobody_me_after.mp4", dur, OUT + "_beat5.wav")
    for i, t in w.frames():
        ph = beat_phase(t)
        if t < 2.5:
            im = Image.new("RGB", (W, H), WHITE)
            d = ImageDraw.Draw(im, "RGBA")
            a = ease_out(t / 0.3)
            d.text((80, 420), "Nobody:", font=LAT(76), fill=(*DARK, int(255 * a)), anchor="la")
            if t > 0.8:
                a2 = ease_out((t - 0.8) / 0.3)
                text(d, (W - 80, 620), "أنا بعد جلسة فيلر + نضارة في بي وايت:", AR_B(58), (*DARK, int(255 * a2)), "ra", shadow=False)
            # small pre-photo
            sm = zoom(BEFORE, 1.0).resize((480, 853))
            im.paste(sm, (300, 860))
            d = ImageDraw.Draw(im, "RGBA")
            text(d, (W // 2, 1760), "قبل", AR_B(44), DARK, "mm", shadow=False)
            if t > 2.3: im = flash(im, (t - 2.3) / 0.2)
        else:
            tt = t - 2.5
            z = 1.0 + 0.35 * ease(clamp(tt / 3.5))   # slow smug zoom-in on face
            im = zoom(AFTER, z + 0.03 * (1 - ease_out(ph * 2)), 0.5, 0.38)
            im = light_leak(im, 2, 0.35, pos=-0.15 + 0.1 * math.sin(tt * 1.5))
            im = grain(im, 0.1, i)
            d = ImageDraw.Draw(im, "RGBA")
            sparkles(d, t, 1.0, 40)
            big_text(d, W // 2, 200, "💅 أنا:", 90, WHITE, sw=7)
            if tt > 1.2:
                big_text(d, W // 2, 1620, "«لا مش عاملة حاجة.. ده نوم» 😌", 50, WHITE, sw=5)
            text(d, (W // 2, 1780), "B.WHITE", LAT(40), GOLD, "mm", shadow=False, lat=True)
            if tt < 0.2: im = flash(im, 1 - tt / 0.2)
        w.put(im)
    w.close()

# ------------------------------------------------------------------ T6 photobooth / polaroid drop
def polaroid(src, size=(560, 760), rot=0, cap=""):
    ph = src.copy(); ph = gen.fill_crop(ph, size[0] - 50, size[1] - 150, focus=0.36)
    fr = Image.new("RGBA", (size[0], size[1]), (255, 255, 255, 255)); fr.paste(ph, (25, 25))
    d = ImageDraw.Draw(fr)
    if cap: text(d, (size[0] // 2, size[1] - 70), cap, AR_B(40), DARK, "mm", shadow=False)
    return fr.rotate(rot, expand=True, resample=Image.BICUBIC)

def t6_polaroid():
    dur = 7.5
    make_beat(OUT + "_beat6.wav", dur)
    w = Writer("T6_polaroid_drop.mp4", dur, OUT + "_beat6.wav")
    P1 = polaroid(gen.BEFORE_SRC, rot=-7, cap="قبل")
    P2 = polaroid(gen.AFTER_SRC, rot=6, cap="بعد ✨")
    bg = Image.blend(BEFORE.filter(ImageFilter.GaussianBlur(30)), Image.new("RGB", (W, H), CREAM), 0.6)
    for i, t in w.frames():
        ph = beat_phase(t)
        im = bg.copy()
        d = ImageDraw.Draw(im, "RGBA")
        big_text(d, W // 2, 180, "نتيجة جلسة النهاردة 📸", 64, DARK, stroke=WHITE, sw=6)
        # P1 drops at 0.3, P2 drops at 2.3 (on beats), each with bounce
        for (P, t0, x, y) in ((P1, 0.5, 120, 420), (P2, 2.5, 380, 760)):
            k = (t - t0) / 0.45
            if k < 0: continue
            e = ease_out(min(1, k)); bounce = 0 if k >= 1 else 0
            yy = y - int((1 - e) * 900)
            sc = 1.6 - 0.6 * e
            PP = P.resize((int(P.width * sc), int(P.height * sc)))
            # shadow
            sh = Image.new("RGBA", PP.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 120), (0, 0), PP.split()[3])
            sh = sh.filter(ImageFilter.GaussianBlur(18))
            im.paste(sh, (x + 20, yy + 30), sh)
            im.paste(PP, (x, yy), PP)
            if 0.98 < k < 1.25:
                im = shake(im, 8)
        d = ImageDraw.Draw(im, "RGBA")
        if t > 3.3:
            sparkles(d, t, 0.9, 25, region=(380, 760, 1000, 1600))
        if t > 4.0:
            a = ease_out((t - 4.0) / 0.4)
            badge(d, W // 2, 1760, "فيلر شفايف + نضارة • B.WHITE", AR_B(40), fill=(*MAUVE_D, int(255 * a)), padx=44, pady=16)
        if abs(t - 0.5) < 0.12 or abs(t - 2.5) < 0.12: im = flash(im, 0.5)
        w.put(im)
    w.close()

ALL = [t1_beat_sync, t2_text_message, t3_wait_for_it, t4_half_face, t5_meme, t6_polaroid]
if __name__ == "__main__":
    sel = sys.argv[1:]
    for fn in ALL:
        if not sel or any(s in fn.__name__ for s in sel):
            fn()
