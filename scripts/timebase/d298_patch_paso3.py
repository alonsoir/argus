#!/usr/bin/env python3
# DAY298 paso 3 (ml-detector): la etapa 1 de la cabeza DDoS v2 consume DDoSFeatures.victim_state del sniffer.
# BAJO_PRESION pasa siempre; FRIO nunca (el ratio en frio no significa nada: 200 pases indebidos medidos DAY298);
# NORMAL con ratio >= k_ratio; sin estado (0 o valor desconocido) = regla antigua, contada y avisada en el resumen.
# evaluate() conserva su firma con un parametro por defecto (desconocido): la paridad Python/C++ no cambia.
# Atomico, todo o nada; valida el JSON del ml-detector. Uso, desde la raiz del repo: --check | --apply
import json, os, sys

MARCA = "DDOS-ETAPA1-D298"
H = "ml-detector/include/ml_defender/ddos_v2_head.hpp"
ZC = "ml-detector/src/zmq_handler.cpp"
ZH = "ml-detector/include/zmq_handler.hpp"
JS = "ml-detector/config/ml_detector_config.json"
PT = "ml-detector/tests/unit/test_ddos_v2_parity.cpp"

ENUM = r'''// [DDOS-ETAPA1-D298] Estado de la victima segun la histeresis del sniffer (DDoSFeatures.victim_state). Valores
// alineados con protobuf::VictimState (zmq_handler.cpp lo comprueba con static_assert); la cabecera no depende del proto.
enum class EstadoVictima : int { Desconocido = 0, Frio = 1, Normal = 2, BajoPresion = 3 };

// Etapa 1. BajoPresion: pasa siempre (la EWMA del sniffer esta congelada y el episodio sigue). Frio: nunca (ratio
// sin base). Normal: ratio >= k. Desconocido o valor no previsto: regla antigua (ratio >= k).
inline bool etapa1_pasa(EstadoVictima e, float ratio, double k) noexcept {
    switch (e) {
        case EstadoVictima::BajoPresion: return true;
        case EstadoVictima::Frio: return false;
        default: return static_cast<double>(ratio) >= k;
    }
}

'''

PARITY = r'''    // [DDOS-ETAPA1-D298] etapa 1 con el estado de la victima (casos fijos, independientes del CSV)
    {
        namespace d2 = ml_defender::ddos_v2;
        const double k = d2::kTrainK;
        const d2::Input alto{0.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f, static_cast<float>(k) + 2.0f};
        d2::Input bajo = alto;
        bajo.victim_rate_ratio = 0.5f;
        int e = 0;
        if (!d2::evaluate(alto, k).stage1) ++e;                                    // desconocido: regla antigua
        if (d2::evaluate(bajo, k).stage1) ++e;
        if (d2::evaluate(alto, k, d2::EstadoVictima::Frio).stage1) ++e;            // frio: nunca (frio benigno D298)
        if (!d2::evaluate(bajo, k, d2::EstadoVictima::BajoPresion).stage1) ++e;    // presion: siempre
        if (!d2::evaluate(alto, k, d2::EstadoVictima::Normal).stage1) ++e;         // normal: ratio >= k
        if (d2::evaluate(bajo, k, d2::EstadoVictima::Normal).stage1) ++e;
        if (!d2::evaluate(alto, k, static_cast<d2::EstadoVictima>(7)).stage1) ++e;  // valor no previsto: regla antigua
        std::printf("[DDOS-V2-ETAPA1] casos=7 fallos=%d\n", e);
        bad += e;
    }
'''

CAMBIOS = {
    H: [
        ("struct Input {\n", ENUM + "struct Input {\n", 1),
        ("inline Result evaluate(const Input& in, double k) noexcept {\n"
         "    Result r;\n"
         "    r.stage1 = static_cast<double>(in.victim_rate_ratio) >= k;\n",
         "inline Result evaluate(const Input& in, double k,\n"
         "                       EstadoVictima estado = EstadoVictima::Desconocido) noexcept {  // [DDOS-ETAPA1-D298]\n"
         "    Result r;\n"
         "    r.stage1 = etapa1_pasa(estado, in.victim_rate_ratio, k);\n", 1),
    ],
    ZH: [
        ("        uint64_t ddos_v2_ataque = 0;         // [DDOS-V2-D293] eventos que la cabeza v2 marca DDoS\n",
         "        uint64_t ddos_v2_ataque = 0;         // [DDOS-V2-D293] eventos que la cabeza v2 marca DDoS\n"
         "        uint64_t ddos_v2_sin_estado = 0;     // [DDOS-ETAPA1-D298] eventos sin victim_state (etapa 1 antigua)\n", 1),
    ],
    ZC: [
        ("            const auto r2 = ml_defender::ddos_v2::evaluate(in2, config_.ml.ddos_v2.k_ratio);\n",
         "            // [DDOS-ETAPA1-D298] la etapa 1 consume el estado de la victima del sniffer\n"
         "            static_assert(static_cast<int>(ml_defender::ddos_v2::EstadoVictima::Frio) == protobuf::VICTIM_STATE_COLD &&\n"
         "                          static_cast<int>(ml_defender::ddos_v2::EstadoVictima::Normal) == protobuf::VICTIM_STATE_NORMAL &&\n"
         "                          static_cast<int>(ml_defender::ddos_v2::EstadoVictima::BajoPresion) ==\n"
         "                              protobuf::VICTIM_STATE_UNDER_PRESSURE &&\n"
         "                          static_cast<int>(ml_defender::ddos_v2::EstadoVictima::Desconocido) == protobuf::VICTIM_STATE_UNKNOWN,\n"
         "                          \"EstadoVictima desalineado con protobuf::VictimState\");\n"
         "            const auto ev2 = static_cast<ml_defender::ddos_v2::EstadoVictima>(static_cast<int>(dv2.victim_state()));\n"
         "            const auto r2 = ml_defender::ddos_v2::evaluate(in2, config_.ml.ddos_v2.k_ratio, ev2);\n", 1),
        ("            p2->set_confidence_score(static_cast<float>(r2.p1));\n",
         "            p2->set_confidence_score(static_cast<float>(r2.p1));\n"
         "            if (dv2.victim_state() == protobuf::VICTIM_STATE_UNKNOWN) {  // [DDOS-ETAPA1-D298] etapa 1 antigua\n"
         "                std::lock_guard<std::mutex> lock(stats_mutex_);\n"
         "                stats_.ddos_v2_sin_estado++;\n"
         "            }\n", 1),
        ('            logger_->debug("🤖 DDoS-v2: etapa1={} ratio={:.3f} p1={:.4f} clase={} event={}",\n'
         '                           r2.stage1, dv2.victim_rate_ratio(), r2.p1, r2.clase, event.event_id());\n',
         '            logger_->debug("🤖 DDoS-v2: etapa1={} estado={} ratio={:.3f} p1={:.4f} clase={} event={}",\n'
         '                           r2.stage1, static_cast<int>(dv2.victim_state()), dv2.victim_rate_ratio(), r2.p1, r2.clase,\n'
         '                           event.event_id());\n', 1),
        ("                const uint64_t d_v2a  = summary_delta(s.ddos_v2_ataque, summary_prev.ddos_v2_ataque);\n",
         "                const uint64_t d_v2a  = summary_delta(s.ddos_v2_ataque, summary_prev.ddos_v2_ataque);\n"
         "                const uint64_t d_v2s  = summary_delta(s.ddos_v2_sin_estado, summary_prev.ddos_v2_sin_estado);  // [DDOS-ETAPA1-D298]\n", 1),
        ("                summary_prev = s;\n                summary_last = now;\n",
         "                if (d_v2s > 0) {  // [DDOS-ETAPA1-D298]\n"
         "                    logger_->warn(\"[DDOS-V2] sin_estado={} en los últimos {} s: eventos sin victim_state (sniffer \"\n"
         "                                  \"antiguo o sin snapshot del lector); se aplica la etapa 1 antigua (ratio >= k_ratio)\",\n"
         "                                  d_v2s, secs);\n"
         "                }\n"
         "                summary_prev = s;\n                summary_last = now;\n", 1),
    ],
    JS: [
        ("k_ratio: número en [1.5, 50], defecto 3.0 = umbral de la etapa 1 sobre victim_rate_ratio (alineado con k_in de la histéresis del sniffer).",
         "k_ratio: número en [1.5, 50], defecto 3.0 = umbral de la etapa 1 sobre victim_rate_ratio (alineado con k_in de la histéresis del sniffer). "
         "[DDOS-ETAPA1-D298] La etapa 1 usa victim_state del sniffer: BAJO_PRESION pasa siempre, FRIO nunca, NORMAL con "
         "ratio >= k_ratio; un evento sin estado aplica la regla antigua y se avisa en el resumen [DDOS-V2] sin_estado.", 1),
    ],
    PT: [
        ('    std::printf("[DDOS-V2-PARITY] filas=%ld discrepancias=%ld\\n", n, bad);\n',
         PARITY + '    std::printf("[DDOS-V2-PARITY] filas=%ld discrepancias=%ld\\n", n, bad);\n', 1),
    ],
}

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_paso3.py --check | --apply")
    nuevos, errores = {}, []
    for f, cambios in CAMBIOS.items():
        txt = open(f).read()
        if MARCA in txt:
            errores.append(f"{f}: ya lleva la marca {MARCA}")
            continue
        for viejo, nuevo, n in cambios:
            c = txt.count(viejo)
            if c != n:
                errores.append(f"{f}: '{viejo.strip()[:70]}...' aparece {c} veces, se esperaban {n}")
            else:
                txt = txt.replace(viejo, nuevo)
        nuevos[f] = txt
    if JS in nuevos:
        try:
            json.loads(nuevos[JS])
        except json.JSONDecodeError as e:
            errores.append(f"{JS}: el resultado no es JSON valido: {e}")
    if errores:
        sys.exit("NO APLICABLE:\n  " + "\n  ".join(errores))
    if sys.argv[1] == "--check":
        print(f"CHECK OK: {len(nuevos)} ficheros; etapa 1 con estado; JSON valido; 7 casos en el test de paridad")
        return
    for f, t in nuevos.items():
        modo = os.stat(f).st_mode
        with open(f + ".tmp", "w") as o:
            o.write(t)
        os.chmod(f + ".tmp", modo)
    for f in nuevos:
        os.replace(f + ".tmp", f)
    print(f"APLICADO [{MARCA}] en {len(nuevos)} ficheros")

main()
