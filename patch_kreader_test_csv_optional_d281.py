#!/usr/bin/env python3
"""DAY281: alinea test_ddos_kernel_reader con [DDOS-VWIN-D279:CSV-OPTIONAL] (e2cac4b0).
Ruta CSV vacia => start() ARRANCA sin CSV (antes el test esperaba que fallara).
Idempotente. --check solo informa. No commitea."""
import sys, pathlib

F = pathlib.Path("sniffer/tests/test_ddos_kernel_reader.cpp")
OLD = '''    {
        DdosKernelReader r(-1, 65536, 100, "");
        CHECK(!r.start());  // sin ruta: no arranca
    }
'''
NEW = '''    {
        // [DDOS-VWIN-D279:CSV-OPTIONAL] (e2cac4b0): sin ruta arranca SIN CSV;
        // el CSV es salida de laboratorio, no condicion de la senal.
        DdosKernelReader r(-1, 65536, 100, "");
        CHECK(r.start());
        r.stop();  // para limpio sin fichero abierto
    }
'''
MARK = "CSV-OPTIONAL] (e2cac4b0)"

src = F.read_text()
if MARK in src:
    print(f"[OK] ya parcheado: {F}")
    sys.exit(0)
n = src.count(OLD)
if n != 1:
    print(f"[ABORT] bloque original encontrado {n} veces (esperado 1); no toco nada")
    sys.exit(2)
if "--check" in sys.argv:
    print(f"[CHECK] se aplicaria el cambio en {F}")
    sys.exit(0)
F.write_text(src.replace(OLD, NEW))
print(f"[APPLIED] {F}")
