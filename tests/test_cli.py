"""Tests de mpbot_mcp/cli.py.

En Windows, `sys.argv[0]` del console-script generado por pip viene **sin**
la extensión `.exe`. Escribir esa ruta tal cual en la config de un agente
(modo puente) apuntaría a un archivo que no existe.
"""

from __future__ import annotations

import platform

import pytest

from mpbot_mcp import cli


@pytest.mark.skipif(platform.system() != "Windows", reason="comportamiento específico de Windows")
def test_agrega_exe_si_sys_argv_0_no_lo_trae_y_el_exe_existe(tmp_path, monkeypatch):
    ejecutable = tmp_path / "mpbot-mcp.exe"
    ejecutable.write_bytes(b"")  # el contenido no importa, solo que exista

    sin_extension = tmp_path / "mpbot-mcp"
    monkeypatch.setattr(cli.sys, "argv", [str(sin_extension)])

    assert cli.ruta_ejecutable_actual() == str(ejecutable)


@pytest.mark.skipif(platform.system() != "Windows", reason="comportamiento específico de Windows")
def test_no_agrega_exe_si_ni_la_ruta_ni_su_exe_existen(tmp_path, monkeypatch):
    ruta_inexistente = tmp_path / "no-existe-de-verdad"
    monkeypatch.setattr(cli.sys, "argv", [str(ruta_inexistente)])

    # Sin nada que existiera, no hay mejor información: se devuelve la ruta tal cual.
    assert cli.ruta_ejecutable_actual() == str(ruta_inexistente.resolve())


def test_no_toca_la_ruta_si_ya_existe_tal_cual(tmp_path, monkeypatch):
    ejecutable = tmp_path / "mpbot-mcp-script"
    ejecutable.write_bytes(b"")
    monkeypatch.setattr(cli.sys, "argv", [str(ejecutable)])

    assert cli.ruta_ejecutable_actual() == str(ejecutable.resolve())
