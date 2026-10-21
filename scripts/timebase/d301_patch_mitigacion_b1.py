#!/usr/bin/env python3
"""DAY301 -- patcher atomico [DDOS-MITIGACION-B1-D301] tanda 3b-b1: configuracion de la mitigacion ddos_v2.
 include/firewall/config_loader.hpp   include ddos_mitigacion.hpp; FirewallAgentConfig::ddos_mitigacion; escalera de
                                      produccion en RecidivismConfigNew.
 src/core/config_loader.cpp           bloque ddos_mitigacion ([CONFIG] por valor valido, [CONFIG-DEFAULT] si falta o es
                                      invalido); parse_recidivism valida strike_durations_sec (lista no vacia en [1, 2147483]).
 include/firewall/batch_processor.hpp escalera de produccion en RecidivismConfig.
 src/main.cpp                         set_type del JSON (hash:ip|hash:net, antes HASH_IP fijo); [CONFIG] de la escalera
                                      efectiva y [CONFIG-AVISO] de escalones por debajo de aviso_castigo_corto_sec.
 config/firewall.json                 bloque ddos_mitigacion (habilitada=false), escalera de produccion, whitelist hash:net.
Uso: --check | --apply. Idempotente por la marca. No commitea. Se ejecuta en el DEFENDER."""
import json
import re
import sys
from pathlib import Path

MARK = "[DDOS-MITIGACION-B1-D301]"
FW = Path("/vagrant/firewall-acl-agent")
F = {
    "cfg_hpp": FW / "include/firewall/config_loader.hpp",
    "cfg_cpp": FW / "src/core/config_loader.cpp",
    "bp_hpp": FW / "include/firewall/batch_processor.hpp",
    "main": FW / "src/main.cpp",
    "json": FW / "config/firewall.json",
}
ESCALERA = [3600, 86400, 604800, 2073600]


def fail(m):
    print("ABORTA:", m)
    sys.exit(1)


def once(t, a, n):
    c = t.count(a)
    if c != 1:
        fail("%s: ancla encontrada %d veces" % (n, c))


def after(t, a, i, n):
    once(t, a, n)
    return t.replace(a, a + i)


def before(t, a, i, n):
    once(t, a, n)
    return t.replace(a, i + a)


def repl(t, a, b, n):
    once(t, a, n)
    return t.replace(a, b)


def first_include(t, ins, n):
    L = t.splitlines(keepends=True)
    i = next((k for k, l in enumerate(L) if l.startswith("#include")), None)
    if i is None:
        fail("%s: sin #include" % n)
    return "".join(L[:i]) + ins + "".join(L[i:])


def p_cfg_hpp(t):
    t = first_include(t, '#include "firewall/ddos_mitigacion.hpp"  // ' + MARK + "\n", "cfg_hpp include")
    t = after(t, "    ::mldefender::firewall::RangosProtegidos ddos_protegidos;  // [PROTEGIDOS-D300] rangos protegidos de la cabeza DDoS\n",
              "    ::mldefender::firewall::DdosMitigacionParams ddos_mitigacion;  // " + MARK + " mitigacion real de ddos_v2\n",
              "cfg_hpp miembro")
    return repl(t, "    std::vector<int> strike_durations_sec = {60, 300, 3600, 86400, 604800};\n",
                "    std::vector<int> strike_durations_sec = {3600, 86400, 604800, 2073600};  // " + MARK + " 1 h, 1 d, 7 d, 24 d\n",
                "cfg_hpp escalera")


CFG_BLOQUE = r"""    {   // __MARK__ mitigacion real de la cabeza ddos_v2 (paso 3b)
        ::mldefender::firewall::DdosMitigacionParams dm;
        const Json::Value s = root.isMember("ddos_mitigacion") ? root["ddos_mitigacion"] : Json::Value(Json::nullValue);
        if (!s.isObject()) {
            std::cerr << "[CONFIG-DEFAULT] ddos_mitigacion ausente o no es un objeto: habilitada=false (sombra pura) "
                         "min_drops_origen=1 aviso_castigo_corto_sec=3600 max_origenes=100000" << std::endl;
        } else {
            auto get_int = [&s](const char* name, int def, int lo, int hi) -> int {
                if (s.isMember(name) && s[name].isInt() && s[name].asInt() >= lo && s[name].asInt() <= hi) {
                    std::cout << "[CONFIG] ddos_mitigacion." << name << "=" << s[name].asInt() << std::endl;
                    return s[name].asInt();
                }
                std::cerr << "[CONFIG-DEFAULT] ddos_mitigacion." << name << " ausente, no entero o fuera de rango (entero en ["
                          << lo << ", " << hi << "]): se usa " << def << std::endl;
                return def;
            };
            if (s.isMember("habilitada") && s["habilitada"].isBool()) {
                dm.habilitada = s["habilitada"].asBool();
                std::cout << "[CONFIG] ddos_mitigacion.habilitada=" << (dm.habilitada ? "true" : "false") << std::endl;
            } else {
                std::cerr << "[CONFIG-DEFAULT] ddos_mitigacion.habilitada ausente o no booleano (formato true|false): "
                             "se usa false (sombra pura)" << std::endl;
            }
            dm.min_drops_origen = get_int("min_drops_origen", 1, 1, 100);
            dm.aviso_castigo_corto_sec = get_int("aviso_castigo_corto_sec", 3600, 1, 2147483);
            dm.max_origenes = get_int("max_origenes", 100000, 1, 10000000);
        }
        config.ddos_mitigacion = dm;
    }
""".replace("__MARK__", MARK)

REC_A = """    if (json.isMember("strike_durations_sec")) {
        config.strike_durations_sec = parse_int_array(json["strike_durations_sec"]);
    }
"""
REC_N = r"""    {   // __MARK__ escalera validada: lista no vacia de enteros en [1, 2147483] s; si no, defecto de produccion
        const Json::Value& a = json["strike_durations_sec"];
        bool ok = json.isMember("strike_durations_sec") && a.isArray() && !a.empty();
        std::vector<int> v;
        if (ok) {
            for (const auto& e : a) {
                if (!e.isInt() || e.asInt() < 1 || e.asInt() > 2147483) {
                    ok = false;
                    break;
                }
                v.push_back(e.asInt());
            }
        }
        if (ok) {
            config.strike_durations_sec = v;
        } else {
            std::cerr << "[CONFIG-DEFAULT] recidivism.strike_durations_sec ausente, vacia o con valores fuera de rango (lista "
                         "no vacia de enteros en [1, 2147483] s): se usa la escalera de produccion [3600, 86400, 604800, 2073600]"
                      << std::endl;
        }
    }
""".replace("__MARK__", MARK)


def p_cfg_cpp(t):
    t = before(t, "    {   // [PROTEGIDOS-D300] DEBT-FW-PROTECTED-RANGES-001: rangos protegidos de la cabeza DDoS\n", CFG_BLOQUE,
               "cfg_cpp bloque")
    return repl(t, REC_A, REC_N, "cfg_cpp parse_recidivism")


def p_bp_hpp(t):
    return repl(t, "    std::vector<uint32_t> strike_durations_sec{60, 300, 3600, 86400, 604800};\n",
                "    std::vector<uint32_t> strike_durations_sec{3600, 86400, 604800, 2073600};  // " + MARK + " 1 h, 1 d, 7 d, 24 d\n",
                "bp_hpp escalera")


MAIN_TIPO = r"""                    // __MARK__ el tipo sale del JSON (antes HASH_IP fijo: set_type se ignoraba)
                    if (ipset_cfg.set_type == "hash:net") {
                        ipset_config.type = IPSetType::HASH_NET;
                    } else {
                        if (ipset_cfg.set_type != "hash:ip") {
                            std::cerr << "[CONFIG-DEFAULT] ipsets." << name << ".set_type '"
                                      << ::mldefender::firewall::saneado(ipset_cfg.set_type)
                                      << "' no admitido (formato: hash:ip | hash:net): se usa hash:ip" << std::endl;
                        }
                        ipset_config.type = IPSetType::HASH_IP;
                    }
                    std::cout << "[CONFIG] ipsets." << name << ".set_type="
                              << (ipset_config.type == IPSetType::HASH_NET ? "hash:net" : "hash:ip") << std::endl;
""".replace("__MARK__", MARK)

MAIN_REC = r"""    {   // __MARK__ escalera efectiva al log y aviso de castigos de prueba
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
""".replace("__MARK__", MARK)


def p_main(t):
    t = first_include(t, "#include <sstream>  // " + MARK + "\n", "main include")
    t = repl(t, "                    ipset_config.type = IPSetType::HASH_IP;\n", MAIN_TIPO, "main set_type")
    return after(t, "    processor.set_recidivism_config(recidivism_config);  // RECIDIVISM-D276\n", MAIN_REC, "main recidivism")


DOC_ESC = (MARK + " Escalera de castigo en segundos por strike (indice 0 = 1.er strike). Lista no vacia de enteros en "
           "[1, 2147483] (techo medido de ipset); nunca 0 ni permanente. Defecto de produccion [3600, 86400, 604800, 2073600] "
           "= 1 h, 1 dia, 7 dias, 24 dias (decision de Alonso DAY301: el castigo debe durar mas que la rafaga y dar tiempo al "
           "admin y a las autoridades para investigar). Ausente o invalida: defecto con [CONFIG-DEFAULT]. Los escalones por "
           "debajo de ddos_mitigacion.aviso_castigo_corto_sec se aplican pero se avisan con [CONFIG-AVISO]: solo pruebas.")
DOC_TIPO = (MARK + " hash:ip (hosts) o hash:net (redes CIDR); otro valor = hash:ip con [CONFIG-DEFAULT]. La whitelist es "
            "hash:net para alojar los rangos protegidos (ddos_protegidos). Un set que YA existe en el kernel no cambia de "
            "tipo: con el agente parado, sudo ipset destroy <set_name>.")
DOC_MIT = (MARK + " Mitigacion REAL de la cabeza ddos_v2 (paso 3b): bloquea en el ipset blacklist la IP de ORIGEN de los DROP "
           "de ddos_v2 solo mientras su victima {dst, proto} esta en episodio (INICIO..FIN de ddos_shadow); nunca la victima "
           "ni un origen protegido (ddos_protegidos). Doble llave: solo bloquea si operation.dry_run=false Y habilitada=true; "
           "con dry_run=true se registra lo que se haria. Un episodio = un strike de reincidencia (recidivism); mientras el "
           "origen siga atacando en el mismo episodio el bloqueo se renueva sin sumar strike y, tras su ultimo DROP, corre el "
           "escalon entero. habilitada: true|false (defecto false = sombra pura). min_drops_origen: entero en [1, 100], DROP "
           "del origen en el episodio antes de bloquearlo (defecto 1; techo PROVISIONAL, se fijara con la medida del E2E). "
           "aviso_castigo_corto_sec: entero en [1, 2147483], todo escalon de recidivism.strike_durations_sec por debajo se "
           "aplica pero se avisa como castigo SOLO DE PRUEBAS (defecto 3600). max_origenes: entero en [1, 10000000], origenes "
           "seguidos a la vez entre todas las victimas; por encima un origen nuevo se bloquea con el escalon vigente sin sumar "
           "strike y se cuenta (defecto 100000). Campo ausente o invalido: defecto con [CONFIG-DEFAULT] y el agente arranca "
           "igual; cada valor valido se registra con [CONFIG].")


def p_json(t):
    m = list(re.finditer(r'(\n([ \t]*))"strike_durations_sec":\s*\[[^\]]*\]', t))
    if len(m) != 1:
        fail("json: strike_durations_sec encontrado %d veces" % len(m))
    nl = m[0].group(1)
    t = (t[:m[0].start()] + nl + '"_doc_strike_durations_sec": ' + json.dumps(DOC_ESC) + "," + nl +
         '"strike_durations_sec": ' + json.dumps(ESCALERA) + t[m[0].end():])
    once(t, '"whitelist": {', "json whitelist")
    w = t.find('"whitelist": {')
    fin = t.find("}", w)
    s = t.find('"set_type": "hash:ip"', w)
    if s < 0 or s > fin:
        fail("json: whitelist sin set_type hash:ip dentro de su objeto")
    ini_linea = t.rfind("\n", 0, s)
    ind = t[ini_linea + 1:s]
    if ind.strip():
        fail("json: indentacion inesperada en whitelist.set_type")
    t = t[:s] + '"_doc_set_type": ' + json.dumps(DOC_TIPO) + ",\n" + ind + '"set_type": "hash:net"' + t[s + len('"set_type": "hash:ip"'):]
    m = list(re.finditer(r'\n([ \t]*)"_comment_transport"', t))
    if len(m) != 1:
        fail("json: _comment_transport encontrado %d veces" % len(m))
    i1 = m[0].group(1)
    i2 = i1 + i1
    bloque = ("\n" + i1 + '"ddos_mitigacion": {\n' + i2 + '"_doc": ' + json.dumps(DOC_MIT) + ",\n" +
              i2 + '"habilitada": false,\n' + i2 + '"min_drops_origen": 1,\n' + i2 + '"aviso_castigo_corto_sec": 3600,\n' +
              i2 + '"max_origenes": 100000\n' + i1 + "},")
    t = t[:m[0].start()] + bloque + t[m[0].start():]
    d = json.loads(t)
    if d["ddos_mitigacion"]["habilitada"] is not False or d["recidivism"]["strike_durations_sec"] != ESCALERA:
        fail("json: validacion de valores")
    if d["ipsets"]["whitelist"]["set_type"] != "hash:net" or d["ipsets"]["blacklist"]["set_type"] != "hash:ip":
        fail("json: validacion de set_type")
    return t


PATCH = {"cfg_hpp": p_cfg_hpp, "cfg_cpp": p_cfg_cpp, "bp_hpp": p_bp_hpp, "main": p_main, "json": p_json}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    txt = {k: p.read_text(encoding="utf-8") for k, p in F.items()}
    hechos = [k for k, t in txt.items() if MARK in t]
    if len(hechos) == len(F):
        print("YA APLICADO (marca presente en todos)")
        return 0
    if hechos:
        fail("marca presente solo en %s: estado mixto" % hechos)
    nuevo = {k: PATCH[k](txt[k]) for k in F}
    if sys.argv[1] == "--check":
        print("CHECK OK: anclas unicas y JSON resultante valido; nada escrito")
        return 0
    for k, p in F.items():
        p.write_text(nuevo[k], encoding="utf-8")
        print("escrito", p)
    print("APPLY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
