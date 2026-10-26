#pragma once
// sniffer/include/flow_table_config.hpp — [FLOW-TABLE-D308]
// Configuracion de la tabla de flujos del sniffer (ShardedFlowManager): un solo sitio, la seccion "flow_table" de
// sniffer.json (DEBT-SNIFFER-FLOWTABLE-CONFIG-001). Politica de Alonso (DAY291/DAY300/DAY308): el JSON es la ley y se
// lee SIEMPRE; si un campo falta, no es entero o esta fuera de rango, se usa el DEFECTO validado de
// flow_table_params.hpp (los mismos valores que trae sniffer.json), se avisa con [CONFIG-DEFAULT] y el sniffer arranca igual. La linea
// [FLOW-TABLE] del arranque dice el valor de cada campo y de donde sale (JSON o DEFECTO, y por que).
// Sin estado y sin dependencias del resto del sniffer, para probarlo suelto (tests/test_flow_expiry.cpp), como
// heads_config.hpp (DAY305).
#include "flow_table_params.hpp"
#include <json/json.h>
#include <cstdint>
#include <iostream>
#include <string>

namespace argus::flowtable {

namespace detalle {
// Entero en [mn, mx] (o 0 si cero_vale): solo tipos enteros de JSON (un 300.0 o un "300" no valen). Devuelve el
// origen del valor para la linea [FLOW-TABLE].
inline std::string leer(const Json::Value& blk, const char* clave, uint64_t def, uint64_t mn, uint64_t mx,
                        bool cero_vale, uint64_t& out, int& n_defectos, std::ostream& aviso) {
    const std::string formato = std::string("entero en [") + std::to_string(mn) + ", " + std::to_string(mx) + "]" +
                                (cero_vale ? " o 0 (sin tope)" : "");
    out = def;
    if (!blk.isObject() || !blk.isMember(clave)) {
        aviso << "[CONFIG-DEFAULT] flow_table." << clave << " ausente (" << formato << "): se usa " << def
              << std::endl;
        ++n_defectos;
        return "DEFECTO: ausente";
    }
    const Json::Value& v = blk[clave];
    const bool entero = v.type() == Json::intValue || v.type() == Json::uintValue;
    if (!entero) {
        aviso << "[CONFIG-DEFAULT] flow_table." << clave << " no es entero (" << formato << "): se usa " << def
              << std::endl;
        ++n_defectos;
        return "DEFECTO: no entero";
    }
    const bool negativo = v.type() == Json::intValue && v.asLargestInt() < 0;
    const uint64_t x = negativo ? 0 : static_cast<uint64_t>(v.asLargestUInt());
    if (negativo || !((cero_vale && x == 0) || (x >= mn && x <= mx))) {
        aviso << "[CONFIG-DEFAULT] flow_table." << clave << "=" << (negativo ? std::to_string(v.asLargestInt())
                                                                              : std::to_string(x))
              << " fuera de rango (" << formato << "): se usa " << def << std::endl;
        ++n_defectos;
        return "DEFECTO: fuera de rango";
    }
    out = x;
    return "JSON";
}
}  // namespace detalle

// Lee la seccion "flow_table" de la raiz de sniffer.json. Avisa ademas con [CONFIG-OBSOLETO] de los campos de la
// tabla que ya no se usan desde DAY308 (sus valores nunca llegaron a la tabla: si siguen en un JSON, el admin cree
// configurado algo que no lo esta).
inline FlowTableParams parse_flow_table(const Json::Value& root, std::ostream& aviso = std::cerr,
                                        std::ostream& info = std::cout) {
    static const Json::Value kVacio(Json::objectValue);
    const bool raiz_ok = root.isObject();
    const Json::Value& blk = (raiz_ok && root.isMember("flow_table") && root["flow_table"].isObject())
                                 ? root["flow_table"] : kVacio;
    if (raiz_ok && root.isMember("flow_table") && !root["flow_table"].isObject()) {
        aviso << "[CONFIG-DEFAULT] flow_table no es un objeto: se usan los defectos de todos sus campos" << std::endl;
    }
    const FlowTableParams d{};
    FlowTableParams p{};
    int n = 0;
    std::string o_shards = detalle::leer(blk, "shards", d.shards, kShardsMin, kShardsMax, false, p.shards, n, aviso);
    std::string o_max = detalle::leer(blk, "max_flows_per_shard", d.max_flows_per_shard, kMaxFlowsMin, kMaxFlowsMax,
                                      false, p.max_flows_per_shard, n, aviso);
    std::string o_idle = detalle::leer(blk, "idle_timeout_s", d.idle_timeout_s, kIdleMin, kIdleMax, false,
                                       p.idle_timeout_s, n, aviso);
    std::string o_act = detalle::leer(blk, "active_timeout_s", d.active_timeout_s, kActiveMin, kActiveMax, true,
                                      p.active_timeout_s, n, aviso);
    std::string o_limp = detalle::leer(blk, "cleanup_interval_ms", d.cleanup_interval_ms, kCleanupMin, kCleanupMax,
                                       false, p.cleanup_interval_ms, n, aviso);
    std::string o_log = detalle::leer(blk, "log_interval_s", d.log_interval_s, kLogMin, kLogMax, false,
                                      p.log_interval_s, n, aviso);
    if (!regla_limpieza_ok(p)) {
        aviso << "[CONFIG-DEFAULT] regla idle_timeout_s * 1000 > cleanup_interval_ms rota (idle_timeout_s="
              << p.idle_timeout_s << ", cleanup_interval_ms=" << p.cleanup_interval_ms << "): se usan "
              << d.idle_timeout_s << " y " << d.cleanup_interval_ms << std::endl;
        p.idle_timeout_s = d.idle_timeout_s;
        p.cleanup_interval_ms = d.cleanup_interval_ms;
        o_idle = o_limp = "DEFECTO: regla con cleanup_interval_ms";
        ++n;
    }
    if (!regla_tope_ok(p)) {
        aviso << "[CONFIG-DEFAULT] regla active_timeout_s = 0 o >= idle_timeout_s rota (active_timeout_s="
              << p.active_timeout_s << ", idle_timeout_s=" << p.idle_timeout_s << "): se usa active_timeout_s="
              << d.active_timeout_s << " (sin tope)" << std::endl;
        p.active_timeout_s = d.active_timeout_s;
        o_act = "DEFECTO: regla con idle_timeout_s";
        ++n;
    }
    if (raiz_ok) {
        const Json::Value& ks = root["kernel_space"];
        if (ks.isObject() && ks.isMember("flow_timeout_seconds")) {
            aviso << "[CONFIG-OBSOLETO] kernel_space.flow_timeout_seconds ya no se usa desde DAY308 (nunca llego a la "
                     "tabla de flujos): la inactividad se configura en flow_table.idle_timeout_s. Se ignora."
                  << std::endl;
        }
        const Json::Value& pr = root["processing"];
        if (pr.isObject() && pr["feature_extraction"].isObject() &&
            pr["feature_extraction"].isMember("flow_timeout_seconds")) {
            aviso << "[CONFIG-OBSOLETO] processing.feature_extraction.flow_timeout_seconds ya no se usa desde DAY308 "
                     "(nunca llego a la tabla de flujos): la inactividad se configura en flow_table.idle_timeout_s. "
                     "Se ignora." << std::endl;
        }
        if (root.isMember("user_space")) {
            aviso << "[CONFIG-OBSOLETO] seccion user_space (flow_table_size, gc_interval_seconds, ...) ya no se usa "
                     "desde DAY308 (nunca llego a la tabla de flujos): la tabla se configura en flow_table. Se ignora."
                  << std::endl;
        }
    }
    if (n > 0) {
        aviso << "[CONFIG-DEFAULT] " << n << " ajustes con valor por defecto en flow_table: revisar sniffer.json"
              << std::endl;
    }
    info << "[FLOW-TABLE] shards=" << p.shards << " (" << o_shards << ") max_flows_per_shard=" << p.max_flows_per_shard
         << " (" << o_max << ") capacidad=" << p.shards * p.max_flows_per_shard << " idle_timeout_s="
         << p.idle_timeout_s << " (" << o_idle << ") active_timeout_s=" << p.active_timeout_s
         << (p.active_timeout_s == 0 ? " sin tope" : "") << " (" << o_act << ") cleanup_interval_ms="
         << p.cleanup_interval_ms << " (" << o_limp << ") log_interval_s=" << p.log_interval_s << " (" << o_log << ")"
         << std::endl;
    return p;
}

}  // namespace argus::flowtable
