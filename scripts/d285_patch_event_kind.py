#!/usr/bin/env python3
"""d285_patch_event_kind.py — DAY285, punto 1: EventKind explicito en el proto.

Fast alert y ventana ransomware llegan al ml-detector con centinelas: no pasan por
level1 ni por las cabezas. Decision neutra aguas abajo: final_score = fast.
Uso (raiz del repo): python3 d285_patch_event_kind.py --check | --apply
Atomico (o todo o nada), idempotente, no commitea.
"""
import sys
import pathlib

M = "[EVENT-KIND-D285]"
PROTO = "protobuf/network_security.proto"
RC = "sniffer/src/userspace/ring_consumer.cpp"
ZH = "ml-detector/src/zmq_handler.cpp"


def ind(s, n=4):
    return "".join((" " * n + l) if l.strip() else l for l in s.splitlines(keepends=True))


def wrap(old, comment):
    return "        if (is_flow_event) {  // " + M + " " + comment + "\n" + ind(old) + "        }\n"


EDITS = []

# ---------------- proto ----------------
EDITS.append((PROTO, "enum EventKind",
    "enum DetectorSource {\n",
    "// " + M + " Tipo de mensaje que emite el sniffer. Solo FLOW trae rasgos de flujo;\n"
    "// el resto llega con centinelas y no pasa por level1 ni por las cabezas del ml-detector.\n"
    "// FLOW = 0 a proposito: un productor que no lo rellene sigue el camino de siempre.\n"
    "enum EventKind {\n"
    "    EVENT_KIND_FLOW = 0;\n"
    "    EVENT_KIND_FAST_ALERT = 1;          // send_fast_alert (heuristica ransomware, capa 1)\n"
    "    EVENT_KIND_RANSOMWARE_WINDOW = 2;   // send_ransomware_features (agregado de ventana)\n"
    "}\n"
    "\n"
    "enum DetectorSource {\n"))

EDITS.append((PROTO, "campo event_kind = 37",
    "  VictimWindow victim_window = 36;\n}\n",
    "  VictimWindow victim_window = 36;\n"
    "  // " + M + " FLOW (0) | FAST_ALERT | RANSOMWARE_WINDOW\n"
    "  EventKind event_kind = 37;\n"
    "}\n"))

# ---------------- sniffer ----------------
o = "    proto_event.set_event_id(event_id);\n"
EDITS.append((RC, "productor FLOW", o,
    o + "    proto_event.set_event_kind(protobuf::EVENT_KIND_FLOW);  // " + M + "\n"))

o = '        alert.set_event_id("fast-alert-" + std::to_string(event.timestamp));\n'
EDITS.append((RC, "productor FAST_ALERT", o,
    o + "        alert.set_event_kind(protobuf::EVENT_KIND_FAST_ALERT);  // " + M + "\n"))

o = '        event.set_event_id("ransomware-features-" + std::to_string(now_ns));\n'
EDITS.append((RC, "productor RANSOMWARE_WINDOW", o,
    o + "        event.set_event_kind(protobuf::EVENT_KIND_RANSOMWARE_WINDOW);  // " + M + "\n"))

# ---------------- ml-detector ----------------
o = ('        logger_->debug("\U0001F3AF Fast Detector: score={:.4f}, triggered={}, reason={}",\n'
     '                       fast_score, fast_triggered, fast_reason);\n')
EDITS.append((ZH, "is_flow_event", o,
    o + "\n"
    "        // " + M + " Solo los eventos de flujo traen rasgos; fast alert y ventana\n"
    "        // ransomware llegan con centinelas y no pasan por level1 ni por las cabezas.\n"
    "        const bool is_flow_event = (event.event_kind() == protobuf::EVENT_KIND_FLOW);\n"))

EDITS.append((ZH, "level1 extraccion",
    "        std::vector<float> features_l1;\n        try {\n",
    "        std::vector<float> features_l1;\n"
    "        if (is_flow_event) try {  // " + M + " level1 solo sobre flujo\n"))

EDITS.append((ZH, "level1 prediccion",
    "        try {\n            auto [pred_label, pred_confidence] = level1_model_->predict(features_l1);\n",
    "        if (is_flow_event) try {  // " + M + "\n"
    "            auto [pred_label, pred_confidence] = level1_model_->predict(features_l1);\n"))

o = ('        auto* level1_pred  = ml_analysis->mutable_level1_general_detection();\n'
     '        level1_pred->set_model_name("level1_attack_detector");\n'
     '        level1_pred->set_model_version("1.0.0");\n'
     '        level1_pred->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_GENERAL);\n'
     '        level1_pred->set_prediction_class(label_l1 == 0 ? "BENIGN" : "ATTACK");\n'
     '        level1_pred->set_confidence_score(confidence_l1);\n'
     '\n'
     '        ml_analysis->set_attack_detected_level1(label_l1 == 1);\n'
     '        ml_analysis->set_level1_confidence(confidence_l1);\n')
EDITS.append((ZH, "enriquecimiento level1", o, wrap(o, "sin level1, sin enriquecer")))

EDITS.append((ZH, "ml_score",
    "        double ml_score    = label_l1 == 1 ? confidence_l1 : (1.0 - confidence_l1);\n",
    "        // " + M + " sin rasgos de flujo el ML no se evalua: 0 (no 1 - 0 = 1)\n"
    "        double ml_score    = !is_flow_event ? 0.0\n"
    "                           : (label_l1 == 1 ? confidence_l1 : (1.0 - confidence_l1));\n"))

EDITS.append((ZH, "authoritative_source",
    "        if (score_divergence > config_.scoring.divergence_warn_threshold) {\n"
    "            event.set_authoritative_source(protobuf::DETECTOR_SOURCE_DIVERGENCE);\n",
    "        if (!is_flow_event) {  // " + M + " sin ML que comparar: autoridad del fast\n"
    "            event.set_authoritative_source(protobuf::DETECTOR_SOURCE_FAST_ONLY);\n"
    "        } else if (score_divergence > config_.scoring.divergence_warn_threshold) {\n"
    "            event.set_authoritative_source(protobuf::DETECTOR_SOURCE_DIVERGENCE);\n"))

o = ('        auto* rf_verdict = provenance->add_verdicts();\n'
     '        rf_verdict->set_engine_name("random-forest-level1");\n'
     '        rf_verdict->set_classification(label_l1 == 0 ? "Benign" : "Attack");\n'
     '        rf_verdict->set_confidence(confidence_l1);\n'
     '        rf_verdict->set_reason_code(\n'
     '            label_l1 == 1\n'
     '                ? ml_defender::to_string(ml_defender::ReasonCode::STAT_ANOMALY)\n'
     '                : ml_defender::to_string(ml_defender::ReasonCode::UNKNOWN)\n'
     '        );\n'
     '        rf_verdict->set_timestamp_ns(\n'
     '            static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(\n'
     '                std::chrono::system_clock::now().time_since_epoch()\n'
     '            ).count())\n'
     '        );\n')
EDITS.append((ZH, "rf_verdict", o, wrap(o, "sin level1, sin veredicto RF")))

EDITS.append((ZH, "compuerta cabezas",
    "        const bool hs_gate = l2_gate_open(force_all_heads_, label_l1, confidence_l1, config_.ml.thresholds.level1_attack);\n",
    "        // " + M + " sin rasgos de flujo la compuerta nunca abre, ni con FORCE_ALL_HEADS\n"
    "        const bool hs_gate = is_flow_event &&\n"
    "                             l2_gate_open(force_all_heads_, label_l1, confidence_l1, config_.ml.thresholds.level1_attack);\n"))

EDITS.append((ZH, "categoria NORMAL",
    '        } else {\n            event.set_threat_category("NORMAL");\n        }\n',
    '        } else if (is_flow_event) {  // ' + M + ' fast alert / ventana: conserva la categoria del sniffer\n'
    '            event.set_threat_category("NORMAL");\n        }\n'))


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
