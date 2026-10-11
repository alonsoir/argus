#!/usr/bin/env python3
"""d285_patch_log_verbose.py — DAY285, punto 3a: logs por evento del ml-detector tras --verbose.

[DUAL-SCORE], [VICTIM-WINDOW], [HEAD-SCORES] y las lineas de deteccion por evento
pasan a debug (--verbose). Los resumenes periodicos van en el patcher 3b.
Uso (raiz del repo): python3 d285_patch_log_verbose.py --check | --apply
Atomico, idempotente, no commitea.
"""
import sys
import pathlib

M = "[LOG-VERBOSE-D285]"
ZH = "ml-detector/src/zmq_handler.cpp"

# Ediciones de bloque: (fichero, nombre, old, new)
BLOCKS = [
    (ZH, "HEAD-SCORES sin coste fuera de verbose",
     "        {\n"
     "            auto hs_fmt = [](int c, double p) -> std::string {\n",
     "        if (logger_->should_log(spdlog::level::debug)) {  // " + M + " sin coste si no hay verbose\n"
     "            auto hs_fmt = [](int c, double p) -> std::string {\n"),
]

# Ediciones de linea: (fichero, nombre, clave unica en la linea, de, a)
LINES = [
    (ZH, "DUAL-SCORE a debug", '"[DUAL-SCORE] event=', "logger_->info(", "logger_->debug("),
    (ZH, "VICTIM-WINDOW a debug", '"[VICTIM-WINDOW] event={}, victim=', "logger_->info(", "logger_->debug("),
    (ZH, "VICTIM-WINDOW absent a debug", '"[VICTIM-WINDOW] event={}, absent"', "logger_->info(", "logger_->debug("),
    (ZH, "HEAD-SCORES a debug", '"[HEAD-SCORES] event=', "logger_->info(", "logger_->debug("),
    (ZH, "Score divergence a debug", "Score divergence: fast=", "logger_->warn(", "logger_->debug("),
    (ZH, "DDoS ATTACK a debug", "DDoS ATTACK: event=", "logger_->warn(", "logger_->debug("),
    (ZH, "RANSOMWARE ATTACK a debug", "RANSOMWARE ATTACK: event=", "logger_->warn(", "logger_->debug("),
    (ZH, "SUSPICIOUS INTERNAL a debug", "SUSPICIOUS INTERNAL ACTIVITY: event=", "logger_->warn(", "logger_->debug("),
    (ZH, "ATTACK L1 a debug", "ATTACK: event={}, L1_conf=", "logger_->info(", "logger_->debug("),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        return 2
    apply = sys.argv[1] == "--apply"
    files = sorted({e[0] for e in BLOCKS} | {e[0] for e in LINES})
    texts = {}
    for f in files:
        p = pathlib.Path(f)
        if not p.is_file():
            print(f"[ABORT] no existe {f} (¿estas en la raiz del repo?)")
            return 1
        texts[f] = p.read_text(encoding="utf-8")
    orig = dict(texts)
    errores = 0
    pendientes = 0

    for f, name, old, new in BLOCKS:
        t = texts[f]
        if new in t:
            print(f"[YA]        {f}: {name}")
            continue
        n = t.count(old)
        if n != 1:
            print(f"[ERROR]     {f}: {name} -> ancla encontrada {n} veces (se esperaba 1)")
            errores += 1
            continue
        texts[f] = t.replace(old, new, 1)
        pendientes += 1
        print(f"[PENDIENTE] {f}: {name}")

    for f, name, key, frm, to in LINES:
        lines = texts[f].splitlines(keepends=True)
        idx = [i for i, l in enumerate(lines) if key in l]
        if len(idx) != 1:
            print(f"[ERROR]     {f}: {name} -> clave encontrada en {len(idx)} lineas (se esperaba 1)")
            errores += 1
            continue
        i = idx[0]
        l = lines[i]
        if frm in l:
            if l.count(frm) != 1:
                print(f"[ERROR]     {f}: {name} -> '{frm}' aparece {l.count(frm)} veces en la linea")
                errores += 1
                continue
            lines[i] = l.replace(frm, to, 1).rstrip("\n") + "  // " + M + "\n"
            texts[f] = "".join(lines)
            pendientes += 1
            print(f"[PENDIENTE] {f}: {name} (L{i + 1})")
        elif to in l:
            print(f"[YA]        {f}: {name} (L{i + 1})")
        else:
            print(f"[ERROR]     {f}: {name} -> la linea L{i + 1} no tiene ni '{frm}' ni '{to}'")
            errores += 1

    total = len(BLOCKS) + len(LINES)
    if errores:
        print(f"[ABORT] {errores} ancla(s) no casan; no se escribe nada")
        return 1
    if not apply:
        print(f"[CHECK] {pendientes} edicion(es) pendiente(s) de {total}")
        return 0
    for f, t in texts.items():
        if t != orig[f]:
            pathlib.Path(f).write_text(t, encoding="utf-8")
            print(f"[ESCRITO]   {f}")
    final = pathlib.Path(ZH).read_text(encoding="utf-8")
    for f, name, _, new in BLOCKS:
        if new not in final:
            print(f"[FALLO]     {f}: {name} no quedo aplicado")
            return 1
    for f, name, key, frm, to in LINES:
        l = [x for x in final.splitlines() if key in x][0]
        if to not in l:
            print(f"[FALLO]     {f}: {name} no quedo aplicado")
            return 1
    print(f"[OK] {total}/{total} ediciones presentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
