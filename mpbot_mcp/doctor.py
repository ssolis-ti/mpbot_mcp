"""Comando `doctor`: diagnóstico de 7 pasos en orden fijo (US2, T025–T031).

Ejecuta siempre los 7 pasos de [data-model.md §3] en su orden fijo:

    API key → Conectividad → Autenticación → Plan → Cuota → Tools → Agentes

Un paso que falla **no aborta** el reporte: los siguientes quedan
`omitido` con su motivo, para que la persona vea el cuadro completo de una
sola vez (FR-010). Las verificaciones de red usan **una sola sesión** con el
servidor (la cuota cuenta cada request, incluido el handshake —
contracts/servidor-mpbot.md).

La API key **nunca** se imprime completa en ningún detalle (FR-012 / SC-004):
toda mención pasa por `config.enmascarar`.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable
from typing import Literal

from . import config
from .agentes import (
    NOMBRE_SERVIDOR,
    REGISTRO,
    ConfiguracionAgenteInvalida,
    detectar_agentes,
    leer_config,
)
from .agentes.perfil import PerfilAgente
from .cliente import ClienteMpbot, FabricaHttpClient
from .errores import ErrorMpbot, TipoError

EstadoPaso = Literal["ok", "falla", "omitido"]

PASOS = (
    "API key",
    "Conectividad",
    "Autenticación",
    "Plan",
    "Cuota",
    "Tools",
    "Agentes",
)


@dataclasses.dataclass(frozen=True)
class PasoDiagnostico:
    """Un paso del diagnóstico (data-model.md §3)."""

    nombre: str
    estado: EstadoPaso
    detalle: str
    accion: str | None = None


@dataclasses.dataclass(frozen=True)
class ReporteDiagnostico:
    """Resultado completo de `doctor` (data-model.md §3)."""

    pasos: list[PasoDiagnostico]

    @property
    def todo_ok(self) -> bool:
        return all(paso.estado == "ok" for paso in self.pasos)


def _omitidos_desde(indice_inicio: int, motivo: str) -> list[PasoDiagnostico]:
    """Pasos que no se ejecutan porque uno anterior falló (FR-010)."""
    return [
        PasoDiagnostico(nombre=nombre, estado="omitido", detalle=f"omitido ({motivo})")
        for nombre in PASOS[indice_inicio:]
    ]


def _agente_esta_configurado(perfil: PerfilAgente, ruta) -> bool:
    """¿La config del agente ya tiene la entrada de mpbot?

    Si el archivo no se puede interpretar, se trata como no configurado:
    el usuario no puede saber si está conectado, y `instalar` lo arregla
    preservando lo que haya.
    """
    try:
        datos = leer_config(perfil, ruta)
    except ConfiguracionAgenteInvalida:
        return False
    contenedor: dict = datos
    for clave in perfil.ruta_en_archivo:
        siguiente = contenedor.get(clave)
        if not isinstance(siguiente, dict):
            return False
        contenedor = siguiente
    return NOMBRE_SERVIDOR in contenedor


async def ejecutar_diagnostico(
    *,
    fabrica_http_client: FabricaHttpClient | None = None,
    registro: list[PerfilAgente] | None = None,
) -> ReporteDiagnostico:
    """Ejecuta los 7 pasos en orden fijo contra el servidor (o el simulado).

    Lógica pura, sin E/S de terminal: la presentación la hace el comando
    Typer. Acepta `fabrica_http_client` para apuntar al servidor simulado en
    los tests (cero red, cero keys reales — constitución, sección tests).
    """
    pasos: list[PasoDiagnostico] = []

    cfg = config.cargar()

    # Paso 1: API key presente (FR-013: doctor es útil sin configuración previa).
    if cfg is None or not cfg.api_key:
        pasos.append(
            PasoDiagnostico(
                nombre="API key",
                estado="falla",
                detalle="No hay API key configurada.",
                accion="Ejecuta `mpbot-mcp instalar` para guardar tu key de app.mpbot.cl.",
            )
        )
        pasos.extend(_omitidos_desde(1, "depende de la API key"))
        return ReporteDiagnostico(pasos)

    pasos.append(
        PasoDiagnostico(
            nombre="API key",
            estado="ok",
            detalle=f"configurada ({config.enmascarar(cfg.api_key)})",
        )
    )

    # Pasos 2–6: una sola sesión, una sola conexión (economía de cuota).
    try:
        async with ClienteMpbot(
            cfg.api_key, cfg.url_servidor, fabrica_http_client=fabrica_http_client
        ) as cliente:
            inicio = time.monotonic()
            tools = await cliente.listar_tools()
            latencia_ms = int((time.monotonic() - inicio) * 1000)
    except ErrorMpbot as error:
        if error.tipo in (TipoError.CONECTIVIDAD, TipoError.HOST_NO_RECONOCIDO):
            pasos.append(
                PasoDiagnostico(
                    nombre="Conectividad",
                    estado="falla",
                    detalle=error.mensaje,
                    accion=error.accion,
                )
            )
            pasos.extend(_omitidos_desde(2, "depende de la conectividad"))
        elif error.tipo is TipoError.CREDENCIAL_INVALIDA:
            pasos.append(
                PasoDiagnostico(
                    nombre="Conectividad",
                    estado="ok",
                    detalle="el servidor responde",
                )
            )
            pasos.append(
                PasoDiagnostico(
                    nombre="Autenticación",
                    estado="falla",
                    detalle=error.mensaje,
                    accion=error.accion,
                )
            )
            pasos.extend(_omitidos_desde(3, "depende de la autenticación"))
        elif error.tipo is TipoError.PLAN_INSUFICIENTE:
            pasos.append(
                PasoDiagnostico(nombre="Conectividad", estado="ok", detalle="el servidor responde")
            )
            pasos.append(
                PasoDiagnostico(nombre="Autenticación", estado="ok", detalle="la key es válida")
            )
            pasos.append(
                PasoDiagnostico(
                    nombre="Plan",
                    estado="falla",
                    detalle=error.mensaje,
                    accion=error.accion,
                )
            )
            pasos.extend(_omitidos_desde(4, "depende del plan"))
        elif error.tipo is TipoError.CUOTA_AGOTADA:
            pasos.append(
                PasoDiagnostico(nombre="Conectividad", estado="ok", detalle="el servidor responde")
            )
            pasos.append(
                PasoDiagnostico(nombre="Autenticación", estado="ok", detalle="la key es válida")
            )
            pasos.append(
                PasoDiagnostico(
                    nombre="Plan",
                    estado="ok",
                    detalle="el plan incluye acceso al servidor MCP",
                )
            )
            pasos.append(
                PasoDiagnostico(
                    nombre="Cuota",
                    estado="falla",
                    detalle=error.mensaje,
                    accion=error.accion,
                )
            )
            pasos.extend(_omitidos_desde(5, "depende de la cuota"))
        else:  # DESCONOCIDO: se reporta en conectividad, no se esconde.
            pasos.append(
                PasoDiagnostico(
                    nombre="Conectividad",
                    estado="falla",
                    detalle=error.mensaje,
                    accion=error.accion,
                )
            )
            pasos.extend(_omitidos_desde(2, "depende de la conectividad"))
        return ReporteDiagnostico(pasos)

    pasos.append(
        PasoDiagnostico(
            nombre="Conectividad",
            estado="ok",
            detalle=f"el servidor responde ({latencia_ms} ms)",
        )
    )
    pasos.append(
        PasoDiagnostico(nombre="Autenticación", estado="ok", detalle="la key es válida")
    )
    pasos.append(
        PasoDiagnostico(
            nombre="Plan",
            estado="ok",
            detalle="el plan incluye acceso al servidor MCP",
        )
    )
    pasos.append(
        PasoDiagnostico(nombre="Cuota", estado="ok", detalle="cuota disponible")
    )
    pasos.append(
        PasoDiagnostico(
            nombre="Tools",
            estado="ok",
            detalle=f"{len(tools)} tools disponibles",
        )
    )

    # Paso 7: agentes detectados y su estado de configuración (T031).
    detectados = detectar_agentes(registro if registro is not None else REGISTRO)
    if not detectados:
        pasos.append(
            PasoDiagnostico(
                nombre="Agentes",
                estado="ok",
                detalle="no se detectaron agentes instalados en este equipo",
            )
        )
    else:
        configurados = [
            perfil.nombre for perfil, ruta in detectados if _agente_esta_configurado(perfil, ruta)
        ]
        sin_configurar = [
            perfil.nombre for perfil, ruta in detectados if not _agente_esta_configurado(perfil, ruta)
        ]
        if sin_configurar:
            pasos.append(
                PasoDiagnostico(
                    nombre="Agentes",
                    estado="falla",
                    detalle=f"detectados sin conectar: {', '.join(sin_configurar)}",
                    accion="Ejecuta `mpbot-mcp instalar` para conectarlos.",
                )
            )
        else:
            pasos.append(
                PasoDiagnostico(
                    nombre="Agentes",
                    estado="ok",
                    detalle=f"configurados: {', '.join(configurados)}",
                )
            )

    return ReporteDiagnostico(pasos)


def _texto_paso(paso: PasoDiagnostico) -> str:
    simbolos = {"ok": "✔", "falla": "✘", "omitido": "‑"}
    return f"{simbolos[paso.estado]} {paso.nombre}: {paso.detalle}"


def formatear_reporte(reporte: ReporteDiagnostico) -> str:
    """Texto llano del reporte, para `doctor` y para los tests (SC-004)."""
    lineas = ["mpbot-mcp · diagnóstico", ""]
    for paso in reporte.pasos:
        linea = _texto_paso(paso)
        if paso.accion:
            linea += f" → {paso.accion}"
        lineas.append("  " + linea)
    lineas.append("")
    lineas.append("Todo en orden." if reporte.todo_ok else "Se encontraron problemas: revisa los pasos marcados con ✘.")
    return "\n".join(lineas)
