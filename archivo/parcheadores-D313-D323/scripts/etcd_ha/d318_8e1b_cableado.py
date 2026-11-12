#!/usr/bin/env python3
# d318_8e1b_cableado.py — DAY318, ADR-060 paso 8e.1b [PROTEGIDOS-MANIFIESTO-D318] (firewall-acl-agent): cableado del
# manifiesto firmado de protegidos. Los rangos protegidos salen SOLO del manifiesto verificado (fuera ddos_protegidos de
# firewall.json y el defecto RFC 1918); set hash:net,iface con sustitución atómica (temporal + swap) y regla
# --match-set <set> src,src -j RETURN (D-A); candado (D6): con la mitigación habilitada y sin manifiesto verificado no
# actúa; la barrera protege por IP siempre (D-G); vigilancia periódica (D6/D7/D-C). Con sus tests.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_8e1b_cableado.py --check|--apply <raíz>
# Todo o nada e idempotente: un fichero reescrito se da por hecho si ya tiene el sha256 nuevo, se escribe si tiene el
# viejo y si tiene otro, para; cada cambio se aplica si su texto viejo aparece una vez y se da por hecho si ya está el
# nuevo. Imprime el sha256 de cada fichero antes y después.
import hashlib
import os
import sys

FW = "firewall-acl-agent/"
HPP_PROT = FW + "include/firewall/ddos_protegidos.hpp"
HPP_MAN = FW + "include/firewall/protegidos_manifiesto.hpp"
CPP_MAN = FW + "src/core/protegidos_manifiesto.cpp"
HPP_IPSET = FW + "include/firewall/ipset_wrapper.hpp"
CPP_IPSET = FW + "src/core/ipset_wrapper.cpp"
HPP_IPT = FW + "include/firewall/iptables_wrapper.hpp"
CPP_IPT = FW + "src/core/iptables_wrapper.cpp"
HPP_CFG = FW + "include/firewall/config_loader.hpp"
CPP_CFG = FW + "src/core/config_loader.cpp"
HPP_BP = FW + "include/firewall/batch_processor.hpp"
HPP_ZMQ = FW + "include/firewall/zmq_subscriber.hpp"
CPP_ZMQ = FW + "src/api/zmq_subscriber.cpp"
CPP_MAIN = FW + "src/main.cpp"
JSON = FW + "config/firewall.json"
TEST_EP = FW + "tests/unit/test_batch_processor_episodio.cpp"
TEST_MAN = FW + "tests/unit/test_protegidos_manifiesto.cpp"
HPP_MIT = FW + "include/firewall/ddos_mitigacion.hpp"

CAMBIOS = {
    HPP_PROT: [
        ("cabecera",
         "// ddos_protegidos.hpp\n"
         "// [PROTEGIDOS-D300] DEBT-FW-PROTECTED-RANGES-001: rangos protegidos de la cabeza DDoS.\n"
         "// Un DROP de la cabeza DDoS cuyo ORIGEN cae en un rango protegido (dmz, intranet, externos_criticos) se\n"
         "// registra como ALERTA_PROTEGIDO y nunca se convierte en bloqueo automatico.\n"
         "// Si no queda ningun rango valido (bloque ausente, listas vacias o todas las entradas invalidas) se\n"
         "// protegen por defecto los rangos privados RFC 1918 y fc00::/7 como intranet (decision de Alonso DAY300:\n"
         "// un descuido de configuracion no puede acabar bloqueando la intranet o la DMZ).\n"
         "// Funciones puras, sin JSON ni red: config_loader extrae las listas y las pasa aqui.\n",
         "// ddos_protegidos.hpp\n"
         "// [PROTEGIDOS-D300] rangos protegidos: un DROP de la cabeza DDoS cuyo ORIGEN cae en un rango protegido se registra\n"
         "// como ALERTA_PROTEGIDO y nunca se convierte en bloqueo automatico; ningun camino lo mete en el blacklist.\n"
         "// [PROTEGIDOS-MANIFIESTO-D318] ADR-060: los rangos salen SOLO del manifiesto firmado verificado\n"
         "// (protegidos_manifiesto.hpp). Fuera ddos_protegidos de firewall.json y el defecto RFC 1918 de DAY300: con el\n"
         "// candado (D6), sin manifiesto verificado no hay bloqueo real del que proteger. La barrera protege por IP siempre\n"
         "// (D-G). Funciones puras, sin JSON ni red.\n"),
        ("fuera por_defecto",
         "    std::vector<RangoProtegido> rangos;\n    bool por_defecto = false;\n",
         "    std::vector<RangoProtegido> rangos;\n"),
        ("fuera el defecto RFC 1918 y construir_rangos_protegidos",
         "inline const std::vector<std::string>& rangos_protegidos_por_defecto() {\n"
         "    static const std::vector<std::string> v{\"10.0.0.0/8\", \"172.16.0.0/12\", \"192.168.0.0/16\", \"fc00::/7\"};\n"
         "    return v;\n"
         "}\n"
         "\n"
         "// Construye los rangos desde las tres listas del JSON. Cada entrada valida se registra con [CONFIG];\n"
         "// cada invalida se descarta con [CONFIG-DEFAULT] (el resto sigue protegiendo). Sin ningun rango valido:\n"
         "// defecto RFC 1918 + fc00::/7 como intranet, con [CONFIG-DEFAULT].\n"
         "inline RangosProtegidos construir_rangos_protegidos(const std::vector<std::string>& dmz,\n"
         "                                                    const std::vector<std::string>& intranet,\n"
         "                                                    const std::vector<std::string>& externos_criticos,\n"
         "                                                    std::ostream& log) {\n"
         "    RangosProtegidos out;\n"
         "    struct Lista {\n"
         "        const std::vector<std::string>* entradas;\n"
         "        CategoriaProtegida cat;\n"
         "    };\n"
         "    const Lista listas[] = {{&dmz, CategoriaProtegida::DMZ},\n"
         "                            {&intranet, CategoriaProtegida::INTRANET},\n"
         "                            {&externos_criticos, CategoriaProtegida::EXTERNOS_CRITICOS}};\n"
         "    for (const auto& l : listas) {\n"
         "        for (const auto& e : *l.entradas) {\n"
         "            RangoProtegido r;\n"
         "            if (parsear_rango(e, l.cat, r)) {\n"
         "                log << \"[CONFIG] ddos_protegidos.\" << nombre_categoria(l.cat) << \" += \" << e << \" (JSON)\\n\";\n"
         "                out.rangos.push_back(r);\n"
         "            } else {\n"
         "                log << \"[CONFIG-DEFAULT] ddos_protegidos.\" << nombre_categoria(l.cat) << \": entrada '\"\n"
         "                    << detalle_protegidos::saneado(e)\n"
         "                    << \"' descartada (formato: IPv4 o IPv6 con prefijo opcional /0-32 o /0-128, p. ej. \"\n"
         "                       \"10.20.0.0/16 o fd00::/8)\\n\";\n"
         "            }\n"
         "        }\n"
         "    }\n"
         "    if (out.rangos.empty()) {\n"
         "        out.por_defecto = true;\n"
         "        log << \"[CONFIG-DEFAULT] ddos_protegidos: ningun rango valido en el JSON (bloque ausente, listas vacias o \"\n"
         "               \"entradas invalidas). Se protegen como intranet los rangos privados:\";\n"
         "        for (const auto& e : rangos_protegidos_por_defecto()) {\n"
         "            RangoProtegido r;\n"
         "            if (parsear_rango(e, CategoriaProtegida::INTRANET, r)) {\n"
         "                out.rangos.push_back(r);\n"
         "                log << \" \" << e;\n"
         "            }\n"
         "        }\n"
         "        log << \". Configure dmz, intranet y externos_criticos de ESTE despliegue \"\n"
         "               \"(docs/operaciones/GUIA_OPERACIONES.md, seccion DDOS-PROTEGIDOS)\\n\";\n"
         "    }\n"
         "    return out;\n"
         "}\n"
         "\n",
         ""),
    ],
    HPP_MAN: [
        ("rangos cacheados en lo vigente",
         "    bool verificado() const;   // candado (D6): hay manifiesto verificado\n",
         "    bool verificado() const;   // candado (D6): hay manifiesto verificado\n"
         "    // [PROTEGIDOS-MANIFIESTO-D318] 8e.1b: los rangos del vigente, ya ordenados (vacíos sin manifiesto). La barrera\n"
         "    // los consulta en cada DROP de la cabeza DDoS: se construyen una vez por manifiesto, no por evento.\n"
         "    std::shared_ptr<const RangosProtegidos> rangos() const;\n"),
        ("miembro rangos_",
         "    std::shared_ptr<const ManifiestoVerificado> vigente_;\n    uint64_t rechazos_ = 0;\n",
         "    std::shared_ptr<const ManifiestoVerificado> vigente_;\n"
         "    std::shared_ptr<const RangosProtegidos> rangos_;\n"
         "    uint64_t rechazos_ = 0;\n"),
        ("candado",
         "// Caché en disco del último manifiesto verificado",
         "// [PROTEGIDOS-MANIFIESTO-D318] candado (ADR-060 D6): con la mitigación habilitada, sin manifiesto verificado la\n"
         "// mitigación no actúa (ni simulada en dry_run: lo simulado es lo que haría de verdad). true = cerrado.\n"
         "inline bool candado_cerrado(bool mitigacion_habilitada, const ProtegidosVigentes* v) {\n"
         "    return mitigacion_habilitada && (v == nullptr || !v->verificado());\n"
         "}\n"
         "\n"
         "// Caché en disco del último manifiesto verificado"),
    ],
    CPP_MAN: [
        ("fuera por_defecto",
         "    out.por_defecto = false;\n    return out;\n",
         "    return out;\n"),
        ("constructor con rangos vacíos",
         "    : claves_(claves), hospital_id_(std::move(hospital_id)), planta_(std::move(planta)) {}\n",
         "    : claves_(claves), hospital_id_(std::move(hospital_id)), planta_(std::move(planta)),\n"
         "      rangos_(std::make_shared<const RangosProtegidos>()) {}\n"),
        ("rangos al aplicar",
         "    if (p.resultado.ok) {\n        vigente_ = p.resultado.manifiesto;\n    } else {\n",
         "    if (p.resultado.ok) {\n"
         "        vigente_ = p.resultado.manifiesto;\n"
         "        rangos_ = std::make_shared<const RangosProtegidos>(vigente_->rangos());\n"
         "    } else {\n"),
        ("rangos()",
         "uint64_t ProtegidosVigentes::rechazos() const {\n",
         "std::shared_ptr<const RangosProtegidos> ProtegidosVigentes::rangos() const {\n"
         "    std::lock_guard<std::mutex> l(m_);\n"
         "    return rangos_;\n"
         "}\n"
         "\n"
         "uint64_t ProtegidosVigentes::rechazos() const {\n"),
    ],
    HPP_IPSET: [
        ("tipo hash:net,iface",
         "    HASH_IP_PORT, ///< IP + Port tuples\n",
         "    HASH_IP_PORT, ///< IP + Port tuples\n"
         "    HASH_NET_IFACE, ///< CIDR + interfaz de entrada (192.168.100.20/32,eth2) [PROTEGIDOS-MANIFIESTO-D318]\n"),
        ("set_type y replace_net_iface",
         "    /// Save all sets to file\n",
         "    /// [PROTEGIDOS-MANIFIESTO-D318] tipo de un set existente ('ipset list -t'); nullopt si no existe\n"
         "    std::optional<std::string> set_type(const std::string& set_name) const;\n"
         "\n"
         "    /// [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D-A: sustituye de forma ATÓMICA el contenido de un set hash:net,iface\n"
         "    /// existente: temporal <set>_n con las entradas (cidr, interfaz), ipset swap y borrado del temporal. Nunca deja\n"
         "    /// un instante sin entradas; si algo falla el set queda como estaba. En dry_run solo imprime las órdenes.\n"
         "    IPSetResult<void> replace_net_iface(const std::string& set_name,\n"
         "                                        const std::vector<std::pair<std::string, std::string>>& entradas,\n"
         "                                        uint32_t maxelem);\n"
         "\n"
         "    /// Save all sets to file\n"),
    ],
    CPP_IPSET: [
        ("nombre del tipo",
         "        case IPSetType::HASH_IP_PORT: return \"hash:ip,port\";\n",
         "        case IPSetType::HASH_IP_PORT: return \"hash:ip,port\";\n"
         "        case IPSetType::HASH_NET_IFACE: return \"hash:net,iface\";  // [PROTEGIDOS-MANIFIESTO-D318]\n"),
        ("set_type y replace_net_iface",
         "            IPSetErrorCode::KERNEL_ERROR, \"Failed to swap sets\"\n"
         "        });\n"
         "    }\n"
         "    return IPSetResult<void>();\n"
         "}\n",
         "            IPSetErrorCode::KERNEL_ERROR, \"Failed to swap sets\"\n"
         "        });\n"
         "    }\n"
         "    return IPSetResult<void>();\n"
         "}\n"
         "\n"
         "// [PROTEGIDOS-MANIFIESTO-D318] tipo de un set existente, leído de 'ipset list -t' (línea \"Type: ...\").\n"
         "std::optional<std::string> IPSetWrapper::set_type(const std::string& set_name) const {\n"
         "    std::lock_guard<std::mutex> lock(mutex_);\n"
         "    if (!is_valid_set_name(set_name)) return std::nullopt;\n"
         "    auto [ret, output] = safe_exec_with_output({kIpsetBin, \"list\", \"-t\", set_name});\n"
         "    if (ret != 0) return std::nullopt;\n"
         "    std::istringstream is(output);\n"
         "    std::string l;\n"
         "    while (std::getline(is, l)) {\n"
         "        if (l.rfind(\"Type: \", 0) == 0) return l.substr(6);\n"
         "    }\n"
         "    return std::nullopt;\n"
         "}\n"
         "\n"
         "namespace {\n"
         "// [A-Za-z0-9._-]{1,15} (IFNAMSIZ - 1): lo mismo que exige el manifiesto\n"
         "bool es_interfaz_ipset(const std::string& s) {\n"
         "    if (s.empty() || s.size() > 15) return false;\n"
         "    for (char c : s) {\n"
         "        if (!std::isalnum(static_cast<unsigned char>(c)) && c != '.' && c != '_' && c != '-') return false;\n"
         "    }\n"
         "    return true;\n"
         "}\n"
         "}  // namespace\n"
         "\n"
         "// [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D-A: sustitución atómica (temporal + swap) de un set hash:net,iface.\n"
         "IPSetResult<void> IPSetWrapper::replace_net_iface(const std::string& set_name,\n"
         "                                                  const std::vector<std::pair<std::string, std::string>>& entradas,\n"
         "                                                  uint32_t maxelem) {\n"
         "    std::lock_guard<std::mutex> lock(mutex_);\n"
         "    const std::string tmp = set_name + \"_n\";\n"
         "    if (!is_valid_set_name(set_name) || !is_valid_set_name(tmp)) {\n"
         "        return IPSetResult<void>(IPSetError{IPSetErrorCode::INVALID_SET_NAME,\n"
         "                                            \"Invalid set name (or temporary '\" + tmp + \"'): '\" + set_name + \"'\"});\n"
         "    }\n"
         "    if (maxelem == 0 || entradas.size() > maxelem) {\n"
         "        return IPSetResult<void>(IPSetError{IPSetErrorCode::KERNEL_ERROR,\n"
         "                                            \"Too many entries: \" + std::to_string(entradas.size()) + \" > maxelem \" +\n"
         "                                                std::to_string(maxelem)});\n"
         "    }\n"
         "    std::ostringstream in;\n"
         "    std::vector<std::string> malas;\n"
         "    for (const auto& [cidr, iface] : entradas) {\n"
         "        if (!is_valid_ip_cidr(cidr) || cidr.find(':') != std::string::npos || !es_interfaz_ipset(iface)) {\n"
         "            malas.push_back(cidr + \",\" + iface);\n"
         "            continue;\n"
         "        }\n"
         "        in << \"add \" << tmp << \" \" << cidr << \",\" << iface << \"\\n\";\n"
         "    }\n"
         "    if (!malas.empty()) {\n"
         "        return IPSetResult<void>(IPSetError{IPSetErrorCode::INVALID_IP_FORMAT,\n"
         "                                            \"Invalid cidr,iface entries (IPv4 only)\", malas});\n"
         "    }\n"
         "    const std::vector<std::string> crear = {kIpsetBin, \"create\", tmp, \"hash:net,iface\", \"family\", \"inet\",\n"
         "                                            \"hashsize\", \"1024\", \"maxelem\", std::to_string(maxelem), \"counters\"};\n"
         "    if (m_dry_run) {\n"
         "        std::cout << \"[DRY-RUN] Would execute: \" << kIpsetBin << \" create \" << tmp << \" hash:net,iface family inet\" << std::endl;\n"
         "        std::istringstream o(in.str());\n"
         "        std::string linea;\n"
         "        std::size_t n = 0;\n"
         "        while (std::getline(o, linea)) {\n"
         "            if (n++ < 20) std::cout << \"[DRY-RUN]   \" << linea << std::endl;\n"
         "        }\n"
         "        if (n > 20) std::cout << \"[DRY-RUN]   ... (+\" << (n - 20) << \" ordenes)\" << std::endl;\n"
         "        std::cout << \"[DRY-RUN] Would execute: \" << kIpsetBin << \" swap \" << tmp << \" \" << set_name\n"
         "                  << \" && \" << kIpsetBin << \" destroy \" << tmp << std::endl;\n"
         "        return IPSetResult<void>();\n"
         "    }\n"
         "    if (!set_exists_unlocked(set_name)) {\n"
         "        return IPSetResult<void>(IPSetError{IPSetErrorCode::SET_NOT_FOUND, \"Set '\" + set_name + \"' does not exist\"});\n"
         "    }\n"
         "    if (set_exists_unlocked(tmp)) safe_exec({kIpsetBin, \"destroy\", tmp});\n"
         "    if (safe_exec(crear) != 0) {\n"
         "        return IPSetResult<void>(IPSetError{IPSetErrorCode::KERNEL_ERROR, \"Failed to create temporary set \" + tmp});\n"
         "    }\n"
         "    auto falla = [&](const std::string& que) {\n"
         "        safe_exec({kIpsetBin, \"destroy\", tmp});\n"
         "        return IPSetResult<void>(IPSetError{IPSetErrorCode::KERNEL_ERROR, que + \" (set '\" + set_name + \"' unchanged)\"});\n"
         "    };\n"
         "    if (!entradas.empty()) {\n"
         "        const char* fichero = \"/run/argus/irp/ipset_protegidos.tmp\";  // como add_batch (DEBT-IRP-IPSET-TMP-001)\n"
         "        std::ofstream f(fichero);\n"
         "        if (!f) return falla(\"Failed to create temporary restore file\");\n"
         "        f << in.str();\n"
         "        f.close();\n"
         "        const int r = safe_exec_with_file_in({kIpsetBin, \"restore\"}, fichero);\n"
         "        std::remove(fichero);\n"
         "        if (r != 0) return falla(\"ipset restore exit=\" + std::to_string(r));\n"
         "    }\n"
         "    if (safe_exec({kIpsetBin, \"swap\", tmp, set_name}) != 0) return falla(\"ipset swap failed (types differ?)\");\n"
         "    safe_exec({kIpsetBin, \"destroy\", tmp});\n"
         "    return IPSetResult<void>();\n"
         "}\n"),
    ],
    HPP_IPT: [
        ("protegidos_ipset",
         "    std::string whitelist_ipset{\"ml_defender_whitelist\"};\n",
         "    // [PROTEGIDOS-MANIFIESTO-D318] set hash:net,iface de protegidos (ADR-060); vacío = sin regla de exención\n"
         "    std::string protegidos_ipset{};\n"),
    ],
    CPP_IPT: [
        ("comentario de la cadena",
         "//   <cadena> -m set --match-set <whitelist> src -j RETURN   (\"protegido\" = aRGus nunca lo bloquea: vuelve a INPUT y\n",
         "//   <cadena> -m set --match-set <protegidos> src,src -j RETURN  ([PROTEGIDOS-MANIFIESTO-D318] origen E interfaz de\n"
         "//                                                            entrada del manifiesto; \"protegido\" = aRGus nunca lo\n"
         "//                                                            bloquea: vuelve a INPUT y\n"),
        ("regla src,src",
         "    if (!config.whitelist_ipset.empty()) {\n"
         "        if (!run({\"-t\", \"filter\", \"-A\", ch, \"-m\", \"set\", \"--match-set\", config.whitelist_ipset, \"src\",\n"
         "                  \"-m\", \"comment\", \"--comment\", \"argus-protegidos\", \"-j\", \"RETURN\"})) return fallo(\"whitelist RETURN\");\n"
         "    }\n",
         "    if (!config.protegidos_ipset.empty()) {\n"
         "        if (!run({\"-t\", \"filter\", \"-A\", ch, \"-m\", \"set\", \"--match-set\", config.protegidos_ipset, \"src,src\",\n"
         "                  \"-m\", \"comment\", \"--comment\", \"argus-protegidos\", \"-j\", \"RETURN\"})) return fallo(\"protegidos RETURN\");\n"
         "    }\n"),
        ("reglas heredadas",
         "                const bool wl = !config.whitelist_ipset.empty() &&\n"
         "                                l.find(\"--match-set \" + config.whitelist_ipset + \" \") != std::string::npos;\n",
         "                const bool wl = !config.protegidos_ipset.empty() &&\n"
         "                                l.find(\"--match-set \" + config.protegidos_ipset + \" \") != std::string::npos;\n"),
        ("log de la cadena",
         "              << \"); dentro: \" << (config.whitelist_ipset.empty() ? \"sin whitelist\" : config.whitelist_ipset + \" RETURN\")\n",
         "              << \"); dentro: \" << (config.protegidos_ipset.empty() ? \"sin protegidos\" : config.protegidos_ipset + \" src,src RETURN\")\n"),
    ],
    HPP_CFG: [
        ("ProtegidosConfig",
         "//===----------------------------------------------------------------------===//\n"
         "// MAIN CONFIGURATION STRUCTURE\n",
         "    // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 sección 6: el manifiesto firmado de protegidos de ESTE firewall.\n"
         "    struct ProtegidosConfig {\n"
         "        std::string hospital_id;    // [a-z0-9-]{1,64}; sin defecto: vacío = sin manifiesto (candado cerrado) y aviso\n"
         "        std::string despliegue_id;  // la planta; igual que hospital_id\n"
         "        std::string set_name = \"ml_defender_protegidos\";  // set hash:net,iface; 1 a 29 (el temporal añade _n)\n"
         "        std::string manifiesto_cache = \"/var/lib/ml-defender/firewall/protegidos.manifiesto\";\n"
         "        int aviso_sec = 300;        // [30, 86400]: avisos periódicos y nueva verificación de la caché (D7)\n"
         "        std::vector<std::string> etcd_endpoints;  // copia de etcd.endpoints para D-C (solo lectura)\n"
         "    };\n"
         "\n"
         "//===----------------------------------------------------------------------===//\n"
         "// MAIN CONFIGURATION STRUCTURE\n"),
        ("protegidos en la configuración",
         "    ::mldefender::firewall::RangosProtegidos ddos_protegidos;  // [PROTEGIDOS-D300] rangos protegidos de la cabeza DDoS\n",
         "    ProtegidosConfig protegidos;  // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 (sustituye a ddos_protegidos)\n"),
        ("ipsets sin whitelist",
         "    std::map<std::string, IPSetConfigNew> ipsets;  // Multiple ipsets (blacklist, whitelist)\n",
         "    std::map<std::string, IPSetConfigNew> ipsets;  // blacklist (el de protegidos lo crea el agente: ADR-060)\n"),
    ],
    CPP_CFG: [
        ("bloque protegidos",
         "    {   // [PROTEGIDOS-D300] DEBT-FW-PROTECTED-RANGES-001: rangos protegidos de la cabeza DDoS\n"
         "        const Json::Value p = root.isMember(\"ddos_protegidos\") ? root[\"ddos_protegidos\"] : Json::Value(Json::nullValue);\n"
         "        std::vector<std::string> dmz, intranet, externos;\n"
         "        if (!p.isObject()) {\n"
         "            std::cerr << \"[CONFIG-DEFAULT] ddos_protegidos ausente o no es un objeto (formato: {\\\"dmz\\\": [CIDR, ...], \"\n"
         "                         \"\\\"intranet\\\": [...], \\\"externos_criticos\\\": [...]})\" << std::endl;\n"
         "        } else {\n"
         "            auto lista = [&p](const char* nombre, std::vector<std::string>& out) {\n"
         "                if (!p.isMember(nombre)) {\n"
         "                    std::cerr << \"[CONFIG-DEFAULT] ddos_protegidos.\" << nombre << \" ausente: lista vacia\" << std::endl;\n"
         "                    return;\n"
         "                }\n"
         "                if (!p[nombre].isArray()) {\n"
         "                    std::cerr << \"[CONFIG-DEFAULT] ddos_protegidos.\" << nombre\n"
         "                              << \" no es una lista de cadenas CIDR: se ignora\" << std::endl;\n"
         "                    return;\n"
         "                }\n"
         "                for (const auto& it : p[nombre]) {\n"
         "                    if (it.isString()) {\n"
         "                        out.push_back(it.asString());\n"
         "                    } else {\n"
         "                        std::cerr << \"[CONFIG-DEFAULT] ddos_protegidos.\" << nombre\n"
         "                                  << \": entrada que no es una cadena, descartada\" << std::endl;\n"
         "                    }\n"
         "                }\n"
         "            };\n"
         "            lista(\"dmz\", dmz);\n"
         "            lista(\"intranet\", intranet);\n"
         "            lista(\"externos_criticos\", externos);\n"
         "        }\n"
         "        std::ostringstream plog;\n"
         "        config.ddos_protegidos = ::mldefender::firewall::construir_rangos_protegidos(dmz, intranet, externos, plog);\n"
         "        std::cout << plog.str() << std::flush;\n"
         "    }\n",
         "    {   // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 sección 6. Los rangos NO están aquí: salen del manifiesto firmado.\n"
         "        // Ningún campo se lee en silencio: cada uno se registra con su valor y su origen.\n"
         "        auto& pc = config.protegidos;\n"
         "        const Json::Value p = root.isMember(\"protegidos\") ? root[\"protegidos\"] : Json::Value(Json::nullValue);\n"
         "        if (root.isMember(\"ddos_protegidos\")) {\n"
         "            std::cerr << \"[CONFIG-AVISO] ddos_protegidos ya no se lee (ADR-060): los rangos protegidos salen SOLO del \"\n"
         "                         \"manifiesto firmado; retire el bloque de este firewall.json\" << std::endl;\n"
         "        }\n"
         "        if (!p.isObject()) {\n"
         "            std::cerr << \"[CONFIG-AVISO] protegidos ausente o no es un objeto: sin hospital_id ni despliegue_id no hay \"\n"
         "                         \"manifiesto verificado (candado cerrado); el resto, defectos\" << std::endl;\n"
         "        }\n"
         "        auto es_id = [](const std::string& s) {\n"
         "            return !s.empty() && s.size() <= 64 && std::all_of(s.begin(), s.end(), [](char c) {\n"
         "                return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-';\n"
         "            });\n"
         "        };\n"
         "        auto id = [&](const char* k, std::string& out) {\n"
         "            if (p.isObject() && p.isMember(k) && p[k].isString() && es_id(p[k].asString())) {\n"
         "                out = p[k].asString();\n"
         "                std::cout << \"[CONFIG] protegidos.\" << k << \"=\" << out << \" (JSON)\" << std::endl;\n"
         "            } else {\n"
         "                out.clear();\n"
         "                std::cerr << \"[CONFIG-AVISO] protegidos.\" << k << \" \" << (p.isObject() && p.isMember(k) ? \"mal formado\" : \"ausente\")\n"
         "                          << \" ([a-z0-9-], de 1 a 64): sin valor sano por defecto; no habrá manifiesto verificado \"\n"
         "                             \"(candado cerrado)\" << std::endl;\n"
         "            }\n"
         "        };\n"
         "        id(\"hospital_id\", pc.hospital_id);\n"
         "        id(\"despliegue_id\", pc.despliegue_id);\n"
         "        {\n"
         "            const std::string def = pc.set_name;\n"
         "            const bool hay = p.isObject() && p.isMember(\"set_name\");\n"
         "            if (hay && p[\"set_name\"].isString() && p[\"set_name\"].asString().size() <= 29 &&\n"
         "                ::mldefender::firewall::is_valid_set_name(p[\"set_name\"].asString())) {\n"
         "                pc.set_name = p[\"set_name\"].asString();\n"
         "                std::cout << \"[CONFIG] protegidos.set_name=\" << pc.set_name << \" (JSON)\" << std::endl;\n"
         "            } else {\n"
         "                std::cerr << \"[CONFIG-DEFAULT] protegidos.set_name \" << (hay ? \"mal formado\" : \"ausente\")\n"
         "                          << \" ([A-Za-z0-9_-], de 1 a 29): se usa \" << def << std::endl;\n"
         "            }\n"
         "        }\n"
         "        {\n"
         "            const std::string def = pc.manifiesto_cache;\n"
         "            const bool hay = p.isObject() && p.isMember(\"manifiesto_cache\");\n"
         "            const std::string v = hay && p[\"manifiesto_cache\"].isString() ? p[\"manifiesto_cache\"].asString() : \"\";\n"
         "            if (!v.empty() && v[0] == '/' && v.size() <= 255 && v.find(\"..\") == std::string::npos &&\n"
         "                std::none_of(v.begin(), v.end(), [](char c) { return static_cast<unsigned char>(c) < 0x20; })) {\n"
         "                pc.manifiesto_cache = v;\n"
         "                std::cout << \"[CONFIG] protegidos.manifiesto_cache=\" << v << \" (JSON)\" << std::endl;\n"
         "            } else {\n"
         "                std::cerr << \"[CONFIG-DEFAULT] protegidos.manifiesto_cache \" << (hay ? \"mal formado\" : \"ausente\")\n"
         "                          << \" (ruta absoluta, sin .., hasta 255): se usa \" << def << std::endl;\n"
         "            }\n"
         "        }\n"
         "        {\n"
         "            constexpr int kMin = 30, kMax = 86400;\n"
         "            const int def = pc.aviso_sec;\n"
         "            const bool hay = p.isObject() && p.isMember(\"aviso_sec\");\n"
         "            if (hay && p[\"aviso_sec\"].isInt() && p[\"aviso_sec\"].asInt() >= kMin && p[\"aviso_sec\"].asInt() <= kMax) {\n"
         "                pc.aviso_sec = p[\"aviso_sec\"].asInt();\n"
         "                std::cout << \"[CONFIG] protegidos.aviso_sec=\" << pc.aviso_sec << \" (JSON)\" << std::endl;\n"
         "            } else {\n"
         "                std::cerr << \"[CONFIG-DEFAULT] protegidos.aviso_sec \" << (hay ? \"mal formado\" : \"ausente\")\n"
         "                          << \" (entero en [\" << kMin << \", \" << kMax << \"]): se usa \" << def << std::endl;\n"
         "            }\n"
         "        }\n"
         "        // D-C: los endpoints del etcd-server (los valida etcd-client; aquí solo se copian para comparar)\n"
         "        if (root.isMember(\"etcd\") && root[\"etcd\"].isObject() && root[\"etcd\"][\"endpoints\"].isArray()) {\n"
         "            for (const auto& e : root[\"etcd\"][\"endpoints\"]) {\n"
         "                if (e.isString()) pc.etcd_endpoints.push_back(e.asString());\n"
         "            }\n"
         "        }\n"
         "    }\n"),
    ],
    HPP_BP: [
        ("fuera whitelist_ipset",
         "    std::string blacklist_ipset{\"ml_defender_blacklist\"};\n    std::string whitelist_ipset{\"ml_defender_whitelist\"};\n",
         "    std::string blacklist_ipset{\"ml_defender_blacklist\"};\n"),
    ],
    HPP_MIT: [
        ("comentario",
         "// Por cada DROP de ddos_v2 cuyo origen NO esta protegido (el suscriptor filtra antes con ddos_protegidos) decide:\n",
         "// Por cada DROP de ddos_v2 cuyo origen NO esta protegido (el suscriptor filtra antes con el manifiesto de protegidos,\n"
         "// ADR-060, y solo llama aqui con el candado abierto: hay manifiesto verificado) decide:\n"),
    ],
    HPP_ZMQ: [
        ("include",
         "#include \"firewall/ddos_protegidos.hpp\"  // [PROTEGIDOS-D300]\n",
         "#include \"firewall/protegidos_manifiesto.hpp\"  // [PROTEGIDOS-MANIFIESTO-D318] ADR-060\n"),
        ("Config.protegidos",
         "        ::mldefender::firewall::RangosProtegidos ddos_protegidos;  ///< [PROTEGIDOS-D300] rangos protegidos\n",
         "        /// [PROTEGIDOS-MANIFIESTO-D318] lo vigente (ADR-060). null = nada protegido y candado cerrado\n"
         "        std::shared_ptr<::mldefender::firewall::ProtegidosVigentes> protegidos;\n"),
        ("contadores",
         "    uint64_t prot_alertas_[4] = {};  // [PROTEGIDOS-D300] ALERTA_PROTEGIDO acumuladas por CategoriaProtegida\n",
         "    uint64_t prot_alertas_[5] = {};  // [PROTEGIDOS-D300] ALERTA_PROTEGIDO acumuladas por CategoriaProtegida (+infra D318)\n"),
        ("contador del candado",
         "    uint64_t mit_invalida_ = 0;\n",
         "    uint64_t mit_invalida_ = 0;\n"
         "    uint64_t mit_candado_ = 0;  // [PROTEGIDOS-MANIFIESTO-D318] DROP no mitigados por el candado (D6) en el periodo\n"),
    ],
    CPP_ZMQ: [
        ("resumen de protegidos",
         "                    const uint64_t* pa = prot_alertas_;\n"
         "                    std::cout << \"[SOMBRA-DDOS] protegidos: alertas=\" << (pa[1] + pa[2] + pa[3]) << \" dmz=\" << pa[1]\n"
         "                              << \" intranet=\" << pa[2] << \" externos_criticos=\" << pa[3]\n"
         "                              << \" por_defecto=\" << (config_.ddos_protegidos.por_defecto ? 1 : 0) << std::endl;\n"
         "                    if (config_.ddos_protegidos.por_defecto) {\n"
         "                        std::cerr << \"[CONFIG-DEFAULT] ddos_protegidos: rigen los rangos privados por defecto (RFC 1918 + \"\n"
         "                                     \"fc00::/7 como intranet); configure los de ESTE despliegue (GUIA_OPERACIONES, \"\n"
         "                                     \"seccion DDOS-PROTEGIDOS)\" << std::endl;\n"
         "                    }\n",
         "                    const uint64_t* pa = prot_alertas_;\n"
         "                    const auto vig = config_.protegidos ? config_.protegidos->vigente() : nullptr;\n"
         "                    std::cout << \"[SOMBRA-DDOS] protegidos: alertas=\" << (pa[1] + pa[2] + pa[3] + pa[4]) << \" dmz=\" << pa[1]\n"
         "                              << \" intranet=\" << pa[2] << \" externos_criticos=\" << pa[3] << \" infraestructura=\" << pa[4]\n"
         "                              << \" manifiesto=\" << (vig ? \"version \" + std::to_string(vig->version) : std::string(\"ninguno\"))\n"
         "                              << std::endl;\n"),
        ("barrera con lo vigente",
         "            const auto cat = config_.ddos_protegidos.categoria_de(nf2.source_ip());\n",
         "            // [PROTEGIDOS-MANIFIESTO-D318] lo vigente del manifiesto; por IP siempre, venga por donde venga (D-G)\n"
         "            const auto rg = config_.protegidos ? config_.protegidos->rangos() : nullptr;\n"
         "            const auto cat = rg ? rg->categoria_de(nf2.source_ip()) : ::mldefender::firewall::CategoriaProtegida::NINGUNA;\n"),
        ("candado",
         "            const Accion accion = ddos_mitigacion_.decidir(dst, proto, src, ddos_shadow_.en_episodio(dst, proto));\n",
         "            if (::mldefender::firewall::candado_cerrado(config_.ddos_mitigacion.habilitada, config_.protegidos.get())) {\n"
         "                ++mit_candado_;  // [PROTEGIDOS-MANIFIESTO-D318] D6: sin manifiesto verificado, la mitigación no actúa\n"
         "                return;\n"
         "            }\n"
         "            const Accion accion = ddos_mitigacion_.decidir(dst, proto, src, ddos_shadow_.en_episodio(dst, proto));\n"),
        ("modo y candado en el resumen de la mitigación",
         "                              << (!config_.ddos_mitigacion.habilitada ? \"deshabilitada\"\n"
         "                                  : (config_.dry_run ? \"dry_run\" : \"ACTIVA\"))\n",
         "                              << (!config_.ddos_mitigacion.habilitada ? \"deshabilitada\"\n"
         "                                  : (::mldefender::firewall::candado_cerrado(true, config_.protegidos.get())\n"
         "                                         ? \"CANDADO\" : (config_.dry_run ? \"dry_run\" : \"ACTIVA\")))\n"
         "                              << \" candado=\" << mit_candado_\n"),
        ("reset del candado",
         "                    mit_invalida_ = 0;\n",
         "                    mit_invalida_ = 0;\n"
         "                    mit_candado_ = 0;\n"),
    ],
    CPP_MAIN: [
        ("include",
         "#include \"firewall/batch_processor.hpp\"\n#include <fstream>\n",
         "#include \"firewall/batch_processor.hpp\"\n"
         "#include \"firewall/protegidos_manifiesto.hpp\"  // [PROTEGIDOS-MANIFIESTO-D318] ADR-060\n"
         "#include <fstream>\n"),
        ("set y caché de protegidos",
         "        {   // [ARGUS-WHITELIST-D301] la whitelist refleja EXACTAMENTE los rangos protegidos (decision de Alonso DAY300)\n"
         "            if (config.ipsets.count(\"whitelist\") > 0) {\n"
         "                const std::string wl = config.ipsets.at(\"whitelist\").set_name;\n"
         "                std::vector<IPSetEntry> entradas;\n"
         "                size_t v6 = 0;\n"
         "                for (const auto& r : config.ddos_protegidos.rangos) {\n"
         "                    if (r.texto.find(':') != std::string::npos) {\n"
         "                        ++v6;\n"
         "                        std::cerr << \"[CONFIG-AVISO] ddos_protegidos \" << r.texto << \": IPv6 no cabe en la whitelist (family \"\n"
         "                                     \"inet; DEBT-FW-IPV6-SETS-001); la barrera del suscriptor si lo protege\" << std::endl;\n"
         "                        continue;\n"
         "                    }\n"
         "                    entradas.push_back(IPSetEntry{r.texto});\n"
         "                }\n"
         "                if (config.operation.dry_run) {\n"
         "                    std::cout << \"[DRY-RUN] ipset flush \" << wl << std::endl;\n"
         "                    for (const auto& en : entradas) {\n"
         "                        std::cout << \"[DRY-RUN] ipset add \" << wl << \" \" << en.ip << std::endl;\n"
         "                    }\n"
         "                    std::cout << \"[ARGUS-WHITELIST] \" << wl << \": se vaciaria y cargaria con \" << entradas.size()\n"
         "                              << \" rangos protegidos IPv4 (IPv6 omitidos=\" << v6 << \") (DRY-RUN: nada aplicado)\" << std::endl;\n"
         "                } else {\n"
         "                    const bool vaciada = static_cast<bool>(ipset.flush_set(wl));\n"
         "                    const bool cargada = entradas.empty() || static_cast<bool>(ipset.add_batch(wl, entradas));\n"
         "                    if (vaciada && cargada) {\n"
         "                        std::cout << \"[ARGUS-WHITELIST] \" << wl << \": vaciada y cargada con \" << entradas.size()\n"
         "                                  << \" rangos protegidos IPv4 (IPv6 omitidos=\" << v6 << \")\" << std::endl;\n"
         "                    } else {\n"
         "                        std::cerr << \"[ARGUS-WHITELIST] ERROR \" << wl << \": flush=\" << (vaciada ? \"ok\" : \"FALLO\")\n"
         "                                  << \" carga=\" << (cargada ? \"ok\" : \"FALLO\") << \"; el agente sigue (la barrera del \"\n"
         "                                     \"suscriptor protege los rangos); revise el set con: sudo ipset list \" << wl << std::endl;\n"
         "                    }\n"
         "                }\n"
         "            } else {\n"
         "                std::cerr << \"[CONFIG-AVISO] ipsets.whitelist ausente: los rangos protegidos no se reflejan en el kernel; \"\n"
         "                             \"solo los protege la barrera del suscriptor\" << std::endl;\n"
         "            }\n"
         "        }\n",
         "        // [PROTEGIDOS-MANIFIESTO-D318] ADR-060: set hash:net,iface de protegidos (solo lo escribe el agente) y manifiesto\n"
         "        // firmado desde la caché. Sin manifiesto verificado el set queda vacío y el candado (D6) cerrado.\n"
         "        auto protegidos = std::make_shared<ProtegidosVigentes>(claves_protegidos_compiladas(),\n"
         "                                                               config.protegidos.hospital_id, config.protegidos.despliegue_id);\n"
         "        const bool protegidos_set_ok = protegidos_preparar_set(ipset, config);\n"
         "        protegidos_cargar_cache(*protegidos, ipset, config, protegidos_set_ok);\n"),
        ("regla de iptables con el set de protegidos",
         "        if (config.ipsets.count(\"whitelist\") > 0) {\n"
         "            firewall_config.whitelist_ipset = config.ipsets.at(\"whitelist\").set_name;\n"
         "            FIREWALL_LOG_INFO(\"Whitelist configured\",\n"
         "                \"ipset_name\", firewall_config.whitelist_ipset);\n"
         "        }\n",
         "        // [PROTEGIDOS-MANIFIESTO-D318] exención del kernel solo si el set es hash:net,iface (si no, solo la barrera)\n"
         "        firewall_config.protegidos_ipset = protegidos_set_ok ? config.protegidos.set_name : std::string();\n"),
        ("batch sin whitelist",
         "        batch_config.blacklist_ipset = blacklist_ipset.set_name;\n"
         "        if (config.ipsets.count(\"whitelist\") > 0) {\n"
         "            batch_config.whitelist_ipset = config.ipsets.at(\"whitelist\").set_name;\n"
         "        }\n"
         "\n"
         "        FIREWALL_LOG_INFO(\"Batch processor ipset configuration\",\n"
         "            \"blacklist_ipset\", batch_config.blacklist_ipset,\n"
         "            \"whitelist_ipset\", batch_config.whitelist_ipset);\n",
         "        batch_config.blacklist_ipset = blacklist_ipset.set_name;\n"
         "\n"
         "        FIREWALL_LOG_INFO(\"Batch processor ipset configuration\",\n"
         "            \"blacklist_ipset\", batch_config.blacklist_ipset);\n"),
        ("barrera de BatchProcessor",
         "    processor.set_rangos_protegidos(config.ddos_protegidos);  // [DDOS-MITIGACION-B2-D302] barrera (2 puertas)\n",
         "    processor.set_rangos_protegidos(*protegidos->rangos());  // [DDOS-MITIGACION-B2-D302] barrera (2 puertas); D318: del manifiesto\n"),
        ("suscriptor con lo vigente",
         "        zmq_config.ddos_protegidos = config.ddos_protegidos;  // [PROTEGIDOS-D300]\n",
         "        zmq_config.protegidos = protegidos;  // [PROTEGIDOS-MANIFIESTO-D318] lo vigente (ADR-060)\n"),
        ("modo de la mitigación",
         "        std::cout << \"[DDOS-MITIGACION] modo: \"\n"
         "                  << (!config.ddos_mitigacion.habilitada ? \"DESHABILITADA (sombra pura, no se llama a la mitigacion)\"\n",
         "        std::cout << \"[DDOS-MITIGACION] modo: \"\n"
         "                  << (!config.ddos_mitigacion.habilitada ? \"DESHABILITADA (sombra pura, no se llama a la mitigacion)\"\n"
         "                      : candado_cerrado(true, protegidos.get())\n"
         "                      ? \"BLOQUEADA POR EL CANDADO (sin manifiesto verificado de protegidos; sombra) [PROTEGIDOS-SIN-MANIFIESTO]\"\n"),
        ("log de los rangos protegidos",
         "        {\n"
         "            std::cout << \"[SOMBRA-DDOS] rangos protegidos (\"\n"
         "                      << (config.ddos_protegidos.por_defecto ? \"DEFECTO RFC 1918 + fc00::/7\" : \"JSON\") << \"):\";\n"
         "            for (const auto& r : config.ddos_protegidos.rangos) {\n",
         "        {\n"
         "            const auto vig = protegidos->vigente();\n"
         "            std::cout << \"[SOMBRA-DDOS] rangos protegidos (\"\n"
         "                      << (vig ? \"manifiesto version \" + std::to_string(vig->version) : std::string(\"NINGUNO: sin manifiesto verificado\"))\n"
         "                      << \"):\";\n"
         "            for (const auto& r : protegidos->rangos()->rangos) {\n"),
        ("vigilancia periódica en el bucle principal",
         "        auto last_health_check = std::chrono::steady_clock::now();\n",
         "        auto last_health_check = std::chrono::steady_clock::now();\n"
         "        auto last_protegidos = std::chrono::steady_clock::now();  // [PROTEGIDOS-MANIFIESTO-D318] D6/D7/D-C\n"),
        ("vigilancia periódica: llamada",
         "                if (elapsed_health >= 30) {\n",
         "                if (std::chrono::duration_cast<std::chrono::seconds>(now - last_protegidos).count() >=\n"
         "                    config.protegidos.aviso_sec) {\n"
         "                    protegidos_vigilar(*protegidos, config);  // [PROTEGIDOS-MANIFIESTO-D318]\n"
         "                    last_protegidos = now;\n"
         "                }\n"
         "\n"
         "                if (elapsed_health >= 30) {\n"),
        ("funciones de protegidos",
         "int main(int argc, char** argv) {\n",
         "// ═══════════════════════════════════════════════════════════════════════\n"
         "// [PROTEGIDOS-MANIFIESTO-D318] ADR-060: set del kernel, caché del manifiesto y vigilancia periódica\n"
         "// ═══════════════════════════════════════════════════════════════════════\n"
         "using ::mldefender::firewall::ProtegidosVigentes;\n"
         "using ::mldefender::firewall::ManifiestoVerificado;\n"
         "using ::mldefender::firewall::candado_cerrado;\n"
         "using ::mldefender::firewall::claves_protegidos_compiladas;\n"
         "\n"
         "// El set hash:net,iface existe y es de ese tipo (lo crea si falta). false = sin exención del kernel (solo barrera).\n"
         "static bool protegidos_preparar_set(IPSetWrapper& ipset, const FirewallAgentConfig& config) {\n"
         "    const auto& pc = config.protegidos;\n"
         "    const auto& k = claves_protegidos_compiladas();\n"
         "    std::cout << \"[PROTEGIDOS-CLAVE] actual huella=\" << ::mldefender::firewall::huella_clave_protegidos(k.actual)\n"
         "              << (k.hay_siguiente ? \" siguiente huella=\" + ::mldefender::firewall::huella_clave_protegidos(k.siguiente)\n"
         "                                  : std::string(\" siguiente=ninguna\"))\n"
         "              << \" (compiladas)\" << std::endl;\n"
         "    const auto tipo = ipset.set_type(pc.set_name);\n"
         "    if (tipo && *tipo != \"hash:net,iface\") {\n"
         "        std::cerr << \"[PROTEGIDOS-SET-TIPO] el set \" << pc.set_name << \" existe con tipo \" << *tipo\n"
         "                  << \" (se espera hash:net,iface): la exención del kernel NO se aplica; la barrera del agente sí protege. \"\n"
         "                     \"Con el agente parado: sudo ipset destroy \" << pc.set_name << std::endl;\n"
         "        return false;\n"
         "    }\n"
         "    if (tipo) {\n"
         "        std::cout << \"[PROTEGIDOS-SET] \" << pc.set_name << \" hash:net,iface ya existe\" << std::endl;\n"
         "        return true;\n"
         "    }\n"
         "    if (config.operation.dry_run) {\n"
         "        std::cout << \"[DRY-RUN] ipset create \" << pc.set_name << \" hash:net,iface family inet counters (no se crea en \"\n"
         "                     \"dry_run)\" << std::endl;\n"
         "        return true;\n"
         "    }\n"
         "    IPSetConfig c;\n"
         "    c.name = pc.set_name;\n"
         "    c.type = IPSetType::HASH_NET_IFACE;\n"
         "    c.family = IPSetFamily::INET;\n"
         "    c.hashsize = 1024;\n"
         "    c.maxelem = static_cast<uint32_t>(::mldefender::firewall::kProtegidosMaxEntradas);\n"
         "    c.timeout = 0;\n"
         "    c.counters = true;\n"
         "    c.comment = false;\n"
         "    if (!ipset.create_set(c)) {\n"
         "        std::cerr << \"[PROTEGIDOS-SET] ERROR: no se pudo crear \" << pc.set_name << \" (hash:net,iface): la exención del \"\n"
         "                     \"kernel NO se aplica; la barrera del agente sí protege\" << std::endl;\n"
         "        return false;\n"
         "    }\n"
         "    std::cout << \"[PROTEGIDOS-SET] \" << pc.set_name << \" hash:net,iface creado (vacío hasta verificar un manifiesto)\" << std::endl;\n"
         "    return true;\n"
         "}\n"
         "\n"
         "// Lleva al kernel las entradas IPv4 del manifiesto (sustitución atómica). IPv6: solo la barrera (D-I).\n"
         "static void protegidos_aplicar_kernel(IPSetWrapper& ipset, const std::string& set, const ManifiestoVerificado& m) {\n"
         "    std::vector<std::pair<std::string, std::string>> e;\n"
         "    std::size_t v6 = 0;\n"
         "    for (const auto& en : m.entradas) {\n"
         "        if (en.rango.v6) {\n"
         "            ++v6;\n"
         "            continue;\n"
         "        }\n"
         "        e.emplace_back(en.rango.texto, en.interfaz);\n"
         "    }\n"
         "    const auto r = ipset.replace_net_iface(set, e, static_cast<uint32_t>(::mldefender::firewall::kProtegidosMaxEntradas));\n"
         "    if (r) {\n"
         "        std::cout << \"[PROTEGIDOS-KERNEL] \" << set << \" = version \" << m.version << \": \" << e.size()\n"
         "                  << \" entradas cidr,interfaz (IPv6 solo en la barrera: \" << v6 << \"; DEBT-FW-IPV6-SETS-001)\" << std::endl;\n"
         "    } else {\n"
         "        std::cerr << \"[PROTEGIDOS-KERNEL] ERROR al cargar \" << set << \": \" << r.get_error().message\n"
         "                  << \"; la barrera del agente sí protege; revise: sudo ipset list \" << set << std::endl;\n"
         "    }\n"
         "}\n"
         "\n"
         "static void protegidos_infra(const ManifiestoVerificado& m, const FirewallAgentConfig& config) {\n"
         "    const auto f = ::mldefender::firewall::infra_sin_cubrir(m, config.protegidos.etcd_endpoints);\n"
         "    if (f.empty()) return;\n"
         "    std::ostringstream o;\n"
         "    for (std::size_t i = 0; i < f.size(); ++i) o << (i ? \" \" : \"\") << ::mldefender::firewall::detalle_protegidos::saneado(f[i]);\n"
         "    std::cerr << \"[PROTEGIDOS-INFRA-INCOMPLETA] etcd.endpoints sin entrada infraestructura en el manifiesto version \"\n"
         "              << m.version << \": \" << o.str() << \" (un DDoS podría dejar al plano de control en el blacklist: firme una \"\n"
         "                 \"versión que lo incluya con argus-infra)\" << std::endl;\n"
         "}\n"
         "\n"
         "// Arranque: el último manifiesto verificado está en la caché (ADR-060 D5.5).\n"
         "static void protegidos_cargar_cache(ProtegidosVigentes& v, IPSetWrapper& ipset, const FirewallAgentConfig& config,\n"
         "                                    bool set_ok) {\n"
         "    const auto& pc = config.protegidos;\n"
         "    if (pc.hospital_id.empty() || pc.despliegue_id.empty()) {\n"
         "        std::cerr << \"[PROTEGIDOS-SIN-MANIFIESTO] protegidos.hospital_id/despliegue_id sin valor: no hay manifiesto que \"\n"
         "                     \"verificar (candado cerrado)\" << std::endl;\n"
         "        return;\n"
         "    }\n"
         "    std::string sobre, err;\n"
         "    if (!::mldefender::firewall::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {\n"
         "        std::cerr << \"[PROTEGIDOS-SIN-MANIFIESTO] caché \" << pc.manifiesto_cache << \": \" << err\n"
         "                  << \" (hospital=\" << pc.hospital_id << \" planta=\" << pc.despliegue_id << \"; candado cerrado)\" << std::endl;\n"
         "        return;\n"
         "    }\n"
         "    const auto p = v.proponer(sobre);\n"
         "    if (!p.resultado.ok) {\n"
         "        std::cerr << \"[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=\" << ::mldefender::firewall::nombre_motivo(p.resultado.motivo)\n"
         "                  << \" \" << p.resultado.detalle << \" (caché \" << pc.manifiesto_cache << \"; candado cerrado)\" << std::endl;\n"
         "        return;\n"
         "    }\n"
         "    std::cout << ::mldefender::firewall::resumen_manifiesto(*p.resultado.manifiesto) << \" (caché \" << pc.manifiesto_cache\n"
         "              << \")\" << std::endl;\n"
         "    if (set_ok) protegidos_aplicar_kernel(ipset, pc.set_name, *p.resultado.manifiesto);\n"
         "    protegidos_infra(*p.resultado.manifiesto, config);\n"
         "}\n"
         "\n"
         "// Cada aviso_sec: sin manifiesto, aviso (D6); con él, la caché tiene que seguir verificando (D7) y el plano de\n"
         "// control tiene que estar dentro (D-C). Nunca se pierde lo vigente por un fallo de disco.\n"
         "static void protegidos_vigilar(const ProtegidosVigentes& v, const FirewallAgentConfig& config) {\n"
         "    const auto& pc = config.protegidos;\n"
         "    const auto m = v.vigente();\n"
         "    if (!m) {\n"
         "        std::cerr << \"[PROTEGIDOS-SIN-MANIFIESTO] sin manifiesto verificado (hospital=\" << pc.hospital_id << \" planta=\"\n"
         "                  << pc.despliegue_id << \" caché=\" << pc.manifiesto_cache << \"): \"\n"
         "                  << (candado_cerrado(config.ddos_mitigacion.habilitada, &v) ? \"mitigacion real BLOQUEADA (candado); sombra\"\n"
         "                                                                            : \"mitigacion deshabilitada\")\n"
         "                  << \"; ningún rango protegido\" << std::endl;\n"
         "        return;\n"
         "    }\n"
         "    std::string sobre, err;\n"
         "    if (!::mldefender::firewall::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {\n"
         "        std::cerr << \"[PROTEGIDOS-CACHE] no se puede leer \" << pc.manifiesto_cache << \": \" << err\n"
         "                  << \"; se conserva en memoria la version \" << m->version << \" (D7)\" << std::endl;\n"
         "    } else {\n"
         "        const auto r = v.reverificar(sobre);\n"
         "        if (!r.ok) {\n"
         "            std::cerr << \"[PROTEGIDOS-CACHE] la caché ya no verifica (motivo=\" << ::mldefender::firewall::nombre_motivo(r.motivo)\n"
         "                      << \" \" << r.detalle << \"): se conserva en memoria la version \" << m->version\n"
         "                      << \" (D7); vuelva a firmar con argus-infra\" << std::endl;\n"
         "        }\n"
         "    }\n"
         "    protegidos_infra(*m, config);\n"
         "}\n"
         "\n"
         "int main(int argc, char** argv) {\n"),
    ],
    TEST_EP: [
        ("intranet_lab desde parsear_rango",
         "RangosProtegidos intranet_lab() {\n"
         "    std::ostringstream log;\n"
         "    return construir_rangos_protegidos({}, {\"192.168.100.0/24\"}, {}, log);\n"
         "}\n",
         "RangosProtegidos intranet_lab() {  // [PROTEGIDOS-MANIFIESTO-D318] sin construir_rangos_protegidos (ADR-060)\n"
         "    RangosProtegidos r;\n"
         "    RangoProtegido x;\n"
         "    if (parsear_rango(\"192.168.100.0/24\", CategoriaProtegida::INTRANET, x)) r.rangos.push_back(x);\n"
         "    return r;\n"
         "}\n"),
    ],
    TEST_MAN: [
        ("rangos cacheados y candado",
         "    // 11. Caché: escribir y leer; ausente; enlace simbólico; tamaño\n",
         "    // 10b. [8e.1b] rangos cacheados (vacíos sin manifiesto) y candado (D6)\n"
         "    {\n"
         "        ProtegidosVigentes v(solo_a, \"hospital-lab\", \"lab-vagrant\");\n"
         "        CHECK(v.rangos() && v.rangos()->rangos.empty());\n"
         "        CHECK(candado_cerrado(true, &v) && !candado_cerrado(false, &v) && candado_cerrado(true, nullptr));\n"
         "        const std::string c1 = carga(1, kLab);\n"
         "        CHECK(v.proponer(sobre(c1, firmar(a, c1))).resultado.ok);\n"
         "        CHECK(!candado_cerrado(true, &v));\n"
         "        const auto r1 = v.rangos();\n"
         "        CHECK(r1->rangos.size() == 2 && r1->categoria_de(\"192.168.100.20\") == C::INFRAESTRUCTURA);\n"
         "        const std::string c2 = carga(2, entrada(\"intranet\", \"192.168.100.61/32\"));\n"
         "        CHECK(!v.proponer(sobre(c2, firmar(otra, c2))).resultado.ok);\n"
         "        CHECK(v.rangos() == r1);   // un rechazo no toca los rangos\n"
         "        CHECK(v.proponer(sobre(c2, firmar(a, c2))).resultado.ok);\n"
         "        CHECK(v.rangos()->rangos.size() == 1 && v.rangos()->categoria_de(\"192.168.100.20\") == C::NINGUNA);\n"
         "        CHECK(r1->rangos.size() == 2);   // quien tenía la copia anterior la conserva entera\n"
         "    }\n"
         "    // 11. Caché: escribir y leer; ausente; enlace simbólico; tamaño\n"),
    ],
}

JSON_ = JSON
SH_E2E = "scripts/timebase/d302_mitigacion_e2e.sh"
CAMBIOS[JSON] = [
    ("bloque protegidos en lugar de ddos_protegidos",
     '  "ddos_protegidos": {\n    "_doc": "[PROTEGIDOS-D300] DEBT-FW-PROTECTED-RANGES-001. Rangos cuyo trafico NUNCA bloquea automaticamente la cabeza DDoS: un DROP cuyo ORIGEN cae aqui se registra como [SOMBRA-DDOS] ALERTA_PROTEGIDO (categoria, victima, evento) y no cuenta para el episodio de la victima. Tres listas de cadenas CIDR, IPv4 o IPv6 con prefijo opcional (/0-32 o /0-128; sin prefijo = un solo host): dmz (servidores publicados), intranet (redes internas), externos_criticos (resolvedores DNS, servidores NTP, operador, socios). Se comprueban en ese orden y gana la primera coincidencia. Una entrada mal formada se descarta con [CONFIG-DEFAULT] y el resto sigue protegiendo. Si NO queda ningun rango valido (bloque ausente, listas vacias o todas las entradas invalidas) se protegen por defecto los rangos privados RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) y fc00::/7 como intranet, avisando con [CONFIG-DEFAULT] en el arranque y en cada resumen: un olvido nunca deja la intranet expuesta a un bloqueo automatico. Cada valor valido se registra con [CONFIG] en el arranque. Guia: docs/operaciones/GUIA_OPERACIONES.md, seccion DDOS-PROTEGIDOS.",\n    "_doc_laboratorio": "VALORES DE LABORATORIO, NO DE PRODUCCION. En el lab Vagrant toda la red es privada (192.168.100.0/24) y la VM client simula INTERNET: 192.168.100.50 (atacante) y 192.168.100.51 (origen benigno) NO deben estar protegidos, porque entonces no se podria medir la cabeza DDoS. 192.168.100.61 simula un host INTERNO y se protege para probar ALERTA_PROTEGIDO. En un despliegue real estos valores los calcula o los pide el script de despliegue de cada instalacion (plantillas por instalacion: BACKLOG DEBT-DEPLOY-TEMPLATES-001). Nunca copiar estos valores a produccion.",\n    "dmz": [],\n    "intranet": ["192.168.100.61/32"],\n    "externos_criticos": []\n  },\n',
     '  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060. Los rangos que aRGus NUNCA bloquea salen SOLO del manifiesto firmado de protegidos (Vault transit del hospital; clave publica compilada en el agente): aqui no hay rangos. Un DROP de la cabeza DDoS cuyo ORIGEN cae en un rango del manifiesto se registra como [SOMBRA-DDOS] ALERTA_PROTEGIDO y nunca se bloquea (la barrera protege por IP, entre por la interfaz que entre). En el kernel, el set hash:net,iface set_name (lo crea y lo escribe solo el agente, por sustitucion atomica) exime cada rango por su interfaz de entrada: --match-set <set> src,src -j RETURN. CANDADO: con ddos_mitigacion.habilitada=true y sin manifiesto verificado la mitigacion no actua ([PROTEGIDOS-SIN-MANIFIESTO] al arrancar y cada aviso_sec). hospital_id y despliegue_id: [a-z0-9-], de 1 a 64, sin defecto (ausentes o mal formados = sin manifiesto, candado cerrado). set_name: [A-Za-z0-9_-], de 1 a 29 (defecto ml_defender_protegidos). manifiesto_cache: ruta absoluta del ultimo manifiesto verificado (defecto /var/lib/ml-defender/firewall/protegidos.manifiesto). aviso_sec: entero en [30, 86400] (defecto 300), avisos periodicos y nueva verificacion de la cache. Cada valor se registra con [CONFIG], [CONFIG-DEFAULT] o [CONFIG-AVISO].",\n    "_doc_laboratorio": "VALORES DE LABORATORIO (ADR-060 E3): hospital-lab / lab-vagrant. El manifiesto del lab lo firma argus-infra en la VM etcd (pasos 8e.3 y 8e.5). Nunca copiar estos valores a produccion.",\n    "hospital_id": "hospital-lab",\n    "despliegue_id": "lab-vagrant",\n    "set_name": "ml_defender_protegidos",\n    "manifiesto_cache": "/var/lib/ml-defender/firewall/protegidos.manifiesto",\n    "aviso_sec": 300\n  },\n'),
    ("_doc de ddos_mitigacion",
     'nunca la victima ni un origen protegido (ddos_protegidos).',
     'nunca la victima ni un origen protegido (manifiesto firmado de protegidos, ADR-060; sin manifiesto verificado no actua: candado).'),
    ("fuera ipsets.whitelist",
     '    },\n    "whitelist": {\n      "set_name": "ml_defender_whitelist",\n      "_doc_set_type": "[DDOS-MITIGACION-B1-D301] hash:ip (hosts) o hash:net (redes CIDR); otro valor = hash:ip con [CONFIG-DEFAULT]. La whitelist es hash:net para alojar los rangos protegidos (ddos_protegidos). Un set que YA existe en el kernel no cambia de tipo: con el agente parado, sudo ipset destroy <set_name>.",\n      "set_type": "hash:net",\n      "hash_size": 512,\n      "max_elements": 500,\n      "timeout": 0,\n      "comment": "ML Defender whitelisted IPs",\n      "family": "inet",\n      "create_if_missing": true,\n      "flush_on_startup": false\n    }\n',
     '    }\n'),
]
CAMBIOS[SH_E2E] = [
    ("set de protegidos en lugar de la whitelist",
     'WL=$(python3 -c \'import json,sys; print(json.load(open(sys.argv[1]))["ipsets"]["whitelist"]["set_name"])\' "$JSON") || falla "no leo ipsets.whitelist.set_name"\n',
     'WL=$(python3 -c \'import json,sys; print(json.load(open(sys.argv[1])).get("protegidos", {}).get("set_name", "ml_defender_protegidos"))\' "$JSON") || falla "no leo protegidos.set_name"  # [PROTEGIDOS-MANIFIESTO-D318]\n'),
]

REESCRITO_0_RUTA = 'firewall-acl-agent/tests/unit/test_ddos_protegidos.cpp'
REESCRITO_0_VIEJO = '9dbc8b1f017902f0ba2c6336a6478e44086b79224c4bd140396672f5a56d5249'
REESCRITO_0_SHA = '9410e7965e6211268c3bbc9d460b86296616c55f95b87b89abd3ef59636d650a'
REESCRITO_0 = r'''// test_ddos_protegidos.cpp — [PROTEGIDOS-D300] rangos protegidos: análisis de CIDR y pertenencia. Standalone, CHECK propio.
// [PROTEGIDOS-MANIFIESTO-D318] ADR-060: los rangos salen solo del manifiesto firmado (test_protegidos_manifiesto.cpp);
// fuera construir_rangos_protegidos y el defecto RFC 1918, y con ellos sus casos.
#include "firewall/ddos_protegidos.hpp"
#include <iostream>
#include <string>
#include <vector>

using namespace mldefender::firewall;
using C = CategoriaProtegida;

static int g_fallos = 0;
static int g_checks = 0;
#define CHECK(c)                                                              \
    do {                                                                      \
        ++g_checks;                                                           \
        if (!(c)) {                                                           \
            std::cerr << "FALLO linea " << __LINE__ << ": " #c << std::endl;  \
            ++g_fallos;                                                       \
        }                                                                     \
    } while (0)

static RangosProtegidos rangos(const std::vector<std::pair<std::string, C>>& v) {
    RangosProtegidos r;
    for (const auto& [cidr, cat] : v) {
        RangoProtegido x;
        if (parsear_rango(cidr, cat, x)) r.rangos.push_back(x);
    }
    return r;
}

int main() {
    // 1. Host único; vecinos no protegidos.
    {
        auto r = rangos({{"192.168.100.61/32", C::INTRANET}, {"192.168.100.20/32", C::INFRAESTRUCTURA}});
        CHECK(r.categoria_de("192.168.100.61") == C::INTRANET);
        CHECK(r.categoria_de("192.168.100.20") == C::INFRAESTRUCTURA);
        CHECK(r.categoria_de("192.168.100.50") == C::NINGUNA);
        CHECK(std::string(nombre_categoria(C::INFRAESTRUCTURA)) == "infraestructura");
        CHECK(std::string(nombre_categoria(C::NINGUNA)) == "ninguna");
    }
    // 2. Red /24 y frontera; red no normalizada; IP sin prefijo = host.
    {
        auto r = rangos({{"192.168.100.77/24", C::DMZ}, {"10.1.2.3", C::INTRANET}});
        CHECK(r.categoria_de("192.168.100.1") == C::DMZ);
        CHECK(r.categoria_de("192.168.100.254") == C::DMZ);
        CHECK(r.categoria_de("192.168.101.1") == C::NINGUNA);
        CHECK(r.categoria_de("10.1.2.3") == C::INTRANET);
        CHECK(r.categoria_de("10.1.2.4") == C::NINGUNA);
        RangoProtegido x;
        CHECK(parsear_rango("192.168.100.77/24", C::DMZ, x) && x.red[3] == 0 && x.prefijo == 24);
    }
    // 3. Prefijo no múltiplo de 8 (/12).
    {
        auto r = rangos({{"172.16.0.0/12", C::EXTERNOS_CRITICOS}});
        CHECK(r.categoria_de("172.31.255.255") == C::EXTERNOS_CRITICOS);
        CHECK(r.categoria_de("172.32.0.1") == C::NINGUNA);
        CHECK(r.categoria_de("172.15.255.255") == C::NINGUNA);
    }
    // 4. IPv6 /128 y /64; las familias no se mezclan.
    {
        auto r = rangos({{"2001:db8:1:2::/64", C::INTRANET}, {"fd00::20/128", C::INFRAESTRUCTURA}});
        CHECK(r.categoria_de("2001:db8:1:2::abcd") == C::INTRANET);
        CHECK(r.categoria_de("2001:db8:1:3::1") == C::NINGUNA);
        CHECK(r.categoria_de("fd00::20") == C::INFRAESTRUCTURA);
        CHECK(r.categoria_de("fd00::21") == C::NINGUNA);
        CHECK(r.categoria_de("192.168.1.1") == C::NINGUNA);
    }
    // 5. Entradas inválidas: parsear_rango las rechaza (nunca protege por error).
    {
        RangoProtegido x;
        for (const std::string& e : {std::string("999.1.1.1"), std::string("10.0.0.0/33"), std::string("abc"),
                                     std::string("1.2.3.4;rm -rf /"), std::string("1.2.3.4\nINYECTADO"),
                                     std::string("::/129"), std::string("")}) {
            CHECK(!parsear_rango(e, C::INTRANET, x));
        }
    }
    // 6. IP de consulta inválida o vacía: NINGUNA; sin rangos, nada protegido.
    {
        auto r = rangos({{"10.0.0.0/8", C::INTRANET}});
        CHECK(r.categoria_de("") == C::NINGUNA);
        CHECK(r.categoria_de("no-es-ip") == C::NINGUNA);
        RangosProtegidos vacio;
        CHECK(vacio.categoria_de("10.1.2.3") == C::NINGUNA);
    }
    // 7. Primera coincidencia gana (el manifiesto ordena: infraestructura delante, luego lo más específico).
    {
        auto r = rangos({{"10.0.0.0/8", C::DMZ}, {"10.1.0.0/16", C::INTRANET}});
        CHECK(r.categoria_de("10.1.2.3") == C::DMZ);
    }
    // 8. El log no se rompe con entradas hostiles.
    {
        const std::string s = detalle_protegidos::saneado("a\nb\x01" + std::string(100, 'x'));
        CHECK(s.find('\n') == std::string::npos && s.size() <= 67);
    }

    if (g_fallos != 0) {
        std::cerr << "test_ddos_protegidos: " << g_fallos << " FALLOS de " << g_checks << " comprobaciones" << std::endl;
        return 1;
    }
    std::cout << "OK test_ddos_protegidos: " << g_checks << " comprobaciones" << std::endl;
    return 0;
}
'''

REESCRITO_1_RUTA = 'firewall-acl-agent/tests/unit/test_argus_cadena_root.cpp'
REESCRITO_1_VIEJO = 'c31859cb9ce00ad33cdf21c75c4121ac50a7b897571c0fa20cf90bef0dfaf8b5'
REESCRITO_1_SHA = 'e3f25091ead2f9c1785938b1ccadc7994af5714018da805bad2da9b50b352424'
REESCRITO_1 = r'''// test_argus_cadena_root.cpp -- [ARGUS-CADENA-D301] reglas base de aRGus contra el KERNEL real.
// Requiere root (make test-firewall-e2e). Sin root sale con 77 = Skipped en ctest (SKIP_RETURN_CODE), nunca un
// Passed falso. Comprueba: blacklist con timeout real, un único salto INPUT -> cadena en posición 1, dentro solo
// protegidos RETURN y blacklist DROP, sin ACCEPT ni rate limiting, idempotencia (dos llamadas) y limpieza completa.
// [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D-A: el set de protegidos es hash:net,iface; la regla casa origen E interfaz
// de entrada (src,src); su contenido se sustituye de forma atómica (temporal + swap) y se lee el tipo del set.
#include "firewall/ipset_wrapper.hpp"
#include "firewall/iptables_wrapper.hpp"

#include <unistd.h>
#include <sys/wait.h>

#include <cstdio>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace mldefender::firewall;

static int g_total = 0;
static int g_fallos = 0;
#define CHECK(c)                                                            \
    do {                                                                    \
        ++g_total;                                                          \
        if (!(c)) {                                                         \
            ++g_fallos;                                                     \
            std::cerr << "FALLA linea " << __LINE__ << ": " #c << std::endl; \
        }                                                                   \
    } while (0)

static std::string sh(const std::string& cmd) {
    std::string out;
    FILE* p = ::popen((cmd + " 2>&1").c_str(), "r");
    if (!p) return out;
    char buf[512];
    while (std::fgets(buf, sizeof(buf), p)) out += buf;
    ::pclose(p);
    return out;
}

static std::vector<std::string> lineas(const std::string& s) {
    std::vector<std::string> v;
    std::istringstream is(s);
    std::string l;
    while (std::getline(is, l)) v.push_back(l);
    return v;
}

static bool tiene(const std::string& s, const std::string& sub) { return s.find(sub) != std::string::npos; }
static bool en_set(const std::string& set, const std::string& elem) {
    return sh("ipset test " + set + " " + elem + " >/dev/null 2>&1; echo $?").rfind("0", 0) == 0;
}

int main() {
    if (::geteuid() != 0) {
        std::cout << "SALTADO: requiere root (make test-firewall-e2e PROFILE=...)" << std::endl;
        return 77;
    }
    const std::string CH = "ARGUS_T301";
    const std::string PR = "d318t_prot";
    const std::string MAL = "d318t_mal";
    const std::string BL = "d301t_bl";
    // hash:net,iface casa por NOMBRE de interfaz, exista o no en esta máquina (la del lab hacia la LAN es eth2).
    const std::string IF = "eth2";
    auto limpiar = [&]() {
        for (int i = 0; i < 8; ++i) sh("iptables -t filter -D INPUT -j " + CH);
        sh("iptables -t filter -F " + CH);
        sh("iptables -t filter -X " + CH);
        for (const auto& s : {PR, PR + "_n", MAL, BL}) sh("ipset destroy " + s);
    };
    limpiar();

    IPSetWrapper ips;
    IPSetConfig pr;
    pr.name = PR;
    pr.type = IPSetType::HASH_NET_IFACE;
    pr.family = IPSetFamily::INET;
    pr.timeout = 0;
    pr.maxelem = 65536;
    CHECK(static_cast<bool>(ips.create_set(pr)));
    CHECK(ips.set_type(PR).value_or("") == "hash:net,iface");
    CHECK(!ips.set_type("d318t_no_existe").has_value());
    IPSetConfig mal;
    mal.name = MAL;
    mal.type = IPSetType::HASH_NET;
    mal.family = IPSetFamily::INET;
    CHECK(static_cast<bool>(ips.create_set(mal)));
    CHECK(ips.set_type(MAL).value_or("") == "hash:net");

    // Sustitución atómica: primera carga, segunda carga (sustituye, no suma), vacía, y entradas malas (no toca nada)
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {{"192.168.100.20/32", IF}, {"192.168.100.61/32", IF}}, 65536)));
    CHECK(en_set(PR, "192.168.100.20," + IF));
    CHECK(!en_set(PR, "192.168.100.20,eth0"));
    CHECK(en_set(PR, "192.168.100.61," + IF));
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {{"192.168.100.20/32", IF}}, 65536)));
    CHECK(en_set(PR, "192.168.100.20," + IF));
    CHECK(!en_set(PR, "192.168.100.61," + IF));
    CHECK(!ips.replace_net_iface(PR, {{"192.168.100.30/32", IF}, {"1.2.3.4;rm", IF}}, 65536));
    CHECK(!ips.replace_net_iface(PR, {{"192.168.100.30/32", "eth2 x"}}, 65536));
    CHECK(en_set(PR, "192.168.100.20," + IF));   // un rechazo no toca el set
    CHECK(!en_set(PR, "192.168.100.30," + IF));
    CHECK(!tiene(sh("ipset list -n"), PR + "_n"));   // el temporal no queda
    CHECK(!ips.replace_net_iface("d318t_no_existe", {{"192.168.100.20/32", IF}}, 65536));
    CHECK(!ips.replace_net_iface(MAL, {{"192.168.100.20/32", IF}}, 65536));   // swap entre tipos distintos: falla
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {}, 65536)));
    CHECK(!en_set(PR, "192.168.100.20," + IF));
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {{"192.168.100.20/32", IF}}, 65536)));

    IPSetConfig bl;
    bl.name = BL;
    bl.type = IPSetType::HASH_IP;
    bl.family = IPSetFamily::INET;
    bl.timeout = 60;
    CHECK(static_cast<bool>(ips.create_set(bl)));
    IPSetEntry e{"203.0.113.77"};
    e.timeout = 30;
    CHECK(static_cast<bool>(ips.add_batch(BL, {e})));
    CHECK(ips.test(BL, "203.0.113.77"));

    FirewallConfig fc;
    fc.blacklist_chain = CH;
    fc.protegidos_ipset = PR;
    fc.blacklist_ipset = BL;
    fc.enable_rate_limiting = false;
    IPTablesWrapper ipt;
    for (int vuelta = 1; vuelta <= 2; ++vuelta) {
        CHECK(static_cast<bool>(ipt.setup_base_rules(fc)));
        const auto in = lineas(sh("iptables -t filter -S INPUT"));
        int saltos = 0;
        std::string primera;
        for (const auto& l : in) {
            if (l.rfind("-A INPUT", 0) == 0) {
                if (primera.empty()) primera = l;
                if (tiene(l, "-j " + CH)) ++saltos;
            }
            CHECK(!tiene(l, "RATELIMIT"));
        }
        CHECK(saltos == 1);
        CHECK(tiene(primera, "-j " + CH));
        std::vector<std::string> reglas;
        for (const auto& l : lineas(sh("iptables -t filter -S " + CH))) {
            if (l.rfind("-A " + CH, 0) == 0) reglas.push_back(l);
            CHECK(!tiene(l, "ACCEPT"));
        }
        CHECK(reglas.size() == 2);
        if (reglas.size() == 2) {
            CHECK(tiene(reglas[0], "--match-set " + PR + " src,src") && tiene(reglas[0], "-j RETURN"));
            CHECK(tiene(reglas[0], "argus-protegidos"));
            CHECK(tiene(reglas[1], "--match-set " + BL + " src") && tiene(reglas[1], "-j DROP"));
        }
        std::cout << "vuelta " << vuelta << ": saltos=" << saltos << " reglas_en_cadena=" << reglas.size()
                  << (reglas.empty() ? std::string() : " protegidos: " + reglas[0]) << std::endl;
    }
    // Con la cadena enganchada, el set sigue sustituyéndose (References > 0)
    CHECK(static_cast<bool>(ips.replace_net_iface(PR, {{"192.168.100.21/32", IF}}, 65536)));
    CHECK(en_set(PR, "192.168.100.21," + IF) && !en_set(PR, "192.168.100.20," + IF));
    CHECK(tiene(sh("iptables -t filter -S " + CH), "--match-set " + PR + " src,src"));

    const std::string lista = sh("ipset list " + BL);
    const auto pos = lista.find("203.0.113.77 timeout ");
    CHECK(pos != std::string::npos);
    if (pos != std::string::npos) {
        const long t = std::strtol(lista.c_str() + pos + std::string("203.0.113.77 timeout ").size(), nullptr, 10);
        std::cout << "timeout restante de 203.0.113.77 = " << t << " s" << std::endl;
        CHECK(t >= 1 && t <= 30);
    }

    // Sin set de protegidos (tipo equivocado en el arranque): solo la regla del blacklist
    FirewallConfig fc2 = fc;
    fc2.protegidos_ipset = "";
    CHECK(static_cast<bool>(ipt.setup_base_rules(fc2)));
    int n = 0;
    for (const auto& l : lineas(sh("iptables -t filter -S " + CH))) {
        if (l.rfind("-A " + CH, 0) == 0) ++n;
    }
    CHECK(n == 1);

    limpiar();
    CHECK(!tiene(sh("iptables -t filter -S INPUT"), CH));
    CHECK(!tiene(sh("ipset list -n"), PR));
    std::cout << "test_argus_cadena_root: " << (g_total - g_fallos) << "/" << g_total << " comprobaciones OK" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
'''
REESCRITOS = [(REESCRITO_0_RUTA, REESCRITO_0_VIEJO, REESCRITO_0_SHA, REESCRITO_0), (REESCRITO_1_RUTA, REESCRITO_1_VIEJO, REESCRITO_1_SHA, REESCRITO_1)]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d318_8e1b_cableado.py --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    errores, hechos, pendientes = [], [], []
    escribir = {}
    for rel, viejo, esperado, contenido in REESCRITOS:
        b = contenido.encode("utf-8")
        if sha(b) != esperado:
            errores.append(f"{rel}: el contenido embebido no da su sha256 (parcheador dañado)")
            continue
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        actual = sha(open(p, "rb").read())
        print(f"sha256 previo  {rel}: {actual}")
        if actual == esperado:
            hechos.append(f"{rel}: reescrito")
        elif actual == viejo:
            pendientes.append(f"{rel}: reescribir")
            escribir[rel] = b
        else:
            errores.append(f"{rel}: sha256 {actual}, ni el viejo esperado ni el nuevo")
    orig, nuevo = {}, {}
    for rel, cambios in CAMBIOS.items():
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        orig[rel] = open(p, "rb").read()
        print(f"sha256 previo  {rel}: {sha(orig[rel])}")
        t = orig[rel].decode("utf-8")
        for nombre, viejo, nv in cambios:
            cv, cn = t.count(viejo), (t.count(nv) if nv else 0)
            if nv and viejo in nv:      # inserción: el texto viejo sigue dentro del nuevo
                aplicar, hecho = cv == 1 and cn == 0, cn == 1
            elif nv in viejo:           # borrado o recorte: el nuevo cabe dentro del viejo
                aplicar, hecho = cv == 1, cv == 0 and (not nv or cn >= 1)
            else:
                aplicar, hecho = cv == 1 and cn == 0, cv == 0 and cn == 1
            if aplicar:
                t = t.replace(viejo, nv)
                pendientes.append(f"{rel}: {nombre}")
            elif hecho:
                hechos.append(f"{rel}: {nombre}")
            else:
                errores.append(f"{rel}: {nombre}: texto viejo {cv} veces, nuevo {cn} veces")
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
        todo = dict(escribir)
        for rel in CAMBIOS:
            if nuevo[rel] != orig[rel]:
                todo[rel] = nuevo[rel]
        for rel, b in todo.items():
            p = os.path.join(raiz, rel)
            m = os.stat(p).st_mode
            with open(p + ".d318tmp", "wb") as f:
                f.write(b)
            os.chmod(p + ".d318tmp", m)
            os.replace(p + ".d318tmp", p)
    for rel, _, esperado, _ in REESCRITOS:
        print(f"sha256 final   {rel}: {esperado}")
    for rel in CAMBIOS:
        estado = "igual" if nuevo[rel] == orig[rel] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {rel}: {sha(nuevo[rel])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
