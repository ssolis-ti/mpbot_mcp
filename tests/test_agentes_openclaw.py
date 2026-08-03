"""Tests del perfil de OpenClaw (JSON anidado, `mcp.servers.<id>` con
`transport: streamable-http` + `headers`)."""

from __future__ import annotations

import json

import pytest

from mpbot_mcp.agentes import detectar_agentes, escribir_config, openclaw


@pytest.fixture(autouse=True)
def _home_aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(openclaw.Path, "home", lambda: tmp_path)
    yield


def test_no_detectado_sin_directorio_openclaw():
    assert openclaw.PERFIL.esta_instalado() is False


def test_detectado_por_directorio_openclaw(tmp_path):
    (tmp_path / ".openclaw").mkdir()
    assert openclaw.PERFIL.esta_instalado() is True


def test_entrada_directa_declara_transporte_streamable_http():
    entrada = openclaw.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test123")
    assert entrada == {
        "transport": "streamable-http",
        "url": "https://app.mpbot.cl/mcp/",
        "headers": {"Authorization": "Bearer mpb_test123"},
    }


def test_escritura_anida_bajo_mcp_servers_preservando_lo_ajeno(tmp_path):
    ruta = openclaw.PERFIL.ruta_archivo_config()
    ruta.parent.mkdir(parents=True)
    ruta.write_text(
        json.dumps({"otraConfig": True, "mcp": {"servers": {"otro": {"url": "https://otro.example"}}}}),
        encoding="utf-8",
    )

    entrada = openclaw.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test123")
    escribir_config(openclaw.PERFIL, ruta, entrada)
    primera = json.loads(ruta.read_text(encoding="utf-8"))

    escribir_config(openclaw.PERFIL, ruta, entrada)
    segunda = json.loads(ruta.read_text(encoding="utf-8"))

    assert primera == segunda
    assert segunda["otraConfig"] is True
    assert segunda["mcp"]["servers"]["otro"] == {"url": "https://otro.example"}
    assert segunda["mcp"]["servers"]["openclaw"] == entrada


def test_detectar_agentes_incluye_openclaw_cuando_esta_instalado(tmp_path):
    (tmp_path / ".openclaw").mkdir()
    encontrados = detectar_agentes([openclaw.PERFIL])
    assert [p.id for p, _ in encontrados] == ["openclaw"]
