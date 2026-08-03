"""Tests del motor genérico en agentes/__init__.py: detección y respaldo (T012)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mpbot_mcp.agentes import (
    ConfiguracionAgenteInvalida,
    detectar_agentes,
    escribir_config,
    leer_config,
    respaldar,
)
from mpbot_mcp.agentes.perfil import PerfilAgente


def _perfil_dummy(tmp_path: Path, *, formato="json") -> PerfilAgente:
    directorio = tmp_path / "agente-dummy"
    archivo = directorio / ("config.yaml" if formato == "yaml" else "config.json")
    return PerfilAgente(
        id="dummy",
        nombre="Agente de prueba",
        rutas_deteccion=lambda: [directorio],
        ruta_archivo_config=lambda: archivo,
        formato=formato,
        ruta_en_archivo=["mcp", "servers"],
        soporta_directo=True,
        soporta_stdio=True,
        construir_entrada_directa=lambda url, key: {"url": url, "headers": {"Authorization": f"Bearer {key}"}},
        construir_entrada_stdio=lambda ruta: {"command": ruta, "args": ["servir"]},
        verificado_en=None,
    )


# --- Detección --------------------------------------------------------


def test_agente_no_detectado_si_su_directorio_no_existe(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    assert perfil.esta_instalado() is False
    assert detectar_agentes([perfil]) == []


def test_agente_detectado_si_su_directorio_existe(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    perfil.ruta_archivo_config().parent.mkdir(parents=True)

    assert perfil.esta_instalado() is True
    encontrados = detectar_agentes([perfil])
    assert len(encontrados) == 1
    assert encontrados[0][0].id == "dummy"


def test_agente_verificado_en_nulo_no_se_declara_verificado(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    assert perfil.esta_verificado() is False


# --- Respaldo (FR-005) --------------------------------------------------


def test_respaldar_archivo_inexistente_devuelve_none(tmp_path):
    assert respaldar(tmp_path / "no-existe.json") is None


def test_respaldar_crea_copia_con_marca_de_tiempo(tmp_path):
    original = tmp_path / "config.json"
    original.write_text('{"a": 1}', encoding="utf-8")

    respaldo = respaldar(original)

    assert respaldo is not None
    assert respaldo.ruta_respaldo.exists()
    assert respaldo.ruta_respaldo.read_text(encoding="utf-8") == '{"a": 1}'
    assert respaldo.ruta_respaldo != original


def test_respaldar_dos_veces_no_sobrescribe_el_respaldo_anterior(tmp_path):
    original = tmp_path / "config.json"
    original.write_text('{"a": 1}', encoding="utf-8")

    primero = respaldar(original)
    original.write_text('{"a": 2}', encoding="utf-8")
    segundo = respaldar(original)

    assert primero.ruta_respaldo != segundo.ruta_respaldo
    assert primero.ruta_respaldo.exists()
    assert segundo.ruta_respaldo.exists()
    assert primero.ruta_respaldo.read_text(encoding="utf-8") == '{"a": 1}'
    assert segundo.ruta_respaldo.read_text(encoding="utf-8") == '{"a": 2}'


# --- Lectura / escritura genérica --------------------------------------


def test_leer_config_archivo_inexistente_devuelve_vacio(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    assert leer_config(perfil, perfil.ruta_archivo_config()) == {}


def test_leer_config_json_corrupto_lanza_error_tipado(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    ruta = perfil.ruta_archivo_config()
    ruta.parent.mkdir(parents=True)
    ruta.write_text("{ esto no es json", encoding="utf-8")

    with pytest.raises(ConfiguracionAgenteInvalida):
        leer_config(perfil, ruta)


def test_escribir_config_preserva_otras_claves_y_otros_servidores(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    ruta = perfil.ruta_archivo_config()
    ruta.parent.mkdir(parents=True)
    ruta.write_text(
        json.dumps(
            {
                "otraClaveDelAgente": "no tocar",
                "mcp": {"servers": {"otro-servidor": {"url": "https://otro.example"}}},
            }
        ),
        encoding="utf-8",
    )

    entrada = perfil.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test")
    escribir_config(perfil, ruta, entrada)

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["otraClaveDelAgente"] == "no tocar"
    assert datos["mcp"]["servers"]["otro-servidor"] == {"url": "https://otro.example"}
    assert datos["mcp"]["servers"]["dummy"] == entrada


def test_escribir_config_respalda_si_el_archivo_ya_existia(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    ruta = perfil.ruta_archivo_config()
    ruta.parent.mkdir(parents=True)
    ruta.write_text("{}", encoding="utf-8")

    resultado = escribir_config(perfil, ruta, {"url": "https://app.mpbot.cl/mcp/"})

    assert resultado.existia_antes is True
    assert resultado.respaldo is not None
    assert resultado.respaldo.ruta_respaldo.exists()


def test_escribir_config_sin_archivo_previo_no_genera_respaldo(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    ruta = perfil.ruta_archivo_config()
    ruta.parent.mkdir(parents=True)

    resultado = escribir_config(perfil, ruta, {"url": "https://app.mpbot.cl/mcp/"})

    assert resultado.existia_antes is False
    assert resultado.respaldo is None


def test_escribir_config_es_idempotente(tmp_path):
    perfil = _perfil_dummy(tmp_path)
    ruta = perfil.ruta_archivo_config()
    ruta.parent.mkdir(parents=True)
    ruta.write_text(json.dumps({"mcp": {"servers": {"otro": {"url": "https://otro.example"}}}}), encoding="utf-8")

    entrada = perfil.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test")
    escribir_config(perfil, ruta, entrada)
    primera_pasada = json.loads(ruta.read_text(encoding="utf-8"))

    escribir_config(perfil, ruta, entrada)
    segunda_pasada = json.loads(ruta.read_text(encoding="utf-8"))

    assert primera_pasada == segunda_pasada
    assert list(segunda_pasada["mcp"]["servers"].keys()) == ["otro", "dummy"]


def test_escribir_config_yaml_preserva_lo_ajeno(tmp_path):
    perfil = _perfil_dummy(tmp_path, formato="yaml")
    ruta = perfil.ruta_archivo_config()
    ruta.parent.mkdir(parents=True)
    ruta.write_text("otra_clave: no tocar\nmcp:\n  servers:\n    otro:\n      url: https://otro.example\n", encoding="utf-8")

    import yaml

    entrada = perfil.construir_entrada_directa("https://app.mpbot.cl/mcp/", "mpb_test")
    escribir_config(perfil, ruta, entrada)

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert datos["otra_clave"] == "no tocar"
    assert datos["mcp"]["servers"]["otro"]["url"] == "https://otro.example"
    assert datos["mcp"]["servers"]["dummy"] == entrada
