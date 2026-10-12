#!/usr/bin/env python3
"""[TIMEBASE-D295] Pieza 2 del contrato temporal v1 en el sniffer (Variant A).
Configuracion (sniffer.json -> ConfigManager -> g_config -> main.cpp -> RingBufferConsumer),
hilo del reloj, stamp_time_context en flujo / fast-alert / ventana ransomware, schema_version 32.
Atomico: todas las anclas deben casar exactamente una vez; el JSON resultante debe ser valido;
si algo falla no se escribe ningun fichero. Uso: --check | --apply"""
import json
import os
import sys
from pathlib import Path

MARCA = "[TIMEBASE-D295]"
F = {
    "cm_hpp": Path("sniffer/include/config_manager.hpp"),
    "ct_h": Path("sniffer/include/config_types.h"),
    "cm_cpp": Path("sniffer/src/userspace/config_manager.cpp"),
    "ct_cpp": Path("sniffer/src/userspace/config_types.cpp"),
    "main": Path("sniffer/src/userspace/main.cpp"),
    "rc_hpp": Path("sniffer/include/ring_consumer.hpp"),
    "rc_cpp": Path("sniffer/src/userspace/ring_consumer.cpp"),
    "json": Path("sniffer/config/sniffer.json"),
}

INC_DDOS = '#include "ddos_contract_v2.hpp"  // [DDOS-HYST-D291]\n'
INC_TB = '#include "timebase.hpp"  // [TIMEBASE-D295]\n'

PARSE = """// [TIMEBASE-D295] Seccion "timebase" del JSON (contrato temporal v1). Mismo criterio que la EWMA
// (DAY291): el JSON manda; si un campo falta, no es numerico o esta fuera de rango, se usa el
// DEFECTO validado (timebase.hpp) y se avisa con [CONFIG-DEFAULT]. El sniffer arranca siempre.
namespace {
int timebase_num(const Json::Value& j, const char* field, double def, double lo, double hi, double& out) {
    out = def;
    if (!j.isMember(field)) {
        std::cerr << "[CONFIG-DEFAULT] timebase." << field << " ausente -> defecto=" << def
                  << " rango=[" << lo << ", " << hi << "]" << std::endl;
        return 1;
    }
    const Json::Value& v = j[field];
    if (!v.isNumeric()) {
        std::cerr << "[CONFIG-DEFAULT] timebase." << field << " no es numerico -> defecto=" << def
                  << " rango=[" << lo << ", " << hi << "]" << std::endl;
        return 1;
    }
    const double x = v.asDouble();
    if (!(x >= lo && x <= hi)) {
        std::cerr << "[CONFIG-DEFAULT] timebase." << field << "=" << x << " fuera de rango -> defecto=" << def
                  << " rango=[" << lo << ", " << hi << "]" << std::endl;
        return 1;
    }
    out = x;
    return 0;
}

::argus::timebase::TimebaseParams parse_timebase(const Json::Value& tin) {
    namespace tb = ::argus::timebase;
    static const Json::Value kVacio(Json::objectValue);
    const Json::Value& t = tin.isObject() ? tin : kVacio;
    const tb::TimebaseParams d{};
    tb::TimebaseParams p{};
    int n = 0;
    double x = 0.0;
    n += timebase_num(t, "anchor_period_s", d.anchor_period_s, tb::kAnchorPeriodMin, tb::kAnchorPeriodMax, x);
    p.anchor_period_s = x;
    n += timebase_num(t, "step_threshold_s", d.step_threshold_s, tb::kStepThresholdMin, tb::kStepThresholdMax, x);
    p.step_threshold_s = x;
    n += timebase_num(t, "slew_window_s", d.slew_window_s, tb::kSlewWindowMin, tb::kSlewWindowMax, x);
    p.slew_window_s = x;
    n += timebase_num(t, "slew_ppm_threshold", d.slew_ppm_threshold, tb::kSlewPpmMin, tb::kSlewPpmMax, x);
    p.slew_ppm_threshold = x;
    n += timebase_num(t, "stepped_recent_s", d.stepped_recent_s, tb::kSteppedRecentMin, tb::kSteppedRecentMax, x);
    p.stepped_recent_s = x;
    if (!tb::params_ok(p)) {
        std::cerr << "[CONFIG-DEFAULT] regla slew_window_s >= anchor_period_s rota (anchor_period_s="
                  << p.anchor_period_s << ", slew_window_s=" << p.slew_window_s << ") -> defectos "
                  << d.anchor_period_s << " y " << d.slew_window_s << std::endl;
        p.anchor_period_s = d.anchor_period_s;
        p.slew_window_s = d.slew_window_s;
        ++n;
    }
    if (n > 0) {
        std::cerr << "[CONFIG-DEFAULT] " << n << " ajustes con valor por defecto en timebase: revisar sniffer.json"
                  << std::endl;
    }
    return p;
}
}  // namespace

"""

START_INIT = """
    // [TIMEBASE-D295] Primera lectura SINCRONA antes de lanzar hilos: sin ella los primeros eventos
    // saldrian con ancla 0 (epoch en 1970). El log muestra los parametros que llegaron al consumidor
    // (cadena sniffer.json -> ConfigManager -> g_config -> main.cpp -> aqui).
    {
        namespace tb = ::argus::timebase;
        tb::TimebaseParams p = config_.timebase;
        if (!tb::params_ok(p)) {
            std::cerr << "[CONFIG-DEFAULT] timebase invalido al llegar al consumidor -> todos los defectos" << std::endl;
            p = tb::TimebaseParams{};
        }
        tb_state_ = tb::TimebaseState(p);
        const auto r0 = tb::read_clocks();
        tb_state_.update(r0);
        tb_anchor_ns_.store(tb_state_.anchor_ns(), std::memory_order_relaxed);
        tb_clock_state_.store(static_cast<uint8_t>(tb::ClockState::Ok), std::memory_order_relaxed);
        tb_start_mono_ns_ = r0.mono_ns;
        tb_boot_id_ = tb::read_boot_id();
        std::cout << "[TIMEBASE] contrato v" << tb::kContractVersion << " activos: anchor_period_s=" << p.anchor_period_s
                  << " step_threshold_s=" << p.step_threshold_s << " slew_window_s=" << p.slew_window_s
                  << " slew_ppm_threshold=" << p.slew_ppm_threshold << " stepped_recent_s=" << p.stepped_recent_s
                  << " boot_id=" << tb_boot_id_ << " ancla_ns=" << tb_state_.anchor_ns() << std::endl;
        if (tb_boot_id_.size() != 36) {
            std::cerr << "[TIMEBASE] AVISO: boot_id no legible; el orden entre arranques no esta garantizado" << std::endl;
        }
    }
"""

THREAD_START = """    // [TIMEBASE-D295] hilo del reloj (ancla, CLOCK_STEP, CLOCK_SLEW)
    consumer_threads_.emplace_back(&RingBufferConsumer::timebase_loop, this);

"""

LOOP = """// [TIMEBASE-D295] Hilo del reloj: cada anchor_period_s relee REALTIME, MONOTONIC y MONOTONIC_RAW;
// publica el ancla y el estado (atomicos) y avisa de [CLOCK-STEP] y [CLOCK-SLEW]. Duerme en trozos
// de 100 ms para que la parada no espere un periodo entero.
void RingBufferConsumer::timebase_loop() {
    namespace tb = ::argus::timebase;
    using clk = std::chrono::steady_clock;
    const auto periodo = std::chrono::duration_cast<clk::duration>(
        std::chrono::duration<double>(tb_state_.params().anchor_period_s));
    const double umbral_ppm = tb_state_.params().slew_ppm_threshold;
    uint64_t saltos = 0;
    auto proximo = clk::now() + periodo;
    while (!should_stop_) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        const auto ahora = clk::now();
        if (ahora < proximo) continue;
        proximo += periodo;
        if (proximo < ahora) proximo = ahora + periodo;
        const auto r = tb::read_clocks();
        const auto ev = tb_state_.update(r);
        tb_anchor_ns_.store(tb_state_.anchor_ns(), std::memory_order_relaxed);
        tb_clock_state_.store(static_cast<uint8_t>(tb_state_.state_at(r.mono_ns)), std::memory_order_relaxed);
        if (ev.stepped) {
            ++saltos;
            std::cerr << "[CLOCK-STEP] el reloj de pared salto " << ev.step_delta_s
                      << " s (REALTIME-MONOTONIC); ancla nueva; saltos desde el arranque=" << saltos << std::endl;
        }
        if (ev.slew_measured && tb_state_.slewing()) {
            std::cerr << "[CLOCK-SLEW] " << (ev.slewing_changed ? "INICIO" : "sigue") << " ppm=" << ev.slew_ppm
                      << " (umbral " << umbral_ppm << "): las duraciones en MONOTONIC no son fiables" << std::endl;
        } else if (ev.slew_measured && ev.slewing_changed) {
            std::cerr << "[CLOCK-SLEW] FIN ppm=" << ev.slew_ppm << std::endl;
        }
    }
}

"""

STAMP = """// [TIMEBASE-D295] Contrato temporal v1: estampa TimeContext y event_timestamp (= epoch derivado =
// mono_ns + ancla) justo antes de serializar. Mismo codigo para flujo, fast-alert y ventana.
// sniffer_send_mono_ns = instante de serializacion (entrada en send_queue_), no el envio por socket.
void RingBufferConsumer::stamp_time_context(protobuf::NetworkSecurityEvent& ev, uint64_t mono_ns) {
    namespace tb = ::argus::timebase;
    const int64_t ancla = tb_anchor_ns_.load(std::memory_order_relaxed);
    const uint64_t epoch = tb::epoch_ns(mono_ns, ancla);
    auto* ts = ev.mutable_event_timestamp();
    ts->set_seconds(static_cast<int64_t>(epoch / 1000000000ULL));
    ts->set_nanos(static_cast<int32_t>(epoch % 1000000000ULL));
    auto* tc = ev.mutable_time_context();
    tc->set_mono_ns(mono_ns);
    tc->set_boot_id(tb_boot_id_);
    tc->set_producer_start_mono_ns(tb_start_mono_ns_);
    tc->set_producer_seq(tb_seq_.fetch_add(1, std::memory_order_relaxed) + 1);
    tc->set_wall_anchor_ns(ancla);
    tc->set_clock_state(static_cast<protobuf::ClockState>(tb_clock_state_.load(std::memory_order_relaxed)));
    tc->set_time_contract_version(tb::kContractVersion);
    tc->set_sniffer_send_mono_ns(static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count()));
}

"""

MIEMBROS = """    // [TIMEBASE-D295] contrato temporal v1: el hilo del reloj escribe tb_state_; el resto lee atomicos.
    // tb_start_mono_ns_ y tb_boot_id_ se fijan en start() antes de lanzar ningun hilo.
    ::argus::timebase::TimebaseState tb_state_{};
    std::atomic<int64_t> tb_anchor_ns_{0};
    std::atomic<uint8_t> tb_clock_state_{0};
    std::atomic<uint64_t> tb_seq_{0};
    uint64_t tb_start_mono_ns_{0};
    std::string tb_boot_id_;
"""

SECCION = """  "timebase": {
    "_doc": "[TIMEBASE-D295] Contrato temporal v1 (docs/timebase/contrato_temporal_day295.md). Base interna CLOCK_MONOTONIC; event_timestamp = mono_ns + ancla (REALTIME - MONOTONIC). anchor_period_s [0,1-60]: cada cuanto se relee el ancla. step_threshold_s [0,001-10]: cambio del ancla que se registra como [CLOCK-STEP]. slew_window_s [1-300], >= anchor_period_s: ventana para medir MONOTONIC frente a MONOTONIC_RAW. slew_ppm_threshold [1000-500000]: |ppm| por encima = correccion gradual, aviso [CLOCK-SLEW] y clock_state SLEWING. stepped_recent_s [1-3600]: tiempo en clock_state STEPPED tras un salto. Si un campo falta, no es numerico o esta fuera de rango: defecto + [CONFIG-DEFAULT]; el sniffer arranca igual. Valores de LABORATORIO medidos DAY295: base -1876 ppm, correccion gradual +81300 ppm, R-M estable < 0,00001 s en reposo. La linea [TIMEBASE] del log muestra los valores activos.",
    "anchor_period_s": 1.0,
    "step_threshold_s": 0.05,
    "slew_window_s": 10.0,
    "slew_ppm_threshold": 10000.0,
    "stepped_recent_s": 60.0
  },
"""

MONO_AHORA = ("static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(\n"
              "            std::chrono::steady_clock::now().time_since_epoch()).count())")

# (fichero, tipo, ancla, texto): tipo after | before | replace
EDITS = [
    ("cm_hpp", "after", INC_DDOS, INC_TB),
    ("cm_hpp", "after", "    MLDefenderConfig ml_defender;\n",
     "    ::argus::timebase::TimebaseParams timebase{};  // [TIMEBASE-D295]\n"),
    ("ct_h", "after", INC_DDOS, INC_TB),
    ("ct_h", "after", "    } kernel_space;\n",
     "\n    ::argus::timebase::TimebaseParams timebase{};  // [TIMEBASE-D295]\n"),
    ("cm_cpp", "replace",
     "namespace sniffer {\n\nstd::unique_ptr<SnifferConfig> ConfigManager::load_from_file(",
     "namespace sniffer {\n\n" + PARSE + "std::unique_ptr<SnifferConfig> ConfigManager::load_from_file("),
    ("cm_cpp", "after",
     '    config->kernel_space = parse_kernel_space(root.get("kernel_space", Json::Value{}));\n',
     '    config->timebase = parse_timebase(root.get("timebase", Json::Value{}));  // [TIMEBASE-D295]\n'),
    ("ct_cpp", "after",
     "        config.kernel_space.ddos_victim_ewma = sniffer_config->kernel_space.ddos_victim_ewma;  // [DDOS-HYST-D291]\n",
     "        config.timebase = sniffer_config->timebase;  // [TIMEBASE-D295]\n"),
    ("main", "after", "        sniffer_config.cluster_name = g_config.cluster_name;\n",
     "        sniffer_config.timebase = g_config.timebase;  // [TIMEBASE-D295]\n"),
    ("rc_hpp", "after", '#include "ddos_victim_board.hpp"  // [DDOS-VWIN-D279:RC-INC]\n', INC_TB),
    ("rc_hpp", "after", "    void zmq_sender_loop();\n",
     "    void timebase_loop();  // [TIMEBASE-D295]\n"
     "    void stamp_time_context(protobuf::NetworkSecurityEvent& ev, uint64_t mono_ns);  // [TIMEBASE-D295]\n"),
    ("rc_hpp", "after", "    std::atomic<bool> initialized_{false};\n", MIEMBROS),
    ("rc_cpp", "after", "    should_stop_ = false;\n    running_ = true;\n    active_consumers_ = 0;\n", START_INIT),
    ("rc_cpp", "replace", "1);  // +1 for stats thread\n", "2);  // +1 stats, +1 reloj [TIMEBASE-D295]\n"),
    ("rc_cpp", "before", "    // Start statistics display thread\n", THREAD_START),
    ("rc_cpp", "before", "void RingBufferConsumer::stats_display_loop() {\n", LOOP),
    ("rc_cpp", "before", "void RingBufferConsumer::stamp_victim_window(protobuf::NetworkSecurityEvent& ev,\n", STAMP),
    ("rc_cpp", "after", "        populate_protobuf_event(event, proto_event, 0, &queued);  // [DDOS-SNAP-D290]\n",
     "        stamp_time_context(proto_event, event.timestamp);  // [TIMEBASE-D295] flujo: reloj del kernel\n"),
    ("rc_cpp", "after", "        stamp_victim_window(alert, event);  // [DDOS-VWIN-D279:STAMP-FAST]\n",
     "        stamp_time_context(alert, event.timestamp);  // [TIMEBASE-D295] fast-alert: reloj del kernel\n"),
    ("rc_cpp", "after", "        event.set_originating_node_id(config_.node_id);\n",
     "        stamp_time_context(event, " + MONO_AHORA + ");  // [TIMEBASE-D295] ventana: instante de emision\n"),
    ("rc_cpp", "replace", "    proto_event.set_schema_version(31);\n",
     "    proto_event.set_schema_version(32);  // [TIMEBASE-D295] contrato temporal v1\n"),
    ("json", "replace", '  },\n  "user_space": {\n', '  },\n' + SECCION + '  "user_space": {\n'),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(2)
    orig = {k: p.read_text(encoding="utf-8") for k, p in F.items()}
    con_marca = [k for k in F if MARCA in orig[k]]
    if len(con_marca) == len(F):
        print("YA APLICADO: la marca esta en los 8 ficheros")
        sys.exit(0)
    if con_marca:
        print(f"ABORTA: estado mixto, marca ya presente en {[str(F[k]) for k in con_marca]}")
        sys.exit(1)
    textos = dict(orig)
    errores = []
    for clave, tipo, ancla, texto in EDITS:
        t = textos[clave]
        n = t.count(ancla)
        if n != 1:
            errores.append(f"{F[clave]}: ancla encontrada {n} veces: {ancla[:80]!r}")
            continue
        if tipo == "after":
            t = t.replace(ancla, ancla + texto, 1)
        elif tipo == "before":
            t = t.replace(ancla, texto + ancla, 1)
        else:
            t = t.replace(ancla, texto, 1)
        textos[clave] = t
    if errores:
        print("ABORTA (no se ha escrito nada):")
        for e in errores:
            print("  " + e)
        sys.exit(1)
    try:
        cfg = json.loads(textos["json"])
        tbj = cfg["timebase"]
        if tbj["anchor_period_s"] != 1.0 or tbj["slew_ppm_threshold"] != 10000.0:
            raise ValueError("valores de timebase inesperados")
    except Exception as e:  # noqa: BLE001
        print(f"ABORTA (no se ha escrito nada): sniffer.json resultante invalido: {e}")
        sys.exit(1)
    sin_marca = [str(F[k]) for k in F if MARCA not in textos[k]]
    if sin_marca:
        print(f"ABORTA: tras aplicar faltan marcas en {sin_marca}")
        sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"CHECK OK: {len(EDITS)} ediciones en {len(F)} ficheros; sniffer.json valido con seccion timebase")
        return
    for k, p in F.items():
        tmp = p.with_name(p.name + ".tmp_d295")
        tmp.write_text(textos[k], encoding="utf-8")
        os.replace(tmp, p)
        print(f"APLICADO: {p} ({len(orig[k])} -> {len(textos[k])} bytes)")


if __name__ == "__main__":
    main()
