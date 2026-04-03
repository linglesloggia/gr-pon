#!/bin/sh
export PYTHONPATH=/home/4moulins/projects/gr-pon/python:$PYTHONPATH
FG_SCRIPT=/home/4moulins/projects/gr-pon/examples/full_pon_demod.py

# Ajusta estos parámetros según tus necesidades
STABLE=4        # segundos sin cambio para considerar terminado
TIMEOUT=300     # segundos max por fichero

# Glob a tus captures (modifica si el patrón es distinto)
for f in /home/4moulins/projects/*/scope_captures/*.f32; do
  [ -f "$f" ] || continue
  base=$(basename "$f")
  # expdir = parent of scope_captures
  expdir=$(dirname "$(dirname "$f")")
  outdir="$expdir/pbcdframe"
  mkdir -p "$outdir"

  export GPON_IN_FILE="$f"
  export GPON_OUT_DIR="$outdir"
  export QT_QPA_PLATFORM=offscreen

  echo "Processing: $f -> $outdir/$base"
  # start the flowgraph in background
  python3 "$FG_SCRIPT" &
  pid=$!
  start=$(date +%s)
  last_size=-1
  stable_since=0

  # wait loop: check size of jsonl (legible) to detect activity
  while true; do
    sleep 1
    size=$(stat -c%s "$outdir/gpon_payloads.jsonl" 2>/dev/null || echo 0)

    if [ "$size" -eq "$last_size" ]; then
      if [ "$stable_since" -eq 0 ]; then
        stable_since=$(date +%s)
      else
        now=$(date +%s)
        if [ $((now - stable_since)) -ge $STABLE ]; then
          echo "Stable for $STABLE s; stopping flowgraph (pid $pid)"
          kill "$pid" 2>/dev/null || true
          wait "$pid" 2>/dev/null || true
          break
        fi
      fi
    else
      stable_since=0
      last_size=$size
    fi

    now=$(date +%s)
    if [ $((now - start)) -ge $TIMEOUT ]; then
      echo "Timeout ($TIMEOUT s) reached; killing $pid"
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      break
    fi
  done

  echo "Done: $f -> outputs in $outdir (binary: output, hex/jsonl files)"
done
