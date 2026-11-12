#!/usr/bin/env python3
# d318_8e3c_consulta_protegidos.py — DAY318, ADR-060 paso 8e.3c [PROTEGIDOS-MANIFIESTO-D318] (F-E, F-F): el firewall-acl-agent
# pide el manifiesto al etcd-server (GET /v1/protegidos, metodo nuevo del etcd-client) al arrancar y cada
# protegidos.consulta_sec; uno nuevo y verificado se aplica, se guarda y deja [INFRA-CAMBIO] con altas y bajas; uno mas
# viejo se rechaza. Anti-rollback entre reinicios: <manifiesto_cache>.version con la version mas alta aplicada.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_8e3c_consulta_protegidos.py --check|--apply <raíz>
# Todo o nada e idempotente: un fichero NUEVO se crea si no existe y se da por hecho si ya tiene su sha256; uno BORRADO
# se borra si tiene el sha256 esperado y se da por hecho si ya no está; cada CAMBIO se aplica si su texto viejo aparece
# una vez y se da por hecho si ya está el nuevo. Si algo no cuadra, no se escribe nada. Imprime los sha256.
import hashlib
import os
import sys

NUEVOS = []

BORRADOS = []

CAMBIOS = {
    'etcd-client/include/etcd_client/etcd_client.hpp': [
        ('    std::optional<std::vector<uint8_t>> get_hmac_key(const std::string& key_path);\n\n    /**\n     * @brief Compute HMAC-SHA256 over data\n',
         '    std::optional<std::vector<uint8_t>> get_hmac_key(const std::string& key_path);\n\n    // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3c: GET /v1/protegidos (mismo transporte mTLS y conmutación de direcciones).\n    // Devuelve el status HTTP (0 = ningún etcd-server respondió) y, con 200, el sobre tal cual en cuerpo; si no, el\n    // error o la respuesta del servidor. No interpreta nada: verifica el firewall.\n    int get_protegidos(std::string& cuerpo);\n\n    /**\n     * @brief Compute HMAC-SHA256 over data\n'),
    ],
    'etcd-client/src/etcd_client.cpp': [
        ('\nServicePaths EtcdClient::get_service_paths() const {\n',
         '\n// [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3c\nint EtcdClient::get_protegidos(std::string& cuerpo) {\n    auto r = pImpl->transporte_.peticion("GET", "/v1/protegidos");\n    cuerpo = r.status == 0 ? r.error : r.body;\n    return r.status;\n}\n\nServicePaths EtcdClient::get_service_paths() const {\n'),
    ],
    'firewall-acl-agent/config/firewall.json': [
        ('  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060. Los rangos que aRGus NUNCA bloquea salen SOLO del manifiesto firmado de protegidos (Vault transit del hospital; clave publica compilada en el agente): aqui no hay rangos. Un DROP de la cabeza DDoS cuyo ORIGEN cae en un rango del manifiesto se registra como [SOMBRA-DDOS] ALERTA_PROTEGIDO y nunca se bloquea (la barrera protege por IP, entre por la interfaz que entre). En el kernel, el set hash:net,iface set_name (lo crea y lo escribe solo el agente, por sustitucion atomica) exime cada rango por su interfaz de entrada: --match-set <set> src,src -j RETURN. CANDADO: con ddos_mitigacion.habilitada=true y sin manifiesto verificado la mitigacion no actua ([PROTEGIDOS-SIN-MANIFIESTO] al arrancar y cada aviso_sec). hospital_id y despliegue_id: [a-z0-9-], de 1 a 64, sin defecto (ausentes o mal formados = sin manifiesto, candado cerrado). set_name: [A-Za-z0-9_-], de 1 a 29 (defecto ml_defender_protegidos). manifiesto_cache: ruta absoluta del ultimo manifiesto verificado (defecto /var/lib/ml-defender/firewall/protegidos.manifiesto). aviso_sec: entero en [30, 86400] (defecto 300), avisos periodicos y nueva verificacion de la cache. Cada valor se registra con [CONFIG], [CONFIG-DEFAULT] o [CONFIG-AVISO].",\n    "_doc_laboratorio": "VALORES DE LABORATORIO (ADR-060 E3): hospital-lab / lab-vagrant. El manifiesto del lab lo firma argus-infra en la VM etcd (pasos 8e.3 y 8e.5). Nunca copiar estos valores a produccion.",\n    "hospital_id": "hospital-lab",\n    "despliegue_id": "lab-vagrant",\n    "set_name": "ml_defender_protegidos",\n    "manifiesto_cache": "/var/lib/ml-defender/firewall/protegidos.manifiesto",\n    "aviso_sec": 300\n  },\n',
         '  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060. Los rangos que aRGus NUNCA bloquea salen SOLO del manifiesto firmado de protegidos (Vault transit del hospital; clave publica compilada en el agente): aqui no hay rangos. Un DROP de la cabeza DDoS cuyo ORIGEN cae en un rango del manifiesto se registra como [SOMBRA-DDOS] ALERTA_PROTEGIDO y nunca se bloquea (la barrera protege por IP, entre por la interfaz que entre). En el kernel, el set hash:net,iface set_name (lo crea y lo escribe solo el agente, por sustitucion atomica) exime cada rango por su interfaz de entrada: --match-set <set> src,src -j RETURN. CANDADO: con ddos_mitigacion.habilitada=true y sin manifiesto verificado la mitigacion no actua ([PROTEGIDOS-SIN-MANIFIESTO] al arrancar y cada aviso_sec). hospital_id y despliegue_id: [a-z0-9-], de 1 a 64, sin defecto (ausentes o mal formados = sin manifiesto, candado cerrado). set_name: [A-Za-z0-9_-], de 1 a 29 (defecto ml_defender_protegidos). manifiesto_cache: ruta absoluta del ultimo manifiesto verificado (defecto /var/lib/ml-defender/firewall/protegidos.manifiesto). aviso_sec: entero en [30, 86400] (defecto 300), avisos periodicos y nueva verificacion de la cache. consulta_sec: entero en [5, 3600] (defecto 30), cada cuanto se pide el manifiesto al etcd-server (GET /v1/protegidos); el mismo que el vigente no hace nada, uno nuevo y verificado se aplica ([INFRA-CAMBIO] con altas y bajas) y se guarda en la cache, uno con version menor se rechaza; sin respuesta, se conserva lo vigente y se avisa cada aviso_sec. Anti-rollback entre reinicios: <manifiesto_cache>.version guarda la version mas alta aplicada y una cache mas vieja se rechaza al arrancar. Cada valor se registra con [CONFIG], [CONFIG-DEFAULT] o [CONFIG-AVISO].",\n    "_doc_laboratorio": "VALORES DE LABORATORIO (ADR-060 E3): hospital-lab / lab-vagrant. El manifiesto del lab lo firma argus-infra en la VM etcd (pasos 8e.3 y 8e.5). Nunca copiar estos valores a produccion.",\n    "hospital_id": "hospital-lab",\n    "despliegue_id": "lab-vagrant",\n    "set_name": "ml_defender_protegidos",\n    "manifiesto_cache": "/var/lib/ml-defender/firewall/protegidos.manifiesto",\n    "aviso_sec": 300,\n    "consulta_sec": 30\n  },\n'),
    ],
    'firewall-acl-agent/include/firewall/config_loader.hpp': [
        ('        int aviso_sec = 300;        // [30, 86400]: avisos periódicos y nueva verificación de la caché (D7)\n        std::vector<std::string> etcd_endpoints;  // copia de etcd.endpoints para D-C (solo lectura)\n',
         '        int aviso_sec = 300;        // [30, 86400]: avisos periódicos y nueva verificación de la caché (D7)\n        int consulta_sec = 30;      // [5, 3600]: cada cuánto se pide el manifiesto al etcd-server (8e.3c, F-E)\n        std::vector<std::string> etcd_endpoints;  // copia de etcd.endpoints para D-C (solo lectura)\n'),
    ],
    'firewall-acl-agent/include/firewall/etcd_client.hpp': [
        ('        std::optional<std::vector<uint8_t>> get_hmac_key(const std::string& key_path);\n    private:\n',
         '        std::optional<std::vector<uint8_t>> get_hmac_key(const std::string& key_path);\n\n        /// [PROTEGIDOS-MANIFIESTO-D318] GET /v1/protegidos: status HTTP (0 = nadie respondió, -1 = sin cliente) y cuerpo\n        int get_protegidos(std::string& cuerpo);\n    private:\n'),
    ],
    'firewall-acl-agent/src/core/config_loader.cpp': [
        ('                std::cerr << "[CONFIG-DEFAULT] protegidos.aviso_sec " << (hay ? "mal formado" : "ausente")\n                          << " (entero en [" << kMin << ", " << kMax << "]): se usa " << def << std::endl;\n',
         '                std::cerr << "[CONFIG-DEFAULT] protegidos.aviso_sec " << (hay ? "mal formado" : "ausente")\n                          << " (entero en [" << kMin << ", " << kMax << "]): se usa " << def << std::endl;\n            }\n        }\n        {   // [PROTEGIDOS-MANIFIESTO-D318] 8e.3c (F-E)\n            constexpr int kMin = 5, kMax = 3600;\n            const int def = pc.consulta_sec;\n            const bool hay = p.isObject() && p.isMember("consulta_sec");\n            if (hay && p["consulta_sec"].isInt() && p["consulta_sec"].asInt() >= kMin && p["consulta_sec"].asInt() <= kMax) {\n                pc.consulta_sec = p["consulta_sec"].asInt();\n                std::cout << "[CONFIG] protegidos.consulta_sec=" << pc.consulta_sec << " (JSON)" << std::endl;\n            } else {\n                std::cerr << "[CONFIG-DEFAULT] protegidos.consulta_sec " << (hay ? "mal formado" : "ausente")\n                          << " (entero en [" << kMin << ", " << kMax << "]): se usa " << def << std::endl;\n'),
    ],
    'firewall-acl-agent/src/core/etcd_client.cpp': [
        ('\n} // namespace mldefender::firewall',
         '\n// [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3c\nint EtcdClient::get_protegidos(std::string& cuerpo) {\n    if (!pImpl->client_) {\n        cuerpo = "sin cliente etcd";\n        return -1;\n    }\n    return pImpl->client_->get_protegidos(cuerpo);\n}\n\n} // namespace mldefender::firewall'),
    ],
    'firewall-acl-agent/src/main.cpp': [
        ('#include <fstream>\n#include <nlohmann/json.hpp>\n',
         '#include <fstream>\n#include <filesystem>  // [PROTEGIDOS-MANIFIESTO-D318] directorio de la caché\n#include <nlohmann/json.hpp>\n'),
        ('\n// Arranque: el último manifiesto verificado está en la caché (ADR-060 D5.5).\nstatic void protegidos_cargar_cache(ProtegidosVigentes& v, IPSetWrapper& ipset, const FirewallAgentConfig& config,\n                                    bool set_ok) {\n    const auto& pc = config.protegidos;\n    if (pc.hospital_id.empty() || pc.despliegue_id.empty()) {\n        std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] protegidos.hospital_id/despliegue_id sin valor: no hay manifiesto que "\n                     "verificar (candado cerrado)" << std::endl;\n        return;\n    }\n    std::string sobre, err;\n    if (!::argus::protegidos::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {\n        std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] caché " << pc.manifiesto_cache << ": " << err\n                  << " (hospital=" << pc.hospital_id << " planta=" << pc.despliegue_id << "; candado cerrado)" << std::endl;\n        return;\n    }\n    const auto p = v.proponer(sobre);\n    if (!p.resultado.ok) {\n        std::cerr << "[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=" << ::argus::protegidos::nombre_motivo(p.resultado.motivo)\n                  << " " << p.resultado.detalle << " (caché " << pc.manifiesto_cache << "; candado cerrado)" << std::endl;\n        return;\n    }\n    std::cout << ::argus::protegidos::resumen_manifiesto(*p.resultado.manifiesto) << " (caché " << pc.manifiesto_cache\n              << ")" << std::endl;\n    if (set_ok) protegidos_aplicar_kernel(ipset, pc.set_name, *p.resultado.manifiesto);\n    protegidos_infra(*p.resultado.manifiesto, config);\n}\n',
         '\n// [PROTEGIDOS-MANIFIESTO-D318] 8e.3c: un manifiesto ya verificado y vigente: kernel, caché + versión (si viene del\n// etcd-server), [INFRA-CAMBIO] con altas y bajas, y el plano de control (D-C).\nstatic void protegidos_aplicado(const ProtegidosVigentes::Propuesta& p, IPSetWrapper& ipset,\n                                const FirewallAgentConfig& config, bool set_ok, const char* origen, bool guardar) {\n    const auto& pc = config.protegidos;\n    const auto& m = *p.resultado.manifiesto;\n    std::cout << ::argus::protegidos::resumen_manifiesto(m) << " (" << origen << ")" << std::endl;\n    if (p.anterior) {\n        std::cout << "[INFRA-CAMBIO] version " << p.anterior->version << " -> " << m.version << " firmante="\n                  << ::argus::protegidos::detalle_protegidos::saneado(m.firmante) << " emitido=" << m.emitido_utc\n                  << " motivo=" << ::argus::protegidos::detalle_protegidos::saneado(m.motivo) << " "\n                  << ::argus::protegidos::diferencias_protegidos(p.anterior.get(), m) << " (" << origen << ")" << std::endl;\n    }\n    if (set_ok) protegidos_aplicar_kernel(ipset, pc.set_name, m);\n    if (guardar) {\n        std::string err;\n        std::error_code ec;\n        std::filesystem::create_directories(std::filesystem::path(pc.manifiesto_cache).parent_path(), ec);\n        if (!::argus::protegidos::escribir_cache_protegidos(pc.manifiesto_cache, m.sobre, err)) {\n            std::cerr << "[PROTEGIDOS-CACHE] no se pudo guardar " << pc.manifiesto_cache << ": " << err\n                      << " (la version " << m.version << " sigue vigente en memoria)" << std::endl;\n        }\n    }\n    std::string err;\n    if (!::argus::protegidos::escribir_version_protegidos(pc.manifiesto_cache + ".version", m.version, err)) {\n        std::cerr << "[PROTEGIDOS-VERSION] no se pudo guardar " << pc.manifiesto_cache << ".version: " << err\n                  << " (anti-rollback entre reinicios sin la version " << m.version << ")" << std::endl;\n    }\n    protegidos_infra(m, config);\n}\n\n// [PROTEGIDOS-MANIFIESTO-D318] 8e.3c (F-E): pide el manifiesto al etcd-server. true si respondió (200 o 404).\n// El mismo sobre que el vigente: nada (cada consulta_sec). Otro: se verifica; con versión menor, rechazo y alarma.\nstatic bool protegidos_consultar(ProtegidosVigentes& v, mldefender::firewall::EtcdClient* etcd, IPSetWrapper& ipset,\n                                 const FirewallAgentConfig& config, bool set_ok, std::string& fallo) {\n    if (etcd == nullptr) {\n        fallo = "sin cliente etcd";\n        return false;\n    }\n    std::string cuerpo;\n    const int st = etcd->get_protegidos(cuerpo);\n    if (st == 404) {\n        fallo = "el etcd-server no tiene manifiesto publicado (404)";\n        return true;\n    }\n    if (st != 200) {\n        fallo = "status " + std::to_string(st) + ": " + ::argus::protegidos::detalle_protegidos::saneado(cuerpo.substr(0, 200));\n        return false;\n    }\n    fallo.clear();\n    const auto vig = v.vigente();\n    if (vig && vig->sobre == cuerpo) return true;\n    const auto p = v.proponer(cuerpo);\n    if (!p.resultado.ok) {\n        std::cerr << "[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=" << ::argus::protegidos::nombre_motivo(p.resultado.motivo)\n                  << " " << p.resultado.detalle << " (etcd-server; se conserva "\n                  << (vig ? "la version " + std::to_string(vig->version) : std::string("el estado sin manifiesto"))\n                  << ")" << std::endl;\n        return true;\n    }\n    protegidos_aplicado(p, ipset, config, set_ok, "etcd-server", true);\n    return true;\n}\n\n// Arranque (ADR-060 D5.5 y F-F): suelo = la versión más alta aplicada antes de reiniciar; primero el etcd-server y, si\n// no responde o no hay nada nuevo, la caché (que no puede ser más vieja que el suelo).\nstatic void protegidos_cargar_cache(ProtegidosVigentes& v, IPSetWrapper& ipset, const FirewallAgentConfig& config,\n                                    bool set_ok, mldefender::firewall::EtcdClient* etcd) {\n    const auto& pc = config.protegidos;\n    if (pc.hospital_id.empty() || pc.despliegue_id.empty()) {\n        std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] protegidos.hospital_id/despliegue_id sin valor: no hay manifiesto que "\n                     "verificar (candado cerrado)" << std::endl;\n        return;\n    }\n    uint64_t suelo = 0;\n    std::string err;\n    if (!::argus::protegidos::leer_version_protegidos(pc.manifiesto_cache + ".version", suelo, err)) {\n        std::cerr << "[PROTEGIDOS-VERSION] " << pc.manifiesto_cache << ".version: " << err\n                  << " (sin suelo: revise el fichero; el etcd-server y la firma siguen mandando)" << std::endl;\n        suelo = 0;\n    }\n    v.fijar_suelo(suelo);\n    std::cout << "[PROTEGIDOS-VERSION] suelo=" << suelo << " (" << pc.manifiesto_cache << ".version)" << std::endl;\n    std::string fallo;\n    if (!protegidos_consultar(v, etcd, ipset, config, set_ok, fallo)) {\n        std::cerr << "[PROTEGIDOS-CONSULTA] al arrancar: " << fallo << "; se usa la caché" << std::endl;\n    }\n    std::string sobre;\n    if (!::argus::protegidos::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {\n        if (!v.vigente()) {\n            std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] caché " << pc.manifiesto_cache << ": " << err << " (hospital="\n                      << pc.hospital_id << " planta=" << pc.despliegue_id << "; candado cerrado)" << std::endl;\n        }\n        return;\n    }\n    const auto vig = v.vigente();\n    if (vig && vig->sobre == sobre) return;   // el etcd-server dio el mismo que la caché\n    const auto p = v.proponer(sobre);\n    if (!p.resultado.ok) {\n        if (!vig) {\n            std::cerr << "[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=" << ::argus::protegidos::nombre_motivo(p.resultado.motivo)\n                      << " " << p.resultado.detalle << " (caché " << pc.manifiesto_cache << ", suelo=" << suelo\n                      << "; candado cerrado)" << std::endl;\n        }\n        return;\n    }\n    protegidos_aplicado(p, ipset, config, set_ok, "caché", false);\n}\n'),
        ('        const bool protegidos_set_ok = protegidos_preparar_set(ipset, config);\n        protegidos_cargar_cache(*protegidos, ipset, config, protegidos_set_ok);\n        const auto& blacklist_ipset = config.ipsets.at("blacklist");\n',
         '        const bool protegidos_set_ok = protegidos_preparar_set(ipset, config);\n        protegidos_cargar_cache(*protegidos, ipset, config, protegidos_set_ok, etcd_client.get());\n        const auto& blacklist_ipset = config.ipsets.at("blacklist");\n'),
        ('        auto last_protegidos = std::chrono::steady_clock::now();  // [PROTEGIDOS-MANIFIESTO-D318] D6/D7/D-C\n        auto last_metrics_export = std::chrono::steady_clock::now();\n',
         '        auto last_protegidos = std::chrono::steady_clock::now();  // [PROTEGIDOS-MANIFIESTO-D318] D6/D7/D-C\n        auto last_consulta = std::chrono::steady_clock::now();    // [PROTEGIDOS-MANIFIESTO-D318] 8e.3c (F-E)\n        auto last_aviso_consulta = std::chrono::steady_clock::time_point{};\n        uint64_t consultas_fallidas = 0;\n        auto last_metrics_export = std::chrono::steady_clock::now();\n'),
        ('                    last_protegidos = now;\n                }\n',
         '                    last_protegidos = now;\n                }\n                if (!config.protegidos.hospital_id.empty() && !config.protegidos.despliegue_id.empty() &&\n                    std::chrono::duration_cast<std::chrono::seconds>(now - last_consulta).count() >=\n                        config.protegidos.consulta_sec) {\n                    std::string fallo;  // [PROTEGIDOS-MANIFIESTO-D318] 8e.3c: un aviso cada aviso_sec, no uno por consulta\n                    const bool respondio =\n                        protegidos_consultar(*protegidos, etcd_client.get(), ipset, config, protegidos_set_ok, fallo);\n                    if (!fallo.empty()) {\n                        if (!respondio) ++consultas_fallidas;\n                        if (std::chrono::duration_cast<std::chrono::seconds>(now - last_aviso_consulta).count() >=\n                            config.protegidos.aviso_sec) {\n                            std::cerr << "[PROTEGIDOS-CONSULTA] " << fallo << " (fallidas=" << consultas_fallidas\n                                      << "; se conserva lo vigente)" << std::endl;\n                            last_aviso_consulta = now;\n                        }\n                    }\n                    last_consulta = now;\n                }\n'),
    ],
    'libs/protegidos/include/protegidos/manifiesto.hpp': [
        ('    uint64_t rechazos() const;\n    const std::string& hospital_id() const { return hospital_id_; }\n',
         '    uint64_t rechazos() const;\n    // [PROTEGIDOS-MANIFIESTO-D318] 8e.3c anti-rollback entre reinicios (ADR-060 F-F): sin vigente, el primer manifiesto\n    // tiene que tener versión >= suelo (la más alta aplicada antes de reiniciar). Con vigente manda la vigente.\n    void fijar_suelo(uint64_t suelo);\n    uint64_t suelo() const;\n    const std::string& hospital_id() const { return hospital_id_; }\n'),
        ('    uint64_t rechazos_ = 0;\n};\n',
         '    uint64_t rechazos_ = 0;\n    uint64_t suelo_ = 0;\n};\n'),
        ('// infraestructura del manifiesto. Una entrada de endpoints mal formada se devuelve tal cual (también falta).\nstd::vector<std::string> infra_sin_cubrir(const ManifiestoVerificado& m, const std::vector<std::string>& endpoints);\n',
         '// infraestructura del manifiesto. Una entrada de endpoints mal formada se devuelve tal cual (también falta).\n// [PROTEGIDOS-MANIFIESTO-D318] 8e.3c (F-F): la versión más alta aplicada, en un fichero aparte (decimal; mismas reglas\n// que la caché: O_NOFOLLOW, temporal y rename). Ausente: 0 y true (primer arranque). Mal formado: false + error.\nbool leer_version_protegidos(const std::string& ruta, uint64_t& version, std::string& error);\nbool escribir_version_protegidos(const std::string& ruta, uint64_t version, std::string& error);\n// [PROTEGIDOS-MANIFIESTO-D318] 8e.3c [INFRA-CAMBIO]: altas y bajas entre dos manifiestos de la misma planta\n// ("categoria cidr interfaz"), en una línea. anterior null = todo altas.\nstd::string diferencias_protegidos(const ManifiestoVerificado* anterior, const ManifiestoVerificado& nuevo);\n\nstd::vector<std::string> infra_sin_cubrir(const ManifiestoVerificado& m, const std::vector<std::string>& endpoints);\n'),
    ],
    'libs/protegidos/src/manifiesto.cpp': [
        ('    p.anterior = vigente_;\n    p.resultado = verificar_manifiesto(sobre, claves_, hospital_id_, planta_, vigente_ ? vigente_->version : 0);\n    if (p.resultado.ok) {\n',
         '    p.anterior = vigente_;\n    const uint64_t aplicada = vigente_ ? vigente_->version : (suelo_ > 0 ? suelo_ - 1 : 0);\n    p.resultado = verificar_manifiesto(sobre, claves_, hospital_id_, planta_, aplicada);\n    if (p.resultado.ok) {\n'),
        ('    return p;\n}\n',
         '    return p;\n}\n\nvoid ProtegidosVigentes::fijar_suelo(uint64_t suelo) {\n    std::lock_guard<std::mutex> l(m_);\n    suelo_ = suelo;\n}\n\nuint64_t ProtegidosVigentes::suelo() const {\n    std::lock_guard<std::mutex> l(m_);\n    return suelo_;\n}\n\nbool leer_version_protegidos(const std::string& ruta, uint64_t& version, std::string& error) {\n    version = 0;\n    std::string t;\n    if (!leer_cache_protegidos(ruta, t, error)) {\n        if (error.find("No such file") != std::string::npos) {\n            error.clear();\n            return true;\n        }\n        return false;\n    }\n    while (!t.empty() && (t.back() == \'\\n\' || t.back() == \'\\r\')) t.pop_back();\n    if (t.empty() || t.size() > 20 || !std::all_of(t.begin(), t.end(), [](char c) { return c >= \'0\' && c <= \'9\'; })) {\n        error = "contenido mal formado (se espera un entero decimal)";\n        return false;\n    }\n    version = std::strtoull(t.c_str(), nullptr, 10);\n    return true;\n}\n\nbool escribir_version_protegidos(const std::string& ruta, uint64_t version, std::string& error) {\n    return escribir_cache_protegidos(ruta, std::to_string(version) + "\\n", error);\n}\n\nstd::string diferencias_protegidos(const ManifiestoVerificado* anterior, const ManifiestoVerificado& nuevo) {\n    auto clave = [](const EntradaProtegida& e) {\n        return std::string(nombre_categoria(e.rango.cat)) + " " + e.rango.texto + " " + e.interfaz;\n    };\n    std::set<std::string> a, n;\n    if (anterior) for (const auto& e : anterior->entradas) a.insert(clave(e));\n    for (const auto& e : nuevo.entradas) n.insert(clave(e));\n    std::ostringstream o;\n    std::size_t na = 0, nb = 0;\n    o << "altas=[";\n    for (const auto& x : n) if (!a.count(x)) o << (na++ ? ", " : "") << x;\n    o << "] bajas=[";\n    for (const auto& x : a) if (!n.count(x)) o << (nb++ ? ", " : "") << x;\n    o << "]";\n    return o.str();\n}\n'),
    ],
    'libs/protegidos/tests/test_protegidos_manifiesto.cpp': [
        ('    }\n    // 11. Caché: escribir y leer; ausente; enlace simbólico; tamaño\n',
         '    }\n    // 10d. [8e.3c] suelo (anti-rollback entre reinicios), fichero de versión y altas/bajas\n    {\n        ProtegidosVigentes v(solo_a, "hospital-lab", "lab-vagrant");\n        v.fijar_suelo(3);\n        const std::string c2 = carga(2, kLab), c3 = carga(3, kLab), c4 = carga(4, entrada("intranet", "192.168.100.61/32"));\n        CHECK(rech(v.proponer(sobre(c2, firmar(a, c2))).resultado, M::VERSION));   // caché vieja tras reiniciar\n        CHECK(v.proponer(sobre(c3, firmar(a, c3))).resultado.ok);                    // la misma que se aplicó: vale\n        const auto ant = v.vigente();\n        CHECK(v.proponer(sobre(c4, firmar(a, c4))).resultado.ok);\n        const std::string d = diferencias_protegidos(ant.get(), *v.vigente());\n        CHECK(d == "altas=[] bajas=[infraestructura 192.168.100.20/32 eth2]");\n        CHECK(diferencias_protegidos(nullptr, *ant).find("altas=[infraestructura 192.168.100.20/32 eth2, intranet 192.168.100.61/32 eth2]") == 0);\n        char plantilla[] = "/tmp/prot_version_XXXXXX";\n        const std::string dir = mkdtemp(plantilla);\n        const std::string f = dir + "/protegidos.version";\n        uint64_t n = 99;\n        std::string e;\n        CHECK(leer_version_protegidos(f, n, e) && n == 0);              // ausente: primer arranque\n        CHECK(escribir_version_protegidos(f, 17, e) && leer_version_protegidos(f, n, e) && n == 17);\n        CHECK(escribir_cache_protegidos(f, "17x", e) && !leer_version_protegidos(f, n, e));\n        std::remove(f.c_str());\n        rmdir(dir.c_str());\n    }\n    // 11. Caché: escribir y leer; ausente; enlace simbólico; tamaño\n'),
    ],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    nombre = os.path.basename(sys.argv[0])
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print(f"uso: {nombre} --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    errores, hechos, pendientes = [], [], []
    crear, borrar = {}, []
    for rel, esperado, contenido in NUEVOS:
        b = contenido.encode("utf-8")
        if sha(b) != esperado:
            errores.append(f"{rel}: el contenido embebido no da su sha256 (parcheador dañado)")
            continue
        p = os.path.join(raiz, rel)
        if os.path.exists(p):
            a = sha(open(p, "rb").read())
            if a == esperado:
                hechos.append(f"{rel}: creado")
            else:
                errores.append(f"{rel}: ya existe con otro contenido (sha256 {a})")
        else:
            pendientes.append(f"{rel}: crear")
            crear[rel] = b
    for rel, esperado in BORRADOS:
        p = os.path.join(raiz, rel)
        if not os.path.exists(p):
            hechos.append(f"{rel}: borrado")
            continue
        a = sha(open(p, "rb").read())
        print(f"sha256 previo  {rel}: {a}")
        if a == esperado:
            pendientes.append(f"{rel}: borrar")
            borrar.append(rel)
        else:
            errores.append(f"{rel}: sha256 {a}, no el esperado para borrarlo")
    orig, nuevo = {}, {}
    for rel, cambios in CAMBIOS.items():
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        orig[rel] = open(p, "rb").read()
        print(f"sha256 previo  {rel}: {sha(orig[rel])}")
        t = orig[rel].decode("utf-8")
        for n, (viejo, nv) in enumerate(cambios, 1):
            cv, cn = t.count(viejo), (t.count(nv) if nv else 0)
            if nv and viejo in nv:
                aplicar, hecho = cv == 1 and cn == 0, cn == 1
            elif nv in viejo:
                aplicar, hecho = cv == 1, cv == 0 and (not nv or cn >= 1)
            else:
                aplicar, hecho = cv == 1 and cn == 0, cv == 0 and cn == 1
            if aplicar:
                t = t.replace(viejo, nv)
                pendientes.append(f"{rel}: cambio {n}")
            elif hecho:
                hechos.append(f"{rel}: cambio {n}")
            else:
                errores.append(f"{rel}: cambio {n}: texto viejo {cv} veces, nuevo {cn} veces")
        nuevo[rel] = t.encode("utf-8")
    print(f"ya aplicados ({len(hechos)})")
    for h in hechos:
        print(f"  = {h}")
    print(f"por aplicar  ({len(pendientes)})")
    for h in pendientes:
        print(f"  + {h}")
    if errores:
        for e in errores:
            print(f"FALLA: {e}")
        print("RESULTADO: FALLA (no se ha escrito nada)")
        return 1
    if modo == "--apply":
        for rel, b in crear.items():
            p = os.path.join(raiz, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p + ".d318tmp", "wb") as f:
                f.write(b)
            os.chmod(p + ".d318tmp", 0o644)
            os.replace(p + ".d318tmp", p)
        for rel in CAMBIOS:
            if nuevo[rel] != orig[rel]:
                p = os.path.join(raiz, rel)
                m = os.stat(p).st_mode
                with open(p + ".d318tmp", "wb") as f:
                    f.write(nuevo[rel])
                os.chmod(p + ".d318tmp", m)
                os.replace(p + ".d318tmp", p)
        for rel in borrar:
            os.remove(os.path.join(raiz, rel))
    for rel, esperado, _ in NUEVOS:
        print(f"sha256 nuevo   {rel}: {esperado}")
    for rel in CAMBIOS:
        estado = "igual" if nuevo[rel] == orig[rel] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {rel}: {sha(nuevo[rel])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
