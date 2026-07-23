import re


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def slugify_filename(filename: str) -> str:
    if "." in filename:
        stem, ext = filename.rsplit(".", 1)
    else:
        stem, ext = filename, ""
    stem_slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", stem).strip("-") or "file"
    return f"{stem_slug}.{ext}" if ext else stem_slug
