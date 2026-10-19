#!/usr/bin/env python3
# DAY302 tanda b2-2 [DDOS-MITIGACION-B2-D302]: cableado de la mitigacion ddos_v2 en el suscriptor y main.
# Latido flush_si_toca en receive_loop; decidir -> bloquear/renovar_episodio tras add_drop; D1 (registro
# DRY_RUN_BLOCK | BLOCKED | BLOCK_RENEWED) y D2 (dry_run: solo resumen; activo: una linea por accion);
# resumen propio + purga + CONFIG-AVISO periodico; pasos 5-8 anotados como inalcanzables.
# Atomico: todas las anclas unicas antes de escribir. Uso: --check | --apply
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "firewall-acl-agent"
MARCA = "[DDOS-MITIGACION-B2-D302]"

P_SHPP = FW / "include/firewall/zmq_subscriber.hpp"
P_SCPP = FW / "src/api/zmq_subscriber.cpp"
P_MAIN = FW / "src/main.cpp"

# ---------------------------------------------------------------- zmq_subscriber.hpp
S1_OLD = '#include "firewall/ddos_protegidos.hpp"  // [PROTEGIDOS-D300]\n'
S1_NEW = S1_OLD + '#include "firewall/ddos_mitigacion.hpp"  // [DDOS-MITIGACION-B2-D302]\n'

S2_OLD = "        ::mldefender::firewall::RangosProtegidos ddos_protegidos;  ///< [PROTEGIDOS-D300] rangos protegidos\n"
S2_NEW = S2_OLD + r'''        ::mldefender::firewall::DdosMitigacionParams ddos_mitigacion;  ///< [DDOS-MITIGACION-B2-D302] mitigacion real
        std::vector<uint32_t> ddos_escalones_cortos;  ///< [DDOS-MITIGACION-B2-D302] escalones de prueba (aviso periodico)
        bool dry_run = true;  ///< [DDOS-MITIGACION-B2-D302] copia de operation.dry_run (1.a llave); defecto el seguro
'''

S3_OLD = "    uint64_t prot_detalle_ = 0;      // [PROTEGIDOS-D300] lineas de detalle del periodo (tope anomalias_detalle_max)\n"
S3_NEW = S3_OLD + r'''    ::mldefender::firewall::DdosMitigacion ddos_mitigacion_{config_.ddos_mitigacion};  ///< [DDOS-MITIGACION-B2-D302]
    // [DDOS-MITIGACION-B2-D302] contadores del periodo de resumen y acumulados (solo hilo receptor)
    uint64_t mit_bloquear_ = 0;
    uint64_t mit_renovar_ = 0;
    uint64_t mit_esperar_ = 0;
    uint64_t mit_protegido_ = 0;
    uint64_t mit_invalida_ = 0;
    uint64_t mit_bloquear_total_ = 0;
    uint64_t mit_renovar_total_ = 0;
'''

# ---------------------------------------------------------------- zmq_subscriber.cpp
Z1_OLD = r'''            TRACK_OPERATION("zmq_receive");

            // Receive message
'''
Z1_NEW = r'''            TRACK_OPERATION("zmq_receive");

            // [DDOS-MITIGACION-B2-D302] latido: flush por tiempo aunque no lleguen IPs nuevas (medido DAY302:
            // should_flush solo se evaluaba al anadir; un bloqueo solo en la cola podia no llegar nunca al ipset)
            processor_.flush_si_toca();

            // Receive message
'''

Z2_OLD = r'''                    prot_detalle_ = 0;
                }
'''
Z2_NEW = Z2_OLD + r'''                {   // [DDOS-MITIGACION-B2-D302] resumen de la mitigacion (linea propia; en dry_run es la unica salida, D2)
                    const std::size_t purgadas = ddos_mitigacion_.purgar(
                        [this](const std::string& d, uint32_t p) { return ddos_shadow_.en_episodio(d, p); });
                    mit_bloquear_total_ += mit_bloquear_;
                    mit_renovar_total_ += mit_renovar_;
                    std::cout << "[DDOS-MITIGACION] resumen: modo="
                              << (!config_.ddos_mitigacion.habilitada ? "deshabilitada"
                                  : (config_.dry_run ? "dry_run" : "ACTIVA"))
                              << " bloquear=" << mit_bloquear_ << " renovar=" << mit_renovar_
                              << " esperar=" << mit_esperar_ << " rechazo_protegido=" << mit_protegido_
                              << " rechazo_ip_invalida=" << mit_invalida_
                              << " bloquear_total=" << mit_bloquear_total_ << " renovar_total=" << mit_renovar_total_
                              << " victimas_seguidas=" << ddos_mitigacion_.victimas_seguidas()
                              << " origenes_seguidos=" << ddos_mitigacion_.origenes_seguidos()
                              << " desbordes=" << ddos_mitigacion_.desbordes() << " purgadas=" << purgadas
                              << " barrera_total=" << processor_.rechazos_protegidos() << std::endl;
                    if (config_.ddos_mitigacion.habilitada && !config_.ddos_escalones_cortos.empty()) {
                        std::ostringstream c;
                        for (std::size_t i = 0; i < config_.ddos_escalones_cortos.size(); ++i) {
                            c << (i ? ", " : "") << config_.ddos_escalones_cortos[i];
                        }
                        std::cerr << "[CONFIG-AVISO] ddos_mitigacion: escalones por debajo de aviso_castigo_corto_sec="
                                  << config_.ddos_mitigacion.aviso_castigo_corto_sec << " s: [" << c.str()
                                  << "] = castigo SOLO DE PRUEBAS, no de produccion" << std::endl;
                    }
                    mit_bloquear_ = 0;
                    mit_renovar_ = 0;
                    mit_esperar_ = 0;
                    mit_protegido_ = 0;
                    mit_invalida_ = 0;
                }
'''

Z3_OLD = r'''        // [DDOS-SHADOW-D293] en este PR NO se bloquea nada: los pasos 5-8 (bloqueo por IP de origen, ipset, registro
        // BLOCKED) no se ejecutan. La mitigación real será por víctima (DEBT-FIREWALL-PER-VICTIM-001).
        return;
'''
Z3_NEW = r'''        {   // [DDOS-MITIGACION-B2-D302] mitigacion real por ORIGEN con su victima en episodio. Doble llave:
            // operation.dry_run (config_.dry_run) + ddos_mitigacion.habilitada (decidir devuelve NADA si es false).
            // Los protegidos ya han salido arriba (ALERTA_PROTEGIDO); la barrera de BatchProcessor es la 2.a y 3.a puerta.
            // D2: en dry_run, solo contadores (resumen); activo, una linea por accion. D1: registro con set y timeout reales.
            const std::string& dst = nf2.destination_ip();
            const uint32_t proto = static_cast<uint32_t>(nf2.protocol_number());
            const std::string& src = nf2.source_ip();
            using Accion = ::mldefender::firewall::AccionMitigacion;
            using Estado = ::mldefender::firewall::ResultadoEpisodio::Estado;
            const Accion accion = ddos_mitigacion_.decidir(dst, proto, src, ddos_shadow_.en_episodio(dst, proto));
            if (accion == Accion::ESPERAR) {
                ++mit_esperar_;
            } else if (accion == Accion::BLOQUEAR || accion == Accion::RENOVAR) {
                const bool bloquear = (accion == Accion::BLOQUEAR);
                const auto r = bloquear ? processor_.bloquear_episodio(src) : processor_.renovar_episodio(src);
                const char* nombre = bloquear ? "BLOQUEAR" : "RENOVAR";
                if (r.estado == Estado::ENCOLADO) {
                    ++(bloquear ? mit_bloquear_ : mit_renovar_);
                    const std::string set = processor_.get_config().blacklist_ipset;
                    // -1 = timeout por defecto del set (reincidencia deshabilitada); nunca 0 (= permanente en ipset)
                    const int t = r.timeout_sec ? static_cast<int>(*r.timeout_sec) : -1;
                    if (!config_.dry_run) {
                        std::cout << "[DDOS-MITIGACION] " << nombre << " origen=" << src << " victima=" << dst
                                  << " proto=" << proto << " timeout_s="
                                  << (r.timeout_sec ? std::to_string(*r.timeout_sec) : std::string("defecto_del_set"))
                                  << " strikes=" << r.strikes << " set=" << set << " ts_s=" << ts_s
                                  << " evento=" << event.event_id() << std::endl;
                    }
                    if (bloquear || !config_.dry_run) {  // D1+D2: en dry_run solo BLOQUEAR (una vez por origen y episodio)
                        const std::string accion_reg =
                            config_.dry_run ? "DRY_RUN_BLOCK" : (bloquear ? "BLOCKED" : "BLOCK_RENEWED");
                        try {
                            BlockedEvent ev = create_blocked_event_from_proto(event, accion_reg, set, t);
                            if (logger_ && logger_->log_blocked_event(ev)) {
                                stats_.events_logged++;
                            }
                            if (logger_ && hmac_key_.has_value()) {
                                logger_->append_csv_log(ev, hmac_key_.value());
                            }
                        } catch (const std::exception& e) {
                            FIREWALL_LOG_ERROR("[DDOS-MITIGACION] fallo al registrar la accion", "error", e.what(),
                                "ip", src);
                        }
                    }
                } else {
                    ++(r.estado == Estado::PROTEGIDO ? mit_protegido_ : mit_invalida_);
                    if (!config_.dry_run) {
                        std::cerr << "[DDOS-MITIGACION] RECHAZADO " << nombre << " origen=" << src
                                  << (r.estado == Estado::PROTEGIDO ? " motivo=protegido" : " motivo=ip_invalida")
                                  << " victima=" << dst << " proto=" << proto << " evento=" << event.event_id()
                                  << std::endl;
                    }
                }
            }
        }
        return;
'''

Z4_OLD = r'''    std::string ipset_name = "ml_defender_blacklist_test";
    int timeout_sec = 300;  // 5 minutes default
'''
Z4_NEW = r'''    // [DDOS-MITIGACION-B2-D302] INALCANZABLE: la rama ddos_v2 de arriba hace return en todos los casos. Nombre de set
    // y timeouts fijos (300/600/3600) que solo iban al registro. Se retira en su propia PR (DEBT-FW-LEGACY-STEPS-001).
''' + Z4_OLD

# ---------------------------------------------------------------- main.cpp
M1_OLD = "    processor.set_recidivism_config(recidivism_config);  // RECIDIVISM-D276\n"
M1_NEW = M1_OLD + "    processor.set_rangos_protegidos(config.ddos_protegidos);  // [DDOS-MITIGACION-B2-D302] barrera (2 puertas)\n"

M2_OLD = "        zmq_config.ddos_protegidos = config.ddos_protegidos;  // [PROTEGIDOS-D300]\n"
M2_NEW = M2_OLD + r'''        zmq_config.ddos_mitigacion = config.ddos_mitigacion;  // [DDOS-MITIGACION-B2-D302]
        zmq_config.dry_run = config.operation.dry_run;        // [DDOS-MITIGACION-B2-D302] 1.a llave
        zmq_config.ddos_escalones_cortos = ::mldefender::firewall::escalones_cortos(
            recidivism_config.strike_durations_sec, static_cast<uint32_t>(config.ddos_mitigacion.aviso_castigo_corto_sec));
        std::cout << "[DDOS-MITIGACION] modo: "
                  << (!config.ddos_mitigacion.habilitada ? "DESHABILITADA (sombra pura, no se llama a la mitigacion)"
                      : (config.operation.dry_run ? "DRY_RUN (simula; solo resumen periodico)"
                                                  : "ACTIVA (bloquea en el ipset; una linea por accion)"))
                  << std::endl;
'''

EDITS = [
    (P_SHPP, S1_OLD, S1_NEW, "S1 include ddos_mitigacion.hpp"),
    (P_SHPP, S2_OLD, S2_NEW, "S2 Config: ddos_mitigacion, escalones cortos, dry_run"),
    (P_SHPP, S3_OLD, S3_NEW, "S3 miembros: ddos_mitigacion_ y contadores"),
    (P_SCPP, Z1_OLD, Z1_NEW, "Z1 latido en receive_loop"),
    (P_SCPP, Z2_OLD, Z2_NEW, "Z2 resumen + purga + aviso"),
    (P_SCPP, Z3_OLD, Z3_NEW, "Z3 mitigacion tras add_drop"),
    (P_SCPP, Z4_OLD, Z4_NEW, "Z4 pasos 5-8 anotados"),
    (P_MAIN, M1_OLD, M1_NEW, "M1 rangos protegidos al procesador"),
    (P_MAIN, M2_OLD, M2_NEW, "M2 copia al suscriptor + linea de modo"),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d302_patch_b2_2.py --check | --apply")
        return 2
    apply = sys.argv[1] == "--apply"
    files = {p: p.read_text(encoding="utf-8") for p in (P_SHPP, P_SCPP, P_MAIN)}
    errores = []
    for p, txt in files.items():
        if MARCA in txt:
            errores.append(f"YA APLICADO: marca presente en {p.relative_to(ROOT)}")
    for p, old, _, nombre in EDITS:
        n = files[p].count(old)
        print(f"{nombre}: {n} coincidencia(s) en {p.relative_to(ROOT)}")
        if n != 1:
            errores.append(f"ancla no unica ({n}): {nombre}")
    if errores:
        print("CHECK FALLA:")
        for e in errores:
            print("  - " + e)
        return 1
    nuevos = dict(files)
    for p, old, new, _ in EDITS:
        nuevos[p] = nuevos[p].replace(old, new, 1)
    if not apply:
        print("CHECK OK: anclas unicas; nada escrito")
        return 0
    for p, txt in nuevos.items():
        p.write_text(txt, encoding="utf-8")
        print(f"escrito {p}")
    print("APPLY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
