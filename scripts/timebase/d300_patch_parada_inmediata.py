#!/usr/bin/env python3
"""DAY300 DEBT-SNIFFER-SHUTDOWN-HANG-001: parada inmediata del sniffer.
Medido: cuatro hilos duermen con sleep_for(30 s) no interrumpible y su parada hace join(): estadisticas y
procesador ransomware (ring_consumer), extraccion ransomware (RansomwareFeatureProcessor) y heartbeat
(etcd-client, libreria compartida). La parada tardaba 0-30 s y sniffer-stop (15 s) acabo en SIGKILL 2/2.
Arreglo: condition_variable::wait_for con predicado + notify_all en la parada (los intervalos no cambian).
Ademas: monitoring.stats_interval_seconds validado con [CONFIG-DEFAULT] y _doc; aviso de sniffer-stop.
--check | --apply desde la raiz del repo. Atomico: todas las ediciones o ninguna."""
import os
import sys

M = "[PARADA-INMEDIATA-D300]"
RCH = "sniffer/include/ring_consumer.hpp"
RCC = "sniffer/src/userspace/ring_consumer.cpp"
RFH = "sniffer/include/ransomware_feature_processor.hpp"
RFC = "sniffer/src/userspace/ransomware_feature_processor.cpp"
ETC = "etcd-client/src/etcd_client.cpp"
CFG = "sniffer/src/userspace/config_manager.cpp"
JSN = "sniffer/config/sniffer.json"
MK = "Makefile"

CFG_NEW = (
    "    {   // " + M + " el JSON manda: entero [1, 3600] s, defecto 30; si falta o es invalido, defecto\n"
    "        // con [CONFIG-DEFAULT] y el sniffer arranca igual.\n"
    "        constexpr int kDef = 30, kMin = 1, kMax = 3600;\n"
    "        const Json::Value& v = monitoring_json[\"stats_interval_seconds\"];\n"
    "        int x = kDef;\n"
    "        if (v.isNull()) {\n"
    "            std::cerr << \"[CONFIG-DEFAULT] monitoring.stats_interval_seconds ausente -> defecto=\" << kDef\n"
    "                      << \" (entero, rango [\" << kMin << \", \" << kMax << \"] s)\" << std::endl;\n"
    "        } else if (!v.isInt()) {\n"
    "            std::cerr << \"[CONFIG-DEFAULT] monitoring.stats_interval_seconds no es entero -> defecto=\" << kDef\n"
    "                      << \" (entero, rango [\" << kMin << \", \" << kMax << \"] s)\" << std::endl;\n"
    "        } else if (v.asInt() < kMin || v.asInt() > kMax) {\n"
    "            std::cerr << \"[CONFIG-DEFAULT] monitoring.stats_interval_seconds=\" << v.asInt()\n"
    "                      << \" fuera de rango [\" << kMin << \", \" << kMax << \"] -> defecto=\" << kDef << std::endl;\n"
    "        } else {\n"
    "            x = v.asInt();\n"
    "        }\n"
    "        monitoring.stats_interval_seconds = x;\n"
    "    }\n"
)

JSN_DOC = (
    "    \"_doc_stats_interval_seconds\": \"entero, rango [1, 3600], defecto 30. " + M + " Cada cuantos "
    "segundos escribe el sniffer el bloque ESTADISTICAS en su log. No afecta a la deteccion ni a la parada "
    "(la espera es interrumpible). Si falta, no es entero o esta fuera de rango: defecto con [CONFIG-DEFAULT].\",\n"
)

EDITS = [
    # --- RingBufferConsumer: espera interrumpible comun ---
    (RCH,
     "#include <condition_variable>\n",
     "#include <condition_variable>\n"
     "#include <mutex>   // " + M + "\n"
     "#include <chrono>  // " + M + "\n"),
    (RCH,
     "    std::atomic<bool> should_stop_{false};\n",
     "    std::atomic<bool> should_stop_{false};\n"
     "    // " + M + " espera interrumpible de los hilos que duermen por intervalo (estadisticas,\n"
     "    // ransomware). Devuelve true si hay que parar. stop() notifica tras poner should_stop_.\n"
     "    std::mutex parada_mtx_;\n"
     "    std::condition_variable parada_cv_;\n"
     "    bool espera_o_parada(std::chrono::seconds s) {\n"
     "        std::unique_lock<std::mutex> lk(parada_mtx_);\n"
     "        return parada_cv_.wait_for(lk, s, [this] { return should_stop_.load(); });\n"
     "    }\n"),
    (RCC,
     "    should_stop_ = true;\n\n    // ORDEN CORRECTO DE PARADA:\n",
     "    should_stop_ = true;\n"
     "    { std::lock_guard<std::mutex> lk(parada_mtx_); }  // " + M + " sin despertar perdido\n"
     "    parada_cv_.notify_all();\n"
     "\n    // ORDEN CORRECTO DE PARADA:\n"),
    (RCC,
     "        std::this_thread::sleep_for(std::chrono::seconds(stats_interval_seconds_));\n",
     "        if (espera_o_parada(std::chrono::seconds(stats_interval_seconds_))) break;  // " + M + "\n"),
    (RCC,
     "        std::this_thread::sleep_for(\n            std::chrono::seconds(RANSOMWARE_EXTRACTION_INTERVAL_SEC));\n",
     "        if (espera_o_parada(std::chrono::seconds(RANSOMWARE_EXTRACTION_INTERVAL_SEC))) break;  // " + M + "\n"),
    # --- RansomwareFeatureProcessor ---
    (RFH,
     "#include <atomic>\n",
     "#include <atomic>\n"
     "#include <mutex>               // " + M + "\n"
     "#include <condition_variable>  // " + M + "\n"),
    (RFH,
     "        std::atomic<bool> running_{false};\n",
     "        std::atomic<bool> running_{false};\n"
     "        std::mutex parada_mtx_;               // " + M + " espera interrumpible de la extraccion\n"
     "        std::condition_variable parada_cv_;   // " + M + "\n"),
    (RFC,
     "        std::this_thread::sleep_for(std::chrono::seconds(extraction_interval_seconds_));\n",
     "        {   // " + M + " espera interrumpible: stop() no espera al intervalo\n"
     "            std::unique_lock<std::mutex> lk(parada_mtx_);\n"
     "            if (parada_cv_.wait_for(lk, std::chrono::seconds(extraction_interval_seconds_),\n"
     "                                    [this] { return !running_.load(); })) break;\n"
     "        }\n"),
    (RFC,
     "    running_ = false;\n\n    if (extraction_thread_.joinable()) {\n",
     "    running_ = false;\n"
     "    { std::lock_guard<std::mutex> lk(parada_mtx_); }  // " + M + " sin despertar perdido\n"
     "    parada_cv_.notify_all();\n"
     "\n    if (extraction_thread_.joinable()) {\n"),
    # --- etcd-client (libreria compartida): heartbeat ---
    (ETC,
     "#include <mutex>\n",
     "#include <mutex>\n#include <condition_variable>  // " + M + "\n"),
    (ETC,
     "    std::atomic<bool> heartbeat_running_{false};\n",
     "    std::atomic<bool> heartbeat_running_{false};\n"
     "    std::mutex hb_mtx_;               // " + M + " espera interrumpible del heartbeat\n"
     "    std::condition_variable hb_cv_;   // " + M + "\n"),
    (ETC,
     "                std::this_thread::sleep_for(\n"
     "                    std::chrono::seconds(config_.heartbeat_interval_seconds)\n"
     "                );\n",
     "                {   // " + M + " espera interrumpible: la parada no espera al intervalo\n"
     "                    std::unique_lock<std::mutex> lk(hb_mtx_);\n"
     "                    if (hb_cv_.wait_for(lk, std::chrono::seconds(config_.heartbeat_interval_seconds),\n"
     "                                        [this] { return !heartbeat_running_.load(); })) break;\n"
     "                }\n"),
    (ETC,
     "        if (heartbeat_running_.exchange(false)) {\n            if (heartbeat_thread_.joinable()) {\n",
     "        if (heartbeat_running_.exchange(false)) {\n"
     "            { std::lock_guard<std::mutex> lk(hb_mtx_); }  // " + M + " sin despertar perdido\n"
     "            hb_cv_.notify_all();\n"
     "            if (heartbeat_thread_.joinable()) {\n"),
    # --- config: stats_interval_seconds ---
    (CFG,
     "    monitoring.stats_interval_seconds = monitoring_json.get(\"stats_interval_seconds\", 30).asInt();\n",
     CFG_NEW),
    (JSN,
     "    \"stats_interval_seconds\": 30,\n",
     JSN_DOC + "    \"stats_interval_seconds\": 30,\n"),
    # --- Makefile: aviso de sniffer-stop (el volcado de parada pudo haberse hecho antes del SIGKILL) ---
    (MK,
     "SIGKILL (sin volcado de parada)'",
     "SIGKILL. Si en sniffer.log no consta el volcado de parada se restaurara el ultimo periodico'"),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d300_patch_parada_inmediata.py --check | --apply")
        return 2
    files = sorted({e[0] for e in EDITS})
    text = {}
    errores = []
    for f in files:
        if not os.path.isfile(f):
            errores.append(f + ": no existe (ejecutar desde la raiz del repo)")
            continue
        with open(f, encoding="utf-8") as fh:
            text[f] = fh.read()
        if f != MK and M in text[f]:
            errores.append(f + ": ya contiene " + M + " (ya aplicado)")
    if errores:
        print("\n".join(errores))
        return 1
    for i, (f, old, new) in enumerate(EDITS, 1):
        n = text[f].count(old)
        if n != 1:
            errores.append("edicion %d en %s: el ancla aparece %d veces (se esperaba 1)" % (i, f, n))
            continue
        text[f] = text[f].replace(old, new, 1)
    if errores:
        print("\n".join(errores))
        print("NADA aplicado")
        return 1
    if sys.argv[1] == "--check":
        print("OK --check: %d ediciones en %d ficheros, todas las anclas unicas" % (len(EDITS), len(files)))
        return 0
    tmps = []
    for f in files:
        tmp = f + ".tmp_d300"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text[f])
        os.chmod(tmp, os.stat(f).st_mode)
        tmps.append((tmp, f))
    for tmp, f in tmps:
        os.replace(tmp, f)
    print("OK --apply: %d ediciones en %d ficheros con marca %s" % (len(EDITS), len(files), M))
    return 0


if __name__ == "__main__":
    sys.exit(main())
