#!/usr/bin/env python3
"""[TIMEBASE-D295:CMAKE-TEST] Registra test_timebase en sniffer/CMakeLists.txt (tras test_ddos_victim_board).
Atomico: el ancla debe aparecer exactamente una vez. Uso: --check | --apply"""
import os
import sys
from pathlib import Path

P = Path("sniffer/CMakeLists.txt")
MARCA = "[TIMEBASE-D295:CMAKE-TEST]"
ANCLA = ('  message(STATUS "Unit Test: test_ddos_victim_board configured (DAY 279 - tablero de ventanas '
         'por victima) [DDOS-VWIN-D279:CMAKE-TEST]")\n')
BLOQUE = """
  add_executable(test_timebase
          tests/test_timebase.cpp
  )
  target_include_directories(test_timebase PRIVATE
          ${CMAKE_SOURCE_DIR}/include
  )
  add_test(NAME test_timebase COMMAND test_timebase)
  message(STATUS "Unit Test: test_timebase configured (DAY 295 - contrato temporal v1) [TIMEBASE-D295:CMAKE-TEST]")
"""


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(2)
    t = P.read_text(encoding="utf-8")
    if MARCA in t:
        print("YA APLICADO")
        sys.exit(0)
    if "test_timebase" in t:
        print("ABORTA: test_timebase ya existe sin la marca")
        sys.exit(1)
    n = t.count(ANCLA)
    if n != 1:
        print(f"ABORTA: ancla encontrada {n} veces (debe ser 1)")
        sys.exit(1)
    nuevo = t.replace(ANCLA, ANCLA + BLOQUE, 1)
    if sys.argv[1] == "--check":
        print("CHECK OK: ancla 1; se registraria test_timebase")
        return
    tmp = P.with_suffix(".txt.tmp")
    tmp.write_text(nuevo, encoding="utf-8")
    os.replace(tmp, P)
    print(f"APLICADO: {P}")


if __name__ == "__main__":
    main()
