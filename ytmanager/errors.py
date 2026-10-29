"""Tratamento de erros amigaveis e informativos (RNF.10).

Define uma excecao estruturada YtManagerError que separa:
- message: mensagem amigavel, sem jargao tecnico (vai para o usuario).
- hint: acao corretiva sugerida (vai para o usuario).
- detail: detalhe tecnico (vai apenas para o log, nao para o usuario).

Assim o usuario recebe texto claro e acionavel, enquanto o log mantem o
detalhe para debug. O CLI permanece estavel apos o erro (retorna exit code).
"""


class YtManagerError(RuntimeError):
    """Erro esperado da aplicacao, com mensagem amigavel e dica de acao.

    Falhas criticas devem ser levantadas como YtManagerError para que o CLI
    exiba uma mensagem amigavel e informativa e retorne um codigo de saida
    estavel (1).
    """

    def __init__(self, message, hint=None, detail=None):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.detail = detail

    def user_message(self):
        """Mensagem amigavel e informativa para o usuario final.

        Inclui a dica corretiva (se houver) e NUNCA inclui o detalhe tecnico.
        """
        base = "Erro: %s" % self.message
        if self.hint:
            base += "\nDica: %s" % self.hint
        return base

    def __str__(self):
        return self.message


# Dicas de acao corretiva reutilizaveis
HINT_URL = ("Verifique se a URL e de um video, playlist ou canal do YouTube "
            "acessivel publicamente (ex.: https://www.youtube.com/watch?v=ID).")
HINT_YTDLP = ("Confirme que o yt-dlp esta instalado e atualizado: rode "
              "install.sh ou ./.venv/bin/pip install -U yt-dlp.")
HINT_NETWORK = ("Verifique sua conexao com a internet e tente novamente em "
                "alguns instantes.")
HINT_SUBS = ("O video pode nao ter legendas. Tente outra legenda (--lang) ou "
             "use transcricao por IA com --whisper.")
HINT_FFMPEG = ("Instale o ffmpeg (ex.: apt install ffmpeg) para usar a "
               "transcricao por IA.")
HINT_WHISPER = ("Instale um backend de transcricao: pip install faster-whisper "
                "av==13.0.0 (veja o README).")

# Mapeamento HTTP -> mensagem amigavel
_HTTP_MESSAGES = {
    400: "A URL informada nao parece ser valida para o YouTube.",
    401: "O acesso a este recurso foi negado (nao autorizado).",
    403: "O acesso a este video foi bloqueado pelo YouTube.",
    404: "O video nao foi encontrado (pode ter sido removido ou ser privado).",
    410: "O video nao esta mais disponivel.",
    429: "Muitas solicitacoes em pouco tempo. Aguarde e tente novamente.",
    500: "O servico do YouTube apresentou um problema interno.",
    503: "O servico do YouTube esta indisponivel no momento.",
}


def friendly_http_message(code):
    """Traduz um codigo HTTP em mensagem amigavel."""
    return _HTTP_MESSAGES.get(code,
                              "O servico respondeu com um erro inesperado (HTTP %s)."
                              % code)
