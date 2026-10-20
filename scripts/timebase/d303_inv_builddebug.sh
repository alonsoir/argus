#!/usr/bin/env bash
# DAY303: inventario de solo lectura de los build-debug fijos del Makefile, set-build-profile y perfiles sanitizer.
# Mac, raiz del repo.
set -u
DIA=day303
OUT=logs/lab/$DIA/inv_builddebug.txt
mkdir -p logs/lab/$DIA
sec() { printf '\n===== %s =====\n' "$1"; }
objetivo_de() {  # imprime el objetivo de make que contiene la linea $1
  LC_ALL=C awk -v n="$1" 'NR<=n && /^[A-Za-z0-9_.+-]+:/ {t=$0; l=NR} NR==n {print "linea " n " -> objetivo (linea " l "): " t; exit}' Makefile
}
{
sec "G1/G2/G4 objetivo que contiene cada build-debug fijo"
for n in $(git grep -n "build-debug" -- Makefile | cut -d: -f2); do objetivo_de "$n"; done
sec "G1 objetivo tools y TOOLS_BUILD_DIR"
git grep -n -A 12 -E "^tools:" -- Makefile
sec "G2 contexto de los actos de Vault (1530-1565)"
sed -n '1528,1566p' Makefile
sec "G3 set-build-profile.sh"
cat etcd-server/config/set-build-profile.sh
sec "G5 Jenkinsfile en el repo"
git ls-files | grep -i -E "jenkins" || echo "(ningun fichero Jenkins trackeado)"
sec "G6 objetivos tsan/asan"
sed -n '2140,2225p' Makefile
git grep -n -E "PROFILE=asan|asan" -- Makefile | head -20
sec "perfiles en CMake de los componentes (flags sanitizer)"
git grep -n -E "fsanitize" -- '*/CMakeLists.txt' '*.cmake' | head -30
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
