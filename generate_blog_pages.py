import os
import markdown2
from jinja2 import Template
import json

# Paths
BASE_DIR = r"C:\Users\neell\Downloads\Academic Website\templates"
MARKDOWN_FOLDER = os.path.join(BASE_DIR, "blogs", "markdown_files")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "blogs", "generated_html")
TEMPLATE_PATH = os.path.join(BASE_DIR, "blog_template.html")
BLOG_PREVIEW_JSON = os.path.join(BASE_DIR, "static", "blog_posts.json")

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Read the blog template
with open(TEMPLATE_PATH, "r") as f:
    blog_template = Template(f.read())

# Blog previews list
blog_previews = []

# Process each Markdown file
for file_name in os.listdir(MARKDOWN_FOLDER):
    if file_name.endswith(".md"):
        # Full path to the Markdown file
        markdown_path = os.path.join(MARKDOWN_FOLDER, file_name)

        # Parse Markdown file
        with open(markdown_path, "r") as f:
            content = f.read()
        md = markdown2.Markdown(extras=["metadata"])
        html_content = md.convert(content)

        # Extract metadata
        metadata = md.metadata
        output_file = file_name.replace(".md", ".html")

        # Generate HTML file for the blog post
        rendered_blog = blog_template.render(
            title=metadata["title"],
            date=metadata["date"],
            author=metadata["author"],
            tags=metadata["tags"],
            content=html_content
        )
        with open(os.path.join(OUTPUT_FOLDER, output_file), "w") as f:
            f.write(rendered_blog)

        # Add to previews list
# Replace this line in the JSON serialization
blog_previews.append({
    "title": metadata["title"],
    "date": metadata["date"],
    "author": metadata["author"],
    "synopsis": html_content.split("\n")[0],  # Extract synopsis
    "image": metadata["image"],
    "link": f"blogs/generated_html/{output_file}",
    "tags": metadata["tags"]
})

# Save blog previews to JSON
with open(BLOG_PREVIEW_JSON, "w") as f:
    json.dump(blog_previews, f, indent=4)

print("Blog pages generated successfully.")
