#!/usr/bin/env python3
"""
agencias.py
===========
Asocia los catálogos de agencias externas (datos/eventos_agencia_<AG>.json, que
ya traen asignado el perfil más cercano) contra nuestro catálogo publicado
(datos/eventos_eventquery.json) y deja:

    datos/comparacion_agencias.json : nuestros eventos (filtrados por magnitud),
        cada uno con la lista 'agencias' de las soluciones que le corresponden.
    datos/agencias_sin_par.json     : eventos de agencia que no tienen
        contraparte en nuestro publicado.

Criterio de asociación (se considera el mismo evento si coincide en espacio y
tiempo): |Δt| <= 6 s y distancia horizontal <= 75 km. Se usa distancia en km,
no una caja de grados, para que el margen sea el mismo en el territorio
continental, insular y antártico. El Δ de magnitud se registra y se marca
cuando supera 0.2. No se exige el mismo día: la ventana de 6 s ya acota, y
exigirlo perdía el cruce de la medianoche.

Uso:
    python3 agencias.py <minmag> <agencia1> [<agencia2> ...]
"""

import csv
import datetime
import json
import os
import sys

import comparacion
import prog
import rutas

# Tolerancias de asociación (mismo evento en espacio y tiempo).
VENTANA_SEG = 6.0
TOL_KM = 75.0
TOL_MAG = 0.2

# Cambiar cuando cambie el criterio de asociación: la app lo usa para no
# reutilizar una comparación calculada con una versión anterior.
VERSION_ASOCIACION = 2


def _instante(texto):
    """Fecha/hora del evento, o None si no se puede leer."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(str(texto).strip()[:19], fmt)
        except (TypeError, ValueError):
            continue
    return None


def _numero(valor):
    return comparacion.a_numero(valor)


def _mejor_publicado(publicados, agencia_ev):
    """El evento publicado que mejor corresponde a 'agencia_ev', o None."""
    t = _instante(agencia_ev.get('fecha hora'))
    lat = _numero(agencia_ev.get('latitud'))
    lon = _numero(agencia_ev.get('longitud'))
    if t is None or lat is None or lon is None:
        return None
    mejor = None
    mejor_dt = None
    for p in publicados:
        tp = p['_dt']
        if tp is None or p['_lat'] is None or p['_lon'] is None:
            continue
        dt = abs((tp - t).total_seconds())
        if dt > VENTANA_SEG:
            continue
        distancia = comparacion.distancia_km(
            p['_lat'], p['_lon'], lat, lon)
        if distancia is None or distancia > TOL_KM:
            continue
        if mejor_dt is None or dt < mejor_dt:
            mejor_dt = dt
            mejor = p
    return mejor


def _deltas(pub, agencia_ev):
    """Δ de la solución de agencia respecto de la nuestra (los que se puedan)."""
    d = {
        'dt_seg': None, 'dist_km': None, 'dprof': None, 'dmag': None,
    }
    tp = pub['_dt']
    t = _instante(agencia_ev.get('fecha hora'))
    if tp is not None and t is not None:
        d['dt_seg'] = round(abs((tp - t).total_seconds()), 1)
    distancia = comparacion.distancia_km(
        pub['_lat'], pub['_lon'],
        _numero(agencia_ev.get('latitud')), _numero(agencia_ev.get('longitud')))
    if distancia is not None:
        d['dist_km'] = round(distancia, 1)
    prof_p, prof_a = _numero(pub.get('prof')), _numero(agencia_ev.get('prof'))
    if prof_p is not None and prof_a is not None:
        d['dprof'] = round(abs(prof_p - prof_a), 1)
    mag_p, mag_a = _numero(pub.get('magnitud')), _numero(agencia_ev.get('magnitud'))
    if mag_p is not None and mag_a is not None:
        d['dmag'] = round(abs(mag_p - mag_a), 1)
    return d


def _flags(delta):
    """Marca los parámetros que superan la tolerancia (para la viñeta/tabla)."""
    partes = []
    if delta.get('dt_seg') is not None and delta['dt_seg'] > 3:
        partes.append('time')
    if delta.get('dmag') is not None and delta['dmag'] > TOL_MAG:
        partes.append('mag')
    return "-".join(partes) + ("-" if partes else "")


def _escribir_csv(nombre, encabezados, filas):
    """Escribe un CSV (utf-8-sig, para Excel) en datos/ y devuelve la ruta."""
    ruta = rutas.p_datos(nombre)
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(encabezados)
        escritor.writerows(filas)
    return ruta


def _mismo_evento(ref, ev):
    """True si 'ev' es el mismo evento que 'ref': ≤6 s y ≤75 km."""
    tr = _instante(ref.get('fecha hora'))
    t = _instante(ev.get('fecha hora'))
    if tr is None or t is None:
        return False
    if abs((tr - t).total_seconds()) > VENTANA_SEG:
        return False
    rlat, rlon = _numero(ref.get('latitud')), _numero(ref.get('longitud'))
    lat, lon = _numero(ev.get('latitud')), _numero(ev.get('longitud'))
    if rlat is None or rlon is None or lat is None or lon is None:
        return False
    distancia = comparacion.distancia_km(rlat, rlon, lat, lon)
    return distancia is not None and distancia <= TOL_KM


def _asociar_entre_agencias(eventos):
    """
    Agrupa eventos de agencias DISTINTAS que son el mismo (≤6 s y ≤75 km).
    Devuelve una lista de grupos (listas de eventos).

    Un evento se suma a un grupo si coincide con CUALQUIER miembro (no solo con
    el primero): así una cadena A-B-C se une entera en vez de partirse cuando C
    queda a más de la ventana del representante pero dentro de la de B.
    """
    grupos = []
    for ev in eventos:
        ag = ev.get('agencia')
        colocado = False
        for grupo in grupos:
            if any(m.get('agencia') == ag for m in grupo):
                continue
            if any(_mismo_evento(m, ev) for m in grupo):
                grupo.append(ev)
                colocado = True
                break
        if not colocado:
            grupos.append([ev])
    return grupos


def _max_distancia(grupo):
    """Distancia máxima (km) entre los eventos de un grupo, o '' si no hay."""
    maximo = None
    for i in range(len(grupo)):
        for j in range(i + 1, len(grupo)):
            d = comparacion.distancia_km(
                grupo[i].get('latitud'), grupo[i].get('longitud'),
                grupo[j].get('latitud'), grupo[j].get('longitud'))
            if d is not None and (maximo is None or d > maximo):
                maximo = d
    return '' if maximo is None else round(maximo, 1)


def _texto_agencias(soluciones):
    """
    Nombres de las fuentes separados por ' + ', y con '≡' las que comparten
    ubicación (misma lat/lon a 3 decimales): la marca de solución superpuesta.
    """
    grupos = {}
    orden = []
    for sol in soluciones:
        nombre = sol.get('agencia') or 'CSN'
        lat = _numero(sol.get('latitud'))
        lon = _numero(sol.get('longitud'))
        clave = ("?", len(orden)) if (lat is None or lon is None) \
            else (round(lat, 3), round(lon, 3))
        if clave not in grupos:
            grupos[clave] = []
            orden.append(clave)
        if nombre not in grupos[clave]:
            grupos[clave].append(nombre)
    return " + ".join("≡".join(grupos[c]) for c in orden)


def _escribir_listados(pubs, sin_par):
    """
    Listados por evento (uno por pestaña), simples y compactos.

    Escribe el CSV (para descarga) y un JSON equivalente que agrega, por fila,
    el evento/grupo de origen para poder plotearlo con doble clic.
    """
    encab = ["Fecha_Hora", "Latitud", "Longitud", "Prof.", "Mag.",
             "Agencias", "Δmáx (km)"]

    # Comparación: una fila por nuestro evento (con sus agencias anidadas).
    filas_cmp = []
    json_cmp = []
    for p in pubs:
        distancias = [a['dist_km'] for a in (p.get('agencias') or [])
                      if a.get('dist_km') not in (None, '')]
        cols = [
            p.get('fecha hora', ''), p.get('latitud', ''), p.get('longitud', ''),
            p.get('prof', ''), p.get('magnitud', ''),
            _texto_agencias([p] + (p.get('agencias') or [])),
            round(max(distancias), 1) if distancias else '',
        ]
        filas_cmp.append(cols)
        json_cmp.append({"cols": cols, "evento": p})

    # Sin contraparte con CSN: una fila por evento asociado entre agencias.
    filas_sp = []
    json_sp = []
    for grupo in _asociar_entre_agencias(sin_par):
        rep = grupo[0]
        cols = [
            rep.get('fecha hora', ''), rep.get('latitud', ''),
            rep.get('longitud', ''), rep.get('prof', ''),
            rep.get('magnitud', ''), _texto_agencias(grupo),
            _max_distancia(grupo),
        ]
        filas_sp.append(cols)
        json_sp.append({"cols": cols, "eventos": grupo})

    _escribir_csv("comparacion_agencias_listado.csv", encab, filas_cmp)
    _escribir_csv("agencias_sin_par_listado.csv", encab, filas_sp)
    with open(rutas.p_datos("comparacion_agencias_listado.json"), "w") as f:
        json.dump({"encabezados": encab, "filas": json_cmp}, f, indent=2)
    with open(rutas.p_datos("agencias_sin_par_listado.json"), "w") as f:
        json.dump({"encabezados": encab, "filas": json_sp}, f, indent=2)


def _escribir_entregables(pubs, sin_par):
    """Escribe los listados de la comparación (referencia-céntrica y larga)."""
    encab_ref = [
        "Fecha_Hora", "Latitud", "Longitud", "Prof.", "Mag.", "Tipo Mag.",
        "Agencia", "Fecha_Hora agencia", "Latitud agencia", "Longitud agencia",
        "Prof. agencia", "Mag. agencia", "Tipo mag. agencia", "Δt (s)",
        "Dist (km)", "Δprof (km)", "Δmag", "Fuera de rango",
    ]
    encab_larga = [
        "Asociado", "Fuente", "Fecha_Hora", "Latitud", "Longitud", "Prof.",
        "Mag.", "Tipo Mag.", "Referencia", "Δt (s)", "Dist (km)",
        "Δprof (km)", "Δmag", "Fuera de rango",
    ]
    encab_sp = [
        "Agencia", "Fecha_Hora", "Latitud", "Longitud", "Prof.", "Mag.",
        "Tipo Mag.", "Referencia",
    ]

    filas_ref = []
    filas_larga = []
    for i, p in enumerate(pubs, start=1):
        base = [p.get('fecha hora', ''), p.get('latitud', ''),
                p.get('longitud', ''), p.get('prof', ''), p.get('magnitud', ''),
                p.get('tipo', '')]
        ags = p.get('agencias') or []
        if not ags:
            filas_ref.append(base + [''] * 12)
        for a in ags:
            filas_ref.append(base + [
                a.get('agencia', ''), a.get('fecha hora', ''),
                a.get('latitud', ''), a.get('longitud', ''), a.get('prof', ''),
                a.get('magnitud', ''), a.get('tipo', ''), a.get('dt_seg', ''),
                a.get('dist_km', ''), a.get('dprof', ''), a.get('dmag', ''),
                a.get('flags', '')])
        # Formato largo: una fila por solución, agrupada por 'Asociado'.
        filas_larga.append([i, 'CSN (nuestro)'] + base
                           + [p.get('referencia', ''), '', '', '', '', ''])
        for a in ags:
            filas_larga.append([i, a.get('agencia', ''), a.get('fecha hora', ''),
                                a.get('latitud', ''), a.get('longitud', ''),
                                a.get('prof', ''), a.get('magnitud', ''),
                                a.get('tipo', ''), a.get('referencia', ''),
                                a.get('dt_seg', ''), a.get('dist_km', ''),
                                a.get('dprof', ''), a.get('dmag', ''),
                                a.get('flags', '')])

    filas_sp = [
        [e.get('agencia', ''), e.get('fecha hora', ''), e.get('latitud', ''),
         e.get('longitud', ''), e.get('prof', ''), e.get('magnitud', ''),
         e.get('tipo', ''), e.get('referencia', '')]
        for e in sin_par
    ]

    _escribir_csv("comparacion_agencias.csv", encab_ref, filas_ref)
    _escribir_csv("comparacion_agencias_larga.csv", encab_larga, filas_larga)
    _escribir_csv("agencias_sin_contraparte.csv", encab_sp, filas_sp)


def main():
    args = sys.argv[1:]
    referencia = "eventquery"
    resto = []
    for a in args:
        if a.startswith("--referencia="):
            referencia = a.split("=", 1)[1]
        else:
            resto.append(a)
    if len(resto) < 2:
        print("Uso: python3 agencias.py <minmag> <agencia1> [<agencia2> ...] "
              "[--referencia=BASE]")
        sys.exit(1)
    minmag = float(resto[0])
    agencias = resto[1:]

    ruta_pub = rutas.p_datos("eventos_%s.json" % referencia)
    if not os.path.isfile(ruta_pub):
        print("[agencias] No está %s; procese ese catálogo primero." % ruta_pub)
        sys.exit(1)
    print("[agencias] Referencia: %s" % os.path.basename(ruta_pub))
    with open(ruta_pub) as f:
        publicados = json.load(f)

    # Nos quedamos con nuestros eventos de magnitud >= minmag y los indexamos.
    pubs = []
    for p in publicados:
        mag = _numero(p.get('magnitud'))
        if mag is None or mag < minmag:
            continue
        p = dict(p)
        p['_dt'] = _instante(p.get('fecha hora'))
        p['_lat'] = _numero(p.get('latitud'))
        p['_lon'] = _numero(p.get('longitud'))
        p['agencias'] = []
        pubs.append(p)

    # Se cargan los eventos de todas las agencias primero para poder reportar
    # progreso (prog.avance) durante la asociación.
    por_agencia = {}
    total_ev = 0
    for ag in agencias:
        ruta = rutas.p_datos("eventos_agencia_%s.json" % ag)
        if not os.path.isfile(ruta):
            print("[agencias] No está %s; se omite %s." % (ruta, ag))
            continue
        with open(ruta) as f:
            por_agencia[ag] = json.load(f)
        total_ev += len(por_agencia[ag])
        print("[agencias] %s: %d eventos." % (ag, len(por_agencia[ag])))

    sin_par = []
    procesados = 0
    for ag, eventos in por_agencia.items():
        for ev in eventos:
            pub = _mejor_publicado(pubs, ev)
            if pub is None:
                sin_par.append(ev)
            else:
                delta = _deltas(pub, ev)
                pub['agencias'].append({
                    'agencia': ag,
                    'fecha hora': ev.get('fecha hora'),
                    'latitud': ev.get('latitud'),
                    'longitud': ev.get('longitud'),
                    'prof': ev.get('prof'),
                    'magnitud': ev.get('magnitud'),
                    'tipo': ev.get('tipo'),
                    'referencia': ev.get('referencia', ''),
                    'dt_seg': delta['dt_seg'],
                    'dist_km': delta['dist_km'],
                    'dprof': delta['dprof'],
                    'dmag': delta['dmag'],
                    'flags': _flags(delta),
                })
            procesados += 1
            if procesados % 200 == 0:
                prog.avance(procesados / max(1, total_ev))
    if total_ev:
        prog.avance(1.0)

    for p in pubs:
        p.pop('_dt', None)
        p.pop('_lat', None)
        p.pop('_lon', None)

    con_par = sum(1 for p in pubs if p['agencias'])
    with open(rutas.p_datos("comparacion_agencias.json"), 'w') as f:
        json.dump(pubs, f, indent=2)
    with open(rutas.p_datos("agencias_sin_par.json"), 'w') as f:
        json.dump(sin_par, f, indent=2)
    _escribir_entregables(pubs, sin_par)
    _escribir_listados(pubs, sin_par)

    print("[agencias] Comparación: %d eventos nuestros (%d con alguna agencia); "
          "sin par: %d eventos de agencia."
          % (len(pubs), con_par, len(sin_par)))


if __name__ == "__main__":
    main()
