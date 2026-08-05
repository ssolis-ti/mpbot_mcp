"""Registro de perfiles, detección de agentes instalados, y el motor genérico
de lectura/escritura/respaldo de su configuración.

Los perfiles (`claude_code.py`, `hermes.py`, `openclaw.py`,
`claude_desktop.py`) son datos puros; toda la lógica que se comparte entre
ellos vive acá, una sola vez, para que agregar un agente nuevo no exija tocar
este motor (Principio VII / contracts/perfil-agente.md).
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from collections.abc import Sequence
from pathlib import Path

import yaml

from .perfil import PerfilAgente


NOMBRE_SERVIDOR = "mpbot"
"""Clave con la que se registra mpbot dentro de la config de CADA agente.

**Corrección real (2026-08-03, auditoría en vivo)**: la primera versión usaba
`perfil.id` (el id del AGENTE que se está configurando: "claude-code",
"hermes"...) como nombre del SERVIDOR MCP — confundía dos dimensiones
distintas. Verificado en vivo: producía `mcpServers["claude-code"]` en la
config de Claude Code, y habría producido `mcp_servers["hermes"]` dentro de
la config del propio Hermes — un servidor llamado "hermes" adentro de Hermes,
que no comunica en absoluto que ese servidor es mpbot.
"""


class ConfiguracionAgenteInvalida(Exception):
    """El archivo de configuración del agente existe pero no se pudo interpretar."""

    def __init__(self, ruta: Path, causa: Exception):
        self.ruta = ruta
        self.causa = causa
        super().__init__(f"No se pudo leer {ruta}: {causa}")


@dataclasses.dataclass(frozen=True)
class RespaldoConfig:
    """Copia de seguridad de la configuración de un agente antes de modificarla (data-model.md §4)."""

    ruta_original: Path
    ruta_respaldo: Path
    creado_en: datetime.datetime


@dataclasses.dataclass(frozen=True)
class ResultadoEscritura:
    ruta: Path
    respaldo: RespaldoConfig | None
    existia_antes: bool


def detectar_agentes(registro: Sequence[PerfilAgente] | None = None) -> list[tuple[PerfilAgente, Path]]:
    """Agentes instalados en este equipo, con la ruta de su archivo de configuración."""
    encontrados: list[tuple[PerfilAgente, Path]] = []
    for perfil in registro if registro is not None else REGISTRO:
        if perfil.esta_instalado():
            encontrados.append((perfil, perfil.ruta_archivo_config()))
    return encontrados


def respaldar(ruta: Path) -> RespaldoConfig | None:
    """Copia `ruta` con marca de tiempo antes de tocarla (FR-005).

    `None` si `ruta` todavía no existe: no hay nada que respaldar. Nunca
    sobrescribe un respaldo anterior — la marca de tiempo (con microsegundos)
    lo evita incluso si se llama dos veces en el mismo segundo.
    """
    if not ruta.exists():
        return None

    ahora = datetime.datetime.now(datetime.timezone.utc)
    marca = ahora.strftime("%Y%m%dT%H%M%S%f")
    ruta_respaldo = ruta.with_name(f"{ruta.name}.{marca}.bak")
    ruta_respaldo.write_bytes(ruta.read_bytes())
    return RespaldoConfig(ruta_original=ruta, ruta_respaldo=ruta_respaldo, creado_en=ahora)


def leer_config(perfil: PerfilAgente, ruta: Path) -> dict:
    """Contenido actual del archivo del agente, o `{}` si todavía no existe."""
    if not ruta.exists():
        return {}

    texto = ruta.read_text(encoding="utf-8")
    if not texto.strip():
        return {}

    try:
        if perfil.formato == "yaml":
            datos = yaml.safe_load(texto)
        else:
            datos = json.loads(texto)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ConfiguracionAgenteInvalida(ruta, exc) from exc

    return datos if isinstance(datos, dict) else {}


def _contenedor_servidores(datos: dict, ruta_en_archivo: Sequence[str]) -> dict:
    """Desciende (creando lo que falte) hasta el diccionario donde viven los servidores MCP."""
    actual = datos
    for clave in ruta_en_archivo:
        siguiente = actual.get(clave)
        if not isinstance(siguiente, dict):
            siguiente = {}
            actual[clave] = siguiente
        actual = siguiente
    return actual


def _volcar(perfil: PerfilAgente, datos: dict) -> str:
    if perfil.formato == "yaml":
        return yaml.safe_dump(datos, allow_unicode=True, sort_keys=False)
    return json.dumps(datos, indent=2, ensure_ascii=False) + "\n"


def escribir_config(perfil: PerfilAgente, ruta: Path, entrada: dict) -> ResultadoEscritura:
    """Agrega o actualiza la entrada de mpbot en la config de un agente.

    Preserva todo lo demás (FR-006), respalda si el archivo ya existía
    (FR-005) y es idempotente: escribirlo dos veces dejan el archivo
    funcionalmente idéntico, sin duplicar la entrada (FR-007).
    """
    existia_antes = ruta.exists()
    respaldo = respaldar(ruta)

    datos = leer_config(perfil, ruta)
    contenedor = _contenedor_servidores(datos, perfil.ruta_en_archivo)
    contenedor[NOMBRE_SERVIDOR] = entrada

    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(_volcar(perfil, datos), encoding="utf-8")

    return ResultadoEscritura(ruta=ruta, respaldo=respaldo, existia_antes=existia_antes)


def _construir_registro() -> list[PerfilAgente]:
    """Descubre los perfiles por convención: todo módulo de `agentes/` que
    exponga un `PERFIL` (instancia de `PerfilAgente`) entra al registro.

    Agregar un agente nuevo es agregar un módulo en este paquete con un
    `PERFIL` — no tocar nada acá. Los módulos cuyo nombre empieza con `_`
    (privados, como `_template.py`) se ignoran a propósito.
    """
    import importlib
    import pkgutil

    from . import claude_code, claude_desktop, hermes, openclaw

    descubiertos: list[PerfilAgente] = [
        claude_code.PERFIL,
        claude_desktop.PERFIL,
        hermes.PERFIL,
        openclaw.PERFIL,
    ]

    paquete = importlib.import_module(__name__)
    for modulo_info in pkgutil.iter_modules(paquete.__path__):
        if modulo_info.name.startswith("_"):
            continue
        modulo = importlib.import_module(f"{__name__}.{modulo_info.name}")
        perfil = getattr(modulo, "PERFIL", None)
        if isinstance(perfil, PerfilAgente) and perfil not in descubiertos:
            descubiertos.append(perfil)

    return descubiertos


REGISTRO: list[PerfilAgente] = _construir_registro()
