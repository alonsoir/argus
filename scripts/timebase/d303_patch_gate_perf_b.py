#!/usr/bin/env python3
# DAY303 [ARGUS-GATE-PERF-D303-B]: correcciones medidas tras la tanda A.
#  - test_ipset_wrapper.cpp: fuera el main propio (escribia el aviso de root por stdout y gtest_discover_tests
#    lo registraba como un test falso que corre 0 tests y "pasa"); queda gtest_main.
#  - CMake: gtest_discover_tests aplana "e2e;root" (medido: root=4, solo los antiguos) -> una etiqueta: e2e / perf.
#  - Makefile: test-components excluye 'e2e|root|perf'.
#  - ctest_label_gate.sh: tambien FALLA si alguna ejecucion de gtest corre 0 tests.
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_gate_perf_b.py --check | --apply
import difflib
import sys
from pathlib import Path

MARCA = "[ARGUS-GATE-PERF-D303-B]"
FW = Path("firewall-acl-agent")
T = FW / "tests/unit/test_ipset_wrapper.cpp"
FIX = FW / "tests/unit/ipset_wrapper_fixture.hpp"
PERF = FW / "tests/unit/test_ipset_wrapper_perf.cpp"
GATE = FW / "tests/ctest_label_gate.sh"
CM = FW / "CMakeLists.txt"
MK = Path("Makefile")

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_gate_perf_b.py --check | --apply")
    sys.exit(2)
MODO = sys.argv[1]
FICHEROS = [T, FIX, PERF, GATE, CM, MK]
orig = {p: p.read_text(encoding="utf-8") for p in FICHEROS}
nuevo = dict(orig)
errores = []

ya = [str(p) for p in FICHEROS if MARCA in orig[p]]
if ya:
    print("YA APLICADO, no se toca nada:", ya)
    sys.exit(1)
if "[ARGUS-GATE-PERF-D303]" not in orig[CM]:
    print("PARO: la tanda A no esta aplicada")
    sys.exit(1)


def cambiar(p, viejo, nuevo_txt):
    n = nuevo[p].count(viejo)
    if n != 1:
        errores.append(f"{p}: se esperaba 1 aparicion de {viejo!r}, hay {n}")
        return
    nuevo[p] = nuevo[p].replace(viejo, nuevo_txt, 1)


# ---- 1. fuera el main propio ------------------------------------------------------------------------
INI = "int main(int argc, char** argv) {\n"
FIN = "    return result;\n}"  # medido N2: el fichero acaba en } sin salto final
t = nuevo[T]
a = t.find(INI)
b = t.find(FIN, a) if a >= 0 else -1
if t.count(INI) != 1 or b < 0:
    errores.append(f"{T}: main ({t.count(INI)} apariciones) o su cierre tras main no encontrados")
else:
    b += len(FIN)
    if t[b:b + 1] == "\n":
        b += 1
    trozo = t[a:b]
    if trozo.count("\n") >= 40:
        errores.append(f"{T}: el trozo de main mide {trozo.count(chr(10))} lineas (>= 40), no se corta")
    if a >= b or "Run: sudo ./firewall_tests" not in trozo or "RUN_ALL_TESTS()" not in trozo:
        errores.append(f"{T}: el bloque de main no es el esperado")
    else:
        nuevo[T] = t[:a] + (
            "// " + MARCA + " sin main propio: lo pone gtest_main. El de antes escribia el aviso de root por\n"
            "// stdout y gtest_discover_tests (que lista los tests sin root al compilar) lo registraba como un test\n"
            "// falso que corria 0 tests y pasaba. Sin root, el SetUp hace GTEST_SKIP y la puerta lo trata como FALLA.\n"
        ) + t[b:]

# ---- 2. CMake: una etiqueta por ejecutable ----------------------------------------------------------
cambiar(CM, 'gtest_discover_tests(ipset_wrapper_tests PROPERTIES LABELS "e2e;root")',
        "gtest_discover_tests(ipset_wrapper_tests PROPERTIES LABELS e2e)")
cambiar(CM, 'gtest_discover_tests(ipset_wrapper_perf_tests PROPERTIES LABELS "perf;root")',
        "gtest_discover_tests(ipset_wrapper_perf_tests PROPERTIES LABELS perf)")
cambiar(CM, "LABELS e2e;root  (make test-firewall-e2e; falla si algo se salta)",
        "LABEL e2e  (make test-firewall-e2e; root; falla si algo se salta)")
cambiar(CM, "LABELS perf;root (make test-firewall-perf; mide, no falla por tiempo)",
        "LABEL perf (make test-firewall-perf; root; mide, no falla por tiempo)")
cambiar(CM, "# test-components excluye root|perf: ningun Skipped por falta de root.",
        "# test-components excluye e2e|root|perf: ningun Skipped por falta de root.\n"
        "    # " + MARCA + " medido: gtest_discover_tests(PROPERTIES LABELS \"a;b\") aplana la lista y solo\n"
        "    # queda la primera etiqueta. Por eso una sola etiqueta por ejecutable descubierto.")

# ---- 3. Makefile ------------------------------------------------------------------------------------
cambiar(MK, "ctest -LE 'root|perf' --output-on-failure\"", "ctest -LE 'e2e|root|perf' --output-on-failure\"")

# ---- 4. puerta: tambien falla con ejecuciones de 0 tests --------------------------------------------
cambiar(GATE, '# (ctest "***Skipped" / "***Not Run" / "did not run", o gtest "[  SKIPPED ]"). Un saltado no es un pasado.\n',
        '# (ctest "***Skipped" / "***Not Run" / "did not run", o gtest "[  SKIPPED ]"). Un saltado no es un pasado.\n'
        "# " + MARCA + " Y si alguna ejecucion de gtest corre 0 tests: un test que no ejecuta nada no es un pasado.\n")
cambiar(GATE, "NO_RUN=$(grep -c -F 'did not run' \"$LOG\")\n",
        "NO_RUN=$(grep -c -F 'did not run' \"$LOG\")\n"
        "VACIOS=$(grep -c -F '0 tests from 0 test suites ran' \"$LOG\")\n")
cambiar(GATE, " did_not_run=$NO_RUN\"", " did_not_run=$NO_RUN gtest_vacios=$VACIOS\"")
cambiar(GATE, '[ "$NO_RUN" -ne 0 ]; then', '[ "$NO_RUN" -ne 0 ] || [ "$VACIOS" -ne 0 ]; then')

# ---- 5. comentarios de los ficheros nuevos ----------------------------------------------------------
cambiar(FIX, "// (ipset_wrapper_tests, e2e;root) y los de rendimiento (ipset_wrapper_perf_tests, perf;root).\n",
        "// (ipset_wrapper_tests, etiqueta e2e) y los de rendimiento (ipset_wrapper_perf_tests, etiqueta perf);\n"
        "// ambos necesitan root. " + MARCA + "\n")
cambiar(PERF, "// Etiquetas ctest: perf;root.   make test-firewall-perf PROFILE=production\n",
        "// Etiqueta ctest: perf (necesita root).   make test-firewall-perf PROFILE=production   " + MARCA + "\n")

if errores:
    print("PARO: el patcher no toca nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)

print(f"=== {MODO}: todas las anclas encontradas, 0 errores ===")
for p in FICHEROS:
    print("".join(difflib.unified_diff(orig[p].splitlines(True), nuevo[p].splitlines(True),
                                       fromfile=f"a/{p}", tofile=f"b/{p}", n=1)))
if MODO == "--apply":
    for p in FICHEROS:
        if nuevo[p] != orig[p]:
            p.write_text(nuevo[p], encoding="utf-8")
    print("APLICADO", MARCA)
