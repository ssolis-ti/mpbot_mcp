"""Tests de config.py: permisos, precedencia del entorno y enmascarado (SC-004)."""

from __future__ import annotations

import platform

import pytest

from mpbot_mcp import config


@pytest.fixture(autouse=True)
def _config_aislada(tmp_path, monkeypatch):
    """Nunca tocar el directorio de configuración real del equipo que corre los tests."""
    monkeypatch.setenv("MPBOT_CONFIG_DIR", str(tmp_path / "mpbot-mcp"))
    monkeypatch.delenv("MPBOT_API_KEY", raising=False)
    monkeypatch.delenv("MPBOT_URL", raising=False)
    yield


def test_no_existe_configuracion_antes_de_guardar():
    assert config.existe_configuracion() is False
    assert config.cargar() is None


def test_guardar_y_cargar_roundtrip():
    cfg = config.ConfiguracionConector(api_key="mpb_abcdef1234567890")
    config.guardar(cfg)

    assert config.existe_configuracion() is True
    cargada = config.cargar()
    assert cargada is not None
    assert cargada.api_key == "mpb_abcdef1234567890"
    assert cargada.url_servidor == config.URL_POR_DEFECTO


def test_guardar_dos_veces_no_duplica_archivo():
    config.guardar(config.ConfiguracionConector(api_key="mpb_primera"))
    config.guardar(config.ConfiguracionConector(api_key="mpb_segunda"))

    cargada = config.cargar()
    assert cargada is not None
    assert cargada.api_key == "mpb_segunda"


@pytest.mark.skipif(platform.system() == "Windows", reason="permisos POSIX no aplican en Windows")
def test_permisos_archivo_restringidos_al_dueno():
    import os
    import stat

    ruta = config.guardar(config.ConfiguracionConector(api_key="mpb_abcdef1234567890"))
    modo = stat.S_IMODE(os.stat(ruta).st_mode)
    assert modo == 0o600


def test_entorno_tiene_precedencia_sobre_el_archivo(monkeypatch):
    config.guardar(config.ConfiguracionConector(api_key="mpb_del_archivo", url_servidor="https://a.example/mcp/"))

    monkeypatch.setenv("MPBOT_API_KEY", "mpb_del_entorno")
    monkeypatch.setenv("MPBOT_URL", "https://b.example/mcp/")

    cargada = config.cargar()
    assert cargada is not None
    assert cargada.api_key == "mpb_del_entorno"
    assert cargada.url_servidor == "https://b.example/mcp/"


def test_entorno_sin_archivo_arma_configuracion_transitoria(monkeypatch):
    monkeypatch.setenv("MPBOT_API_KEY", "mpb_solo_entorno")

    cargada = config.cargar()
    assert cargada is not None
    assert cargada.api_key == "mpb_solo_entorno"
    # No debe haberse escrito nada a disco solo por leer el entorno.
    assert config.existe_configuracion() is False


@pytest.mark.parametrize(
    "key",
    [
        "mpb_2f5a1b2c3d4e5f6a7b8c9d",
        "mpb_1234567890abcdef",
        "corta",
        "",
    ],
)
def test_enmascarado_nunca_deja_pasar_la_key_completa(key):
    enmascarada = config.enmascarar(key)
    if key:
        assert enmascarada != key
        assert key not in enmascarada or len(enmascarada) < len(key)
    assert "…" in enmascarada or enmascarada == ""
