#!/usr/bin/env bash
# Corredor de los tests unitarios de RCS.
#
#   ./tests/correr.sh                 # toda la suite (sin gui ni db)
#   ./tests/correr.sh base            # tests/base (suite entregada)
#   ./tests/correr.sh ampliacion      # tests/ampliacion (sin gui ni db)
#   ./tests/correr.sh gui             # tests/ampliacion/gui  (necesita DISPLAY)
#   ./tests/correr.sh db              # tests/ampliacion/db
#   ./tests/correr.sh red             # tests/ampliacion/red  (con mock)
#   ./tests/correr.sh -k comparacion  # filtro por nombre (mantiene el filtro)
#
# Usa el intérprete del entorno virtual del proyecto.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${RAIZ}/.venv/bin/python"

if [[ ! -x "${PY}" ]]; then
    echo "[X] No está el entorno virtual (${PY})."
    echo "    Créalo con ./preparar_venv.sh e instala requirements-dev.txt."
    exit 1
fi

# Filtro por defecto: los que necesitan pantalla o base quedan afuera.
FILTRO=(-m "not gui and not db")

uso() {
    cat <<'FIN'
Uso: ./tests/correr.sh [grupo] [args de pytest...]

Sin argumentos corre toda la suite (menos gui y db).

Grupos:
  base          tests/base (suite entregada, congelada)
  ampliacion    tests/ampliacion (menos gui y db)
  modulos       tests/ampliacion/modulos
  bordes        tests/ampliacion/bordes
  scripts       tests/ampliacion/scripts
  red           tests/ampliacion/red (con mock)
  gui           tests/ampliacion/gui (necesita DISPLAY, marca gui)
  db            tests/ampliacion/db  (marca db)
  todo          toda la suite, sin excluir gui ni db

Ejemplos:
  ./tests/correr.sh -k comparacion   # filtro por nombre (mantiene el filtro)
  ./tests/correr.sh base -v
  ./tests/correr.sh gui
FIN
}

case "${1:-}" in
    -h|--help) uso; exit 0;;
esac

if [[ $# -eq 0 ]]; then
    exec "${PY}" -m pytest "${FILTRO[@]}"
fi

grupo="$1"
shift

case "$grupo" in
    base)       set -- tests/base "$@";;
    ampliacion) set -- tests/ampliacion "$@";;
    modulos)    set -- tests/ampliacion/modulos "$@";;
    bordes)     set -- tests/ampliacion/bordes "$@";;
    scripts)    set -- tests/ampliacion/scripts "$@";;
    red)        set -- tests/ampliacion/red "$@";;
    gui)        set -- tests/ampliacion/gui "$@";;
    db)         set -- tests/ampliacion/db "$@";;
    todo)       exec "${PY}" -m pytest "$@";;
    *)          set -- "$grupo" "$@";;
esac

# Si el usuario ya pasó -m, se respeta y no se agrega el filtro por defecto.
for a in "$@"; do
    if [[ "$a" == "-m" || "$a" == -m=* ]]; then
        exec "${PY}" -m pytest "$@"
    fi
done

# Los grupos gui/db ya seleccionan por carpeta y no llevan el filtro por defecto.
case "$grupo" in
    gui|db) exec "${PY}" -m pytest "$@";;
    *)      exec "${PY}" -m pytest "${FILTRO[@]}" "$@";;
esac
