"""Extracao de playlists e canais (listagem de videos)."""

import json
import subprocess

from .errors import HINT_URL, HINT_YTDLP, YtManagerError
from .validation import ensure_arg_list


def list_entries(url, ytdlp_path="yt-dlp", limit=None, flat=True, timeout=None):
    """Lista videos de uma playlist/canal. Retorna lista de dicts."""
    cmd = [ytdlp_path, "--no-warnings", "--dump-json"]
    if flat:
        cmd.append("--flat-playlist")
    if limit:
        cmd += ["--playlist-end", str(limit)]
    cmd.append(url)
    cmd = ensure_arg_list(cmd)

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout,
                                check=False)
    except FileNotFoundError as exc:
        raise YtManagerError(
            "O yt-dlp nao foi encontrado.",
            hint=HINT_YTDLP,
            detail="executavel '%s' inexistente" % ytdlp_path,
        ) from exc
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", "replace").strip()
        raise YtManagerError(
            "Nao foi possivel listar a playlist ou canal.",
            hint=HINT_URL,
            detail="yt-dlp falhou:\n%s" % err[-1200:],
        )

    entries = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        entries.append({
            "id": raw.get("id"),
            "title": raw.get("title"),
            "url": raw.get("url") or raw.get("webpage_url"),
            "duration": raw.get("duration"),
            "uploader": raw.get("uploader") or raw.get("channel"),
        })
    return entries
