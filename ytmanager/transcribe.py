"""Transcricao de audio via Whisper (opcional).

Requer: ffmpeg + um dos backends:
  - faster-whisper (recomendado, mais rapido)  -> pip install faster-whisper
  - openai-whisper                             -> pip install openai-whisper
"""

import os
import shutil
import subprocess
import tempfile

from .errors import (HINT_FFMPEG, HINT_URL, HINT_WHISPER, HINT_YTDLP,
                     YtManagerError)


def download_audio(url, out_dir=None, ytdlp_path="yt-dlp", timeout=None):
    """Baixa apenas o audio (m4a) do video. Retorna o caminho do arquivo."""
    workdir = out_dir or tempfile.mkdtemp(prefix="ytmgr_audio_")
    os.makedirs(workdir, exist_ok=True)
    outtmpl = os.path.join(workdir, "audio.%(ext)s")
    cmd = [ytdlp_path, "--no-warnings", "-x", "-f", "bestaudio",
           "-o", outtmpl, url]
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
            "Nao foi possivel baixar o audio do video.",
            hint=HINT_URL,
            detail="yt-dlp falhou:\n%s" % err[-1200:],
        )

    for ext in ("m4a", "webm", "mp3", "opus", "ogg"):
        p = os.path.join(workdir, "audio." + ext)
        if os.path.exists(p):
            return p
    raise YtManagerError(
        "O audio baixado nao foi encontrado no disco.",
        hint=HINT_YTDLP,
        detail="nenhum arquivo audio.* em %s" % workdir,
    )


def to_wav(audio_path, sample_rate=16000):
    """Converte qualquer audio em WAV PCM 16-bit mono via ffmpeg.

    Contorna o decodificador 'av' do faster-whisper (evita bugs de versao).
    """
    if audio_path.lower().endswith(".wav") and "16" in audio_path:
        return audio_path
    wav_path = os.path.splitext(audio_path)[0] + ".16k.wav"
    cmd = ["ffmpeg", "-y", "-i", audio_path, "-ac", "1",
           "-ar", str(sample_rate), "-c:a", "pcm_s16le", wav_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False)
    except FileNotFoundError as exc:
        raise YtManagerError(
            "O ffmpeg nao foi encontrado.",
            hint=HINT_FFMPEG,
            detail="executavel 'ffmpeg' inexistente",
        ) from exc
    if result.returncode != 0 or not os.path.exists(wav_path):
        err = result.stderr.decode("utf-8", "replace").strip()
        raise YtManagerError(
            "Falha ao converter o audio para o formato de transcricao.",
            hint=HINT_FFMPEG,
            detail="ffmpeg falhou: %s" % err[-1000:],
        )
    return wav_path


def transcribe_audio(audio_path, model_size="medium", language="pt"):
    """Transcreve audio com faster-whisper ou openai-whisper.

    Retorna texto unico. Levanta RuntimeError se nenhum backend instalado.
    """
    if not shutil.which("ffmpeg"):
        raise YtManagerError(
            "O ffmpeg nao esta instalado (necessario para a transcricao por IA).",
            hint=HINT_FFMPEG,
            detail="ffmpeg ausente no PATH",
        )

    try:
        return _transcribe_faster(audio_path, model_size, language)
    except ImportError:
        pass

    try:
        return _transcribe_openai(audio_path, model_size, language)
    except ImportError:
        pass

    raise YtManagerError(
        "O backend de transcricao por IA (Whisper) nao esta instalado.",
        hint=HINT_WHISPER,
        detail="nenhum de faster-whisper / openai-whisper importavel",
    )


def _transcribe_faster(audio_path, model_size, language):
    from faster_whisper import WhisperModel  # noqa: F401
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    wav = to_wav(audio_path)
    segments, _info = model.transcribe(wav, language=language)
    return " ".join(seg.text.strip() for seg in segments).strip()


def _transcribe_openai(audio_path, model_size, language):
    import whisper  # noqa: F401
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path, language=language)
    return (result.get("text") or "").strip()
