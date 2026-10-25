"""Testes do entry point ytmanager.__main__."""

import runpy
import sys
import warnings
from unittest import mock

import pytest

from ytmanager import __main__ as entry


def test_main_symbol_exists():
    assert callable(entry.main)


def test_run_module_invokes_main_and_exits():
    # remove o modulo do cache para permitir re-execucao limpa
    sys.modules.pop("ytmanager.__main__", None)
    with mock.patch("ytmanager.cli.main", return_value=0):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(SystemExit) as exc:
                runpy.run_module("ytmanager.__main__", run_name="__main__")
    assert exc.value.code == 0
