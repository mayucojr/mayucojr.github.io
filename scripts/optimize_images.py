"""
Shrinks and fixes the images in assets/images so the website loads fast.

You normally never run this by hand: `python3 scripts/build.py` runs it first.

What it does, for every picture in assets/images:
  * iPhone photos (.heic) are converted to .jpg (Chrome can't show .heic).
  * Anything bigger than 1600 pixels on its longest side is shrunk to 1600.
  * Very heavy photos/screenshots are re-saved at a smaller file size.
  * Big .png files with no transparency become .jpg (much smaller).
  * Any link to a renamed file (in the .md files and the .html pages) is
    updated automatically.

It is safe to run again and again: files that are already small are skipped.

One-time setup (per computer):   pip3 install pillow pillow-heif
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

try:
    from PIL import Image, ImageOps
except ImportError:  # handled in main()
    Image = None

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_OK = True
except Exception:
    HEIF_OK = False

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "assets" / "images"

MAX_EDGE = 1600            # longest side, in pixels
JPEG_QUALITY = 82
PNG_TO_JPEG_QUALITY = 85
BIG_JPEG_BYTES = 1_500_000  # re-save JPEGs heavier than this
BIG_PNG_BYTES = 400_000     # turn PNGs heavier than this into JPEGs

HEIC_EXTS = {".heic", ".heif"}
JPEG_EXTS = {".jpg", ".jpeg"}

# Files whose links may need updating if an image is renamed
def _reference_files():
    files = []
    files += (ROOT / "assets" / "articles" / "markdown").glob("*.md")
    files += (ROOT / "assets" / "curation" / "markdown").glob("*.md")
    files += ROOT.glob("*.html")
    files += (ROOT / "assets" / "templates").glob("*.html")
    return files


def _unique(path: Path) -> Path:
    """Return path, or path with -2, -3... added if something is already there."""
    if not path.exists():
        return path
    n = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def _open(path: Path):
    """Open an image, upright. Falls back to macOS `sips` for .heic if needed."""
    if path.suffix.lower() in HEIC_EXTS and not HEIF_OK:
        if not shutil.which("sips"):
            raise RuntimeError("can't read .heic (run: pip3 install pillow-heif)")
        tmp = Path(tempfile.mkdtemp()) / "x.jpg"
        subprocess.run(["sips", "-s", "format", "jpeg", str(path), "--out", str(tmp)],
                       check=True, capture_output=True)
        img = Image.open(tmp)
        img.load()
    else:
        img = Image.open(path)
        img.load()
    return ImageOps.exif_transpose(img)  # fixes sideways phone photos


def _has_alpha(img) -> bool:
    if img.mode in ("RGBA", "LA"):
        return img.getchannel("A").getextrema()[0] < 255
    return "transparency" in img.info


def _shrink(img):
    if max(img.size) > MAX_EDGE:
        img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    return img


def _save(img, dest: Path, fmt: str, **opts):
    tmp = dest.with_name(dest.name + ".tmp")
    img.save(tmp, format=fmt, **opts)
    tmp.replace(dest)


def _save_jpeg(img, dest: Path, quality: int):
    if img.mode != "RGB":
        if _has_alpha(img):  # flatten transparency onto white
            bg = Image.new("RGB", img.size, "white")
            bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").getchannel("A"))
            img = bg
        else:
            img = img.convert("RGB")
    _save(img, dest, "JPEG", quality=quality, optimize=True, progressive=True)


def process(path: Path):
    """Optimize one file. Returns the new path if it was renamed, else None."""
    ext = path.suffix.lower()
    size = path.stat().st_size

    if ext in HEIC_EXTS:
        img = _shrink(_open(path))
        dest = _unique(path.with_suffix(".jpg"))
        _save_jpeg(img, dest, JPEG_QUALITY)
        path.unlink()
        return dest

    if ext in JPEG_EXTS:
        img = _open(path)
        if max(img.size) <= MAX_EDGE and size <= BIG_JPEG_BYTES:
            return None
        _save_jpeg(_shrink(img), path, JPEG_QUALITY)
        return None

    if ext == ".png":
        img = _open(path)
        if _has_alpha(img):  # keep transparency, just shrink if huge
            if max(img.size) > MAX_EDGE:
                _save(_shrink(img), path, "PNG", optimize=True)
            return None
        if size <= BIG_PNG_BYTES and max(img.size) <= MAX_EDGE:
            return None
        dest = _unique(path.with_suffix(".jpg"))
        _save_jpeg(_shrink(img), dest, PNG_TO_JPEG_QUALITY)
        path.unlink()
        return dest

    return None  # gif, svg, webp, videos...: leave alone


def _tolerant(name: str) -> str:
    """Regex matching a filename whether spaces are written as ' ' or '%20'."""
    space = r"(?:\s|%20|%E2%80%AF)"  # macOS screenshots use a special space before AM/PM
    return "".join(space if ch.isspace() else re.escape(ch) for ch in name)


def update_references(renames: dict):
    """Point links at the new filenames (works with spaces or %20 in the old link)."""
    for ref_file in _reference_files():
        text = ref_file.read_text(encoding="utf-8")
        new_text = text
        for old, new in renames.items():
            pattern = re.escape(old.parent.name + "/") + _tolerant(old.name)
            replacement = new.parent.name + "/" + quote(new.name)
            new_text = re.sub(pattern, lambda m: replacement, new_text)
        if new_text != text:
            ref_file.write_text(new_text, encoding="utf-8")
            print(f"  updated links in {ref_file.relative_to(ROOT)}")


def main():
    if Image is None:
        print("Image optimizer skipped: Pillow isn't installed.\n"
              "  Run once:  pip3 install pillow pillow-heif")
        return
    if not IMAGES_DIR.exists():
        return

    before = sum(p.stat().st_size for p in IMAGES_DIR.rglob("*") if p.is_file())
    files = [p for p in IMAGES_DIR.rglob("*")
             if p.is_file() and not p.name.startswith(".")]
    # .heic first, so converted names are settled before .png -> .jpg conversions
    files.sort(key=lambda p: (p.suffix.lower() not in HEIC_EXTS, str(p)))

    renames = {}
    for path in files:
        try:
            new = process(path)
        except Exception as e:  # never block the build over one bad image
            print(f"  could not optimize {path.relative_to(ROOT)}: {e}")
            continue
        if new is not None:
            renames[path] = new
            print(f"  converted {path.relative_to(ROOT)} -> {new.name}")

    if renames:
        update_references(renames)

    after = sum(p.stat().st_size for p in IMAGES_DIR.rglob("*") if p.is_file())
    if before != after:
        print(f"Images optimized: {before/1e6:.0f} MB -> {after/1e6:.0f} MB")


if __name__ == "__main__":
    main()
