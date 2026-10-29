"""Testes de ytmanager.metadata (funcoes puras e com mock)."""

import json
import subprocess
from unittest import mock

import pytest

from ytmanager import metadata as md


class TestExtractVideoId:
    def test_watch_url(self):
        assert md.extract_video_id(
            "https://www.youtube.com/watch?v=gGmb70z3iYU") == "gGmb70z3iYU"

    def test_short_url(self):
        assert md.extract_video_id("https://youtu.be/-s15mEx_Xsw") == "-s15mEx_Xsw"

    def test_short_url_with_query(self):
        assert md.extract_video_id(
            "https://youtu.be/-s15mEx_Xsw?si=abc123") == "-s15mEx_Xsw"

    def test_embed_url(self):
        assert md.extract_video_id(
            "https://www.youtube.com/embed/ABC123") == "ABC123"

    def test_shorts_url(self):
        assert md.extract_video_id(
            "https://www.youtube.com/shorts/XYZ789") == "XYZ789"

    def test_live_url(self):
        assert md.extract_video_id(
            "https://www.youtube.com/live/LIVE01") == "LIVE01"

    def test_no_id(self):
        assert md.extract_video_id("https://www.youtube.com/") is None


class TestFormatDuration:
    def test_none(self):
        assert md._format_duration(None) is None

    def test_zero(self):
        assert md._format_duration(0) is None

    def test_seconds_only(self):
        assert md._format_duration(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert md._format_duration(125) == "2:05"

    def test_hours(self):
        assert md._format_duration(7337) == "2:02:17"

    def test_string_input(self):
        assert md._format_duration("125") == "2:05"


class TestFormatDate:
    def test_none(self):
        assert md._format_date(None) is None

    def test_valid(self):
        assert md._format_date("20260806") == "2026-08-06"

    def test_invalid_length(self):
        assert md._format_date("2026") == "2026"


class TestFetchOembed:
    def _mock_response(self, payload):
        resp = mock.MagicMock()
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.__enter__ = mock.MagicMock(return_value=resp)
        resp.__exit__ = mock.MagicMock(return_value=False)
        return resp

    def test_success(self):
        payload = {
            "title": "Titulo",
            "author_name": "Canal",
            "author_url": "https://youtube.com/@canal",
            "thumbnail_url": "https://img/thumb.jpg",
            "provider_name": "YouTube",
        }
        with mock.patch("urllib.request.urlopen",
                        return_value=self._mock_response(payload)):
            data = md.fetch_oembed("https://youtu.be/gGmb70z3iYU")
        assert data["id"] == "gGmb70z3iYU"
        assert data["title"] == "Titulo"
        assert data["author"] == "Canal"
        assert data["provider"] == "YouTube"

    def test_http_error(self):
        import urllib.error
        err = urllib.error.HTTPError("url", 400, "Bad", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(RuntimeError, match="nao parece ser valida"):
                md.fetch_oembed("https://youtu.be/x")

    def test_network_error(self):
        import urllib.error
        err = urllib.error.URLError("sem rede")
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(RuntimeError, match="conectar ao YouTube"):
                md.fetch_oembed("https://youtu.be/x")


class TestFetchFullMetadata:
    def _completed(self, returncode=0, stdout=b"", stderr=b""):
        return subprocess.CompletedProcess(args=[], returncode=returncode,
                                           stdout=stdout, stderr=stderr)

    def test_success(self):
        raw = {
            "id": "abc", "title": "T", "uploader": "U", "duration": 125,
            "view_count": 10, "upload_date": "20260101",
            "subtitles": {"en": [{"ext": "vtt"}]},
            "automatic_captions": {"pt": [{}], "en": [{}]},
        }
        cp = self._completed(stdout=json.dumps(raw).encode())
        with mock.patch("subprocess.run", return_value=cp):
            data = md.fetch_full_metadata("https://youtu.be/abc")
        assert data["id"] == "abc"
        assert data["duration_string"] == "2:05"
        assert data["upload_date"] == "2026-01-01"
        assert data["subtitles"] == {"en": ["vtt"]}
        assert set(data["automatic_captions"]) == {"pt", "en"}

    def test_yt_dlp_not_found(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="yt-dlp nao foi encontrado"):
                md.fetch_full_metadata("https://youtu.be/x")

    def test_nonzero_returncode(self):
        cp = self._completed(returncode=1, stderr=b"erro do yt-dlp")
        with mock.patch("subprocess.run", return_value=cp):
            with pytest.raises(RuntimeError, match="obter os metadados"):
                md.fetch_full_metadata("https://youtu.be/x")

    def test_empty_output(self):
        cp = self._completed(stdout=b"")
        with mock.patch("subprocess.run", return_value=cp):
            with pytest.raises(RuntimeError, match="nao retornou metadados"):
                md.fetch_full_metadata("https://youtu.be/x")
