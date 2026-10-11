#!/usr/bin/env python3
"""d285_patch_summaries.py — DAY285, punto 3b: resumenes periodicos del ml-detector.

[ZMQ-DROP-OUT] (descartes hacia el firewall) y [DETECCIONES] (ddos/ransomware/internal)
cada 10 s en run(), siempre visibles (warn), solo si hay algo que contar. Las lineas por
evento ya estan en debug (patcher 3a).
Uso (raiz del repo): python3 d285_patch_summaries.py --check | --apply
Atomico, idempotente, no commitea.
"""
import sys
import pathlib

M = "[SUMMARY-D285]"
ZH = "ml-detector/src/zmq_handler.cpp"
HH = "ml-detector/include/zmq_handler.hpp"

BLOCKS = [
    (HH, "contadores en Stats",
     "        uint64_t attacks_detected = 0;\n",
     "        uint64_t attacks_detected = 0;\n"
     "        uint64_t send_failures = 0;          // " + M + " descartes hacia el firewall\n"
     "        uint64_t detections_ddos = 0;        // " + M + "\n"
     "        uint64_t detections_ransomware = 0;  // " + M + "\n"
     "        uint64_t detections_internal = 0;    // " + M + "\n"),

    (ZH, "estado del resumen en run()",
     "    auto stats_interval = std::chrono::seconds(config_.monitoring.stats_interval_seconds);\n",
     "    auto stats_interval = std::chrono::seconds(config_.monitoring.stats_interval_seconds);\n"
     "    // " + M + " resumenes siempre visibles cada 10 s (intervalo fijo, independiente de stats_interval)\n"
     "    constexpr auto kSummaryInterval = std::chrono::seconds(10);\n"
     "    auto summary_last = std::chrono::steady_clock::now();\n"
     "    Stats summary_prev = get_stats();\n"
     "    auto summary_delta = [](uint64_t cur, uint64_t prev) -> uint64_t {\n"
     "        return cur >= prev ? cur - prev : cur;  // reset_stats(): sin desbordar\n"
     "    };\n"),

    (ZH, "emision del resumen en run()",
     "                last_stats_report_ = now;\n"
     "            }\n",
     "                last_stats_report_ = now;\n"
     "            }\n"
     "\n"
     "            // " + M + " solo se imprime si hay algo que contar\n"
     "            if (now - summary_last >= kSummaryInterval) {\n"
     "                const auto s = get_stats();\n"
     "                const auto secs = std::chrono::duration_cast<std::chrono::seconds>(now - summary_last).count();\n"
     "                const uint64_t d_drop = summary_delta(s.send_failures, summary_prev.send_failures);\n"
     "                const uint64_t d_ddos = summary_delta(s.detections_ddos, summary_prev.detections_ddos);\n"
     "                const uint64_t d_rw   = summary_delta(s.detections_ransomware, summary_prev.detections_ransomware);\n"
     "                const uint64_t d_int  = summary_delta(s.detections_internal, summary_prev.detections_internal);\n"
     "                if (d_drop > 0) {\n"
     "                    logger_->warn(\"[ZMQ-DROP-OUT] descartados={} en los últimos {} s (total={})\",\n"
     "                                  d_drop, secs, s.send_failures);\n"
     "                }\n"
     "                if (d_ddos + d_rw + d_int > 0) {\n"
     "                    logger_->warn(\"[DETECCIONES] ddos={} ransomware={} internal={} en los últimos {} s\",\n"
     "                                  d_ddos, d_rw, d_int, secs);\n"
     "                }\n"
     "                summary_prev = s;\n"
     "                summary_last = now;\n"
     "            }\n"),

    (ZH, "descarte hacia el firewall contado",
     "            logger_->warn(\"Failed to send event {} (queue full?)\", event.event_id());\n",
     "            std::lock_guard<std::mutex> lock(stats_mutex_);\n"
     "            stats_.send_failures++;  // " + M + " resumido cada 10 s en run()\n"
     "            logger_->debug(\"Failed to send event {} (queue full?)\", event.event_id());\n"),
]

# Insercion de una linea ANTES de la linea unica que contiene la clave, con su sangria.
INSERTS = [
    (ZH, "contador DDoS", "DDoS ATTACK: event=",
     "{ std::lock_guard<std::mutex> lock(stats_mutex_); stats_.detections_ddos++; }  // " + M),
    (ZH, "contador ransomware", "RANSOMWARE ATTACK: event=",
     "{ std::lock_guard<std::mutex> lock(stats_mutex_); stats_.detections_ransomware++; }  // " + M),
    (ZH, "contador internal", "SUSPICIOUS INTERNAL ACTIVITY: event=",
     "{ std::lock_guard<std::mutex> lock(stats_mutex_); stats_.detections_internal++; }  // " + M),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        return 2
    apply = sys.argv[1] == "--apply"
    files = sorted({e[0] for e in BLOCKS} | {e[0] for e in INSERTS})
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

    for f, name, key, ins in INSERTS:
        lines = texts[f].splitlines(keepends=True)
        idx = [i for i, l in enumerate(lines) if key in l]
        if len(idx) != 1:
            print(f"[ERROR]     {f}: {name} -> clave encontrada en {len(idx)} lineas (se esperaba 1)")
            errores += 1
            continue
        i = idx[0]
        if i > 0 and ins in lines[i - 1]:
            print(f"[YA]        {f}: {name} (L{i})")
            continue
        sangria = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
        lines.insert(i, sangria + ins + "\n")
        texts[f] = "".join(lines)
        pendientes += 1
        print(f"[PENDIENTE] {f}: {name} (antes de L{i + 1})")

    total = len(BLOCKS) + len(INSERTS)
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
    for f, name, _, new in BLOCKS:
        if new not in pathlib.Path(f).read_text(encoding="utf-8"):
            print(f"[FALLO]     {f}: {name} no quedo aplicado")
            return 1
    for f, name, _, ins in INSERTS:
        if ins not in pathlib.Path(f).read_text(encoding="utf-8"):
            print(f"[FALLO]     {f}: {name} no quedo aplicado")
            return 1
    print(f"[OK] {total}/{total} ediciones presentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
