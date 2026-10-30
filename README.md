# RWX YTManager

**Versao:** 0.1.0 | **Licenca:** MIT | **Linguagem:** Python 3.8+

CLI em Python para extrair conteudo do YouTube: metadados, legendas
(automaticas/manuais) e transcricao por IA (Whisper). Roda inteiramente no
terminal, sem interface grafica.

Desenvolvido por **RWX Solucoes Inteligentes**.

---

## Sumario

- [Escopo e nao aplicabilidade](#escopo-e-nao-aplicabilidade)
- [Instalacao](#instalacao)
- [Manual do Aplicativo](#manual-do-aplicativo)
- [Configuracao e customizacao](#configuracao-e-customizacao)
- [Estrategia de extracao](#estrategia-de-extracao)
- [Limitacoes e cuidados](#limitacoes-e-cuidados)
- [Dicionario de arquivos](#dicionario-de-arquivos)
- [Testes](#testes)
- [Validacao de entrada e seguranca](#validacao-de-entrada-e-seguranca)
- [Tratamento de erros](#tratamento-de-erros)
- [Changelog](#changelog)
- [Desenvolvedor](#desenvolvedor)

---

## Escopo e nao aplicabilidade

Este projeto e uma **ferramenta de linha de comando (CLI)** em Python. Por essa
natureza, alguns requisitos tipicos de aplicacoes web **nao se aplicam** e sao
aqui registrados explicitamente para fins de conformidade:

| Requisito | Situacao | Motivo |
|---|---|---|
| App web responsivo (celular/tablet/PC) | Nao aplicavel | Nao ha frontend/interface web |
| Desenvolvido em TypeScript | Divergente (documentado) | Decisao de escopo: Python |
| Acessibilidade WCAG / layout no browser | Nao aplicavel | Sem interface no navegador |
| FCP em 3G / metricas de browser | Nao aplicavel | Sem pagina web |
| Container / orquestracao / serverless | Nao implementado | Projeto local; ver roadmap |

---

## Instalacao

Requisitos:

- Python 3.8 ou superior
- ffmpeg (somente para o modo --whisper)

Clone o repositorio e execute o instalador:

    cd RWX-YTManager
    bash install.sh

O instalador cria um ambiente virtual local (.venv) e instala o yt-dlp.

### Transcricao por IA (opcional)

Para transcrever o audio (quando nao ha legenda, ou para maior precisao),
instale o ffmpeg e um backend Whisper (ver requirements.txt). Exemplo:

    source .venv/bin/activate
    pip install -r requirements.txt

> Nota (Python 3.13): versoes recentes do pacote av (19.x) falham com
> 'TypeError: open() got an unexpected keyword argument metadata_errors'.
> O requirements.txt fixa av==13.0.0 para evitar esse bug.

---

## Manual do Aplicativo

O ytmanager possui quatro comandos. A forma geral e:

    ./bin/ytmanager <comando> <URL> [opcoes]

### info - metadados do video

    ./bin/ytmanager info URL            # basico (oEmbed: titulo, autor, thumb)
    ./bin/ytmanager info URL --full     # completo (duracao, views, descricao, capitulos)
    ./bin/ytmanager info URL --json     # saida JSON

### subs - idiomas de legenda disponiveis

    ./bin/ytmanager subs URL

### transcript - extracao de transcricao

    ./bin/ytmanager transcript URL                                  # padrao: legenda, pt, txt+md
    ./bin/ytmanager transcript URL --lang en                        # outro idioma
    ./bin/ytmanager transcript URL --format txt,json,md --out ./saida
    ./bin/ytmanager transcript URL --whisper --whisper-model medium # forca IA no audio
    ./bin/ytmanager transcript URL --whisper-fallback               # IA so se nao houver legenda

Opcoes de transcript:

| Opcao | Padrao | Descricao |
|---|---|---|
| --lang | pt | Idioma da legenda/transcricao |
| --no-auto | desligado | Nao usar legenda automatica (so manual) |
| --whisper | desligado | Forcar transcricao via Whisper |
| --whisper-fallback | desligado | Usar Whisper apenas se nao houver legenda |
| --whisper-model | medium | tiny, base, small, medium, large-v3 |
| --format | txt,md | Formatos de saida (txt, json, md) |
| --out | . | Diretorio de saida |

### playlist - videos de playlists e canais

    ./bin/ytmanager playlist URL --limit 50
    ./bin/ytmanager playlist URL --json --out ./saida

### video - baixa o video em mp4/mkv/webm

Baixa o video (com audio) e converte/junta para o formato pedido. Requer
ffmpeg instalado (usado pelo yt-dlp para juntar video e audio).

    ./bin/ytmanager video URL                          # mp4, melhor qualidade
    ./bin/ytmanager video URL --format mkv             # container mkv
    ./bin/ytmanager video URL --format webm --quality 720
    ./bin/ytmanager video URL --quality 1080 --out ./videos

| Opcao | Padrao | Descricao |
|---|---|---|
| --format | mp4 | Container de saida: mp4, mkv ou webm |
| --quality | best | Altura maxima (ex.: 1080, 720). Use best para o melhor |
| --out | temporario | Diretorio de saida |

---

## Configuracao e customizacao

Ajustes disponiveis e como faze-los:

### 1. Caminho do yt-dlp

Por padrao usa-se o yt-dlp do venv. Para apontar outro binario:

    # via variavel de ambiente
    export YTDLP_PATH=/caminho/para/yt-dlp
    ./bin/ytmanager info URL

    # ou por linha de comando
    ./bin/ytmanager --ytdlp /caminho/para/yt-dlp info URL

### 2. Idioma padrao

O idioma padrao e pt. Para extrair em ingles:

    ./bin/ytmanager transcript URL --lang en

### 3. Modelo Whisper

Modelos maiores sao mais precisos e mais lentos:

    # rapido, menor qualidade
    ./bin/ytmanager transcript URL --whisper --whisper-model tiny

    # equilibrado (padrao)
    ./bin/ytmanager transcript URL --whisper --whisper-model medium

    # alta qualidade (exige mais RAM/CPU/GPU)
    ./bin/ytmanager transcript URL --whisper --whisper-model large-v3

### 4. Diretorio e formato de saida

    ./bin/ytmanager transcript URL --out ./transcricoes --format txt,json

### 5. Nome dos arquivos de saida

Os arquivos sao nomeados a partir do titulo do video (slug automatico). O
slugify fica em ytmanager/output.py e pode ser ajustado (ex: comprimento
maximo, remocao de acentos).

### 6. Logging (monitoramento)

O ytmanager emite logs estruturados em JSON (RNF.11). Cada execucao recebe um
correlation_id unico, presente em todas as linhas. Os logs vao para stderr e,
fora de ambientes serverless, tambem para arquivo rotativo.

Niveis: INFO, WARN, ERROR, FATAL (mapeados internamente). Variaveis de ambiente:

    export YTMANAGER_LOG_LEVEL=DEBUG          # DEBUG, INFO, WARNING, ERROR
    export YTMANAGER_LOG_FILE=/var/log/ytm.log # caminho do arquivo de log

Exemplo de linha de log:

    {"timestamp": "2026-10-24T21:51:22", "severity": "INFO",
     "service": "rwx-ytmanager", "correlation_id": "a50cf280-...",
     "message": "execucao iniciada", "command": "info"}

Por padrao, o arquivo de log fica em ~/.cache/rwx-ytmanager/ytmanager.log.
Em ambientes serverless (Cloud Run, Lambda, App Engine) o arquivo e
desabilitado automaticamente, mantendo apenas a saida para stderr.

---

## Testes

O projeto inclui testes unitarios e de integracao (pytest), cobrindo ~94% do
codigo. Os testes sao rapidos (segundos) e isolados: nao acessam a rede nem o
yt-dlp real (usam mock).

Instalar as dependencias de desenvolvimento:

    source .venv/bin/activate
    pip install -e .[dev]

Executar a suite com cobertura:

    pytest

Rodar um modulo especifico:

    pytest tests/test_metadata.py -v

O pyproject.toml exige cobertura minima de 70% (--cov-fail-under=70).

---

## Validacao de entrada e seguranca

### Validacao da URL (RNF.08)

Toda URL e validada antes de qualquer acesso a rede ou ao yt-dlp:

- Precisa ter scheme `http://` ou `https://` (http e normalizado para https).
- O host precisa estar na allowlist do YouTube: `youtube.com`, `youtu.be`,
  `youtube-nocookie.com` (e seus subdominios legitimos).
- URLs com tamanho excessivo (acima de 2048 caracteres) ou caracteres de
  controle sao rejeitadas.
- Dominios parecidos sao bloqueados (ex.: `youtu.be.evil.com` NAO e aceito).

Se a URL for invalida, o comando e abortado com mensagem amigavel, sem
qualquer chamada de rede.

### Controles de seguranca (RNF.09)

- **Sem injecao de comandos**: todas as chamadas ao `subprocess` usam uma
  lista de argumentos (nunca `shell=True`). As listas passam por
  `ensure_arg_list()`, que rejeita strings soltas.
- **Sanitizacao de nome de arquivo**: nomes gerados a partir do titulo do
  video passam por `safe_output_name()`, que remove separadores de caminho.
  Isso impede path traversal (`../../etc/passwd`) e variantes.
- **Limite de tamanho da URL**: defesa contra payloads gigantes.

---

## Tratamento de erros

As falhas sao reportadas com uma mensagem amigavel (sem jargao tecnico) e uma
dica de acao corretiva. O detalhe tecnico completo vai para o log, nao para a
tela. Apos um erro o programa retorna um codigo de saida estavel (sem quebrar).

Exemplo:

    Erro: O video nao foi encontrado (pode ter sido removido ou ser privado).
    Dica: Verifique se a URL e de um video acessivel publicamente.

Codigos de saida:

| Codigo | Significado |
|---|---|
| 0 | Sucesso |
| 1 | Erro esperado (URL invalida, sem legenda, falha do yt-dlp, etc.) |
| 2 | Erro inesperado (inclui correlation_id para investigacao) |
| 130 | Interrompido pelo usuario (Ctrl+C) |

---

## Estrategia de extracao

1. Legenda manual (enviada pelo autor): melhor qualidade.
2. Legenda automatica (ASR do YouTube): existe para quase todo video, mas
   erra nomes/termos e duplica frases -- por isso limpamos o VTT (removemos
   timestamps, tags e duplicatas).
3. Whisper (IA no audio): melhor precisao, mais lento e pesado. Use
   --whisper-fallback para acionar apenas quando nao houver legenda.
4. Metadados: oEmbed e rapido e sem risco; --full usa o yt-dlp.

---

## Limitacoes e cuidados

- Usa yt-dlp, que contorna a API oficial. Destina-se a uso pessoal/estudo.
  Para produto comercial em escala, utilize a API oficial do YouTube.
- Baixar e redistribuir videos inteiros viola os Termos do YouTube. Aqui
  extraimos apenas texto e metadados.
- Mantenha o yt-dlp atualizado: ./.venv/bin/pip install -U yt-dlp
- Videos sem legenda e sem ffmpeg/Whisper nao podem ser transcritos.

---

## Dicionario de arquivos

| Arquivo | Finalidade |
|---|---|
| bin/ytmanager | Atalho executavel; resolve venv, PYTHONPATH e o binario yt-dlp. |
| ytmanager/__init__.py | Define a versao do pacote (__version__). |
| ytmanager/__main__.py | Permite python -m ytmanager; delega para cli.main. |
| ytmanager/cli.py | Interface de linha de comando; parser argparse e orquestracao. |
| ytmanager/metadata.py | Metadados do video: oEmbed e yt-dlp --dump-json. |
| ytmanager/subtitles.py | Download de legendas (manual/automatica) e limpeza do VTT. |
| ytmanager/transcribe.py | Download de audio e transcricao via Whisper (opcional). |
| ytmanager/playlist.py | Listagem de videos de playlists e canais. |
| ytmanager/output.py | Escrita de resultados em txt, json e markdown; slugify. |
| ytmanager/logging_config.py | Logging estruturado (JSON), niveis e correlation_id (RNF.11). |
| ytmanager/errors.py | Excecao YtManagerError (mensagem amigavel + dica + detalhe) (RNF.10). |
| ytmanager/validation.py | Validacao de URL/host e controles de seguranca (RNF.08/RNF.09). |
| ytmanager/download.py | Download de video (mp4/mkv/webm) e conversao via ffmpeg. |
| requirements.txt | Dependencias do projeto. |
| install.sh | Cria o venv e instala as dependencias. |
| pyproject.toml | Metadados do pacote e entry point ytmanager. |
| tests/ | Suite de testes automatizados (pytest), cobertura ~94%. |
| tests/test_cli.py | Testes de integracao do CLI (comando, args, exit codes). |
| tests/test_metadata.py | Testes de metadados (funcoes puras + mock de rede). |
| tests/test_output.py | Testes de escrita txt/json/md e slugify. |
| tests/test_subtitles.py | Testes de parsing VTT e listagem de legendas. |
| tests/test_playlist.py | Testes de listagem de playlist/canal. |
| tests/test_transcribe.py | Testes de download de audio e backends Whisper. |
| tests/test_logging_config.py | Testes do logging estruturado (RNF.11). |
| tests/test_main.py | Teste do entry point python -m ytmanager. |
| tests/test_errors.py | Testes de erros amigaveis e comando video (RNF.10). |
| tests/test_download.py | Testes de download/conversao de video. |
| tests/test_validation.py | Testes de validacao de entrada e seguranca (RNF.08/RNF.09). |
| CHANGELOG.md | Historico cronologico de alteracoes. |
| README.md | Este documento. |

---

## Changelog

O historico completo esta em [CHANGELOG.md](CHANGELOG.md).

### Versao atual: 0.1.0

- Estruturacao inicial do CLI com os comandos info, subs, transcript e playlist.
- Suporte a legendas automaticas/manuais e transcricao por Whisper.
- Saidas em txt, json e markdown.

---

## Desenvolvedor

**RWX Solucoes Inteligentes**

- Projeto: RWX YTManager
- Versao: 0.1.0
- Licenca: MIT

Para contribuicoes: abra uma issue ou envie um pull request descrevendo a
mudanca pretendida.
