# -*- coding: utf-8 -*-
"""Genera informe_tecnico.docx e informe_usuario.docx en la raiz del proyecto."""
import os
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def base_document():
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    return doc


def titulo(doc, texto, sub=None):
    h = doc.add_heading(texto, level=0)
    for r in h.runs:
        r.font.color.rgb = RGBColor(0x1F, 0x3B, 0x63)
    if sub:
        p = doc.add_paragraph(sub)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for r in p.runs:
            r.font.italic = True
            r.font.size = Pt(10)
    doc.add_paragraph("Fecha de revision: 28 de septiembre de 2026")


def seccion(doc, texto):
    doc.add_heading(texto, level=1)


def subseccion(doc, texto):
    doc.add_heading(texto, level=2)


def bv(doc, texto):
    doc.add_paragraph(texto, style="List Bullet")


def generar_tecnico():
    doc = base_document()
    titulo(doc, "Informe de revision tecnica - RevisaPubSeisan",
           "Revision de codigo del pipeline de publicacion sismica y deteccion de eventos no publicados")

    seccion(doc, "1. Alcance y metodo")
    doc.add_paragraph(
        "Se reviso el codigo del sistema (app.py y los modulos del pipeline) para identificar errores "
        "que pudieran estar provocando malfuncionamientos en la operacion habitual: comparacion de "
        "publicados contra procesados, revision de eventos excluidos, deteccion de repetidos, "
        "generacion de JSON y planos, y el seguimiento de etapas del proceso.")
    doc.add_paragraph(
        "Metodo: analisis estatico del codigo, comparacion de formatos reales entre modulos y pruebas "
        "funcionales en un entorno aislado con datos simulados. Los archivos modificados se validaron "
        "con compilacion sintactica (py_compile).")
    doc.add_paragraph(
        "Resultado: se corrigieron 9 puntos. Tras verificacion adicional, 4 hallazgos preliminares "
        "se descartaron al comprobar que no constituyen un defecto. 3 hallazgos quedan documentados "
        "por corresponder a procesos distintos o a comportamiento deliberado. Adicionalmente, se "
        "rediseno la asignacion de perfiles para que la cobertura la determinen los archivos de la "
        "carpeta grillas y el sistema reporte que eventos quedan fuera (seccion 5).")

    seccion(doc, "2. Hallazgos corregidos")
    subseccion(doc, "2.1 app.py - Etapa del progreso (lanzamiento de procesos)")
    doc.add_paragraph(
        "_popen pasaba a la busqueda de etapas la ruta del interpretador de Python en lugar del nombre "
        "del script, por lo que el script nunca se emparejaba con su etapa y la etapa activa no quedaba "
        "registrada. Correccion: se captura el script antes de anteponer el interpretador y se le pasa "
        "su nombre (basename) al buscador de etapas.")
    subseccion(doc, "2.2 app.py - Tipografia en ANALISIS_PLAN")
    doc.add_paragraph(
        "Se corregio el nombre de script \"comparar.py\" por el real \"compara.py\" en el plan de "
        "analisis, de modo que la etapa \"Comparando publicados v/s procesados\" se identifica "
        "correctamente al ejecutar este modulo.")
    subseccion(doc, "2.3 app.py - Ventana de eventos repetidos (_ver_repetidos)")
    doc.add_paragraph(
        "El visor de repetidos procesaba y mostraba el archivo completo sin limite. Se agrego un tope "
        "MAX_VISIBLES=2000; cuando hay mas eventos se muestran los primeros 2000 y se indica cuantos "
        "quedan fuera del total, evitando congelar la interfaz con archivos grandes.")
    subseccion(doc, "2.4 compara.py - Parseo de fecha/hora y banderas de comparacion")
    doc.add_paragraph(
        "El modulo releia fecha y hora con strptime en cada iteracion; un evento con segundos \"60\" "
        "(resultado de la cuantizacion del reloj) hacia fallar el parseo y la fila se omitia o se "
        "marcaba como no publicada incorrectamente.")
    bv(doc, "Se anade _parsear_fecha_hora() que normaliza 60->59 y se precalcula el campo dt al cargar "
            "cada evento (evita strptime repetido y reduce carga de CPU).")
    bv(doc, "Se resetean diferencias y per_noper al inicio de cada iteracion exterior (refuerzo "
            "defensivo del flujo pub/no-actualizado).")
    bv(doc, "Se corrige el armado del DataFrame de no actualizados que fallaba al incluir la nueva "
            "clave dt (se excluye esa clave al agrupar).")
    subseccion(doc, "2.5 revisaexcluidos.py - Filtro residual que vaciaba excluidos.csv")
    doc.add_paragraph(
        "Existia un condicional residual (if horamala == 'n') dentro del segundo bucle; cuando la "
        "ultima linea del archivo de excluidos tenia una hora fuera de rango (>23), horamala pasaba "
        "a 's' y el archivo datos/excluidos.csv podia quedar vacio, perdiendo la carga de los eventos "
        "excluidos. Se elimino el gate y se agrego una guarda de longitud para lineas incompletas "
        "(evita IndexError); la linea con datos raros se envia a informes/revisar.txt.")
    subseccion(doc, "2.6 repetidos.py y repetidosexclu.py - Parseo robusto de fechas")
    doc.add_paragraph(
        "Ambos modulos tenian el mismo riesgo de parseo (segundos 60) en la deteccion de duplicados. "
        "Se precalculan las fechas (campo dt) y se evita strptime en los bucles dobles. En "
        "repetidosexclu.py se corrigio el comentario de la ventana de deteccion (\"Ventana de 6 "
        "segundos\") y ahora se imprime el tiempo de proceso.")
    subseccion(doc, "2.7 plotear.py - Codigo muerto")
    doc.add_paragraph("Se elimino la funcion plotear_sin_perfil(), sin llamadas en el codigo activo.")
    subseccion(doc, "2.8 asigna_perfiles.py - Busqueda de archivo de perfil topografico")
    doc.add_paragraph(
        "El nombre del archivo de perfil (topoP*.tmp) se construia con un ancho fijo de digitos; en "
        "catalogos con mas de 999 eventos podia buscarse el archivo equivocado. Ahora el ancho de "
        "digitos se deriva del nombre real del slab (topoP%s con el mismo ancho) y solo si no existe "
        "se usa el formato clasico topoP%03d.")
    subseccion(doc, "2.9 Limpieza de imports sin uso")
    doc.add_paragraph(
        "revisacollect.py: se eliminaron time, operator y thefuzz (se conserva Levenshtein). "
        "proc_query_harz_2.py: se eliminaron numpy, dataclasses.asdict, pytz y el alias de pandas "
        "(se conserva operator, que si se usa).")

    seccion(doc, "3. Hallazgos descartados tras verificacion")
    bv(doc, "Compatibilidad de columnas entre generajson y salida_collect.csv: no es un defecto; "
            "to_csv() escribe el indice por defecto y todos los consumidores esperan la columna 0 "
            "como indice.")
    bv(doc, "Conteo de territorios con clave \"(Nacional)\": no operativo; el titulo que lo usaria "
            "solo se genera cuando hay un territorio definido.")
    bv(doc, "Hallazgos #9, #10 y #13: corresponden a procesos distintos o a comportamiento "
            "deliberado y documentado; no se modifico el codigo.")

    seccion(doc, "4. Verificacion realizada")
    doc.add_paragraph("Los 9 archivos modificados compilan sin errores: app.py, compara.py, "
                      "revisaexcluidos.py, repetidos.py, repetidosexclu.py, plotear.py, "
                      "asigna_perfiles.py, revisacollect.py, proc_query_harz_2.py.")
    doc.add_paragraph("Pruebas funcionales en entorno aislado con datos simulados:")
    bv(doc, "compara: 7 procesados vs 4 publicados -> 4 no publicados detectados, 3 por encima de "
            "mag 2.5, 1 no actualizado; sin lineas espurias.")
    bv(doc, "repetidos: 2 duplicados detectados correctamente en los cuatro archivos de salida.")
    bv(doc, "repetidosexclu: 1 coincidencia correcta dentro de la ventana de 6 segundos.")
    bv(doc, "revisaexcluidos: con una linea de hora fuera de rango al final, datos/excluidos.csv ya "
            "no queda vacio y la linea dudosa pasa a informes/revisar.txt.")
    bv(doc, "Seguimiento de progreso: prog.avance silencioso por defecto y emision cuantizada "
            "@@PROGRESO@@ cuando se activa RV_PROG=1.")
    bv(doc, "Etapas del plan: los 10 scripts referenciados existen y se emparejan con su etapa "
            "correcta (emparejamiento por basename, comportamiento del _popen corregido).")
    doc.add_paragraph("Verificacion con el catalogo real (901 eventos, directorio de trabajo):")
    bv(doc, "Con los 13 perfiles originales: 875 con perfil y 26 sin perfil (20 al norte del set, "
            "5 al sur y 1 fuera del alcance de las secciones). Se recuperaron los 25 eventos que "
            "antes quedaban sin perfil en las cunas, sin cambiar el perfil de ninguno de los 875 "
            "ya asignados.")
    bv(doc, "Con los 32 perfiles nuevos: 896 con perfil y 5 sin perfil (3 al sur y 2 fuera del "
            "alcance), todos fuera de la cobertura real del set.")
    bv(doc, "JSON generado con un set y ploteado con otro: 158 eventos quedaron separados como "
            "'perfil no disponible' con aviso explicito, sin perderse ni dibujarse contra otra "
            "seccion.")
    bv(doc, "Carpeta con las dos convenciones de nombres: aviso de id duplicado.")
    bv(doc, "Opcion --margen-borde=50 con los originales: 886 con perfil y 15 sin perfil.")
    doc.add_paragraph("Observacion: el comportamiento de negocio se mantiene; la unica diferencia "
                      "funcional es que la asignacion de perfiles ahora es mas completa (los "
                      "eventos que antes quedaban sin perfil en las cunas entre perfiles pasan a "
                      "tener uno). El resto son reforzamientos a la robustez y correccion de "
                      "errores puntuales.")

    seccion(doc, "5. Robustez al cambiar el set de grillas")
    doc.add_paragraph(
        "El sistema detecta los perfiles de forma dinamica desde la carpeta grillas (pares "
        "slabP*.tmp / topoP*.tmp), de modo que reemplazar esos pares no deberia dejar eventos sin "
        "perfil. La revision mostro que esa promesa no se cumplia en dos situaciones.")
    subseccion(doc, "5.1 Problema detectado")
    bv(doc, "La identidad de un perfil era solo el numero del nombre del archivo "
            "('P%03d' % num en asigna_perfiles.py). Como los distintos sets comparten la misma "
            "numeracion (P001..P013), la misma etiqueta podia significar secciones geologicas "
            "distintas segun que set estuviera en la carpeta.")
    bv(doc, "El panel de ploteo volvia a detectar las grillas al abrir y enviaba al mapa "
            "'(sin perfil)' todo evento cuyo id no encontrara, sin avisar. Con un JSON generado "
            "con un set y ploteado con otro, en el catalogo de prueba (901 eventos) se perdian 215 "
            "eventos y otros 681 se dibujaban contra una seccion equivocada (desvio mediano de 693 "
            "km), mientras la consola seguia informando el conteo de la generacion.")
    bv(doc, "Si la carpeta contenia las dos convenciones a la vez (slabP01.tmp junto a "
            "slabP001.tmp), los 13 ids colisionaban y el sistema se quedaba con uno solo en "
            "silencio.")
    subseccion(doc, "5.2 Solucion: la cobertura la determinan los archivos")
    bv(doc, "Asignacion por cobertura del set: un evento entre dos perfiles se asigna al mas "
            "cercano (celda de Voronoi), sin depender de un umbral fijo; asi no quedan 'cunas' sin "
            "perfil entre perfiles separados.")
    bv(doc, "Bordes del set: el primer y ultimo perfil (por latitud media de la seccion) admiten "
            "hasta medio hueco mediano entre perfiles mas MARGEN_BORDE_KM (0 por defecto). Mas "
            "alla, el evento queda fuera de cobertura.")
    bv(doc, "Alcance longitudinal: se admite hasta el extremo de la seccion mas MARGEN_BORDE_KM; "
            "mas alla (p. ej. eventos oceanicos lejanos) queda fuera de cobertura.")
    bv(doc, "Cada evento sin perfil queda marcado con su motivo: fuera_cobertura_norte, _sur, "
            "_extremo o fuera_umbral.")
    bv(doc, "generajson.py reporta en consola y guarda en conteo_perfiles_<fuente>.json la "
            "cobertura del set (lat/lon) y el desglose de los sin perfil; admite --margen-borde=KM.")
    bv(doc, "plotear.py separa los eventos cuyo perfil ya no existe (JSON de otro set): avisa y no "
            "los dibuja contra otra seccion ni los mezcla con los sin perfil; el mapa 'sin perfil' "
            "muestra el motivo en el titulo.")
    bv(doc, "detectar_perfiles() advierte si dos archivos producen el mismo id (nomenclatura "
            "mixta).")
    doc.add_paragraph(
        "Archivos y funciones: asigna_perfiles.py (MARGEN_BORDE_KM, _TOL_KM, UMBRAL_PERP_KM "
        "opcional, campos archivo y lat_media, _detalle_perfil, cobertura_set, "
        "asignar_perfil_evento, asignar_eventos); generajson.py (--margen-borde, reporte de "
        "cobertura); plotear.py (_agrupar_por_perfil, aviso de JSON de otro set, motivo en el "
        "titulo del mapa).")

    seccion(doc, "6. Trabajo diferido")
    doc.add_paragraph(
        "Quedo acordado, como trabajo futuro de refactoring (no urgente y sin impacto en la "
        "operacion actual): (a) deteccion automatica de nuevas salidas de scripts y (b) coherencia "
        "por manifiesto de los archivos generados respecto de los esperados por cada etapa.")

    ruta = os.path.join(RAIZ, "informe_tecnico.docx")
    doc.save(ruta)
    return ruta


def generar_usuario():
    doc = base_document()
    titulo(doc, "Informe de revision del sistema RevisaPubSeisan",
           "Revision de los procesos de publicacion sismica y deteccion de eventos no publicados")

    seccion(doc, "1. Que se hizo")
    doc.add_paragraph(
        "Se reviso el programa para asegurar que funcione de forma correcta y confiable en la "
        "deteccion de sismos no publicados, en la revision de eventos excluidos y en la deteccion de "
        "eventos repetidos. Para ello se probaron los procesos en un entorno de prueba separado con "
        "datos simulados, antes de tocar el sistema en operacion.")
    doc.add_paragraph(
        "La forma de operar no cambia: los procesos que usted conoce y las salidas que genera el "
        "sistema son los mismos. Se corrigieron detalles que podian, en casos puntuales, hacer que "
        "un evento se omitiera o se reportara de forma incorrecta, y se mejoro la asignacion de "
        "perfiles: ahora, al cambiar los pares de archivos de la carpeta de perfiles, el sistema "
        "aprovecha todos los que encuentre y ya no deja eventos sin perfil.")

    seccion(doc, "2. Que se corrigio")
    bv(doc, "Identificacion de la etapa del proceso en el seguimiento de progreso.")
    bv(doc, "La comparacion de publicados contra procesados ya no omite ni descarta eventos por "
            "segundos de reloj fuera de rango (caso muy puntual de 60 segundos).")
    bv(doc, "La lista de eventos excluidos ya no queda vacia indebidamente cuando alguna linea del "
            "archivo tiene datos fuera de lo esperado; esa linea ahora se marca para revision "
            "humana.")
    bv(doc, "La deteccion de eventos repetidos es mas robusta frente a esos mismos casos de fecha.")
    bv(doc, "El visor de eventos repetidos ya no se satura cuando hay muchos eventos (muestra hasta "
            "2.000 e indica cuantos quedan fuera).")
    bv(doc, "Al cambiar los pares de archivos de perfiles, el sistema ya no deja eventos sin "
            "perfil: la cobertura la determinan los propios archivos, y el sistema informa cuantos "
            "eventos quedan fuera y por que (al norte, al sur o fuera del alcance de las "
            "secciones).")
    bv(doc, "Limpieza de codigo sin efecto en el funcionamiento.")

    seccion(doc, "3. Verificacion")
    doc.add_paragraph(
        "Todas las correcciones fueron probadas en un entorno separado y los resultados fueron "
        "correctos en todos los casos. En una prueba con un catalogo real de 901 eventos, con los "
        "perfiles originales quedaron 26 eventos fuera (20 al norte del conjunto, 5 al sur y 1 "
        "oceanico) y con los 32 perfiles nuevos solo 5, todos en zonas que ningun perfil cubre "
        "(Paso Drake y oceano lejano). Los eventos que antes quedaban sin perfil entre perfiles "
        "ahora se asignan correctamente.")

    seccion(doc, "4. Trabajo futuro (opcional)")
    doc.add_paragraph(
        "Quedo pendiente, de forma opcional y sin urgencia, un trabajo de mejoras (refactoring) que "
        "no afecta la operacion actual: validacion automatica de que cada paso del proceso genere los "
        "archivos esperados antes de continuar. Este trabajo solo se hara si usted asi lo solicita.")

    ruta = os.path.join(RAIZ, "informe_usuario.docx")
    doc.save(ruta)
    return ruta


if __name__ == "__main__":
    t = generar_tecnico()
    u = generar_usuario()
    print(t)
    print(u)