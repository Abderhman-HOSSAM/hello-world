#!/usr/bin/env python3
"""Final B.WHITE finish: pad to 1080x1920, composite the official logo top-left,
re-marry the ORIGINAL audio bit-for-bit (-c:a copy), encode to Reels spec."""
import argparse, os, subprocess, sys
from PIL import Image, ImageFilter
import imageio_ffmpeg

W, H = 1080, 1920
MAUVE = (165, 119, 119)
FF = imageio_ffmpeg.get_ffmpeg_exe()


def logo_layer(path, width_px, opacity):
    im = Image.open(path).convert("RGBA")
    h = round(im.height * width_px / im.width)          # aspect preserved
    im = im.resize((width_px, h), Image.LANCZOS)
    out = Image.new("RGBA", im.size, MAUVE + (0,))       # tint to brand mauve
    out.putalpha(im.split()[3].point(lambda v: int(v * opacity)))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True, help="generated clip")
    p.add_argument("--audio-from", required=True, help="ORIGINAL source, audio copied from here")
    p.add_argument("--logo", default="bwhite/assets/bwhite_logo_vertical_alpha.png")
    p.add_argument("--logo-width-pct", type=float, default=7.8)
    p.add_argument("--logo-x", type=int, default=43)
    p.add_argument("--logo-y", type=int, default=152)
    p.add_argument("--opacity", type=float, default=0.90)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--out", default="work/BWHITE_MiniAesthetic_FINAL.mp4")
    a = p.parse_args()

    work = "work/_frames"
    os.makedirs(work, exist_ok=True)
    for f in os.listdir(work):
        os.remove(os.path.join(work, f))

    subprocess.run([FF, "-y", "-i", a.video, "-vf", f"fps={a.fps}",
                    f"{work}/s_%05d.png", "-loglevel", "error"], check=True)
    frames = sorted(os.listdir(work))
    print(f"{len(frames)} frames")

    lg = logo_layer(a.logo, round(W * a.logo_width_pct / 100), a.opacity)
    print(f"logo {lg.width}x{lg.height} = {lg.width/W*100:.1f}% width at ({a.logo_x},{a.logo_y})")

    for fn in frames:
        p_ = os.path.join(work, fn)
        im = Image.open(p_).convert("RGB")
        if im.size != (W, H):                            # fit without distorting
            s = min(W / im.width, H / im.height)
            im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            c = Image.new("RGB", (W, H), (0, 0, 0))
            c.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
            im = c
        im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=40, threshold=3)).convert("RGBA")
        im.alpha_composite(lg, (a.logo_x, a.logo_y))
        im.convert("RGB").save(p_, compress_level=1)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    subprocess.run([FF, "-y", "-framerate", str(a.fps), "-i", f"{work}/s_%05d.png",
                    "-i", a.audio_from, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
                    "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "slow",
                    "-x264-params", "keyint=48:min-keyint=24:scenecut=0",
                    "-c:a", "copy", "-movflags", "+faststart", "-shortest",
                    a.out, "-loglevel", "error"], check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
