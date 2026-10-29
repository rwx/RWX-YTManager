"""Download e conversao de video do YouTube para arquivo local.

Baixa o video (video+audio) e converte/remuxa para o formato pedido (mp4,
mkv, webm). Para MP4 seleciona video H.264 + audio AAC (compatibilidade
maxima); para MKV faz remux sem perda quando possivel.

Requer ffmpeg para conversao/merging (yt-dlp usa ffmpeg internamente).
"""

import os
import subprocess

from .errors import HINT_FFMPEG, HINT_URL, HINT_YTDLP, YtManagerError

# Perfis de formato por container de saida.
_FORMAT_SELECTOR = {
    "mp4": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
    "mkv": "bv*+ba/b",
    "webm": "bv*[ext=webm]+ba[ext=webm]/b[ext=webm]/bv*+ba/b",
}

SUPPORTED_FORMATS = tuple(_FORMAT_SELECTOR.keys())


def download_video(url, out_dir=None, fmt="mp4", quality=None,
                   ytdlp_path="yt-dlp", timeout=None, extra_args=None):
    """Baixa o video do YouTube e retorna o caminho do arquivo final.

    Args:
        url: URL do video.
        out_dir: diretorio de saida (default: diretorio temporario).
        fmt: "mp4" (default), "mkv" ou "webm".
        quality: limite de altura, ex. "1080", "720", "best" (default: best).
        ytdlp_path: executavel do yt-dlp.
        timeout: timeout do subprocess.
        extra_args: lista de argumentos extras para o yt-dlp.

    Returns:
        Caminho absoluto do arquivo baixado (base.<fmt>).

    Raises:
        YtManagerError: em falha de download/conversao.
    """
    if fmt not in SUPPORTED_FORMATS:
        raise YtManagerError(
            "Formato de video nao suportado: '%s'." % fmt,
            hint="Use um destes formatos: %s." % ", ".join(SUPPORTED_FORMATS),
            detail="fmt invalido: %s" % fmt,
        )

    workdir = out_dir or _tempdir()
    os.makedirs(workdir, exist_ok=True)
    outtmpl = os.path.join(workdir, "video.%(ext)s")

    selector = _FORMAT_SELECTOR[fmt]
    if quality and quality != "best":
        selector = selector.replace("bv*", "bv*[height<=%s]" % quality, 1)

    cmd = [ytdlp_path, "--no-warnings", "--no-playlist",
           "-f", selector, "--merge-output-format", fmt,
           "-o", outtmpl]
    if extra_args:
        cmd += list(extra_args)
    cmd.append(url)

    if not _has_ffmpeg():
        raise YtManagerError(
            "O ffmpeg nao esta instalado (necessario para juntar video e audio).",
            hint=HINT_FFMPEG,
            detail="ffmpeg ausente no PATH",
        )

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
            "Nao foi possivel baixar o video.",
            hint=HINT_URL,
            detail="yt-dlp falhou:\n%s" % err[-1500:],
        )

    final = os.path.join(workdir, "video." + fmt)
    if os.path.exists(final):
        return final

    # yt-dlp pode escolher extensao diferente mesmo com --merge-output-format
    for ext in (fmt, "mkv", "mp4", "webm"):
        candidate = os.path.join(workdir, "video." + ext)
        if os.path.exists(candidate):
            return candidate

    raise YtManagerError(
        "O video baixado nao foi encontrado no disco.",
        hint=HINT_YTDLP,
        detail="nenhum arquivo video.* em %s" % workdir,
    )


def convert_video(src_path, dst_format, out_dir=None, timeout=None):
    """Converte um arquivo de video local para outro container via ffmpeg.

    Remux sem reencode quando possivel (-c copy); se o container de destino
    nao aceitar os codecs, o ffmpeg faz reencode automatico como fallback.

    Returns:
        Caminho do arquivo convertido.

    Raises:
        YtManagerError: se ffmpeg falhar.
    """
    if dst_format not in SUPPORTED_FORMATS:
        raise YtManagerError(
            "Formato de destino nao suportado: '%s'." % dst_format,
            hint="Use um destes formatos: %s." % ", ".join(SUPPORTED_FORMATS),
            detail="dst_format invalido: %s" % dst_format,
        )
    if not os.path.exists(src_path):
        raise YtManagerError(
            "O arquivo de origem nao foi encontrado.",
            hint="Confira o caminho do arquivo de entrada.",
            detail="inexistente: %s" % src_path,
        )
    if not _has_ffmpeg():
        raise YtManagerError(
            "O ffmpeg nao esta instalado (necessario para converter videos).",
            hint=HINT_FFMPEG,
            detail="ffmpeg ausente no PATH",
        )

    workdir = out_dir or os.path.dirname(os.path.abspath(src_path))
    base = os.path.splitext(os.path.basename(src_path))[0]
    out_path = os.path.join(workdir, "%s.%s" % (base, dst_format))

    # 1) tenta remux (-c copy); 2) se falhar, reencode
    for copy_mode in (True, False):
        cmd = ["ffmpeg", "-y", "-i", src_path]
        if copy_mode:
            cmd += ["-c", "copy"]
        cmd += [out_path]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=timeout,
                                    check=False)
        except FileNotFoundError as exc:
            raise YtManagerError(
                "O ffmpeg nao foi encontrado.",
                hint=HINT_FFMPEG,
                detail="executavel 'ffmpeg' inexistente",
            ) from exc
        if result.returncode == 0 and os.path.exists(out_path):
            return out_path
        if copy_mode:
            continue  # tenta com reencode

    err = result.stderr.decode("utf-8", "replace").strip()
    raise YtManagerError(
        "Nao foi possivel converter o video para %s." % dst_format,
        hint=HINT_FFMPEG,
        detail="ffmpeg falhou: %s" % err[-1000:],
    )


def _has_ffmpeg():
    import shutil
    return shutil.which("ffmpeg") is not None


def _tempdir():
    import tempfile
    return tempfile.mkdtemp(prefix="ytmgr_video_")
