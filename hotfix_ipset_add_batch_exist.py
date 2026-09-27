#!/usr/bin/env python3
"""hotfix_ipset_add_batch_exist.py -- anade el flag -exist a `ipset restore`
en IPSetWrapper::add_batch() (firewall-acl-agent/src/core/ipset_wrapper.cpp).

Bug real, PREEXISTENTE (no introducido por el patch de recidivism-D276),
expuesto por el test de aceptacion test_recidivism_e2e:

    ipset v7.17: Error in line 1: Element cannot be added to the set:
    it's already added

add_batch() construye un fichero para `ipset restore` con lineas
"add <set> <ip> timeout N comment ..." pero lo ejecuta SIN el flag
-exist. Sin ese flag, `ipset restore` rechaza cualquier `add` sobre una
IP que ya es miembro del set en vez de actualizar su timeout/comentario
-- exactamente lo que necesita la escalada de castigo por reincidencia
(y, mas en general, cualquier re-insercion de una IP ya bloqueada antes
de que expire su timeout previo). delete_batch(), en el mismo fichero,
ya usa -exist correctamente; este hotfix iguala add_batch() a ese mismo
patron.

Dos sitios en add_batch(): la ejecucion real y el mensaje de [DRY-RUN]
(para que el log de dry-run no mienta sobre el comando que se lanzaria).

Uso (desde la raiz del repo):
  python3 hotfix_ipset_add_batch_exist.py --check
  python3 hotfix_ipset_add_batch_exist.py --dry
  python3 hotfix_ipset_add_batch_exist.py --apply
"""
import argparse
import difflib
import sys
from pathlib import Path

REL = "firewall-acl-agent/src/core/ipset_wrapper.cpp"

PATCHES = [
    (
        "dry_run_message",
        '        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin\n'
        '                  << " restore < " << tmpfile << std::endl;\n'
        '        return IPSetResult<void>();\n'
        '    }\n'
        '    int ret = safe_exec_with_file_in({kIpsetBin, "restore"}, tmpfile);',
        "HOTFIX-IPSET-ADD-EXIST-001",
        '        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin\n'
        '                  << " restore -exist < " << tmpfile << std::endl;\n'
        '        return IPSetResult<void>();\n'
        '    }\n'
        '    // HOTFIX-IPSET-ADD-EXIST-001: sin -exist, ipset restore rechaza\n'
        '    // el add de una IP que ya es miembro del set (p.ej. reincidencia:\n'
        '    // la misma IP vuelve a aparecer antes de que expire su timeout\n'
        '    // previo). Con -exist, el add sobre un elemento existente\n'
        '    // ACTUALIZA su timeout/comment en vez de fallar. delete_batch()\n'
        '    // ya usaba -exist; add_batch() se equipara aqui.\n'
        '    int ret = safe_exec_with_file_in({kIpsetBin, "restore", "-exist"}, tmpfile);',
    ),
]

ALREADY_APPLIED_NEEDLE = "HOTFIX-IPSET-ADD-EXIST-001"


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
        print("%s: ya aplicado (marcador %s presente)" % (REL, ALREADY_APPLIED_NEEDLE))
        return 0

    ok = True
    patched = text
    for name, anchor, _marker, replacement in PATCHES:
        count = patched.count(anchor)
        status = "OK" if count == 1 else ("FALTA" if count == 0 else "AMBIGUO(%d)" % count)
        if args.check:
            print("%-40s [%s] ancla '%s'" % (REL, status, name))
        if count != 1:
            ok = False
            continue
        patched = patched.replace(anchor, replacement, 1)

    if args.check:
        return 0 if ok else 1

    if not ok:
        print("ERROR: alguna ancla no encontrada exactamente una vez -- aborto", file=sys.stderr)
        return 1

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
        backup = path.with_suffix(path.suffix + ".orig")
        if not backup.exists():
            backup.write_text(text, encoding="utf-8")
            print("backup: %s" % backup)
        path.write_text(patched, encoding="utf-8")
        print("aplicado: %s" % REL)
        return 0


if __name__ == "__main__":
    sys.exit(main())