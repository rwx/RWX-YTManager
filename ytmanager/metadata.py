"""Extracao de metadados de videos do YouTube.

Estrategia em duas camadas:
1. oEmbed (rapido) - titulo, autor, thumbnail.
2. yt-dlp --dump-json (completo) - duracao, views, data, descricao, capitulos.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from .errors import (HINT_NETWORK, HINT_URL, HINT_YTDLP, YtManagerError,
                     friendly_http_message)

OEMBED_URL = "https://www.youtube.com/oembed"


def fetch_oembed(url, timeout=15):
    """Metadados basicos via oEmbed (sem autenticacao)."""
    params = urllib.parse.urlencode({"url": url, "format": "json"})
    req = urllib.request.Request(
        "%s?%s" % (OEMBED_URL, params),
        headers={"User-Agent": "RWX-YTManager/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise YtManagerError(
            friendly_http_message(exc.code),
            hint=HINT_URL,
            detail="oEmbed HTTP %s para %s" % (exc.code, url),
        ) from exc
    except urllib.error.URLError as exc:
        raise YtManagerError(
            "Nao foi possivel conectar ao YouTube.",
            hint=HINT_NETWORK,
            detail="oEmbed URLError: %s" % exc.reason,
        ) from exc

    return {
        "id": extract_video_id(url),
        "url": url,
        "title": data.get("title"),
        "author": data.get("author_name"),
        "author_url": data.get("author_url"),
        "thumbnail": data.get("thumbnail_url"),
        "provider": data.get("provider_name"),
    }


def fetch_full_metadata(url, ytdlp_path="yt-dlp", timeout=None):
    """Metadados completos via yt-dlp (--dump-json)."""
    import subprocess

    cmd = [ytdlp_path, "--no-warnings", "--skip-download", "--dump-json", url]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False,
        )
    except FileNotFoundError as exc:
        raise YtManagerError(
            "O yt-dlp nao foi encontrado.",
            hint=HINT_YTDLP,
            detail="executavel '%s' inexistente" % ytdlp_path,
        ) from exc

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", "replace").strip()
        raise YtManagerError(
            "Nao foi possivel obter os metadados do video.",
            hint=HINT_URL,
            detail="yt-dlp falhou:\n%s" % err[-1500:],
        )

    lines = result.stdout.decode("utf-8", "replace").splitlines()
    if not lines:
        raise YtManagerError(
            "O video nao retornou metadados.",
            hint=HINT_URL,
            detail="yt-dlp nao produziu saida para %s" % url,
        )

    raw = json.loads(lines[0])
    return {
        "id": raw.get("id"),
        "url": raw.get("webpage_url") or url,
        "title": raw.get("title"),
        "author": raw.get("uploader") or raw.get("channel"),
        "author_url": raw.get("channel_url"),
        "channel_id": raw.get("channel_id"),
        "thumbnail": raw.get("thumbnail"),
        "duration_seconds": raw.get("duration"),
        "duration_string": _format_duration(raw.get("duration")),
        "view_count": raw.get("view_count"),
        "like_count": raw.get("like_count"),
        "comment_count": raw.get("comment_count"),
        "upload_date": _format_date(raw.get("upload_date")),
        "description": raw.get("description"),
        "categories": raw.get("categories"),
        "tags": raw.get("tags"),
        "chapters": raw.get("chapters"),
        "subtitles": {
            k: [f.get("ext") for f in v]
            for k, v in (raw.get("subtitles") or {}).items()
        },
        "automatic_captions": list((raw.get("automatic_captions") or {}).keys()),
    }


def extract_video_id(url):
    """Extrai o ID do video de varios formatos de URL do YouTube."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if "youtu.be" in host:
        return parsed.path.lstrip("/").split("/")[0] or None
    qs = urllib.parse.parse_qs(parsed.query)
    if "v" in qs:
        return qs["v"][0]
    parts = [p for p in parsed.path.split("/") if p]
    for marker in ("shorts", "embed", "live", "v"):
        if marker in parts:
            i = parts.index(marker)
            if i + 1 < len(parts):
                return parts[i + 1]
    return parts[-1] if parts else None


def _format_duration(seconds):
    if not seconds:
        return None
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%d:%02d:%02d" % (h, m, s)
    return "%d:%02d" % (m, s)


def _format_date(yyyymmdd):
    if not yyyymmdd or len(str(yyyymmdd)) != 8:
        return yyyymmdd
    d = str(yyyymmdd)
    return "%s-%s-%s" % (d[0:4], d[4:6], d[6:8])
