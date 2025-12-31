import re
import json
import datetime
from pathlib import Path

import pandas as pd
import markdown as md_lib

# ==============================
# CONFIG
# ==============================

EXCEL_PATH = r"C:\Users\nlal\Downloads\AL Website\blogs\blog_index.xlsx"

# UPDATED per your note:
# Posts and images live here:
OBSIDIAN_ROOT = r"C:\Users\nlal\Downloads\AL Website\blogs\blog_posts\Blog Posts"

# Individual post HTML output:
POST_OUTPUT_DIR = r"C:\Users\nlal\Downloads\AL Website\blogs\generated"

# Tag pages output:
TAG_OUTPUT_DIR = r"C:\Users\nlal\Downloads\AL Website\blogs\tags"

# Main blog page output (site root):
BLOG_INDEX_OUTPUT = r"C:\Users\nlal\Downloads\AL Website\blog.html"

# From blogs/generated/<slug>.html -> site root is two levels up
REL_TO_SITE_ROOT_FROM_POST = "../.."

ACCENT_RED = "#bb271a"
HEADER_GRAY = "#f5f5f5"
AUTHOR_NAME = "Anand Lal M.D."

DISCLAIMER_TEXT = (
    "This content is not intended to be as medical advice. "
    "Please address any medical questions or concerns with your clinician."
)

# ==============================
# Helpers
# ==============================

def yn_to_bool(x) -> bool:
    if x is None:
        return False
    return str(x).strip().upper() == "Y"

def safe_slug(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-zA-Z0-9\-_]", "", s)
    return s.lower()

def safe_tag_slug(tag: str) -> str:
    # tag -> url-friendly: "Artificial Intelligence" -> "artificial-intelligence"
    tag = prettify_tag(tag)
    tag = tag.lower()
    tag = re.sub(r"\s+", "-", tag)
    tag = re.sub(r"[^a-z0-9\-]", "", tag)
    return tag

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def find_markdown_file(folder_path: Path, file_base: str) -> Path | None:
    if not folder_path.exists() or not folder_path.is_dir():
        return None

    exact = folder_path / f"{file_base}.md"
    if exact.exists():
        return exact

    for c in folder_path.glob("*.md"):
        if c.stem.lower() == str(file_base).lower():
            return c

    candidates = list(folder_path.glob("*.md"))
    return candidates[0] if candidates else None

# ==============================
# Obsidian Properties (frontmatter)
# ==============================

def parse_obsidian_properties(md_text: str) -> dict:
    """
    Reads YAML frontmatter:
    ---
    tags:
      - Artificial_Intelligence
      - Case_Report
    date: 2025-11-30
    tagline: This is my tagline...
    ---
    """
    props = {}
    m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n", md_text, flags=re.S)
    if not m:
        return props

    fm = m.group(1)

    # tags inline: tags: [a, b]
    tags_inline = re.search(r"(?m)^\s*tags\s*:\s*\[(.*?)\]\s*$", fm)
    if tags_inline:
        raw = tags_inline.group(1)
        tags = [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]
        props["tags"] = tags

    # tags block
    tags_block = re.search(r"(?ms)^\s*tags\s*:\s*\n((?:\s*-\s*.*\n)+)", fm)
    if tags_block:
        lines = tags_block.group(1).splitlines()
        tags = []
        for line in lines:
            mm = re.match(r"^\s*-\s*(.+)\s*$", line)
            if mm:
                tags.append(mm.group(1).strip().strip("'\""))
        props["tags"] = tags

    # date:
    date_m = re.search(r"(?m)^\s*date\s*:\s*(.+)\s*$", fm)
    if date_m:
        props["date"] = date_m.group(1).strip().strip("'\"")

    # tagline:  (case-insensitive match for convenience)
    tagl_m = re.search(r"(?mi)^\s*tagline\s*:\s*(.+)\s*$", fm)
    if tagl_m:
        props["tagline"] = tagl_m.group(1).strip().strip("'\"")

    return props

def strip_frontmatter(md_text: str) -> str:
    return re.sub(r"^\s*---\s*\n.*?\n---\s*\n", "", md_text, flags=re.S)

def prettify_tag(tag: str) -> str:
    # Convert underscores to spaces (per your request)
    return str(tag).strip().replace("_", " ")

# ==============================
# Images: NO COPYING, link in-place
# ==============================

WIKILINK_IMAGE_RE = re.compile(r"!\[\[(.+?)\]\]")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

def obsidian_md_to_web_md(markdown_text: str, folder_name: str) -> str:
    """
    For post pages in blogs/generated/<slug>.html, images live at:
      ../blog_posts/Blog Posts/<folder_name>/<image_file>
    """
    base_prefix = f"../blog_posts/Blog Posts/{folder_name}/"

    def repl_wikilink(m):
        target = m.group(1).strip()
        target_file = target.split("|")[0].strip()
        return f"![Image]({base_prefix}{target_file})"

    markdown_text = WIKILINK_IMAGE_RE.sub(repl_wikilink, markdown_text)

    def repl_md_img(m):
        alt = m.group(1)
        src = m.group(2).strip()

        if re.match(r"^https?://", src, flags=re.I):
            return m.group(0)

        src_clean = src.strip("\"'")

        if src_clean.startswith("../blog_posts/Blog Posts/"):
            return f"![{alt}]({src_clean})"

        return f"![{alt}]({base_prefix}{src_clean})"

    return MARKDOWN_IMAGE_RE.sub(repl_md_img, markdown_text)

def extract_first_image_src(raw_md: str, folder_name: str, from_where: str) -> str | None:
    """
    Returns a *relative src* to the first image in the post, depending on where we are linking FROM.

    - from_where="site_root": from blog.html (at site root)
        => "blogs/blog_posts/Blog Posts/<folder>/<image>"
    - from_where="tag_page": from blogs/tags/<tag>.html
        => "../blog_posts/Blog Posts/<folder>/<image>"
    - from_where="post_page": from blogs/generated/<slug>.html
        => "../blog_posts/Blog Posts/<folder>/<image>"
    """
    # Find first Obsidian wikilink image
    m = WIKILINK_IMAGE_RE.search(raw_md)
    if m:
        target = m.group(1).strip().split("|")[0].strip()
        img_file = target
    else:
        # Find first markdown image
        m2 = MARKDOWN_IMAGE_RE.search(raw_md)
        if not m2:
            return None
        src = m2.group(2).strip().strip("\"'")
        if re.match(r"^https?://", src, flags=re.I):
            return src
        img_file = src  # treat as local filename in the folder

    if from_where == "site_root":
        return f"blogs/blog_posts/Blog Posts/{folder_name}/{img_file}"
    if from_where in ("tag_page", "post_page"):
        return f"../blog_posts/Blog Posts/{folder_name}/{img_file}"

    return None

def markdown_to_html(markdown_text: str) -> str:
    return md_lib.markdown(
        markdown_text,
        extensions=["extra", "tables", "toc", "fenced_code", "sane_lists", "smarty"],
        output_format="html5",
    )

# ==============================
# POST PAGE TEMPLATE
# ==============================

def make_post_header_block(tags: list[str], title: str, date_str: str | None) -> str:
    tags_html = "; ".join(prettify_tag(t) for t in tags) if tags else ""
    date_html = f'<div class="post-date">{date_str}</div>' if date_str else ""

    author_html = (
        f'By <a class="author-link" href="{REL_TO_SITE_ROOT_FROM_POST}/about.html">{AUTHOR_NAME}</a>'
    )

    return f"""
<section class="post-hero">
  <div class="post-hero-inner">
    <div class="post-tags">{tags_html}</div>
    <h1 class="post-title">{title}</h1>
    {date_html}
    <div class="post-author">{author_html}</div>
  </div>
</section>
"""

def wrap_post_page(title: str, header_block_html: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title} | Anand Lal</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap" rel="stylesheet">

  <link rel="stylesheet" href="{REL_TO_SITE_ROOT_FROM_POST}/static/style.css">

  <style>
    .blog-post-wrapper {{
      max-width: 980px;
      margin: 40px auto 90px;
      padding: 0 40px;
    }}

    .post-hero {{
      background: {HEADER_GRAY};
      width: 100%;
      padding: 0;
      margin-top: 120px;
    }}

    .post-hero-inner {{
      max-width: 980px;
      margin: 0 auto;
      padding: 48px 48px 36px;
    }}

    .post-tags {{
      color: {ACCENT_RED};
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      font-size: 18px;
      margin-bottom: 18px;
    }}

    .post-title {{
      margin: 0 0 18px;
      font-size: 64px;
      line-height: 1.05;
      font-weight: 700;
      color: #000;
    }}

    .post-date {{
      font-size: 18px;
      margin-bottom: 18px;
      color: #000;
    }}

    .post-author {{
      font-size: 20px;
      font-weight: 700;
      color: {ACCENT_RED};
    }}

    .author-link {{
      color: {ACCENT_RED};
      text-decoration: none;
      font-weight: 700;
    }}
    .author-link:hover {{
      text-decoration: underline;
    }}

    .post-body {{
      margin-top: 38px;
    }}

    .post-body p {{
      font-size: 18px;
      line-height: 1.85;
      margin: 16px 0;
    }}

    .post-body img {{
      max-width: 100%;
      height: auto;
      border: 2px solid #000;
      background: #e0e0e0;
      margin: 22px 0;
      display: block;
    }}

    .post-disclaimer {{
      margin-top: 48px;
      padding-top: 18px;
      border-top: 1px solid #000;
      font-size: 16px;
      line-height: 1.7;
      color: #000;
    }}

    .back-link {{
      display: inline-block;
      margin-top: 36px;
      font-weight: 700;
      text-decoration: none;
      color: {ACCENT_RED};
    }}
    .back-link:hover {{
      text-decoration: underline;
    }}
  </style>
</head>

<body>

<header class="navbar">
  <div class="navbar-left">
    <a href="{REL_TO_SITE_ROOT_FROM_POST}/index.html" class="logo">
      <img src="{REL_TO_SITE_ROOT_FROM_POST}/Attachments/logo.jpg" alt="Anand Lal Logo">
    </a>
  </div>

  <nav class="navbar-right">
    <a href="{REL_TO_SITE_ROOT_FROM_POST}/index.html">Home</a>
    <a href="{REL_TO_SITE_ROOT_FROM_POST}/about.html">About Me</a>
    <a href="{REL_TO_SITE_ROOT_FROM_POST}/poetry.html">Poetry</a>
    <a href="{REL_TO_SITE_ROOT_FROM_POST}/photos.html">Photos</a>
    <a href="{REL_TO_SITE_ROOT_FROM_POST}/blog.html" class="active">Blog</a>
  </nav>
</header>

<main>
  {header_block_html}

  <div class="blog-post-wrapper">
    <div class="post-body">
      {body_html}

      <div class="post-disclaimer">{DISCLAIMER_TEXT}</div>
    </div>

    <a class="back-link" href="{REL_TO_SITE_ROOT_FROM_POST}/blog.html">← Back to Blog</a>
  </div>
</main>

<footer class="site-footer">
  © 2026 Anand Lal. All rights reserved.
</footer>

</body>
</html>
"""

# ==============================
# BLOG INDEX PAGE (site root blog.html)
# ==============================

def wrap_blog_index_page(featured_posts: list[dict], all_tags: list[str]) -> str:
    # Categories chips
    cat_html = "".join(
        f'<a class="cat-chip" href="blogs/tags/{safe_tag_slug(t)}.html">{prettify_tag(t)}</a>'
        for t in all_tags
    )

    # Featured grid (image + title + date)
    cards = []
    for p in featured_posts:
        img = p.get("hero_image") or ""
        img_html = f'<img src="{img}" alt="{p["title"]}">' if img else ""
        tags = p.get("tags_pretty", [])
        tagline = p.get("tagline") or ""
        tag_label = prettify_tag(tags[0]) if tags else ""
        tag_label_html = f'<div class="card-tag">{tag_label}</div>' if tag_label else ""

        cards.append(f"""
        <article class="feat-card">
          <a class="feat-link" href="{p["url_site_root"]}">
            <div class="feat-img">{img_html}</div>
            <div class="feat-body">
              {tag_label_html}
              <h2 class="feat-title">{p["title"]}</h2>
              <div class="feat-date">{p.get("date","")}</div>
              <div class="feat-tagline">{tagline}</div>
            </div>
          </a>
        </article>
        """)

    cards_html = "\n".join(cards)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Blog | Anand Lal</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap" rel="stylesheet">

  <link rel="stylesheet" href="static/style.css">

  <style>
    .blog-hero {{
      margin-top: 120px; /* below fixed navbar */
      background: #000;
      color: #fff;
      padding: 70px 80px;
    }}
    .blog-hero h1 {{
      margin: 0;
      font-size: 72px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}

    .blog-divider {{
      height: 1px;
      background: #000;
      margin: 0;
    }}

    .blog-cats {{
      background: {HEADER_GRAY};
      padding: 18px 80px 26px;
    }}
    .blog-cats-title {{
      font-weight: 700;
      margin: 10px 0 14px;
      font-size: 18px;
      color: #000;
    }}
    .cat-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
    }}
    .cat-chip {{
      display: inline-block;
      padding: 10px 14px;
      border: 1px solid #000;
      background: #fff;
      color: #000;
      text-decoration: none;
      font-weight: 700;
      border-radius: 999px;
      transition: transform 0.15s ease, color 0.15s ease, border-color 0.15s ease;
    }}
    .cat-chip:hover {{
      color: {ACCENT_RED};
      border-color: {ACCENT_RED};
      transform: translateY(-1px);
    }}

    .featured-wrap {{
      max-width: 1200px;
      margin: 40px auto 90px;
      padding: 0 40px;
    }}

    .featured-title {{
      font-size: 30px;
      font-weight: 700;
      margin: 10px 0 22px;
    }}

    /* Featured cards: clean, editorial */
    .featured-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 28px;
    }}

    .feat-card {{
      border: 1px solid #e0e0e0;
      background: #fff;
    }}

    .feat-link {{
      display: grid;
      grid-template-columns: 240px 1fr;
      gap: 0;
      text-decoration: none;
      color: #000;
      min-height: 170px;
    }}

    .feat-img {{
      background: #e0e0e0;
      border-right: 1px solid #e0e0e0;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .feat-img img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}

    .feat-body {{
      padding: 18px 18px 16px;
    }}

    .card-tag {{
      font-size: 13px;
      font-weight: 700;
      color: {ACCENT_RED};
      text-transform: uppercase;
      letter-spacing: 0.8px;
      margin-bottom: 8px;
    }}

    .feat-title {{
      margin: 0 0 10px;
      font-size: 22px;
      font-weight: 700;
      line-height: 1.25;
    }}

    .feat-date {{
      font-size: 13px;
      color: #333;
      margin-bottom: 10px;
    }}

    .feat-tagline {{
      font-size: 14px;
      color: #000;
      line-height: 1.5;
    }}

    .feat-link:hover .feat-title {{
      color: {ACCENT_RED};
    }}

    @media (max-width: 900px) {{
      .featured-grid {{
        grid-template-columns: 1fr;
      }}
      .feat-link {{
        grid-template-columns: 1fr;
      }}
      .feat-img {{
        border-right: none;
        border-bottom: 1px solid #e0e0e0;
        height: 240px;
      }}
      .blog-hero {{
        padding: 60px 24px;
      }}
      .blog-cats {{
        padding: 18px 24px 26px;
      }}
    }}
  </style>
</head>

<body>

<header class="navbar">
  <div class="navbar-left">
    <a href="index.html" class="logo">
      <img src="Attachments/logo.jpg" alt="Anand Lal Logo">
    </a>
  </div>

  <nav class="navbar-right">
    <a href="index.html">Home</a>
    <a href="about.html">About Me</a>
    <a href="poetry.html">Poetry</a>
    <a href="photos.html">Photos</a>
    <a href="blog.html" class="active">Blog</a>
  </nav>
</header>

<section class="blog-hero">
  <h1>Blog</h1>
</section>

<div class="blog-divider"></div>

<section class="blog-cats">
  <div class="blog-cats-title">Categories</div>
  <div class="cat-row">
    {cat_html}
  </div>
</section>

<div class="featured-wrap">
  <div class="featured-title">Featured Articles</div>
  <div class="featured-grid">
    {cards_html}
  </div>
</div>

<footer class="site-footer">
  © 2026 Anand Lal. All rights reserved.
</footer>

</body>
</html>
"""

# ==============================
# TAG PAGES (blogs/tags/<tag>.html)
# ==============================

def wrap_tag_page(tag: str, posts: list[dict]) -> str:
    tag_pretty = prettify_tag(tag)
    items = []
    for p in posts:
        img = p.get("hero_image_tag_page") or ""
        img_html = f'<img src="{img}" alt="{p["title"]}">' if img else ""

        items.append(f"""
        <div class="tag-item">
          <a class="tag-item-link" href="{p["url_from_tag_page"]}">
            <div class="tag-item-img">{img_html}</div>
            <div class="tag-item-body">
              <div class="tag-item-tag">{tag_pretty}</div>
              <div class="tag-item-title">{p["title"]}</div>
              <div class="tag-item-date">{p.get("date","")}</div>
              <div class="tag-item-tagline">{p.get("tagline","")}</div>
            </div>
          </a>
        </div>
        <div class="tag-divider"></div>
        """)

    items_html = "\n".join(items)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{tag_pretty} | Blog | Anand Lal</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap" rel="stylesheet">

  <link rel="stylesheet" href="../../static/style.css">

  <style>
    .tag-page-wrap {{
      max-width: 980px;
      margin: 160px auto 90px;
      padding: 0 40px;
    }}

    .tag-page-title {{
      font-size: 34px;
      font-weight: 700;
      margin: 0 0 18px;
    }}

    .tag-item {{
      padding: 22px 0;
    }}

    .tag-item-link {{
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 22px;
      text-decoration: none;
      color: #000;
      align-items: start;
    }}

    .tag-item-img {{
      background: #e0e0e0;
      border: 1px solid #e0e0e0;
      height: 200px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .tag-item-img img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}

    .tag-item-tag {{
      font-size: 12px;
      font-weight: 700;
      color: {ACCENT_RED};
      text-transform: uppercase;
      letter-spacing: 0.9px;
      margin-bottom: 8px;
    }}

    .tag-item-title {{
      font-size: 22px;
      font-weight: 700;
      line-height: 1.3;
      margin-bottom: 10px;
    }}

    .tag-item-date {{
      font-size: 13px;
      color: #333;
      margin-bottom: 10px;
    }}

    .tag-item-tagline {{
      font-size: 14px;
      color: #000;
      line-height: 1.55;
    }}

    .tag-item-link:hover .tag-item-title {{
      color: {ACCENT_RED};
    }}

    .tag-divider {{
      height: 1px;
      background: #000;
      opacity: 0.18;
      margin: 0;
    }}

    @media (max-width: 900px) {{
      .tag-item-link {{
        grid-template-columns: 1fr;
      }}
      .tag-item-img {{
        height: 240px;
      }}
    }}
  </style>
</head>

<body>

<header class="navbar">
  <div class="navbar-left">
    <a href="../../index.html" class="logo">
      <img src="../../Attachments/logo.jpg" alt="Anand Lal Logo">
    </a>
  </div>

  <nav class="navbar-right">
    <a href="../../index.html">Home</a>
    <a href="../../about.html">About Me</a>
    <a href="../../poetry.html">Poetry</a>
    <a href="../../photos.html">Photos</a>
    <a href="../../blog.html" class="active">Blog</a>
  </nav>
</header>

<main class="tag-page-wrap">
  <div class="tag-page-title">{tag_pretty}</div>
  {items_html}
</main>

<footer class="site-footer">
  © 2026 Anand Lal. All rights reserved.
</footer>

</body>
</html>
"""

# ==============================
# MAIN
# ==============================

def main():
    excel_path = Path(EXCEL_PATH)
    obs_root = Path(OBSIDIAN_ROOT)
    post_out = Path(POST_OUTPUT_DIR)
    tag_out = Path(TAG_OUTPUT_DIR)

    post_out.mkdir(parents=True, exist_ok=True)
    tag_out.mkdir(parents=True, exist_ok=True)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    if not obs_root.exists():
        raise FileNotFoundError(f"Obsidian root not found: {obs_root}")

    df = pd.read_excel(excel_path)
    required_cols = ["File Name", "Folder Name", "Desired URL Name", "Published (Y/N)", "Featured (Y/N)"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing required column in Excel: {c}")

    posts = []

    # -------- Build posts & individual pages --------
    for _, row in df.iterrows():
        if not yn_to_bool(row["Published (Y/N)"]):
            continue

        file_name = str(row["File Name"]).strip()
        folder_name = str(row["Folder Name"]).strip()
        desired_url = str(row["Desired URL Name"]).strip()
        featured = yn_to_bool(row["Featured (Y/N)"])

        if not desired_url:
            desired_url = safe_slug(file_name)
        slug = safe_slug(desired_url)

        folder_path = obs_root / folder_name
        md_path = find_markdown_file(folder_path, file_name)
        if md_path is None:
            print(f"[WARN] No markdown file found: Folder='{folder_name}', File='{file_name}'")
            continue

        raw_md = read_text(md_path)
        props = parse_obsidian_properties(raw_md)

        tags = props.get("tags", [])
        date_str = props.get("date", "")
        tagline = props.get("tagline", "")

        content_md = strip_frontmatter(raw_md)

        # Title: first H1
        title_match = re.search(r"^\s*#\s+(.+)\s*$", content_md, flags=re.M)
        title = title_match.group(1).strip() if title_match else file_name

        # Image: first image in raw md
        hero_site_root = extract_first_image_src(raw_md, folder_name, from_where="site_root")
        hero_tag_page = extract_first_image_src(raw_md, folder_name, from_where="tag_page")

        # Rewrite images for post page markdown
        processed_md = obsidian_md_to_web_md(content_md, folder_name)
        body_html = markdown_to_html(processed_md)

        header_block = make_post_header_block(tags=tags, title=title, date_str=date_str)
        full_html = wrap_post_page(title, header_block, body_html)

        out_path = post_out / f"{slug}.html"
        write_text(out_path, full_html)
        print(f"[OK] Generated post: {out_path}")

        posts.append({
            "title": title,
            "slug": slug,
            "folder": folder_name,
            "source_md": str(md_path),
            "featured": featured,
            "tags_raw": tags,
            "tags_pretty": [prettify_tag(t) for t in tags],
            "date": date_str,
            "tagline": tagline,
            # Links:
            "url_site_root": f"blogs/generated/{slug}.html",
            "url_from_tag_page": f"../generated/{slug}.html",   # from blogs/tags/*.html
            # Images:
            "hero_image": hero_site_root,         # for blog.html at site root
            "hero_image_tag_page": hero_tag_page, # for tag pages
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        })

    # Write JSON index (useful later for carousels, search, etc.)
    blog_json_path = post_out / "blog.json"
    write_text(blog_json_path, json.dumps(posts, indent=2))
    print(f"[OK] Wrote: {blog_json_path}")

    if not posts:
        print("[WARN] No posts published; skipping blog.html/tag pages.")
        return

    # -------- Build blog.html (featured posts) --------
    featured_posts = [p for p in posts if p["featured"]]
    # If none are featured, fall back to all
    if not featured_posts:
        featured_posts = posts

    # -------- Categories from tags (auto-updating) --------
    tag_set = set()
    for p in posts:
        for t in p["tags_raw"]:
            tag_set.add(t)
    all_tags = sorted(tag_set, key=lambda x: prettify_tag(x).lower())

    blog_html = wrap_blog_index_page(featured_posts=featured_posts, all_tags=all_tags)
    write_text(Path(BLOG_INDEX_OUTPUT), blog_html)
    print(f"[OK] Wrote blog index: {BLOG_INDEX_OUTPUT}")

    # -------- Build tag subpages --------
    tag_to_posts = {t: [] for t in all_tags}
    for p in posts:
        for t in p["tags_raw"]:
            tag_to_posts.setdefault(t, []).append(p)

    for t, plist in tag_to_posts.items():
        # newest-first if you use ISO date; otherwise it will still be stable
        plist_sorted = sorted(plist, key=lambda x: (x.get("date") or ""), reverse=True)
        tag_slug = safe_tag_slug(t)
        tag_page_html = wrap_tag_page(t, plist_sorted)
        out_path = Path(TAG_OUTPUT_DIR) / f"{tag_slug}.html"
        write_text(out_path, tag_page_html)
        print(f"[OK] Generated tag page: {out_path}")

if __name__ == "__main__":
    main()
