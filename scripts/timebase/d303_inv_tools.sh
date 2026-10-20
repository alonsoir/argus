#!/usr/bin/env bash
# DAY303: inventario de solo lectura: quien compila tools/, edad de los binarios compilados, limpieza en bootstrap,
# enlace legacy de etcd-server y usos de common/build. Mac, raiz del repo (= /vagrant en la VM).
set -u
DIA=day303
OUT=logs/lab/$DIA/inv_tools.txt
mkdir -p logs/lab/$DIA
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "I1 lineas del Makefile que invocan el objetivo tools"
git grep -n -E '(^[A-Za-z0-9_.+-]+:.*[[:space:]]tools([[:space:]]|$))|MAKE\)[^#]*[[:space:]]tools([[:space:]]|$)' -- Makefile
sec "I1 cuerpo completo de bootstrap-x86-ebpf"
git grep -n -A 40 -E "^bootstrap-x86-ebpf:" -- Makefile
sec "I1 cabecera del objetivo all"
git grep -n -A 3 -E "^all:" -- Makefile
sec "I2 binarios synthetic_* compilados y su fecha"
ls -l tools/build-*/synthetic_* 2>&1
sec "I2 fecha del proto actual"
ls -l protobuf/network_security.proto protobuf/network_security.pb.* 2>&1
sec "I3 limpieza: objetivos clean y donde se llaman"
git grep -n -B 2 -A 12 "Removing profile-specific builds" -- Makefile
git grep -n -E 'MAKE\) [A-Za-z-]*clean' -- Makefile | head -20
sec "I4 ETCD_SERVER_LEGACY_LINK"
git grep -n "ETCD_SERVER_LEGACY_LINK" -- Makefile
ls -ld etcd-server/build etcd-server/build-* 2>&1
sec "I5 usos de common/build"
git grep -n "common/build" -- Makefile '*/CMakeLists.txt' '*.cmake' | head -30
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
