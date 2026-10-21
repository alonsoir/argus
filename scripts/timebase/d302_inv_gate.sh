#!/usr/bin/env bash
# DAY302: inventario del gate (solo lectura): test-firewall-e2e, test-components, EMECAS, etiquetas ctest y SetUp de
# IPSetWrapperTest. Mac, raiz del repo.
set -u
DIA=day302
OUT=logs/lab/$DIA/inv_gate.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "G1 Makefile: test-firewall-e2e"
git grep -n -A 25 -E "^test-firewall-e2e" -- Makefile
sec "G3 Makefile: test-components"
git grep -n -A 30 -E "^test-components" -- Makefile
sec "G2 Makefile: objetivos EMECAS y quien llama a test-firewall-e2e"
git grep -n -E "^emecas[A-Za-z0-9+_-]*:|test-firewall-e2e|test-components" -- Makefile
sec "G4 CMake del firewall: etiquetas, gtest_discover_tests, SKIP_RETURN_CODE"
git grep -n -B 3 -A 6 -E "LABELS|gtest_discover_tests|SKIP_RETURN_CODE" -- "$FW/CMakeLists.txt"
sec "G5 IPSetWrapperTest: fixture y SetUp"
git grep -n -B 3 -A 15 "class IPSetWrapperTest" -- "$FW/tests/unit/test_ipset_wrapper.cpp"
sec "G5 tests que miran geteuid"
git grep -n "geteuid" -- "$FW/tests"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
