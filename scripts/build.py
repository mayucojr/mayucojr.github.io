import markdown
import yaml
import re
from datetime import datetime, date as date_type
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
# Helpers
# -------------------------------------------------------
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


def parse_front_matter(md_text: str):
    """Extract YAML front matter and return dict + markdown body."""
    if md_text.startswith("---"):
        _, front, body = md_text.split("---", 2)
        meta = yaml.safe_load(front.strip()) or {}
        return meta, body.strip()
    raise ValueError("Markdown file missing YAML front matter section")


def coerce_date(date_input):
    """Convert YAML date/date-like into a datetime for sorting."""
    if date_input is None:
        return None
    if isinstance(date_input, datetime):
        return date_input
    if isinstance(date_input, date_type):
        return datetime.combine(date_input, datetime.min.time())
    # expected string "YYYY-MM-DD"
    return datetime.strptime(str(date_input), "%Y-%m-%d")


def format_date(dt: datetime):
    """Format datetime into '13 Nov. 2025'."""
    return dt.strftime("%d %b. %Y")


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
    if not tags:
        return ""
    out = []
    for tag in tags:
        if isinstance(tag, dict):
            text = tag.get("text", "").strip()
            href = tag.get("href", "#")
            if text:
                out.append(f'<a href="{href}" target="_blank">{text}</a>')
        else:
            # string tag fallback
            out.append(f'<a href="#">{tag}</a>')
    return "\n".join(out) + ("\n" if out else "")


def safe_img(src: str):
    """Return an <img> tag if src exists, else an empty placeholder div."""
    src = (src or "").strip()
    if src:
        return f'<img src="{src}" alt="" loading="lazy" />'
    return '<div class="curation-img placeholder"></div>'


# -------------------------------------------------------
# Writing pipeline (kept consistent with your previous setup)
# -------------------------------------------------------
def build_writing_html_from_md(md_path: Path):
    """Convert a writing markdown file into a full HTML article using template."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    meta, body = parse_front_matter(text)

    title = meta.get("title", md_path.stem)
    dt = coerce_date(meta.get("date"))
    if dt is None:
        raise ValueError(f"{md_path.name} missing required front matter field: date")
    date_str = format_date(dt)
    tags = meta.get("tags", [])

    html_content = add_image_captions(MARKDOWN_EXT.convert(body))

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

    tag_str = ""
    for tag in entry["tags"]:
        if isinstance(tag, dict):
            text = tag.get("text", "")
            href = tag.get("href", "#")
            tag_str += f'<a href="{href}" target="_blank">{text}</a>\n'
        else:
            tag_str += f'<a href="#">{tag}</a>\n'

    return (
        tpl.replace("{{date}}", entry["date_str"])
        .replace("{{link}}", entry["filename"])
        .replace("{{title}}", entry["title"])
        .replace("{{tags}}", tag_str)
    )


def build_writing():
    WRITING_HTML_DIR.mkdir(parents=True, exist_ok=True)
    entries = []

    for md_file in sorted(WRITING_MD_DIR.glob("*.md")):
        info = build_writing_html_from_md(md_file)
        entries.append(info)

    # newest → oldest by date
    entries = sorted(entries, key=lambda x: x["date_dt"], reverse=True)

    entry_blocks = [build_writing_entry(e) for e in entries]
    update_index(WRITING_FILE, entry_blocks)


# -------------------------------------------------------
# Curation pipeline (different layout + date range + images)
# -------------------------------------------------------
def build_curation_html_from_md(md_path: Path):
    """
    Convert a curation markdown file into a full HTML page.
    Uses the same article_template.html, but injects an image row + date range.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    meta, body = parse_front_matter(text)

    title = meta.get("title", md_path.stem)

    start_dt = coerce_date(meta.get("start-date"))
    if start_dt is None:
        raise ValueError(f"{md_path.name} missing required front matter field: start-date")
    end_dt = coerce_date(meta.get("end-date"))  # optional

    start_str = format_date(start_dt)
    end_str = format_date(end_dt) if end_dt else ""

    tags = meta.get("tags", [])

    img_l = meta.get("image-left", "")
    img_m = meta.get("image-middle", "")
    img_r = meta.get("image-right", "")

    # Build a small header block for the curation detail page
    date_line = start_str if not end_str else f"{start_str} — {end_str}"
    images_html = f"""
<div class="curation-detail">
  <div class="curation-detail-images">
  </div>
</div>
""".strip()

    html_content = images_html + "\n" + add_image_captions(MARKDOWN_EXT.convert(body))


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
        "img_l": (img_l or "").strip(),
        "img_m": (img_m or "").strip(),
        "img_r": (img_r or "").strip(),
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

    img_l = f'<img src="{entry["img_l"]}" alt="" loading="lazy" />' if entry["img_l"] else '<div class="curation-img placeholder"></div>'
    img_m = f'<img src="{entry["img_m"]}" alt="" loading="lazy" />' if entry["img_m"] else '<div class="curation-img placeholder"></div>'
    img_r = f'<img src="{entry["img_r"]}" alt="" loading="lazy" />' if entry["img_r"] else '<div class="curation-img placeholder"></div>'

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
    entries = []

    for md_file in sorted(CURATION_MD_DIR.glob("*.md")):
        info = build_curation_html_from_md(md_file)
        entries.append(info)

    # newest → oldest by start-date
    entries = sorted(entries, key=lambda x: x["start_dt"], reverse=True)

    entry_blocks = [build_curation_entry(e) for e in entries]
    update_index(CURATION_FILE, entry_blocks)


# -------------------------------------------------------
# Main
# -------------------------------------------------------
def main():
    build_writing()
    build_curation()
    print("Build complete.")


if __name__ == "__main__":
    main()
