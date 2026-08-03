"""Perfil de Claude Code.

Config de usuario en `~/.claude.json`, clave `mcpServers` (research §4).
Admite conexión directa por HTTP con headers propios, y también puede lanzar
un programa local (stdio).

**Sin verificar en vivo todavía** (`verificado_en=None`): no se presenta como
compatible hasta completar el protocolo de research §6 (T024, fuera de
alcance de esta corrida).
"""

from __future__ import annotations

from pathlib import Path

from .perfil import PerfilAgente


def _rutas_deteccion() -> list[Path]:
    home = Path.home()
    return [home / ".claude.json", home / ".claude"]


def _ruta_archivo_config() -> Path:
    return Path.home() / ".claude.json"


def _entrada_directa(url_servidor: str, api_key: str) -> dict:
    return {
        "type": "http",
        "url": url_servidor,
        "headers": {"Authorization": f"Bearer {api_key}"},
    }


def _entrada_stdio(ruta_ejecutable: str) -> dict:
    return {"command": ruta_ejecutable, "args": ["servir"]}


PERFIL = PerfilAgente(
    id="claude-code",
    nombre="Claude Code",
    rutas_deteccion=_rutas_deteccion,
    ruta_archivo_config=_ruta_archivo_config,
    formato="json",
    ruta_en_archivo=["mcpServers"],
    soporta_directo=True,
    soporta_stdio=True,
    construir_entrada_directa=_entrada_directa,
    construir_entrada_stdio=_entrada_stdio,
    verificado_en=None,
)
