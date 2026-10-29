import math, subprocess, sys, os, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H, FPS = 1080, 1920, 30
UP = "/root/.claude/uploads/82a74d15-a2ef-5c8b-9f08-456976cb35e4/"
BEFORE_P = UP + "14f2287c-image.png"
AFTER_P = UP + "9a4173c1-image.png"
OUT = "/home/user/hello-world/reels_bwhite/"
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts/")

CREAM = (246, 239, 234)
MAUVE = (150, 105, 115)
MAUVE_D = (110, 70, 80)
GOLD = (196, 160, 96)
DARK = (58, 40, 44)
WHITE = (255, 255, 255)
RED = (190, 70, 70)
GREEN = (80, 140, 100)

_fc = {}
def F(name, size):
    k = (name, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FD + name, size)
    return _fc[k]
def AR_B(s): return F("Tajawal-ExtraBold.ttf", s)
def AR_R(s): return F("Tajawal-Regular.ttf", s)
def AR_M(s): return F("Tajawal-Bold.ttf", s)
def LAT(s): return F("Montserrat-Bold.ttf", s)

def fill_crop(img, w, h, focus=0.36):
    iw, ih = img.size
    s = max(w / iw, h / ih)
    im = img.resize((round(iw * s), round(ih * s)), Image.LANCZOS)
    cw, ch = im.size
    cy = int(focus * ch) - h // 2
    cy = max(0, min(ch - h, cy))
    cx = (cw - w) // 2
    return im.crop((cx, cy, cx + w, cy + h))

BEFORE_SRC = Image.open(BEFORE_P).convert("RGB")
AFTER_SRC = Image.open(AFTER_P).convert("RGB")
BEFORE = fill_crop(BEFORE_SRC, W, H)
AFTER = fill_crop(AFTER_SRC, W, H)
# half-width versions for split screens
BEFORE_H = fill_crop(BEFORE_SRC, W // 2, H)
AFTER_H = fill_crop(AFTER_SRC, W // 2, H)

def ease(t):
    t = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)
def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3
def clamp(t): return max(0.0, min(1.0, t))

def tw(text, font):
    return font.getlength(text, direction="rtl")

def wrap(text, font, maxw):
    words = EMO.sub("", text).split()
    lines, cur = [], ""
    for w_ in words:
        cand = (cur + " " + w_).strip()
        if tw(cand, font) <= maxw or not cur:
            cur = cand
        else:
            lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

EMO = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+")
def text(d, xy, s, font, fill=WHITE, anchor="ma", shadow=True, lat=False):
    s = EMO.sub("", s).strip()
    x, y = xy
    kw = {} if lat else dict(direction="rtl", language="ar")
    if shadow:
        d.text((x + 3, y + 4), s, font=font, fill=(0, 0, 0, 110), anchor=anchor, **kw)
    d.text((x, y), s, font=font, fill=fill, anchor=anchor, **kw)

def para(d, cx, y, s, font, maxw=900, fill=WHITE, gap=1.25, shadow=True):
    lines = wrap(s, font, maxw)
    lh = font.size * gap
    for i, ln in enumerate(lines):
        text(d, (cx, y + i * lh), ln, font, fill, "ma", shadow)
    return y + len(lines) * lh

def rrect(d, box, r, fill, outline=None, width=0):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def badge(d, cx, cy, s, font, fill=MAUVE, color=WHITE, padx=36, pady=14, lat=False):
    w = (font.getlength(s) if lat else tw(s, font))
    h = font.size
    rrect(d, (cx - w / 2 - padx, cy - h / 2 - pady, cx + w / 2 + padx, cy + h / 2 + pady), 40, fill)
    text(d, (cx, cy), s, font, color, "mm", shadow=False, lat=lat)

def overlay_layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def gradient(alpha_top=0, alpha_bot=200, y0=0.55):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = g.load()
    s = int(H * y0)
    for y in range(s, H):
        a = int(alpha_top + (alpha_bot - alpha_top) * (y - s) / (H - s))
        for x in range(W):
            px[x, y] = (20, 10, 12, a)
    return g
GRAD = gradient()
GRAD_TOP = gradient().transpose(Image.FLIP_TOP_BOTTOM)

def brand(d, alpha=255, y=H - 150, small=True):
    text(d, (W // 2, y), "B.WHITE", LAT(44), (*GOLD, alpha), "mm", shadow=False, lat=True)
    text(d, (W // 2, y + 56), "بي وايت", AR_M(30), (*CREAM, alpha), "mm", shadow=False)
    if small:
        text(d, (W // 2, H - 48), "النتائج تختلف من شخص لآخر", AR_R(24), (*CREAM, int(alpha * 0.8)), "mm", shadow=False)

def label_tag(d, cx, cy, s, fill):
    badge(d, cx, cy, s, AR_B(40), fill=fill, padx=40, pady=12)

def compose(base, layer):
    return Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")

def tint(img, color, amount):
    if amount <= 0: return img
    ov = Image.new("RGB", img.size, color)
    return Image.blend(img, ov, amount)

def soften(img, amt):
    """amt 0..1: slight blur + brightness to simulate glow/freshness levels"""
    if amt <= 0: return img
    b = ImageEnhance.Brightness(img).enhance(1 + 0.06 * amt)
    return b

class Writer:
    def __init__(self, name, dur):
        self.n = int(dur * FPS)
        path = OUT + name
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
             "-movflags", "+faststart", path], stdin=subprocess.PIPE)
        self.name = name
    def frames(self):
        for i in range(self.n):
            yield i, i / FPS
    def put(self, img):
        self.p.stdin.write(img.tobytes())
    def close(self):
        self.p.stdin.close(); self.p.wait()
        print("done", self.name, flush=True)

def flash(img, a):
    if a <= 0: return img
    return Image.blend(img, Image.new("RGB", img.size, WHITE), a)

def split_frame(labels=True):
    im = Image.new("RGB", (W, H), CREAM)
    im.paste(BEFORE_H, (0, 0)); im.paste(AFTER_H, (W // 2, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((W // 2 - 3, 0, W // 2 + 3, H), fill=CREAM)
    if labels:
        label_tag(d, W // 4, 120, "قبل", MAUVE_D)
        label_tag(d, 3 * W // 4, 120, "بعد", GOLD)
    return im

def slide_in_text(d, t, t0, cx, y, s, font, fill=WHITE, maxw=900, dur=0.5):
    k = ease_out((t - t0) / dur)
    n = len(wrap(s, font, maxw))
    if k <= 0: return y + n * font.size * 1.25
    a = int(255 * k)
    col = (*fill[:3], a)
    para(d, cx, y + (1 - k) * 40, s, font, maxw, col)
    return y + n * font.size * 1.25

def new_canvas(base):
    im = base.copy().convert("RGBA")
    return im

# ---------------------------------------------------------------- 1
def v01_flash():
    w = Writer("01_flash_transition.mp4", 6)
    for i, t in w.frames():
        if t < 2.4:
            base = BEFORE.copy()
            # subtle zoom
            z = 1 + 0.03 * t / 2.4
            base = base.resize((int(W * z), int(H * z))).crop(((int(W * z) - W) // 2, (int(H * z) - H) // 2, (int(W * z) - W) // 2 + W, (int(H * z) - H) // 2 + H))
            im = compose(base, GRAD); d = ImageDraw.Draw(im, "RGBA")
            label_tag(d, 150, 120, "قبل", MAUVE_D)
            slide_in_text(d, t, 0.2, W // 2, 1380, "جلسة واحدة فيلر + نضارة", AR_B(78))
            slide_in_text(d, t, 0.6, W // 2, 1500, "شوفي الفرق 👀", AR_M(54), CREAM)
            if t > 2.1: im = flash(im, (t - 2.1) / 0.3)
        else:
            tt = t - 2.4
            z = 1.04 - 0.03 * clamp(tt / 3)
            base = AFTER.resize((int(W * z), int(H * z))).crop(((int(W * z) - W) // 2, (int(H * z) - H) // 2, (int(W * z) - W) // 2 + W, (int(H * z) - H) // 2 + H))
            im = compose(base, GRAD); d = ImageDraw.Draw(im, "RGBA")
            label_tag(d, 150, 120, "بعد", GOLD)
            slide_in_text(d, tt, 0.1, W // 2, 1380, "بعد الجلسة مباشرة ✨", AR_B(78))
            slide_in_text(d, tt, 0.5, W // 2, 1500, "نتيجة طبيعية.. وملامحك زي ما هي", AR_M(50), CREAM)
            brand(d)
            if tt < 0.3: im = flash(im, 1 - tt / 0.3)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 2
def v02_slider():
    w = Writer("02_slider.mp4", 8)
    for i, t in w.frames():
        # position: sweep L->R then back, then rest at middle
        if t < 3: p = ease(t / 3)
        elif t < 6: p = 1 - ease((t - 3) / 3)
        else: p = 0.5 * ease((t - 6) / 1.0) if t < 7 else 0.5
        x = int(80 + (W - 160) * p)
        im = AFTER.copy()
        im.paste(BEFORE.crop((0, 0, x, H)), (0, 0))
        im = compose(im, GRAD); d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((x - 3, 0, x + 3, H), fill=WHITE)
        d.ellipse((x - 44, H // 2 - 44, x + 44, H // 2 + 44), fill=WHITE, outline=GOLD, width=5)
        text(d, (x, H // 2), "◀ ▶", LAT(24), DARK, "mm", shadow=False, lat=True)
        label_tag(d, 150, 120, "قبل", MAUVE_D)
        label_tag(d, W - 150, 120, "بعد", GOLD)
        y1 = para(d, W // 2, 1340, "اسحبي الخط.. وشوفي الفرق", AR_B(68))
        para(d, W // 2, y1 + 10, "فيلر شفايف + سكين بوستر للنضارة", AR_M(46), fill=CREAM)
        brand(d)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 3
def v03_storyboard():
    w = Writer("03_storyboard_4_stages.mp4", 10)
    pw, ph = 500, 780
    cells = [(40, 180), (540, 180), (40, 1000), (540, 1000)]
    panels = [
        (fill_crop(BEFORE_SRC, pw, ph), "قبل", "يوم 0", MAUVE_D),
        (tint(fill_crop(BEFORE_SRC, pw, ph), (220, 190, 170), 0.18), "الجلسة", "15 دقيقة", MAUVE),
        (fill_crop(AFTER_SRC, pw, ph), "يوم 7", "اختفى التورم", GOLD),
        (fill_crop(AFTER_SRC, pw, ph), "يوم 30", "النتيجة النهائية", GOLD),
    ]
    for i, t in w.frames():
        im = Image.new("RGB", (W, H), CREAM); d = ImageDraw.Draw(im, "RGBA")
        text(d, (W // 2, 90), "رحلة النتيجة في 30 يوم", AR_B(64), DARK, "mm", shadow=False)
        for k, ((cx, cy), (pimg, lab, sub, col)) in enumerate(zip(cells, panels)):
            t0 = 0.5 + k * 1.6
            a = ease_out((t - t0) / 0.5)
            if a <= 0: continue
            off = int((1 - a) * 60)
            mask = Image.new("L", (pw, ph), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw, ph), 36, fill=int(255 * a))
            im.paste(pimg, (cx, cy + off), mask)
            d = ImageDraw.Draw(im, "RGBA")
            badge(d, cx + pw // 2, cy + off + 60, lab, AR_B(40), fill=(*col, int(255 * a)))
            text(d, (cx + pw // 2, cy + off + ph - 60), sub, AR_M(38), (*WHITE, int(255 * a)), "mm")
        if t > 7.3:
            a = int(255 * ease_out((t - 7.3) / 0.5))
            rrect(d, (120, 1800, W - 120, 1880), 40, (*DARK, a))
            text(d, (W // 2, 1840), "النتائج تختلف من شخص لآخر  •  B.WHITE", AR_M(30), (*CREAM, a), "mm", shadow=False)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 4
def v04_guess():
    w = Writer("04_guess_what_she_did.mp4", 10)
    opts = ["فيلر شفايف", "نضارة", "الاتنين مع بعض"]
    for i, t in w.frames():
        if t < 6.2:
            im = compose(AFTER, GRAD); d = ImageDraw.Draw(im, "RGBA")
            slide_in_text(d, t, 0.2, W // 2, 160, "خمّني عملت إيه؟ 🤔", AR_B(80))
            for k, o in enumerate(opts):
                t0 = 0.8 + k * 0.4
                a = ease_out((t - t0) / 0.4)
                if a <= 0: continue
                y = 1300 + k * 130
                rrect(d, (170, y, W - 170, y + 100), 50, (*WHITE, int(230 * a)))
                text(d, (W // 2, y + 50), f"{k + 1}. {o}", AR_B(44), (*DARK, int(255 * a)), "mm", shadow=False)
            if t > 2.2:
                sec = 3 - int(min(2.99, t - 2.2))
                if t < 5.2:
                    d.ellipse((W // 2 - 90, 1080, W // 2 + 90, 1260), fill=(*MAUVE, 230))
                    text(d, (W // 2, 1170), str(sec), LAT(90), WHITE, "mm", shadow=False, lat=True)
            text(d, (W // 2, 1740), "اكتبي رقمك في الكومنتات 👇", AR_M(42), CREAM, "mm")
            if t > 5.9: im = flash(im, (t - 5.9) / 0.3)
        else:
            tt = t - 6.2
            im = split_frame(); im = compose(im, GRAD); d = ImageDraw.Draw(im, "RGBA")
            a = int(255 * ease_out(tt / 0.4))
            rrect(d, (120, 1280, W - 120, 1420), 50, (*GOLD, a))
            text(d, (W // 2, 1350), "الإجابة: الاتنين مع بعض ✅", AR_B(56), (*WHITE, a), "mm", shadow=False)
            slide_in_text(d, tt, 0.5, W // 2, 1480, "فيلر شفايف 1 سيرنج + سكين بوستر للنضارة", AR_M(44), CREAM)
            brand(d)
            if tt < 0.3: im = flash(im, 1 - tt / 0.3)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 5
def area_crop(src, box_rel, w, h):
    iw, ih = src.size
    x0, y0, x1, y1 = [int(v * s) for v, s in zip(box_rel, (iw, ih, iw, ih))]
    c = src.crop((x0, y0, x1, y1))
    return fill_crop(c, w, h, focus=0.5)

def v05_area_only():
    w = Writer("05_zoom_area_only.mp4", 7)
    hh = H // 2
    # region: eyes to lips (under-eye + lips)
    bA = area_crop(BEFORE_SRC, (0.22, 0.29, 0.78, 0.47), W, hh)
    aA = area_crop(AFTER_SRC, (0.26, 0.29, 0.80, 0.47), W, hh)
    for i, t in w.frames():
        z = 1 + 0.06 * ease(t / 7)
        def kb(img):
            zi = img.resize((int(W * z), int(hh * z)))
            return zi.crop(((zi.width - W) // 2, (zi.height - hh) // 2, (zi.width - W) // 2 + W, (zi.height - hh) // 2 + hh))
        im = Image.new("RGB", (W, H), CREAM)
        im.paste(kb(bA), (0, 0)); im.paste(kb(aA), (0, hh))
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, hh - 4, W, hh + 4), fill=CREAM)
        label_tag(d, 150, 110, "قبل", MAUVE_D)
        label_tag(d, 150, hh + 110, "بعد", GOLD)
        a = int(255 * ease_out((t - 0.4) / 0.5))
        if a > 0:
            rrect(d, (90, hh - 90, W - 90, hh + 90), 45, (*DARK, min(a, 215)))
            text(d, (W // 2, hh), "تحت العين + الشفايف فقط", AR_B(52), (*WHITE, a), "mm", shadow=False)
        a2 = int(255 * ease_out((t - 1.4) / 0.5))
        if a2 > 0:
            text(d, (W // 2, H - 170), "نتيجة من غير ما نظهر الوش كامل 🤍", AR_M(42), (*WHITE, a2), "mm")
            text(d, (W // 2, H - 100), "B.WHITE", LAT(40), (*GOLD, a2), "mm", shadow=False, lat=True)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 6
def v06_natural():
    w = Writer("06_natural_not_overdone.mp4", 9)
    pts = ["شفايف أنعم من غير نفخ", "نضارة أعلى من غير لمعة صناعية", "ملامحك.. بس في أحسن نسخة"]
    for i, t in w.frames():
        k = ease(clamp((t - 2) / 3))
        base = Image.blend(BEFORE, AFTER, k)
        im = compose(base, GRAD); d = ImageDraw.Draw(im, "RGBA")
        lab = "قبل" if k < 0.5 else "بعد"
        label_tag(d, 150, 120, lab, MAUVE_D if k < 0.5 else GOLD)
        slide_in_text(d, t, 0.2, W // 2, 1250, "فيلر من غير ما حد يلاحظ إنك عملتي حاجة", AR_B(64))
        for j, p in enumerate(pts):
            a = ease_out((t - (4.2 + j * 0.8)) / 0.5)
            if a <= 0: continue
            y = 1480 + j * 95
            text(d, (W // 2, y), "✓ " + p, AR_M(42), (*CREAM, int(255 * a)), "mm")
        brand(d, y=H - 110, small=False)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 7
def v07_doctor_explains():
    w = Writer("07_doctor_explains.mp4", 12)
    # half-screen crops to keep face large
    pts = [  # (x_rel, y_rel on AFTER_H, label)
        (0.42, 0.355, "الهالات تحت العين"),
        (0.47, 0.425, "تكبير وترطيب الشفايف"),
        (0.30, 0.39, "نضارة ولمعة البشرة"),
    ]
    base = split_frame()
    for i, t in w.frames():
        im = compose(base, GRAD); d = ImageDraw.Draw(im, "RGBA")
        slide_in_text(d, t, 0.2, W // 2, 1250, "الطبيب يشرح: اتعالج إيه بالظبط؟", AR_B(56))
        for j, (px, py, lab) in enumerate(pts):
            t0 = 1.5 + j * 2.6
            a = ease_out((t - t0) / 0.5)
            if a <= 0: continue
            for side, x0 in ((0, 0), (1, W // 2)):
                cx, cy = x0 + int(px * W // 2), int(py * H)
                r = 70 + int(14 * math.sin((t - t0) * 6)) if side == 1 else 70
                d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*GOLD, int(255 * a)), width=6)
            y = 1400 + j * 100
            rrect(d, (140, y, W - 140, y + 80), 40, (*WHITE, int(225 * a)))
            text(d, (W // 2, y + 40), f"{j + 1}. {lab}", AR_B(40), (*DARK, int(255 * a)), "mm", shadow=False)
        # doctor avatar placeholder
        d.ellipse((60, 1700, 220, 1860), fill=(*MAUVE, 240), outline=WHITE, width=5)
        text(d, (140, 1780), "د.", AR_B(60), WHITE, "mm", shadow=False)
        text(d, (250, 1760), "هنا فيديو الطبيب (كام صغير)", AR_M(32), CREAM, "la")
        text(d, (250, 1810), "أو تعليق صوتي 15-20 ثانية", AR_R(30), CREAM, "la")
        text(d, (W - 60, 1800), "B.WHITE", LAT(40), GOLD, "rm", shadow=False, lat=True)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 8
def v08_three_questions():
    w = Writer("08_three_questions.mp4", 12)
    qa = [("كام سيرنج؟", "1 سيرنج شفايف"), ("كام جلسة؟", "جلسة واحدة بس"), ("النتيجة تفضل قد إيه؟", "من 9 إلى 12 شهر")]
    base = split_frame()
    for i, t in w.frames():
        im = compose(base, GRAD); d = ImageDraw.Draw(im, "RGBA")
        slide_in_text(d, t, 0.2, W // 2, 1230, "الأسئلة اللي بتوصلنا كل يوم 💬", AR_B(58))
        for j, (q, a_) in enumerate(qa):
            t0 = 1.2 + j * 3.2
            a = ease_out((t - t0) / 0.5)
            if a <= 0: continue
            y = 1310 + j * 140
            rrect(d, (100, y, W - 100, y + 120), 36, (*WHITE, int(235 * a)))
            text(d, (W - 150, y + 60), q, AR_B(40), (*DARK, int(255 * a)), "rm", shadow=False)
            a2 = ease_out((t - t0 - 1.0) / 0.4)
            if a2 > 0:
                badge(d, 330, y + 60, a_, AR_B(34), fill=(*GOLD, int(255 * a2)), padx=28, pady=10)
        brand(d)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 9
def v09_series_template():
    w = Writer("09_series_one_area_lips.mp4", 7)
    bA = area_crop(BEFORE_SRC, (0.25, 0.37, 0.75, 0.47), 980, 620)
    aA = area_crop(AFTER_SRC, (0.29, 0.37, 0.79, 0.47), 980, 620)
    for i, t in w.frames():
        im = Image.new("RGB", (W, H), CREAM); d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, 0, W, 300), fill=MAUVE_D)
        text(d, (W // 2, 110), "سلسلة: منطقة واحدة", AR_M(40), CREAM, "mm", shadow=False)
        text(d, (W // 2, 200), "الحلقة 1: الشفايف 💋", AR_B(66), WHITE, "mm", shadow=False)
        for k, (img, lab, col, y) in enumerate(((bA, "قبل", MAUVE_D, 360), (aA, "بعد", GOLD, 1060))):
            a = ease_out((t - 0.3 - k * 1.2) / 0.5)
            if a <= 0: continue
            mask = Image.new("L", img.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), 40, fill=int(255 * a))
            im.paste(img, (50, y), mask); d = ImageDraw.Draw(im, "RGBA")
            badge(d, 160, y + 70, lab, AR_B(38), fill=(*col, int(255 * a)))
        a = ease_out((t - 3.2) / 0.5)
        if a > 0:
            text(d, (W // 2, 1740), "الحلقة الجاية: تحت العين 👁️", AR_M(40), (*DARK, int(255 * a)), "mm", shadow=False)
        text(d, (W // 2, 1830), "B.WHITE  •  النتائج تختلف من شخص لآخر", AR_R(28), MAUVE_D, "mm", shadow=False)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 10
def v10_healing_timelapse():
    w = Writer("10_healing_timelapse.mp4", 9)
    stages = [("يوم 1", "تورم بسيط طبيعي", 0.22), ("يوم 3", "التورم بيقل", 0.12), ("يوم 7", "الشكل استقر", 0.04), ("يوم 14", "النتيجة النهائية ✨", 0.0)]
    for i, t in w.frames():
        k = min(3, int(t / 2.0))
        lab, sub, red = stages[k]
        base = AFTER if k >= 2 else BEFORE
        base = tint(base, (210, 120, 120), red)
        im = compose(base, GRAD); d = ImageDraw.Draw(im, "RGBA")
        slide_in_text(d, t, 0.2, W // 2, 140, "رحلة التعافي بعد الفيلر ⏳", AR_B(62))
        # progress bar
        p = ease(clamp(t / 8.0))
        rrect(d, (120, 1260, W - 120, 1290), 15, (*WHITE, 90))
        rrect(d, (120, 1260, 120 + int((W - 240) * p), 1290), 15, GOLD)
        for j in range(4):
            x = 120 + int((W - 240) * j / 3)
            d.ellipse((x - 18, 1257, x + 18, 1293), fill=GOLD if j <= k else CREAM)
        tt = t - k * 2.0
        a = int(255 * ease_out(tt / 0.4))
        badge(d, W // 2, 1400, lab, AR_B(54), fill=(*MAUVE, a), padx=50, pady=18)
        text(d, (W // 2, 1510), sub, AR_M(46), (*CREAM, a), "mm")
        text(d, (W // 2, 1640), "ملحوظة: الكدمات والتورم بيختلفوا من شخص لآخر", AR_R(30), CREAM, "mm")
        brand(d, y=H - 110, small=False)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 11
def v11_myth_fact():
    w = Writer("11_myth_vs_fact.mp4", 8)
    for i, t in w.frames():
        if t < 3.5:
            base = tint(BEFORE, (40, 30, 35), 0.35)
            im = compose(base, GRAD); d = ImageDraw.Draw(im, "RGBA")
            badge(d, W // 2, 160, "أسطورة ❌", AR_B(54), fill=RED, padx=50, pady=16)
            slide_in_text(d, t, 0.3, W // 2, 1300, "«الفيلر بيخلي الوش منفوخ ومبالغ فيه»", AR_B(62))
            if t > 3.2: im = flash(im, (t - 3.2) / 0.3)
        else:
            tt = t - 3.5
            im = compose(AFTER, GRAD); d = ImageDraw.Draw(im, "RGBA")
            badge(d, W // 2, 160, "الحقيقة ✅", AR_B(54), fill=GREEN, padx=50, pady=16)
            slide_in_text(d, tt, 0.1, W // 2, 1280, "الفيلر الصح بيحافظ على ملامحك", AR_B(58))
            slide_in_text(d, tt, 0.6, W // 2, 1400, "الفرق في الكمية.. ومكان الحقن.. وإيد الطبيب", AR_M(44), CREAM)
            label_tag(d, 150, 300, "بعد", GOLD)
            brand(d)
            if tt < 0.3: im = flash(im, 1 - tt / 0.3)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 12
def v12_fears():
    w = Writer("12_fears_before_session.mp4", 10)
    fears = ["خايفة من الألم 😣", "خايفة الشكل يبقى مبالغ", "خايفة من الكدمات"]
    for i, t in w.frames():
        if t < 5.5:
            im = compose(BEFORE, GRAD); d = ImageDraw.Draw(im, "RGBA")
            slide_in_text(d, t, 0.2, W // 2, 140, "كانت خايفة من إيه قبل الجلسة؟", AR_B(58))
            for j, f_ in enumerate(fears):
                a = ease_out((t - (1.0 + j * 0.9)) / 0.5)
                if a <= 0: continue
                y = 1300 + j * 130
                rrect(d, (150, y, W - 150, y + 100), 50, (*WHITE, int(230 * a)))
                text(d, (W // 2, y + 50), f_, AR_B(42), (*DARK, int(255 * a)), "mm", shadow=False)
            label_tag(d, 150, 300, "قبل", MAUVE_D)
            if t > 5.2: im = flash(im, (t - 5.2) / 0.3)
        else:
            tt = t - 5.5
            im = compose(AFTER, GRAD); d = ImageDraw.Draw(im, "RGBA")
            label_tag(d, 150, 300, "بعد", GOLD)
            slide_in_text(d, tt, 0.1, W // 2, 1250, "وبعد الجلسة قالت:", AR_M(46), CREAM)
            slide_in_text(d, tt, 0.5, W // 2, 1340, "«ما حسيتش بحاجة.. والشكل طبيعي جداً 🤍»", AR_B(58))
            slide_in_text(d, tt, 1.2, W // 2, 1560, "— تقييم عميلة بي وايت", AR_R(36), CREAM)
            brand(d)
            if tt < 0.3: im = flash(im, 1 - tt / 0.3)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 13
def v13_pov():
    w = Writer("13_pov_session.mp4", 8)
    for i, t in w.frames():
        if t < 4.5:
            base = BEFORE
            im = compose(base, GRAD); d = ImageDraw.Draw(im, "RGBA")
            # camera UI
            if int(t * 2) % 2 == 0: d.ellipse((70, 70, 110, 110), fill=(230, 50, 50))
            text(d, (130, 90), "REC", LAT(34), WHITE, "lm", shadow=False, lat=True)
            text(d, (W - 70, 90), f"00:{int(t):02d}:{int((t % 1) * 30):02d}", LAT(34), WHITE, "rm", shadow=False, lat=True)
            for (x, y, dx, dy) in ((60, 160, 1, 1), (W - 60, 160, -1, 1), (60, H - 240, 1, -1), (W - 60, H - 240, -1, -1)):
                d.line((x, y, x + 60 * dx, y), fill=WHITE, width=5); d.line((x, y, x, y + 60 * dy), fill=WHITE, width=5)
            slide_in_text(d, t, 0.3, W // 2, 1300, "POV: جلستك في بي وايت 💉", AR_B(66))
            slide_in_text(d, t, 0.9, W // 2, 1420, "هنا بنحط لقطات الجلسة من زاوية الطبيب", AR_M(40), CREAM)
            slide_in_text(d, t, 1.3, W // 2, 1490, "تعقيم • تخدير • حقن • مساج", AR_R(36), CREAM)
            if t > 4.2: im = flash(im, (t - 4.2) / 0.3)
        else:
            tt = t - 4.5
            im = split_frame(); im = compose(im, GRAD); d = ImageDraw.Draw(im, "RGBA")
            slide_in_text(d, tt, 0.1, W // 2, 1350, "والنتيجة بعد 15 دقيقة بس ✨", AR_B(64))
            brand(d)
            if tt < 0.3: im = flash(im, 1 - tt / 0.3)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 14
def v14_occasion():
    w = Writer("14_occasion_before_wedding.mp4", 7)
    for i, t in w.frames():
        if t < 3.5:
            im = compose(BEFORE, GRAD); d = ImageDraw.Draw(im, "RGBA")
            slide_in_text(d, t, 0.2, W // 2, 1250, "باقي 14 يوم على الفرح 👰", AR_B(70))
            slide_in_text(d, t, 0.8, W // 2, 1380, "جلسة نضارة + فيلر خفيف.. وتبقي جاهزة", AR_M(46), CREAM)
            label_tag(d, 150, 120, "قبل", MAUVE_D)
            if t > 3.2: im = flash(im, (t - 3.2) / 0.3)
        else:
            tt = t - 3.5
            im = compose(AFTER, GRAD); d = ImageDraw.Draw(im, "RGBA")
            label_tag(d, 150, 120, "بعد", GOLD)
            slide_in_text(d, tt, 0.1, W // 2, 1280, "جاهزة ليوم الفرح ✨", AR_B(76))
            slide_in_text(d, tt, 0.6, W // 2, 1400, "احجزي جلستك قبل المناسبة بأسبوعين على الأقل", AR_M(40), CREAM)
            brand(d)
            if tt < 0.3: im = flash(im, 1 - tt / 0.3)
        w.put(im)
    w.close()

# ---------------------------------------------------------------- 15
def v15_ultra_short():
    w = Writer("15_ultra_short_3s.mp4", 3.5)
    for i, t in w.frames():
        if t < 1.1:
            im = BEFORE.copy(); d = ImageDraw.Draw(im, "RGBA")
            label_tag(d, W // 2, 160, "قبل", MAUVE_D)
            if t > 0.95: im = flash(im, (t - 0.95) / 0.15)
        elif t < 2.4:
            im = AFTER.copy(); d = ImageDraw.Draw(im, "RGBA")
            label_tag(d, W // 2, 160, "بعد", GOLD)
            if t < 1.25: im = flash(im, 1 - (t - 1.1) / 0.15)
        else:
            im = Image.new("RGB", (W, H), CREAM); d = ImageDraw.Draw(im, "RGBA")
            a = int(255 * ease_out((t - 2.4) / 0.4))
            text(d, (W // 2, H // 2 - 40), "B.WHITE", LAT(90), (*GOLD, a), "mm", shadow=False, lat=True)
            text(d, (W // 2, H // 2 + 60), "بي وايت", AR_B(54), (*MAUVE_D, a), "mm", shadow=False)
            text(d, (W // 2, H // 2 + 160), "فيلر • نضارة • بوتوكس", AR_M(40), (*DARK, a), "mm", shadow=False)
        w.put(im)
    w.close()

ALL = [v01_flash, v02_slider, v03_storyboard, v04_guess, v05_area_only, v06_natural, v07_doctor_explains,
       v08_three_questions, v09_series_template, v10_healing_timelapse, v11_myth_fact, v12_fears, v13_pov,
       v14_occasion, v15_ultra_short]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sel = sys.argv[1:]
    for fn in ALL:
        if not sel or any(s in fn.__name__ for s in sel):
            fn()
