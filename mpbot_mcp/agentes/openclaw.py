"""Perfil de OpenClaw.

Config en `~/.openclaw/config.json`, clave `mcp.servers.<id>` con
`transport: "streamable-http"` + `url` + `headers` (research §3/§4,
documentación oficial de OpenClaw).

**Sin verificar en vivo todavía** (`verificado_en=None`): no se presenta como
compatible hasta completar el protocolo de research §6 (T024, fuera de
alcance de esta corrida).
"""

from __future__ import annotations

from pathlib import Path

from .perfil import PerfilAgente


def _directorio_base() -> Path:
    return Path.home() / ".openclaw"


def _rutas_deteccion() -> list[Path]:
    return [_directorio_base()]


def _ruta_archivo_config() -> Path:
    return _directorio_base() / "config.json"


def _entrada_directa(url_servidor: str, api_key: str) -> dict:
    return {
        "transport": "streamable-http",
        "url": url_servidor,
        "headers": {"Authorization": f"Bearer {api_key}"},
    }


def _entrada_stdio(ruta_ejecutable: str) -> dict:
    return {"command": ruta_ejecutable, "args": ["servir"]}


PERFIL = PerfilAgente(
    id="openclaw",
    nombre="OpenClaw",
    rutas_deteccion=_rutas_deteccion,
    ruta_archivo_config=_ruta_archivo_config,
    formato="json",
    ruta_en_archivo=["mcp", "servers"],
    soporta_directo=True,
    soporta_stdio=True,
    construir_entrada_directa=_entrada_directa,
    construir_entrada_stdio=_entrada_stdio,
    verificado_en=None,
)
