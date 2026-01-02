import os
import markdown
import yaml
from datetime import datetime, date as date_type
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_DIR = ROOT / "assets" / "articles" / "markdown"
HTML_DIR = ROOT / "assets" / "articles" / "html"
TEMPLATE_FILE = ROOT / "assets" / "templates" / "article_template.html"
ENTRY_TEMPLATE_FILE = ROOT / "assets" / "templates" / "entry_template.html"
WRITING_FILE = ROOT / "writing.html"

MARKDOWN_EXT = markdown.Markdown(extensions=['fenced_code', 'tables'])

# -------------------------------------------------------
# Helper Functions
# -------------------------------------------------------

def parse_front_matter(md_text):
    """Extract YAML front matter and return dict + markdown body."""
    if md_text.startswith("---"):
        _, front, body = md_text.split("---", 2)
        meta = yaml.safe_load(front.strip())
        return meta, body.strip()
    raise ValueError("Markdown file missing YAML front matter section")


def format_date(date_input):
    """Convert YAML date into '13 Nov. 2025' format."""
    if isinstance(date_input, date_type):  # already a datetime.date object
        dt = datetime.combine(date_input, datetime.min.time())
    else:
        dt = datetime.strptime(date_input, "%Y-%m-%d")
    return dt.strftime("%d %b. %Y")


def build_html_from_md(md_path):
    """Convert a markdown file into a full HTML article using template."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    meta, body = parse_front_matter(text)

    title = meta.get("title")
    date = format_date(meta.get("date"))
    tags = meta.get("tags", [])

    html_content = MARKDOWN_EXT.convert(body)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as temp:
        template = temp.read()

    article_html = template.replace("{{title}}", title) \
                           .replace("{{date}}", date) \
                           .replace("{{content}}", html_content)

    filename = md_path.stem + ".html"
    output_path = HTML_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(article_html)

    return {
        "title": title,
        "date": date,
        "tags": tags,
        "filename": f"assets/articles/html/{filename}"
    }


def build_entry(entry):
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


    return tpl.replace("{{date}}", entry["date"]) \
              .replace("{{link}}", entry["filename"]) \
              .replace("{{title}}", entry["title"]) \
              .replace("{{tags}}", tag_str)


def update_writing(entries):
    """Insert generated entries into writing.html between <!-- AUTO --> markers."""
    with open(WRITING_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    start = "<!-- AUTO:START -->"
    end = "<!-- AUTO:END -->"

    before = html.split(start)[0] + start
    after = end + html.split(end)[1]

    mid = "\n".join(entries)

    new_html = before + "\n" + mid + "\n" + after

    with open(WRITING_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)


# -------------------------------------------------------
# Main
# -------------------------------------------------------
def main():
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    entries = []

    for md_file in sorted(MD_DIR.glob("*.md")):
        info = build_html_from_md(md_file)
        entries.append(info)

    # sort newest → oldest
    entries = sorted(entries, key=lambda x: x["date"], reverse=True)

    entry_blocks = [build_entry(e) for e in entries]
    update_writing(entry_blocks)

    print("✔ Build complete!")


if __name__ == "__main__":
    main()
