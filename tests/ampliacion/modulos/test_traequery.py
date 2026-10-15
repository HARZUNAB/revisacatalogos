#!/usr/bin/env python3
"""
Tests de traequery.py
=====================
Cubre el helper interactivo `solicitar`, los helpers de armado
(`_normalizar_salida`, `_construir_args`, `_comando_remoto`, `_hay_datos`) y el
flujo completo de `main()` con `input` y `subprocess.run` mockeados, incluido el
caso de una ventana sin datos.

Sin marcador: solo usa la stdlib, así que corre en CI.
"""

import os
import subprocess

import pytest

import traequery as t


def _entradas(monkeypatch, valores):
    it = iter(valores)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))


def _fake_run(monkeypatch, comportamiento="ok", contenido="a,b\n1,2\n",
              registro=None):
    """Reemplaza `subprocess.run`: ssh no hace nada; scp crea/omite el archivo."""

    def run(args, check=False, **kwargs):
        if registro is not None:
            registro.append(args)
        if args[0] == "ssh":
            if comportamiento == "ssh_falla":
                raise subprocess.CalledProcessError(1, args)
            return None
        if args[0] == "scp":
            destino, remoto = args[-1], args[-2]
            archivo = os.path.join(destino, os.path.basename(remoto))
            if comportamiento == "falla":
                raise subprocess.CalledProcessError(1, args)
            if comportamiento == "vacio":
                open(archivo, "w").close()
                return None
            with open(archivo, "w") as f:
                f.write(contenido)
            return None

    monkeypatch.setattr(t.subprocess, "run", run)


_ENTRADAS_OK = ["20260501000000", "20260507235959", "datos", "analista",
                "", "", "", "", "", "", "", ""]


# --------------------------------------------------------------------------
# solicitar
# --------------------------------------------------------------------------
def test_tiempo_corto_valido(monkeypatch):
    _entradas(monkeypatch, ["20260501000000"])
    assert t.solicitar("x", "e", "tiempo_corto") == "2026-05-01T00:00:00"


def test_tiempo_corto_formato_malo_repregunta(monkeypatch, capsys):
    _entradas(monkeypatch, ["2026", "20260501000000"])
    assert t.solicitar("x", "e", "tiempo_corto") == "2026-05-01T00:00:00"
    assert "14 dígitos" in capsys.readouterr().out


def test_tiempo_corto_fecha_invalida_repregunta(monkeypatch, capsys):
    _entradas(monkeypatch, ["20261301000000", "20260501000000"])
    assert t.solicitar("x", "e", "tiempo_corto") == "2026-05-01T00:00:00"
    assert "Fecha o hora inválida" in capsys.readouterr().out


def test_numero_valido(monkeypatch):
    _entradas(monkeypatch, ["-38.5"])
    assert t.solicitar("x", "e", "numero") == "-38.5"


def test_numero_invalido_repregunta(monkeypatch, capsys):
    _entradas(monkeypatch, ["abc", "3.0"])
    assert t.solicitar("x", "e", "numero") == "3.0"
    assert "valor numérico" in capsys.readouterr().out


def test_texto_sanea_caracteres_peligrosos(monkeypatch):
    _entradas(monkeypatch, ["a`b$c;d\"e'f"])
    assert t.solicitar("x", "e", "texto") == "abcdef"


def test_vacio_opcional_devuelve_none(monkeypatch):
    _entradas(monkeypatch, [""])
    assert t.solicitar("x", "e", "numero") is None


def test_vacio_obligatorio_repregunta(monkeypatch, capsys):
    _entradas(monkeypatch, ["", "valor"])
    assert t.solicitar("x", "e", "texto", obligatorio=True) == "valor"
    assert "no puede estar vacío" in capsys.readouterr().out


def test_cancelado_sale(monkeypatch):
    def revienta(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", revienta)
    with pytest.raises(SystemExit) as exc:
        t.solicitar("x", "e", "texto")
    assert exc.value.code == 1


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def test_normalizar_salida():
    assert t._normalizar_salida("datos") == "datos.csv"
    assert t._normalizar_salida("datos.csv") == "datos.csv"
    assert t._normalizar_salida("datos.CSV") == "datos.CSV"


def test_construir_args_incluye_solo_no_nulos():
    opcionales = [("--min-latitude", "-38.5"), ("--max-latitude", None)]
    assert t._construir_args("ini", "fin", opcionales, "d.csv") == \
        ["--start-time", "ini", "--end-time", "fin",
         "--min-latitude", "-38.5", "d.csv"]


def test_comando_remoto():
    comando = t._comando_remoto(["--start-time", "ini"])
    assert comando == ("mkdir -p %s && cd %s && %s --start-time ini"
                       % (t.DIR_REMOTO, t.DIR_REMOTO, t.EXE_EVENTQUERY))


def test_hay_datos(tmp_path):
    assert t._hay_datos(str(tmp_path / "no_existe")) is False
    vacio = tmp_path / "vacio.csv"
    vacio.write_text("", encoding="utf-8")
    assert t._hay_datos(str(vacio)) is False
    lleno = tmp_path / "lleno.csv"
    lleno.write_text("x", encoding="utf-8")
    assert t._hay_datos(str(lleno)) is True


# --------------------------------------------------------------------------
# main() end-to-end
# --------------------------------------------------------------------------
def test_main_exito(cwd_tmp, monkeypatch, capsys):
    _entradas(monkeypatch, _ENTRADAS_OK)
    registro = []
    _fake_run(monkeypatch, "ok", registro=registro)

    t.main()

    assert (cwd_tmp / "datos.csv").is_file()
    ssh = [a for a in registro if a[0] == "ssh"][0]
    assert "eventquery" in ssh[-1] and "datos.csv" in ssh[-1]
    assert "2026-05-01T00:00:00" in ssh[-1]
    assert any(a[0] == "scp" for a in registro)
    assert "ÉXITO" in capsys.readouterr().out


def test_main_fin_no_posterior_repregunta(cwd_tmp, monkeypatch, capsys):
    _entradas(monkeypatch, ["20260501000000", "20260401000000",
                            "20260501000000", "20260507235959",
                            "datos", "analista",
                            "", "", "", "", "", "", "", ""])
    _fake_run(monkeypatch, "ok")
    t.main()
    assert "ERROR LÓGICO" in capsys.readouterr().out
    assert (cwd_tmp / "datos.csv").is_file()


def test_main_sin_datos_scp_falla(cwd_tmp, monkeypatch, capsys):
    _entradas(monkeypatch, _ENTRADAS_OK)
    _fake_run(monkeypatch, "falla")
    t.main()   # no debe levantar SystemExit
    assert not (cwd_tmp / "datos.csv").exists()
    assert "No hay datos" in capsys.readouterr().out


def test_main_sin_datos_archivo_vacio(cwd_tmp, monkeypatch, capsys):
    _entradas(monkeypatch, _ENTRADAS_OK)
    _fake_run(monkeypatch, "vacio")
    t.main()
    # El archivo de 0 bytes se borra: no queda un CSV vacío en disco.
    assert not (cwd_tmp / "datos.csv").exists()
    assert "No hay datos" in capsys.readouterr().out


def test_main_scp_falla_con_archivo_previo_es_error(cwd_tmp, monkeypatch, capsys):
    # Si el scp falla pero ya había un archivo con datos, no es "sin datos":
    # es un error real y sale con código 1.
    (cwd_tmp / "datos.csv").write_text("viejo", encoding="utf-8")
    _entradas(monkeypatch, _ENTRADAS_OK)
    _fake_run(monkeypatch, "falla")
    with pytest.raises(SystemExit) as exc:
        t.main()
    assert exc.value.code == 1


def test_main_error_ssh(cwd_tmp, monkeypatch, capsys):
    _entradas(monkeypatch, _ENTRADAS_OK)
    _fake_run(monkeypatch, "ssh_falla")
    with pytest.raises(SystemExit) as exc:
        t.main()
    assert exc.value.code == 1
    assert "Error crítico" in capsys.readouterr().err
