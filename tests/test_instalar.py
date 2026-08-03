"""Test del flujo `instalar` (T017).

Con key inválida no escribe ningún archivo (FR-003), y sin agentes
detectados no falla con un error técnico.
"""

from __future__ import annotations

import json

import pytest

from mpbot_mcp import config
from mpbot_mcp.agentes.perfil import PerfilAgente
from mpbot_mcp.cli import ejecutar_instalar
from mpbot_mcp.errores import TipoError

from .conftest import API_KEY_INVALIDA, API_KEY_VALIDA, URL_SERVIDOR_SIMULADO

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _config_aislada(tmp_path, monkeypatch):
    monkeypatch.setenv("MPBOT_CONFIG_DIR", str(tmp_path / "mpbot-mcp"))
    monkeypatch.delenv("MPBOT_API_KEY", raising=False)
    monkeypatch.delenv("MPBOT_URL", raising=False)
    yield


def _perfil_dummy(tmp_path, *, instalado: bool) -> PerfilAgente:
    directorio = tmp_path / "agente"
    if instalado:
        directorio.mkdir(parents=True, exist_ok=True)
    archivo = directorio / "config.json"
    return PerfilAgente(
        id="dummy",
        nombre="Agente de prueba",
        rutas_deteccion=lambda: [directorio],
        ruta_archivo_config=lambda: archivo,
        formato="json",
        ruta_en_archivo=["mcpServers"],
        soporta_directo=True,
        soporta_stdio=False,
        construir_entrada_directa=lambda url, key: {"url": url, "headers": {"Authorization": f"Bearer {key}"}},
        construir_entrada_stdio=None,
        verificado_en=None,
    )


async def test_key_invalida_no_escribe_ningun_archivo(tmp_path, fabrica_http_simulada, monkeypatch):
    perfil = _perfil_dummy(tmp_path, instalado=True)
    monkeypatch.setattr("mpbot_mcp.cliente._fabrica_por_defecto", fabrica_http_simulada)

    resultado = await ejecutar_instalar(
        api_key=API_KEY_INVALIDA,
        url_servidor=URL_SERVIDOR_SIMULADO,
        registro=[perfil],
    )

    assert resultado.ok is False
    assert resultado.error is not None
    assert resultado.error.tipo is TipoError.CREDENCIAL_INVALIDA
    assert not perfil.ruta_archivo_config().exists()
    assert config.existe_configuracion() is False


async def test_sin_agentes_detectados_no_es_error(tmp_path, fabrica_http_simulada, monkeypatch):
    perfil = _perfil_dummy(tmp_path, instalado=False)
    monkeypatch.setattr("mpbot_mcp.cliente._fabrica_por_defecto", fabrica_http_simulada)

    resultado = await ejecutar_instalar(
        api_key=API_KEY_VALIDA,
        url_servidor=URL_SERVIDOR_SIMULADO,
        registro=[perfil],
    )

    assert resultado.ok is True
    assert resultado.sin_agentes_detectados is True
    assert resultado.error is None
    # La key sí sirve: se guarda igual, aunque no haya a quién escribirle.
    assert config.existe_configuracion() is True


async def test_key_valida_escribe_config_del_agente_detectado(tmp_path, fabrica_http_simulada, monkeypatch):
    perfil = _perfil_dummy(tmp_path, instalado=True)
    monkeypatch.setattr("mpbot_mcp.cliente._fabrica_por_defecto", fabrica_http_simulada)

    resultado = await ejecutar_instalar(
        api_key=API_KEY_VALIDA,
        url_servidor=URL_SERVIDOR_SIMULADO,
        registro=[perfil],
    )

    assert resultado.ok is True
    assert resultado.tools_disponibles == 2
    assert len(resultado.agentes_configurados) == 1
    assert resultado.agentes_configurados[0].ok is True

    datos = json.loads(perfil.ruta_archivo_config().read_text(encoding="utf-8"))
    assert datos["mcpServers"]["dummy"]["headers"]["Authorization"] == f"Bearer {API_KEY_VALIDA}"


async def test_confirmacion_rechazada_no_escribe_nada(tmp_path, fabrica_http_simulada, monkeypatch):
    perfil = _perfil_dummy(tmp_path, instalado=True)
    monkeypatch.setattr("mpbot_mcp.cliente._fabrica_por_defecto", fabrica_http_simulada)

    resultado = await ejecutar_instalar(
        api_key=API_KEY_VALIDA,
        url_servidor=URL_SERVIDOR_SIMULADO,
        registro=[perfil],
        confirmar=lambda _detectados: False,
    )

    assert resultado.ok is False
    assert resultado.cancelado_por_el_usuario is True
    assert not perfil.ruta_archivo_config().exists()


async def test_ejecutar_dos_veces_es_idempotente(tmp_path, fabrica_http_simulada, monkeypatch):
    perfil = _perfil_dummy(tmp_path, instalado=True)
    monkeypatch.setattr("mpbot_mcp.cliente._fabrica_por_defecto", fabrica_http_simulada)

    await ejecutar_instalar(api_key=API_KEY_VALIDA, url_servidor=URL_SERVIDOR_SIMULADO, registro=[perfil])
    primera = perfil.ruta_archivo_config().read_text(encoding="utf-8")

    await ejecutar_instalar(api_key=API_KEY_VALIDA, url_servidor=URL_SERVIDOR_SIMULADO, registro=[perfil])
    segunda = perfil.ruta_archivo_config().read_text(encoding="utf-8")

    assert json.loads(primera) == json.loads(segunda)
