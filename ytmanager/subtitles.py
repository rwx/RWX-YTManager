"""Download e limpeza de legendas do YouTube via yt-dlp."""

import glob
import os
import re
import subprocess
import tempfile

from .errors import HINT_SUBS, HINT_YTDLP, YtManagerError


def list_subtitles(url, ytdlp_path="yt-dlp", timeout=None):
    """Lista idiomas de legenda manual e automatica disponiveis."""
    cmd = [ytdlp_path, "--no-warnings", "--skip-download", "--list-subs", url]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, check=False,
        )
    except FileNotFoundError as exc:
        raise YtManagerError(
            "O yt-dlp nao foi encontrado.",
            hint=HINT_YTDLP,
            detail="executavel '%s' inexistente" % ytdlp_path,
        ) from exc

    out = result.stdout.decode("utf-8", "replace")
    manual, auto = set(), set()
    section = None
    for line in out.splitlines():
        low = line.lower()
        if "available subtitles" in low:
            section = "manual"
            continue
        if "available automatic captions" in low:
            section = "auto"
            continue
        if not section:
            continue
        if low.startswith("language "):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        code = parts[0]
        if not re.fullmatch(r"[a-zA-Z]{2,10}(-[a-zA-Z]+)?", code):
            continue
        (manual if section == "manual" else auto).add(code)
    return {"manual": sorted(manual), "automatic": sorted(auto)}


def download_subtitles(url, lang="pt", auto_fallback=True, out_dir=None,
                       ytdlp_path="yt-dlp", timeout=None):
    """Baixa legenda (manual; ou automatica se auto_fallback) e retorna caminho.

    Retorna isto: {"path": <arquivo .vtt>, "lang": lang, "auto": bool}
    Levanta RuntimeError se nenhuma legenda for encontrada.
    """
    workdir = out_dir or tempfile.mkdtemp(prefix="ytmgr_")
    os.makedirs(workdir, exist_ok=True)
    outtmpl = os.path.join(workdir, "subs.%(ext)s")

    base = [ytdlp_path, "--no-warnings", "--skip-download", "-o", outtmpl]

    # 1) tenta legenda manual (escrita) no idioma pedido
    manual = base + ["--write-subs", "--sub-langs", lang, "--sub-format", "vtt", url]
    try:
        subprocess.run(manual, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise YtManagerError(
            "O yt-dlp nao foi encontrado.",
            hint=HINT_YTDLP,
            detail="executavel '%s' inexistente" % ytdlp_path,
        ) from exc
    found = glob.glob(os.path.join(workdir, "subs*.vtt"))
    found = [f for f in found if _lang_in_name(f, lang)]
    if found:
        return {"path": found[0], "lang": lang, "auto": False}

    # 2) fallback: legenda automatica
    if auto_fallback:
        auto = base + ["--write-auto-subs", "--sub-langs", lang,
                       "--sub-format", "vtt", url]
        subprocess.run(auto, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout, check=False)
        found = glob.glob(os.path.join(workdir, "subs*.vtt"))
        found = [f for f in found if _lang_in_name(f, lang)]
        if found:
            return {"path": found[0], "lang": lang, "auto": True}

    raise YtManagerError(
        "Nenhuma legenda foi encontrada para o idioma '%s'." % lang,
        hint=HINT_SUBS,
        detail="sem legenda manual/automatica em %s" % lang,
    )


def vtt_to_text(vtt_path, dedup=True):
    """Converte VTT em texto limpo (remove timestamps, tags e duplicatas)."""
    with open(vtt_path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if "-->" in ln:
            continue
        if re.fullmatch(r"\d+", ln):
            continue
        ln = re.sub(r"<[^>]+>", "", ln).strip()
        if not ln:
            continue
        if dedup and out and out[-1] == ln:
            continue
        out.append(ln)

    text = " ".join(out)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _lang_in_name(path, lang):
    name = os.path.basename(path)
    return (".%s." % lang) in name or ("(%s)" % lang) in name
