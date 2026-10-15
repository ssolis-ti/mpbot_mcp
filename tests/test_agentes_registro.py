"""Tests del registro dinámico de agentes: autodescubrimiento por convención.

Un módulo dentro de `mpbot_mcp/agentes/` que exponga un `PERFIL` (instancia
de `PerfilAgente`) entra solo al registro — sin tocar `__init__.py`. Los
módulos cuyo nombre empieza con `_` (privados, como `_template.py`) se
ignoran a propósito.
"""

from __future__ import annotations

import sys
from pathlib import Path

from mpbot_mcp.agentes import REGISTRO, _construir_registro
from mpbot_mcp.agentes.perfil import PerfilAgente

IDS_CONOCIDOS = {"claude-code", "claude-desktop", "hermes", "openclaw"}


def test_registro_incluye_los_cuatro_agentes_conocidos():
    ids = {perfil.id for perfil in REGISTRO}
    assert IDS_CONOCIDOS <= ids


def test_registro_no_tiene_ids_duplicados():
    ids = [perfil.id for perfil in REGISTRO]
    assert len(ids) == len(set(ids))


def test_todo_elemento_del_registro_es_un_perfil():
    assert all(isinstance(perfil, PerfilAgente) for perfil in REGISTRO)


def _escribir_modulo_agente_de_prueba(nombre: str, contenido: str) -> Path:
    """Escribe un módulo real dentro del paquete `agentes/` (editable install)."""
    paquete_dir = Path(__file__).resolve().parent.parent / "mpbot_mcp" / "agentes"
    ruta = paquete_dir / f"{nombre}.py"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _limpiar_modulo(nombre: str, ruta: Path) -> None:
    ruta.unlink(missing_ok=True)
    sys.modules.pop(f"mpbot_mcp.agentes.{nombre}", None)


def test_modulo_nuevo_con_perfil_entra_solo_al_registro():
    nombre = "agente_descubierto_prueba"
    ruta = _escribir_modulo_agente_de_prueba(
        nombre,
        "from mpbot_mcp.agentes.perfil import PerfilAgente\n"
        "PERFIL = PerfilAgente(\n"
        "    id='descubierto-prueba', nombre='Agente descubierto',\n"
        "    rutas_deteccion=lambda: [], ruta_archivo_config=lambda: __import__('pathlib').Path('x'),\n"
        "    formato='json', ruta_en_archivo=['mcpServers'],\n"
        "    soporta_directo=True, soporta_stdio=False,\n"
        "    construir_entrada_directa=lambda url, key: {'url': url},\n"
        "    construir_entrada_stdio=None, verificado_en=None,\n"
        ")\n",
    )
    try:
        registro = _construir_registro()
        assert any(p.id == "descubierto-prueba" for p in registro)
    finally:
        _limpiar_modulo(nombre, ruta)


def test_modulo_sin_perfil_no_rompe_ni_entra():
    nombre = "modulo_sin_perfil_prueba"
    ruta = _escribir_modulo_agente_de_prueba(nombre, "VALOR_INOCUO = 42\n")
    try:
        registro = _construir_registro()
        assert all(p.id != "modulo-sin-perfil" for p in registro)
    finally:
        _limpiar_modulo(nombre, ruta)
