"""Testes de ytmanager.output (escrita de arquivos e slugify)."""

import json
import os

import pytest

from ytmanager import output as out


class TestSlugify:
    def test_basic(self):
        assert out.slugify("O Plano de Flavio") == "o-plano-de-flavio"

    def test_accents(self):
        assert out.slugify("Flavio Bolsonaro - Seguranca") == \
            "flavio-bolsonaro-seguranca"

    def test_accents_unicode(self):
        assert out.slugify("Informacao") == "informacao"

    def test_special_chars(self):
        assert out.slugify("A/B:C?D") == "a-b-c-d"

    def test_empty_returns_default(self):
        assert out.slugify("") == "video"

    def test_none_returns_default(self):
        assert out.slugify(None) == "video"

    def test_max_len(self):
        result = out.slugify("a" * 200, max_len=10)
        assert len(result) == 10

    def test_leading_trailing_dashes_stripped(self):
        assert out.slugify("---abc---") == "abc"


class TestUnicodedataStaff:
    def test_strip(self):
        assert out.unicodedata_strip("cafe") == "cafe"


class TestWriteJson:
    def test_writes_file(self, tmp_path):
        path = str(tmp_path / "x.json")
        data = {"a": 1, "b": [1, 2, 3]}
        result = out.write_json(data, path)
        assert result == path
        with open(path, encoding="utf-8") as fh:
            assert json.load(fh) == data

    def test_ensure_ascii_false(self, tmp_path):
        path = str(tmp_path / "x.json")
        out.write_json({"t": "Informacao"}, path)
        with open(path, encoding="utf-8") as fh:
            assert "Informacao" in fh.read()


class TestWriteText:
    def test_writes_file(self, tmp_path):
        path = str(tmp_path / "x.txt")
        result = out.write_text("conteudo", path)
        assert result == path
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == "conteudo"


class TestWriteMarkdown:
    def test_full(self, tmp_path):
        path = str(tmp_path / "x.md")
        result = {
            "metadata": {
                "title": "Titulo",
                "author": "Canal",
                "url": "https://youtu.be/x",
                "duration_string": "2:05",
                "upload_date": "2026-01-01",
                "view_count": 100,
                "description": "Descricao do video",
            },
            "transcript": "Texto da transcricao",
        }
        out.write_markdown(result, path)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "# Titulo" in content
        assert "**Canal:** Canal" in content
        assert "**Duracao:** 2:05" in content
        assert "## Descricao" in content
        assert "## Transcricao" in content
        assert "Texto da transcricao" in content

    def test_minimal(self, tmp_path):
        path = str(tmp_path / "x.md")
        out.write_markdown({}, path)
        with open(path, encoding="utf-8") as fh:
            assert "# Video" in fh.read()

    def test_only_transcript(self, tmp_path):
        path = str(tmp_path / "x.md")
        out.write_markdown({"transcript": "so texto"}, path)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "## Transcricao" in content
        assert "so texto" in content
