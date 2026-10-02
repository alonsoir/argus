#!/usr/bin/env python3
"""d285_patch_writers.py — DAY285: rag_logger y csv_writer fuera del camino caliente (por JSON)
y guarda de plugins sin plugins cargados.

- config_loader: csv_writer.enabled y rag_logger.enabled (opcionales, por defecto true).
- zmq_handler: no crea csv_writer_/rag_logger_ si estan desactivados; invoke de plugins solo si
  loaded_count() > 0 (antes serializaba el evento entero con 0 plugins).
- ml_detector_config.json: rag_logger (seccion muerta) -> solo enabled=false; csv_writer.enabled=false.
Uso (raiz del repo): python3 d285_patch_writers.py --check | --apply
Atomico, idempotente, valida el JSON, no commitea.
"""
import sys
import json
import pathlib

M = "[WRITERS-D285]"
HH = "ml-detector/include/config_loader.hpp"
CC = "ml-detector/src/config_loader.cpp"
ZH = "ml-detector/src/zmq_handler.cpp"
JS = "ml-detector/config/ml_detector_config.json"

EDITS = []

EDITS.append((HH, "struct csv_writer.enabled + rag_logger",
    "    // CSV Writer\n"
    "    struct {\n"
    "        std::string base_dir;\n"
    "        float min_score_threshold;\n"
    "        int max_events_per_file;\n"
    "    } csv_writer;\n",
    "    // CSV Writer\n"
    "    struct {\n"
    "        bool enabled = true;  // " + M + " opcional en el JSON\n"
    "        std::string base_dir;\n"
    "        float min_score_threshold;\n"
    "        int max_events_per_file;\n"
    "    } csv_writer;\n"
    "\n"
    "    // " + M + " RAG Logger: solo el interruptor; el resto vive en rag_logger_config.json\n"
    "    struct {\n"
    "        bool enabled = true;\n"
    "    } rag_logger;\n"))

EDITS.append((CC, "lectura de los interruptores",
    '        config.csv_writer.max_events_per_file = get_required<int>(csv, "max_events_per_file", "csv_writer");\n'
    "    }\n",
    '        config.csv_writer.max_events_per_file = get_required<int>(csv, "max_events_per_file", "csv_writer");\n'
    "        // " + M + " interruptor opcional (por defecto true: otras configs no cambian)\n"
    '        config.csv_writer.enabled = csv.value("enabled", true);\n'
    "    }\n"
    "\n"
    "    // " + M + " RAG Logger: solo 'enabled'; el resto de su config vive en rag_logger_config.json\n"
    "    {\n"
    '        config.rag_logger.enabled = json_.contains("rag_logger")\n'
    '            ? json_["rag_logger"].value("enabled", true) : true;\n'
    "    }\n"))

EDITS.append((ZH, "csv_writer condicionado",
    "    if (!hmac_key_hex_.empty()) {\n"
    "        try {\n"
    "            std::string csv_dir = config_.csv_writer.base_dir;\n",
    "    if (!config_.csv_writer.enabled) {  // " + M + "\n"
    '        logger_->info("CsvEventWriter desactivado por configuracion (csv_writer.enabled=false)");\n'
    "    } else if (!hmac_key_hex_.empty()) {\n"
    "        try {\n"
    "            std::string csv_dir = config_.csv_writer.base_dir;\n"))

EDITS.append((ZH, "rag_logger condicionado",
    "    try {\n"
    "        rag_logger_ = ml_defender::create_rag_logger_from_config(\n",
    "    if (!config_.rag_logger.enabled) {  // " + M + "\n"
    '        logger_->info("RAG Logger desactivado por configuracion (rag_logger.enabled=false)");\n'
    "    } else try {\n"
    "        rag_logger_ = ml_defender::create_rag_logger_from_config(\n"))

EDITS.append((ZH, "guarda de plugins",
    "        if (plugin_loader_ != nullptr) {\n",
    "        if (plugin_loader_ != nullptr && plugin_loader_->loaded_count() > 0) {  // " + M + " sin plugins: sin serializar\n"))

EDITS.append((JS, "seccion rag_logger",
    '  "rag_logger": {\n'
    '    "enabled": true,\n'
    '    "base_dir": "/vagrant/logs/rag",\n'
    '    "log_all_events": false,\n'
    '    "log_detections_only": true,\n'
    '    "min_score_threshold": 0.5,\n'
    '    "buffer_size": 100,\n'
    '    "flush_interval_seconds": 1,\n'
    '    "include_artifacts": true,\n'
    '    "artifact_format": "protobuf",\n'
    '    "save_protobuf_artifacts": false,\n'
    '    "save_json_artifacts": false\n'
    '  },\n',
    '  "rag_logger": {\n'
    '    "_comment": "' + M + ' Solo se lee enabled; el resto de la config vive en ml-detector/config/rag_logger_config.json. Desactivado: el grafo cubre lo que hacia y generaba 2 artefactos cifrados por evento sobre vboxsf.",\n'
    '    "enabled": false\n'
    '  },\n'))

EDITS.append((JS, "csv_writer.enabled",
    '  "csv_writer": {\n'
    '    "base_dir": "/vagrant/logs/ml-detector/events",\n',
    '  "csv_writer": {\n'
    '    "_comment": "' + M + ' Desactivado: su unico consumidor era make parquet-convert (Parquet antiguo, DEBT-PARQUET-SCHEMA-001).",\n'
    '    "enabled": false,\n'
    '    "base_dir": "/vagrant/logs/ml-detector/events",\n'))


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
    try:
        json.loads(texts[JS])
    except Exception as e:
        print(f"[ERROR]     {JS}: el JSON resultante no es valido: {e}")
        errores += 1
    if errores:
        print(f"[ABORT] {errores} error(es); no se escribe nada")
        return 1
    if not apply:
        print(f"[CHECK] {pendientes} edicion(es) pendiente(s) de {len(EDITS)}; JSON resultante valido")
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
