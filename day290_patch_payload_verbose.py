#!/usr/bin/env python3
"""DAY290 [PAYLOAD-VERBOSE-D290] El analisis de carga del hilo del anillo solo se calcula con
verbosidad BASIC o superior: su resultado solo lo consume el log que hay dentro del bloque.
Uso: python3 day290_patch_payload_verbose.py --check | --apply
Idempotente (marca en el codigo) y todo-o-nada: si el texto esperado no aparece exactamente
una vez, no toca nada."""
import pathlib
import sys

F = pathlib.Path("/vagrant/sniffer/src/userspace/ring_consumer.cpp")
MARK = "[PAYLOAD-VERBOSE-D290]"
OLD = ("    if (event.payload_len > 0) {\n"
       "        auto payload_features = payload_analyzer_.analyze(event.payload, event.payload_len);\n")
NEW = ("    // " + MARK + " solo con verbosidad BASIC+: el resultado solo lo consume el log de abajo\n"
       "    if (event.payload_len > 0 && g_verbosity >= FeatureLogger::VerbosityLevel::BASIC) {\n"
       "        auto payload_features = payload_analyzer_.analyze(event.payload, event.payload_len);\n")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        return 2
    if not F.is_file():
        print(f"ABORTO: no existe {F}")
        return 1
    src = F.read_text()
    if MARK in src:
        print("YA APLICADO: no se toca nada")
        return 0
    n = src.count(OLD)
    if n != 1:
        print(f"ABORTO: el texto esperado aparece {n} veces (debe ser 1); no se toca nada")
        return 1
    if sys.argv[1] == "--check":
        print("OK: aplicable (1 coincidencia)")
        return 0
    F.write_text(src.replace(OLD, NEW, 1))
    if F.read_text().count(MARK) != 1:
        print("ERROR: tras escribir, la marca no aparece exactamente una vez; revisa el fichero")
        return 1
    print("APLICADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
