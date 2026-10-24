"""Escrita de resultados em txt, json e markdown."""

import json
import os
import re


def slugify(text, max_len=80):
    text = (text or "video").strip().lower()
    text = unicodedata_strip(text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text[:max_len] or "video")


def unicodedata_strip(text):
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def write_json(data, out_path):
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return out_path


def write_text(text, out_path):
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return out_path


def write_markdown(result, out_path):
    md = []
    meta = result.get("metadata") or {}
    md.append("# %s" % (meta.get("title") or "Video"))
    md.append("")
    if meta.get("author"):
        md.append("- **Canal:** %s" % meta["author"])
    if meta.get("url"):
        md.append("- **URL:** %s" % meta["url"])
    if meta.get("duration_string"):
        md.append("- **Duracao:** %s" % meta["duration_string"])
    if meta.get("upload_date"):
        md.append("- **Publicado:** %s" % meta["upload_date"])
    if meta.get("view_count"):
        md.append("- **Views:** %s" % meta["view_count"])
    md.append("")
    if meta.get("description"):
        md.append("## Descricao")
        md.append("")
        md.append(meta["description"])
        md.append("")
    if result.get("transcript"):
        md.append("## Transcricao")
        md.append("")
        md.append(result["transcript"])
        md.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    return out_path
