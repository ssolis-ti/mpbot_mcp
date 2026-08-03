"""Tests del perfil de Hermes (YAML, `mcp_servers:` con `url` + `headers`)."""

from __future__ import annotations

import pytest
import yaml

from mpbot_mcp.agentes import detectar_agentes, escribir_config, hermes


@pytest.fixture(autouse=True)
def _home_aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(hermes.Path, "home", lambda: tmp_path)
    yield


def test_no_detectado_sin_directorio_hermes():
    assert hermes.PERFIL.esta_instalado() is False


def test_detectado_por_directorio_hermes(tmp_path):
    (tmp_path / ".hermes").mkdir()
    assert hermes.PERFIL.esta_instalado() is True


def test_entrada_directa_es_url_mas_headers():
    entrada = hermes.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test123")
    assert entrada == {
        "url": "https://app.mpbot.cl/mcp/",
        "headers": {"Authorization": "Bearer mpb_test123"},
    }


def test_escritura_yaml_preserva_otros_servidores_y_es_idempotente(tmp_path):
    ruta = hermes.PERFIL.ruta_archivo_config()
    ruta.parent.mkdir(parents=True)
    ruta.write_text(
        "otra_config: 1\nmcp_servers:\n  otro:\n    url: https://otro.example\n",
        encoding="utf-8",
    )

    entrada = hermes.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test123")
    escribir_config(hermes.PERFIL, ruta, entrada)
    primera = yaml.safe_load(ruta.read_text(encoding="utf-8"))

    escribir_config(hermes.PERFIL, ruta, entrada)
    segunda = yaml.safe_load(ruta.read_text(encoding="utf-8"))

    assert primera == segunda
    assert segunda["otra_config"] == 1
    assert segunda["mcp_servers"]["otro"] == {"url": "https://otro.example"}
    assert segunda["mcp_servers"]["hermes"] == entrada


def test_detectar_agentes_incluye_hermes_cuando_esta_instalado(tmp_path):
    (tmp_path / ".hermes").mkdir()
    encontrados = detectar_agentes([hermes.PERFIL])
    assert [p.id for p, _ in encontrados] == ["hermes"]
