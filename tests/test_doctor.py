"""Tests del comando `doctor` (US2, T025–T028).

Los 7 pasos se ejecutan en el orden fijo de data-model.md §3; un paso que
falla marca los siguientes como `omitido` sin abortar el reporte (FR-010);
los cuatro modos de falla (credencial, plan, cuota, conectividad) producen
mensajes distintos (FR-011); la key literal nunca aparece en la salida
(SC-004); y `doctor` es útil incluso sin configuración previa (FR-013).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mpbot_mcp import config
from mpbot_mcp.agentes.perfil import PerfilAgente
from mpbot_mcp.cli import ejecutar_diagnostico
from mpbot_mcp.doctor import formatear_reporte

from .conftest import (
    API_KEY_HOST_MALO,
    API_KEY_INVALIDA,
    API_KEY_SIN_CUOTA,
    API_KEY_SIN_PLAN,
    API_KEY_VALIDA,
    URL_SERVIDOR_SIMULADO,
)

pytestmark = pytest.mark.anyio

NOMBRES_PASOS = [
    "API key",
    "Conectividad",
    "Autenticación",
    "Plan",
    "Cuota",
    "Tools",
    "Agentes",
]

# Registro aislado para no depender de los agentes instalados en la máquina
# donde corre la suite (constitución: los tests no tocan el equipo real).
REGISTRO_VACIO: list[PerfilAgente] = []


def _perfil_dummy(tmp_path: Path, *, instalado: bool, con_entrada_mpbot: bool = False) -> PerfilAgente:
    directorio = tmp_path / "agente"
    if instalado:
        directorio.mkdir(parents=True, exist_ok=True)
    archivo = directorio / "config.json"
    if instalado and con_entrada_mpbot:
        archivo.write_text(
            '{"mcpServers": {"mpbot": {"url": "https://app.mpbot.cl/mcp/"}}}',
            encoding="utf-8",
        )
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


@pytest.fixture(autouse=True)
def _config_aislada(tmp_path, monkeypatch):
    monkeypatch.setenv("MPBOT_CONFIG_DIR", str(tmp_path / "mpbot-mcp"))
    monkeypatch.delenv("MPBOT_API_KEY", raising=False)
    monkeypatch.delenv("MPBOT_URL", raising=False)
    yield


def _guardar_key(api_key: str, url: str = URL_SERVIDOR_SIMULADO) -> None:
    config.guardar(config.ConfiguracionConector(api_key=api_key, url_servidor=url))


async def test_sin_configuracion_previa_es_util_y_no_falla_tecnico(fabrica_http_simulada, monkeypatch):
    """FR-013: doctor sin key dice exactamente qué falta, sin crash."""
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )

    assert not reporte.todo_ok
    assert [p.nombre for p in reporte.pasos] == NOMBRES_PASOS
    assert reporte.pasos[0].estado == "falla"
    assert "API key" in reporte.pasos[0].detalle
    # Sin key, nada de red: el resto queda omitido, no falla técnico.
    assert all(p.estado == "omitido" for p in reporte.pasos[1:])


async def test_todo_ok_con_key_valida(fabrica_http_simulada):
    _guardar_key(API_KEY_VALIDA)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )

    assert reporte.todo_ok is True
    assert [p.nombre for p in reporte.pasos] == NOMBRES_PASOS
    assert all(p.estado == "ok" for p in reporte.pasos)
    assert reporte.pasos[5].detalle == "2 tools disponibles"


# --- Los 4 modos de falla producen mensajes distintos (FR-011) ----------


async def test_credencial_invalida_falla_solo_autenticacion(fabrica_http_simulada):
    _guardar_key(API_KEY_INVALIDA)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )

    estados = [p.estado for p in reporte.pasos]
    assert estados == ["ok", "ok", "falla", "omitido", "omitido", "omitido", "omitido"]
    assert reporte.pasos[2].detalle != reporte.pasos[3].detalle  # no genérico


async def test_plan_insuficiente_falla_solo_plan(fabrica_http_simulada):
    _guardar_key(API_KEY_SIN_PLAN)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )

    estados = [p.estado for p in reporte.pasos]
    assert estados == ["ok", "ok", "ok", "falla", "omitido", "omitido", "omitido"]


async def test_cuota_agotada_falla_solo_cuota(fabrica_http_simulada):
    _guardar_key(API_KEY_SIN_CUOTA)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )

    estados = [p.estado for p in reporte.pasos]
    assert estados == ["ok", "ok", "ok", "ok", "falla", "omitido", "omitido"]


async def test_conectividad_falla_primero_y_omite_el_resto(fabrica_http_sin_red):
    _guardar_key(API_KEY_VALIDA)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_sin_red, registro=REGISTRO_VACIO
    )

    estados = [p.estado for p in reporte.pasos]
    assert estados == ["ok", "falla", "omitido", "omitido", "omitido", "omitido", "omitido"]
    assert "red" in reporte.pasos[1].detalle.lower() or "contactar" in reporte.pasos[1].detalle.lower()


async def test_host_no_reconocido_es_falla_de_conectividad_no_de_key(fabrica_http_simulada):
    """421 no debe confundirse con credenciales (contracts/servidor-mpbot.md)."""
    _guardar_key(API_KEY_HOST_MALO)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )

    assert reporte.pasos[1].estado == "falla"  # Conectividad
    assert reporte.pasos[2].estado == "omitido"  # Autenticación no se evalúa


# --- SC-004: la key literal nunca aparece en la salida --------------------


@pytest.mark.parametrize(
    "api_key",
    [API_KEY_VALIDA, API_KEY_INVALIDA, API_KEY_SIN_PLAN, API_KEY_SIN_CUOTA, API_KEY_HOST_MALO],
)
async def test_la_key_literal_nunca_aparece_en_la_salida(api_key, fabrica_http_simulada):
    _guardar_key(api_key)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )
    texto = formatear_reporte(reporte)

    assert api_key not in texto
    assert "…" in texto  # la key enmascarada sí aparece


async def test_el_reporte_formateado_dice_todo_en_orden(fabrica_http_simulada):
    _guardar_key(API_KEY_VALIDA)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )
    texto = formatear_reporte(reporte)

    assert "Todo en orden." in texto
    assert "mpbot-mcp · diagnóstico" in texto


async def test_el_reporte_formateado_dice_se_encontraron_problemas(fabrica_http_simulada):
    _guardar_key(API_KEY_INVALIDA)
    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=REGISTRO_VACIO
    )
    texto = formatear_reporte(reporte)

    assert "Se encontraron problemas" in texto


# --- Paso Agentes: estado de configuración de agentes detectados (T031) ----


async def test_agente_detectado_sin_configurar_marca_falla(fabrica_http_simulada, tmp_path):
    _guardar_key(API_KEY_VALIDA)
    perfil = _perfil_dummy(tmp_path, instalado=True, con_entrada_mpbot=False)

    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=[perfil]
    )

    paso_agentes = reporte.pasos[-1]
    assert paso_agentes.estado == "falla"
    assert "sin conectar" in paso_agentes.detalle
    assert "instalar" in (paso_agentes.accion or "")


async def test_agente_detectado_y_configurado_marca_ok(fabrica_http_simulada, tmp_path):
    _guardar_key(API_KEY_VALIDA)
    perfil = _perfil_dummy(tmp_path, instalado=True, con_entrada_mpbot=True)

    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=[perfil]
    )

    paso_agentes = reporte.pasos[-1]
    assert paso_agentes.estado == "ok"
    assert "configurados" in paso_agentes.detalle


async def test_sin_agentes_detectados_es_ok_informativo(fabrica_http_simulada, tmp_path):
    _guardar_key(API_KEY_VALIDA)
    perfil = _perfil_dummy(tmp_path, instalado=False)

    reporte = await ejecutar_diagnostico(
        fabrica_http_client=fabrica_http_simulada, registro=[perfil]
    )

    paso_agentes = reporte.pasos[-1]
    assert paso_agentes.estado == "ok"
    assert "no se detectaron agentes" in paso_agentes.detalle
