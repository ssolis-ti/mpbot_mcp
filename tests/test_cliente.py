"""Tests de cliente.py contra el servidor MCP simulado (T009).

Descubre tools sin lista propia (Principio III) y propaga cada error
tipado correctamente (401/403/429/421/red), traducido por errores.py.
"""

from __future__ import annotations

import pytest

from mpbot_mcp.cliente import ClienteMpbot
from mpbot_mcp.errores import ErrorMpbot, TipoError

from .conftest import (
    API_KEY_HOST_MALO,
    API_KEY_INVALIDA,
    API_KEY_SIN_CUOTA,
    API_KEY_SIN_PLAN,
    API_KEY_VALIDA,
    NOMBRES_TOOLS_SIMULADAS,
    URL_SERVIDOR_SIMULADO,
)

pytestmark = pytest.mark.anyio


async def test_descubre_tools_por_protocolo_sin_lista_propia(fabrica_http_simulada):
    async with ClienteMpbot(API_KEY_VALIDA, URL_SERVIDOR_SIMULADO, fabrica_http_client=fabrica_http_simulada) as cliente:
        tools = await cliente.listar_tools()

    nombres = {t.name for t in tools}
    assert nombres == set(NOMBRES_TOOLS_SIMULADAS)


async def test_llamar_tool_devuelve_resultado_real(fabrica_http_simulada):
    async with ClienteMpbot(API_KEY_VALIDA, URL_SERVIDOR_SIMULADO, fabrica_http_client=fabrica_http_simulada) as cliente:
        resultado = await cliente.llamar_tool("buscar_licitaciones", {"rubro": "construcción"})

    texto = resultado.content[0].text
    assert "construcción" in texto


@pytest.mark.parametrize(
    "api_key,tipo_esperado",
    [
        (API_KEY_INVALIDA, TipoError.CREDENCIAL_INVALIDA),
        (API_KEY_SIN_PLAN, TipoError.PLAN_INSUFICIENTE),
        (API_KEY_SIN_CUOTA, TipoError.CUOTA_AGOTADA),
        (API_KEY_HOST_MALO, TipoError.HOST_NO_RECONOCIDO),
    ],
)
async def test_cada_modo_de_falla_llega_tipado(fabrica_http_simulada, api_key, tipo_esperado):
    with pytest.raises(ErrorMpbot) as exc_info:
        async with ClienteMpbot(api_key, URL_SERVIDOR_SIMULADO, fabrica_http_client=fabrica_http_simulada):
            pass

    assert exc_info.value.tipo is tipo_esperado


async def test_caida_de_red_se_reporta_como_conectividad(fabrica_http_sin_red):
    with pytest.raises(ErrorMpbot) as exc_info:
        async with ClienteMpbot(API_KEY_VALIDA, URL_SERVIDOR_SIMULADO, fabrica_http_client=fabrica_http_sin_red):
            pass

    assert exc_info.value.tipo is TipoError.CONECTIVIDAD


async def test_una_sola_sesion_se_reusa_para_varias_llamadas(fabrica_http_simulada):
    async with ClienteMpbot(API_KEY_VALIDA, URL_SERVIDOR_SIMULADO, fabrica_http_client=fabrica_http_simulada) as cliente:
        primera = await cliente.listar_tools()
        segunda = await cliente.listar_tools()

    assert {t.name for t in primera} == {t.name for t in segunda}
