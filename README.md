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
| requirements.txt | Dependencias do projeto. |
| install.sh | Cria o venv e instala as dependencias. |
| pyproject.toml | Metadados do pacote e entry point ytmanager. |
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
