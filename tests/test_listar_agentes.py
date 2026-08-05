"""Tests del comando `listar-agentes` (resumen de agentes soportados).

La lógica pura (`resumen_agentes`) no hace E/S: se prueba aislada. El
contrato que se verifica: un agente con `verificado_en=None` se reporta
como no verificado (Principio II), y los cuatro conocidos aparecen con su
formato y modos de conexión.
"""

from __future__ import annotations

import datetime

from mpbot_mcp.agentes.perfil import PerfilAgente
from mpbot_mcp.cli import resumen_agentes


def _perfil_dummy(
    *,
    id: str = "dummy",
    verificado_en: datetime.date | None = None,
    soporta_directo: bool = True,
    soporta_stdio: bool = True,
    formato: str = "json",
) -> PerfilAgente:
    return PerfilAgente(
        id=id,
        nombre=id.title(),
        rutas_deteccion=lambda: [],
        ruta_archivo_config=lambda: __import__("pathlib").Path("x"),
        formato=formato,
        ruta_en_archivo=["mcpServers"],
        soporta_directo=soporta_directo,
        soporta_stdio=soporta_stdio,
        construir_entrada_directa=lambda url, key: {"url": url},
        construir_entrada_stdio=lambda ruta: {"command": ruta},
        verificado_en=verificado_en,
    )


def test_resumen_incluye_los_cuatro_agentes_conocidos():
    estados = resumen_agentes()
    ids = {e.id for e in estados}
    assert {"claude-code", "claude-desktop", "hermes", "openclaw"} <= ids


def test_agente_sin_verificar_se_reporta_como_no_verificado():
    estado = resumen_agentes([_perfil_dummy(verificado_en=None)])[0]
    assert estado.verificado is False
    assert estado.fecha_verificacion is None


def test_agente_verificado_reporta_fecha_iso():
    fecha = datetime.date(2026, 8, 5)
    estado = resumen_agentes([_perfil_dummy(verificado_en=fecha)])[0]
    assert estado.verificado is True
    assert estado.fecha_verificacion == "2026-08-05"


def test_modos_de_conexion_se_reportan_correctamente():
    solo_directo = resumen_agentes(
        [_perfil_dummy(soporta_directo=True, soporta_stdio=False)]
    )[0]
    assert solo_directo.soporta_directo is True
    assert solo_directo.soporta_stdio is False

    solo_puente = resumen_agentes(
        [_perfil_dummy(soporta_directo=False, soporta_stdio=True)]
    )[0]
    assert solo_puente.soporta_directo is False
    assert solo_puente.soporta_stdio is True


def test_formato_yaml_se_reporta():
    estado = resumen_agentes([_perfil_dummy(formato="yaml")])[0]
    assert estado.formato == "yaml"
