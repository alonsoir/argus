#!/usr/bin/env bash
# Localiza la definicion de DdosKernelReader::start() y muestra historia + cuerpo.
set -uo pipefail
echo "== ficheros que mencionan DdosKernelReader =="
git grep -l "DdosKernelReader" -- sniffer/ ':!sniffer/tests'
echo
for f in $(git grep -l "DdosKernelReader" -- sniffer/ ':!sniffer/tests'); do
  n=$(grep -n -E 'bool[[:space:]]+(DdosKernelReader::)?start[[:space:]]*\(' "$f" | head -1 | cut -d: -f1)
  [ -z "$n" ] && continue
  echo "== $f : start() en linea $n =="
  echo "-- historia --"
  git log --oneline -6 -- "$f"
  echo "-- cuerpo --"
  sed -n "${n},$((n+35))p" "$f"
  echo
done
