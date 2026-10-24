#!/usr/bin/env bash
# Instala o RWX YTManager num venv local e baixa o yt-dlp.
# Uso: bash install.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo ">> Criando venv em .venv"
python3 -m venv .venv

echo ">> Instalando dependencias"
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

echo ">> Verificando yt-dlp"
./.venv/bin/yt-dlp --version

echo ">> Concluido. Teste com:"
echo "   ./bin/ytmanager info <URL>"
