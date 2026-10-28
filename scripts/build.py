"""
Builds the website pages from the markdown files.

    python3 scripts/build.py

On the live site this runs automatically (GitHub Actions) every time something
is saved in the Pages CMS, so you normally never run it by hand.

If one entry has a problem, it is skipped with a plain-English warning and the
rest of the site still builds.
"""
import html as html_lib
import os
import re
import sys
from datetime import datetime, date as date_type
from pathlib import Path
from urllib.parse import quote

import markdown
import yaml

ROOT = Path(__file__).resolve().parents[1]

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".ogg"}

# -----------------------------
# Templates (writing)
# -----------------------------
ARTICLE_TEMPLATE_FILE = ROOT / "assets" / "templates" / "article_template.html"
ENTRY_TEMPLATE_FILE = ROOT / "assets" / "templates" / "entry_template.html"

MARKDOWN_EXT = markdown.Markdown(extensions=["fenced_code", "tables"])

# -----------------------------
# Paths
# -----------------------------
# Writing (articles)
WRITING_MD_DIR = ROOT / "assets" / "articles" / "markdown"
WRITING_HTML_DIR = ROOT / "assets" / "articles" / "html"
WRITING_FILE = ROOT / "writing.html"
WRITING_LINK_PREFIX = "assets/articles/html"

# Curation
CURATION_MD_DIR = ROOT / "assets" / "curation" / "markdown"
CURATION_HTML_DIR = ROOT / "assets" / "curation" / "html"
CURATION_FILE = ROOT / "curation.html"
CURATION_LINK_PREFIX = "assets/curation/html"


# -------------------------------------------------------
# Problems with a single entry
# -------------------------------------------------------
class EntryError(Exception):
    """Something is wrong with one entry. The message is written for a non-programmer."""


SKIPPED = []  # (file, message) for every entry that could not be built


def warn(md_path: Path, message: str):
    """Report a skipped entry. On GitHub this shows up as a yellow warning on the run."""
    rel = md_path.relative_to(ROOT).as_posix()
    SKIPPED.append((rel, message))
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::warning file={rel}::Skipped. {message}")
    else:
        print(f"WARNING: {rel} was skipped. {message}")


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def esc(text) -> str:
    """Make text safe to put inside HTML (so a title with & or < can't break the page)."""
    return html_lib.escape(str(text), quote=False)


def add_image_captions(html: str) -> str:
    """
    Wrap markdown-generated <p><img ...></p> blocks in <figure> with a <figcaption>
    using the <img> alt text as the caption.

    Notes:
    - Only targets images that appear alone inside a <p>...</p> block.
    - Leaves inline images (images mixed with text) alone.
    """
    img_re = re.compile(
        r'<p>\s*(<img[^>]*alt="([^"]+)"[^>]*>)\s*</p>',
        flags=re.IGNORECASE
    )

    def repl(m):
        img_tag = m.group(1)
        caption = m.group(2).strip()
        # If you ever want to allow "no caption", set alt="" in markdown
        if not caption:
            return f'<figure class="md-figure">{img_tag}</figure>'
        return f'<figure class="md-figure">{img_tag}<figcaption>{caption}</figcaption></figure>'

    return img_re.sub(repl, html)


def process_video_embeds(html: str) -> str:
    """
    Convert standalone <p><img src="file.mp4" alt="caption"></p> blocks into
    <figure class="md-video"><video ...></video><figcaption>...</figcaption></figure>.

    Orientation class (portrait / landscape) is applied at runtime by video.js.

    Usage in markdown — same syntax as images, just point at a video file:
        ![Optional caption](assets/videos/clip.mp4)
    """
    img_p_re = re.compile(r"<p>\s*(<img\b[^>]*>)\s*</p>", re.IGNORECASE)
    src_re   = re.compile(r'\bsrc="([^"]+)"', re.IGNORECASE)
    alt_re   = re.compile(r'\balt="([^"]*)"', re.IGNORECASE)

    def repl(m):
        img_tag   = m.group(1)
        src_match = src_re.search(img_tag)
        if not src_match:
            return m.group(0)
        src = src_match.group(1).strip()
        if Path(src).suffix.lower() not in VIDEO_EXTENSIONS:
            return m.group(0)   # regular image — leave for add_image_captions
        alt_match = alt_re.search(img_tag)
        caption   = alt_match.group(1).strip() if alt_match else ""
        cap_html  = f"\n  <figcaption>{caption}</figcaption>" if caption else ""
        return (
            f'<figure class="md-video">\n'
            f'  <video src="{src}" autoplay muted loop playsinline preload="metadata" controls>\n'
            f'    Your browser does not support the video tag.\n'
            f'  </video>{cap_html}\n'
            f'</figure>'
        )

    return img_p_re.sub(repl, html)


FRONT_MATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(.*)\Z", re.DOTALL
)


def parse_front_matter(md_text: str):
    """Extract YAML front matter (the details between the two --- lines) and the body."""
    match = FRONT_MATTER_RE.match(md_text.lstrip("﻿"))
    if not match:
        raise EntryError(
            "The file must begin with a line of three dashes (---), then the details "
            "(title, date...), then another line of three dashes."
        )
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        raise EntryError(
            "The details at the top of the file could not be read. A common cause is a "
            "title containing a colon (:) or a quote mark that is not wrapped in quotes."
        )
    if not isinstance(meta, dict):
        raise EntryError("The details at the top of the file are not in the expected format.")
    return meta, match.group(2).strip()


def coerce_date(date_input, field="date"):
    """
    Convert a date from the front matter into a datetime for sorting.
    Returns None when the date is blank. Accepts 2026-09-05, 2026-09-05T10:30, or a YAML date.
    """
    if date_input is None:
        return None
    if isinstance(date_input, str) and not date_input.strip():
        return None
    if isinstance(date_input, datetime):
        return date_input.replace(tzinfo=None)
    if isinstance(date_input, date_type):
        return datetime.combine(date_input, datetime.min.time())
    try:
        return datetime.strptime(str(date_input).strip()[:10], "%Y-%m-%d")
    except ValueError:
        raise EntryError(
            f'The {field} is "{date_input}", but it must look like 2026-09-05 (year-month-day).'
        )


def required_date(meta: dict, field: str):
    dt = coerce_date(meta.get(field), field)
    if dt is None:
        raise EntryError(f"The {field} is empty. Every entry needs a {field}.")
    return dt


def format_date(dt: datetime):
    """Format datetime into '13 Nov. 2025'."""
    return dt.strftime("%d %b. %Y")


def asset_url(path) -> str:
    """
    Turn an image path from an entry into one that works from any page.
    '../assets/images/x.jpg', 'assets/images/x.jpg' and '/assets/images/x.jpg' all
    become '/assets/images/x.jpg'. Full web addresses are left alone.
    """
    p = str(path or "").strip()
    if not p:
        return ""
    if re.match(r"^[a-z][a-z0-9+.-]*:", p, re.IGNORECASE) or p.startswith("//"):
        return p
    while p.startswith("./") or p.startswith("../"):
        p = p[2:] if p.startswith("./") else p[3:]
    if not p.startswith("/"):
        p = "/" + p
    return quote(p, safe="/%:@!$&'()*+,;=-._~")


def get_title(meta: dict, md_path: Path) -> str:
    return esc(str(meta.get("title") or md_path.stem).strip())


def get_tags(meta: dict):
    tags = meta.get("tags")
    if tags is None:
        return []
    if isinstance(tags, (str, dict)):
        return [tags]
    return list(tags)


def update_index(index_file: Path, entry_blocks):
    """Insert generated entries into index file between AUTO markers."""
    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()

    start = "<!-- AUTO:START -->"
    end = "<!-- AUTO:END -->"

    if start not in html or end not in html:
        raise ValueError(
            f"{index_file} missing AUTO markers. "
            f"Expected to find '{start}' and '{end}'."
        )

    before = html.split(start)[0] + start
    after = end + html.split(end)[1]

    mid = "\n".join(entry_blocks)
    new_html = before + "\n" + mid + "\n" + after

    with open(index_file, "w", encoding="utf-8") as f:
        f.write(new_html)


def render_tag_links(tags):
    """Render tags as link list. Supports string tags or {text, href} dict tags."""
    out = []
    for tag in tags or []:
        if isinstance(tag, dict):
            text = str(tag.get("text") or "").strip()
            href = str(tag.get("href") or "").strip() or "#"
            if text:
                out.append(f'<a href="{html_lib.escape(href)}" target="_blank">{esc(text)}</a>')
        else:
            text = str(tag or "").strip()
            if text:
                out.append(f'<a href="#">{esc(text)}</a>')
    return "\n".join(out) + ("\n" if out else "")


def safe_img(src: str):
    """Return an <img> tag if src exists, else an empty placeholder div."""
    src = (src or "").strip()
    if src:
        return f'<img src="{src}" alt="" loading="lazy" />'
    return '<div class="curation-img placeholder"></div>'


def read_entry(md_path: Path):
    try:
        text = md_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise EntryError("The file is not saved as plain text (UTF-8).")
    return parse_front_matter(text)


def build_all(md_dir: Path, builder):
    """Run `builder` on every .md file. A broken entry is skipped, not fatal."""
    entries = []
    md_files = sorted(md_dir.glob("*.md"))
    for md_file in md_files:
        try:
            entries.append(builder(md_file))
        except EntryError as e:
            warn(md_file, str(e))
        except Exception as e:  # never let one entry take down the whole site
            warn(md_file, f"Unexpected problem ({type(e).__name__}: {e}).")
    if md_files and not entries:
        # Every entry failed: that's a bug in the build, not a typo. Don't publish an empty list.
        raise SystemExit(f"Build stopped: none of the {len(md_files)} files in {md_dir} could be built.")
    return entries


# -------------------------------------------------------
# Writing pipeline (kept consistent with your previous setup)
# -------------------------------------------------------
def build_writing_html_from_md(md_path: Path):
    """Convert a writing markdown file into a full HTML article using template."""
    meta, body = read_entry(md_path)

    title = get_title(meta, md_path)
    dt = required_date(meta, "date")
    date_str = format_date(dt)
    tags = get_tags(meta)

    html_content = add_image_captions(process_video_embeds(MARKDOWN_EXT.convert(body)))
    MARKDOWN_EXT.reset()

    with open(ARTICLE_TEMPLATE_FILE, "r", encoding="utf-8") as temp:
        template = temp.read()

    article_html = (
        template.replace("{{title}}", title)
        .replace("{{date}}", date_str)
        .replace("{{content}}", html_content)
    )

    WRITING_HTML_DIR.mkdir(parents=True, exist_ok=True)
    filename = md_path.stem + ".html"
    output_path = WRITING_HTML_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(article_html)

    return {
        "title": title,
        "date_dt": dt,
        "date_str": date_str,
        "tags": tags,
        "filename": f"{WRITING_LINK_PREFIX}/{filename}",
    }


def build_writing_entry(entry: dict):
    """Generate the <div class='entry'> block for writing.html list."""
    with open(ENTRY_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        tpl = f.read()

    return (
        tpl.replace("{{date}}", entry["date_str"])
        .replace("{{link}}", entry["filename"])
        .replace("{{title}}", entry["title"])
        .replace("{{tags}}", render_tag_links(entry["tags"]))
    )


def build_writing():
    WRITING_HTML_DIR.mkdir(parents=True, exist_ok=True)
    entries = build_all(WRITING_MD_DIR, build_writing_html_from_md)

    # newest → oldest by date
    entries = sorted(entries, key=lambda x: x["date_dt"], reverse=True)

    entry_blocks = [build_writing_entry(e) for e in entries]
    update_index(WRITING_FILE, entry_blocks)
    return len(entries)


# -------------------------------------------------------
# Curation pipeline (different layout + date range + images)
# -------------------------------------------------------
def build_curation_html_from_md(md_path: Path):
    """
    Convert a curation markdown file into a full HTML page.
    Uses the same article_template.html, but injects an image row + date range.
    """
    meta, body = read_entry(md_path)

    title = get_title(meta, md_path)

    start_dt = required_date(meta, "start-date")
    end_dt = coerce_date(meta.get("end-date"), "end-date")  # optional

    start_str = format_date(start_dt)
    end_str = format_date(end_dt) if end_dt else ""

    tags = get_tags(meta)

    img_l = asset_url(meta.get("image-left"))
    img_m = asset_url(meta.get("image-middle"))
    img_r = asset_url(meta.get("image-right"))

    # Build a small header block for the curation detail page
    date_line = start_str if not end_str else f"{start_str} — {end_str}"
    images_html = f"""
<div class="curation-detail">
  <div class="curation-detail-images">
  </div>
</div>
""".strip()

    html_content = images_html + "\n" + add_image_captions(process_video_embeds(MARKDOWN_EXT.convert(body)))
    MARKDOWN_EXT.reset()

    with open(ARTICLE_TEMPLATE_FILE, "r", encoding="utf-8") as temp:
        template = temp.read()

    # Reuse template slots: title + date + content
    page_html = (
        template.replace("{{title}}", title)
        .replace("{{date}}", date_line)
        .replace("{{content}}", html_content)
    )

    CURATION_HTML_DIR.mkdir(parents=True, exist_ok=True)
    filename = md_path.stem + ".html"
    output_path = CURATION_HTML_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page_html)

    return {
        "title": title,
        "start_dt": start_dt,
        "end_dt": end_dt,
        "start_str": start_str,
        "end_str": end_str,
        "tags": tags,
        "img_l": img_l,
        "img_m": img_m,
        "img_r": img_r,
        "filename": f"{CURATION_LINK_PREFIX}/{filename}",
    }


def build_curation_entry(entry: dict):
    """
    Build a curation list item:
    left: start/end dates + centered dash
    right: 3 square images + title link + tag links
    """
    bottom_date = entry["end_str"] if entry["end_str"] else entry["start_str"]
    tags_html = render_tag_links(entry["tags"])

    img_l = safe_img(entry["img_l"])
    img_m = safe_img(entry["img_m"])
    img_r = safe_img(entry["img_r"])

    return f"""
<div class="curation-entry">
  <div class="curation-dates">
    <div class="curation-date-top">{entry["start_str"]}</div>
    <div class="curation-sep" aria-hidden="true">—</div>
    <div class="curation-date-bottom">{bottom_date}</div>
  </div>

  <div class="curation-main">
    <div class="curation-images">
      {img_l}
      {img_m}
      {img_r}
    </div>

    <div class="curation-text">
      <a class="curation-title" href="{entry["filename"]}" target="_blank">{entry["title"]}</a>
      <div class="meta">
        {tags_html}
      </div>
    </div>
  </div>
</div>
""".strip()



def build_curation():
    CURATION_HTML_DIR.mkdir(parents=True, exist_ok=True)
    entries = build_all(CURATION_MD_DIR, build_curation_html_from_md)

    # newest → oldest by start-date
    entries = sorted(entries, key=lambda x: x["start_dt"], reverse=True)

    entry_blocks = [build_curation_entry(e) for e in entries]
    update_index(CURATION_FILE, entry_blocks)
    return len(entries)


# -------------------------------------------------------
# Main
# -------------------------------------------------------
def main():
    # Shrink/convert any new photos first (and fix their links) so pages load fast
    try:
        import optimize_images
        optimize_images.main()
    except ImportError:
        print("Skipping image optimizer (scripts/optimize_images.py not found).")
    except Exception as e:  # a photo problem should never stop the site from publishing
        print(f"WARNING: image optimizer failed ({type(e).__name__}: {e}); continuing.")
    n_writing = build_writing()
    n_curation = build_curation()
    print(f"Build complete: {n_writing} writing entries, {n_curation} curation entries.")
    if SKIPPED:
        print(f"{len(SKIPPED)} entr{'y was' if len(SKIPPED) == 1 else 'ies were'} skipped:")
        for rel, message in SKIPPED:
            print(f"  - {rel}: {message}")
        if "--strict" in sys.argv:
            sys.exit(1)


if __name__ == "__main__":
    main()
