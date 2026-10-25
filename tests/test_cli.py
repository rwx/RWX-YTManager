"""Testes de integracao do CLI (ytmanager.cli)."""

import json
import os
from unittest import mock

import pytest

from ytmanager import cli


META_FULL = {
    "id": "abc", "title": "Titulo", "author": "Canal",
    "duration_string": "2:05", "url": "https://youtu.be/abc",
    "description": "desc",
}


@pytest.fixture(autouse=True)
def _no_file_logging(monkeypatch):
    # evita gravar logs em disco durante os testes
    monkeypatch.setenv("K_SERVICE", "test")  # forca stderr-only


class TestParser:
    def test_version(self, capsys):
        with pytest.raises(SystemExit):
            cli.main(["--version"])
        out = capsys.readouterr().out
        assert "ytmanager" in out

    def test_requires_command(self):
        with pytest.raises(SystemExit):
            cli.main([])


class TestCmdInfo:
    def test_oembed(self, capsys):
        with mock.patch("ytmanager.metadata.fetch_oembed",
                        return_value={"id": "abc", "title": "T"}) as m:
            code = cli.main(["info", "https://youtu.be/abc"])
        assert code == 0
        m.assert_called_once()
        assert "abc" in capsys.readouterr().out

    def test_full(self):
        with mock.patch("ytmanager.metadata.fetch_full_metadata",
                        return_value=META_FULL) as m:
            code = cli.main(["info", "https://youtu.be/abc", "--full"])
        assert code == 0
        m.assert_called_once()

    def test_json(self, capsys):
        with mock.patch("ytmanager.metadata.fetch_oembed",
                        return_value={"id": "abc", "title": "T"}):
            cli.main(["info", "https://youtu.be/abc", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert data["id"] == "abc"


class TestCmdSubs:
    def test_lists(self, capsys):
        with mock.patch("ytmanager.subtitles.list_subtitles",
                        return_value={"manual": [], "automatic": ["pt"]}):
            code = cli.main(["subs", "https://youtu.be/abc"])
        assert code == 0
        assert "pt" in capsys.readouterr().out


class TestCmdPlaylist:
    def test_list(self, capsys):
        entries = [{"id": "a", "title": "A", "duration": 65}]
        with mock.patch("ytmanager.playlist.list_entries",
                        return_value=entries):
            code = cli.main(["playlist", "https://youtube.com/@x"])
        assert code == 0
        out = capsys.readouterr().out
        assert "1 videos" in out
        assert "1m05s" in out

    def test_json_output(self, tmp_path, capsys):
        entries = [{"id": "a", "title": "A"}]
        with mock.patch("ytmanager.playlist.list_entries",
                        return_value=entries):
            code = cli.main(["playlist", "u", "--json", "--out",
                             str(tmp_path)])
        assert code == 0
        assert (tmp_path / "playlist.json").exists()


class TestCmdTranscript:
    def _patch_subtitles(self):
        return mock.patch(
            "ytmanager.subtitles.download_subtitles",
            return_value={"path": "/tmp/s.vtt", "lang": "pt", "auto": True})

    def test_from_legenda(self, tmp_path, capsys):
        with mock.patch("ytmanager.metadata.fetch_full_metadata",
                        return_value=META_FULL), \
             self._patch_subtitles(), \
             mock.patch("ytmanager.subtitles.vtt_to_text",
                        return_value="texto da legenda"):
            code = cli.main(["transcript", "https://youtu.be/abc",
                             "--out", str(tmp_path), "--format", "txt"])
        assert code == 0
        assert "legenda automatica" in capsys.readouterr().out
        files = os.listdir(tmp_path)
        assert any(f.endswith(".txt") for f in files)

    def test_whisper_forced(self, tmp_path, capsys):
        with mock.patch("ytmanager.metadata.fetch_full_metadata",
                        return_value=META_FULL), \
             mock.patch("ytmanager.transcribe.download_audio",
                        return_value="/tmp/a.m4a"), \
             mock.patch("ytmanager.transcribe.transcribe_audio",
                        return_value="texto whisper"):
            code = cli.main(["transcript", "https://youtu.be/abc",
                             "--whisper", "--whisper-model", "tiny",
                             "--out", str(tmp_path), "--format", "txt"])
        assert code == 0
        assert "whisper (tiny)" in capsys.readouterr().out

    def test_whisper_fallback_when_no_subs(self, tmp_path, capsys):
        with mock.patch("ytmanager.metadata.fetch_full_metadata",
                        return_value=META_FULL), \
             mock.patch("ytmanager.subtitles.download_subtitles",
                        side_effect=RuntimeError("sem legenda")), \
             mock.patch("ytmanager.transcribe.download_audio",
                        return_value="/tmp/a.m4a"), \
             mock.patch("ytmanager.transcribe.transcribe_audio",
                        return_value="texto"):
            code = cli.main(["transcript", "https://youtu.be/abc",
                             "--whisper-fallback", "--out", str(tmp_path),
                             "--format", "txt"])
        assert code == 0

    def test_multiple_formats(self, tmp_path):
        with mock.patch("ytmanager.metadata.fetch_full_metadata",
                        return_value=META_FULL), \
             self._patch_subtitles(), \
             mock.patch("ytmanager.subtitles.vtt_to_text",
                        return_value="texto"):
            cli.main(["transcript", "https://youtu.be/abc",
                      "--out", str(tmp_path), "--format", "txt,json,md"])
        files = os.listdir(tmp_path)
        assert any(f.endswith(".txt") for f in files)
        assert any(f.endswith(".json") for f in files)
        assert any(f.endswith(".md") for f in files)


class TestErrorHandling:
    def test_runtime_error_returns_1(self, capsys):
        with mock.patch("ytmanager.metadata.fetch_oembed",
                        side_effect=RuntimeError("falhou")):
            code = cli.main(["info", "https://youtu.be/abc"])
        assert code == 1
        assert "falhou" in capsys.readouterr().err

    def test_keyboard_interrupt_returns_130(self):
        with mock.patch("ytmanager.metadata.fetch_oembed",
                        side_effect=KeyboardInterrupt):
            code = cli.main(["info", "https://youtu.be/abc"])
        assert code == 130

    def test_unexpected_error_returns_2(self, capsys):
        with mock.patch("ytmanager.metadata.fetch_oembed",
                        side_effect=ValueError("bug")):
            code = cli.main(["info", "https://youtu.be/abc"])
        assert code == 2
        assert "correlation_id" in capsys.readouterr().err
