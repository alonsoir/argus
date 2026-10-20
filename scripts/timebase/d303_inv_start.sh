#!/usr/bin/env bash
# DAY303 K7: cuerpo de pipeline-build y pipeline-start; de donde arranca cada componente
set -u
cuerpo() { awk -v t="$1" '$0 ~ "^"t":" {p=1; print NR": "substr($0,1,120); next} p && /^[^\t#]/ {exit} p {print NR": "substr($0,1,170)}' Makefile; }
for t in pipeline-build pipeline-start; do echo "===== K7 cuerpo de $t ====="; cuerpo "$t"; done
echo "===== K7 lineas de arranque (tmux new-session) y de donde sale el binario ====="
git grep -n -E 'tmux new-session' -- Makefile | grep -o -E '^Makefile:[0-9]+:|cd [^ ;&]+|build-active[^ ;&]*|\$\([A-Z_]+_BUILD_DIR\)[^ ;&]*' | paste -sd' ' | sed 's/ Makefile:/\nMakefile:/g'
echo "===== K7 definiciones *_BUILD_DIR ====="
git grep -n -E '^[A-Z_]+_BUILD_DIR[[:space:]]*:?=' -- Makefile | cut -c1-130
