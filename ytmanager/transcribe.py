"""Transcricao de audio via Whisper (opcional).

Requer: ffmpeg + um dos backends:
  - faster-whisper (recomendado, mais rapido)  -> pip install faster-whisper
  - openai-whisper                             -> pip install openai-whisper
"""

import os
import shutil
import subprocess
import tempfile


def download_audio(url, out_dir=None, ytdlp_path="yt-dlp", timeout=None):
    """Baixa apenas o audio (m4a) do video. Retorna o caminho do arquivo."""
    workdir = out_dir or tempfile.mkdtemp(prefix="ytmgr_audio_")
    os.makedirs(workdir, exist_ok=True)
    outtmpl = os.path.join(workdir, "audio.%(ext)s")
    cmd = [ytdlp_path, "--no-warnings", "-x", "-f", "bestaudio",
           "-o", outtmpl, url]
    result = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=timeout, check=False)
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError("Falha ao baixar audio:\n%s" % err[-1200:])

    for ext in ("m4a", "webm", "mp3", "opus", "ogg"):
        p = os.path.join(workdir, "audio." + ext)
        if os.path.exists(p):
            return p
    raise RuntimeError("Audio nao encontrado apos o download.")


def to_wav(audio_path, sample_rate=16000):
    """Converte qualquer audio em WAV PCM 16-bit mono via ffmpeg.

    Contorna o decodificador 'av' do faster-whisper (evita bugs de versao).
    """
    if audio_path.lower().endswith(".wav") and "16" in audio_path:
        return audio_path
    wav_path = os.path.splitext(audio_path)[0] + ".16k.wav"
    cmd = ["ffmpeg", "-y", "-i", audio_path, "-ac", "1",
           "-ar", str(sample_rate), "-c:a", "pcm_s16le", wav_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    if result.returncode != 0 or not os.path.exists(wav_path):
        err = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError("ffmpeg falhou ao converter audio: %s" % err[-1000:])
    return wav_path


def transcribe_audio(audio_path, model_size="medium", language="pt"):
    """Transcreve audio com faster-whisper ou openai-whisper.

    Retorna texto unico. Levanta RuntimeError se nenhum backend instalado.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg nao encontrado (necessario para Whisper).")

    try:
        return _transcribe_faster(audio_path, model_size, language)
    except ImportError:
        pass

    try:
        return _transcribe_openai(audio_path, model_size, language)
    except ImportError:
        pass

    raise RuntimeError(
        "Whisper nao instalado. Instale 'faster-whisper' (recomendado) "
        "ou 'openai-whisper'."
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
