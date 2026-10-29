"""Testes de ytmanager.transcribe (download de audio e backend)."""

import subprocess
from unittest import mock

import pytest

from ytmanager import transcribe as tr


def _cp(returncode=0, stdout=b"", stderr=b""):
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                       stdout=stdout, stderr=stderr)


class TestDownloadAudio:
    def test_success(self, tmp_path):
        def fake_run(cmd, **kwargs):
            # simula arquivo criado pelo yt-dlp
            open(os.path.join(str(tmp_path), "audio.m4a"), "w").close()
            return _cp()

        import os
        with mock.patch("subprocess.run", side_effect=fake_run):
            path = tr.download_audio("https://youtu.be/x", out_dir=str(tmp_path))
        assert path.endswith("audio.m4a")

    def test_failure(self, tmp_path):
        with mock.patch("subprocess.run",
                        return_value=_cp(returncode=1, stderr=b"erro")):
            with pytest.raises(RuntimeError, match="baixar o audio"):
                tr.download_audio("https://youtu.be/x", out_dir=str(tmp_path))

    def test_no_audio_file(self, tmp_path):
        with mock.patch("subprocess.run", return_value=_cp()):
            with pytest.raises(RuntimeError, match="nao foi encontrado no disco"):
                tr.download_audio("https://youtu.be/x", out_dir=str(tmp_path))


class TestToWav:
    def test_failure(self, tmp_path):
        src = str(tmp_path / "audio.m4a")
        open(src, "w").close()
        with mock.patch("subprocess.run",
                        return_value=_cp(returncode=1, stderr=b"erro ffmpeg")):
            with pytest.raises(RuntimeError, match="converter o audio"):
                tr.to_wav(src)

    def test_success(self, tmp_path):
        src = str(tmp_path / "audio.m4a")
        open(src, "w").close()

        def fake_run(cmd, **kwargs):
            # cria o wav de destino (ultimo argumento)
            open(cmd[-1], "w").close()
            return _cp()

        with mock.patch("subprocess.run", side_effect=fake_run):
            wav = tr.to_wav(src)
        assert wav.endswith(".wav")


class TestTranscribeAudio:
    def test_no_ffmpeg(self):
        with mock.patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="ffmpeg nao esta instalado"):
                tr.transcribe_audio("audio.m4a")

    def test_faster_backend(self):
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("ytmanager.transcribe._transcribe_faster",
                        return_value="texto"):
            assert tr.transcribe_audio("audio.m4a") == "texto"

    def test_falls_back_to_openai(self):
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("ytmanager.transcribe._transcribe_faster",
                        side_effect=ImportError), \
             mock.patch("ytmanager.transcribe._transcribe_openai",
                        return_value="texto openai"):
            assert tr.transcribe_audio("audio.m4a") == "texto openai"

    def test_no_backend(self):
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("ytmanager.transcribe._transcribe_faster",
                        side_effect=ImportError), \
             mock.patch("ytmanager.transcribe._transcribe_openai",
                        side_effect=ImportError):
            with pytest.raises(RuntimeError, match="Whisper"):
                tr.transcribe_audio("audio.m4a")
