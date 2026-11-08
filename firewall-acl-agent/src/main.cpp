//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// main.cpp - High-Performance Packet DROP Agent with Full Observability
// Day 50: Comprehensive diagnostics and crash analysis
// Day 52: Config-driven logging, ipsets-only (no singleton ipset)
//===----------------------------------------------------------------------===//

#include <sstream>  // [DDOS-MITIGACION-B1-D301]
#include <iostream>
#include <csignal>
#include <atomic>
#include <thread>
#include <chrono>
#include <ctime>

// Day 50: Observability infrastructure
#include "firewall_observability_logger.hpp"
#include "crash_diagnostics.hpp"

#include "firewall/config_loader.hpp"
#include "firewall/ipset_wrapper.hpp"
#include "firewall/iptables_wrapper.hpp"
#include "firewall/batch_processor.hpp"
#include "protegidos/manifiesto.hpp"  // [PROTEGIDOS-MANIFIESTO-D318] ADR-060
#include "firewall/protegidos_vigia.hpp"  // [PROTEGIDOS-VIGIA-D320] ADR-060 D8, 8e.4a
#include "firewall/protegidos_antispoof.hpp"  // [PROTEGIDOS-ANTISPOOF-D320] ADR-060 D8, 8e.4b
#include <fstream>
#include <filesystem>  // [PROTEGIDOS-MANIFIESTO-D318] directorio de la caché
#include <nlohmann/json.hpp>
#include "firewall/zmq_subscriber.hpp"
#include "firewall/etcd_client.hpp"
#include "firewall/autonomy_subscriber.hpp"
#include "firewall/autonomy_reactor.hpp"

#include <json/json.h>
#include <cstring>
#include <unistd.h>
#include <exception>

#ifdef PLUGIN_LOADER_ENABLED
#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"
#endif

using namespace mldefender::firewall;

//===----------------------------------------------------------------------===//
// Global Observability Infrastructure (Day 50)
//===----------------------------------------------------------------------===//

namespace mldefender::firewall::observability {
    std::unique_ptr<ObservabilityLogger> g_logger;
}

namespace mldefender::firewall::diagnostics {
    std::unique_ptr<SystemState> g_system_state;
}

//===----------------------------------------------------------------------===//
// Signal Handling (Enhanced for Day 50)
//===----------------------------------------------------------------------===//

std::atomic<bool> g_running{true};

void signal_handler(int signum) {
    FIREWALL_LOG_INFO("Shutdown signal received", "signal", signum);

    // Stop processing loop
    if (mldefender::firewall::diagnostics::g_system_state) {
        mldefender::firewall::diagnostics::g_system_state->is_running.store(false);
    }
    g_running.store(false);

    // Dump final state
    DUMP_STATE_ON_ERROR("graceful_shutdown");
}

void setup_signal_handlers() {
    struct sigaction sa;
    sa.sa_handler = signal_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;

    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGTERM, &sa, nullptr);

    FIREWALL_LOG_INFO("Signal handlers installed", "signals", "SIGINT,SIGTERM");

    // DEBT-IRP-SIGCHLD-001: evitar zombies de fork()+execv() IRP
    // SA_NOCLDWAIT: el kernel recoge hijos automáticamente, sin necesidad de wait()
    sa.sa_handler = SIG_DFL;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_NOCLDWAIT;
    sigaction(SIGCHLD, &sa, nullptr);
    FIREWALL_LOG_INFO("SIGCHLD SA_NOCLDWAIT instalado — IRP zombie prevention active");
}

//===----------------------------------------------------------------------===//
// Metrics Export (Enhanced for Day 50)
//===----------------------------------------------------------------------===//

void export_metrics(const FirewallAgentConfig& config,
                   const ZMQSubscriber& subscriber,
                   const BatchProcessor& processor) {
    const auto& zmq_stats = subscriber.get_stats();

    FIREWALL_LOG_INFO("Periodic metrics export",
        "messages_received", zmq_stats.messages_received.load(),
        "detections_processed", zmq_stats.detections_processed.load(),
        "parse_errors", zmq_stats.parse_errors.load(),
        "reconnects", zmq_stats.reconnects.load());

    // Also dump system state from diagnostics
    DUMP_STATE_ON_ERROR("periodic_metrics");
}

//===----------------------------------------------------------------------===//
// Health Checks (Enhanced for Day 50, Day 52: uses ipsets)
//===----------------------------------------------------------------------===//

bool perform_health_checks(const FirewallAgentConfig& config,
                          IPSetWrapper& ipset,
                          IPTablesWrapper& iptables,
                          const ZMQSubscriber& subscriber) {
    FIREWALL_LOG_INFO("Starting health checks");
    bool all_healthy = true;

    // ✅ Day 52: Use ipsets.at("blacklist")
    const auto& blacklist_ipset = config.ipsets.at("blacklist");

    // Check IPSet
    bool ipset_exists = ipset.set_exists(blacklist_ipset.set_name);
    if (!ipset_exists) {
        FIREWALL_LOG_ERROR("Health check failed: IPSet missing",
            "ipset_name", blacklist_ipset.set_name);
        all_healthy = false;
    } else {
        FIREWALL_LOG_DEBUG("Health check passed: IPSet exists",
            "ipset_name", blacklist_ipset.set_name);
    }

    // Check IPTables rule
    auto rules = iptables.list_rules("INPUT");
    bool rule_found = false;
    for (const auto& rule : rules) {
        if (rule.find(blacklist_ipset.set_name) != std::string::npos) {
            rule_found = true;
            break;
        }
    }

    if (!rule_found) {
        FIREWALL_LOG_ERROR("Health check failed: IPTables rule missing",
            "ipset_name", blacklist_ipset.set_name);
        all_healthy = false;
    } else {
        FIREWALL_LOG_DEBUG("Health check passed: IPTables rule exists");
    }

    // Check ZMQ connection
    const auto& stats = subscriber.get_stats();
    bool zmq_connected = stats.currently_connected.load();
    if (!zmq_connected) {
        FIREWALL_LOG_WARN("Health check warning: ZMQ not connected");
        all_healthy = false;
    } else {
        FIREWALL_LOG_DEBUG("Health check passed: ZMQ connected");
    }

    FIREWALL_LOG_INFO("Health checks completed",
        "status", all_healthy ? "HEALTHY" : "DEGRADED",
        "ipset_ok", ipset_exists,
        "iptables_ok", rule_found,
        "zmq_ok", zmq_connected);

    return all_healthy;
}

//===----------------------------------------------------------------------===//
// Usage
//===----------------------------------------------------------------------===//

void print_usage(const char* program_name) {
    std::cout << "ML Defender - Firewall ACL Agent\n"
              << "High-Performance Packet DROP Agent (1M+ packets/sec)\n"
              << "Day 52: Config-driven, ipsets-only (no singleton)\n\n"
              << "Usage: " << program_name << " [options]\n\n"
              << "Options:\n"
              << "  -c, --config <file>    Configuration file (required)\n"
              << "  -d, --daemonize        Run as daemon\n"
              << "  -t, --test-config      Test configuration and exit\n"
              << "  --verbose              Enable verbose logging (DEBUG level)\n"
              << "  --quiet                Quiet mode (ERROR level only)\n"
              << "  -v, --version          Show version\n"
              << "  -h, --help             Show this help\n\n"
              << "Day 52 Features:\n"
              << "  • Log path from config.logging.file\n"
              << "  • IPSet names from config.ipsets (no singleton)\n"
              << "  • IPSet creation verification\n"
              << std::endl;
}

void print_version() {
    std::cout << "ML Defender - Firewall ACL Agent v1.0.0 (Day 52)\n"
              << "Via Appia Quality: Built to last decades\n"
              << "Enhanced: Config-driven, ipsets-only\n"
              << std::endl;
}

//===----------------------------------------------------------------------===//
// Main Entry Point (Day 52 Enhanced)
//===----------------------------------------------------------------------===//

// ═══════════════════════════════════════════════════════════════════════
// [PROTEGIDOS-MANIFIESTO-D318] ADR-060: set del kernel, caché del manifiesto y vigilancia periódica
// ═══════════════════════════════════════════════════════════════════════
using ::argus::protegidos::ProtegidosVigentes;
using ::argus::protegidos::ManifiestoVerificado;
using ::argus::protegidos::candado_cerrado;
using ::argus::protegidos::claves_protegidos_compiladas;

// El set hash:net,iface existe y es de ese tipo (lo crea si falta). false = sin exención del kernel (solo barrera).
static bool protegidos_preparar_set(IPSetWrapper& ipset, const FirewallAgentConfig& config) {
    const auto& pc = config.protegidos;
    const auto& k = claves_protegidos_compiladas();
    std::cout << "[PROTEGIDOS-CLAVE] actual huella=" << ::argus::protegidos::huella_clave_protegidos(k.actual)
              << (k.hay_siguiente ? " siguiente huella=" + ::argus::protegidos::huella_clave_protegidos(k.siguiente)
                                  : std::string(" siguiente=ninguna"))
              << " (compiladas)" << std::endl;
    const auto tipo = ipset.set_type(pc.set_name);
    if (tipo && *tipo != "hash:net,iface") {
        std::cerr << "[PROTEGIDOS-SET-TIPO] el set " << pc.set_name << " existe con tipo " << *tipo
                  << " (se espera hash:net,iface): la exención del kernel NO se aplica; la barrera del agente sí protege. "
                     "Con el agente parado: sudo ipset destroy " << pc.set_name << std::endl;
        return false;
    }
    if (tipo) {
        std::cout << "[PROTEGIDOS-SET] " << pc.set_name << " hash:net,iface ya existe" << std::endl;
        return true;
    }
    if (config.operation.dry_run) {
        std::cout << "[DRY-RUN] ipset create " << pc.set_name << " hash:net,iface family inet counters (no se crea en "
                     "dry_run)" << std::endl;
        return true;
    }
    // [PROTEGIDOS-VIGIA-D320] la misma configuración que usa el vigía si tiene que recrear el set
    const IPSetConfig c = mldefender::firewall::config_set_protegidos(
        pc.set_name, static_cast<uint32_t>(::argus::protegidos::kProtegidosMaxEntradas));
    if (!ipset.create_set(c)) {
        std::cerr << "[PROTEGIDOS-SET] ERROR: no se pudo crear " << pc.set_name << " (hash:net,iface): la exención del "
                     "kernel NO se aplica; la barrera del agente sí protege" << std::endl;
        return false;
    }
    std::cout << "[PROTEGIDOS-SET] " << pc.set_name << " hash:net,iface creado (vacío hasta verificar un manifiesto)" << std::endl;
    return true;
}

// Entradas IPv4 (cidr, interfaz) de un manifiesto verificado: las que van al set del kernel. IPv6: solo la barrera
// (D-I). nullptr (sin vigente) = ninguna. [PROTEGIDOS-VIGIA-D320] la usan la aplicación y el vigía.
static std::vector<std::pair<std::string, std::string>> protegidos_entradas_kernel(const ManifiestoVerificado* m,
                                                                                   std::size_t* v6 = nullptr) {
    std::vector<std::pair<std::string, std::string>> e;
    if (v6) *v6 = 0;
    if (m == nullptr) return e;
    for (const auto& en : m->entradas) {
        if (en.rango.v6) {
            if (v6) ++*v6;
            continue;
        }
        e.emplace_back(en.rango.texto, en.interfaz);
    }
    return e;
}

// Lleva al kernel las entradas IPv4 del manifiesto (sustitución atómica). IPv6: solo la barrera (D-I).
static void protegidos_aplicar_kernel(IPSetWrapper& ipset, const std::string& set, const ManifiestoVerificado& m) {
    std::size_t v6 = 0;
    const auto e = protegidos_entradas_kernel(&m, &v6);
    const auto r = ipset.replace_net_iface(set, e, static_cast<uint32_t>(::argus::protegidos::kProtegidosMaxEntradas));
    if (r) {
        std::cout << "[PROTEGIDOS-KERNEL] " << set << " = version " << m.version << ": " << e.size()
                  << " entradas cidr,interfaz (IPv6 solo en la barrera: " << v6 << "; DEBT-FW-IPV6-SETS-001)" << std::endl;
    } else {
        std::cerr << "[PROTEGIDOS-KERNEL] ERROR al cargar " << set << ": " << r.get_error().message
                  << "; la barrera del agente sí protege; revise: sudo ipset list " << set << std::endl;
    }
}

static void protegidos_infra(const ManifiestoVerificado& m, const FirewallAgentConfig& config) {
    const auto f = ::argus::protegidos::infra_sin_cubrir(m, config.protegidos.etcd_endpoints);
    if (f.empty()) return;
    std::ostringstream o;
    for (std::size_t i = 0; i < f.size(); ++i) o << (i ? " " : "") << ::argus::protegidos::detalle_protegidos::saneado(f[i]);
    std::cerr << "[PROTEGIDOS-INFRA-INCOMPLETA] etcd.endpoints sin entrada infraestructura en el manifiesto version "
              << m.version << ": " << o.str() << " (un DDoS podría dejar al plano de control en el blacklist: firme una "
                 "versión que lo incluya con argus-infra)" << std::endl;
}

// [PROTEGIDOS-MANIFIESTO-D318] 8e.3c: un manifiesto ya verificado y vigente: kernel, caché + versión (si viene del
// etcd-server), [INFRA-CAMBIO] con altas y bajas, y el plano de control (D-C).
static void protegidos_aplicado(const ProtegidosVigentes::Propuesta& p, IPSetWrapper& ipset,
                                const FirewallAgentConfig& config, bool set_ok, const char* origen, bool guardar) {
    const auto& pc = config.protegidos;
    const auto& m = *p.resultado.manifiesto;
    std::cout << ::argus::protegidos::resumen_manifiesto(m) << " (" << origen << ")" << std::endl;
    if (p.anterior) {
        std::cout << "[INFRA-CAMBIO] version " << p.anterior->version << " -> " << m.version << " firmante="
                  << ::argus::protegidos::detalle_protegidos::saneado(m.firmante) << " emitido=" << m.emitido_utc
                  << " motivo=" << ::argus::protegidos::detalle_protegidos::saneado(m.motivo) << " "
                  << ::argus::protegidos::diferencias_protegidos(p.anterior.get(), m) << " (" << origen << ")" << std::endl;
    }
    if (set_ok) protegidos_aplicar_kernel(ipset, pc.set_name, m);
    if (guardar) {
        std::string err;
        std::error_code ec;
        std::filesystem::create_directories(std::filesystem::path(pc.manifiesto_cache).parent_path(), ec);
        if (!::argus::protegidos::escribir_cache_protegidos(pc.manifiesto_cache, m.sobre, err)) {
            std::cerr << "[PROTEGIDOS-CACHE] no se pudo guardar " << pc.manifiesto_cache << ": " << err
                      << " (la version " << m.version << " sigue vigente en memoria)" << std::endl;
        }
    }
    std::string err;
    if (!::argus::protegidos::escribir_version_protegidos(pc.manifiesto_cache + ".version", m.version, err)) {
        std::cerr << "[PROTEGIDOS-VERSION] no se pudo guardar " << pc.manifiesto_cache << ".version: " << err
                  << " (anti-rollback entre reinicios sin la version " << m.version << ")" << std::endl;
    }
    protegidos_infra(m, config);
}

// [PROTEGIDOS-MANIFIESTO-D318] 8e.3c (F-E): pide el manifiesto al etcd-server. true si respondió (200 o 404).
// El mismo sobre que el vigente: nada (cada consulta_sec). Otro: se verifica; con versión menor, rechazo y alarma.
static bool protegidos_consultar(ProtegidosVigentes& v, mldefender::firewall::EtcdClient* etcd, IPSetWrapper& ipset,
                                 const FirewallAgentConfig& config, bool set_ok, std::string& fallo) {
    if (etcd == nullptr) {
        fallo = "sin cliente etcd";
        return false;
    }
    std::string cuerpo;
    const int st = etcd->get_protegidos(cuerpo);
    if (st == 404) {
        fallo = "el etcd-server no tiene manifiesto publicado (404)";
        return true;
    }
    if (st != 200) {
        fallo = "status " + std::to_string(st) + ": " + ::argus::protegidos::detalle_protegidos::saneado(cuerpo.substr(0, 200));
        return false;
    }
    fallo.clear();
    const auto vig = v.vigente();
    if (vig && vig->sobre == cuerpo) return true;
    const auto p = v.proponer(cuerpo);
    if (!p.resultado.ok) {
        std::cerr << "[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=" << ::argus::protegidos::nombre_motivo(p.resultado.motivo)
                  << " " << p.resultado.detalle << " (etcd-server; se conserva "
                  << (vig ? "la version " + std::to_string(vig->version) : std::string("el estado sin manifiesto"))
                  << ")" << std::endl;
        return true;
    }
    protegidos_aplicado(p, ipset, config, set_ok, "etcd-server", true);
    return true;
}

// Arranque (ADR-060 D5.5 y F-F): suelo = la versión más alta aplicada antes de reiniciar; primero el etcd-server y, si
// no responde o no hay nada nuevo, la caché (que no puede ser más vieja que el suelo).
static void protegidos_cargar_cache(ProtegidosVigentes& v, IPSetWrapper& ipset, const FirewallAgentConfig& config,
                                    bool set_ok, mldefender::firewall::EtcdClient* etcd) {
    const auto& pc = config.protegidos;
    if (pc.hospital_id.empty() || pc.despliegue_id.empty()) {
        std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] protegidos.hospital_id/despliegue_id sin valor: no hay manifiesto que "
                     "verificar (candado cerrado)" << std::endl;
        return;
    }
    uint64_t suelo = 0;
    std::string err;
    if (!::argus::protegidos::leer_version_protegidos(pc.manifiesto_cache + ".version", suelo, err)) {
        std::cerr << "[PROTEGIDOS-VERSION] " << pc.manifiesto_cache << ".version: " << err
                  << " (sin suelo: revise el fichero; el etcd-server y la firma siguen mandando)" << std::endl;
        suelo = 0;
    }
    v.fijar_suelo(suelo);
    std::cout << "[PROTEGIDOS-VERSION] suelo=" << suelo << " (" << pc.manifiesto_cache << ".version)" << std::endl;
    std::string fallo;
    if (!protegidos_consultar(v, etcd, ipset, config, set_ok, fallo)) {
        std::cerr << "[PROTEGIDOS-CONSULTA] al arrancar: " << fallo << "; se usa la caché" << std::endl;
    }
    std::string sobre;
    if (!::argus::protegidos::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {
        if (!v.vigente()) {
            std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] caché " << pc.manifiesto_cache << ": " << err << " (hospital="
                      << pc.hospital_id << " planta=" << pc.despliegue_id << "; candado cerrado)" << std::endl;
        }
        return;
    }
    const auto vig = v.vigente();
    if (vig && vig->sobre == sobre) return;   // el etcd-server dio el mismo que la caché
    const auto p = v.proponer(sobre);
    if (!p.resultado.ok) {
        if (!vig) {
            std::cerr << "[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=" << ::argus::protegidos::nombre_motivo(p.resultado.motivo)
                      << " " << p.resultado.detalle << " (caché " << pc.manifiesto_cache << ", suelo=" << suelo
                      << "; candado cerrado)" << std::endl;
        }
        return;
    }
    protegidos_aplicado(p, ipset, config, set_ok, "caché", false);
}

// Cada aviso_sec: sin manifiesto, aviso (D6); con él, la caché tiene que seguir verificando (D7) y el plano de
// control tiene que estar dentro (D-C). Nunca se pierde lo vigente por un fallo de disco.
static void protegidos_vigilar(const ProtegidosVigentes& v, const FirewallAgentConfig& config) {
    const auto& pc = config.protegidos;
    const auto m = v.vigente();
    if (!m) {
        std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] sin manifiesto verificado (hospital=" << pc.hospital_id << " planta="
                  << pc.despliegue_id << " caché=" << pc.manifiesto_cache << "): "
                  << (candado_cerrado(config.ddos_mitigacion.habilitada, &v) ? "mitigacion real BLOQUEADA (candado); sombra"
                                                                            : "mitigacion deshabilitada")
                  << "; ningún rango protegido" << std::endl;
        return;
    }
    std::string sobre, err;
    if (!::argus::protegidos::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {
        std::cerr << "[PROTEGIDOS-CACHE] no se puede leer " << pc.manifiesto_cache << ": " << err
                  << "; se conserva en memoria la version " << m->version << " (D7)" << std::endl;
    } else {
        const auto r = v.reverificar(sobre);
        if (!r.ok) {
            std::cerr << "[PROTEGIDOS-CACHE] la caché ya no verifica (motivo=" << ::argus::protegidos::nombre_motivo(r.motivo)
                      << " " << r.detalle << "): se conserva en memoria la version " << m->version
                      << " (D7); vuelva a firmar con argus-infra" << std::endl;
        }
    }
    protegidos_infra(*m, config);
}

// [PROTEGIDOS-VIGIA-D320] ADR-060 D8, 8e.4a: contadores del vigía (solo los toca el bucle principal).
struct ContadoresVigia {
    uint64_t comprobaciones = 0, divergencias = 0, reconciliaciones = 0, fallos = 0;
};

// Lista corta para el log: como mucho 10 elementos saneados y el resto contado.
static std::string protegidos_lista(const std::vector<std::string>& v) {
    std::ostringstream o;
    o << "[";
    for (std::size_t i = 0; i < v.size() && i < 10; ++i) {
        o << (i ? " " : "") << ::argus::protegidos::detalle_protegidos::saneado(v[i]);
    }
    if (v.size() > 10) o << " ... (+" << (v.size() - 10) << ")";
    o << "]";
    return o.str();
}

// Una vuelta del vigía (cada comprobacion_kernel_sec, desde el bucle principal: fuera del camino del paquete).
static void protegidos_vigia(const ProtegidosVigentes& v, IPSetWrapper& ipset, IPTablesWrapper& iptables,
                             const FirewallConfig& fc, const FirewallAgentConfig& config, bool set_ok,
                             ContadoresVigia& cv) {
    const auto& pc = config.protegidos;
    const auto m = v.vigente();
    const std::string version = m ? std::to_string(m->version) : std::string("ninguna");
    const auto r = mldefender::firewall::vigia_protegidos_paso(
        ipset, iptables, fc, pc.set_name, set_ok, protegidos_entradas_kernel(m.get()),
        static_cast<uint32_t>(::argus::protegidos::kProtegidosMaxEntradas));
    ++cv.comprobaciones;
    if (r.set_divergente) {
        ++cv.divergencias;
        std::cerr << "[PROTEGIDOS-DIVERGENCIA] set " << pc.set_name << " != manifiesto version " << version << ": "
                  << (r.motivo_set.empty() ? std::string() : r.motivo_set + "; ")
                  << "sobran=" << protegidos_lista(r.diferencia.sobran) << " faltan=" << protegidos_lista(r.diferencia.faltan)
                  << std::endl;
        if (r.set_tipo_ajeno) {
            std::cerr << "[PROTEGIDOS-SET-TIPO] no se destruye un set ajeno; con el agente parado: sudo ipset destroy "
                      << pc.set_name << std::endl;
        } else if (r.set_reconciliado) {
            ++cv.reconciliaciones;
            std::cout << "[PROTEGIDOS-RECONCILIADO] set " << pc.set_name << " = manifiesto version " << version
                      << " (comprobado tras la sustitución atómica)" << std::endl;
        }
    }
    if (r.reglas_divergentes) {
        ++cv.divergencias;
        std::cerr << "[PROTEGIDOS-DIVERGENCIA] reglas: " << r.motivo_reglas << std::endl;
        if (r.reglas_reconciliadas) {
            ++cv.reconciliaciones;
            std::cout << "[PROTEGIDOS-RECONCILIADO] reglas de " << fc.blacklist_chain
                      << " rehechas (salto INPUT en la posición 1; protegidos RETURN antes de blacklist DROP)" << std::endl;
        }
    }
    if (!r.error.empty()) {
        ++cv.fallos;
        std::cerr << "[PROTEGIDOS-VIGIA] ERROR al reconciliar: " << r.error
                  << " (la barrera del agente sigue protegiendo por IP; se reintenta en la próxima vuelta)" << std::endl;
    }
}

// ═══════════════════════════════════════════════════════════════════════
// [PROTEGIDOS-ANTISPOOF-D320] ADR-060 D8, 8e.4b: antispoofing en raw PREROUTING (solo lo toca el bucle principal)
// ═══════════════════════════════════════════════════════════════════════
struct EstadoAntispoof {
    bool activo = false;                 // dry_run=false, configuración válida y set de protegidos utilizable
    mldefender::firewall::NombresAntispoof n;
    bool aplicado = false;
    uint64_t version = 0;                // versión del manifiesto aplicada (0 = ninguno)
    bool descarta = false;               // modo aplicado
    mldefender::firewall::RepartoAntispoof reparto;
    uint64_t ult_if = 0, ult_mac = 0, total_if = 0, total_mac = 0;
};

static std::vector<mldefender::firewall::EntradaAntispoof> antispoof_entradas(const ManifiestoVerificado* m) {
    std::vector<mldefender::firewall::EntradaAntispoof> v;
    if (m == nullptr) return v;
    for (const auto& en : m->entradas) {
        if (en.rango.v6) continue;  // IPv6: solo la barrera (D-I)
        v.push_back({en.rango.texto, en.interfaz, en.mac});
    }
    return v;
}

static mldefender::firewall::RepartoAntispoof antispoof_reparto(const ManifiestoVerificado* m) {
    return mldefender::firewall::repartir_antispoof(
        antispoof_entradas(m), [](const std::string& ip) { return IPTablesWrapper::interfaz_de_ruta(ip); });
}

// Modo descarta solo con la mitigación real: dry_run=false, habilitada=true y candado abierto (manifiesto verificado).
static bool antispoof_descarta(const ProtegidosVigentes& v, const FirewallAgentConfig& config) {
    return !config.operation.dry_run && config.ddos_mitigacion.habilitada &&
           !candado_cerrado(config.ddos_mitigacion.habilitada, &v) && v.vigente() != nullptr;
}

static void antispoof_aplicar(EstadoAntispoof& e, IPSetWrapper& ipset, IPTablesWrapper& iptables,
                              const ProtegidosVigentes& v, const FirewallAgentConfig& config, const std::string& por) {
    const auto m = v.vigente();
    e.reparto = antispoof_reparto(m.get());
    e.descarta = antispoof_descarta(v, config);
    e.version = m ? m->version : 0;
    const auto r = mldefender::firewall::antispoof_paso(ipset, iptables, e.n, e.reparto, e.descarta,
                                                       static_cast<uint32_t>(::argus::protegidos::kProtegidosMaxEntradas),
                                                       false);
    e.aplicado = true;
    e.ult_if = e.ult_mac = 0;  // la cadena se rehace con los contadores a cero
    if (r.reconciliado) {
        std::cout << "[PROTEGIDOS-ANTISPOOF] aplicado (" << por << "): manifiesto version "
                  << (m ? std::to_string(m->version) : std::string("ninguna")) << " modo="
                  << (e.descarta ? "descarta" : "cuenta") << " redes=" << e.reparto.redes.size()
                  << " ips_mac=" << e.reparto.ips_mac.size() << " mac=" << e.reparto.mac.size()
                  << (e.n.con_mac ? "" : " (sin hash:ip,mac en el kernel: SIN comprobación de MAC)")
                  << " cadena raw " << e.n.cadena << std::endl;
    } else {
        std::cerr << "[PROTEGIDOS-ANTISPOOF] ERROR al aplicar (" << por << "): " << r.error
                  << " (la barrera del agente sigue protegiendo por IP; el vigía reintenta)" << std::endl;
    }
    for (const auto& x : e.reparto.sin_ruta) {
        std::cerr << "[PROTEGIDOS-RUTA] " << ::argus::protegidos::detalle_protegidos::saneado(x)
                  << ": esa red no se cuenta ni se descarta (un DROP por la interfaz equivocada sería un DoS "
                     "autoinfligido); corrija la interfaz en el manifiesto con argus-infra" << std::endl;
    }
}

// Vuelta del vigía (cada comprobacion_kernel_sec): rutas, K4/K5 y contadores de spoofing.
static void antispoof_vigia(EstadoAntispoof& e, IPSetWrapper& ipset, IPTablesWrapper& iptables,
                            const ProtegidosVigentes& v, const FirewallAgentConfig& config, ContadoresVigia& cv) {
    const auto m = v.vigente();
    const auto rep = antispoof_reparto(m.get());
    if (rep.redes != e.reparto.redes || rep.ips_mac != e.reparto.ips_mac || rep.mac != e.reparto.mac ||
        rep.sin_ruta != e.reparto.sin_ruta) {
        antispoof_aplicar(e, ipset, iptables, v, config, "las rutas del kernel han cambiado");
    }
    const auto r = mldefender::firewall::antispoof_paso(ipset, iptables, e.n, e.reparto, e.descarta,
                                                       static_cast<uint32_t>(::argus::protegidos::kProtegidosMaxEntradas),
                                                       true);
    ++cv.comprobaciones;
    if (r.divergente) {
        ++cv.divergencias;
        std::ostringstream o;
        for (std::size_t i = 0; i < r.motivos.size(); ++i) o << (i ? "; " : "") << r.motivos[i];
        std::cerr << "[PROTEGIDOS-DIVERGENCIA] antispoof: " << o.str() << std::endl;
        if (r.reconciliado) {
            ++cv.reconciliaciones;
            e.ult_if = e.ult_mac = 0;
            std::cout << "[PROTEGIDOS-RECONCILIADO] antispoof: sets y cadenas raw de " << e.n.cadena
                      << " como dice el manifiesto (modo " << (e.descarta ? "descarta" : "cuenta") << ")" << std::endl;
        }
    }
    if (!r.error.empty() && !r.reconciliado) {
        ++cv.fallos;
        std::cerr << "[PROTEGIDOS-VIGIA] ERROR antispoof: " << r.error << std::endl;
    }
    const auto ci = iptables.contadores(e.n.cadena + "_IF", IPTablesTable::RAW);
    const auto cm = iptables.contadores(e.n.cadena + "_MAC", IPTablesTable::RAW);
    const uint64_t vi = ci.size() >= 2 ? ci[1] : 0, vm = cm.size() >= 2 ? cm[1] : 0;
    const uint64_t di = vi >= e.ult_if ? vi - e.ult_if : vi, dm = vm >= e.ult_mac ? vm - e.ult_mac : vm;
    e.ult_if = vi;
    e.ult_mac = vm;
    if (di > 0 || dm > 0) {
        e.total_if += di;
        e.total_mac += dm;
        std::cerr << "[PROTEGIDOS-SPOOFING] origen protegido falsificado: interfaz=+" << di << " mac=+" << dm
                  << " (total interfaz=" << e.total_if << " mac=" << e.total_mac << ") modo="
                  << (e.descarta ? "descarta" : "cuenta") << "; evidencia: journalctl -k | grep ARGUS-SPOOF" << std::endl;
    }
}

int main(int argc, char** argv) {
#ifdef PLUGIN_LOADER_ENABLED
    std::unique_ptr<ml_defender::PluginLoader> plugin_loader;
#endif

    // SET_TERMINATE — DAY 100 (ADR-022: fail-closed, unhandled exceptions)
    std::set_terminate([]() {
        std::cerr << "[FATAL] std::terminate() called — unhandled exception or contract violation\n";
        std::abort();
    });
    // Parse command line arguments
    std::string config_path = "/etc/ml-defender/firewall-acl-agent/firewall.json";  // ✅ Prod path — symlink → /vagrant/ en dev
    bool test_config = false;
    bool verbose = false;
    bool quiet = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            return 0;
        } else if (arg == "-v" || arg == "--version") {
            print_version();
            return 0;
        } else if (arg == "-c" || arg == "--config") {
            if (i + 1 < argc) {
                config_path = argv[++i];  // ✅ Use user-provided path
            } else {
                std::cerr << "[ERROR] --config requires a file path" << std::endl;
                return 1;
            }
        } else if (arg == "-t" || arg == "--test-config") {
            test_config = true;
        } else if (arg == "--verbose") {
            verbose = true;
        } else if (arg == "--quiet") {
            quiet = true;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Day 52: Early initialization (crash diagnostics only, logger after config)
    // ═══════════════════════════════════════════════════════════════════════

    try {
        // Initialize system state for crash diagnostics (before config loading)
        mldefender::firewall::diagnostics::g_system_state =
            std::make_unique<mldefender::firewall::diagnostics::SystemState>();

        // Install crash diagnostics early
        mldefender::firewall::diagnostics::install_crash_handlers();

    } catch (const std::exception& e) {
        std::cerr << "[FATAL] Failed to initialize crash diagnostics: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "╔════════════════════════════════════════════════════════╗\n"
              << "║  ML Defender - Firewall ACL Agent (Day 52)            ║\n"
              << "║  High-Performance Packet DROP Agent                   ║\n"
              << "║  Target: 1M+ packets/sec                               ║\n"
              << "║  Config-Driven: ipsets-only (no singleton)            ║\n"
              << "╚════════════════════════════════════════════════════════╝\n"
              << std::endl;

    // ═══════════════════════════════════════════════════════════════════════
    // Configuration Loading (Day 52: Before logger init)
    // ═══════════════════════════════════════════════════════════════════════

    std::unique_ptr<mldefender::firewall::EtcdClient> etcd_client;
    FirewallAgentConfig config;

    try {
        std::cout << "[INFO] Loading configuration from: " << config_path << std::endl;

        config = ConfigLoader::load_from_file(config_path);

        std::cout << "[INFO] Configuration loaded successfully" << std::endl;

#ifdef PLUGIN_LOADER_ENABLED
    plugin_loader = std::make_unique<ml_defender::PluginLoader>(config_path);
    plugin_loader->load_plugins();
    std::cout << "[INFO] plugin-loader: " << plugin_loader->loaded_count() << " plugin(s) cargados" << std::endl;

    // TEST-INTEG-4a: invocar plugin_process_message() con MessageContext real
    // Gate: result_code==0 + CryptoTransport decryption path sin modificar
    if (plugin_loader->loaded_count() > 0) {
        const char* synthetic_payload =
            "{\"event\":\"TEST-INTEG-4a\",\"src_ip\":\"192.168.1.1\",\"threat\":\"none\"}";
        ::MessageContext msg_ctx{};  // C ABI — namespace global (extern "C")
        msg_ctx.payload     = reinterpret_cast<const uint8_t*>(synthetic_payload);
        msg_ctx.payload_len = std::strlen(synthetic_payload);
        msg_ctx.src_ip      = 0xC0A80101; // 192.168.1.1
        msg_ctx.dst_ip      = 0xC0A80164; // 192.168.1.100
        msg_ctx.src_port    = 12345;
        msg_ctx.dst_port    = 5572;
        msg_ctx.protocol    = 6;  // TCP
        msg_ctx.direction   = 0;  // RX
        msg_ctx.nonce       = nullptr; // no disponible pre-decrypt — válido en smoke test
        msg_ctx.tag         = nullptr;
        msg_ctx.result_code = 0;
        msg_ctx.annotation[0] = '\0';

        plugin_loader->invoke_all(msg_ctx);
        std::cout << "[INFO] TEST-INTEG-4a: result_code=" << msg_ctx.result_code;
        if (msg_ctx.annotation[0] != '\0') {
            std::cout << " annotation='" << msg_ctx.annotation << "'";
        }
        std::cout << std::endl;
    }
#endif
        std::cout << "[INFO] Dry-run mode: " << (config.operation.dry_run ? "ENABLED" : "DISABLED") << std::endl;

        // Show DRY-RUN status prominently
        if (config.operation.dry_run) {
            std::cout << "\n╔════════════════════════════════════════════════════════╗\n"
                      << "║  🔍 DRY-RUN MODE ENABLED 🔍                           ║\n"
                      << "║  No actual firewall rules will be modified            ║\n"
                      << "╚════════════════════════════════════════════════════════╝\n"
                      << std::endl;
        }

        // ✅ Day 52: Validate required ipsets exist in config
        if (config.ipsets.count("blacklist") == 0) {
            std::cerr << "[FATAL] Configuration error: 'ipsets.blacklist' is required" << std::endl;
            return 1;
        }

    } catch (const std::exception& e) {
        std::cerr << "[FATAL] Failed to load configuration: " << e.what() << std::endl;
        return 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Day 52: Initialize Logger with Config Path
    // ═══════════════════════════════════════════════════════════════════════

    try {
        // Determine log level
        bool enable_verbose = verbose && !quiet;  // Verbose overrides quiet

        // ✅ Day 52: Use log path from config
        std::string log_path = config.logging.file;

        std::cout << "[INFO] Initializing logger: " << log_path << std::endl;

        mldefender::firewall::observability::g_logger =
            std::make_unique<mldefender::firewall::observability::ObservabilityLogger>(
                log_path, enable_verbose);

        {  // [LOG-LEVEL-D296] logging.level del JSON (debug|info|batch|ipset|warn|error|crash); defecto validado: info
            using OL = mldefender::firewall::observability::ObservabilityLogger;
            OL::Level lvl = OL::Level::LOG_INFO;
            if (!OL::parse_level(config.logging.level, lvl)) {
                std::cerr << "[CONFIG-DEFAULT] logging.level='" << config.logging.level
                          << "' no valido (admitidos: debug|info|batch|ipset|warn|error|crash); se usa el defecto validado 'info'" << std::endl;
                lvl = OL::Level::LOG_INFO;
            }
            mldefender::firewall::observability::g_logger->set_min_level(lvl);
            std::cout << "[INFO] logging.level aplicado=" << OL::level_str(lvl) << " [LOG-LEVEL-D296]" << std::endl;
        }

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("ML Defender - Firewall ACL Agent v1.0.0 (Day 52)");
        FIREWALL_LOG_INFO("High-Performance Packet DROP Agent");
        FIREWALL_LOG_INFO("Via Appia Quality: Built to last decades");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        FIREWALL_LOG_INFO("Observability initialized",
            "log_file", log_path,
            "verbose_mode", enable_verbose,
            "config_path", config_path);

    } catch (const std::exception& e) {
        std::cerr << "[FATAL] Failed to initialize logger: " << e.what() << std::endl;
        return 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Configuration Summary (Day 52: Now with logger available)
    // ═══════════════════════════════════════════════════════════════════════

    ConfigLoader::log_config_summary(config);

    // ═══════════════════════════════════════════════════════════════════════
    // ETCD Integration (Day 50: Fixed path bug)
    // ═══════════════════════════════════════════════════════════════════════

    // [ETCD-CLIENTE-D316] F1: el bloque etcd lo lee y valida la librería; D2: fuera etcd.enabled.
    // [ETCD-CLIENTE-B1-D316] G2: el firewall nunca sale ni espera por etcd. Sin fatales, el mantenedor de la librería
    // se registra en segundo plano y sube este JSON (G3); con fatales, sigue sin etcd y lo repite en el log cada 30 s.
    std::unique_ptr<etcd_client::AvisoBloqueFatal> aviso_etcd_fatal;
    auto lectura_etcd = etcd_client::leer_bloque_etcd(config.etcd.bloque_json, std::cout);
    if (lectura_etcd.fatales.empty()) {
        try {
            etcd_client = std::make_unique<mldefender::firewall::EtcdClient>(
                lectura_etcd.config,
                "firewall-acl-agent"
            );
            etcd_client->arrancar(config_path);
        } catch (const std::exception& e) {
            FIREWALL_LOG_ERROR("etcd client exception - continuing without etcd",
                "error", e.what());
            etcd_client.reset();
        }
    } else {
        aviso_etcd_fatal = std::make_unique<etcd_client::AvisoBloqueFatal>("firewall-acl-agent",
                                                                           lectura_etcd.fatales.size());
    }

        FIREWALL_LOG_DEBUG("Configuration phase completed successfully");

        // ═══════════════════════════════════════════════════════════
        // AUTONOMY PLANE — FirewallAutonomyReactor + AutonomySubscriber
        // DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 (DAY 156)
        // ═══════════════════════════════════════════════════════════
    FIREWALL_LOG_INFO("Initializing autonomy plane",
        "zmq_endpoint", config.autonomy.zmq_endpoint,
        "reconcile_interval_sec", config.autonomy.reconcile_interval_sec);

    mldefender::firewall::FirewallAutonomyReactor autonomy_reactor(
        config.autonomy.whitelist_cidrs,
        config.operation.dry_run
    );
    // DEBT-CRYPTO-RECONCILIATION-001 (DAY 157)
    // STALENESS GUARD (DAY 157 — B1 post-Consejo):
    // shared_last_update_ns: nanosegundos steady_clock del último evento ZMQ.
    // poll_callback: si now - last_update > staleness_timeout → NORMAL.
    // Previene firewall congelado en AUTONOMOUS si etcd-server muere.
    using AtomicMode = std::atomic<mldefender::firewall::FirewallAutonomyMode>;
    auto shared_mode = std::make_shared<AtomicMode>(
        mldefender::firewall::FirewallAutonomyMode::NORMAL);

    auto shared_last_update_ns = std::make_shared<std::atomic<int64_t>>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());

    const int staleness_timeout_sec = config.autonomy.reconcile_interval_sec * 3;

    auto poll_callback = [shared_mode, shared_last_update_ns, staleness_timeout_sec]()
        -> mldefender::firewall::FirewallAutonomyMode {
        const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        const int64_t last_ns = shared_last_update_ns->load(std::memory_order_acquire);
        const int64_t elapsed_sec = (now_ns - last_ns) / 1'000'000'000LL;
        if (elapsed_sec > staleness_timeout_sec) {
            std::cerr << "[poll_callback] STALE: sin eventos ZMQ desde "
                      << elapsed_sec << "s — fallback NORMAL\n";
            return mldefender::firewall::FirewallAutonomyMode::NORMAL;
        }
        return shared_mode->load(std::memory_order_acquire);
    };
    auto autonomy_sub = std::make_unique<mldefender::firewall::AutonomySubscriber>(
        autonomy_reactor,
        poll_callback,
        config.autonomy.zmq_endpoint,
        config.autonomy.reconcile_interval_sec,
        shared_mode,
        shared_last_update_ns,
        staleness_timeout_sec
    );
    autonomy_sub->start();
    FIREWALL_LOG_INFO("AutonomySubscriber started",
        "endpoint", config.autonomy.zmq_endpoint);



    // Test config mode
    if (test_config) {
        FIREWALL_LOG_INFO("Configuration test mode - exiting");
        std::cout << "[INFO] Configuration test passed ✓" << std::endl;
        return 0;
    }

    // Permission check
    if (getuid() != 0 && !config.operation.dry_run) {
        FIREWALL_LOG_CRASH("Insufficient privileges - must run as root",
            "uid", getuid(),
            "dry_run", config.operation.dry_run);
        std::cerr << "[ERROR] This program must be run as root (or use dry_run mode)" << std::endl;
        return 1;
    }

    FIREWALL_LOG_DEBUG("Permission check passed",
        "uid", getuid(),
        "dry_run", config.operation.dry_run);

    // ═══════════════════════════════════════════════════════════════════════
    // Component Initialization (Day 52: ipsets-only, enhanced verification)
    // ═══════════════════════════════════════════════════════════════════════

    try {
        FIREWALL_LOG_INFO("Starting component initialization phase");

        // ───────────────────────────────────────────────────────────────────
        // IPSet Configuration (Day 52: All from ipsets map)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("Initializing IPSet wrapper");
        IPSetWrapper ipset;
        ipset.set_dry_run(config.operation.dry_run);

        // Create all ipsets from config.ipsets map
        if (!config.ipsets.empty()) {
            FIREWALL_LOG_INFO("Processing ipsets",
                "count", config.ipsets.size());

            for (const auto& [name, ipset_cfg] : config.ipsets) {
                if (!ipset.set_exists(ipset_cfg.set_name)) {
                    FIREWALL_LOG_INFO("Creating ipset",
                        "logical_name", name,
                        "set_name", ipset_cfg.set_name,
                        "timeout", ipset_cfg.timeout);

                    IPSetConfig ipset_config;
                    ipset_config.name = ipset_cfg.set_name;
                    // [DDOS-MITIGACION-B1-D301] el tipo sale del JSON (antes HASH_IP fijo: set_type se ignoraba)
                    if (ipset_cfg.set_type == "hash:net") {
                        ipset_config.type = IPSetType::HASH_NET;
                    } else {
                        if (ipset_cfg.set_type != "hash:ip") {
                            std::cerr << "[CONFIG-DEFAULT] ipsets." << name << ".set_type '"
                                      << ::argus::protegidos::detalle_protegidos::saneado(ipset_cfg.set_type)
                                      << "' no admitido (formato: hash:ip | hash:net): se usa hash:ip" << std::endl;
                        }
                        ipset_config.type = IPSetType::HASH_IP;
                    }
                    std::cout << "[CONFIG] ipsets." << name << ".set_type="
                              << (ipset_config.type == IPSetType::HASH_NET ? "hash:net" : "hash:ip") << std::endl;
                    ipset_config.family = IPSetFamily::INET;
                    ipset_config.hashsize = ipset_cfg.hash_size;
                    ipset_config.maxelem = ipset_cfg.max_elements;
                    ipset_config.timeout = ipset_cfg.timeout;
                    ipset_config.counters = true;
                    ipset_config.comment = !ipset_cfg.comment.empty();

                    if (!ipset.create_set(ipset_config)) {
                        FIREWALL_LOG_ERROR("Failed to create ipset",
                            "logical_name", name,
                            "set_name", ipset_cfg.set_name);
                        DUMP_STATE_ON_ERROR("ipset_creation_failed");
                        return 1;
                    }

                    FIREWALL_LOG_INFO("IPSet created successfully",
                        "logical_name", name,
                        "set_name", ipset_cfg.set_name);
                } else {
                    FIREWALL_LOG_DEBUG("IPSet already exists",
                        "logical_name", name,
                        "set_name", ipset_cfg.set_name);
                }
            }
        }

        // ═══════════════════════════════════════════════════════════════════════
        // Day 52: IPSet Creation Verification
        // ═══════════════════════════════════════════════════════════════════════

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("IPSet Creation Verification (Day 52)");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        // Verify all ipsets
        for (const auto& [name, ipset_cfg] : config.ipsets) {
            bool exists = ipset.set_exists(ipset_cfg.set_name);
            FIREWALL_LOG_INFO("IPSet verification",
                "logical_name", name,
                "set_name", ipset_cfg.set_name,
                "status", exists ? "EXISTS" : "MISSING");

            if (!exists && config.operation.dry_run) {  // [FW-DRYRUN-VERIF-D294] en dry_run no se crean: no es fallo
                FIREWALL_LOG_INFO("IPSet verification skipped (dry-run: ipset not created)",
                    "logical_name", name,
                    "set_name", ipset_cfg.set_name);
                std::cout << "[DRY-RUN] verificación de ipset omitida (no se crea en dry_run): "
                          << ipset_cfg.set_name << std::endl;
            } else if (!exists) {
                FIREWALL_LOG_CRASH("IPSet verification failed",
                    "logical_name", name,
                    "set_name", ipset_cfg.set_name);
                std::cerr << "[FATAL] IPSet does not exist: " << ipset_cfg.set_name << std::endl;
                return 1;
            }
        }

        FIREWALL_LOG_INFO("All ipsets verified successfully",
            "count", config.ipsets.size());
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        // ───────────────────────────────────────────────────────────────────
        // IPTables Configuration (Day 52: uses ipsets.at("blacklist"))
        // ───────────────────────────────────────────────────────────────────

        // [PROTEGIDOS-MANIFIESTO-D318] ADR-060: set hash:net,iface de protegidos (solo lo escribe el agente) y manifiesto
        // firmado desde la caché. Sin manifiesto verificado el set queda vacío y el candado (D6) cerrado.
        auto protegidos = std::make_shared<ProtegidosVigentes>(claves_protegidos_compiladas(),
                                                               config.protegidos.hospital_id, config.protegidos.despliegue_id);
        const bool protegidos_set_ok = protegidos_preparar_set(ipset, config);
        protegidos_cargar_cache(*protegidos, ipset, config, protegidos_set_ok, etcd_client.get());
        const auto& blacklist_ipset = config.ipsets.at("blacklist");

        FIREWALL_LOG_INFO("Configuring IPTables",
            "chain", config.iptables.chain_name,
            "rate_limiting", config.iptables.enable_rate_limiting);

        FirewallConfig firewall_config;
        firewall_config.blacklist_chain = config.iptables.chain_name;
        firewall_config.blacklist_ipset = blacklist_ipset.set_name;  // ✅ Day 52

        // [PROTEGIDOS-MANIFIESTO-D318] exención del kernel solo si el set es hash:net,iface (si no, solo la barrera)
        firewall_config.protegidos_ipset = protegidos_set_ok ? config.protegidos.set_name : std::string();

        firewall_config.enable_rate_limiting = config.iptables.enable_rate_limiting;
        firewall_config.rate_limit_connections = config.iptables.rate_limit_connections;

        FIREWALL_LOG_INFO("Initializing IPTables wrapper");
        IPTablesWrapper iptables;
        iptables.set_dry_run(config.operation.dry_run);

        FIREWALL_LOG_INFO("Setting up IPTables rules");
        if (!iptables.setup_base_rules(firewall_config)) {
            FIREWALL_LOG_ERROR("Failed to setup IPTables rules");
            DUMP_STATE_ON_ERROR("iptables_setup_failed");

            if (!config.operation.dry_run) {
                std::cerr << "[ERROR] Failed to setup IPTables rules" << std::endl;
                return 1;
            }
        }

        FIREWALL_LOG_INFO("IPTables rules configured successfully");

        // [PROTEGIDOS-ANTISPOOF-D320] ADR-060 D8, 8e.4b: antispoofing en raw PREROUTING desde el manifiesto vigente
        EstadoAntispoof antispoof;
        {
            const auto& ac = config.protegidos.antispoof;
            if (config.operation.dry_run) {
                std::cerr << "[PROTEGIDOS-ANTISPOOF] operation.dry_run=true: no se instala (el agente no toca el kernel)"
                          << std::endl;
            } else if (!ac.valido) {
                std::cerr << "[PROTEGIDOS-ANTISPOOF] NO se instala: " << ac.motivo_invalido << std::endl;
            } else if (!protegidos_set_ok) {
                std::cerr << "[PROTEGIDOS-ANTISPOOF] NO se instala: el set " << config.protegidos.set_name
                          << " no es utilizable (ver [PROTEGIDOS-SET-TIPO])" << std::endl;
            } else {
                antispoof.activo = true;
                antispoof.n = {ac.cadena, ac.set_redes, config.protegidos.set_name, ac.set_ips_mac, ac.set_mac,
                               ac.log_por_minuto, ac.log_rafaga, true};
                const auto t = ipset.set_type(ac.set_mac);
                if (!t) {
                    antispoof.n.con_mac = static_cast<bool>(ipset.create_set(mldefender::firewall::config_set_antispoof(
                        ac.set_mac, IPSetType::HASH_IP_MAC,
                        static_cast<uint32_t>(::argus::protegidos::kProtegidosMaxEntradas))));
                }
                if (!antispoof.n.con_mac) {
                    std::cerr << "[PROTEGIDOS-ANTISPOOF] el kernel no admite hash:ip,mac: sin comprobación de MAC (la de "
                                 "interfaz sí)" << std::endl;
                }
                antispoof_aplicar(antispoof, ipset, iptables, *protegidos, config, "arranque");
            }
        }

        // ───────────────────────────────────────────────────────────────────
        // Batch Processor Configuration (Day 52: IPSet names from ipsets)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("Configuring batch processor",
            "batch_size_threshold", config.batch_processor.batch_size_threshold,
            "batch_time_threshold_ms", config.batch_processor.batch_time_threshold_ms,
            "max_pending_ips", config.batch_processor.max_pending_ips,
            "min_confidence", config.batch_processor.min_confidence);

        BatchProcessorConfig batch_config;
        batch_config.batch_size_threshold = config.batch_processor.batch_size_threshold;
        batch_config.batch_time_threshold = std::chrono::milliseconds(config.batch_processor.batch_time_threshold_ms);
        batch_config.max_pending_ips = config.batch_processor.max_pending_ips;
        batch_config.confidence_threshold = config.batch_processor.min_confidence;

        // ✅ Day 52: Assign ipset names from ipsets map
        batch_config.blacklist_ipset = blacklist_ipset.set_name;

        FIREWALL_LOG_INFO("Batch processor ipset configuration",
            "blacklist_ipset", batch_config.blacklist_ipset);

        FIREWALL_LOG_INFO("Initializing batch processor");
        BatchProcessor processor(ipset, batch_config);
        // ── AlertClient config (DEBT-ALERTING-EDGE-SOS-001) ──────────────────
        try {
            std::ifstream falert("/etc/ml-defender/firewall-acl-agent/firewall.json");
            if (falert.good()) batch_config.alerting_json = nlohmann::json::parse(falert);
        } catch (...) {}
        processor.set_irp_config(config.irp);  // ADR-042

    // ── Recidivism config (RECIDIVISM-D276) ──────────────────────────────────
    // Misma logica que la conversion de batch_config de arriba: el JSON
    // se parsea a tipos planos (RecidivismConfigNew) y aqui se convierte
    // al tipo "real" que usa BatchProcessor (RecidivismConfig), con los
    // tipos de chrono/uint32_t que compute_penalty_timeout necesita.
    RecidivismConfig recidivism_config;
    recidivism_config.enabled = config.recidivism.enabled;
    // DAY277-NEVER-PERMANENT: un negativo en el JSON pasaba por static_cast a
    // ~4.29e9 y tumbaba el 'ipset restore'. Ahora negativo -> 0 -> saneado con
    // ERROR visible en set_recidivism_config().
    recidivism_config.strike_durations_sec.clear();
    for (int d : config.recidivism.strike_durations_sec) {
        recidivism_config.strike_durations_sec.push_back(d < 0 ? 0u : static_cast<uint32_t>(d));
    }
    recidivism_config.max_penalty_after_strikes =
        config.recidivism.max_penalty_after_strikes < 0 ? 0u
            : static_cast<uint32_t>(config.recidivism.max_penalty_after_strikes);
    recidivism_config.max_penalty_sec =
        config.recidivism.max_penalty_sec < 0 ? 0u
            : static_cast<uint32_t>(config.recidivism.max_penalty_sec);
    recidivism_config.quiet_period_reset =
        std::chrono::seconds(config.recidivism.quiet_period_reset_sec);
    recidivism_config.max_tracked_ips =
        static_cast<size_t>(config.recidivism.max_tracked_ips);
    recidivism_config.overflow_log_path = config.recidivism.overflow_log_path;
    processor.set_recidivism_config(recidivism_config);  // RECIDIVISM-D276
    processor.set_rangos_protegidos(*protegidos->rangos());  // [DDOS-MITIGACION-B2-D302] barrera (2 puertas); D318: del manifiesto
    {   // [DDOS-MITIGACION-B1-D301] escalera efectiva al log y aviso de castigos de prueba
        std::ostringstream esc;
        for (size_t i = 0; i < recidivism_config.strike_durations_sec.size(); ++i) {
            esc << (i ? ", " : "") << recidivism_config.strike_durations_sec[i];
        }
        std::cout << "[CONFIG] recidivism: enabled=" << (recidivism_config.enabled ? "true" : "false")
                  << " strike_durations_sec=[" << esc.str() << "] max_penalty_after_strikes="
                  << recidivism_config.max_penalty_after_strikes << " max_penalty_sec=" << recidivism_config.max_penalty_sec
                  << " quiet_period_reset_sec=" << config.recidivism.quiet_period_reset_sec
                  << " max_tracked_ips=" << recidivism_config.max_tracked_ips
                  << " (valores pedidos; set_recidivism_config corrige con ERROR/WARN si hace falta)" << std::endl;
        const auto cortos = ::mldefender::firewall::escalones_cortos(
            recidivism_config.strike_durations_sec, static_cast<uint32_t>(config.ddos_mitigacion.aviso_castigo_corto_sec));
        if (!cortos.empty()) {
            std::ostringstream c;
            for (size_t i = 0; i < cortos.size(); ++i) {
                c << (i ? ", " : "") << cortos[i];
            }
            std::cerr << "[CONFIG-AVISO] recidivism.strike_durations_sec tiene escalones por debajo de "
                         "ddos_mitigacion.aviso_castigo_corto_sec=" << config.ddos_mitigacion.aviso_castigo_corto_sec
                      << " s: [" << c.str() << "] = castigo SOLO DE PRUEBAS, no de produccion" << std::endl;
        }
    }
        FIREWALL_LOG_INFO("Batch processor started successfully",
            "irp_auto_isolate", config.irp.auto_isolate,
            "irp_threshold",    config.irp.threat_score_threshold,
            "irp_interface",    config.irp.isolate_interface);

        // DEBT-IRP-AUTOISO-FALSE-001: WARNING prominente cuando IRP desactivado
        if (!config.irp.auto_isolate) {
            FIREWALL_LOG_WARN("════════════════════════════════════════════════════════");
            FIREWALL_LOG_WARN("IRP AUTO-ISOLATE DESACTIVADO (auto_isolate: false)");
            FIREWALL_LOG_WARN("El agente NO aislara el host automaticamente.");
            FIREWALL_LOG_WARN("Para activar: set auto_isolate=true en isolate.json");
            FIREWALL_LOG_WARN("SOLO activar tras onboarding explicito del operador.");
            FIREWALL_LOG_WARN("════════════════════════════════════════════════════════");
        }

        // ───────────────────────────────────────────────────────────────────
        // ZMQ Configuration (Day 50: Enhanced transport logging)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("Configuring ZMQ subscriber",
            "endpoint", config.zmq.endpoint,
            "topic", config.zmq.topic,
            "recv_timeout_ms", config.zmq.recv_timeout_ms);

        ZMQSubscriber::Config zmq_config;
        zmq_config.endpoint = config.zmq.endpoint;
        zmq_config.topic = config.zmq.topic;
        zmq_config.recv_timeout_ms = config.zmq.recv_timeout_ms;
        zmq_config.linger_ms = config.zmq.linger_ms;
        zmq_config.reconnect_interval_ms = config.zmq.reconnect_interval_ms;
        zmq_config.max_reconnect_interval_ms = config.zmq.max_reconnect_interval_ms;
        zmq_config.enable_reconnect = config.zmq.enable_reconnect;
        zmq_config.high_water_mark = config.zmq.high_water_mark;  // BACKLOG-ZMQ-TUNING-001

        // ✅ Day 61: CSV batch logger output directory
        zmq_config.log_directory = config.csv_batch_logger.output_dir;

        // [DDOS-SHADOW-D293] política por víctima en sombra (solo registra)
        zmq_config.ddos_shadow = config.ddos_shadow;
        zmq_config.protegidos = protegidos;  // [PROTEGIDOS-MANIFIESTO-D318] lo vigente (ADR-060)
        zmq_config.ddos_mitigacion = config.ddos_mitigacion;  // [DDOS-MITIGACION-B2-D302]
        zmq_config.dry_run = config.operation.dry_run;        // [DDOS-MITIGACION-B2-D302] 1.a llave
        zmq_config.hmac_key_check_interval_seconds = config.hmac_key_check_interval_seconds;  // [FW-CSV-CLAVE-B2-D316]
        zmq_config.ddos_escalones_cortos = ::mldefender::firewall::escalones_cortos(
            recidivism_config.strike_durations_sec, static_cast<uint32_t>(config.ddos_mitigacion.aviso_castigo_corto_sec));
        std::cout << "[DDOS-MITIGACION] modo: "
                  << (!config.ddos_mitigacion.habilitada ? "DESHABILITADA (sombra pura, no se llama a la mitigacion)"
                      : candado_cerrado(true, protegidos.get())
                      ? "BLOQUEADA POR EL CANDADO (sin manifiesto verificado de protegidos; sombra) [PROTEGIDOS-SIN-MANIFIESTO]"
                      : (config.operation.dry_run ? "DRY_RUN (simula; solo resumen periodico)"
                                                  : "ACTIVA (bloquea en el ipset; una linea por accion)"))
                  << std::endl;
        {
            const auto vig = protegidos->vigente();
            std::cout << "[SOMBRA-DDOS] rangos protegidos ("
                      << (vig ? "manifiesto version " + std::to_string(vig->version) : std::string("NINGUNO: sin manifiesto verificado"))
                      << "):";
            for (const auto& r : protegidos->rangos()->rangos) {
                std::cout << " " << ::argus::protegidos::nombre_categoria(r.cat) << "=" << r.texto;
            }
            std::cout << " (DROP de la cabeza DDoS con origen protegido = ALERTA_PROTEGIDO, nunca bloqueo)" << std::endl;
        }
        std::cout << "[SOMBRA-DDOS] política por víctima " << (config.ddos_shadow.enabled ? "ACTIVA" : "DESACTIVADA")
                  << ": m=" << config.ddos_shadow.m << " k=" << config.ddos_shadow.k << " n=" << config.ddos_shadow.n
                  << " hold_windows=" << config.ddos_shadow.hold_windows << " resumen_s=" << config.ddos_shadow.resumen_s
                  << " lag_max_valid_s=" << config.ddos_shadow.lag_max_valid_s  // [TIMEBASE-D295]
                  << " anomalias_detalle_max=" << config.ddos_shadow.anomalias_detalle_max
                  << " seq_ventana=" << config.ddos_shadow.seq_ventana  // [TIMEBASE-SEQ-D297]
                  << " (solo registra, no bloquea)" << std::endl;  // [DDOS-SHADOW-OBS-D293]

        // Transport configuration (compression)
        if (config.transport.compression.enabled) {
            zmq_config.compression_enabled = true;
            FIREWALL_LOG_INFO("LZ4 decompression enabled",
                "algorithm", config.transport.compression.algorithm);
        } else {
            zmq_config.compression_enabled = false;
            FIREWALL_LOG_INFO("LZ4 decompression disabled");
        }

        // Transport configuration (encryption)
        if (config.transport.encryption.enabled) {
            zmq_config.encryption_enabled = true;

            // [ETCD-CLIENTE-B1-D316] G2: fuera la salida «Encryption enabled but etcd not initialized»: el cifrado de ZMQ
            // sale de seed.bin (SeedClient), no de etcd. Medido DAY316: con ella, sin etcd el firewall no arrancaba.

            // ADR-013 PHASE 2 — DAY 159: crypto_token deprecated.
            // CryptoTransport inicializa desde seed.bin via SeedClient en ZMQSubscriber.
            // DEBT-FIREWALL-CRYPTO-FORMAT-001 FIX
            FIREWALL_LOG_INFO("ChaCha20-Poly1305 decryption via CryptoTransport (seed.bin)",
                "algorithm", config.transport.encryption.algorithm);
        } else {
            zmq_config.encryption_enabled = false;
            FIREWALL_LOG_INFO("Decryption disabled");
        }

        FIREWALL_LOG_INFO("Initializing ZMQ subscriber");
        ZMQSubscriber subscriber(processor, zmq_config, etcd_client.get());

        FIREWALL_LOG_INFO("ZMQ subscriber created",
            "etcd_integration", etcd_client ? "ENABLED" : "DISABLED");

        // Start ZMQ subscriber thread
        FIREWALL_LOG_INFO("Starting ZMQ subscriber thread");
        mldefender::firewall::diagnostics::g_system_state->is_running.store(true);
        std::thread zmq_thread([&subscriber]() {
            subscriber.run();
        });
        zmq_thread.detach();

        FIREWALL_LOG_INFO("ZMQ subscriber initialized and running");

        // ───────────────────────────────────────────────────────────────────
        // Signal Handlers (Day 50: Enhanced)
        // ───────────────────────────────────────────────────────────────────

        setup_signal_handlers();

        // ───────────────────────────────────────────────────────────────────
        // Main Loop (Day 50: Enhanced with diagnostics)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("Firewall ACL Agent is now ACTIVE");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("Configuration summary",
            "zmq_endpoint", config.zmq.endpoint,
            "topic_filter", config.zmq.topic.empty() ? "(all)" : config.zmq.topic,
            "blacklist_ipset", blacklist_ipset.set_name,
            "dry_run", config.operation.dry_run);

        std::cout << "\n[RUNNING] Firewall ACL Agent is now active\n"
                  << "[INFO] Listening on: " << config.zmq.endpoint << "\n"
                  << "[INFO] Topic filter: " << (config.zmq.topic.empty() ? "(all)" : config.zmq.topic) << "\n"
                  << "[INFO] Press Ctrl+C to stop\n"
                  << std::endl;

        auto last_health_check = std::chrono::steady_clock::now();
        auto last_protegidos = std::chrono::steady_clock::now();  // [PROTEGIDOS-MANIFIESTO-D318] D6/D7/D-C
        auto last_consulta = std::chrono::steady_clock::now();    // [PROTEGIDOS-MANIFIESTO-D318] 8e.3c (F-E)
        auto last_vigia = std::chrono::steady_clock::now();       // [PROTEGIDOS-VIGIA-D320] 8e.4a (D8)
        // (antispoofing: estado en 'antispoof', declarado al configurar iptables) [PROTEGIDOS-ANTISPOOF-D320]
        ContadoresVigia vigia_cv;
        if (config.operation.dry_run) {
            std::cerr << "[PROTEGIDOS-VIGIA] operation.dry_run=true: el agente no toca el kernel y el vigía no compara "
                         "set ni reglas (se avisa cada aviso_sec)" << std::endl;
        } else {
            std::cout << "[PROTEGIDOS-VIGIA] kernel <-> manifiesto cada " << config.protegidos.comprobacion_kernel_sec
                      << " s (set " << config.protegidos.set_name << (protegidos_set_ok ? "" : " NO utilizable: solo reglas")
                      << ", cadena " << firewall_config.blacklist_chain << ")" << std::endl;
        }
        auto last_aviso_consulta = std::chrono::steady_clock::time_point{};
        uint64_t consultas_fallidas = 0;
        auto last_metrics_export = std::chrono::steady_clock::now();

        while (g_running.load() &&
               mldefender::firewall::diagnostics::g_system_state->is_running.load()) {

            auto now = std::chrono::steady_clock::now();

            try {
                // Health checks every 30 seconds
                auto elapsed_health = std::chrono::duration_cast<std::chrono::seconds>(
                    now - last_health_check).count();

                if (std::chrono::duration_cast<std::chrono::seconds>(now - last_protegidos).count() >=
                    config.protegidos.aviso_sec) {
                    protegidos_vigilar(*protegidos, config);  // [PROTEGIDOS-MANIFIESTO-D318]
                    if (config.operation.dry_run) {  // [PROTEGIDOS-VIGIA-D320]
                        std::cerr << "[PROTEGIDOS-VIGIA] dry_run: no se compara el kernel con el manifiesto" << std::endl;
                    } else {
                        std::cout << "[PROTEGIDOS-VIGIA] comprobaciones=" << vigia_cv.comprobaciones
                                  << " divergencias=" << vigia_cv.divergencias
                                  << " reconciliaciones=" << vigia_cv.reconciliaciones << " fallos=" << vigia_cv.fallos
                                  << std::endl;
                    }
                    if (antispoof.activo) {  // [PROTEGIDOS-ANTISPOOF-D320]
                        std::cout << "[PROTEGIDOS-ANTISPOOF] modo=" << (antispoof.descarta ? "descarta" : "cuenta")
                                  << " version=" << antispoof.version << " redes=" << antispoof.reparto.redes.size()
                                  << " spoofing_interfaz=" << antispoof.total_if << " spoofing_mac=" << antispoof.total_mac
                                  << " sin_ruta=" << antispoof.reparto.sin_ruta.size() << std::endl;
                        for (const auto& x : antispoof.reparto.sin_ruta) {
                            std::cerr << "[PROTEGIDOS-RUTA] " << ::argus::protegidos::detalle_protegidos::saneado(x)
                                      << ": esa red no se cuenta ni se descarta (periódico)" << std::endl;
                        }
                    } else if (!config.operation.dry_run && !config.protegidos.antispoof.valido) {
                        std::cerr << "[PROTEGIDOS-ANTISPOOF] NO instalado: " << config.protegidos.antispoof.motivo_invalido
                                  << " (periódico)" << std::endl;
                    }
                    last_protegidos = now;
                }
                if (!config.protegidos.hospital_id.empty() && !config.protegidos.despliegue_id.empty() &&
                    std::chrono::duration_cast<std::chrono::seconds>(now - last_consulta).count() >=
                        config.protegidos.consulta_sec) {
                    std::string fallo;  // [PROTEGIDOS-MANIFIESTO-D318] 8e.3c: un aviso cada aviso_sec, no uno por consulta
                    const bool respondio =
                        protegidos_consultar(*protegidos, etcd_client.get(), ipset, config, protegidos_set_ok, fallo);
                    if (!fallo.empty()) {
                        if (!respondio) ++consultas_fallidas;
                        if (std::chrono::duration_cast<std::chrono::seconds>(now - last_aviso_consulta).count() >=
                            config.protegidos.aviso_sec) {
                            std::cerr << "[PROTEGIDOS-CONSULTA] " << fallo << " (fallidas=" << consultas_fallidas
                                      << "; se conserva lo vigente)" << std::endl;
                            last_aviso_consulta = now;
                        }
                    }
                    last_consulta = now;
                }

                if (antispoof.activo) {  // [PROTEGIDOS-ANTISPOOF-D320] manifiesto o modo nuevos: se aplican enseguida
                    const auto mv = protegidos->vigente();
                    const uint64_t ver = mv ? mv->version : 0;
                    const bool desc = antispoof_descarta(*protegidos, config);
                    if (ver != antispoof.version || desc != antispoof.descarta) {
                        antispoof_aplicar(antispoof, ipset, iptables, *protegidos, config,
                                          ver != antispoof.version
                                              ? "manifiesto version " + std::to_string(antispoof.version) + " -> " +
                                                    std::to_string(ver)
                                              : std::string("modo ") + (antispoof.descarta ? "descarta" : "cuenta") +
                                                    " -> " + (desc ? "descarta" : "cuenta"));
                    }
                }

                if (!config.operation.dry_run &&  // [PROTEGIDOS-VIGIA-D320] 8e.4a (D8)
                    std::chrono::duration_cast<std::chrono::seconds>(now - last_vigia).count() >=
                        config.protegidos.comprobacion_kernel_sec) {
                    protegidos_vigia(*protegidos, ipset, iptables, firewall_config, config, protegidos_set_ok, vigia_cv);
                    if (antispoof.activo) {  // [PROTEGIDOS-ANTISPOOF-D320] 8e.4b
                        antispoof_vigia(antispoof, ipset, iptables, *protegidos, config, vigia_cv);
                    }
                    last_vigia = now;
                }

                if (elapsed_health >= 30) {
                    perform_health_checks(config, ipset, iptables, subscriber);
                    last_health_check = now;
                }

                // Metrics export every 30 seconds
                auto elapsed_metrics = std::chrono::duration_cast<std::chrono::seconds>(
                    now - last_metrics_export).count();

                if (elapsed_metrics >= 30) {
                    export_metrics(config, subscriber, processor);
                    last_metrics_export = now;
                }

            } catch (const std::exception& e) {
                FIREWALL_LOG_ERROR("Exception in main loop",
                    "error", e.what());
                DUMP_STATE_ON_ERROR("main_loop_exception");
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }

        // ───────────────────────────────────────────────────────────────────
        // Graceful Shutdown (Day 50: Enhanced)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("Initiating graceful shutdown");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        std::cout << "\n[SHUTDOWN] Stopping components..." << std::endl;

#ifdef PLUGIN_LOADER_ENABLED
        if (plugin_loader) {
            plugin_loader->shutdown();
            std::cout << "[INFO] plugin-loader: shutdown OK" << std::endl;
        }
#endif

        // Detener AutonomySubscriber antes de shutdown
        if (autonomy_sub && autonomy_sub->is_running()) {
            autonomy_sub->stop();
            FIREWALL_LOG_INFO("AutonomySubscriber stopped");
        }

        // Export final metrics
        export_metrics(config, subscriber, processor);
        FIREWALL_LOG_INFO("Final metrics exported");

        // Display final statistics
        const auto& zmq_stats = subscriber.get_stats();

        FIREWALL_LOG_INFO("Final statistics",
            "messages_received", zmq_stats.messages_received.load(),
            "detections_processed", zmq_stats.detections_processed.load(),
            "parse_errors", zmq_stats.parse_errors.load(),
            "reconnections", zmq_stats.reconnects.load());

        std::cout << "\n[STATS] Final Statistics:\n"
                  << "  Messages Received:     " << zmq_stats.messages_received.load() << "\n"
                  << "  Detections Processed:  " << zmq_stats.detections_processed.load() << "\n"
                  << "  Parse Errors:          " << zmq_stats.parse_errors.load() << "\n"
                  << "  Reconnections:         " << zmq_stats.reconnects.load() << "\n"
                  << std::endl;

        // Final state dump
        DUMP_STATE_ON_ERROR("clean_shutdown");

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("Firewall ACL Agent stopped cleanly");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        std::cout << "[SHUTDOWN] ✓ Firewall ACL Agent stopped cleanly" << std::endl;

    } catch (const std::exception& e) {
        FIREWALL_LOG_CRASH("Fatal exception in main",
            "error", e.what());
        DUMP_STATE_ON_ERROR("fatal_exception");

        std::cerr << "[FATAL] Exception: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
