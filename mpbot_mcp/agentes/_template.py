"""PLANTILLA para agregar un agente nuevo al conector.

Copia este archivo a `mpbot_mcp/agentes/<id-del-agente>.py` (sin el prefijo
`_`) y completa las funciones. El registro lo descubre solo: **no hay que
tocar ningún otro archivo** (ver `agentes/__init__.py`, `_construir_registro`).

Reglas de la casa (constitución):

1. **Principio II — Compatibilidad verificada, jamás declarada.** Un perfil
   con `verificado_en=None` NO se presenta como compatible: `listar-agentes`
   y la documentación lo marcan como "no verificado". Solo después de probar
   en vivo contra el agente real (configurar → listar tools → ejecutar una
   tool) se fija la fecha (ej. `datetime.date(2026, 8, 5)`) y se publica.

2. **Principio IV — La API key es un secreto.** Si el agente admite conexión
   directa (HTTP con headers), `soporta_directo=True` y la key queda en su
   config (se le advierte a la persona). Si no está confirmado, déjalo en
   `False`: el conector usará el modo puente (stdio) y la key nunca se
   escribe en la config del agente.

3. **Principio VII — Datos puros.** Un perfil describe CÓMO tratar a un
   agente (rutas, formato, claves). Toda la lógica compartida vive en
   `agentes/__init__.py`, una sola vez. Acá no se implementa lógica nueva.

4. Las rutas se resuelven a absolutas antes de escribirse. Usa `Path.home()`,
   `%APPDATA%`/`%LOCALAPPDATA%` (Windows) o XDG (Linux/macOS) — mira los
   perfiles existentes (`claude_code.py`, `hermes.py`) como referencia.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from .perfil import PerfilAgente


def _rutas_deteccion() -> list[Path]:
    """Dónde mirar para saber si el agente está instalado en este equipo.

    Se detecta por la PRESENCIA de archivo/directorio de configuración, nunca
    ejecutando el agente ni buscándolo en el PATH (research §5).
    """
    # TODO: reemplazar por las rutas reales del agente.
    return [Path.home() / ".mi-agente"]


def _ruta_archivo_config() -> Path:
    """Archivo de configuración exacto a leer/escribir (puede vivir fuera de
    las rutas de detección)."""
    # TODO: reemplazar por la ruta real del archivo de config.
    return Path.home() / ".mi-agente" / "config.json"


def _entrada_directa(url_servidor: str, api_key: str) -> dict:
    """Entrada a escribir en la config para conexión directa (HTTP con
    headers). Solo si `soporta_directo=True`."""
    return {
        "url": url_servidor,
        "headers": {"Authorization": f"Bearer {api_key}"},
    }


def _entrada_stdio(ruta_ejecutable: str) -> dict:
    """Entrada a escribir en la config para modo puente (el agente lanza
    `mpbot-mcp servir` como programa local; la key NO va en su config)."""
    return {"command": ruta_ejecutable, "args": ["servir"]}


PERFIL = PerfilAgente(
    id="mi-agente",  # Identificador estable, en minúsculas y con guiones.
    nombre="Mi Agente",  # Nombre legible que ve la persona.
    rutas_deteccion=_rutas_deteccion,
    ruta_archivo_config=_ruta_archivo_config,
    formato="json",  # "json" o "yaml".
    ruta_en_archivo=["mcpServers"],  # Claves anidadas hasta los servidores MCP.
    soporta_directo=True,  # False hasta confirmar en vivo (Principio IV).
    soporta_stdio=True,
    construir_entrada_directa=_entrada_directa,  # None si soporta_directo=False.
    construir_entrada_stdio=_entrada_stdio,
    verificado_en=None,  # Fijar fecha SOLO tras verificación en vivo real.
)
