"""Tests del perfil de Claude Code: detección, escritura, respaldo, idempotencia
(FR-005/006/007, SC-005)."""

from __future__ import annotations

import json

import pytest

from mpbot_mcp.agentes import NOMBRE_SERVIDOR, claude_code, detectar_agentes, escribir_config


@pytest.fixture(autouse=True)
def _home_aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_code.Path, "home", lambda: tmp_path)
    yield


def test_no_detectado_sin_home_claude():
    assert claude_code.PERFIL.esta_instalado() is False


def test_detectado_por_archivo_claude_json(tmp_path):
    (tmp_path / ".claude.json").write_text("{}", encoding="utf-8")
    assert claude_code.PERFIL.esta_instalado() is True


def test_detectado_por_directorio_claude(tmp_path):
    (tmp_path / ".claude").mkdir()
    assert claude_code.PERFIL.esta_instalado() is True


def test_entrada_directa_trae_headers_con_bearer():
    entrada = claude_code.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test123")
    assert entrada["type"] == "http"
    assert entrada["url"] == "https://app.mpbot.cl/mcp/"
    assert entrada["headers"]["Authorization"] == "Bearer mpb_test123"


def test_escritura_preserva_otros_mcp_servers_y_es_idempotente(tmp_path):
    ruta = claude_code.PERFIL.ruta_archivo_config()
    ruta.write_text(json.dumps({"mcpServers": {"otro": {"command": "otro-binario"}}}), encoding="utf-8")

    entrada = claude_code.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test123")
    escribir_config(claude_code.PERFIL, ruta, entrada)
    primera = json.loads(ruta.read_text(encoding="utf-8"))

    escribir_config(claude_code.PERFIL, ruta, entrada)
    segunda = json.loads(ruta.read_text(encoding="utf-8"))

    assert primera == segunda
    assert segunda["mcpServers"]["otro"] == {"command": "otro-binario"}
    assert segunda["mcpServers"][NOMBRE_SERVIDOR] == entrada


def test_escritura_respalda_config_previa(tmp_path):
    ruta = claude_code.PERFIL.ruta_archivo_config()
    ruta.write_text("{}", encoding="utf-8")

    resultado = escribir_config(
        claude_code.PERFIL, ruta, claude_code.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_x")
    )

    assert resultado.respaldo is not None
    assert resultado.respaldo.ruta_respaldo.read_text(encoding="utf-8") == "{}"


def test_detectar_agentes_incluye_claude_code_cuando_esta_instalado(tmp_path):
    (tmp_path / ".claude.json").write_text("{}", encoding="utf-8")
    encontrados = detectar_agentes([claude_code.PERFIL])
    assert [p.id for p, _ in encontrados] == ["claude-code"]


def test_la_entrada_se_llama_mpbot_no_claude_code(tmp_path):
    """Regresión (auditoría 2026-08-03): la clave del servidor debe ser
    literalmente "mpbot" — no el id del agente que se está configurando."""
    ruta = claude_code.PERFIL.ruta_archivo_config()
    entrada = claude_code.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_x")
    escribir_config(claude_code.PERFIL, ruta, entrada)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert "mpbot" in datos["mcpServers"]
    assert "claude-code" not in datos["mcpServers"]
