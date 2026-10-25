"""Configuracao de logging estruturado (JSON) do RWX YTManager.

Atende ao RNF.11 (Monitoramento e Logs):
- Logs estruturados em JSON.
- Niveis de severidade padronizados (INFO, WARN, ERROR, FATAL).
- ID de correlacao por execucao (correlation_id).
- Saida para stderr e arquivo rotativo (retencao).
- Compativel com ambientes sem sistema de arquivos (Cloud Run/Lambda).
"""

import json
import logging
import logging.handlers
import os
import uuid

# Mapeamento para os 4 niveis exigidos pelo RNF.11
_SEVERITY = {
    logging.DEBUG: "INFO",
    logging.INFO: "INFO",
    logging.WARNING: "WARN",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "FATAL",
}


def _is_serverless():
    env_markers = (
        "K_SERVICE",
        "FUNCTION_NAME",
        "AWS_LAMBDA_FUNCTION_NAME",
        "GAE_ENV",
    )
    return any(k in os.environ for k in env_markers)


class JsonFormatter(logging.Formatter):
    """Formata registros de log como JSON de uma linha."""

    def __init__(self, correlation_id=None, service="rwx-ytmanager"):
        super().__init__()
        self.correlation_id = correlation_id
        self.service = service

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "severity": _SEVERITY.get(record.levelno, record.levelname),
            "level_no": record.levelno,
            "logger": record.name,
            "service": self.service,
            "correlation_id": getattr(record, "correlation_id", self.correlation_id),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # inclui campos passados via extra_* no log
        for key, val in record.__dict__.items():
            if key.startswith("extra_"):
                payload[key[len("extra_"):]] = val
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(correlation_id=None, log_file=None, level=None, service="rwx-ytmanager"):
    """Configura o logger raiz. Retorna (logger, correlation_id)."""
    correlation_id = correlation_id or str(uuid.uuid4())
    level = level or os.environ.get("YTMANAGER_LOG_LEVEL", "INFO").upper()
    level_value = getattr(logging, level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level_value)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = JsonFormatter(correlation_id=correlation_id, service=service)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    root.addHandler(stream)

    if not _is_serverless():
        path = log_file or os.environ.get("YTMANAGER_LOG_FILE")
        if not path:
            cache = os.path.join(os.path.expanduser("~"), ".cache", service)
            try:
                os.makedirs(cache, exist_ok=True)
                path = os.path.join(cache, "ytmanager.log")
            except OSError:
                path = None
        if path:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                fh = logging.handlers.RotatingFileHandler(path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
                fh.setFormatter(fmt)
                root.addHandler(fh)
            except OSError:
                pass

    return root, correlation_id


def get_logger(name="rwx-ytmanager"):
    return logging.getLogger(name)
