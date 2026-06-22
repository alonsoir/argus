#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# audit_config_boundaries.py  —  triage heurístico (NO auditoría)
#
# Busca "fronteras generador→lenguaje": sitios donde un dato (a menudo derivado
# de config/tráfico) se concatena hacia un lenguaje que otro proceso parsea:
#   - shell           (CWE-78/88):  system() / popen() / execlp() / execvp()
#   - mini-config      (CWE-93):    líneas 'add/create/flush/-A/-I/comment ...'
#                                   construidas por concatenación hacia ipset/
#                                   iptables/nft/restore...
#   - query           (CWE-89):     MATCH/MERGE/SELECT/WHERE concatenados (vs
#                                   prepared statements / parámetros $)
#
# Reconoce fronteras YA defendidas (is_valid_* / validate_* / safe_exec /
# prepare()) en la ventana cercana y las degrada a LOW para no ahogarte en ruido.
#
# ── HONESTIDAD SOBRE LÍMITES ────────────────────────────────────────────────
# Esto es grep con contexto, no análisis de flujo. NO sigue taint entre
# funciones ni ficheros, NO entiende el AST, y se equivocará en ambos sentidos:
# marcará cosas seguras (falsos positivos) y se le escaparán cadenas indirectas
# (falsos negativos). Úsalo como PRIMER PASE para decidir dónde mirar de verdad
# con semgrep acotado por fichero (DEBT-AUDIT-VBOXSF-IO-001). Un HIGH no es un
# bug confirmado; un 0-HIGH no es "limpio". Es un mapa de dónde concentrar ojos.
# ─────────────────────────────────────────────────────────────────────────────
#
# Uso (desde la raíz del repo):
#   python3 tools/audit_config_boundaries.py
#   python3 tools/audit_config_boundaries.py --root . --verbose
# Exit code: 1 si hay algún HIGH, 0 en caso contrario (informativo, no bloqueante).

import argparse
import os
import re
import sys

EXTS = (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h", ".hxx")
SKIP_DIRS = {".git", "build", "build-debug", "build-release", "cmake-build-debug",
             "third_party", "vendor", "node_modules", "_deps", ".cache"}

WINDOW_UP, WINDOW_DOWN = 6, 2  # líneas de contexto para buscar guard/taint

# ── sinks ────────────────────────────────────────────────────────────────────
# Shell PATH-searching o con shell. execv/execve con ruta absoluta es el patrón
# SEGURO (safe_exec) y a propósito NO se marca aquí.
RE_SHELL = re.compile(r'\b(system|popen|execlp|execvp|execvpe)\s*\(|["\']/bin/sh["\']')
# mini-lenguaje de config: literal con verbo de comando + concatenación/stream
RE_CONFIG = re.compile(
    r'"(?:\s*(?:add|create|del|delete|flush|destroy|swap|rename)\s|-A |-I |-D | comment )'
    r'.*?"\s*(?:<<|\+|,)|(?:<<|\+)\s*"(?:\s*(?:add|create|flush|destroy)\s|-A |-I )')
# query string interpolada (sin parámetro $)
RE_QUERY = re.compile(r'"(?:[^"]*\b(?:MATCH|MERGE|CREATE|SELECT|INSERT|DELETE|WHERE|SET)\b[^"]*)"'
                      r'\s*(?:\+|<<)')

# ── señales ──────────────────────────────────────────────────────────────────
RE_GUARD = re.compile(r'\b(is_valid_\w+|validate_\w+|\w+_validator|safe_exec\w*|prepare)\s*\(|nosemgrep')
RE_TAINT = re.compile(r'\b(config|json|getenv|recv|payload|comment|argv|request|user_input|'
                      r'whitelist|cidr|set_name|hostname|domain)\b|\.at\(|\["|->at\(')
RE_PARAMQUERY = re.compile(r'\$\w+|bind\s*\(|->bind|prepared|PreparedStatement')
RE_COMMENT_ONLY = re.compile(r'^\s*(//|\*|/\*)')

SEV = {"HIGH": 3, "MED": 2, "LOW": 1, "INFO": 0}


def is_test(path):
    p = path.replace("\\", "/")
    return "/test" in p or "/tests/" in p or os.path.basename(p).startswith("test_")


def scan_file(path):
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return []
    findings = []
    test = is_test(path)
    for i, ln in enumerate(lines):
        if RE_COMMENT_ONLY.match(ln):
            continue  # comentario puro: no es código vivo (evita el nosemgrep interino)
        kind = None
        if RE_SHELL.search(ln):
            kind = ("shell", "CWE-78/88")
        elif RE_CONFIG.search(ln):
            kind = ("config", "CWE-93")
        elif RE_QUERY.search(ln) and not RE_PARAMQUERY.search(ln):
            kind = ("query", "CWE-89")
        if not kind:
            continue
        lo, hi = max(0, i - WINDOW_UP), min(len(lines), i + WINDOW_DOWN + 1)
        window = "\n".join(lines[lo:hi])
        guarded = bool(RE_GUARD.search(window))
        tainted = bool(RE_TAINT.search(window))
        # severidad
        if guarded:
            sev = "LOW"          # frontera ya parece defendida cerca
        elif tainted:
            sev = "HIGH"         # sink + fuente sospechosa + sin guard visible
        else:
            sev = "MED"          # sink sin guard, fuente no evidente
        if test and SEV[sev] > SEV["LOW"]:
            sev = "INFO"         # en tests, payloads de ataque suelen ser intencionados
        findings.append({
            "path": path, "line": i + 1, "kind": kind[0], "cwe": kind[1],
            "sev": sev, "guarded": guarded, "tainted": tainted,
            "code": ln.strip()[:140], "test": test,
        })
    return findings


def walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in fns:
            if fn.endswith(EXTS):
                yield os.path.join(dp, fn)


def main():
    ap = argparse.ArgumentParser(description="Triage heurístico de fronteras generador→lenguaje")
    ap.add_argument("--root", default=".")
    ap.add_argument("--verbose", action="store_true", help="muestra también LOW e INFO")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    all_f = []
    for fp in walk(root):
        all_f.extend(scan_file(fp))
    all_f.sort(key=lambda f: (-SEV[f["sev"]], f["path"], f["line"]))

    counts = {k: 0 for k in SEV}
    for f in all_f:
        counts[f["sev"]] += 1

    print("=" * 78)
    print(" TRIAGE HEURÍSTICO — fronteras generador→lenguaje (NO es una auditoría)")
    print(" grep con contexto: ni taint inter-función ni AST. Confirma con semgrep.")
    print("=" * 78)
    print(f" raíz: {root}")
    print(f" HIGH={counts['HIGH']}  MED={counts['MED']}  LOW={counts['LOW']}  "
          f"INFO={counts['INFO']}  (LOW=frontera ya defendida cerca · "
          f"INFO=en tests)\n")

    shown = 0
    for f in all_f:
        if not args.verbose and f["sev"] in ("LOW", "INFO"):
            continue
        rel = os.path.relpath(f["path"], root)
        tags = []
        if f["guarded"]:
            tags.append("guard-cerca")
        if f["tainted"]:
            tags.append("fuente-sospechosa")
        if f["test"]:
            tags.append("test")
        tag = (" [" + ", ".join(tags) + "]") if tags else ""
        print(f"  {f['sev']:<4} {f['cwe']:<10} {rel}:{f['line']}  ({f['kind']}){tag}")
        print(f"       {f['code']}")
        shown += 1

    if not args.verbose and (counts["LOW"] or counts["INFO"]):
        print(f"\n  (+{counts['LOW']} LOW y {counts['INFO']} INFO ocultos — usa --verbose)")
    if shown == 0 and not args.verbose:
        print("  (sin HIGH ni MED — repasa LOW/INFO con --verbose antes de cantar victoria)")

    print("\n" + "-" * 78)
    print(" SIGUIENTE PASO para cada HIGH/MED: semgrep acotado al fichero")
    print("   semgrep --config p/cwe-top-25 --error <fichero>   # evita el stall vboxsf")
    print(" Recuerda: la defensa vive en TU frontera C++ (is_valid_*), nunca")
    print(" delegada en la herramienta de abajo, cuyo parser varía entre versiones.")
    print("-" * 78)

    sys.exit(1 if counts["HIGH"] else 0)


if __name__ == "__main__":
    main()