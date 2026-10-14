#!/usr/bin/bash
# ==============================================================================
# traer_plantuml.sh
# Baja el plantuml.jar (no versionado, pesado) y renderiza los .puml de
# docs/proyecto/plantuml/ a PNG en docs/proyecto/img/.
#
# El .jar NO va al repositorio: se baja acá. El render necesita Java (y, para
# algunos diagramas, Graphviz; este proyecto no lo usa: los diagramas se
# eligieron para que rendericen con el motor propio de PlantUML).
#
# Uso:
#   docs/proyecto/herramientas/traer_plantuml.sh          # baja el jar si falta
#   docs/proyecto/herramientas/traer_plantuml.sh --render # además renderiza
#   docs/proyecto/herramientas/traer_plantuml.sh --render solo 07_modelo_relacional_seiscomp
# ==============================================================================

set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO="$(cd "$DIR/.." && pwd)"
PLANTUML="$DIR/plantuml.jar"
PUML="$PROYECTO/plantuml"
IMG="$PROYECTO/img"
URL="https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar"

bajar_jar() {
    if [ -f "$PLANTUML" ]; then
        echo "[plantuml] Ya existe $PLANTUML"
        return 0
    fi
    echo "[plantuml] Bajando plantuml.jar ..."
    if ! curl -sL -o "$PLANTUML" "$URL"; then
        echo "[plantuml] ERROR: no se pudo bajar el jar (¿sin red?)."
        echo "           Los .puml quedan en $PUML para renderizarlos aparte."
        return 1
    fi
    echo "[plantuml] Listo: $PLANTUML"
}

renderizar() {
    local filtro="${1:-}"
    if ! command -v java >/dev/null 2>&1; then
        echo "[plantuml] ERROR: no hay 'java' en el PATH; no se puede renderizar."
        return 1
    fi
    [ -f "$PLANTUML" ] || bajar_jar || return 1
    mkdir -p "$IMG"
    local archivos
    if [ -n "$filtro" ]; then
        archivos="$PUML/$filtro.puml"
    else
        archivos="$PUML/*.puml"
    fi
    echo "[plantuml] Renderizando $archivos -> $IMG ..."
    # -tsvg daría vectores; se usa PNG porque python-docx embebe PNG.
    java -jar "$PLANTUML" -tpng -charset UTF-8 -o "$IMG" $archivos
}

case "${1:-}" in
    --render)
        renderizar "${2:-}"
        ;;
    --jar)
        bajar_jar
        ;;
    *)
        bajar_jar
        ;;
esac
