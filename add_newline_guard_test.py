#!/usr/bin/env python3
"""
add_newline_guard_test.py — DAY 186
Inserta los 3 bloques del test DEBT-BRONZE-EMBEDDED-NEWLINE-001 dentro de
test_P2_confinement(), justo ANTES del printf de cierre (guard col 17 D-D).

ANCLA sobre string literal único. Si el ancla no aparece EXACTAMENTE una vez,
ABORTA sin escribir (nunca adivina, nunca duplica). Idempotente: si el marcador
del bloque nuevo ya está presente, no re-inserta.

Uso:
    python3 add_newline_guard_test.py            # dry-run (default, no escribe)
    python3 add_newline_guard_test.py --write     # escribe (con backup)
"""

import argparse
import shutil
import sys
from pathlib import Path

REL_PATH = "libs/correlation-v1/tests/test_correlation_v1.cpp"

# Ancla: línea 130 del fichero, única. Insertamos ANTES de ella.
ANCHOR = '    std::printf("  (guard col 17 -> commit de contrato D-D, no este refactor)\\n");'

# Marcador de idempotencia: si este string ya está, el bloque ya se insertó.
IDEMPOTENCY_MARKER = "DEBT-BRONZE-EMBEDDED-NEWLINE-001"

BLOCK = r'''
    // ── DEBT-BRONZE-EMBEDDED-NEWLINE-001 (Camino A, fail-closed) ─────────────
    // \n/\r embebido en campo de texto rompe el reader getline (main.cpp parte
    // la línea física ANTES de que split_csv vea las comillas) -> fila fragmentada
    // -> ambas mitades fallan HMAC -> pérdida silenciosa disfrazada de "corrupto".
    // validate RECHAZA en origen; serialize NO emite. Origen MEDIDO: imposible en
    // ml-detector (veredictos de conjunto cerrado, zmq_handler.cpp:437,547+); el
    // guard protege a los productores de texto libre (Suricata/Wazuh/Zeek/Andres).
    {
        auto row = make_valid_row();
        row.final_classification = "LINEA1\nLINEA2";          // \n embebido (rincon_04)
        CHECK(!validate(row),
              "\\n embebido en final_classification -> validate RECHAZA");
        CHECK(!serialize(row, kTestKey),
              "\\n embebido en final_classification -> serialize NO emite");
    }
    {
        auto row = make_valid_row();
        row.event_id = "evt\rCR";                             // \r embebido (linea 116)
        CHECK(!validate(row),
              "\\r embebido en event_id -> validate RECHAZA");
        CHECK(!serialize(row, kTestKey),
              "\\r embebido en event_id -> serialize NO emite");
    }
    {
        // \t NO se rechaza: no rompe getline ni split_csv. Regresion contra el
        // sobre-celo: fija que la frontera del guard es newline-class, no control-char.
        auto row = make_valid_row();
        row.threat_category = "A\tB";                         // \t embebido
        CHECK(validate(row),
              "\\t embebido en threat_category -> validate ACEPTA (no rompe el reader)");
        CHECK(serialize(row, kTestKey),
              "\\t embebido en threat_category -> serialize SI emite");
    }

'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="raíz del repo (default: cwd)")
    ap.add_argument("--write", action="store_true",
                    help="escribe el cambio (sin esto: dry-run)")
    args = ap.parse_args()

    path = Path(args.root) / REL_PATH
    if not path.is_file():
        sys.exit(f"ABORTA: no existe {path}")

    text = path.read_text(encoding="utf-8")

    # Idempotencia: si el bloque ya está, no tocar.
    if IDEMPOTENCY_MARKER in text:
        print(f"YA PRESENTE: '{IDEMPOTENCY_MARKER}' encontrado en el fichero.")
        print("No se inserta nada (idempotente). Nada que hacer.")
        return

    # Ancla única: ni ausente ni duplicada.
    n = text.count(ANCHOR)
    if n == 0:
        sys.exit("ABORTA: ancla NO encontrada. El fichero no es el esperado "
                 "(¿cambió la línea 130?). No se escribe nada.")
    if n > 1:
        sys.exit(f"ABORTA: ancla aparece {n} veces (esperaba 1). Ambiguo. "
                 "No se escribe nada.")

    new_text = text.replace(ANCHOR, BLOCK.lstrip("\n") + ANCHOR, 1)

    # Verificación post-sustitución: el marcador debe aparecer exactamente una vez.
    if new_text.count(IDEMPOTENCY_MARKER) != 1:
        sys.exit("ABORTA: verificación post-inserción falló (marcador no único).")

    if not args.write:
        print("=== DRY-RUN (no se escribe; usa --write para aplicar) ===")
        print(f"Fichero:  {path}")
        print(f"Ancla:    encontrada 1 vez (OK)")
        print(f"Insertar: 3 bloques ({BLOCK.count('{')} CHECK-pairs) ANTES del printf de cierre de P2")
        print(f"Backup:   se crearía {path}.bak")
        print("\n--- bloque a insertar ---")
        print(BLOCK)
        return

    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    path.write_text(new_text, encoding="utf-8")
    print(f"✅ Escrito.  Backup en {backup}")
    print(f"✅ Marcador '{IDEMPOTENCY_MARKER}' presente 1 vez (verificado).")
    print("Siguiente: make correlation-v1-clean && make correlation-v1-test")

if __name__ == "__main__":
    main()