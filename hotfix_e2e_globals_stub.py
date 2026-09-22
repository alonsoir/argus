#!/usr/bin/env python3
"""hotfix_e2e_globals_stub.py -- anade tests/test_globals_stub.cpp como fuente
de test_recidivism_e2e en firewall-acl-agent/CMakeLists.txt.

Motivo (visto en el log de `make firewall-build`): el linker de
test_recidivism_e2e falla con "referencia a
mldefender::firewall::observability::g_logger sin definir" (y lo mismo para
diagnostics::g_system_state). firewall_tests SI enlaza porque incluye
tests/test_globals_stub.cpp en sus fuentes -- ese fichero es el que da esos
globals a un binario de test que no pasa por main(). test_recidivism_e2e
llama a BatchProcessor de verdad (a diferencia de test_ipset_injection_integration
o test_autonomy_e2e, que no tocan ese codigo), asi que el linker tira del
.o de batch_processor.cpp y necesita esos simbolos.

No reutiliza patch_recidivism_batch_processor.py porque ese script salta el
fichero entero si ya contiene el marcador RECIDIVISM-D276 (que CMakeLists.txt
ya tiene tras el --apply anterior) -- este hotfix es independiente, con su
propia ancla exacta e idempotencia propia.

Uso (desde la raiz del repo):
  python3 hotfix_e2e_globals_stub.py --check
  python3 hotfix_e2e_globals_stub.py --dry
  python3 hotfix_e2e_globals_stub.py --apply
"""
import argparse
import difflib
import sys
from pathlib import Path

REL = "firewall-acl-agent/CMakeLists.txt"

ANCHOR = """    add_executable(test_recidivism_e2e
        tests/test_recidivism_e2e.cpp
    )"""
REPLACEMENT = """    add_executable(test_recidivism_e2e
        tests/test_recidivism_e2e.cpp
        tests/test_globals_stub.cpp   # ← HOTFIX-E2E-GLOBALS-001: g_logger/g_system_state
    )"""

ALREADY_APPLIED_NEEDLE = "tests/test_globals_stub.cpp   # ← HOTFIX-E2E-GLOBALS-001"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="raiz del repo (default: directorio actual)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--dry", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    path = root / REL
    if not path.exists():
        print("ERROR: no existe %s" % path, file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")

    if ALREADY_APPLIED_NEEDLE in text:
        print("%s: ya aplicado (encontrado %r)" % (REL, ALREADY_APPLIED_NEEDLE))
        return 0

    count = text.count(ANCHOR)
    if args.check:
        status = "OK" if count == 1 else ("FALTA" if count == 0 else "AMBIGUO(%d)" % count)
        print("%-40s [%s] ancla add_executable(test_recidivism_e2e...)" % (REL, status))
        return 0 if count == 1 else 1

    if count != 1:
        print("ERROR: ancla encontrada %d veces (se esperaba 1) -- aborto" % count, file=sys.stderr)
        return 1

    patched = text.replace(ANCHOR, REPLACEMENT, 1)

    if args.dry:
        diff = difflib.unified_diff(
            text.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=REL + " (actual)",
            tofile=REL + " (parcheado)",
        )
        sys.stdout.writelines(diff)
        return 0

    if args.apply:
        backup = path.with_suffix(path.suffix + ".orig2")
        if not backup.exists():
            backup.write_text(text, encoding="utf-8")
            print("backup: %s" % backup)
        path.write_text(patched, encoding="utf-8")
        print("aplicado: %s" % REL)
        return 0


if __name__ == "__main__":
    sys.exit(main())