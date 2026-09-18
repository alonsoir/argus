#!/usr/bin/env python3
"""
patch_log_all_features.py  —  DAY272, paso 1 de la grieta B.

Extiende la línea de log "DDoS Features:" de zmq_handler.cpp para que imprima
las 9 features del vector, no 4. Hoy loguea syn_ack[0], entropy[4], amp[5],
disp[2]; le añade symmetry[1], protocol[3], completion[6], escalation[7],
saturation[8]. Objetivo: ver cuáles VARÍAN bajo flood y confirmar que el
discriminador del 21/79 es packet_size_entropy (sospecha: las de ventana
—escalation/saturation— clavadas como disp).

Estilo hermano de patch_force_all_heads.py:
  - idempotente  : re-ejecutar no hace nada (detecta ya-parcheado).
  - atómico      : escribe a temp y os.replace; si algo no casa, no toca nada.
  - --dry        : enseña el diff, no escribe.
  - --apply      : escribe. Verifica que compila (make ml-detector); si NO
                   compila, revierte. Salvo con --no-build.
  - --check      : solo dice si está parcheado (exit 0) o no (exit 1).
  - NO commitea.

Los 4 tokens actuales (syn_ack=, entropy=, amp=, disp=) se conservan tal cual
—vocabulario y greps previos siguen valiendo—; los 5 nuevos se APPENDEAN.
'saturation=' (no 'resource=') a propósito, para no colisionar con el
'resource=' de la línea de log de ransomware al grepear.
"""

import argparse
import os
import subprocess
import sys
import tempfile

TARGET = "ml-detector/src/zmq_handler.cpp"

# Anclas: subcadenas distintivas, no líneas enteras → inmunes a la sangría.
# Cada una debe aparecer EXACTAMENTE una vez en el fichero.
OLD_FMT = "DDoS Features: syn_ack={:.3f}, entropy={:.3f}, amp={:.3f}, disp={:.3f}"
ADD_FMT = ", symmetry={:.3f}, protocol={:.3f}, completion={:.3f}, escalation={:.3f}, saturation={:.3f}"

OLD_ARGS = "ddos_features_vec[0], ddos_features_vec[4], ddos_features_vec[5], ddos_features_vec[2]"
ADD_ARGS = ", ddos_features_vec[1], ddos_features_vec[3], ddos_features_vec[6], ddos_features_vec[7], ddos_features_vec[8]"

NEW_FMT = OLD_FMT + ADD_FMT
NEW_ARGS = OLD_ARGS + ADD_ARGS


def die(msg, code=2):
    print(f"[ABORT] {msg}", file=sys.stderr)
    sys.exit(code)


def read_target():
    if not os.path.isfile(TARGET):
        die(f"no encuentro {TARGET} — ¿ejecutas desde la raíz del repo?")
    with open(TARGET, "r", encoding="utf-8") as fh:
        return fh.read()


def is_patched(src):
    return (NEW_FMT in src) and (NEW_ARGS in src)


def apply_in_memory(src):
    """Devuelve (nuevo_src). Aborta si las anclas no casan 1:1."""
    for label, needle in (("format string", OLD_FMT), ("args", OLD_ARGS)):
        n = src.count(needle)
        if n == 0:
            die(f"ancla '{label}' no encontrada — el fichero no está en el "
                f"estado esperado (¿ya editado a mano, u otra rama?)")
        if n > 1:
            die(f"ancla '{label}' aparece {n} veces — no es única, no toco nada")
    src = src.replace(OLD_FMT, NEW_FMT, 1)
    src = src.replace(OLD_ARGS, NEW_ARGS, 1)
    return src


def atomic_write(new_src):
    d = os.path.dirname(os.path.abspath(TARGET))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new_src)
        os.replace(tmp, TARGET)  # atómico en el mismo FS
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def build_ok():
    print("[*] make ml-detector (el compilador es el árbitro)...")
    r = subprocess.run(["make", "ml-detector"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true", help="muestra qué haría, no escribe")
    g.add_argument("--apply", action="store_true", help="escribe y verifica que compila")
    g.add_argument("--check", action="store_true", help="exit 0 si parcheado, 1 si no")
    ap.add_argument("--no-build", action="store_true",
                    help="con --apply, no correr make (verifícalo tú)")
    args = ap.parse_args()

    src = read_target()

    if args.check:
        if is_patched(src):
            print("[check] PARCHEADO"); sys.exit(0)
        print("[check] SIN PARCHEAR"); sys.exit(1)

    if is_patched(src):
        print("[=] ya parcheado, nada que hacer (idempotente)")
        sys.exit(0)

    new_src = apply_in_memory(src)

    if args.dry:
        print("[dry] format:")
        print(f"    - {OLD_FMT}")
        print(f"    + {NEW_FMT}")
        print("[dry] args:")
        print(f"    - {OLD_ARGS}")
        print(f"    + {NEW_ARGS}")
        print("[dry] no se ha escrito nada.")
        sys.exit(0)

    # --apply
    backup = src
    atomic_write(new_src)
    print(f"[+] {TARGET} parcheado (9 features en el log de DDoS).")

    if args.no_build:
        print("[!] --no-build: recuerda `make ml-detector` a mano.")
        sys.exit(0)

    if build_ok():
        print("[✓] compila. Listo para truncar log + re-replay del flood.")
        sys.exit(0)
    else:
        atomic_write(backup)
        die("no compila → REVERTIDO. El fichero queda como estaba.", code=3)


if __name__ == "__main__":
    main()