"""Servidor MCP simulado compartido por toda la suite.

Ningún test de este repo llama a producción ni usa una API key real
(constitución, sección "Flujo de desarrollo y compuertas"). Este módulo
levanta un servidor MCP real (SDK oficial) en memoria, vía ASGI, con una
capa de autenticación falsa que reproduce los cuatro modos de falla del
contrato real (401/403/429/421 — contracts/servidor-mpbot.md).
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

URL_SERVIDOR_SIMULADO = "http://mpbot.test/mcp"

API_KEY_VALIDA = "mpb_test_valida_0000000000"
API_KEY_INVALIDA = "mpb_test_invalida_0000000"
API_KEY_SIN_PLAN = "mpb_test_sinplan_00000000"
API_KEY_SIN_CUOTA = "mpb_test_sincuota_0000000"
API_KEY_HOST_MALO = "mpb_test_hostmalo_0000000"

NOMBRES_TOOLS_SIMULADAS = ("buscar_licitaciones", "obtener_cotizacion")


def _construir_mcp() -> FastMCP:
    servidor = FastMCP(
        "mpbot-simulado",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["mpbot.test"],
        ),
    )

    @servidor.tool()
    def buscar_licitaciones(rubro: str) -> str:
        """Busca licitaciones por rubro (herramienta simulada, solo para tests)."""
        return f"3 licitaciones encontradas para el rubro '{rubro}'"

    @servidor.tool()
    def obtener_cotizacion(id_licitacion: str) -> str:
        """Obtiene el detalle de una cotización (herramienta simulada, solo para tests)."""
        return f"Cotización {id_licitacion}: adjudicada"

    return servidor


def _clave_de(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key", "").strip()


def _envolver_con_autenticacion(app_mcp):
    async def con_autenticacion(scope, receive, send):
        if scope["type"] != "http":
            await app_mcp(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        key = _clave_de(request)

        respuesta: JSONResponse | None = None
        if key == API_KEY_HOST_MALO:
            respuesta = JSONResponse({"error": "host no reconocido"}, status_code=421)
        elif not key or key == API_KEY_INVALIDA:
            respuesta = JSONResponse({"error": "la key no existe o fue revocada"}, status_code=401)
        elif key == API_KEY_SIN_PLAN:
            respuesta = JSONResponse({"error": "tu plan no incluye acceso a api_datos"}, status_code=403)
        elif key == API_KEY_SIN_CUOTA:
            respuesta = JSONResponse({"error": "cuota mensual excedida: 10000/10000"}, status_code=429)

        if respuesta is not None:
            await respuesta(scope, receive, send)
            return

        await app_mcp(scope, receive, send)

    return con_autenticacion


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def app_simulada_mpbot():
    """La app ASGI del servidor MCP simulado, con la capa de autenticación falsa.

    `httpx.ASGITransport` no dispara los eventos de ciclo de vida ASGI
    (`lifespan`), así que el `session_manager` de FastMCP —que normalmente
    arranca ahí— se ejecuta acá a mano, con la misma duración que el test.
    """
    servidor = _construir_mcp()
    app_mcp = servidor.streamable_http_app()  # crea el session_manager (lazy)

    async with servidor.session_manager.run():
        yield _envolver_con_autenticacion(app_mcp)


@pytest.fixture
def fabrica_http_simulada(app_simulada_mpbot) -> Callable[[str], httpx.AsyncClient]:
    """Fábrica inyectable en `ClienteMpbot(fabrica_http_client=...)` para no salir a la red."""

    def fabrica(api_key: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_simulada_mpbot),
            base_url="http://mpbot.test",
            headers={"Authorization": f"Bearer {api_key}"},
        )

    return fabrica


@pytest.fixture
def fabrica_http_sin_red() -> Callable[[str], httpx.AsyncClient]:
    """Fábrica que simula una caída de red/TLS/proxy: nunca llega al servidor."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no se pudo establecer conexión", request=request)

    def fabrica(api_key: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    return fabrica
