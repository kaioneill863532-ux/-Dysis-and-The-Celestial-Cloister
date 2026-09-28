"""Build a small UI font from the OFL-licensed Fontsource Noto Serif SC pack.

Usage: python scripts/subset-font.py /path/to/fontsource-noto-serif-sc-5.3.0.tgz
Requires fontTools with brotli. The output is deterministic for a fixed pack.
"""

from __future__ import annotations

import re
import sys
import tarfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from fontTools.merge import Merger
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "prototype" / "rotunda"
DEST = SOURCE / "fonts"
TEXT_FILES = [*SOURCE.rglob("*.html"), *SOURCE.rglob("*.js")]
# Keep Latin glyphs supplied by the browser's existing Georgia/Palatino stack.
CHARS = {ord(c) for file in TEXT_FILES for c in file.read_text() if ord(c) > 0x7F}


def main(archive: str) -> None:
    DEST.mkdir(exist_ok=True)
    used = set()
    with TemporaryDirectory() as temporary, tarfile.open(archive, "r:gz") as pack:
        slices = []
        members = sorted(
            (m for m in pack if re.fullmatch(r"package/files/noto-serif-sc-\d+-400-normal\.woff2", m.name)),
            key=lambda m: int(m.name.split("-")[-3]),
        )
        for member in members:
            font = TTFont(BytesIO(pack.extractfile(member).read()))
            present = set(font.getBestCmap()) & CHARS
            present -= used
            if not present:
                continue
            options = Options()
            options.flavor = "woff2"
            options.layout_features = []
            subsetter = Subsetter(options=options)
            subsetter.populate(unicodes=present)
            subsetter.subset(font)
            font.flavor = "woff2"
            filename = Path(temporary) / ("ui-" + member.name.split("-")[-3] + ".woff2")
            font.save(filename)
            slices.append(str(filename))
            used |= present
        merged = Merger().merge(slices)
        merged.flavor = "woff2"
        merged.save(DEST / "dysis-serif-sc.woff2")
        (DEST / "OFL.txt").write_bytes(pack.extractfile("package/LICENSE").read())
    missing = sorted(c for c in CHARS - used if 0x3000 <= c <= 0x9FFF)
    if missing:
        raise RuntimeError(f"Missing CJK glyphs: {''.join(map(chr, missing))}")
    for old in DEST.glob("ui-*.woff2"):
        old.unlink()
    ranges = ",".join(f"U+{c:X}" for c in sorted(used))
    (DEST / "faces.css").write_text(
        "@font-face{font-family:'Dysis Serif SC';font-style:normal;"
        "font-weight:400;font-display:block;"
        "src:url('./dysis-serif-sc.woff2') format('woff2');"
        f"unicode-range:{ranges}}}\n"
    )
    print(f"{len(used)} glyphs in one face, "
          f"{(DEST / 'dysis-serif-sc.woff2').stat().st_size / 1024:.0f} KiB")


if __name__ == "__main__":
    main(sys.argv[1])
