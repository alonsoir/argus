#!/usr/bin/env python3
# DAY305 — [HEADS-INTERVALO-D305] ml-detector: el intervalo del resumen [HEADS] pasa a configurarse en el JSON
# (decision de Alonso: lo decide el admin). Campo nuevo monitoring.heads_log_interval_seconds:
#   entero en [10, 3600] segundos, defecto 60 (tambien en el codigo). Si falta, o no es entero, o esta fuera de
#   rango -> se aplica 60 y se avisa con [CONFIG-DEFAULT] (campo, formato y limites); el ml-detector arranca igual.
#   El valor EFECTIVO se registra en el log al arrancar. El maximo (1 h) garantiza que el estado de las cabezas
#   siga viendose periodicamente.
# El resumen deja de ir atado a stats_interval_seconds: temporizador propio en run(), etiqueta "(periodico)".
# Requiere aplicado d305_mld_heads.py (marca [HEADS-SWITCH-D305]). Valida TODO antes de escribir NADA.
# Uso, raiz del repo:  python3 d305_mld_heads_intervalo.py --check | --apply
import json, sys

MARK = "[HEADS-INTERVALO-D305]"
PREV = "[HEADS-SWITCH-D305]"
CH = "ml-detector/include/config_loader.hpp"
CL = "ml-detector/src/config_loader.cpp"
ZC = "ml-detector/src/zmq_handler.cpp"
JS = "ml-detector/config/ml_detector_config.json"

EDITS = []
def E(f, old, new):
    EDITS.append((f, old, new))

E(CH,
"""    struct {
        int stats_interval_seconds;
""",
f"""    struct {{
        int stats_interval_seconds;
        int heads_log_interval_seconds = 60;  // {MARK} resumen [HEADS]; [10, 3600] s, defecto 60
""")

E(CL,
"""        config.monitoring.stats_interval_seconds = get_required<int>(mon, "stats_interval_seconds", "monitoring");
""",
f"""        config.monitoring.stats_interval_seconds = get_required<int>(mon, "stats_interval_seconds", "monitoring");
        {{   // {MARK} el JSON manda; ausente, no entero o fuera de rango -> defecto validado + [CONFIG-DEFAULT]
            constexpr int kDef = 60, kMin = 10, kMax = 3600;
            config.monitoring.heads_log_interval_seconds = kDef;
            if (!mon.contains("heads_log_interval_seconds")) {{
                std::cerr << "[CONFIG-DEFAULT] monitoring.heads_log_interval_seconds ausente (entero en [" << kMin
                          << ", " << kMax << "] segundos): se usa " << kDef << "\\n";
            }} else if (!mon["heads_log_interval_seconds"].is_number_integer() ||
                       mon["heads_log_interval_seconds"].get<long long>() < kMin ||
                       mon["heads_log_interval_seconds"].get<long long>() > kMax) {{
                std::cerr << "[CONFIG-DEFAULT] monitoring.heads_log_interval_seconds invalido ("
                          << mon["heads_log_interval_seconds"].dump() << "; entero en [" << kMin << ", " << kMax
                          << "] segundos): se usa " << kDef << "\\n";
            }} else {{
                config.monitoring.heads_log_interval_seconds = mon["heads_log_interval_seconds"].get<int>();
            }}
        }}
""")

E(ZC,
"""    log_heads_state("arranque");  // [HEADS-SWITCH-D305]
""",
f"""    log_heads_state("arranque");  // [HEADS-SWITCH-D305]
    logger_->info("[HEADS] resumen periodico cada {{}} s (monitoring.heads_log_interval_seconds)",  // {MARK}
                  config_.monitoring.heads_log_interval_seconds);
""")
E(ZC,
"""                log_heads_state("estadisticas");  // [HEADS-SWITCH-D305]
""",
"")
E(ZC,
"""    auto stats_interval = std::chrono::seconds(config_.monitoring.stats_interval_seconds);
""",
f"""    auto stats_interval = std::chrono::seconds(config_.monitoring.stats_interval_seconds);
    // {MARK} resumen [HEADS] con temporizador propio (monitoring.heads_log_interval_seconds)
    const auto heads_interval = std::chrono::seconds(config_.monitoring.heads_log_interval_seconds);
    auto heads_last = std::chrono::steady_clock::now();
""")
E(ZC,
"""            // [SUMMARY-D285] solo se imprime si hay algo que contar
""",
f"""            if (now - heads_last >= heads_interval) {{  // {MARK}
                log_heads_state("periodico");
                heads_last = now;
            }}

            // [SUMMARY-D285] solo se imprime si hay algo que contar
""")

JSON_OLD = """  "monitoring": {
    "stats_interval_seconds": 60,
"""
JSON_DOC = (f"{MARK} heads_log_interval_seconds: cada cuantos segundos escribe el ml-detector la linea [HEADS] con "
            "el estado EFECTIVO de cada cabeza (siempre visible, sin verbose). Entero en [10, 3600]; defecto 60. Si "
            "falta, no es entero o esta fuera de rango se usa 60 con [CONFIG-DEFAULT] y el ml-detector arranca "
            "igual. El maximo de 1 h garantiza que el estado siga viendose periodicamente.")
JSON_NEW = ("  \"monitoring\": {\n"
            f"    \"_doc_heads_log_interval_seconds\": {json.dumps(JSON_DOC, ensure_ascii=False)},\n"
            "    \"heads_log_interval_seconds\": 60,\n"
            "    \"stats_interval_seconds\": 60,\n")
E(JS, JSON_OLD, JSON_NEW)

def die(m):
    print("ABORTA (no se ha escrito nada): " + m)
    sys.exit(1)

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        die("uso: python3 d305_mld_heads_intervalo.py --check | --apply")
    files = sorted({f for f, _, _ in EDITS})
    text = {}
    for f in files:
        try:
            text[f] = open(f, encoding="utf-8").read()
        except OSError as e:
            die(f"no puedo leer {f}: {e}")
        if MARK in text[f]:
            die(f"{f} ya contiene {MARK}: el parche ya se aplico (o a medias). Revisa con git diff.")
    if PREV not in text[ZC] or PREV not in text[CL]:
        die(f"falta {PREV}: aplica antes d305_mld_heads.py")
    new = dict(text)
    for i, (f, old, rep) in enumerate(EDITS, 1):
        n = new[f].count(old)
        if n != 1:
            die(f"edicion {i} en {f}: el ancla aparece {n} veces (se esperaba 1):\n---\n{old}---")
        new[f] = new[f].replace(old, rep, 1)
    exp = {CH: 1, CL: 1, ZC: 3, JS: 1}
    for f in files:
        if new[f].count(MARK) != exp[f]:
            die(f"{f}: {new[f].count(MARK)} marcas {MARK} (se esperaban {exp[f]})")
    if 'log_heads_state("estadisticas")' in new[ZC]:
        die("zmq_handler.cpp: sigue el resumen atado a stats_interval_seconds")
    if new[ZC].count('log_heads_state("periodico");') != 1 or new[ZC].count('log_heads_state("arranque");') != 1:
        die("zmq_handler.cpp: llamadas a log_heads_state inesperadas")
    try:
        j = json.loads(new[JS])
    except json.JSONDecodeError as e:
        die(f"el JSON resultante no parsea: {e}")
    if j["monitoring"].get("heads_log_interval_seconds") != 60 or j["monitoring"].get("stats_interval_seconds") != 60:
        die("JSON: monitoring.heads_log_interval_seconds o stats_interval_seconds inesperados")
    print(f"OK: {len(EDITS)} ediciones validadas en {len(files)} ficheros; JSON valido "
          f"(monitoring.heads_log_interval_seconds=60)")
    for f in files:
        print(f"   {f}: +{new[f].count(chr(10)) - text[f].count(chr(10))} lineas")
    if sys.argv[1] == "--check":
        print("--check: no se ha escrito nada")
        return
    for f in files:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new[f])
    print("--apply: escrito. Siguiente: compilacion completa en production")

if __name__ == "__main__":
    main()
