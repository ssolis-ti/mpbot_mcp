"""Tests del modo puente (US3): `servidor local <-> cliente upstream <-> servidor remoto`.

El puente debe exponer exactamente las mismas tools que el servidor remoto
(FR-016/SC-006), pasar los errores del servidor como mensajes comprensibles
en vez de fallas mudas (FR-017), y no quedarse colgado ante una caída de
red (T034). Las dos primeras se prueban de punta a punta: un `ClientSession`
real conectado en memoria (sin stdio real, vía `mcp.shared.memory`) contra
el `Server` que arma `puente.construir_servidor`, y ese servidor a su vez
habla con el servidor MCP simulado de `conftest.py` — dos saltos reales,
cero red.

El manejo de fallas a mitad de sesión (key revocada, cuota agotada, red
caída *después* de conectar) se prueba con un cliente upstream falso —
cualquier objeto con `listar_tools`/`llamar_tool` sirve, porque
`construir_servidor` no exige que sea un `ClienteMpbot` real — para poder
forzar la falla exactamente donde importa sin depender de que el servidor
simulado reproduzca ese timing específico.
"""

from __future__ import annotations

import anyio
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mpbot_mcp.cliente import ClienteMpbot
from mpbot_mcp.errores import ErrorMpbot, TipoError
from mpbot_mcp.puente import construir_servidor

from .conftest import API_KEY_VALIDA, NOMBRES_TOOLS_SIMULADAS, URL_SERVIDOR_SIMULADO

pytestmark = pytest.mark.anyio


class _ClienteFalso:
    """Cliente upstream mínimo para probar el puente en aislamiento."""

    def __init__(self, *, tools=None, error_en_llamada: ErrorMpbot | None = None):
        self._tools = tools or []
        self._error_en_llamada = error_en_llamada

    async def listar_tools(self):
        return self._tools

    async def llamar_tool(self, nombre, argumentos=None):
        if self._error_en_llamada is not None:
            raise self._error_en_llamada
        raise AssertionError(f"tool inesperada llamada en el falso: {nombre}")


async def test_expone_las_mismas_tools_que_el_servidor_remoto(fabrica_http_simulada):
    async with ClienteMpbot(API_KEY_VALIDA, URL_SERVIDOR_SIMULADO, fabrica_http_client=fabrica_http_simulada) as cliente_upstream:
        tools_directas = {t.name for t in await cliente_upstream.listar_tools()}

        servidor = construir_servidor(cliente_upstream)
        async with create_connected_server_and_client_session(servidor) as sesion_local:
            resultado = await sesion_local.list_tools()
            tools_por_el_puente = {t.name for t in resultado.tools}

    assert tools_por_el_puente == tools_directas == set(NOMBRES_TOOLS_SIMULADAS)


async def test_llamar_tool_a_traves_del_puente_da_el_mismo_resultado_que_directo(fabrica_http_simulada):
    async with ClienteMpbot(API_KEY_VALIDA, URL_SERVIDOR_SIMULADO, fabrica_http_client=fabrica_http_simulada) as cliente_upstream:
        directo = await cliente_upstream.llamar_tool("buscar_licitaciones", {"rubro": "aseo"})

        servidor = construir_servidor(cliente_upstream)
        async with create_connected_server_and_client_session(servidor) as sesion_local:
            por_el_puente = await sesion_local.call_tool("buscar_licitaciones", {"rubro": "aseo"})

    assert por_el_puente.content[0].text == directo.content[0].text
    assert por_el_puente.isError in (False, None)


async def test_error_a_mitad_de_sesion_llega_como_mensaje_no_como_falla_muda():
    """FR-017: si la cuota se agota o la key se revoca mientras el agente ya
    está conectado al puente, la llamada debe volver con `isError=True` y el
    mensaje en español + acción — nunca un traceback ni un cuelgue."""
    error = ErrorMpbot(TipoError.CUOTA_AGOTADA, "Se agotó la cuota mensual.", "Espera a la renovación.")
    cliente_falso = _ClienteFalso(error_en_llamada=error)

    servidor = construir_servidor(cliente_falso)
    async with create_connected_server_and_client_session(servidor) as sesion_local:
        with anyio.fail_after(5):
            resultado = await sesion_local.call_tool("cualquier_tool", {})

    assert resultado.isError is True
    assert "cuota mensual" in resultado.content[0].text
    assert "renovación" in resultado.content[0].text


async def test_llamar_una_tool_inexistente_no_cuelga_y_reporta_error(fabrica_http_simulada):
    async with ClienteMpbot(API_KEY_VALIDA, URL_SERVIDOR_SIMULADO, fabrica_http_client=fabrica_http_simulada) as cliente_upstream:
        servidor = construir_servidor(cliente_upstream)
        async with create_connected_server_and_client_session(servidor) as sesion_local:
            with anyio.fail_after(5):
                resultado = await sesion_local.call_tool("tool_que_no_existe", {})

    assert resultado.isError is True


async def test_caida_de_red_a_mitad_de_sesion_no_deja_la_llamada_colgada():
    error_red = ErrorMpbot(TipoError.CONECTIVIDAD, "No se pudo contactar al servidor.", "Revisa tu conexión.")
    cliente_falso = _ClienteFalso(error_en_llamada=error_red)

    servidor = construir_servidor(cliente_falso)
    async with create_connected_server_and_client_session(servidor) as sesion_local:
        with anyio.fail_after(5):
            resultado = await sesion_local.call_tool("cualquier_tool", {})

    assert resultado.isError is True
    assert "conexión" in resultado.content[0].text.lower() or "contactar" in resultado.content[0].text.lower()
