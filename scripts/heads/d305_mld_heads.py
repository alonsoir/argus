#!/usr/bin/env python3
# DAY305 — [HEADS-SWITCH-D305] ml-detector: interruptores de cabeza reales leidos del JSON (bloque A, parte ml-detector).
#  - config_loader.cpp: los 5 'enabled' de cabeza (level1, level2.ddos, level2.ransomware, level3.internal,
#    level3.web) dejan de ser obligatorios: ausente o no booleano -> true (comportamiento historico) con
#    [CONFIG-DEFAULT]. ddos_v2 ya lo hacia asi (DAY293).
#  - main.cpp: level1 apagada ya no hace 'return 1'; el ml-detector arranca igual.
#  - zmq_handler.cpp/.hpp: level1 solo corre si su modelo existe (l1_on); apagada no extrae rasgos, no infiere
#    y no publica prediccion ni veredicto de level1. Linea [HEADS] con el estado EFECTIVO de cada cabeza, al
#    arrancar y en cada informe de estadisticas (monitoring.stats_interval_seconds), sin verbose.
# Valida TODO antes de escribir NADA (cada ancla exactamente 1 vez; marca ausente). No toca el JSON ni commitea.
# Uso, raiz del repo:  python3 d305_mld_heads.py --check   (solo valida)
#                      python3 d305_mld_heads.py --apply   (valida y escribe)
import sys

MARK = "[HEADS-SWITCH-D305]"
CL  = "ml-detector/src/config_loader.cpp"
MN  = "ml-detector/src/main.cpp"
ZC  = "ml-detector/src/zmq_handler.cpp"
ZH  = "ml-detector/include/zmq_handler.hpp"

EDITS = []  # (fichero, ancla, reemplazo)
def E(f, old, new):
    EDITS.append((f, old, new))

# ---------------------------------------------------------------- config_loader.cpp
E(CL,
"DetectorConfig ConfigLoader::load() {\n",
"""// [HEADS-SWITCH-D305] interruptor de cabeza: el JSON manda; si 'enabled' falta o no es booleano se usa true
// (comportamiento historico, un JSON incompleto no apaga nada en silencio) y se avisa con [CONFIG-DEFAULT].
// El estado EFECTIVO de cada cabeza se registra en el log con [HEADS] (zmq_handler).
namespace {
bool read_head_enabled(const nlohmann::json& block, const std::string& ctx) {
    if (block.is_object() && block.contains("enabled") && block["enabled"].is_boolean()) {
        return block["enabled"].get<bool>();
    }
    std::cerr << "[CONFIG-DEFAULT] " << ctx << ".enabled ausente o no booleano (formato true|false): se usa true\\n";
    return true;
}
}  // namespace

DetectorConfig ConfigLoader::load() {
""")
for blk, ctx, var in [("l1", "ml.level1", "level1"),
                      ("l2ddos", "ml.level2.ddos", "level2.ddos"),
                      ("l2ransom", "ml.level2.ransomware", "level2.ransomware"),
                      ("l3int", "ml.level3.internal", "level3.internal"),
                      ("l3web", "ml.level3.web", "level3.web")]:
    E(CL,
      f'        config.ml.{var}.enabled = get_required<bool>({blk}, "enabled", "{ctx}");\n',
      f'        config.ml.{var}.enabled = read_head_enabled({blk}, "{ctx}");  // {MARK}\n')

# ---------------------------------------------------------------- main.cpp
E(MN,
"""        } else {
            log->error("❌ Level 1 model is not enabled in configuration");
            return 1;
        }
""",
f"""        }} else {{  // {MARK} level1 apagada: el ml-detector arranca igual, sin rasgos ni inferencia level1
            log->warn("[HEADS] level1 DESACTIVADA por configuracion (ml.level1.enabled=false): el ml-detector "
                      "arranca sin extraccion ni inferencia level1");
        }}
""")
E(MN,
"""        log->info("     Level 1: General Attack (ONNX)");
""",
f"""        if (model) {{  // {MARK}
            log->info("     Level 1: General Attack (ONNX)");
        }}
""")

# ---------------------------------------------------------------- zmq_handler.hpp
E(ZH,
"""    void memory_monitor_loop();
""",
f"""    void memory_monitor_loop();
    // {MARK} estado EFECTIVO de cada cabeza; siempre visible (arranque + informe de estadisticas)
    void log_heads_state(const char* momento) const;
""")

# ---------------------------------------------------------------- zmq_handler.cpp
E(ZC,
"""    logger_->info("   Level 1: General Attack (ONNX)");
""",
f"""    if (level1_model_) {{  // {MARK}
        logger_->info("   Level 1: General Attack (ONNX)");
    }}
    log_heads_state("arranque");  // {MARK}
""")
E(ZC,
"""                             stats.feature_extraction_errors, stats.inference_errors);
                last_stats_report_ = now;
""",
f"""                             stats.feature_extraction_errors, stats.inference_errors);
                log_heads_state("estadisticas");  // {MARK}
                last_stats_report_ = now;
""")
E(ZC,
"""        const bool is_flow_event = (event.event_kind() == protobuf::EVENT_KIND_FLOW);
""",
f"""        const bool is_flow_event = (event.event_kind() == protobuf::EVENT_KIND_FLOW);
        // {MARK} level1 solo si su modelo existe (ml.level1.enabled); apagada: ni rasgos, ni inferencia, ni
        // prediccion/veredicto level1 publicados (antes un label -1 se habria publicado como "ATTACK").
        const bool l1_on = is_flow_event && level1_model_ != nullptr;
""")
E(ZC,
"""        if (is_flow_event) try {  // [EVENT-KIND-D285] level1 solo sobre flujo
""",
f"""        if (l1_on) try {{  // [EVENT-KIND-D285] level1 solo sobre flujo; {MARK} y encendida
""")
E(ZC,
"""        if (is_flow_event) try {  // [EVENT-KIND-D285]
            auto [pred_label, pred_confidence] = level1_model_->predict(features_l1);
""",
f"""        if (l1_on) try {{  // [EVENT-KIND-D285] {MARK}
            auto [pred_label, pred_confidence] = level1_model_->predict(features_l1);
""")
E(ZC,
"""        if (is_flow_event) {  // [EVENT-KIND-D285] sin level1, sin enriquecer
""",
f"""        if (l1_on) {{  // [EVENT-KIND-D285] sin level1, sin enriquecer; {MARK}
""")
E(ZC,
"""        double ml_score    = !is_flow_event ? 0.0
""",
f"""        double ml_score    = !l1_on ? 0.0  // {MARK} level1 apagada: tampoco hay ML que puntuar
""")
E(ZC,
"""        if (!is_flow_event) {  // [EVENT-KIND-D285] sin ML que comparar: autoridad del fast
""",
f"""        if (!l1_on) {{  // [EVENT-KIND-D285] sin ML que comparar: autoridad del fast; {MARK} idem con level1 apagada
""")
E(ZC,
"""        if (is_flow_event) {  // [EVENT-KIND-D285] sin level1, sin veredicto RF
""",
f"""        if (l1_on) {{  // [EVENT-KIND-D285] sin level1, sin veredicto RF; {MARK}
""")
E(ZC,
"""double ZMQHandler::get_memory_usage_mb() {
""",
"""// """ + MARK + """ estado EFECTIVO de cada cabeza (no solo el JSON: una cabeza encendida cuyo detector no se pudo
// construir sale OFF). Siempre visible, sin verbose: al arrancar y en cada informe de estadisticas.
void ZMQHandler::log_heads_state(const char* momento) const {
    const bool l1 = level1_model_ != nullptr;
    const bool v2 = config_.ml.ddos_v2.enabled;
    const bool d1 = ddos_detector_ && config_.ml.level2.ddos.enabled;
    const bool rw = ransomware_detector_ && config_.ml.level2.ransomware.enabled;
    const bool tr = traffic_detector_ && config_.ml.level3.web.enabled;
    const bool in = internal_detector_ && config_.ml.level3.internal.enabled;
    auto s = [](bool b) { return b ? "ON" : "OFF"; };
    std::string nota;
    if (!l1 && !v2 && !(force_all_heads_ && (d1 || rw || tr || in))) {
        nota = " | TODAS APAGADAS: sin clasificacion, final_decision=ALLOW (el bronce se sigue escribiendo)";
    } else if (!l1 && !force_all_heads_ && (d1 || rw || tr || in)) {
        nota = " | AVISO: ddos_v1/ransomware/traffic/internal solo corren tras level1=ATTACK; con level1 OFF no se evaluan";
    }
    logger_->warn("[HEADS] ({}) level1={} ddos_v2={} ddos_v1={} ransomware={} traffic={} internal={} force_all_heads={}{}",
                  momento, s(l1), s(v2), s(d1), s(rw), s(tr), s(in), s(force_all_heads_), nota);
}

double ZMQHandler::get_memory_usage_mb() {
""")

def die(m):
    print("ABORTA (no se ha escrito nada): " + m)
    sys.exit(1)

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        die("uso: python3 d305_mld_heads.py --check | --apply")
    files = sorted({f for f, _, _ in EDITS})
    text = {}
    for f in files:
        try:
            text[f] = open(f, encoding="utf-8").read()
        except OSError as e:
            die(f"no puedo leer {f}: {e}")
        if MARK in text[f]:
            die(f"{f} ya contiene {MARK}: el parche ya se aplico (o a medias). Revisa con git diff.")
    new = dict(text)
    for i, (f, old, rep) in enumerate(EDITS, 1):
        n = new[f].count(old)
        if n != 1:
            die(f"edicion {i} en {f}: el ancla aparece {n} veces (se esperaba 1):\n---\n{old}---")
        new[f] = new[f].replace(old, rep, 1)
    # comprobaciones del resultado
    exp = {CL: 6, MN: 2, ZH: 1, ZC: 11}
    for f in files:
        c = new[f].count(MARK)
        if c != exp[f]:
            die(f"{f}: {c} marcas {MARK} tras el parche (se esperaban {exp[f]})")
    if new[MN].count('log->error("❌ Level 1 model is not enabled in configuration");') != 0:
        die("main.cpp: el return 1 de level1 sigue presente")
    if new[ZC].count("level1_model_->predict(") != 1 or "if (l1_on) try {  // [EVENT-KIND-D285] [HEADS-SWITCH-D305]\n            auto [pred_label" not in new[ZC]:
        die("zmq_handler.cpp: la inferencia level1 no queda protegida por l1_on")
    if new[CL].count('get_required<bool>(') and any(f'"enabled", "{c}")' in new[CL] for c in
            ("ml.level1", "ml.level2.ddos", "ml.level2.ransomware", "ml.level3.internal", "ml.level3.web")):
        die("config_loader.cpp: queda algun 'enabled' de cabeza como obligatorio")
    print(f"OK: {len(EDITS)} ediciones validadas en {len(files)} ficheros")
    for f in files:
        print(f"   {f}: +{new[f].count(chr(10)) - text[f].count(chr(10))} lineas, {new[f].count(MARK)} marcas")
    if sys.argv[1] == "--check":
        print("--check: no se ha escrito nada")
        return
    for f in files:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new[f])
    print("--apply: escrito. Siguiente: git diff --stat y compilacion completa en el defender")

if __name__ == "__main__":
    main()
