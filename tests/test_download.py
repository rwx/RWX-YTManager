"""Testes de ytmanager.download (baixar/converter video)."""

import os
import subprocess
from unittest import mock

import pytest

from ytmanager import download as dl
from ytmanager.errors import YtManagerError


def _cp(returncode=0, stdout=b"", stderr=b""):
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                       stdout=stdout, stderr=stderr)


class TestDownloadVideo:
    def test_invalid_format(self):
        with pytest.raises(YtManagerError, match="nao suportado"):
            dl.download_video("u", fmt="avi")

    def test_no_ffmpeg(self):
        with mock.patch("shutil.which", return_value=None):
            with pytest.raises(YtManagerError, match="ffmpeg"):
                dl.download_video("u", out_dir="/tmp/x")

    def test_success(self, tmp_path):
        def fake_run(cmd, **kwargs):
            open(os.path.join(str(tmp_path), "video.mp4"), "w").close()
            return _cp()
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run", side_effect=fake_run):
            path = dl.download_video("https://youtu.be/x",
                                     out_dir=str(tmp_path))
        assert path.endswith("video.mp4")
        assert os.path.exists(path)

    def test_mkv_format(self, tmp_path):
        def fake_run(cmd, **kwargs):
            open(os.path.join(str(tmp_path), "video.mkv"), "w").close()
            return _cp()
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run", side_effect=fake_run):
            path = dl.download_video("u", out_dir=str(tmp_path), fmt="mkv")
        assert path.endswith("video.mkv")

    def test_quality_selector(self, tmp_path):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            open(os.path.join(str(tmp_path), "video.mp4"), "w").close()
            return _cp()
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run", side_effect=fake_run):
            dl.download_video("u", out_dir=str(tmp_path), quality="720")
        joined = " ".join(captured["cmd"])
        assert "height<=720" in joined

    def test_ytdlp_not_found(self, tmp_path):
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(YtManagerError, match="yt-dlp nao foi encontrado"):
                dl.download_video("u", out_dir=str(tmp_path))

    def test_failure(self, tmp_path):
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run",
                        return_value=_cp(returncode=1, stderr=b"erro")):
            with pytest.raises(YtManagerError, match="baixar o video"):
                dl.download_video("u", out_dir=str(tmp_path))

    def test_file_missing_after_success(self, tmp_path):
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run", return_value=_cp()):
            with pytest.raises(YtManagerError, match="nao foi encontrado no disco"):
                dl.download_video("u", out_dir=str(tmp_path))


class TestConvertVideo:
    def test_invalid_format(self, tmp_path):
        src = str(tmp_path / "a.mp4")
        open(src, "w").close()
        with pytest.raises(YtManagerError, match="nao suportado"):
            dl.convert_video(src, "avi")

    def test_missing_source(self):
        with pytest.raises(YtManagerError, match="origem"):
            dl.convert_video("/nao/existe.mp4", "mkv")

    def test_no_ffmpeg(self, tmp_path):
        src = str(tmp_path / "a.mp4")
        open(src, "w").close()
        with mock.patch("shutil.which", return_value=None):
            with pytest.raises(YtManagerError, match="ffmpeg"):
                dl.convert_video(src, "mkv")

    def test_remux_copy_success(self, tmp_path):
        src = str(tmp_path / "a.mp4")
        open(src, "w").close()

        def fake_run(cmd, **kwargs):
            open(cmd[-1], "w").close()
            return _cp()
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run", side_effect=fake_run):
            out = dl.convert_video(src, "mkv", out_dir=str(tmp_path))
        assert out.endswith("a.mkv")

    def test_fallback_to_reencode(self, tmp_path):
        src = str(tmp_path / "a.mp4")
        open(src, "w").close()
        calls = {"n": 0}

        def fake_run(cmd, **kwargs):
            calls["n"] += 1
            # primeira tentativa (-c copy) falha; segunda (reencode) ok
            if "-c" in cmd and "copy" in cmd:
                return _cp(returncode=1, stderr=b"copy falhou")
            open(cmd[-1], "w").close()
            return _cp()

        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run", side_effect=fake_run):
            out = dl.convert_video(src, "mkv", out_dir=str(tmp_path))
        assert out.endswith("a.mkv")
        assert calls["n"] == 2

    def test_ffmpeg_failure(self, tmp_path):
        src = str(tmp_path / "a.mp4")
        open(src, "w").close()
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run",
                        return_value=_cp(returncode=1, stderr=b"falhou")):
            with pytest.raises(YtManagerError, match="converter o video"):
                dl.convert_video(src, "mkv", out_dir=str(tmp_path))

    def test_ffmpeg_not_found_binary(self, tmp_path):
        src = str(tmp_path / "a.mp4")
        open(src, "w").close()
        with mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(YtManagerError, match="ffmpeg nao foi encontrado"):
                dl.convert_video(src, "mkv", out_dir=str(tmp_path))
