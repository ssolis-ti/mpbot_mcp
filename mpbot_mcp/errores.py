"""Traducción de fallas del servidor/transporte a mensaje en español + acción.

Cuatro modos de falla deben distinguirse siempre entre sí (FR-011): credencial
inválida, plan insuficiente, cuota agotada y problema de conectividad. El caso
`421` (host no reconocido, protección anti DNS-rebinding del servidor) es un
quinto caso que **no** debe confundirse con credenciales
(contracts/servidor-mpbot.md).
"""

from __future__ import annotations

import enum
import json

import httpx


class TipoError(enum.Enum):
    CREDENCIAL_INVALIDA = "credencial_invalida"
    PLAN_INSUFICIENTE = "plan_insuficiente"
    CUOTA_AGOTADA = "cuota_agotada"
    CONECTIVIDAD = "conectividad"
    HOST_NO_RECONOCIDO = "host_no_reconocido"
    DESCONOCIDO = "desconocido"


class ErrorMpbot(Exception):
    """Error ya traducido: lenguaje llano + acción sugerida."""

    def __init__(self, tipo: TipoError, mensaje: str, accion: str | None = None):
        self.tipo = tipo
        self.mensaje = mensaje
        self.accion = accion
        super().__init__(mensaje)

    def __str__(self) -> str:  # pragma: no cover - solo formateo
        if self.accion:
            return f"{self.mensaje} → {self.accion}"
        return self.mensaje


def _mensaje_servidor(response: httpx.Response) -> str | None:
    # El body puede no estar disponible: la respuesta llega desde un stream
    # (`client.stream(...)`) que ya se cerró para cuando la excepción original
    # terminó de propagarse a través del transporte.
    try:
        cuerpo = response.json()
    except (json.JSONDecodeError, ValueError, httpx.ResponseNotRead, httpx.StreamClosed):
        return None
    if isinstance(cuerpo, dict):
        mensaje = cuerpo.get("error")
        if isinstance(mensaje, str):
            return mensaje
    return None


def _buscar(exc: BaseException, tipos: tuple[type, ...]) -> BaseException | None:
    """Recorre recursivamente ExceptionGroup/`__cause__` buscando alguno de `tipos`."""
    if isinstance(exc, tipos):
        return exc
    grupo = getattr(exc, "exceptions", None)
    if grupo:
        for sub in grupo:
            encontrado = _buscar(sub, tipos)
            if encontrado is not None:
                return encontrado
    if exc.__cause__ is not None:
        return _buscar(exc.__cause__, tipos)
    return None


def traducir_error(exc: BaseException) -> ErrorMpbot:
    """Convierte cualquier excepción cruda del transporte en un `ErrorMpbot`."""
    status_error = _buscar(exc, (httpx.HTTPStatusError,))
    if status_error is not None:
        assert isinstance(status_error, httpx.HTTPStatusError)
        detalle = _mensaje_servidor(status_error.response)
        codigo = status_error.response.status_code
        return _traducir_status(codigo, detalle)

    error_transporte = _buscar(exc, (httpx.TransportError,))
    if error_transporte is not None:
        return ErrorMpbot(
            TipoError.CONECTIVIDAD,
            "No se pudo contactar al servidor de mpbot (problema de red, TLS o proxy).",
            "Revisa tu conexión a internet o la configuración de tu proxy corporativo, y vuelve a intentar.",
        )

    return ErrorMpbot(
        TipoError.DESCONOCIDO,
        f"Ocurrió un problema inesperado al hablar con el servidor: {exc}",
        "Ejecuta `mpbot-mcp doctor` para más detalle, o vuelve a intentar en unos minutos.",
    )


def _traducir_status(codigo: int, detalle: str | None) -> ErrorMpbot:
    sufijo = f" ({detalle})" if detalle else ""

    if codigo == 401:
        return ErrorMpbot(
            TipoError.CREDENCIAL_INVALIDA,
            f"La API key no sirve o fue revocada{sufijo}.",
            "Genera una nueva en app.mpbot.cl/config y vuelve a intentar.",
        )
    if codigo == 403:
        return ErrorMpbot(
            TipoError.PLAN_INSUFICIENTE,
            f"Tu plan no incluye acceso al servidor MCP de mpbot{sufijo}.",
            "El servidor MCP está disponible desde el plan Empresa; revisa tu plan en app.mpbot.cl/config.",
        )
    if codigo == 429:
        return ErrorMpbot(
            TipoError.CUOTA_AGOTADA,
            f"Se agotó la cuota mensual de tu API key{sufijo}.",
            "La cuota se renueva al inicio del próximo ciclo; revisa el detalle en app.mpbot.cl/config.",
        )
    if codigo == 421:
        return ErrorMpbot(
            TipoError.HOST_NO_RECONOCIDO,
            f"El servidor no reconoce esta dirección{sufijo}.",
            "Revisa la URL configurada (MPBOT_URL); no es un problema de tu API key.",
        )

    return ErrorMpbot(
        TipoError.DESCONOCIDO,
        f"El servidor respondió con un error inesperado (código {codigo}){sufijo}.",
        "Ejecuta `mpbot-mcp doctor` para más detalle, o vuelve a intentar en unos minutos.",
    )
