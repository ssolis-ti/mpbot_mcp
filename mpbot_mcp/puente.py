"""Modo puente (US3): servidor MCP local por stdio que reexpone dinámicamente
las tools remotas de mpbot.

Lo lanza el agente (o cualquier programa que solo sepa lanzar un ejecutable
local), no la persona. Habla MCP por stdio hacia adentro y MCP Streamable
HTTP hacia mpbot, con la credencial que toma de su propio almacenamiento o
del entorno (FR-015) — nunca de la config del agente que lo lanzó, que es
justamente el problema que este modo existe para evitar.

Reexpone EXACTAMENTE lo que el servidor remoto declara en cada momento
(FR-016): nada de lista propia, filtrado ni transformación (Principio III).

Un único `ClienteMpbot` se abre al arrancar y se reusa para toda la vida del
proceso — no se reconecta en bucle, la cuota cuenta cada handshake
(contracts/servidor-mpbot.md).

Sobre el manejo de errores: no hace falta capturar `ErrorMpbot` a mano
adentro de los handlers. El SDK oficial (`Server._handle_request`, con
`raise_exceptions=False` por defecto) ya convierte cualquier excepción de un
handler en una respuesta de error MCP en vez de tumbar el proceso o dejarlo
colgado (FR-017) — y como `ErrorMpbot.__str__()` ya trae el mensaje en
español más la acción sugerida, ese texto llega tal cual al agente.
"""

from __future__ import annotations

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from .cliente import ClienteMpbot


def construir_servidor(cliente: ClienteMpbot) -> Server:
    """Arma el servidor MCP local que reexpone lo que declare `cliente`.

    `cliente` debe estar ya conectado (dentro de su propio `async with`).
    Cada `list_tools`/`call_tool` vuelve a preguntarle al servidor remoto:
    nunca hay un catálogo propio que se pueda desactualizar.
    """
    servidor: Server = Server("mpbot-mcp")

    @servidor.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return await cliente.listar_tools()

    @servidor.call_tool(validate_input=False)
    async def _call_tool(nombre: str, argumentos: dict) -> types.CallToolResult:
        return await cliente.llamar_tool(nombre, argumentos)

    return servidor


async def ejecutar_puente(cliente: ClienteMpbot) -> None:
    """Corre el servidor MCP local por stdio hasta que el agente lo cierre."""
    servidor = construir_servidor(cliente)
    opciones_inicializacion = servidor.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await servidor.run(read_stream, write_stream, opciones_inicializacion)
