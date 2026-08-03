"""Tests del perfil de Hermes (YAML, `mcp_servers:` con `url` + `headers`).

**Corrección real (2026-08-03, auditoría en vivo)**: reescrito completo tras
el bug encontrado — el perfil asumía `~/.hermes/cli-config.yaml` en toda
plataforma, cuando la instalación real de Hermes en Windows usa
`%LOCALAPPDATA%\\hermes\\config.yaml` (u override por `HERMES_HOME`, mismo
criterio que el propio Hermes). Con la versión vieja, `~/.hermes/` podía
existir por otras razones (Hermes deja ahí una carpeta `scripts/`) y producir
un falso positivo de "instalado" sin que el archivo real existiera —
por eso ahora la detección se aísla vía `HERMES_HOME`, y se prueba
detectando por la presencia del ARCHIVO `config.yaml`, no del directorio.
"""

from __future__ import annotations

import pytest
import yaml

from mpbot_mcp.agentes import NOMBRE_SERVIDOR, detectar_agentes, escribir_config, hermes


@pytest.fixture(autouse=True)
def _home_aislado(tmp_path, monkeypatch):
    # HERMES_HOME tiene precedencia sobre cualquier resolución por plataforma
    # (mismo criterio que el propio Hermes) — es la forma correcta de aislar
    # el test sin depender de si corre en Windows, macOS o Linux.
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    yield


def test_no_detectado_sin_archivo_config_yaml():
    assert hermes.PERFIL.esta_instalado() is False


def test_directorio_hermes_solo_no_basta_para_detectarlo(tmp_path):
    """Regresión del bug real: el directorio puede existir por otras razones
    (ej. una carpeta `scripts/`) sin que `config.yaml` exista — no debe dar
    falso positivo."""
    (tmp_path / "scripts").mkdir()
    assert hermes.PERFIL.esta_instalado() is False


def test_detectado_por_archivo_config_yaml(tmp_path):
    (tmp_path / "config.yaml").write_text("mcp_servers: {}\n", encoding="utf-8")
    assert hermes.PERFIL.esta_instalado() is True


def test_ruta_de_config_es_config_yaml_no_cli_config_yaml(tmp_path):
    """Regresión del bug real: el archivo se llama `config.yaml` — el nombre
    `cli-config.yaml` es solo el de la plantilla de ejemplo empaquetada con
    el código fuente de Hermes, nunca la config viva."""
    assert hermes.PERFIL.ruta_archivo_config().name == "config.yaml"


def test_entrada_directa_es_url_mas_headers():
    entrada = hermes.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test123")
    assert entrada == {
        "url": "https://app.mpbot.cl/mcp/",
        "headers": {"Authorization": "Bearer mpb_test123"},
    }


def test_escritura_yaml_preserva_otros_servidores_y_es_idempotente(tmp_path):
    ruta = hermes.PERFIL.ruta_archivo_config()
    ruta.parent.mkdir(parents=True, exist_ok=True)
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
    assert segunda["mcp_servers"][NOMBRE_SERVIDOR] == entrada


def test_la_entrada_se_llama_mpbot_no_hermes(tmp_path):
    """Regresión (auditoría 2026-08-03): la clave no puede ser "hermes" — un
    servidor llamado "hermes" adentro de la config de Hermes no comunica que
    es mpbot."""
    ruta = hermes.PERFIL.ruta_archivo_config()
    entrada = hermes.PERFIL.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_x")
    escribir_config(hermes.PERFIL, ruta, entrada)
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert "mpbot" in datos["mcp_servers"]
    assert "hermes" not in datos["mcp_servers"]


def test_detectar_agentes_incluye_hermes_cuando_esta_instalado(tmp_path):
    (tmp_path / "config.yaml").write_text("mcp_servers: {}\n", encoding="utf-8")
    encontrados = detectar_agentes([hermes.PERFIL])
    assert [p.id for p, _ in encontrados] == ["hermes"]
