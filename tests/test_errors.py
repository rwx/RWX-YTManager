"""Testes do tratamento de erros amigaveis (RNF.10)."""

from unittest import mock

import pytest

from ytmanager import cli
from ytmanager.errors import (HINT_URL, HINT_YTDLP, YtManagerError,
                              friendly_http_message)


class TestYtManagerError:
    def test_is_runtime_error(self):
        # compatibilidade: continua sendo RuntimeError
        assert issubclass(YtManagerError, RuntimeError)

    def test_message_without_hint(self):
        err = YtManagerError("algo falhou")
        assert err.user_message() == "Erro: algo falhou"

    def test_message_with_hint(self):
        err = YtManagerError("falhou", hint="tente de novo")
        msg = err.user_message()
        assert "Erro: falhou" in msg
        assert "Dica: tente de novo" in msg

    def test_detail_not_in_user_message(self):
        err = YtManagerError("erro amigavel", hint="dica",
                             detail="TRACEBACK_INTERNO_CHEIO_DE_JARGAO")
        msg = err.user_message()
        assert "TRACEBACK_INTERNO" not in msg
        assert err.detail == "TRACEBACK_INTERNO_CHEIO_DE_JARGAO"

    def test_str_is_message(self):
        assert str(YtManagerError("texto")) == "texto"


class TestFriendlyHttpMessage:
    @pytest.mark.parametrize("code,esperado", [
        (400, "nao parece ser valida"),
        (403, "bloqueado"),
        (404, "nao foi encontrado"),
        (429, "Muitas solicitacoes"),
        (500, "problema interno"),
        (503, "indisponivel"),
    ])
    def test_known_codes(self, code, esperado):
        assert esperado in friendly_http_message(code)

    def test_unknown_code(self):
        msg = friendly_http_message(418)
        assert "HTTP 418" in msg


class TestCliErrorHandlingRNF10:
    def test_friendly_message_printed(self, capsys):
        err = YtManagerError("Video nao encontrado.",
                             hint="Confira a URL.",
                             detail="HTTP 404 interno")
        with mock.patch("ytmanager.metadata.fetch_oembed", side_effect=err):
            code = cli.main(["info", "https://youtu.be/x"])
        assert code == 1
        captured = capsys.readouterr().err
        # isola apenas as linhas de mensagem ao usuario (nao os logs JSON)
        linhas_msg = [l for l in captured.splitlines()
                      if not l.strip().startswith("{")]
        texto = "\n".join(linhas_msg)
        # mensagem amigavel + dica presentes
        assert "Video nao encontrado." in texto
        assert "Dica: Confira a URL." in texto
        # detalhe tecnico NAO vaza para a mensagem do usuario
        assert "HTTP 404 interno" not in texto

    def test_stable_state_after_error(self, capsys):
        # apos um erro, uma segunda chamada deve funcionar normalmente
        with mock.patch("ytmanager.metadata.fetch_oembed",
                        side_effect=YtManagerError("falhou")):
            code1 = cli.main(["info", "https://youtu.be/x"])
        assert code1 == 1

        with mock.patch("ytmanager.metadata.fetch_oembed",
                        return_value={"id": "abc", "title": "T"}):
            code2 = cli.main(["info", "https://youtu.be/x"])
        assert code2 == 0

    def test_error_is_logged_with_detail(self, capsys):
        import json
        err = YtManagerError("msg amigavel", hint="dica", detail="DETALHE_TECNICO")
        with mock.patch("ytmanager.metadata.fetch_oembed", side_effect=err):
            cli.main(["info", "https://youtu.be/x"])
        stderr = capsys.readouterr().err
        # procura um log JSON de ERROR que contenha o detail tecnico
        logs = [json.loads(l) for l in stderr.splitlines()
                if l.strip().startswith("{")]
        erros = [d for d in logs if d.get("severity") == "ERROR"]
        assert erros, "esperava um log de ERROR"
        assert any(d.get("detail") == "DETALHE_TECNICO" for d in erros)


class TestCmdVideoCLI:
    def test_success(self, tmp_path, capsys):
        path = str(tmp_path / "video.mp4")
        with mock.patch("ytmanager.download.download_video",
                        return_value=path) as m:
            open(path, "w").close()
            code = cli.main(["video", "https://youtu.be/x",
                             "--out", str(tmp_path), "--format", "mp4"])
        assert code == 0
        m.assert_called_once()
        assert "Video salvo" in capsys.readouterr().out

    def test_format_passed_as_string(self, tmp_path):
        # regressao: --format do video nao deve virar lista
        captured = {}

        def fake(url, out_dir=None, fmt="mp4", quality=None, ytdlp_path="yt-dlp"):
            captured["fmt"] = fmt
            path = str(tmp_path / ("video." + fmt))
            open(path, "w").close()
            return path

        with mock.patch("ytmanager.download.download_video", side_effect=fake):
            code = cli.main(["video", "https://youtu.be/abc", "--out", str(tmp_path),
                             "--format", "mkv"])
        assert code == 0
        assert captured["fmt"] == "mkv"

    def test_invalid_format_argument(self):
        with pytest.raises(SystemExit):
            cli.main(["video", "https://youtu.be/abc", "--format", "avi"])

    def test_download_error_returns_1(self, tmp_path, capsys):
        with mock.patch("ytmanager.download.download_video",
                        side_effect=YtManagerError("Nao foi possivel baixar.",
                                                   hint=HINT_URL)):
            code = cli.main(["video", "https://youtu.be/abc", "--out", str(tmp_path)])
        assert code == 1
        assert "Nao foi possivel baixar." in capsys.readouterr().err
