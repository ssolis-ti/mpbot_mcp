"""Perfil de Claude Desktop.

Config en `claude_desktop_config.json`, clave `mcpServers`. Se conecta en
modo puente (stdio): así la API key nunca queda escrita en su config.
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
