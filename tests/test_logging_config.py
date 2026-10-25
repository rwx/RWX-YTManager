"""Testes de ytmanager.logging_config (RNF.11)."""

import io
import json
import logging

from ytmanager import logging_config as lc


class TestJsonFormatter:
    def _record(self, msg="teste", level=logging.INFO, **extra):
        rec = logging.LogRecord(
            name="test", level=level, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None)
        for k, v in extra.items():
            setattr(rec, k, v)
        return rec

    def test_basic_json(self):
        fmt = lc.JsonFormatter(correlation_id="cid-123")
        out = fmt.format(self._record("ola"))
        data = json.loads(out)
        assert data["message"] == "ola"
        assert data["correlation_id"] == "cid-123"
        assert data["severity"] == "INFO"
        assert data["service"] == "rwx-ytmanager"

    def test_severity_mapping(self):
        fmt = lc.JsonFormatter()
        cases = {
            logging.INFO: "INFO",
            logging.WARNING: "WARN",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "FATAL",
        }
        for level, expected in cases.items():
            data = json.loads(fmt.format(self._record(level=level)))
            assert data["severity"] == expected

    def test_extra_fields(self):
        fmt = lc.JsonFormatter()
        rec = self._record()
        rec.extra_command = "info"
        rec.extra_url = "https://x"
        data = json.loads(fmt.format(rec))
        assert data["command"] == "info"
        assert data["url"] == "https://x"

    def test_record_correlation_overrides(self):
        fmt = lc.JsonFormatter(correlation_id="default")
        rec = self._record()
        rec.correlation_id = "override"
        data = json.loads(fmt.format(rec))
        assert data["correlation_id"] == "override"


class TestSetupLogging:
    def test_returns_correlation_id(self):
        logger, cid = lc.setup_logging(service="test-svc")
        assert cid
        assert isinstance(cid, str)
        assert len(cid) > 10

    def test_generates_unique_ids(self):
        _, a = lc.setup_logging(service="test-svc")
        _, b = lc.setup_logging(service="test-svc")
        assert a != b

    def test_uses_provided_id(self):
        _, cid = lc.setup_logging(correlation_id="fixed-id", service="test-svc")
        assert cid == "fixed-id"

    def test_writes_json_to_stream(self):
        logger, _ = lc.setup_logging(service="test-svc")
        buf = io.StringIO()
        for h in logging.getLogger().handlers:
            if isinstance(h, logging.StreamHandler):
                h.stream = buf
        logger.info("mensagem de teste")
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        assert lines
        data = json.loads(lines[-1])
        assert data["message"] == "mensagem de teste"


class TestIsServerless:
    def test_detects_cloud_run(self, monkeypatch):
        monkeypatch.setenv("K_SERVICE", "svc")
        assert lc._is_serverless() is True

    def test_detects_lambda(self, monkeypatch):
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "fn")
        assert lc._is_serverless() is True

    def test_local_not_serverless(self, monkeypatch):
        for k in ("K_SERVICE", "FUNCTION_NAME",
                  "AWS_LAMBDA_FUNCTION_NAME", "GAE_ENV"):
            monkeypatch.delenv(k, raising=False)
        assert lc._is_serverless() is False


class TestGetLogger:
    def test_returns_logger(self):
        lg = lc.get_logger("meu.logger")
        assert isinstance(lg, logging.Logger)
        assert lg.name == "meu.logger"
