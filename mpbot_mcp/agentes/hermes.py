"""Perfil de Hermes.

Config en `config.yaml`, clave `mcp_servers`. Se respeta `HERMES_HOME` si
está definida (mismo criterio que el propio Hermes), con fallback a
`%LOCALAPPDATA%\\hermes` en Windows y `~/.hermes` en el resto.

Se detecta por el archivo `config.yaml` y no solo por el directorio: este
puede existir por otras razones sin que Hermes lea nada de ahí.
"""

from __future__ import annotations

import os
import platform
from datetime import date
from pathlib import Path

from .perfil import PerfilAgente


def _directorio_base() -> Path:
    override = os.environ.get("HERMES_HOME")
    if override:
        return Path(override)
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "hermes"
    return Path.home() / ".hermes"


def _rutas_deteccion() -> list[Path]:
    return [_directorio_base() / "config.yaml"]


def _ruta_archivo_config() -> Path:
    return _directorio_base() / "config.yaml"


def _entrada_directa(url_servidor: str, api_key: str) -> dict:
    return {
        "url": url_servidor,
        "headers": {"Authorization": f"Bearer {api_key}"},
    }


def _entrada_stdio(ruta_ejecutable: str) -> dict:
    return {"command": ruta_ejecutable, "args": ["servir"]}


PERFIL = PerfilAgente(
    id="hermes",
    nombre="Hermes",
    rutas_deteccion=_rutas_deteccion,
    ruta_archivo_config=_ruta_archivo_config,
    formato="yaml",
    ruta_en_archivo=["mcp_servers"],
    soporta_directo=True,
    soporta_stdio=True,
    construir_entrada_directa=_entrada_directa,
    construir_entrada_stdio=_entrada_stdio,
    verificado_en=date(2026, 8, 2),
)
