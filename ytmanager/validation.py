"""Validacao de entrada e controles de seguranca (RNF.08 e RNF.09).

RNF.08 - Validacao de Entrada:
- Rejeita URLs vazias, longas demais, com scheme invalido ou host nao-YouTube.
- Aceita apenas hosts de uma allowlist (match exato ou subdominio legitimo).
- Valida o ID do video e normaliza a URL.

RNF.09 - Seguranca:
- Garante que comandos de subprocess sejam listas (nunca string com shell),
  prevenindo injecao de comandos.
- Sanitiza nomes de arquivo (sem path traversal, sem caracteres perigosos).
- Aplica limite de tamanho na URL para evitar abuso.
"""

import os
import re
import urllib.parse

from .errors import HINT_URL, YtManagerError

# Hosts oficiais do YouTube (allowlist).
# O match e exato ou subdominio legitimo (ex.: www.youtube.com, m.youtube.com).
YOUTUBE_HOSTS = (
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
)

# Limite defensivo de tamanho da URL (evita abuso / payloads gigantes).
MAX_URL_LENGTH = 2048

# Um ID de video do YouTube tem 11 caracteres (letras, numeros, - e _).
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _host_matches(host, allowed):
    """True se host == allowed ou for subdominio legitimo de allowed.

    Evita o furo de 'in host': 'youtu.be.evil.com' NAO casa com 'youtu.be'.
    """
    host = (host or "").lower().rstrip(".")
    if not host:
        return False
    if host == allowed:
        return True
    return host.endswith("." + allowed)


def is_youtube_host(host):
    """Verifica se o host pertence ao YouTube (allowlist)."""
    return any(_host_matches(host, allowed) for allowed in YOUTUBE_HOSTS)


def validate_url(url):
    """Valida e normaliza uma URL do YouTube (RNF.08).

    Retorna a URL normalizada (scheme https forcado, sem espacos).

    Raises:
        YtManagerError: se a URL for vazia, longa demais, nao-http(s) ou
        de um host que nao seja do YouTube.
    """
    if url is None or not str(url).strip():
        raise YtManagerError(
            "Nenhuma URL foi informada.",
            hint=HINT_URL,
            detail="url vazia ou None",
        )

    url = str(url).strip()

    if len(url) > MAX_URL_LENGTH:
        raise YtManagerError(
            "A URL informada e longa demais.",
            hint=HINT_URL,
            detail="tamanho %d > limite %d" % (len(url), MAX_URL_LENGTH),
        )

    # Rejeita caracteres de controle / quebra de linha (defesa contra injection)
    if any(ord(c) < 32 for c in url):
        raise YtManagerError(
            "A URL contem caracteres invalidos.",
            hint=HINT_URL,
            detail="caracteres de controle detectados",
        )

    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise YtManagerError(
            "A URL deve comecar com http:// ou https://.",
            hint=HINT_URL,
            detail="scheme invalido: %r" % scheme,
        )

    host = (parsed.hostname or "").lower()
    if not is_youtube_host(host):
        raise YtManagerError(
            "A URL nao pertence ao YouTube.",
            hint=HINT_URL,
            detail="host nao permitido: %r" % host,
        )

    # Normaliza para https (seguranca: evita downgrade para http)
    if scheme == "http":
        parsed = parsed._replace(scheme="https")
        url = urllib.parse.urlunparse(parsed)

    return url


def is_valid_video_id(video_id):
    """True se o ID tem o formato esperado de um video do YouTube."""
    return bool(video_id and VIDEO_ID_RE.match(video_id))


def validate_video_id(video_id):
    """Valida o ID do video, levantando YtManagerError se invalido."""
    if not is_valid_video_id(video_id):
        raise YtManagerError(
            "Nao foi possivel identificar um ID de video valido na URL.",
            hint=HINT_URL,
            detail="video_id invalido: %r" % video_id,
        )
    return video_id


def safe_output_name(name, fallback="video"):
    """Sanitiza um nome de arquivo base (RNF.09).

    - Remove separadores de caminho (impede path traversal: ../, /, barra).
    - Remove caracteres perigosos para o sistema de arquivos.
    - Garante que o resultado nunca seja vazio nem '.'/'..'.
    """
    name = str(name or "").strip()
    # descarta qualquer componente de diretorio
    name = name.replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "")
    name = re.sub(r"[^\w\-. ]+", "_", name, flags=re.UNICODE)
    name = name.strip(" .")
    if name in ("", ".", ".."):
        return fallback
    return name[:200]


def ensure_arg_list(args):
    """Garante que argumentos de subprocess sejam uma lista de strings (RNF.09).

    Nunca permite string solta (que, com shell=True, poderia permitir
    injecao de comandos). Use sempre listas com subprocess.run(cmd).
    """
    if isinstance(args, (str, bytes)):
        raise YtManagerError(
            "Erro interno de seguranca: comando malformado.",
            hint="Este e um bug; reporte mantendo o correlation_id do log.",
            detail="argumentos de subprocess nao podem ser string",
        )
    if not all(isinstance(a, str) for a in args):
        raise YtManagerError(
            "Erro interno de seguranca: comando malformado.",
            hint="Este e um bug; reporte mantendo o correlation_id do log.",
            detail="argumentos nao-string em subprocess",
        )
    return list(args)


def safe_cli_url(url, out_dir=None):
    """Compat helper: valida URL e opcionalmente o diretorio de saida.

    Nao cria diretorios; apenas valida o caminho contra traversal obvio.
    """
    url = validate_url(url)
    if out_dir is not None and (".." in str(out_dir).split(os.sep)):
        raise YtManagerError(
            "O diretorio de saida informado e invalido.",
            hint="Use um caminho de diretorio simples, sem '..'.",
            detail="out_dir suspeito: %r" % out_dir,
        )
    return url
