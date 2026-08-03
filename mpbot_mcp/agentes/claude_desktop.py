"""Perfil de Claude Desktop.

Config en `claude_desktop_config.json`, clave `mcpServers` (research §4).
Su soporte de conexión directa con headers está "por confirmar": mientras no
se verifique en vivo (T024, fuera de alcance de esta corrida), se trata como
agente **solo stdio** — así el conector nunca escribe la API key en su
config sin haber confirmado que hace falta (Principio IV).

**Sin verificar en vivo todavía** (`verificado_en=None`).
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

from .perfil import PerfilAgente


def _directorio_base() -> Path:
    sistema = platform.system()
    if sistema == "Windows":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "Claude"
    if sistema == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude"
    return Path.home() / ".config" / "Claude"


def _rutas_deteccion() -> list[Path]:
    return [_directorio_base()]


def _ruta_archivo_config() -> Path:
    return _directorio_base() / "claude_desktop_config.json"


def _entrada_stdio(ruta_ejecutable: str) -> dict:
    return {"command": ruta_ejecutable, "args": ["servir"]}


PERFIL = PerfilAgente(
    id="claude-desktop",
    nombre="Claude Desktop",
    rutas_deteccion=_rutas_deteccion,
    ruta_archivo_config=_ruta_archivo_config,
    formato="json",
    ruta_en_archivo=["mcpServers"],
    soporta_directo=False,
    soporta_stdio=True,
    construir_entrada_directa=None,
    construir_entrada_stdio=_entrada_stdio,
    verificado_en=None,
)
