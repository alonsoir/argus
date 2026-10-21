#!/usr/bin/env bash
# DAY303: inventario de solo lectura para separar IPSetWrapperTest y cerrar el gate. Mac, raiz del repo.
set -u
DIA=day303
OUT=logs/lab/$DIA/inv_gate2.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "P1 git"
git status -sb
git log --oneline -5
sec "P2 CMake: definicion de firewall_tests y su registro"
git grep -n -A 25 -E "add_executable\(firewall_tests" -- "$FW/CMakeLists.txt"
git grep -n -B 2 -A 8 -E "gtest_discover_tests\(firewall_tests" -- "$FW/CMakeLists.txt"
sec "P3 TEST_F de IPSetWrapperTest"
git grep -n -E "TEST_F\(IPSetWrapperTest" -- "$FW/tests/unit/test_ipset_wrapper.cpp"
echo "total: $(git grep -c -E 'TEST_F\(IPSetWrapperTest' -- "$FW/tests/unit/test_ipset_wrapper.cpp")"
sec "P3 quien compila test_ipset_wrapper.cpp"
git grep -n "test_ipset_wrapper" -- "$FW/CMakeLists.txt" Makefile
sec "P4 Makefile: test-firewall-e2e"
git grep -n -A 25 -E "^test-firewall-e2e" -- Makefile
sec "P5 Makefile: ctest dentro de test-components"
git grep -n -A 40 -E "^test-components" -- Makefile | grep -n -i -E "ctest|firewall"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
