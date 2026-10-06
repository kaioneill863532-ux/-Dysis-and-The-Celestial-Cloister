"""把 build.py 用到的 Freesound 素材下载到 audio/_src（不进仓库）。

  python audio/tools/fetch_sources.py

全部是 CC0（公有领域）：可以商用、可以改，不需要署名（我们还是在 audio/README.md 里列了出处）。
下载的是 Freesound 的高质量试听版（-hq.ogg，约 192 kbps），用 ffmpeg 解码成 48 kHz 的浮点 WAV。
每一条下载前都会重新打开它在 Freesound 上的页面，确认许可证仍然是 CC0；不是就跳过并报出来。
需要：curl、ffmpeg。
"""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("DYSIS_SRC", os.path.join(HERE, "..", "_src"))
UA = "Mozilla/5.0 (X11; Linux x86_64) DysisSfx/1.0"


def curl(url, dest=None):
    a = ["curl", "-sL", "-m", "180", "-A", UA, url] + (["-o", dest, "-w", "%{http_code}"] if dest else [])
    return subprocess.run(a, capture_output=True, text=True).stdout


def page(sid, tries=4):
    """打开素材页；被限流（403/429）时等一会儿再试。"""
    for k in range(tries):
        tmp = os.path.join(OUT, f".{sid}.html")
        code = curl(f"https://freesound.org/s/{sid}/", tmp)
        html = open(tmp, encoding="utf-8", errors="ignore").read() if os.path.exists(tmp) else ""
        if os.path.exists(tmp):
            os.remove(tmp)
        if code == "200" and html:
            return html, code
        time.sleep(5 * 2 ** k)
    return "", code


def main():
    os.makedirs(OUT, exist_ok=True)
    src = json.load(open(os.path.join(HERE, "sources.json")))
    bad = []
    for sid, meta in src.items():
        wav = os.path.join(OUT, f"{sid}.wav")
        if os.path.exists(wav):
            continue
        html, code = page(sid)
        if not html:
            bad.append((sid, f"打不开素材页（HTTP {code}），多半是 Freesound 限流，过一会儿重跑"))
            continue
        lic = re.search(r'href="(https?://creativecommons.org/[^"]+)"', html)
        if not lic or "publicdomain/zero" not in lic.group(1):
            bad.append((sid, "许可证已经不是 CC0：" + (lic.group(1) if lic else "?")))
            continue
        ogg = re.search(r'data-ogg="([^"]+)"', html)
        url = ogg.group(1).replace("-lq.", "-hq.") if ogg else meta["preview"]
        tmp = os.path.join(OUT, f"{sid}.ogg")
        if curl(url, tmp) != "200":
            bad.append((sid, "download failed"))
            continue
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ar", "48000", "-c:a", "pcm_f32le", wav], check=True)
        os.remove(tmp)
        print("ok", sid, meta["user"], meta["title"][:60])
        time.sleep(1.0)   # 对 Freesound 客气一点
    json.dump(src, open(os.path.join(OUT, "credits.json"), "w"), ensure_ascii=False, indent=1)
    if bad:
        print("有问题的素材：", bad)
        sys.exit(1)
    print(f"{len(src)} 条素材都在 {os.path.abspath(OUT)}")


if __name__ == "__main__":
    main()
