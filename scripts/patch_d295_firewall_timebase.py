#!/usr/bin/env python3
"""[TIMEBASE-D295] Firewall: contrato temporal v1.
- Reloj de la sombra = time_context.mono_ns / 1e9 (segundos enteros de CLOCK_MONOTONIC del sniffer).
- time_context ausente o anomalo (8 causas): NO entra en ninguna ventana; [TIMEBASE-ANOMALIA] con detalle limitado
  por causa y periodo (anomalias_detalle_max) + recuento en el resumen periodico.
- Retraso sniffer->firewall (D17): media y maximo en el resumen [TIMEBASE].
- hold_s -> hold_windows (ventanas), con aviso si un JSON antiguo trae hold_s.
Atomico: todas las anclas deben casar exactamente una vez; firewall.json resultante valido; si algo falla no se escribe
nada. Uso: --check | --apply"""
import json
import os
import sys
from pathlib import Path

MARCA = "[TIMEBASE-D295]"
F = {
    "pol": Path("firewall-acl-agent/include/firewall/ddos_shadow_policy.hpp"),
    "cl": Path("firewall-acl-agent/src/core/config_loader.cpp"),
    "main": Path("firewall-acl-agent/src/main.cpp"),
    "json": Path("firewall-acl-agent/config/firewall.json"),
    "zh": Path("firewall-acl-agent/include/firewall/zmq_subscriber.hpp"),
    "zc": Path("firewall-acl-agent/src/api/zmq_subscriber.cpp"),
}

MIEMBROS = """    // [TIMEBASE-D295] validacion de time_context y retraso sniffer->firewall (contrato temporal v1).
    // Todo evento anomalo queda FUERA de las ventanas: puede ser un fallo nuestro, un productor sin contrato o un
    // componente comprometido; se registra para estudiarlo, nunca se castiga a la IP del paquete.
    static constexpr int kTbCausas = 8;
    static constexpr const char* kTbCausaNombre[kTbCausas] = {
        "sin_time_context", "version", "mono_cero", "boot_id", "futuro",
        "retraso_otro_boot", "retraso_negativo", "retraso_absurdo"};
    std::string tb_boot_id_propio_;
    uint64_t tb_anom_[kTbCausas] = {};
    uint64_t tb_detalle_[kTbCausas] = {};
    uint64_t tb_lag_n_ = 0;
    double tb_lag_suma_ms_ = 0.0;
    double tb_lag_max_ms_ = 0.0;

    void tb_detallar(int causa, const ::protobuf::NetworkSecurityEvent& ev, const std::string& valor) {
        ++tb_anom_[causa];
        if (tb_detalle_[causa] >= static_cast<uint64_t>(config_.ddos_shadow.anomalias_detalle_max)) return;
        ++tb_detalle_[causa];
        const auto& nf = ev.network_features();
        std::cerr << "[TIMEBASE-ANOMALIA] causa=" << kTbCausaNombre[causa] << " event_id=" << ev.event_id()
                  << " nodo=" << ev.originating_node_id() << " kind=" << static_cast<int>(ev.event_kind())
                  << " src=" << nf.source_ip() << " dst=" << nf.destination_ip()
                  << (valor.empty() ? "" : " ") << valor << std::endl;
    }

    // Devuelve true si el evento puede entrar en las ventanas; mide el retraso de los validos.
    bool tb_validar_time_context(const ::protobuf::NetworkSecurityEvent& ev) {
        namespace tl = ::mldefender::firewall::timebase_lite;
        if (tb_boot_id_propio_.empty()) tb_boot_id_propio_ = tl::read_boot_id();
        const uint64_t ahora = tl::mono_now_ns();
        if (!ev.has_time_context()) {
            tb_detallar(0, ev, "");
            return false;
        }
        const auto& tc = ev.time_context();
        if (tc.time_contract_version() != 1) {
            tb_detallar(1, ev, "version=" + std::to_string(tc.time_contract_version()));
            return false;
        }
        if (tc.mono_ns() == 0) {
            tb_detallar(2, ev, "");
            return false;
        }
        if (tc.boot_id().size() != 36) {
            tb_detallar(3, ev, "boot_id='" + tc.boot_id().substr(0, 40) + "'");
            return false;
        }
        if (tc.boot_id() != tb_boot_id_propio_) {
            tb_detallar(5, ev, "boot_id_evento=" + tc.boot_id() + " boot_id_firewall=" + tb_boot_id_propio_);
            return false;
        }
        if (tc.mono_ns() > ahora) {
            tb_detallar(4, ev, "mono_ns=" + std::to_string(tc.mono_ns()) + " ahora=" + std::to_string(ahora));
            return false;
        }
        const uint64_t enviado = tc.sniffer_send_mono_ns();
        if (enviado > ahora) {
            tb_detallar(6, ev, "sniffer_send_mono_ns=" + std::to_string(enviado) + " ahora=" + std::to_string(ahora));
            return false;
        }
        if (enviado != 0) {
            const double ms = static_cast<double>(ahora - enviado) / 1e6;
            if (ms > static_cast<double>(config_.ddos_shadow.lag_max_valid_s) * 1000.0) {
                tb_detallar(7, ev, "retraso_ms=" + std::to_string(ms));
                return false;
            }
            ++tb_lag_n_;
            tb_lag_suma_ms_ += ms;
            if (ms > tb_lag_max_ms_) tb_lag_max_ms_ = ms;
        }
        return true;
    }
"""

RESUMEN_TB = """                {  // [TIMEBASE-D295] retraso sniffer->firewall y anomalias de tiempo del periodo
                    uint64_t total = 0;
                    std::ostringstream o;
                    o << "[TIMEBASE] resumen: retraso_sniffer_fw n=" << tb_lag_n_ << " media_ms="
                      << (tb_lag_n_ ? tb_lag_suma_ms_ / static_cast<double>(tb_lag_n_) : 0.0)
                      << " max_ms=" << tb_lag_max_ms_ << " anomalias:";
                    for (int i = 0; i < kTbCausas; ++i) {
                        o << " " << kTbCausaNombre[i] << "=" << tb_anom_[i];
                        total += tb_anom_[i];
                        tb_anom_[i] = 0;
                        tb_detalle_[i] = 0;
                    }
                    std::cout << o.str() << std::endl;
                    if (total > 0) {
                        std::cerr << "[TIMEBASE-ANOMALIA] " << total
                                  << " eventos con tiempo anomalo en el periodo, fuera de las ventanas: " << o.str()
                                  << std::endl;
                    }
                    tb_lag_n_ = 0;
                    tb_lag_suma_ms_ = 0.0;
                    tb_lag_max_ms_ = 0.0;
                }
"""

TS_VIEJO = """        const int64_t ts_s = static_cast<int64_t>(event.event_timestamp().seconds());
        // [DDOS-SHADOW-RELOJ-D293] un solo reloj: el de los eventos de FLUJO (monotónico desde el arranque). Otros
        // tipos de evento llegan con event_timestamp en epoch (DEBT-EVENT-TIMESTAMP-TIMEBASE-001) y no lo mueven.
        const bool es_flujo = (event.event_kind() == protobuf::EVENT_KIND_FLOW);
"""
TS_NUEVO = """        // [TIMEBASE-D295] reloj de la sombra = time_context.mono_ns / 1e9 (segundos enteros de CLOCK_MONOTONIC del
        // sniffer; 1 ventana = 1 s, inmune a saltos del reloj de pared). Un time_context ausente o anomalo NO entra en
        // ninguna ventana (ver tb_validar_time_context). Siguen contando solo los eventos de FLUJO (D293).
        const bool tc_ok = tb_validar_time_context(event);
        const int64_t ts_s = tc_ok ? static_cast<int64_t>(event.time_context().mono_ns() / 1000000000ULL) : 0;
        const bool es_flujo = tc_ok && (event.event_kind() == protobuf::EVENT_KIND_FLOW);
"""

EDITS = [
    # politica: hold_s -> hold_windows; parametros nuevos
    ("pol", "replace",
     "// w - última_positiva >= hold_s (y se vacía la cola). Solo REGISTRA: no toca ipset ni iptables.\n",
     "// w - última_positiva >= hold_windows (y se vacía la cola). Solo REGISTRA: no toca ipset ni iptables.\n"
     "// [TIMEBASE-D295] desde el contrato temporal v1 la marca es time_context.mono_ns / 1e9 (segundos enteros de\n"
     "// CLOCK_MONOTONIC del sniffer): 1 ventana = 1 s y un salto del reloj de pared no mueve las ventanas.\n"),
    ("pol", "replace", "    int hold_s = 30;\n",
     "    int hold_windows = 30;  // [TIMEBASE-D295] ventanas (1 ventana = 1 s de CLOCK_MONOTONIC) sin positiva para FIN\n"),
    ("pol", "after", "    int resumen_s = 10;  // [DDOS-SHADOW-OBS-D293] segundos entre resúmenes (reloj de pared)\n",
     "    int lag_max_valid_s = 600;       // [TIMEBASE-D295] retraso sniffer->firewall maximo valido (s)\n"
     "    int anomalias_detalle_max = 10;  // [TIMEBASE-D295] anomalias detalladas por causa y periodo de resumen\n"),
    ("pol", "replace", "static_cast<int64_t>(p_.hold_s)", "static_cast<int64_t>(p_.hold_windows)"),
    ("pol", "replace", "w - s.last_pos >= p_.hold_s)", "w - s.last_pos >= p_.hold_windows)"),
    # cargador
    ("cl", "replace", "enabled=true m=5 k=3 n=5 hold_s=30\\n", "enabled=true m=5 k=3 n=5 hold_windows=30\\n"),
    ("cl", "replace", '            d.hold_s = get_int("hold_s", 30, 1, 3600);\n',
     '            if (s.isMember("hold_s")) {  // [TIMEBASE-D295]\n'
     '                std::cerr << "[CONFIG-DEFAULT] ddos_shadow.hold_s esta obsoleto: renombrado a hold_windows "\n'
     '                             "(ventanas de 1 s de CLOCK_MONOTONIC del sniffer); se ignora hold_s\\n";\n'
     '            }\n'
     '            d.hold_windows = get_int("hold_windows", 30, 1, 3600);  // [TIMEBASE-D295]\n'),
    ("cl", "after", '            d.resumen_s = get_int("resumen_s", 10, 1, 3600);  // [DDOS-SHADOW-OBS-D293]\n',
     '            d.lag_max_valid_s = get_int("lag_max_valid_s", 600, 1, 86400);  // [TIMEBASE-D295]\n'
     '            d.anomalias_detalle_max = get_int("anomalias_detalle_max", 10, 0, 1000);  // [TIMEBASE-D295]\n'),
    # main: linea de arranque
    ("main", "replace",
     '                  << " hold_s=" << config.ddos_shadow.hold_s << " resumen_s=" << config.ddos_shadow.resumen_s\n',
     '                  << " hold_windows=" << config.ddos_shadow.hold_windows << " resumen_s=" << config.ddos_shadow.resumen_s\n'
     '                  << " lag_max_valid_s=" << config.ddos_shadow.lag_max_valid_s  // [TIMEBASE-D295]\n'
     '                  << " anomalias_detalle_max=" << config.ddos_shadow.anomalias_detalle_max\n'),
    # JSON
    ("json", "replace", "Ventanas de 1 s por marca de tiempo del evento.",
     "Ventanas de 1 s por time_context.mono_ns del evento (contrato temporal v1, [TIMEBASE-D295]): 1 ventana = 1 s de "
     "CLOCK_MONOTONIC del sniffer, inmune a saltos del reloj de pared; un evento con time_context ausente o anomalo no "
     "entra en ninguna ventana y se registra como [TIMEBASE-ANOMALIA]."),
    ("json", "replace", "hold_s: entero en [1, 3600], segundos sin positiva para FIN (defecto 30).",
     "hold_windows: entero en [1, 3600], VENTANAS sin positiva para FIN (defecto 30)."),
    ("json", "replace", "resumen (defecto 10) [DDOS-SHADOW-OBS-D293].",
     "resumen (defecto 10) [DDOS-SHADOW-OBS-D293]. lag_max_valid_s: entero en [1, 86400], retraso sniffer->firewall "
     "(mismo nodo y boot_id) por encima del cual el evento es anomalo y no cuenta (defecto 600). anomalias_detalle_max: "
     "entero en [0, 1000], eventos anomalos detallados en el log por causa y periodo de resumen; el resto solo se cuenta "
     "(defecto 10)."),
    ("json", "replace", '    "hold_s": 30,\n    "resumen_s": 10\n  },\n',
     '    "hold_windows": 30,\n    "resumen_s": 10,\n    "lag_max_valid_s": 600,\n    "anomalias_detalle_max": 10\n  },\n'),
    # subscriber
    ("zh", "after", '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n',
     '#include "firewall/timebase_lite.hpp"  // [TIMEBASE-D295]\n'),
    ("zh", "after", "    bool sombra_primer_drop_ = false;\n", MIEMBROS),
    ("zc", "replace", TS_VIEJO, TS_NUEVO),
    ("zc", "after", '                          << " victimas_activas=" << ddos_shadow_.victims() << std::endl;\n',
     RESUMEN_TB),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(2)
    if not Path("firewall-acl-agent/include/firewall/timebase_lite.hpp").exists():
        print("ABORTA: falta firewall-acl-agent/include/firewall/timebase_lite.hpp (paso 1)")
        sys.exit(1)
    orig = {k: p.read_text(encoding="utf-8") for k, p in F.items()}
    con_marca = [k for k in F if MARCA in orig[k]]
    if len(con_marca) == len(F):
        print("YA APLICADO")
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
            errores.append(f"{F[clave]}: ancla encontrada {n} veces: {ancla[:90]!r}")
            continue
        if tipo == "after":
            t = t.replace(ancla, ancla + texto, 1)
        else:
            t = t.replace(ancla, texto, 1)
        textos[clave] = t
    if errores:
        print("ABORTA (no se ha escrito nada):")
        for e in errores:
            print("  " + e)
        sys.exit(1)
    try:
        ds = json.loads(textos["json"])["ddos_shadow"]
        if "hold_s" in ds or ds["hold_windows"] != 30 or ds["lag_max_valid_s"] != 600 or ds["anomalias_detalle_max"] != 10:
            raise ValueError("claves de ddos_shadow inesperadas")
    except Exception as e:  # noqa: BLE001
        print(f"ABORTA (no se ha escrito nada): firewall.json resultante invalido: {e}")
        sys.exit(1)
    if "hold_s" in textos["pol"].replace("hold_windows", ""):
        print("ABORTA: queda hold_s en la politica")
        sys.exit(1)
    sin_marca = [str(F[k]) for k in F if MARCA not in textos[k]]
    if sin_marca:
        print(f"ABORTA: tras aplicar faltan marcas en {sin_marca}")
        sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"CHECK OK: {len(EDITS)} ediciones en {len(F)} ficheros; firewall.json valido (hold_windows, lag_max_valid_s, "
              "anomalias_detalle_max)")
        return
    for k, p in F.items():
        tmp = p.with_name(p.name + ".tmp_d295fw")
        tmp.write_text(textos[k], encoding="utf-8")
        os.replace(tmp, p)
        print(f"APLICADO: {p} ({len(orig[k])} -> {len(textos[k])} bytes)")


if __name__ == "__main__":
    main()
