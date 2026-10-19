# -*- coding: utf-8 -*-
"""Prueba de la lógica pura de estaciones sin arribos, sin base ni pantalla."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import exporta_ventana_seiscomp as E

fallos = []


def check(nombre, condicion, detalle=""):
    if condicion:
        print("  OK    %s" % nombre)
    else:
        print("  FALLA %s  -> %s" % (nombre, detalle))
        fallos.append(nombre)


def _reg(red, est, loc, cha, lat, lon, ini=None, fin=None,
         red_ini=None, red_fin=None, loc_ini=None, loc_fin=None,
         cha_ini=None, cha_fin=None, elev=100, lugar="", pais=""):
    """Una fila de inventario como la devuelve la consulta (un stream)."""
    return {
        "red": red, "estacion": est, "loc": loc, "cha": cha,
        "latitud": lat, "longitud": lon, "elevacion": elev,
        "lugar": lugar, "pais": pais,
        "epoca_inicio": ini, "epoca_fin": fin,
        "red_inicio": red_ini, "red_fin": red_fin,
        "loc_inicio": loc_ini, "loc_fin": loc_fin,
        "cha_inicio": cha_ini, "cha_fin": cha_fin,
    }


print("== _distancia_km ==")
# Santiago (-33.45,-70.67) a Valparaiso (-33.05,-71.62): con haversine sale
# 98.9 km, que es el calculo correcto sobre la esfera.
d = E._distancia_km(-33.45, -70.67, -33.05, -71.62)
check("Santiago-Valparaiso ~99 km", 95 < d < 103, "d=%s" % d)
check("distancia consigo mismo es 0",
      E._distancia_km(-33.0, -70.0, -33.0, -70.0) == 0.0)
d_grado = E._distancia_km(0.0, 0.0, 1.0, 0.0)
check("1 grado de latitud ~111.2 km", 111.1 < d_grado < 111.3, "d=%s" % d_grado)
d1 = E._distancia_km(-33.0, -70.0, -34.0, -71.0)
d2 = E._distancia_km(-34.0, -71.0, -33.0, -70.0)
check("es simetrica", abs(d1 - d2) < 1e-9, "%s vs %s" % (d1, d2))

print("== _coordenada_valida ==")
check("rechaza 0,0 (que es como llega un null)", not E._coordenada_valida(0.0, 0.0))
check("rechaza lat > 90", not E._coordenada_valida(91.0, 0.0))
check("rechaza lon < -180", not E._coordenada_valida(-30.0, -181.0))
check("acepta Chile", E._coordenada_valida(-33.45, -70.67))

print("== _vigente ==")
check("sin límites está vigente",
      E._vigente(None, None, datetime(2020, 1, 1)))
check("antes del inicio no", not E._vigente(datetime(2021, 1, 1), None,
                                            datetime(2020, 1, 1)))
check("después del fin no", not E._vigente(None, datetime(2019, 1, 1),
                                           datetime(2020, 1, 1)))
check("dentro del rango sí",
      E._vigente(datetime(2019, 1, 1), datetime(2021, 1, 1),
                 datetime(2020, 1, 1)))

print("== _indice_por_celda ==")
inventario = [
    _reg("CL", "SCL", "", "BHZ", -34.5, -70.9, ini=datetime(2000, 1, 1),
         fin=datetime(2015, 1, 1), lugar="Santiago viejo"),
    _reg("CL", "SCL", "", "BHZ", -33.45, -70.67, ini=datetime(2015, 1, 1),
         lugar="Santiago"),
    _reg("AR", "LPA", "", "BHZ", -26.5, -54.6, ini=datetime(2000, 1, 1),
         lugar="Paso de los Libres", pais="Argentina"),
    _reg("CL", "SINCOORD", "", "BHZ", None, None, ini=datetime(2000, 1, 1),
         lugar="?"),
]
indice = E._indice_por_celda(inventario)
totales = [e for celda in indice.values() for e in celda]
check("la estación sin coordenadas no entró al índice",
      not any(e["estacion"] == "SINCOORD" for e in totales), totales)
check("SCL aparece dos veces, una por época",
      sum(1 for e in totales if e["estacion"] == "SCL") == 2)
check("el índice se reparte en varias celdas", len(indice) >= 3, len(indice))
check("las coordenadas quedaron como float",
      all(isinstance(e["latitud"], float) for e in totales))
check("guarda loc y cha del stream",
      all(e["cha"] == "BHZ" for e in totales), totales)
# Duplicado exacto: la misma clave de stream dos veces no puede entrar dos veces.
duplicado = inventario + [inventario[0]]
check("una fila repetida no se duplica",
      sum(1 for e in
          [x for c in E._indice_por_celda(duplicado).values() for x in c]
          if e["estacion"] == "SCL") == 2)
# Dos streams distintos de la misma estación/época: ambos entran.
dos_streams = [
    _reg("CL", "MULTI", "", "BHZ", -33.0, -70.0, ini=datetime(2000, 1, 1)),
    _reg("CL", "MULTI", "", "BHN", -33.0, -70.0, ini=datetime(2000, 1, 1)),
]
check("dos streams de la misma estación entran los dos",
      len([e for c in E._indice_por_celda(dos_streams).values() for e in c]) == 2)

# Filtro por bindings: solo las estaciones que SeisComp tiene configurado.
idx_bind = E._indice_por_celda(inventario, bindings={("CL", "SCL")})
nombres_bind = {(v["red"], v["estacion"])
                for celda in idx_bind.values() for v in celda}
check("el índice filtra por bindings", nombres_bind == {("CL", "SCL")},
      nombres_bind)
sin_bind = {(v["red"], v["estacion"])
            for celda in E._indice_por_celda(inventario).values() for v in celda}
check("sin bindings entra todo el inventario", len(sin_bind) > 1, sin_bind)
check("bindings vacío (None) no filtra",
      {(v["red"], v["estacion"])
       for celda in E._indice_por_celda(inventario, bindings=None).values()
       for v in celda} == sin_bind)

print("== _stream_valido ==")
scl = [e for e in totales if e["estacion"] == "SCL"]
ref, n = E._stream_valido(scl, datetime(2020, 6, 1))
check("en 2020 la referencia es la época nueva",
      ref["lugar"] == "Santiago", ref)
check("cuenta 1 stream vigente", n == 1, n)
ref_vieja, _ = E._stream_valido(scl, datetime(2010, 6, 1))
check("en 2010 la referencia es la época vieja",
      ref_vieja["lugar"] == "Santiago viejo", ref_vieja)
check("antes de la primera época no hay stream",
      E._stream_valido(scl, datetime(1995, 6, 1)) == (None, 0))
check("después de la última tampoco",
      E._stream_valido([_reg("CL", "X", "", "BHZ", -33.0, -70.0,
                             ini=datetime(2000, 1, 1),
                             fin=datetime(2001, 1, 1))],
                       datetime(2010, 1, 1)) == (None, 0))
# Épocas de los cuatro niveles: basta que una no cubra para descartar.
base = datetime(2020, 6, 1)
casos = [
    ("red vencida", _reg("CL", "X", "", "BHZ", -33.0, -70.0,
                         red_ini=datetime(2000, 1, 1),
                         red_fin=datetime(2019, 1, 1))),
    ("estación vencida", _reg("CL", "X", "", "BHZ", -33.0, -70.0,
                              ini=datetime(2000, 1, 1),
                              fin=datetime(2019, 1, 1))),
    ("sensor location vencida", _reg("CL", "X", "", "BHZ", -33.0, -70.0,
                                     loc_ini=datetime(2000, 1, 1),
                                     loc_fin=datetime(2019, 1, 1))),
    ("stream vencido", _reg("CL", "X", "", "BHZ", -33.0, -70.0,
                            cha_ini=datetime(2000, 1, 1),
                            cha_fin=datetime(2019, 1, 1))),
]
for nombre, registro in casos:
    check("descarta por %s" % nombre,
          E._stream_valido([registro], base) == (None, 0))
# Cadena completa vigente.
bueno = _reg("CL", "X", "00", "BHZ", -33.0, -70.0,
             ini=datetime(2010, 1, 1), red_ini=datetime(2000, 1, 1),
             loc_ini=datetime(2010, 1, 1), cha_ini=datetime(2010, 1, 1))
ref, n = E._stream_valido([bueno], base)
check("cadena completa vigente pasa", ref is bueno and n == 1)
# Varios streams vigentes: la referencia es el de época de estación más nueva.
viejo = _reg("CL", "X", "", "BHZ", -33.0, -70.0, ini=datetime(2010, 1, 1))
nuevo = _reg("CL", "X", "00", "BHN", -33.0, -70.0, ini=datetime(2018, 1, 1))
ref, n = E._stream_valido([viejo, nuevo], base)
check("la referencia es el de época más nueva", ref is nuevo, ref)
check("cuenta los dos streams vigentes", n == 2, n)

print("== _no_picadas_de_evento ==")
evento_lat, evento_lon = -33.0, -70.8
ahora = datetime(2020, 6, 1)
actividad = {("CL", "LPA"): [datetime(2020, 6, 1, 3), datetime(2020, 6, 1, 8)],
             ("CL", "SCL"): [datetime(2020, 6, 1, 1)]}

con_picadas, desc = E._no_picadas_de_evento(
    ahora, "ev1", "origen-1", evento_lat, evento_lon, indice,
    {("CL", "SCL")}, actividad, radio_km=300.0)
check("la que tiene arribos no sale", con_picadas == [], con_picadas)
check("sin descartes en este caso", desc == 0, desc)

sin_picadas, desc = E._no_picadas_de_evento(
    ahora, "ev1", "origen-1", evento_lat, evento_lon, indice, set(), actividad,
    radio_km=300.0)
check("sale SCL una sola vez",
      [f["estacion"] for f in sin_picadas] == ["SCL"], sin_picadas)
fila = sin_picadas[0]
check("trae el id_origen", fila["id_origen"] == "origen-1", fila)
check("usa las coordenadas de la epoca vigente, no de la vieja",
      fila["est_lat"] == -33.45, fila["est_lat"])
check("distancia redondeada a un decimal",
      fila["distancia_km"] == round(fila["distancia_km"], 1), fila)
check("SCL esta a unos 50 km", 45 < fila["distancia_km"] < 60,
      fila["distancia_km"])
check("radio_km queda escrito", fila["radio_km"] == 300.0)
check("actividad_ventana cuenta 1", fila["actividad_ventana"] == 1,
      fila["actividad_ventana"])
check("streams_vigentes queda en 1", fila["streams_vigentes"] == 1, fila)
check("loc_ref/cha_ref salen del stream",
      fila["loc_ref"] == "" and fila["cha_ref"] == "BHZ", fila)
check("waveform_status es NO_CONSULTADO",
      fila["waveform_status"] == "NO_CONSULTADO", fila)
check("los campos de disponibilidad van vacíos",
      fila["availability_source"] == "" and fila["cobertura_desde"] == ""
      and fila["cobertura_hasta"] == "", fila)

# Un evento de 2010 tiene que usar la epoca vieja, con otra distancia.
viejo, _ = E._no_picadas_de_evento(datetime(2010, 6, 1), "ev0", "or0",
                                   evento_lat, evento_lon, indice, set(), {},
                                   radio_km=300.0)
check("el evento de 2010 trae la epoca vieja",
      viejo and viejo[0]["est_lugar"] == "Santiago viejo", viejo)
check("la epoca vieja esta mas lejos",
      viejo and viejo[0]["distancia_km"] > sin_picadas[0]["distancia_km"],
      viejo and viejo[0]["distancia_km"])

# Una estación cuya cadena de épocas no cubre el evento se descarta y se cuenta.
solo_vencida = E._indice_por_celda([
    _reg("CL", "VENC", "", "BHZ", -33.1, -70.8, ini=datetime(2000, 1, 1),
         fin=datetime(2005, 1, 1)),
])
filas_venc, desc = E._no_picadas_de_evento(
    ahora, "ev1", "or1", evento_lat, evento_lon, solo_vencida, set(), {},
    radio_km=300.0)
check("sin stream vigente no sale fila", filas_venc == [], filas_venc)
check("y se cuenta como descartada", desc == 1, desc)

# Radio chico: SCL sigue, LPA nunca.
check("con radio 100 km sigue entrando SCL",
      [f["estacion"] for f in
       E._no_picadas_de_evento(ahora, "ev1", "o", evento_lat, evento_lon,
                               indice, set(), actividad, radio_km=100.0)[0]]
      == ["SCL"])
check("con radio 30 km SCL queda fuera",
      E._no_picadas_de_evento(ahora, "ev1", "o", evento_lat, evento_lon,
                              indice, set(), actividad, radio_km=30.0)[0] == [])

# Sin límite (radio_km=None): entran todas las válidas, sin cortar por distancia.
sin_limite, _ = E._no_picadas_de_evento(
    ahora, "ev1", "o", evento_lat, evento_lon, indice, set(), actividad,
    radio_km=None)
nombres_lim = {f["estacion"] for f in sin_limite}
check("sin límite incluye la estación lejana (LPA)",
      "LPA" in nombres_lim, nombres_lim)
check("sin límite trae las válidas del inventario",
      nombres_lim == {"SCL", "LPA"}, nombres_lim)
check("sin límite no corta por distancia",
      all(f["radio_km"] is None for f in sin_limite), sin_limite)
check("sin límite excluye las picadas",
      all(f["estacion"] != "SCL" for f in
          E._no_picadas_de_evento(ahora, "ev1", "o", evento_lat, evento_lon,
                                  indice, {("CL", "SCL")}, actividad,
                                  radio_km=None)[0]))

# Tolerancia: se mide la actividad con dos estaciones cerca.
indice_cerca = E._indice_por_celda([
    _reg("CL", "A", "", "BHZ", -33.1, -70.8, ini=datetime(2000, 1, 1),
         lugar="A"),
    _reg("CL", "B", "", "BHZ", -33.2, -70.8, ini=datetime(2000, 1, 1),
         lugar="B"),
])
act = {("CL", "A"): [datetime(2020, 6, 1, 6), datetime(2020, 6, 1, 20),
                     datetime(2020, 6, 5)],
       ("CL", "B"): [datetime(2020, 5, 20)]}
for horas, esperado_a, esperado_b in ((0, 0, 0), (1, 0, 0), (12, 1, 0),
                                     (24, 2, 0), (24 * 30, 3, 1)):
    filas, _ = E._no_picadas_de_evento(ahora, "ev1", "o", evento_lat,
                                       evento_lon, indice_cerca, set(), act,
                                       radio_km=300.0, actividad_horas=horas)
    cuentas = {f["estacion"]: f["actividad_ventana"] for f in filas}
    check("tolerancia %g h -> A=%d B=%d" % (horas, esperado_a, esperado_b),
          cuentas.get("A") == esperado_a and cuentas.get("B") == esperado_b,
          cuentas)

# Orden por distancia.
muchas = [_reg("CL", "E%02d" % i, "", "BHZ", -33.0 + i * 0.09, -70.8,
               ini=datetime(2000, 1, 1), elev=100 + i, lugar="L%02d" % i)
          for i in range(40)]
filas, _ = E._no_picadas_de_evento(ahora, "ev2", "o2", -33.0, -70.8,
                                   E._indice_por_celda(muchas), set(), {},
                                   radio_km=300.0)
distancias = [f["distancia_km"] for f in filas]
check("con 40 estaciones entran las que estan en radio", len(filas) == 30,
      len(filas))
check("todas dentro del radio", all(d <= 300.0 for d in distancias),
      max(distancias))
check("ordenadas de mas cerca a mas lejos", distancias == sorted(distancias))

# Casos limite.
check("radio 0 no devuelve nada",
      E._no_picadas_de_evento(ahora, "ev1", "o", evento_lat, evento_lon,
                              indice, set(), actividad, radio_km=0)[0] == [])
check("coordenadas 0,0 no devuelven nada",
      E._no_picadas_de_evento(ahora, "ev1", "o", 0.0, 0.0, indice, set(),
                              actividad)[0] == [])
check("coordenadas None no devuelven nada",
      E._no_picadas_de_evento(ahora, "ev1", "o", None, None, indice, set(),
                              actividad)[0] == [])
check("sin actividad la cuenta es 0 y no falla",
      E._no_picadas_de_evento(ahora, "ev1", "o", evento_lat, evento_lon,
                              indice, set(), {}, radio_km=300.0)[0][0]
      ["actividad_ventana"] == 0)
check("inventario vacio no revienta",
      E._no_picadas_de_evento(ahora, "ev1", "o", evento_lat, evento_lon, {},
                              set(), actividad) == ([], 0))
check("sin id de evento igual calcula distancia",
      E._no_picadas_de_evento(ahora, "", "o", evento_lat, evento_lon, indice,
                              set(), actividad, radio_km=300.0)[0][0]
      ["id_evento"] == "")

print("== _ruta_no_picadas ==")
check("deriva del nombre de eventos",
      E._ruta_no_picadas("/x/seiscomp_20260101000000_20260131235959.csv")
      == "/x/seiscomp_20260101000000_20260131235959_no_picadas.csv",
      E._ruta_no_picadas("/x/seiscomp_20260101000000_20260131235959.csv"))
check("pone .csv si no hay extensión",
      E._ruta_no_picadas("/x/seiscomp_v.csv").endswith("_no_picadas.csv"))

print()
if fallos:
    print("FALLARON %d: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasaron.")
