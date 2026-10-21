#!/usr/bin/env bash
# DAY303: inventario de solo lectura antes de cambiar PROFILE ?= debug -> production. Mac, raiz del repo.
set -u
DIA=day303
OUT=logs/lab/$DIA/inv_profile.txt
mkdir -p logs/lab/$DIA
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "F1 ficheros trackeados con build-debug escrito a mano (fuera de docs/), recuento por fichero"
git grep -c "build-debug" -- ':!docs' ':!*.md'
sec "F1 detalle (maximo 60 lineas)"
git grep -n "build-debug" -- ':!docs' ':!*.md' | head -60
sec "F2 set-build-profile"
git grep -n -A 15 -E "^set-build-profile:" -- Makefile
sec "F3 PROFILE y make en Jenkinsfile y Vagrantfile"
git grep -n -E "PROFILE|make " -- Jenkinsfile Vagrantfile
sec "F4 perfiles disponibles (ayuda del Makefile y bloques por perfil)"
git grep -n -A 12 "Build Profiles (PROFILE=name)" -- Makefile
git grep -n -E "ifeq \(\\\$\(PROFILE\)" -- Makefile
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
