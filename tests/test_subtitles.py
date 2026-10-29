"""Testes de ytmanager.subtitles (parsing VTT/lista e download com mock)."""

import os
import subprocess
from unittest import mock

import pytest

from ytmanager import subtitles as subs


class TestVttToText:
    def _write(self, tmp_path, content):
        path = str(tmp_path / "s.vtt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_basic(self, tmp_path):
        vtt = """WEBVTT
Kind: captions
Language: pt

00:00:01.000 --> 00:00:03.000
Ola mundo

00:00:03.000 --> 00:00:05.000
Segunda frase
"""
        text = subs.vtt_to_text(self._write(tmp_path, vtt))
        assert text == "Ola mundo Segunda frase"

    def test_dedup(self, tmp_path):
        vtt = """WEBVTT

00:00:01.000 --> 00:00:02.000
Repetida

00:00:02.000 --> 00:00:03.000
Repetida

00:00:03.000 --> 00:00:04.000
Nova
"""
        text = subs.vtt_to_text(self._write(tmp_path, vtt), dedup=True)
        assert text == "Repetida Nova"

    def test_no_dedup(self, tmp_path):
        vtt = """WEBVTT

00:00:01.000 --> 00:00:02.000
Repetida

00:00:02.000 --> 00:00:03.000
Repetida
"""
        text = subs.vtt_to_text(self._write(tmp_path, vtt), dedup=False)
        assert text == "Repetida Repetida"

    def test_strips_tags(self, tmp_path):
        vtt = """WEBVTT

00:00:01.000 --> 00:00:02.000
<c>texto</c> com <b>tags</b>
"""
        text = subs.vtt_to_text(self._write(tmp_path, vtt))
        assert "texto com tags" == text
        assert "<" not in text

    def test_ignores_timestamps_and_numbers(self, tmp_path):
        vtt = """WEBVTT

1
00:00:01.000 --> 00:00:02.000
Unica linha
"""
        text = subs.vtt_to_text(self._write(tmp_path, vtt))
        assert text == "Unica linha"

    def test_empty(self, tmp_path):
        text = subs.vtt_to_text(self._write(tmp_path, "WEBVTT\n"))
        assert text == ""


class TestLangInName:
    def test_dot_lang(self):
        assert subs._lang_in_name("subs.pt.vtt", "pt") is True

    def test_paren_lang(self):
        assert subs._lang_in_name("subs (pt).vtt", "pt") is True

    def test_not_found(self):
        assert subs._lang_in_name("subs.en.vtt", "pt") is False


class TestListSubtitles:
    SAMPLE = """[info] Available automatic captions for abc:
Language Name                  Formats
ab       Abkhazian             vtt, srt, json3
pt       Portuguese            vtt, srt, json3
en       English               vtt, srt, json3
"""

    def test_parses_auto(self):
        cp = subprocess.CompletedProcess(args=[], returncode=0,
                                         stdout=self.SAMPLE.encode())
        with mock.patch("subprocess.run", return_value=cp):
            langs = subs.list_subtitles("https://youtu.be/x")
        assert "pt" in langs["automatic"]
        assert "en" in langs["automatic"]
        assert "Language" not in langs["automatic"]

    def test_parses_manual_section(self):
        sample = """[info] Available subtitles for abc:
Language Name Formats
pt       Portuguese   vtt
"""
        cp = subprocess.CompletedProcess(args=[], returncode=0,
                                         stdout=sample.encode())
        with mock.patch("subprocess.run", return_value=cp):
            langs = subs.list_subtitles("https://youtu.be/x")
        assert "pt" in langs["manual"]

    def test_yt_dlp_not_found(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="yt-dlp nao foi encontrado"):
                subs.list_subtitles("https://youtu.be/x")


class TestDownloadSubtitles:
    def test_manual_found(self, tmp_path):
        # simula yt-dlp criando o arquivo manual
        def fake_run(cmd, **kwargs):
            if "--write-subs" in cmd:
                path = os.path.join(str(tmp_path), "subs.pt.vtt")
                open(path, "w").close()
            return subprocess.CompletedProcess(args=cmd, returncode=0,
                                               stdout=b"", stderr=b"")
        with mock.patch("subprocess.run", side_effect=fake_run):
            got = subs.download_subtitles("https://youtu.be/x", lang="pt",
                                          out_dir=str(tmp_path))
        assert got["auto"] is False
        assert got["lang"] == "pt"

    def test_auto_fallback(self, tmp_path):
        def fake_run(cmd, **kwargs):
            if "--write-auto-subs" in cmd:
                path = os.path.join(str(tmp_path), "subs.pt.vtt")
                open(path, "w").close()
            return subprocess.CompletedProcess(args=cmd, returncode=0,
                                               stdout=b"", stderr=b"")
        with mock.patch("subprocess.run", side_effect=fake_run):
            got = subs.download_subtitles("https://youtu.be/x", lang="pt",
                                          out_dir=str(tmp_path))
        assert got["auto"] is True

    def test_not_found(self, tmp_path):
        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0,
                                               stdout=b"", stderr=b"")
        with mock.patch("subprocess.run", side_effect=fake_run):
            with pytest.raises(RuntimeError, match="Nenhuma legenda"):
                subs.download_subtitles("https://youtu.be/x", lang="pt",
                                        out_dir=str(tmp_path))
