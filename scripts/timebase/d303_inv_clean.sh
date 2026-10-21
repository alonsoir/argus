#!/usr/bin/env bash
# DAY303 K1: que limpia clean-all / clean-libs, si pregunta algo, y que levanta make up
set -u
cuerpo() { awk -v t="$1" '$0 ~ "^"t":" {p=1; print FILENAME":"NR": "$0; next} p && /^[^\t#]/ {exit} p {print NR": "$0}' Makefile; }
for t in clean-all clean-libs up; do echo "===== K1 cuerpo de $t ====="; cuerpo "$t"; done
echo "===== K1 lecturas interactivas en esos objetivos ====="
for t in clean-all clean-libs; do cuerpo "$t"; done | grep -n -E 'read |confirm|\[y/N\]|-i ' || echo "ninguna"
echo "===== K1 directorios de build que existen hoy en el repo ====="
ls -d */build* */build-* 2>/dev/null | sort -u
