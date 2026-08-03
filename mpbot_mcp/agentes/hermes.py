"""Perfil de Hermes.

**Corrección real (2026-08-03, auditoría en vivo)**: la primera versión de
este perfil asumía `~/.hermes/cli-config.yaml` en toda plataforma. Contra la
instalación real de Hermes en la máquina de desarrollo, eso era **doblemente
falso**: el archivo real se llama `config.yaml` (no `cli-config.yaml` — ese
nombre es solo el de `cli-config.yaml.example`, la plantilla de ejemplo
empaquetada con el código fuente, nunca la config viva), y en Windows nativo
Hermes resuelve su directorio a `%LOCALAPPDATA%\\hermes` (variable
`HERMES_HOME`, confirmado en `hermes_cli/auth.py` del propio Hermes:
*"``%LOCALAPPDATA%\\hermes`` on native Windows"*), no `~/.hermes`.

`~/.hermes/` sí puede existir igual (Hermes deja ahí otros artefactos, como
una carpeta `scripts/`), lo que producía un **falso positivo de detección**:
el conector habría reportado "✔ configurado" sin que Hermes viera jamás esa
entrada — el fallo silencioso exacto que el Principio II existe para
prevenir.

Se respeta `HERMES_HOME` si el usuario la tiene fijada (mismo criterio que el
propio Hermes), con fallback a `%LOCALAPPDATA%\\hermes` en Windows y
`~/.hermes` en el resto.

**Sin verificar en vivo todavía** (`verificado_en=None`): esta corrección
arregla la ruta según el código fuente de Hermes, pero el protocolo completo
de verificación (research §6: configurar → listar tools → ejecutar una tool)
sigue pendiente (T024) antes de declararlo compatible.
"""

from __future__ import annotations

import os
import platform
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
    verificado_en=None,
)
