#!/usr/bin/env bash
# Localiza donde se construye el id "fast-alert-" y si la rama toco ese fichero respecto a origin/main.
set -uo pipefail
git grep -n 'fast-alert-' -- sniffer/src ml-detector/src ':!*.bak*'
for f in $(git grep -l 'fast-alert-' -- sniffer/src ml-detector/src ':!*.bak*'); do
  echo "== commits de la rama en $f:"
  git log --oneline origin/main..HEAD -- "$f"
done
