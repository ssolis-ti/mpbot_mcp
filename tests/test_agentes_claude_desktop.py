"""Tests del perfil de Claude Desktop.

Su soporte de conexión directa está sin confirmar (research §4): el perfil
debe comportarse como agente solo-stdio hasta que T024 lo verifique en vivo.
"""

from __future__ import annotations

import json

import pytest

from mpbot_mcp.agentes import NOMBRE_SERVIDOR, claude_desktop, detectar_agentes, escribir_config


@pytest.fixture(autouse=True)
def _appdata_aislado(tmp_path, monkeypatch):
    # Fuerza la rama Windows del perfil, independiente del SO donde corran los tests.
    monkeypatch.setattr(claude_desktop.platform, "system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield


def test_no_declara_soporte_directo_hasta_verificarse():
    assert claude_desktop.PERFIL.soporta_directo is False
    assert claude_desktop.PERFIL.construir_entrada_directa is None


def test_soporta_modo_stdio():
    assert claude_desktop.PERFIL.soporta_stdio is True
    entrada = claude_desktop.PERFIL.construir_entrada_stdio("C:/ruta/mpbot-mcp.exe")
    assert entrada == {"command": "C:/ruta/mpbot-mcp.exe", "args": ["servir"]}


def test_no_detectado_sin_directorio_claude(tmp_path):
    assert claude_desktop.PERFIL.esta_instalado() is False


def test_detectado_por_directorio_claude(tmp_path):
    (tmp_path / "Claude").mkdir()
    assert claude_desktop.PERFIL.esta_instalado() is True


def test_escritura_stdio_preserva_lo_ajeno_y_es_idempotente(tmp_path):
    (tmp_path / "Claude").mkdir()
    ruta = claude_desktop.PERFIL.ruta_archivo_config()
    ruta.write_text(json.dumps({"mcpServers": {"otro": {"command": "otro-binario"}}}), encoding="utf-8")

    entrada = claude_desktop.PERFIL.construir_entrada_stdio("C:/ruta/mpbot-mcp.exe")
    escribir_config(claude_desktop.PERFIL, ruta, entrada)
    primera = json.loads(ruta.read_text(encoding="utf-8"))

    escribir_config(claude_desktop.PERFIL, ruta, entrada)
    segunda = json.loads(ruta.read_text(encoding="utf-8"))

    assert primera == segunda
    assert segunda["mcpServers"]["otro"] == {"command": "otro-binario"}
    assert segunda["mcpServers"][NOMBRE_SERVIDOR] == entrada


def test_la_entrada_se_llama_mpbot_no_claude_desktop(tmp_path):
    """Regresión (auditoría 2026-08-03): la clave no puede ser "claude-desktop"."""
    (tmp_path / "Claude").mkdir()
    ruta = claude_desktop.PERFIL.ruta_archivo_config()
    entrada = claude_desktop.PERFIL.construir_entrada_stdio("C:/ruta/mpbot-mcp.exe")
    escribir_config(claude_desktop.PERFIL, ruta, entrada)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert "mpbot" in datos["mcpServers"]
    assert "claude-desktop" not in datos["mcpServers"]


def test_detectar_agentes_incluye_claude_desktop_cuando_esta_instalado(tmp_path):
    (tmp_path / "Claude").mkdir()
    encontrados = detectar_agentes([claude_desktop.PERFIL])
    assert [p.id for p, _ in encontrados] == ["claude-desktop"]
