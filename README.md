# RWX YTManager

CLI em Python para extrair conteudo do YouTube: metadados, legendas
(automaticas/manuais) e transcricao por IA (Whisper). Roda no terminal.

> Licenca: MIT.

## Instalacao

```bash
cd RWX-YTManager
bash install.sh
```

Cria um venv local (.venv) e instala o yt-dlp.

### Transcricao por IA (opcional)

Para transcrever o audio, instale ffmpeg e um backend Whisper:

```bash
sudo apt install ffmpeg
source .venv/bin/activate
pip install faster-whisper
```

## Uso

### Metadados

```bash
./bin/ytmanager info URL            # basico (oEmbed)
./bin/ytmanager info URL --full     # completo (yt-dlp)
./bin/ytmanager info URL --json
```

### Idiomas de legenda

```bash
./bin/ytmanager subs URL
```

### Transcricao

```bash
./bin/ytmanager transcript URL
./bin/ytmanager transcript URL --lang en
./bin/ytmanager transcript URL --format txt,json,md --out ./saida
./bin/ytmanager transcript URL --whisper --whisper-model medium
./bin/ytmanager transcript URL --whisper-fallback
```

### Playlists / canais

```bash
./bin/ytmanager playlist URL --limit 50
./bin/ytmanager playlist URL --json --out ./saida
```

## Estrategia de extracao

1. Legenda manual: melhor qualidade.
2. Legenda automatica (ASR): quase todo video tem, mas erra nomes e
   duplica frases -- por isso limpamos o VTT (remove timestamps, tags e
   duplicatas).
3. Whisper (IA no audio): melhor precisao, mais lento. Use
   --whisper-fallback para so acionar quando nao houver legenda.
4. Metadados: oEmbed e rapido; --full usa yt-dlp.

## Limitacoes e cuidados

- Usa yt-dlp (contorna API oficial). Use para uso pessoal/estudo. Para
  produto comercial em escala, use a YouTube Data API v3.
- Baixar/redistribuir videos inteiros viola os Termos do YouTube.
  Aqui extraimos apenas texto/metadados.
- Mantenha o yt-dlp atualizado: ./.venv/bin/pip install -U yt-dlp
- Videos sem legenda e sem ffmpeg/Whisper nao podem ser transcritos.

## Estrutura

```
RWX-YTManager/
|-- bin/ytmanager        atalho executavel
|-- ytmanager/
|   |-- metadata.py      oEmbed + yt-dlp --dump-json
|   |-- subtitles.py     download de legenda + limpeza VTT
|   |-- transcribe.py    audio -> Whisper (opcional)
|   |-- playlist.py      playlists e canais
|   |-- output.py        escrita txt/json/md
|   `-- cli.py           interface de linha de comando
|-- requirements.txt
|-- install.sh
`-- pyproject.toml
```
