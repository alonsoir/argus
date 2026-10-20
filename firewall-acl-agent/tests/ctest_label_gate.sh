#!/usr/bin/env bash
# [ARGUS-GATE-PERF-D303] Puerta de ctest por etiqueta del firewall-acl-agent. Se ejecuta DENTRO del defender;
# la lanzan desde el Mac "make test-firewall-e2e" y "make test-firewall-perf" (PROFILE=production).
# FALLA (rc 1) si: ctest falla, no hay ningun test con la etiqueta, o aparece CUALQUIER test saltado
# (ctest "***Skipped" / "***Not Run" / "did not run", o gtest "[  SKIPPED ]"). Un saltado no es un pasado.
# [ARGUS-GATE-PERF-D303-B] Y si alguna ejecucion de gtest corre 0 tests: un test que no ejecuta nada no es un pasado.
set -u
BUILD=${1:?uso: ctest_label_gate.sh BUILD_DIR ETIQUETA}
ETIQUETA=${2:?uso: ctest_label_gate.sh BUILD_DIR ETIQUETA}
LOG=/tmp/argus_ctest_${ETIQUETA}.log
cd "$BUILD" || { echo "[CTEST-GATE] FALLA: no existe $BUILD"; exit 1; }
echo "[CTEST-GATE] etiqueta=$ETIQUETA build=$BUILD log=$LOG"
sudo env LD_LIBRARY_PATH=/usr/local/lib ctest -L "$ETIQUETA" -V 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}
TOTAL=$(LC_ALL=C awk '/tests failed out of/ {print $NF}' "$LOG" | tail -1)
SALT_CTEST=$(grep -c -E '\*\*\*(Skipped|Not Run)' "$LOG")
SALT_GTEST=$(grep -c -F '[  SKIPPED ]' "$LOG")
NO_RUN=$(grep -c -F 'did not run' "$LOG")
VACIOS=$(grep -c -F '0 tests from 0 test suites ran' "$LOG")
echo
echo "[CTEST-GATE] resumen etiqueta=$ETIQUETA rc_ctest=$RC tests=${TOTAL:-0} saltados_ctest=$SALT_CTEST saltados_gtest=$SALT_GTEST did_not_run=$NO_RUN gtest_vacios=$VACIOS"
if grep -q -F '[PERF]' "$LOG"; then
    echo "[CTEST-GATE] medidas:"
    grep -F '[PERF]' "$LOG" | sed 's/^[0-9]*: //'
fi
if [ "$RC" -ne 0 ] || [ -z "$TOTAL" ] || [ "$TOTAL" = "0" ] || [ "$SALT_CTEST" -ne 0 ] || [ "$SALT_GTEST" -ne 0 ] || [ "$NO_RUN" -ne 0 ] || [ "$VACIOS" -ne 0 ]; then
    echo "[CTEST-GATE] FALLA ($ETIQUETA)"
    exit 1
fi
echo "[CTEST-GATE] PASA ($ETIQUETA): ${TOTAL} tests, 0 saltados"
