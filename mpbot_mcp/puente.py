"""Modo puente: servidor MCP local por stdio que reexpone las tools remotas
de mpbot.

Lo lanza el agente (o cualquier programa que solo sepa lanzar un ejecutable
local), no la persona. Habla MCP por stdio hacia adentro y MCP Streamable
HTTP hacia mpbot, con la credencial de la configuración guardada o del
entorno, nunca de la config del agente que lo lanzó.

Reexpone exactamente lo que el servidor remoto declara en cada momento: sin
lista propia, filtrado ni transformación.

Un único `ClienteMpbot` se abre al arrancar y se reusa durante toda la vida
del proceso (conectarse no gasta créditos; solo las consultas de datos).

Los errores dentro de los handlers no se capturan a mano: el SDK de MCP ya
los convierte en una respuesta de error en vez de tumbar el proceso, y
`ErrorMpbot.__str__()` trae el mensaje en español con la acción sugerida.
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
