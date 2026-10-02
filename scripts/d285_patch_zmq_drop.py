#!/usr/bin/env python3
"""d285_patch_zmq_drop.py — DAY285, punto 2: [ZMQ-DROP] periodico en el sniffer.

Quita el [ERROR] por mensaje descartado y emite un resumen cada 10 s, siempre
visible (sin verbose), solo si hubo descartes.
Uso (raiz del repo): python3 d285_patch_zmq_drop.py --check | --apply
Atomico, idempotente, no commitea.
"""
import sys
import pathlib

M = "[ZMQ-DROP-D285]"
RC = "sniffer/src/userspace/ring_consumer.cpp"

EDITS = []

EDITS.append((RC, "resumen periodico en zmq_sender_loop",
    '    std::cout << "[INFO] ZMQ sender thread started" << std::endl;\n'
    '    while (!should_stop_) {\n'
    '        std::vector<uint8_t> data;\n',
    '    std::cout << "[INFO] ZMQ sender thread started" << std::endl;\n'
    '    // ' + M + ' resumen periodico de descartes, siempre visible (sin verbose)\n'
    '    constexpr auto kDropReportInterval = std::chrono::seconds(10);\n'
    '    auto drop_last_report = std::chrono::steady_clock::now();\n'
    '    uint64_t drop_last_total = stats_.zmq_send_failures.load();\n'
    '    while (!should_stop_) {\n'
    '        {  // ' + M + '\n'
    '            const auto now = std::chrono::steady_clock::now();\n'
    '            if (now - drop_last_report >= kDropReportInterval) {\n'
    '                const uint64_t total = stats_.zmq_send_failures.load();\n'
    '                if (total > drop_last_total) {\n'
    '                    std::cerr << "[ZMQ-DROP] descartados=" << (total - drop_last_total)\n'
    '                              << " en los últimos "\n'
    '                              << std::chrono::duration_cast<std::chrono::seconds>(now - drop_last_report).count()\n'
    '                              << " s (total=" << total << ")" << std::endl;\n'
    '                }\n'
    '                drop_last_total = total;\n'
    '                drop_last_report = now;\n'
    '            }\n'
    '        }\n'
    '        std::vector<uint8_t> data;\n'))

EDITS.append((RC, "sin [ERROR] por mensaje",
    '            std::cerr << "[ERROR] ZMQ send falló!" << std::endl;\n'
    '            stats_.zmq_send_failures++;\n',
    '            // ' + M + ' sin log por mensaje: lo resume zmq_sender_loop cada 10 s\n'
    '            stats_.zmq_send_failures++;\n'))


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        return 2
    apply = sys.argv[1] == "--apply"
    texts = {}
    for f, _, _, _ in EDITS:
        if f not in texts:
            p = pathlib.Path(f)
            if not p.is_file():
                print(f"[ABORT] no existe {f} (¿estas en la raiz del repo?)")
                return 1
            texts[f] = p.read_text(encoding="utf-8")
    orig = dict(texts)
    errores = 0
    pendientes = 0
    for f, name, old, new in EDITS:
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
    if errores:
        print(f"[ABORT] {errores} ancla(s) no casan; no se escribe nada")
        return 1
    if not apply:
        print(f"[CHECK] {pendientes} edicion(es) pendiente(s) de {len(EDITS)}")
        return 0
    for f, t in texts.items():
        if t != orig[f]:
            pathlib.Path(f).write_text(t, encoding="utf-8")
            print(f"[ESCRITO]   {f}")
    for f, name, _, new in EDITS:
        if new not in pathlib.Path(f).read_text(encoding="utf-8"):
            print(f"[FALLO]     {f}: {name} no quedo aplicado")
            return 1
    print(f"[OK] {len(EDITS)}/{len(EDITS)} ediciones presentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
