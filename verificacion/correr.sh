#!/usr/bin/env bash
# ==============================================================================
# correr.sh — corre los scripts de comprobación de verificacion/
#
#   * offline/: siempre (no necesitan pantalla).
#   * gui/:     solo si hay DISPLAY; si no, se saltean con un aviso.
#
# Los scripts que bloquean en mainloop se cortan con timeout: que terminen
# "colgados" es lo esperado cuando todo sale bien.
#
# Uso:
#   ./verificacion/correr.sh            # todo
#   ./verificacion/correr.sh offline    # solo offline
#   ./verificacion/corror.sh gui        # solo gui (falla sin DISPLAY)
# ==============================================================================
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO="$(cd "$DIR/.." && pwd)"
PY="$PROYECTO/.venv/bin/python"
TIMEOUT_SEG=120

if [ ! -x "$PY" ]; then
    echo "No está el venv en $PY — crealo con ./supervisor.sh o preparar_venv.sh"
    exit 2
fi

GRUPO="${1:-todo}"
[ "$GRUPO" = "todo" ] && GRUPOS="offline gui" || GRUPOS="$GRUPO"

FALLAS=0
CORRIDOS=0

for g in $GRUPOS; do
    [ -d "$DIR/$g" ] || { echo "No existe $DIR/$g"; exit 2; }
    echo "==================== $g ===================="
    for script in "$DIR/$g"/*.py; do
        nombre="$(basename "$script")"
        if [ "$g" = "gui" ] && [ -z "${DISPLAY:-}" ]; then
            echo "  SALTEADO $nombre (sin DISPLAY)"
            continue
        fi
        echo "--- $nombre"
        if [ "$g" = "gui" ]; then
            # Los de pantalla se cuelgan en mainloop si todo va bien.
            timeout "$TIMEOUT_SEG" "$PY" "$script" 2>&1 | tail -15
            rc=${PIPESTATUS[0]}
        else
            "$PY" "$script" 2>&1 | tail -15
            rc=${PIPESTATUS[0]}
        fi
        if [ "$rc" -eq 0 ]; then
            CORRIDOS=$((CORRIDOS + 1))
        else
            FALLAS=$((FALLAS + 1))
            echo "  -> $nombre terminó con código $rc"
        fi
    done
done

echo "==================== resumen ===================="
echo "  OK: $CORRIDOS   FALLAN: $FALLAS"
[ "$FALLAS" -eq 0 ] || exit 1
