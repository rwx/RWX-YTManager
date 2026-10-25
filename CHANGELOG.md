# Changelog

Todas as mudancas notaveis deste projeto serao documentadas aqui.
O formato segue Keep a Changelog e Versionamento Semantico.

## [0.1.0] - 2026-10-24

### Adicionado

- Estrutura inicial do projeto RWX YTManager (CLI em Python).
- Comando info: metadados via oEmbed e via yt-dlp (--full, --json).
- Comando subs: lista idiomas de legenda manual e automatica.
- Comando transcript: extrai transcricao com limpeza de VTT e dedup de frases.
- Comando playlist: lista videos de playlists e canais (--limit, --json).
- Transcricao por IA via faster-whisper (--whisper, --whisper-fallback).
- Saidas em txt, json e markdown (--format, --out).
- Atalho bin/ytmanager com resolucao automatica de venv e PYTHONPATH.
- Logging estruturado em JSON com niveis (INFO/WARN/ERROR/FATAL),
  correlation_id por execucao e arquivo rotativo (RNF.11).
- Suite de testes automatizados (pytest + pytest-cov): 96 testes,
  cobertura de 94%, exigencia minima de 70% (RNF.13/RNF.14).

### Corrigido

- Fixa av==13.0.0 para contornar bug de metadata_errors no Python 3.13.
- Parser de list-subs ignora cabecalho e exige 3 colunas.
