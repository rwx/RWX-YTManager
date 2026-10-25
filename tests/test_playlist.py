"""Testes de ytmanager.playlist."""

import json
import subprocess
from unittest import mock

import pytest

from ytmanager import playlist as pl


def _cp(returncode=0, stdout=b"", stderr=b""):
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                       stdout=stdout, stderr=stderr)


class TestListEntries:
    def test_success(self):
        rows = [
            {"id": "a", "title": "Video A", "url": "https://youtu.be/a",
             "duration": 125, "uploader": "Canal"},
            {"id": "b", "title": "Video B", "duration": None},
        ]
        stdout = ("\n".join(json.dumps(r) for r in rows) + "\n").encode()
        with mock.patch("subprocess.run", return_value=_cp(stdout=stdout)):
            entries = pl.list_entries("https://youtube.com/@x")
        assert len(entries) == 2
        assert entries[0]["id"] == "a"
        assert entries[0]["duration"] == 125
        assert entries[1]["id"] == "b"

    def test_skips_blank_lines(self):
        stdout = b'{"id": "a"}\n\n{"id": "b"}\n'
        with mock.patch("subprocess.run", return_value=_cp(stdout=stdout)):
            entries = pl.list_entries("u")
        assert len(entries) == 2

    def test_flat_playlist_flag(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _cp(stdout=b"")

        with mock.patch("subprocess.run", side_effect=fake_run):
            pl.list_entries("u", flat=True, limit=5)
        assert "--flat-playlist" in captured["cmd"]
        assert "--playlist-end" in captured["cmd"]

    def test_nonzero_returncode(self):
        with mock.patch("subprocess.run",
                        return_value=_cp(returncode=1, stderr=b"falhou")):
            with pytest.raises(RuntimeError, match="Falha ao listar"):
                pl.list_entries("u")

    def test_empty(self):
        with mock.patch("subprocess.run", return_value=_cp(stdout=b"")):
            assert pl.list_entries("u") == []
