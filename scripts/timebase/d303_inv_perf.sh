#!/usr/bin/env bash
# DAY303: inventario de solo lectura de los tests de rendimiento de IPSetWrapperTest y del mecanismo del wrapper.
# Mac, raiz del repo.
set -u
DIA=day303
OUT=logs/lab/$DIA/inv_perf.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
T=$FW/tests/unit/test_ipset_wrapper.cpp
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "fixture IPSetWrapperTest (SetUp/TearDown) e includes"
git grep -n -E "^#include" -- "$T"
git grep -n -A 30 "class IPSetWrapperTest" -- "$T"
sec "Q1 BatchAddPerformance"
git grep -n -A 26 "TEST_F(IPSetWrapperTest, BatchAddPerformance)" -- "$T"
sec "Q2 TestPerformance"
git grep -n -A 31 "TEST_F(IPSetWrapperTest, TestPerformance)" -- "$T"
sec "Q2 StressTestLargeSet (por si tambien mide tiempos)"
git grep -n -A 34 "TEST_F(IPSetWrapperTest, StressTestLargeSet)" -- "$T"
sec "Q3 mecanismo de ejecucion en ipset_wrapper.cpp"
git grep -n -E "fork|exec[lv]|popen|system\(|posix_spawn|restore" -- "$FW/src/core/ipset_wrapper.cpp"
sec "Q3 IPSetWrapper::test"
git grep -n -A 30 -E "IPSetWrapper::test\(" -- "$FW/src/core/ipset_wrapper.cpp"
sec "Q4 llamadas a test() fuera de los tests"
git grep -n -E "(\.|->)test\(" -- "$FW/src" "$FW/include"
sec "Q5 TEST_SOURCES"
git grep -n -B 2 -A 20 -E "set\(TEST_SOURCES" -- "$FW/CMakeLists.txt"
sec "cmake_minimum_required"
git grep -n "cmake_minimum_required" -- "$FW/CMakeLists.txt"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
