"""Estructura de un perfil de agente. Es dato, no lógica (Principio VII).

Agregar soporte a un agente nuevo es agregar un módulo con un `PerfilAgente`,
no tocar el motor de `agentes/__init__.py` (contracts/perfil-agente.md).
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal


@dataclasses.dataclass(frozen=True)
class PerfilAgente:
    """Cómo tratar a un agente concreto (data-model.md §2)."""

    id: str
    nombre: str

    # Si alguna de estas rutas existe, el agente se considera instalado
    # (research §5: se detecta por presencia de archivo/directorio de
    # configuración, nunca ejecutando el agente ni buscándolo en el PATH).
    rutas_deteccion: Callable[[], Sequence[Path]]

    # Ruta absoluta del archivo de configuración a leer/escribir. Puede vivir
    # fuera de las rutas de detección (p.ej. un agente cuyo directorio de
    # estado y cuyo archivo de config no son el mismo lugar).
    ruta_archivo_config: Callable[[], Path]

    formato: Literal["json", "yaml"]

    # Claves anidadas hasta el diccionario donde viven los servidores MCP
    # (p.ej. ["mcpServers"] o ["mcp", "servers"]).
    ruta_en_archivo: Sequence[str]

    soporta_directo: bool
    soporta_stdio: bool

    # (url_servidor, api_key) -> entrada a escribir bajo `ruta_en_archivo[id]`.
    construir_entrada_directa: Callable[[str, str], dict] | None = None

    # (ruta_ejecutable) -> entrada a escribir, para el modo puente (US3).
    construir_entrada_stdio: Callable[[str], dict] | None = None

    verificado_en: datetime.date | None = None

    def esta_verificado(self) -> bool:
        """Nulo = no verificado: no se presenta como compatible (Principio II)."""
        return self.verificado_en is not None

    def esta_instalado(self) -> bool:
        return any(ruta.exists() for ruta in self.rutas_deteccion())
