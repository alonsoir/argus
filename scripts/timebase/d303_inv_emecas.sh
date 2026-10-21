#!/usr/bin/env bash
# DAY303: inventario de solo lectura de EMECAS y del perfil de compilacion. Mac, raiz del repo.
set -u
DIA=day303
OUT=logs/lab/$DIA/inv_emecas.txt
mkdir -p logs/lab/$DIA
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "E1/E4 cuerpos de emecas, emecas++ y emecas+++"
git grep -n -A 22 -E "^emecas:" -- Makefile
git grep -n -A 30 -E "^emecas\+\+:" -- Makefile
git grep -n -A 4 -E "^emecas\+\+\+:" -- Makefile
sec "E2 definicion de PROFILE y de los directorios de build"
git grep -n -E "^(override )?PROFILE[[:space:]]*[?:+]?=|^[A-Z_]*BUILD_DIR[[:space:]]*[?:]?=|^BUILD_ACTIVE|build-active" -- Makefile
sec "E3 bootstrap y test-all"
git grep -n -A 20 -E "^bootstrap:" -- Makefile
git grep -n -A 4 -E "^test-all:" -- Makefile
sec "usos de PROFILE dentro de recetas de emecas/bootstrap"
git grep -n -E "PROFILE=" -- Makefile
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
