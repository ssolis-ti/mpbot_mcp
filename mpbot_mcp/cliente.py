"""Cliente MCP contra el servidor remoto de mpbot.

Una sola sesión reutilizable por instancia: la cuota del servidor cuenta cada
request HTTP, incluido el handshake (contracts/servidor-mpbot.md), así que
`doctor` y `instalar` deben abrir un único `ClienteMpbot` por corrida y
reusarlo para todas sus verificaciones.

Este módulo no interpreta el contenido de las tools (Principio III): solo
hace el handshake, descubre por protocolo y transporta.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

import httpx
import mcp.types as types
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from .errores import traducir_error

FabricaHttpClient = Callable[[str], httpx.AsyncClient]


def _fabrica_por_defecto(api_key: str) -> httpx.AsyncClient:
    return create_mcp_http_client(headers={"Authorization": f"Bearer {api_key}"})


class ClienteMpbot:
    """Handshake + `tools/list` + `tools/call` contra el servidor de mpbot.

    Uso:

        async with ClienteMpbot(api_key, url) as cliente:
            tools = await cliente.listar_tools()
            resultado = await cliente.llamar_tool(tools[0].name, {})

    Cualquier falla (autenticación, plan, cuota, red) llega como
    `errores.ErrorMpbot`, ya traducida a español con acción sugerida.
    """

    def __init__(
        self,
        api_key: str,
        url_servidor: str,
        *,
        fabrica_http_client: FabricaHttpClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._url = url_servidor
        self._fabrica = fabrica_http_client or _fabrica_por_defecto
        self._stack: contextlib.AsyncExitStack | None = None
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "ClienteMpbot":
        stack = contextlib.AsyncExitStack()
        try:
            http_client = self._fabrica(self._api_key)
            await stack.enter_async_context(http_client)
            read_stream, write_stream, _ = await stack.enter_async_context(
                streamable_http_client(self._url, http_client=http_client)
            )
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
        except BaseException as exc:
            await self._cerrar_y_traducir(stack, exc)

        self._stack = stack
        self.session = session
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
        self.session = None

    async def listar_tools(self) -> list[types.Tool]:
        if self.session is None:
            raise RuntimeError("ClienteMpbot debe usarse dentro de `async with ClienteMpbot(...) as cliente:`")
        try:
            resultado = await self.session.list_tools()
        except BaseException as exc:
            await self._cerrar_y_traducir(self._stack, exc)
        return resultado.tools

    async def llamar_tool(self, nombre: str, argumentos: dict[str, Any] | None = None) -> types.CallToolResult:
        if self.session is None:
            raise RuntimeError("ClienteMpbot debe usarse dentro de `async with ClienteMpbot(...) as cliente:`")
        try:
            return await self.session.call_tool(nombre, argumentos)
        except BaseException as exc:
            await self._cerrar_y_traducir(self._stack, exc)

    @staticmethod
    async def _cerrar_y_traducir(stack: contextlib.AsyncExitStack | None, exc_original: BaseException) -> None:
        """Traduce y relanza como `ErrorMpbot`.

        El transporte streamable-HTTP corre la petición en una tarea hija de
        un `anyio.TaskGroup`: cuando esa tarea falla (401/403/429/red), lo
        primero que ve quien está esperando (`initialize`/`list_tools`/
        `call_tool`) suele ser una cancelación, y el error real (el
        `httpx.HTTPStatusError` o `httpx.TransportError` con la causa
        concreta) solo aparece al cerrar el `AsyncExitStack`. Por eso hay que
        cerrar acá mismo y traducir lo que salga de ahí — no lo que llegó
        primero — para no perder el motivo real de la falla.
        """
        if stack is not None:
            try:
                await stack.aclose()
            except BaseException as exc_cierre:
                raise traducir_error(exc_cierre) from exc_cierre
        raise traducir_error(exc_original) from exc_original
