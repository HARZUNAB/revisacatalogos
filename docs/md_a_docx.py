#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md_a_docx.py
============
Convierte los manuales en Markdown (docs/manual_tecnico.md y
docs/manual_usuario.md) a .docx con python-docx, en la raíz del proyecto.

Es el generador vigente de los .docx: los manuales se mantienen como .md (única
fuente de verdad) y este script los exporta. Reemplaza al generador anterior
(generar_manuales.py), cuyo contenido embebido quedó desactualizado respecto de
los .md.

Construcciones soportadas: encabezados (#, ##, ###), párrafos, listas (viñetas y
numeradas, con un nivel de anidado), citas (>), reglas (---), bloques de código
(```), tablas de tubería (| ... |), imágenes (![alt](ruta)) y el énfasis en
línea (**negrita**, *cursiva*, `código`).

Uso:
    python3 docs/md_a_docx.py
    python3 docs/md_a_docx.py <entrada.md> <salida.docx>
"""
import os
import re
import sys

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOCS = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(DOCS, ".."))

# Orden: primero se quita el link del Markdown (deja solo el texto visible).
_RE_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_RE_INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\*[^*]+?\*)")
_RE_ENCABEZADO = re.compile(r"^(#{1,6})\s+(.*)$")
_RE_IMAGEN = re.compile(r"^\s*!\[(.*?)\]\((.*?)\)\s*$")
_RE_VINETA = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_RE_NUMERO = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_RE_REGLA = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_RE_SEP_TABLA = re.compile(r"^\s*\|?\s*:?-{2,}[-\s:|]*\|?\s*$")


def _agregar_runs(parrafo, texto):
    """Vuelca 'texto' en 'parrafo' aplicando el énfasis en línea del Markdown."""
    texto = _RE_LINK.sub(r"\1", texto)
    for parte in _RE_INLINE.split(texto):
        if not parte:
            continue
        if parte.startswith("**") and parte.endswith("**") and len(parte) > 4:
            parrafo.add_run(parte[2:-2]).bold = True
        elif parte.startswith("`") and parte.endswith("`") and len(parte) > 2:
            run = parrafo.add_run(parte[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif (parte.startswith("*") and parte.endswith("*")
              and len(parte) > 2):
            parrafo.add_run(parte[1:-1]).italic = True
        else:
            parrafo.add_run(parte)


def _emitir_tabla(doc, lineas):
    """Convierte un bloque de tabla Markdown (tuberías) en una tabla de docx."""
    filas = []
    for linea in lineas:
        if _RE_SEP_TABLA.match(linea) or set(linea.strip()) <= set("|-: "):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        filas.append(celdas)
    if not filas:
        return
    n = max(len(f) for f in filas)
    tabla = doc.add_table(rows=0, cols=n)
    try:
        tabla.style = "Table Grid"
    except Exception:
        pass
    for i, fila in enumerate(filas):
        celdas = tabla.add_row().cells
        for j, texto in enumerate(fila):
            if j >= n:
                break
            celdas[j].text = ""
            parrafo = celdas[j].paragraphs[0]
            _agregar_runs(parrafo, texto)
            if i == 0:
                for run in parrafo.runs:
                    run.bold = True
    doc.add_paragraph()


def _estilo_lista(base, indent):
    """Estilo de lista según el anidado por sangría (espacios)."""
    if indent < 2:
        return base
    if indent < 4:
        return base + " 2"
    return base + " 3"


def convertir(md_path, docx_path, base_img=None):
    """Convierte 'md_path' a 'docx_path'. Devuelve la ruta del .docx.

    Las imágenes se resuelven relativas a 'base_img', que por defecto es la
    carpeta del propio .md (así un .md en docs/proyecto/ resuelve img/x.png
    contra docs/proyecto/img/). Antes se resolvían contra docs/ a secas, que
    solo servía para los manuales de la raíz de docs/.
    """
    if base_img is None:
        base_img = os.path.dirname(os.path.abspath(md_path))
    with open(md_path, encoding="utf-8") as f:
        lineas = f.read().split("\n")

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)

    i = 0
    total = len(lineas)
    while i < total:
        linea = lineas[i]

        # Bloque de código (``` ... ```)
        if linea.lstrip().startswith("```"):
            i += 1
            while i < total and not lineas[i].lstrip().startswith("```"):
                parrafo = doc.add_paragraph()
                parrafo.paragraph_format.space_after = Pt(0)
                run = parrafo.add_run(lineas[i])
                run.font.name = "Consolas"
                run.font.size = Pt(9)
                i += 1
            i += 1
            continue

        # Tabla (líneas que empiezan con '|')
        if linea.lstrip().startswith("|"):
            bloque = []
            while i < total and lineas[i].lstrip().startswith("|"):
                bloque.append(lineas[i])
                i += 1
            _emitir_tabla(doc, bloque)
            continue

        # Imagen
        m = _RE_IMAGEN.match(linea)
        if m:
            alt, ruta = m.group(1), m.group(2)
            if not re.match(r"^[a-zA-Z]+://", ruta):
                ruta_abs = os.path.join(base_img, ruta)
                if os.path.isfile(ruta_abs):
                    doc.add_picture(ruta_abs, width=Inches(6.0))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if alt:
                cap = doc.add_paragraph()
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = cap.add_run(alt)
                run.italic = True
                run.font.size = Pt(9)
            i += 1
            continue

        # Encabezado
        m = _RE_ENCABEZADO.match(linea)
        if m:
            nivel = min(len(m.group(1)), 3)
            enc = doc.add_heading("", level=nivel)
            _agregar_runs(enc, m.group(2))
            i += 1
            continue

        # Regla horizontal
        if _RE_REGLA.match(linea):
            i += 1
            continue

        # Cita (>) — puede abarcar varias líneas
        if linea.lstrip().startswith(">"):
            buf = []
            while i < total and lineas[i].lstrip().startswith(">"):
                buf.append(lineas[i].lstrip()[1:].strip())
                i += 1
            parrafo = doc.add_paragraph()
            try:
                parrafo.style = doc.styles["Quote"]
            except Exception:
                pass
            _agregar_runs(parrafo, " ".join(buf))
            continue

        # Viñeta
        m = _RE_VINETA.match(linea)
        if m:
            parrafo = doc.add_paragraph(
                style=_estilo_lista("List Bullet", len(m.group(1))))
            _agregar_runs(parrafo, m.group(2))
            i += 1
            continue

        # Lista numerada
        m = _RE_NUMERO.match(linea)
        if m:
            parrafo = doc.add_paragraph(
                style=_estilo_lista("List Number", len(m.group(1))))
            _agregar_runs(parrafo, m.group(2))
            i += 1
            continue

        # Línea en blanco
        if not linea.strip():
            i += 1
            continue

        # Párrafo: junta líneas consecutivas de texto hasta una en blanco o
        # una construcción especial (así los .md con líneas envueltas quedan
        # como un solo párrafo en el .docx).
        buf = [linea.strip()]
        i += 1
        while i < total:
            siguiente = lineas[i]
            if not siguiente.strip():
                break
            if (siguiente.lstrip().startswith(("|", "```", ">", "#", "!["))
                    or _RE_VINETA.match(siguiente)
                    or _RE_NUMERO.match(siguiente)
                    or _RE_REGLA.match(siguiente)):
                break
            buf.append(siguiente.strip())
            i += 1
        parrafo = doc.add_paragraph()
        _agregar_runs(parrafo, " ".join(buf))

    doc.save(docx_path)
    return docx_path


def main():
    # Con dos argumentos (md, docx) convierte ese par; sin argumentos, los
    # manuales de siempre a la raíz del proyecto. Así el documento del sistema
    # (docs/proyecto/…) se genera sin tocar la lógica de los manuales.
    if len(sys.argv) >= 3:
        md_path, docx_path = sys.argv[1], sys.argv[2]
        if not os.path.isfile(md_path):
            print("No existe %s" % md_path)
            return
        print(convertir(md_path, docx_path))
        return

    trabajos = [("manual_tecnico.md", "manual_tecnico.docx"),
                ("manual_usuario.md", "manual_usuario.docx")]
    for md, docx in trabajos:
        md_path = os.path.join(DOCS, md)
        if not os.path.isfile(md_path):
            print("No existe %s" % md_path)
            continue
        salida = convertir(md_path, os.path.join(RAIZ, docx))
        print(salida)


if __name__ == "__main__":
    main()
