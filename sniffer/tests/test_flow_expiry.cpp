// sniffer/tests/test_flow_expiry.cpp — [FLOW-TABLE-D308]
// Caducidad de la tabla de flujos (DEBT-SNIFFER-FLOW-EXPIRY-001, DEBT-SNIFFER-FLOWTABLE-CONFIG-001):
//   1. lector de la seccion flow_table de sniffer.json (flow_table_config.hpp): valor del JSON y su origen, defecto
//      + [CONFIG-DEFAULT] si falta, no es entero o esta fuera de rango, reglas cruzadas, [CONFIG-OBSOLETO];
//   2. ShardedFlowManager: limpieza por inactividad desde la cola de la LRU, tope de duracion activa (el flujo
//      vuelve a cero y el paquete abre el nuevo), guarda de should_expire, desalojo LRU contado, marcas futuras
//      contadas, y el matiz de la LRU con marcas desordenadas.
// Sin gtest: imprime cada fallo y devuelve 1 si hay alguno.
#include "flow/sharded_flow_manager.hpp"
#include "flow_manager.hpp"
#include "flow_table_config.hpp"
#include "main.h"

#include <cstdint>
#include <cstdio>
#include <limits>
#include <sstream>
#include <string>

using namespace sniffer;
using namespace sniffer::flow;
namespace ft = ::argus::flowtable;

namespace {

int g_fallos = 0;
int g_pruebas = 0;

void comprobar(bool ok, const char* que) {
    ++g_pruebas;
    if (!ok) {
        ++g_fallos;
        std::printf("FALLO: %s\n", que);
    }
}

bool contiene(const std::string& s, const std::string& sub) { return s.find(sub) != std::string::npos; }

int cuenta(const std::string& s, const std::string& sub) {
    int n = 0;
    for (size_t p = s.find(sub); p != std::string::npos; p = s.find(sub, p + 1)) ++n;
    return n;
}

Json::Value json(const std::string& texto) {
    Json::Value v;
    Json::CharReaderBuilder b;
    std::string err;
    std::istringstream in(texto);
    if (!Json::parseFromStream(b, in, &v, &err)) {
        std::printf("FALLO: JSON de prueba mal escrito: %s\n", err.c_str());
        ++g_fallos;
    }
    return v;
}

struct Lectura {
    ft::FlowTableParams p;
    std::string aviso, info;
};

Lectura leer(const std::string& texto) {
    std::ostringstream a, i;
    Lectura l;
    l.p = ft::parse_flow_table(json(texto), a, i);
    l.aviso = a.str();
    l.info = i.str();
    return l;
}

void pruebas_lector() {
    // valido completo: todo del JSON, sin avisos
    {
        const auto l = leer(R"({"flow_table": {"shards": 8, "max_flows_per_shard": 5000, "idle_timeout_s": 120,
                               "active_timeout_s": 600, "cleanup_interval_ms": 500, "log_interval_s": 30}})");
        comprobar(l.p.shards == 8 && l.p.max_flows_per_shard == 5000 && l.p.idle_timeout_s == 120 &&
                      l.p.active_timeout_s == 600 && l.p.cleanup_interval_ms == 500 && l.p.log_interval_s == 30,
                  "lector: valores validos del JSON");
        comprobar(l.aviso.empty(), "lector: sin avisos con un JSON valido");
        comprobar(cuenta(l.info, "(JSON)") == 6 && contiene(l.info, "capacidad=40000"),
                  "lector: [FLOW-TABLE] con los 6 campos de origen JSON y la capacidad");
    }
    // seccion ausente: todos los defectos, con aviso por campo y resumen
    {
        const auto l = leer(R"({"timebase": {}})");
        const ft::FlowTableParams d{};
        comprobar(l.p.shards == d.shards && l.p.max_flows_per_shard == d.max_flows_per_shard &&
                      l.p.idle_timeout_s == 300 && l.p.active_timeout_s == 0 && l.p.cleanup_interval_ms == 1000 &&
                      l.p.log_interval_s == 60,
                  "lector: defectos con la seccion ausente (300 s, sin tope, 1000 ms, 60 s)");
        comprobar(cuenta(l.aviso, "[CONFIG-DEFAULT] flow_table.") == 6 &&
                      contiene(l.aviso, "6 ajustes con valor por defecto en flow_table"),
                  "lector: un aviso por campo ausente y el resumen");
        comprobar(cuenta(l.info, "(DEFECTO: ausente)") == 6 && contiene(l.info, "sin tope"),
                  "lector: [FLOW-TABLE] dice que cada valor sale del defecto");
    }
    // mal formados: texto, real, cero, negativo, fuera de rango
    {
        const auto l = leer(R"({"flow_table": {"shards": "16", "max_flows_per_shard": 10000.0, "idle_timeout_s": 0,
                               "active_timeout_s": -5, "cleanup_interval_ms": 99, "log_interval_s": 3601}})");
        const ft::FlowTableParams d{};
        comprobar(l.p.shards == d.shards && l.p.max_flows_per_shard == d.max_flows_per_shard &&
                      l.p.idle_timeout_s == d.idle_timeout_s && l.p.active_timeout_s == d.active_timeout_s &&
                      l.p.cleanup_interval_ms == d.cleanup_interval_ms && l.p.log_interval_s == d.log_interval_s,
                  "lector: defectos para texto, real, cero, negativo y fuera de rango");
        comprobar(cuenta(l.info, "(DEFECTO: no entero)") == 2 && cuenta(l.info, "(DEFECTO: fuera de rango)") == 4,
                  "lector: origen de cada defecto (2 no entero, 4 fuera de rango)");
        comprobar(contiene(l.aviso, "entero en [1, 256]") && contiene(l.aviso, "o 0 (sin tope)"),
                  "lector: el aviso dice formato y limites");
    }
    // regla: idle_timeout_s * 1000 > cleanup_interval_ms
    {
        const auto l = leer(R"({"flow_table": {"shards": 16, "max_flows_per_shard": 10000, "idle_timeout_s": 30,
                               "active_timeout_s": 0, "cleanup_interval_ms": 60000, "log_interval_s": 60}})");
        comprobar(l.p.idle_timeout_s == 300 && l.p.cleanup_interval_ms == 1000,
                  "lector: regla limpieza rota -> defectos de idle y cleanup");
        comprobar(contiene(l.aviso, "regla idle_timeout_s * 1000 > cleanup_interval_ms rota"),
                  "lector: aviso de la regla de limpieza");
    }
    // regla: active_timeout_s = 0 o >= idle_timeout_s
    {
        const auto l = leer(R"({"flow_table": {"shards": 16, "max_flows_per_shard": 10000, "idle_timeout_s": 300,
                               "active_timeout_s": 100, "cleanup_interval_ms": 1000, "log_interval_s": 60}})");
        comprobar(l.p.active_timeout_s == 0 && l.p.idle_timeout_s == 300, "lector: regla tope rota -> sin tope");
        comprobar(contiene(l.info, "(DEFECTO: regla con idle_timeout_s)"), "lector: origen de la regla del tope");
    }
    // campos obsoletos
    {
        const auto l = leer(R"({"kernel_space": {"flow_timeout_seconds": 300},
                               "processing": {"feature_extraction": {"flow_timeout_seconds": 300}},
                               "user_space": {"flow_table_size": 1000000},
                               "flow_table": {"shards": 16, "max_flows_per_shard": 10000, "idle_timeout_s": 300,
                               "active_timeout_s": 0, "cleanup_interval_ms": 1000, "log_interval_s": 60}})");
        comprobar(cuenta(l.aviso, "[CONFIG-OBSOLETO]") == 3, "lector: tres avisos [CONFIG-OBSOLETO]");
        comprobar(!contiene(l.aviso, "[CONFIG-DEFAULT]"), "lector: los obsoletos no tocan los valores de flow_table");
    }
}

constexpr uint64_t S = 1'000'000'000ULL;  // un segundo en ns

SimpleEvent paquete(uint32_t id, uint64_t ts) {
    SimpleEvent e{};
    e.src_ip = 0x0A000000u | id;
    e.dst_ip = 0x0A800001;
    e.src_port = static_cast<uint16_t>(1024 + id);
    e.dst_port = 53;
    e.protocol = 17;
    e.packet_len = 100;
    e.ip_header_len = 20;
    e.l4_header_len = 8;
    e.timestamp = ts;
    return e;
}

FlowKey clave(uint32_t id) {
    const SimpleEvent e = paquete(id, 0);
    return FlowKey{.src_ip = e.src_ip, .dst_ip = e.dst_ip, .src_port = e.src_port, .dst_port = e.dst_port,
                   .protocol = e.protocol};
}

void meter(uint32_t id, uint64_t ts) { ShardedFlowManager::instance().add_packet(clave(id), paquete(id, ts)); }

bool existe(uint32_t id) { return ShardedFlowManager::instance().get_flow_stats_copy(clave(id)).has_value(); }

// Hora maxima: caduca todo, tambien flujos con marcas en el futuro de la maquina (prueba de marcas futuras).
void vaciar() { ShardedFlowManager::instance().cleanup_expired_flows(std::numeric_limits<uint64_t>::max()); }

void pruebas_tabla() {
    // un shard (orden de la LRU determinista), 4 flujos, inactividad 10 s, tope activo 60 s
    auto& mgr = ShardedFlowManager::instance();
    mgr.initialize(ShardedFlowManager::Config{.shard_count = 1, .max_flows_per_shard = 4,
                                              .idle_timeout_ns = 10 * S, .active_timeout_ns = 60 * S});
    // guarda de should_expire: una ultima marca posterior a la hora no caduca
    {
        FlowStatistics f;
        f.add_packet(paquete(99, 500 * S), clave(99));
        comprobar(!f.should_expire(100 * S, 10 * S), "should_expire: marca futura no caduca (antes daba la vuelta)");
        comprobar(f.should_expire(511 * S, 10 * S) && !f.should_expire(509 * S, 10 * S),
                  "should_expire: caduca solo pasada la inactividad");
    }
    // inactividad desde la cola: A, B, C a 100, 101, 102 s; a 111,5 s caducan A y B
    {
        mgr.take_counters();
        meter(1, 100 * S);
        meter(2, 101 * S);
        meter(3, 102 * S);
        const size_t n = mgr.cleanup_expired_flows(111 * S + S / 2);
        const auto c = mgr.take_counters();
        comprobar(n == 2 && !existe(1) && !existe(2) && existe(3), "inactividad: caducan A y B, queda C");
        comprobar(c.caducados == 2 && c.vivos == 1, "inactividad: contadores caducados=2 vivos=1");
        vaciar();
    }
    // tope activo: E empieza a 200 s; a 230 s sigue; a 261 s (61 s > 60) se cierra y el paquete abre el nuevo
    {
        mgr.take_counters();
        meter(5, 200 * S);
        meter(5, 230 * S);
        auto antes = mgr.get_flow_stats_copy(clave(5));
        meter(5, 261 * S);
        auto despues = mgr.get_flow_stats_copy(clave(5));
        const auto c = mgr.take_counters();
        comprobar(antes && antes->spkts == 2 && antes->flow_start_ns == 200 * S, "tope: antes del corte, 2 paquetes");
        comprobar(despues && despues->spkts == 1 && despues->flow_start_ns == 261 * S &&
                      despues->iat_all.pairs == 0 && despues->len_all.max == 100,
                  "tope: el flujo vuelve a cero y el paquete abre el nuevo");
        comprobar(c.cortes_tope == 1, "tope: cortes_tope=1");
        vaciar();
    }
    // desalojo LRU con el shard lleno: 5 flujos en 4 huecos; se va el mas antiguo y se cuenta
    {
        mgr.take_counters();
        for (uint32_t id = 10; id < 15; ++id) meter(id, (300 + id) * S);
        const auto c = mgr.take_counters();
        comprobar(c.desalojos_lru == 1 && !existe(10) && existe(14) && c.vivos == 4,
                  "desalojo: 1 contado, se va el mas antiguo, quedan 4");
        vaciar();
    }
    // marca futura: un paquete con marca posterior a la hora de la tabla se cuenta
    {
        mgr.take_counters();
        meter(20, mgr.now_ns() + 1'000 * S);
        const auto c = mgr.take_counters();
        comprobar(c.marcas_futuras == 1, "marcas futuras: contada");
        vaciar();
    }
    // LRU por llegada, no por marca: F llega primero con marca 300 s, G despues con marca 290 s. A 305 s la cola es F
    // (no caducada) y la limpieza para: G (caducada) espera. A 311 s caducan las dos.
    {
        meter(30, 300 * S);
        meter(31, 290 * S);
        const size_t n1 = mgr.cleanup_expired_flows(305 * S);
        const bool g_sigue = existe(31);
        const size_t n2 = mgr.cleanup_expired_flows(311 * S);
        comprobar(n1 == 0 && g_sigue, "LRU: con la cola viva, un caducado detras espera a otra pasada");
        comprobar(n2 == 2 && !existe(30) && !existe(31), "LRU: en la pasada siguiente caducan los dos");
        vaciar();
    }
}

}  // namespace

int main() {
    pruebas_lector();
    pruebas_tabla();
    std::printf("%s test_flow_expiry: %d pruebas, %d fallos\n", g_fallos == 0 ? "OK" : "FALLO", g_pruebas, g_fallos);
    return g_fallos == 0 ? 0 : 1;
}
