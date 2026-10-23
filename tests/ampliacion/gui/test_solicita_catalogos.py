#!/usr/bin/env python3
"""
Tests de solicita_catalogos.py — ventana de solicitud
=====================================================
Cubre los helpers puros (`_validar`, `_hay_archivo`) y la ventana `App`
(validaciones, indicador de archivos y pipeline) con **interfaz real** y
`_popen`/`tc`/`ev` mockeados donde la dependencia es externa o bloqueante.
Necesita `DISPLAY`.

El módulo importa ttkbootstrap en el nivel superior, así que no corre en el CI
(igual que el resto de `gui/`); `importorskip` evita romper la colecta.
"""

import os

import pytest

pytest.importorskip("ttkbootstrap")

import solicita_catalogos as sc  # noqa: E402

pytestmark = pytest.mark.gui

_INI = "20260901000000"
_FIN = "20260930235959"


def _poner(entry, valor):
    entry.delete(0, "end")
    entry.insert(0, valor)


def _escribir(cwd, rel, texto="x"):
    ruta = cwd / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _drenar(app):
    datos = []
    while not app.cola.empty():
        datos.append(app.cola.get_nowait())
    return datos


class _RaizFalsa:
    """Raíz Tk de mentira: evita destruir la raíz compartida de la sesión."""

    def __init__(self):
        self.destruida = False

    def destroy(self):
        self.destruida = True

    def after_cancel(self, _ident):
        pass


@pytest.fixture
def app_solicita(raiz_tk, monkeypatch, cwd_tmp):
    """Construye `App` sobre la raíz compartida (parcheando `ttk.Window`)."""
    monkeypatch.setattr(sc.ttk, "Window", lambda **k: raiz_tk)
    app = sc.App()
    yield app
    try:
        if app._after_drenar is not None:
            raiz_tk.after_cancel(app._after_drenar)
    except Exception:
        pass
    for widget in list(raiz_tk.winfo_children()):
        try:
            widget.destroy()
        except Exception:
            pass
    raiz_tk.update_idletasks()


# --------------------------------------------------------------------------
# Helpers puros
# --------------------------------------------------------------------------
def test_validar_ok():
    dt, marca = sc._validar(_INI)
    assert marca == _INI
    assert dt.year == 2026


@pytest.mark.parametrize("texto", [
    "", "   ", "abc", "2026090100000", "202609010000000",
    "2026090100000a", "20261301000000",
])
def test_validar_invalidos(texto):
    assert sc._validar(texto) is None


def test_hay_archivo(cwd_tmp):
    assert sc._hay_archivo(str(cwd_tmp / "no_existe")) is False
    vacio = cwd_tmp / "vacio.txt"
    vacio.write_text("", encoding="utf-8")
    assert sc._hay_archivo(str(vacio)) is False
    lleno = _escribir(cwd_tmp, "lleno.txt", "contenido")
    assert sc._hay_archivo(str(lleno)) is True


def test_barra_de_avance_celeste_solida(app_solicita):
    estilo = str(app_solicita.barra.cget("style")).lower()
    assert "info" in estilo
    assert "striped" not in estilo


# --------------------------------------------------------------------------
# Validaciones
# --------------------------------------------------------------------------
def test_validar_campos_ok(app_solicita):
    a = app_solicita
    _poner(a.ent_ini, _INI)
    _poner(a.ent_fin, _FIN)
    _poner(a.ent_radio, "400")
    _poner(a.ent_pass, "secreta")

    assert a._validar_campos(pedir_pass=True) is True
    assert (a._inicio, a._fin) == (_INI, _FIN)
    assert a._pass == "secreta"
    assert a._radio == 400.0


def test_validar_campos_errores(app_solicita):
    a = app_solicita
    _poner(a.ent_radio, "400")

    _poner(a.ent_ini, "no"); _poner(a.ent_fin, _FIN)
    assert a._validar_campos(pedir_pass=False) is False
    assert "inicio" in a.aviso.cget("text").lower()

    _poner(a.ent_ini, _INI); _poner(a.ent_fin, "no")
    assert a._validar_campos(pedir_pass=False) is False
    assert "fin" in a.aviso.cget("text").lower()

    _poner(a.ent_fin, _INI)
    assert a._validar_campos(pedir_pass=False) is False
    assert "posterior" in a.aviso.cget("text").lower()

    _poner(a.ent_fin, _FIN); _poner(a.ent_radio, "muy")
    assert a._validar_campos(pedir_pass=False) is False
    assert "radio" in a.aviso.cget("text").lower()

    _poner(a.ent_radio, "0")
    assert a._validar_campos(pedir_pass=False) is False
    assert "mayor que cero" in a.aviso.cget("text").lower()

    _poner(a.ent_radio, "400"); _poner(a.ent_pass, "")
    assert a._validar_campos(pedir_pass=True) is False
    assert "contraseña" in a.aviso.cget("text").lower()


def test_radio_actual(app_solicita):
    a = app_solicita
    _poner(a.ent_radio, "")
    assert a._radio_actual() == sc.ev.RADIO_ESTACIONES_KM
    _poner(a.ent_radio, "abc")
    assert a._radio_actual() == sc.ev.RADIO_ESTACIONES_KM
    _poner(a.ent_radio, "0")
    assert a._radio_actual() == sc.ev.RADIO_ESTACIONES_KM
    _poner(a.ent_radio, "250km")
    assert a._radio_actual() == 250.0


def test_al_editar_fecha_limpia_aviso(app_solicita):
    a = app_solicita
    _poner(a.ent_ini, _INI)
    _poner(a.ent_fin, _FIN)
    a.aviso.configure(text="algo")
    a.nota_deteccion.configure(text="nota")

    a._al_editar_fecha()

    assert a.aviso.cget("text") == ""
    assert a.nota_deteccion.cget("text") == ""


# --------------------------------------------------------------------------
# Indicador de archivos
# --------------------------------------------------------------------------
def test_ventanas_detectadas(app_solicita, cwd_tmp):
    a = app_solicita
    assert a._ventanas_detectadas() == []
    _escribir(cwd_tmp, "select_%s_%s.out" % (_INI, _FIN))
    _escribir(cwd_tmp, "eventquery_%s_%s.csv" % (_INI, _FIN))
    assert a._ventanas_detectadas() == [(_INI, _FIN)]


def test_refrescar_estado_archivos(app_solicita, cwd_tmp):
    a = app_solicita
    _poner(a.ent_ini, _INI)
    _poner(a.ent_fin, _FIN)

    a._refrescar_estado_archivos()
    texto = a.estado_archivos.cget("text")
    assert "Seisan: no" in texto and "eventquery: no" in texto

    _escribir(cwd_tmp, "select_%s_%s.out" % (_INI, _FIN),
              " 2025  2 1 0041 28.5QL -28.121 -70.037109.0  GUC 10 0.3\n")
    _escribir(cwd_tmp, "eventquery_%s_%s.csv" % (_INI, _FIN),
              ",Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,"
              "Referencia,Percep.\n"
              "0,2025-02-01 00:00:00,-33.0,-71.0,10.0,3.0,ML,R,N\n")
    a._refrescar_estado_archivos()
    texto = a.estado_archivos.cget("text")
    assert "Seisan: sí" in texto and "eventquery: sí" in texto


# --------------------------------------------------------------------------
# Acciones y pipeline
# --------------------------------------------------------------------------
def test_ya_los_tengo_falta_catalogos(app_solicita, cwd_tmp):
    a = app_solicita
    _poner(a.ent_ini, _INI)
    _poner(a.ent_fin, _FIN)
    _poner(a.ent_radio, "400")

    a._ya_los_tengo()

    assert a.trabajando is False
    assert "Faltan catálogos" in a.aviso.cget("text")


def test_iniciar_arranca_tarea(app_solicita, monkeypatch):
    a = app_solicita
    _poner(a.ent_ini, _INI)
    _poner(a.ent_fin, _FIN)
    _poner(a.ent_radio, "400")
    _poner(a.ent_pass, "x")

    llamado = {}

    class _ThreadFalso:
        def __init__(self, target=None, args=(), daemon=None):
            self._target, self._args = target, args

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr(sc.threading, "Thread", _ThreadFalso)
    monkeypatch.setattr(a, "_confirmar_tamano_seiscomp", lambda: True)
    monkeypatch.setattr(a, "_tarea",
                        lambda modo: llamado.setdefault("modo", modo))

    a._iniciar("descargar")

    assert llamado["modo"] == "descargar"
    assert a.trabajando is True


def test_tarea_usar_ok(app_solicita, monkeypatch, cwd_tmp):
    a = app_solicita
    _escribir(cwd_tmp, "select_%s_%s.out" % (_INI, _FIN))
    _escribir(cwd_tmp, "eventquery_%s_%s.csv" % (_INI, _FIN))
    a._inicio, a._fin, a._radio = _INI, _FIN, 400.0
    monkeypatch.setattr(a, "_popen", lambda args: 0)

    a._tarea("usar")

    fines = [dato for tipo, dato in _drenar(a) if tipo == "fin"]
    assert fines
    ruta, estado = fines[0]
    assert estado["faltantes"] == []
    assert os.path.isfile(os.path.join(str(cwd_tmp), "select.out"))


def test_tarea_usar_falta_eventquery(app_solicita, monkeypatch, cwd_tmp):
    a = app_solicita
    _escribir(cwd_tmp, "select_%s_%s.out" % (_INI, _FIN))
    a._inicio, a._fin, a._radio = _INI, _FIN, 400.0
    monkeypatch.setattr(a, "_popen", lambda args: 0)

    a._tarea("usar")

    fines = [dato for tipo, dato in _drenar(a) if tipo == "fin"]
    assert fines
    assert "eventquery" in fines[0][1]["faltantes"]


def test_exportar_seiscomp_falla_verificacion(app_solicita, monkeypatch):
    a = app_solicita
    monkeypatch.setattr(a, "_popen", lambda args: 1)
    with pytest.raises(RuntimeError):
        a._exportar_seiscomp(_INI, _FIN, 0, 1)


def test_popen_ejecuta_y_devuelve_codigo(app_solicita):
    a = app_solicita
    assert a._popen(["-c", "import sys; sys.exit(0)"]) == 0
    assert a._popen(["-c", "import sys; sys.exit(3)"]) == 3


def test_popen_traduce_marca_progreso(app_solicita):
    a = app_solicita
    a.etapa_base, a.etapa_ancho, a.etapa_nombre = 0.0, 1.0, "etapa"
    assert a._popen(["-c", "print('@@PROGRESO@@ 0.5')"]) == 0
    prog = [dato for tipo, dato in _drenar(a) if tipo == "prog"]
    assert prog and abs(prog[-1][0] - 0.5) < 1e-9


# --------------------------------------------------------------------------
# Cierre
# --------------------------------------------------------------------------
def test_terminar_error_sale(app_solicita, monkeypatch, capsys):
    a = app_solicita
    monkeypatch.setattr(a, "_cancelar_after", lambda: None)
    monkeypatch.setattr(a, "raiz", _RaizFalsa())

    with pytest.raises(SystemExit):
        a._terminar_error("boom")

    assert "boom" in capsys.readouterr().err


def test_progreso_revision_actualiza_barra_y_texto(app_solicita):
    a = app_solicita

    class _Barra:
        def __init__(self):
            self.valor = None

        def configure(self, **kwargs):
            self.valor = kwargs.get("value")

    class _Etiqueta:
        def __init__(self):
            self.texto = None

        def configure(self, **kwargs):
            self.texto = kwargs.get("text")

    barra, etiqueta = _Barra(), _Etiqueta()
    a._barra_revision = barra
    a._etiqueta_revision = etiqueta

    a._progreso_revision(0.42, "Armando la interfaz…")

    assert barra.valor == 420
    assert etiqueta.texto == "Armando la interfaz…"


def test_terminar_ok_construye_la_revision_en_la_misma_raiz(
        app_solicita, monkeypatch):
    a = app_solicita
    llamado = {}
    nueva = object()

    def _panel():
        a._overlay_revision = object()
        llamado["panel"] = True

    def _abrir(ruta, estado):
        llamado["revision"] = (ruta, estado)
        return nueva

    monkeypatch.setattr(a, "_cancelar_after", lambda: None)
    monkeypatch.setattr(a, "_preparar_overlay_revision", _panel)
    monkeypatch.setattr(a, "_poner_estado_revision",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(a, "_abrir_revision_en_raiz", _abrir)
    monkeypatch.setattr(a, "_cerrar_overlay_revision",
                        lambda: llamado.setdefault("cerrar", True))

    estado = {"inicio": _INI, "fin": _FIN, "faltantes": []}
    a._terminar_ok(("eventquery_x.csv", estado))

    assert llamado["panel"] is True
    assert llamado["revision"] == ("eventquery_x.csv", estado)
    assert llamado["cerrar"] is True
    assert a._nueva_app is nueva
    assert a._transicion is False


def test_terminar_ok_muestra_error_si_falla_la_construccion(
        app_solicita, monkeypatch):
    a = app_solicita
    llamado = {}
    monkeypatch.setattr(a, "_cancelar_after", lambda: None)
    monkeypatch.setattr(a, "_preparar_overlay_revision", lambda: None)
    monkeypatch.setattr(a, "_poner_estado_revision",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(
        a, "_abrir_revision_en_raiz",
        lambda ruta, estado: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(
        a, "_error_transicion",
        lambda mensaje, detalle="": llamado.setdefault("error",
                                                       (mensaje, detalle)))

    a._terminar_ok(("eventquery_x.csv", {"inicio": _INI, "fin": _FIN}))

    assert llamado["error"][0] == "No se pudo abrir la revisión."
    assert "boom" in llamado["error"][1]


def test_main_arranca(monkeypatch):
    llamado = {}

    class _Raiz:
        def deiconify(self):
            llamado["deiconify"] = True

        def update(self):
            llamado["update"] = True

        def mainloop(self):
            llamado["mainloop"] = True

    class _AppFalsa:
        def __init__(self):
            self.raiz = _Raiz()

    monkeypatch.setattr(sc, "App", _AppFalsa)

    sc.main()

    assert llamado.get("deiconify") is True
    assert llamado.get("update") is True
    assert llamado.get("mainloop") is True


# --------------------------------------------------------------------------
# Catálogos vacíos
# --------------------------------------------------------------------------
_SELECT_OK = " 2025  2 1 0041 28.5QL -28.121 -70.037109.0  GUC 10 0.3\n"
_EVENTQUERY_OK = (",Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,"
                  "Referencia,Percep.\n"
                  "0,2025-02-01 00:00:00,-33.0,-71.0,10.0,3.0,ML,R,N\n")


def test_tarea_avisa_catalogos_locales_vacios(app_solicita, monkeypatch,
                                              cwd_tmp):
    a = app_solicita
    _escribir(cwd_tmp, "select_%s_%s.out" % (_INI, _FIN),
              " Welcome to select\n")
    _escribir(cwd_tmp, "eventquery_%s_%s.csv" % (_INI, _FIN),
              ",Fecha_Hora,Latitud,Longitud\n")
    a._inicio, a._fin, a._radio = _INI, _FIN, 400.0
    monkeypatch.setattr(a, "_exportar_seiscomp", lambda *args: 1)

    a._tarea("usar")

    _ruta, estado = [d for t, d in _drenar(a) if t == "fin"][0]
    catalogos = {aviso["catalogo"] for aviso in estado["avisos"]}
    assert catalogos == {"Seisan", "eventquery"}


def test_tarea_avisa_seiscomp_sin_eventos(app_solicita, monkeypatch, cwd_tmp):
    a = app_solicita
    _escribir(cwd_tmp, "select_%s_%s.out" % (_INI, _FIN), _SELECT_OK)
    _escribir(cwd_tmp, "eventquery_%s_%s.csv" % (_INI, _FIN), _EVENTQUERY_OK)
    a._inicio, a._fin, a._radio = _INI, _FIN, 400.0
    monkeypatch.setattr(a, "_exportar_seiscomp", lambda *args: 0)

    a._tarea("usar")

    _ruta, estado = [d for t, d in _drenar(a) if t == "fin"][0]
    assert [a["catalogo"] for a in estado["avisos"]] == ["SeisComp"]
    assert estado["faltantes"] == []
