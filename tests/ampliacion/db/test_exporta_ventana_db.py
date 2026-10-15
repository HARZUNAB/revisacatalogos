#!/usr/bin/env python3
"""
Tests de base de datos de exporta_ventana_seiscomp.py
=====================================================
Cubre la capa de consulta con `psycopg2` mockeado: configuración, conexión,
cursores y las consultas de eventos, inventario, bindings, actividad,
estimación y escritura de fases. No se toca ninguna base real.

Marcador `db` (excluido del CI: no hay PostgreSQL en integración).
"""

from datetime import datetime

import pytest

import exporta_ventana_seiscomp as ev

pytestmark = pytest.mark.db

CONFIG = {"host": "h", "database": "d", "user": "u", "password": "p",
          "connect_timeout": 10}
INI = datetime(2026, 9, 1)
FIN = datetime(2026, 9, 30)


class CursorFalso:
    """Devuelve una respuesta por cada fetch, en orden de llamada."""

    def __init__(self, respuestas=None, lotes=None):
        self.respuestas = list(respuestas or [])
        self.lotes = list(lotes or [])
        self.ejecutados = []
        self.itersize = None
        self.cerrado = False

    def execute(self, sql, params=None):
        self.ejecutados.append((sql, params))

    def fetchone(self):
        return self.respuestas.pop(0) if self.respuestas else None

    def fetchall(self):
        return self.respuestas.pop(0) if self.respuestas else []

    def fetchmany(self, n):
        return self.lotes.pop(0) if self.lotes else []

    def close(self):
        self.cerrado = True


class ConexionFalsa:
    def __init__(self, cursor=None):
        self._cursor = cursor
        self.cerrada = False

    def cursor(self, *args, **kwargs):
        return self._cursor

    def close(self):
        self.cerrada = True


def _cablear(monkeypatch, cursor):
    conn = ConexionFalsa(cursor)
    monkeypatch.setattr(ev, "configuracion", lambda base=None: CONFIG)
    monkeypatch.setattr(ev, "conectar", lambda config=None: conn)
    monkeypatch.setattr(ev, "crear_cursor", lambda c: cursor)
    return conn


# --------------------------------------------------------------------------
# conectar / crear_cursor
# --------------------------------------------------------------------------
def test_conectar_arma_los_parametros(psycopg2_falso):
    centinela = object()
    psycopg2_falso.conexion = centinela
    assert ev.conectar(CONFIG) is centinela
    kwargs = psycopg2_falso.conexiones[-1]
    assert kwargs["host"] == "h" and kwargs["database"] == "d"
    assert kwargs["user"] == "u" and kwargs["password"] == "p"
    assert "statement_timeout=60000" in kwargs["options"]


def test_crear_cursor_usa_real_dict(psycopg2_falso):
    class Conn:
        def __init__(self):
            self.factory = None

        def cursor(self, cursor_factory=None):
            self.factory = cursor_factory
            return "cursor"

    conn = Conn()
    assert ev.crear_cursor(conn) == "cursor"
    assert conn.factory is psycopg2_falso.extras.RealDictCursor


# --------------------------------------------------------------------------
# configuración
# --------------------------------------------------------------------------
def test_parametros_estatus():
    assert ev._parametros_estatus(True) == ("confirmed", "confirmed")
    assert ev._parametros_estatus(False) == (None, None)


def test_leer_global_cfg(monkeypatch, tmp_path):
    cfg = tmp_path / "global.cfg"
    cfg.write_text("# comentario\n"
                   "database = postgresql://user:pass@host/base\n",
                   encoding="utf-8")
    monkeypatch.setattr(ev, "_ruta_global_cfg", lambda: str(cfg))
    assert ev._leer_global_cfg() == {"host": "host", "database": "base",
                                     "user": "user", "password": "pass"}


def test_leer_global_cfg_sin_archivo(monkeypatch):
    monkeypatch.setattr(ev, "_ruta_global_cfg", lambda: None)
    assert ev._leer_global_cfg() is None


def test_leer_global_cfg_sin_base(monkeypatch, tmp_path):
    cfg = tmp_path / "global.cfg"
    cfg.write_text("database = postgresql://user:pass@host\n", encoding="utf-8")
    monkeypatch.setattr(ev, "_ruta_global_cfg", lambda: str(cfg))
    assert ev._leer_global_cfg() is None


def test_configuracion_entorno_gana(monkeypatch):
    monkeypatch.setattr(ev, "_leer_global_cfg", lambda: {
        "host": "hcfg", "database": "dcfg", "user": "ucfg", "password": "pcfg"})
    monkeypatch.setenv("NEWPT_DB_HOST", "henv")
    monkeypatch.delenv("NEWPT_DB_DATABASE", raising=False)
    cfg = ev.configuracion()
    assert cfg["host"] == "henv"
    assert cfg["database"] == "dcfg"
    assert cfg["user"] == "ucfg"


def test_configuracion_base_por_argumento(monkeypatch):
    monkeypatch.setattr(ev, "_leer_global_cfg", lambda: {
        "host": "h", "database": "d", "user": "u", "password": "p"})
    monkeypatch.delenv("NEWPT_DB_DATABASE", raising=False)
    cfg = ev.configuracion("otra")
    assert cfg["database"] == "otra"
    assert cfg["_origen"] == "línea de comandos"


def test_configuracion_sin_base(monkeypatch):
    monkeypatch.setattr(ev, "_leer_global_cfg", lambda: None)
    for var in ("NEWPT_DB_HOST", "NEWPT_DB_DATABASE", "NEWPT_DB_USER",
                "NEWPT_DB_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ev.FaltanParametros):
        ev.configuracion()


def test_configuracion_sin_host(monkeypatch):
    monkeypatch.setattr(ev, "_leer_global_cfg", lambda: None)
    monkeypatch.delenv("NEWPT_DB_HOST", raising=False)
    monkeypatch.setenv("NEWPT_DB_DATABASE", "d")
    with pytest.raises(ev.FaltanParametros):
        ev.configuracion()


# --------------------------------------------------------------------------
# consultas
# --------------------------------------------------------------------------
def test_consultar_eventos_de_base(monkeypatch):
    cursor = CursorFalso(respuestas=[{"desde": 1, "hasta": 2},
                                     [{"id_evento": "E1"}], {"llegadas": 5}])
    conn = _cablear(monkeypatch, cursor)
    filas, cobertura, estimadas = ev._consultar_eventos_de_base(
        "d", INI, FIN, True)
    assert filas == [{"id_evento": "E1"}]
    assert cobertura == {"desde": 1, "hasta": 2}
    assert estimadas == 5
    assert conn.cerrada
    params = [e[1] for e in cursor.ejecutados if e[1]]
    assert (INI, FIN, "confirmed", "confirmed") in params


def test_consultar_inventario_de_base(monkeypatch):
    cursor = CursorFalso(respuestas=[[{"red": "IU"}]])
    _cablear(monkeypatch, cursor)
    assert ev._consultar_inventario_de_base("d", INI, FIN) == [{"red": "IU"}]
    # El orden de los parámetros es (fin, inicio).
    params = [e[1] for e in cursor.ejecutados if e[1]]
    assert (FIN, INI) in params


def test_consultar_bindings_de_base(monkeypatch):
    cursor = CursorFalso(respuestas=[[
        {"red": "IU", "estacion": "ABC"},
        {"red": "", "estacion": "X"},
        {"red": "IU", "estacion": None},
    ]])
    _cablear(monkeypatch, cursor)
    assert ev._consultar_bindings_de_base("d") == {("IU", "ABC")}


def test_consultar_actividad_de_base(monkeypatch):
    t1 = datetime(2020, 6, 1, 10)
    t2 = datetime(2020, 6, 1, 9)
    cursor = CursorFalso(respuestas=[[
        {"red": "IU", "estacion": "ABC", "instante": t1},
        {"red": "IU", "estacion": "ABC", "instante": t2},
        {"red": "IU", "estacion": "ABC", "instante": None},
        {"red": "CX", "estacion": "XYZ", "instante": t1},
    ]])
    _cablear(monkeypatch, cursor)
    actividad = ev._consultar_actividad_de_base("d", datetime(2020, 6, 1, 12), 24)
    assert actividad[("IU", "ABC")] == [t2, t1]
    assert ("CX", "XYZ") in actividad


# --------------------------------------------------------------------------
# _bases_seiscomp
# --------------------------------------------------------------------------
def test_bases_seiscomp(monkeypatch, psycopg2_falso):
    cursor = CursorFalso(respuestas=[[("seiscomp",), ("seiscomp2",)]])
    conn = ConexionFalsa(cursor)
    psycopg2_falso.conexion = conn
    monkeypatch.setattr(ev, "configuracion", lambda base=None: CONFIG)
    assert ev._bases_seiscomp() == ["seiscomp", "seiscomp2"]
    assert conn.cerrada


def test_bases_seiscomp_falla_devuelve_vacio(monkeypatch, psycopg2_falso):
    psycopg2_falso.error_conectar = Exception("pg_hba.conf")
    monkeypatch.setattr(ev, "configuracion", lambda base=None: CONFIG)
    assert ev._bases_seiscomp() == []


def test_bases_seiscomp_sin_filas_cae_a_la_config(monkeypatch, psycopg2_falso):
    cursor = CursorFalso(respuestas=[[]])
    psycopg2_falso.conexion = ConexionFalsa(cursor)
    monkeypatch.setattr(ev, "configuracion", lambda base=None: CONFIG)
    assert ev._bases_seiscomp() == ["d"]


# --------------------------------------------------------------------------
# estimar_no_picadas
# --------------------------------------------------------------------------
def test_estimar_no_picadas_radio_no_positivo():
    assert ev.estimar_no_picadas(["d"], INI, FIN, radio_km=0) == (0, 0.0)


def test_estimar_no_picadas_escala_la_muestra(monkeypatch):
    cursor = CursorFalso(respuestas=[{"total": 100},
                                     {"muestra": 10, "pares": 30}])
    _cablear(monkeypatch, cursor)
    filas, mb = ev.estimar_no_picadas(["d"], INI, FIN, radio_km=100)
    assert filas == 300
    assert mb == pytest.approx(300 * ev.NO_PICADAS_BYTES_FILA / 1000000.0)


# --------------------------------------------------------------------------
# _escribir_fases_de_base
# --------------------------------------------------------------------------
def test_escribir_fases_de_base(monkeypatch, tmp_path):
    lote = [
        {"id_evento": "E1", "usada": "true", "red": "IU", "estacion": "ABC",
         "tiene_magnitud": "Si", "mag_estacion": "4.0", "mag_est_residuo": "0.1"},
        {"id_evento": "E2", "usada": "false", "red": "CX", "estacion": "XYZ"},
    ]
    batch = CursorFalso(lotes=[[lote[0], lote[1]], []])
    conn = ConexionFalsa(batch)
    monkeypatch.setattr(ev, "configuracion", lambda base=None: CONFIG)
    monkeypatch.setattr(ev, "conectar", lambda config=None: conn)
    monkeypatch.setattr(ev, "crear_cursor", lambda c: CursorFalso())

    ruta = tmp_path / "fases.csv"
    ruta.write_text("", encoding="utf-8")
    resumen = {}
    pasos = []

    total = ev._escribir_fases_de_base(
        "d", INI, FIN, False, {"E1": "d"}, str(ruta), resumen, esperado=1,
        progreso=lambda escritas, esperado: pasos.append((escritas, esperado)))

    assert total == 1                       # solo E1 es dueño de la base "d"
    assert "E1" in ruta.read_text(encoding="utf-8")
    assert resumen["E1"]["fases"] == 1
    assert pasos == [(1, 1)]
    assert batch.cerrado


# --------------------------------------------------------------------------
# no_picadas_de_evento_desde_base
# --------------------------------------------------------------------------
def _fila_inventario():
    return {"red": "IU", "estacion": "ABC", "loc": "00", "cha": "BHZ",
            "latitud": -26.0, "longitud": -70.0, "elevacion": "1000",
            "lugar": "Lugar", "pais": "Chile",
            "epoca_inicio": datetime(2019, 1, 1)}


def test_no_picadas_de_evento_desde_base(monkeypatch):
    monkeypatch.setattr(ev, "_consultar_bindings_de_base",
                        lambda base: {("IU", "ABC")})
    monkeypatch.setattr(ev, "_consultar_inventario_de_base",
                        lambda base, i, f: [_fila_inventario()])
    monkeypatch.setattr(ev, "_consultar_actividad_de_base",
                        lambda base, inst, horas, solo: {})
    filas, descartadas = ev.no_picadas_de_evento_desde_base(
        "d", datetime(2020, 6, 1), "E1", "O1", -26.0, -70.0, set(),
        radio_km=100.0)
    assert len(filas) == 1
    assert filas[0]["estacion"] == "ABC"
    assert descartadas == 0
