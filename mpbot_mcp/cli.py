"""Punto de entrada de línea de comandos: `instalar` (US1). `doctor` y
`servir` se agregan en fases posteriores (ver tasks.md, Fases 4 y 5).
"""

from __future__ import annotations

import asyncio
import dataclasses
import sys
from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import config
from .agentes import ConfiguracionAgenteInvalida, REGISTRO, detectar_agentes, escribir_config
from .agentes.perfil import PerfilAgente
from .cliente import ClienteMpbot
from .doctor import ejecutar_diagnostico, formatear_reporte
from .errores import ErrorMpbot

app = typer.Typer(add_completion=False, no_args_is_help=True)
_consola = Console()


@app.callback()
def _raiz() -> None:
    """mpbot-mcp: conector de mpbot para agentes de IA.

    Un `@app.callback()` vacío es lo que le dice a Typer que exija el nombre
    del subcomando (`instalar`, y más adelante `doctor`/`servir`) en vez de
    colapsar a un único comando implícito cuando solo hay uno registrado.
    """

ConfirmarFn = Callable[[list[tuple[PerfilAgente, Path]]], bool]


@dataclasses.dataclass
class ResultadoInstalacionAgente:
    perfil: PerfilAgente
    ok: bool
    modo: str | None = None
    ruta: Path | None = None
    respaldo: Path | None = None
    error_mensaje: str | None = None


@dataclasses.dataclass
class ResultadoInstalar:
    ok: bool
    tools_disponibles: int | None = None
    error: ErrorMpbot | None = None
    sin_agentes_detectados: bool = False
    cancelado_por_el_usuario: bool = False
    agentes_configurados: list[ResultadoInstalacionAgente] = dataclasses.field(default_factory=list)


def ruta_ejecutable_actual() -> str:
    """Ruta absoluta a este mismo programa, para configurar el modo puente (US3)."""
    return str(Path(sys.argv[0]).resolve())


async def ejecutar_instalar(
    *,
    api_key: str,
    url_servidor: str = config.URL_POR_DEFECTO,
    registro: list[PerfilAgente] | None = None,
    agentes_elegidos: list[str] | None = None,
    confirmar: ConfirmarFn = lambda _detectados: True,
    ruta_ejecutable: str | None = None,
) -> ResultadoInstalar:
    """El flujo de 7 pasos de contracts/cli.md, sin nada de E/S de terminal.

    Separado de la capa Typer a propósito: así se puede probar sin simular
    una sesión interactiva de verdad.
    """
    # Paso 3: validar la key contra el servidor real ANTES de tocar nada (FR-003).
    try:
        async with ClienteMpbot(api_key, url_servidor) as cliente:
            tools = await cliente.listar_tools()
    except ErrorMpbot as error:
        return ResultadoInstalar(ok=False, error=error)

    # Paso 1: detectar agentes instalados.
    detectados = detectar_agentes(registro)
    if agentes_elegidos is not None:
        detectados = [(perfil, ruta) for perfil, ruta in detectados if perfil.id in agentes_elegidos]

    if not detectados:
        # La key ya sirve: se guarda igual, para que `doctor`/`servir` la usen,
        # aunque no haya ningún agente al que escribirle (edge case: no es un error).
        config.guardar(config.ConfiguracionConector(api_key=api_key, url_servidor=url_servidor))
        return ResultadoInstalar(ok=True, tools_disponibles=len(tools), sin_agentes_detectados=True)

    # Paso 4: confirmación explícita antes de modificar cualquier archivo (FR-004).
    if not confirmar(detectados):
        return ResultadoInstalar(ok=False, cancelado_por_el_usuario=True)

    config.guardar(config.ConfiguracionConector(api_key=api_key, url_servidor=url_servidor))

    ejecutable = ruta_ejecutable or ruta_ejecutable_actual()
    resultados: list[ResultadoInstalacionAgente] = []

    for perfil, ruta in detectados:
        modo = "directo" if perfil.soporta_directo else "stdio"
        entrada = (
            perfil.construir_entrada_directa(url_servidor, api_key)
            if modo == "directo"
            else perfil.construir_entrada_stdio(ejecutable)
        )
        try:
            # Paso 5 (respaldo) y 6 (escritura preservando lo demás) los hace escribir_config.
            resultado_escritura = escribir_config(perfil, ruta, entrada)
        except (PermissionError, OSError, ConfiguracionAgenteInvalida) as exc:
            resultados.append(ResultadoInstalacionAgente(perfil=perfil, ok=False, error_mensaje=str(exc)))
            continue

        resultados.append(
            ResultadoInstalacionAgente(
                perfil=perfil,
                ok=True,
                modo=modo,
                ruta=resultado_escritura.ruta,
                respaldo=(resultado_escritura.respaldo.ruta_respaldo if resultado_escritura.respaldo else None),
            )
        )

    # Paso 7: verificación de punta a punta ya ocurrió arriba (handshake + tools/list);
    # `tools_disponibles` es justamente ese resultado (FR-008).
    return ResultadoInstalar(ok=True, tools_disponibles=len(tools), agentes_configurados=resultados)


def _mostrar_confirmacion(detectados: list[tuple[PerfilAgente, Path]]) -> bool:
    tabla = Table(title="Se va a modificar la configuración de estos agentes")
    tabla.add_column("Agente")
    tabla.add_column("Archivo")
    tabla.add_column("Modo")
    for perfil, ruta in detectados:
        modo = "directo (con headers)" if perfil.soporta_directo else "puente local (stdio)"
        tabla.add_row(perfil.nombre, str(ruta), modo)
    _consola.print(tabla)

    # Principio IV: la API key es un secreto. Si algún agente va por conexión
    # directa, su propia key queda escrita en texto plano en SU archivo de
    # configuración (no solo en el nuestro) — hay que decirlo antes de escribir.
    agentes_con_key_en_su_config = [perfil.nombre for perfil, _ in detectados if perfil.soporta_directo]
    if agentes_con_key_en_su_config:
        lista = ", ".join(agentes_con_key_en_su_config)
        _consola.print(
            f"[yellow]⚠[/yellow]  Tu API key quedará escrita en texto plano en la configuración de: {lista}."
        )

    return typer.confirm("¿Continuar?")


def _reportar_resultado(resultado: ResultadoInstalar) -> int:
    if resultado.error is not None:
        _consola.print(f"[red]✘[/red] {resultado.error.mensaje}")
        if resultado.error.accion:
            _consola.print(f"  → {resultado.error.accion}")
        return 1

    if resultado.cancelado_por_el_usuario:
        _consola.print("Operación cancelada: no se modificó ningún archivo.")
        return 1

    if resultado.sin_agentes_detectados:
        _consola.print("Tu API key es válida y quedó guardada, pero no se detectó ningún agente soportado en este equipo.")
        _consola.print("Puedes conectar tu agente a mano — ver la documentación en docs/agentes/.")
        return 0

    for r in resultado.agentes_configurados:
        if r.ok:
            _consola.print(f"[green]✔[/green] {r.perfil.nombre}: configurado ({r.modo}) en {r.ruta}")
            if r.respaldo:
                _consola.print(f"  Respaldo de tu configuración anterior en: {r.respaldo}")
        else:
            _consola.print(f"[red]✘[/red] {r.perfil.nombre}: no se pudo escribir su configuración ({r.error_mensaje})")

    _consola.print(f"\n[green]Listo.[/green] {resultado.tools_disponibles} tools de mpbot disponibles.")
    return 0


@dataclasses.dataclass(frozen=True)
class EstadoAgente:
    """Resumen de un agente soportado para `listar-agentes`."""

    id: str
    nombre: str
    formato: str
    verificado: bool
    fecha_verificacion: str | None
    soporta_directo: bool
    soporta_stdio: bool


def resumen_agentes(registro: list[PerfilAgente] | None = None) -> list[EstadoAgente]:
    """Estado de cada agente soportado, en orden del registro.

    Lógica pura (sin E/S): la presentación la hace el comando Typer. Un
    agente con `verificado_en=None` se reporta como no verificado
    (Principio II: compatibilidad jamás declarada).
    """
    return [
        EstadoAgente(
            id=perfil.id,
            nombre=perfil.nombre,
            formato=perfil.formato,
            verificado=perfil.esta_verificado(),
            fecha_verificacion=(
                perfil.verificado_en.isoformat() if perfil.verificado_en else None
            ),
            soporta_directo=perfil.soporta_directo,
            soporta_stdio=perfil.soporta_stdio,
        )
        for perfil in (registro if registro is not None else REGISTRO)
    ]


@app.command()
def listar_agentes() -> None:
    """Muestra los agentes soportados y su estado de verificación."""
    tabla = Table(title="Agentes soportados por mpbot-mcp")
    tabla.add_column("Agente")
    tabla.add_column("Id")
    tabla.add_column("Formato")
    tabla.add_column("Verificado")
    tabla.add_column("Conexión")

    for estado in resumen_agentes():
        verificacion = (
            f"[green]✔ {estado.fecha_verificacion}[/green]"
            if estado.verificado
            else "[yellow]no verificado[/yellow]"
        )
        modos = []
        if estado.soporta_directo:
            modos.append("directa")
        if estado.soporta_stdio:
            modos.append("puente")
        tabla.add_row(
            estado.nombre,
            estado.id,
            estado.formato,
            verificacion,
            " + ".join(modos),
        )

    _consola.print(tabla)
    _consola.print(
        "[dim]Los agentes marcados como «no verificado» no se declaran compatibles "
        "hasta pasar la verificación en vivo (constitución, Principio II).[/dim]"
    )


@app.command()
def doctor() -> None:
    """Diagnostica en lenguaje llano por qué algo no funciona."""
    reporte = asyncio.run(ejecutar_diagnostico())
    _consola.print(formatear_reporte(reporte))
    if not reporte.todo_ok:
        raise typer.Exit(code=1)


@app.command()
def instalar(
    api_key: str | None = typer.Option(
        None, "--api-key", envvar="MPBOT_API_KEY", help="Tu API key de mpbot (mpb_...). Si no se indica, se pide de forma interactiva."
    ),
    url_servidor: str = typer.Option(config.URL_POR_DEFECTO, "--url", envvar="MPBOT_URL", help="Endpoint del servidor MCP de mpbot."),
    agentes: list[str] = typer.Option([], "--agente", help="Restringe la instalación a estos ids de agente (repetible). Por defecto, todos los detectados."),
    sin_confirmar: bool = typer.Option(False, "--si", "-y", help="No pedir confirmación antes de escribir (para automatización)."),
) -> None:
    """Detecta tus agentes, pide tu API key y los deja conectados a mpbot."""
    if not api_key:
        api_key = typer.prompt("Tu API key de mpbot (mpb_...)", hide_input=True)

    confirmar: ConfirmarFn = (lambda _detectados: True) if sin_confirmar else _mostrar_confirmacion

    resultado = asyncio.run(
        ejecutar_instalar(
            api_key=api_key,
            url_servidor=url_servidor,
            agentes_elegidos=agentes or None,
            confirmar=confirmar,
        )
    )

    codigo_salida = _reportar_resultado(resultado)
    raise typer.Exit(code=codigo_salida)


if __name__ == "__main__":
    app()
