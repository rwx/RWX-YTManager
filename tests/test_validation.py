"""Testes de ytmanager.validation (RNF.08 - entrada, RNF.09 - seguranca)."""

from unittest import mock

import pytest

from ytmanager import cli
from ytmanager import validation as val
from ytmanager.errors import YtManagerError


class TestHostMatching:
    def test_exact_host(self):
        assert val.is_youtube_host("youtube.com")

    def test_subdomain(self):
        assert val.is_youtube_host("www.youtube.com")
        assert val.is_youtube_host("m.youtube.com")

    def test_youtu_be(self):
        assert val.is_youtube_host("youtu.be")

    def test_nocookie(self):
        assert val.is_youtube_host("www.youtube-nocookie.com")

    @pytest.mark.parametrize("evil", [
        "youtu.be.evil.com",      # furo classico do 'in host'
        "evil.com",
        "notyoutube.com",
        "youtube.com.evil.com",
        "youtube.co",
        "",
    ])
    def test_rejects_lookalikes(self, evil):
        assert val.is_youtube_host(evil) is False


class TestValidateUrl:
    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=gGmb70z3iYU",
        "https://youtu.be/gGmb70z3iYU",
        "http://youtube.com/watch?v=x",
        "https://m.youtube.com/watch?v=x",
        "https://www.youtube.com/shorts/abc",
        "  https://youtu.be/abc  ",
    ])
    def test_accepts_youtube_urls(self, url):
        assert val.validate_url(url)

    def test_normalizes_http_to_https(self):
        out = val.validate_url("http://www.youtube.com/watch?v=x")
        assert out.startswith("https://")

    def test_strips_whitespace(self):
        out = val.validate_url("   https://youtu.be/abc   ")
        assert out == "https://youtu.be/abc"

    @pytest.mark.parametrize("url", [None, "", "   "])
    def test_rejects_empty(self, url):
        with pytest.raises(YtManagerError, match="Nenhuma URL"):
            val.validate_url(url)

    def test_rejects_too_long(self):
        url = "https://youtu.be/" + "a" * val.MAX_URL_LENGTH
        with pytest.raises(YtManagerError, match="longa demais"):
            val.validate_url(url)

    @pytest.mark.parametrize("url", [
        "ftp://youtube.com/x",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "//youtube.com/x",
    ])
    def test_rejects_bad_scheme(self, url):
        with pytest.raises(YtManagerError):
            val.validate_url(url)

    @pytest.mark.parametrize("url", [
        "https://evil.com/watch?v=x",
        "https://youtu.be.evil.com/x",
        "https://notyoutube.com/watch?v=x",
    ])
    def test_rejects_non_youtube_host(self, url):
        with pytest.raises(YtManagerError, match="nao pertence ao YouTube"):
            val.validate_url(url)

    def test_rejects_control_chars(self):
        with pytest.raises(YtManagerError, match="caracteres invalidos"):
            val.validate_url("https://youtu.be/abc\nrm -rf /")


class TestVideoId:
    def test_valid_id(self):
        assert val.is_valid_video_id("gGmb70z3iYU")
        assert val.is_valid_video_id("_-abcDEF123")

    @pytest.mark.parametrize("bad", ["", None, "abc", "a" * 12,
                                     "abc def ghi", "abc!defghi"])
    def test_invalid_id(self, bad):
        assert val.is_valid_video_id(bad) is False

    def test_validate_video_id_raises(self):
        with pytest.raises(YtManagerError, match="ID de video valido"):
            val.validate_video_id("curto")

    def test_validate_video_id_ok(self):
        assert val.validate_video_id("gGmb70z3iYU") == "gGmb70z3iYU"


class TestSafeOutputName:
    def test_normal(self):
        assert val.safe_output_name("meu-video") == "meu-video"

    @pytest.mark.parametrize("path", [
        "../../etc/passwd",
        "/etc/passwd",
        "..\\..\\windows\\system32",
        "sub/dir/file",
    ])
    def test_strips_directories(self, path):
        out = val.safe_output_name(path)
        assert "/" not in out
        assert "\\" not in out

    def test_removes_nul(self):
        assert "\x00" not in val.safe_output_name("a\x00b")

    def test_replaces_special_chars(self):
        out = val.safe_output_name("a|b;c&d")
        assert "|" not in out and ";" not in out and "&" not in out

    @pytest.mark.parametrize("bad", ["", "   ", ".", ".."])
    def test_fallback_on_empty(self, bad):
        assert val.safe_output_name(bad) == "video"

    def test_custom_fallback(self):
        assert val.safe_output_name("..", fallback="x") == "x"

    def test_truncates_long(self):
        assert len(val.safe_output_name("a" * 500)) <= 200


class TestEnsureArgList:
    def test_list_ok(self):
        assert val.ensure_arg_list(["a", "b"]) == ["a", "b"]

    def test_tuple_ok(self):
        assert val.ensure_arg_list(("a", "b")) == ["a", "b"]

    @pytest.mark.parametrize("bad", ["cmd --x", b"bytes"])
    def test_rejects_string(self, bad):
        with pytest.raises(YtManagerError, match="seguranca"):
            val.ensure_arg_list(bad)

    def test_rejects_non_string_items(self):
        with pytest.raises(YtManagerError, match="seguranca"):
            val.ensure_arg_list(["a", 123])


class TestSafeCliUrl:
    def test_valid(self):
        assert val.safe_cli_url("https://youtu.be/abc")

    def test_rejects_traversal_out_dir(self):
        with pytest.raises(YtManagerError, match="diretorio"):
            val.safe_cli_url("https://youtu.be/abc", out_dir="../../etc")


class TestCLIValidationIntegration:
    """A validacao deve barrar URLs invalidas antes de qualquer comando."""

    @pytest.mark.parametrize("command", ["info", "subs", "playlist",
                                         "transcript", "video"])
    def test_invalid_url_rejected_for_all_commands(self, command):
        with mock.patch("ytmanager.metadata.fetch_oembed") as m:
            code = cli.main([command, "https://evil.com/watch?v=x"])
        assert code == 1
        # nenhum acesso externo deve ter ocorrido
        m.assert_not_called()

    def test_url_normalized_passed_to_command(self):
        captured = {}

        def fake(url, **kwargs):
            captured["url"] = url
            return {"id": "abc", "title": "T"}

        with mock.patch("ytmanager.metadata.fetch_oembed", side_effect=fake):
            cli.main(["info", "http://youtu.be/abc"])
        # http foi normalizado para https
        assert captured["url"].startswith("https://")
