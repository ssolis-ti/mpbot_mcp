"""Almacenamiento de la configuración del conector: la API key y el endpoint.

Un solo archivo por equipo, en el directorio de configuración del usuario,
con permisos restringidos al dueño (Principio IV de la constitución). La
key nunca se expone completa: toda lectura para mostrar pasa por
:func:`enmascarar`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime
import json
import os
import platform
import subprocess
from pathlib import Path

URL_POR_DEFECTO = "https://app.mpbot.cl/mcp/"
NOMBRE_ARCHIVO = "config.json"

_VAR_ENTORNO_KEY = "MPBOT_API_KEY"
_VAR_ENTORNO_URL = "MPBOT_URL"
_VAR_ENTORNO_DIR = "MPBOT_CONFIG_DIR"


@dataclasses.dataclass
class ConfiguracionConector:
    """Lo único que el conector persiste (data-model.md §1)."""

    api_key: str
    url_servidor: str = URL_POR_DEFECTO
    creada_en: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    ultima_verificacion: datetime.datetime | None = None

    def a_dict(self) -> dict:
        return {
            "api_key": self.api_key,
            "url_servidor": self.url_servidor,
            "creada_en": self.creada_en.isoformat(),
            "ultima_verificacion": (
                self.ultima_verificacion.isoformat() if self.ultima_verificacion else None
            ),
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "ConfiguracionConector":
        return cls(
            api_key=datos["api_key"],
            url_servidor=datos.get("url_servidor", URL_POR_DEFECTO),
            creada_en=datetime.datetime.fromisoformat(datos["creada_en"]),
            ultima_verificacion=(
                datetime.datetime.fromisoformat(datos["ultima_verificacion"])
                if datos.get("ultima_verificacion")
                else None
            ),
        )


def directorio_config() -> Path:
    """Directorio de configuración del usuario para este conector.

    Honra ``MPBOT_CONFIG_DIR`` (usado por los tests para no tocar el equipo
    real). En Windows usa ``%APPDATA%``; en el resto, XDG o ``~/.config``.
    """
    override = os.environ.get(_VAR_ENTORNO_DIR)
    if override:
        return Path(override)

    if platform.system() == "Windows":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "mpbot-mcp"

    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "mpbot-mcp"


def archivo_config() -> Path:
    return directorio_config() / NOMBRE_ARCHIVO


def existe_configuracion() -> bool:
    return archivo_config().exists()


def _restringir_permisos(ruta: Path) -> None:
    """Deja el archivo legible solo por el dueño. Best-effort: nunca falla el flujo."""
    with contextlib.suppress(Exception):
        if platform.system() == "Windows":
            usuario = os.environ.get("USERNAME", "")
            if usuario:
                subprocess.run(
                    [
                        "icacls",
                        str(ruta),
                        "/inheritance:r",
                        "/grant:r",
                        f"{usuario}:F",
                    ],
                    check=False,
                    capture_output=True,
                )
        else:
            os.chmod(ruta, 0o600)


def guardar(cfg: ConfiguracionConector) -> Path:
    """Escribe la configuración en disco con permisos restringidos al dueño."""
    ruta = archivo_config()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(cfg.a_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    _restringir_permisos(ruta)
    return ruta


def _cargar_desde_archivo() -> ConfiguracionConector | None:
    ruta = archivo_config()
    if not ruta.exists():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return ConfiguracionConector.desde_dict(datos)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def cargar() -> ConfiguracionConector | None:
    """Carga la configuración activa.

    El entorno (``MPBOT_API_KEY`` / ``MPBOT_URL``) tiene precedencia sobre el
    archivo, para permitir automatización sin tocar disco. Si no hay archivo
    pero sí variable de entorno con la key, se arma una configuración
    transitoria (no se persiste sola).
    """
    cfg = _cargar_desde_archivo()

    env_key = os.environ.get(_VAR_ENTORNO_KEY)
    env_url = os.environ.get(_VAR_ENTORNO_URL)

    if cfg is None:
        if env_key:
            return ConfiguracionConector(api_key=env_key, url_servidor=env_url or URL_POR_DEFECTO)
        return None

    if env_key:
        cfg.api_key = env_key
    if env_url:
        cfg.url_servidor = env_url
    return cfg


def enmascarar(api_key: str) -> str:
    """Nunca deja pasar la key completa (FR-012 / SC-004)."""
    if not api_key:
        return ""
    prefijo = api_key[:8]
    if len(api_key) <= 8:
        prefijo = api_key[: max(len(api_key) - 1, 1)]
    return f"{prefijo}…"
