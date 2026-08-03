"""Tests de errores.py: los 4 modos de falla se distinguen entre sí (FR-011)."""

from __future__ import annotations

import httpx
import pytest

from mpbot_mcp.errores import ErrorMpbot, TipoError, traducir_error


def _status_error(codigo: int, cuerpo: dict | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://app.mpbot.cl/mcp/")
    response = httpx.Response(codigo, json=cuerpo or {}, request=request)
    return httpx.HTTPStatusError(f"status {codigo}", request=request, response=response)


@pytest.mark.parametrize(
    "codigo,tipo_esperado",
    [
        (401, TipoError.CREDENCIAL_INVALIDA),
        (403, TipoError.PLAN_INSUFICIENTE),
        (429, TipoError.CUOTA_AGOTADA),
        (421, TipoError.HOST_NO_RECONOCIDO),
        (500, TipoError.DESCONOCIDO),
    ],
)
def test_cada_codigo_produce_un_tipo_distinto(codigo, tipo_esperado):
    error = traducir_error(_status_error(codigo, {"error": "detalle del servidor"}))
    assert isinstance(error, ErrorMpbot)
    assert error.tipo is tipo_esperado


def test_los_cuatro_modos_tienen_mensajes_todos_distintos():
    codigos = [401, 403, 429, 421]
    mensajes = {traducir_error(_status_error(c)).mensaje for c in codigos}
    assert len(mensajes) == len(codigos), "ningún mensaje puede repetirse entre modos de falla"


def test_todos_los_modos_traen_accion_sugerida():
    for codigo in (401, 403, 429, 421):
        error = traducir_error(_status_error(codigo))
        assert error.accion, f"código {codigo} no trae acción sugerida"


def test_401_no_se_confunde_con_conectividad():
    error = traducir_error(_status_error(401))
    assert error.tipo != TipoError.CONECTIVIDAD


def test_error_de_red_se_reporta_como_conectividad_no_credenciales():
    request = httpx.Request("POST", "https://app.mpbot.cl/mcp/")
    exc = httpx.ConnectError("no route to host", request=request)
    error = traducir_error(exc)
    assert error.tipo is TipoError.CONECTIVIDAD
    assert error.tipo != TipoError.CREDENCIAL_INVALIDA


def test_error_de_red_dentro_de_exceptiongroup_se_detecta():
    request = httpx.Request("POST", "https://app.mpbot.cl/mcp/")
    exc = ExceptionGroup("fallo de transporte", [httpx.ConnectError("sin ruta", request=request)])
    error = traducir_error(exc)
    assert error.tipo is TipoError.CONECTIVIDAD


def test_401_dentro_de_exceptiongroup_anidado_se_detecta():
    interno = ExceptionGroup("interno", [_status_error(401)])
    externo = ExceptionGroup("externo", [interno])
    error = traducir_error(externo)
    assert error.tipo is TipoError.CREDENCIAL_INVALIDA


def test_mensaje_del_servidor_se_incluye_en_el_detalle():
    error = traducir_error(_status_error(429, {"error": "47 de 47 usadas este mes"}))
    assert "47 de 47" in error.mensaje


def test_error_desconocido_no_deja_pasar_la_excepcion_cruda():
    error = traducir_error(ValueError("algo raro"))
    assert isinstance(error, ErrorMpbot)
    assert error.tipo is TipoError.DESCONOCIDO
