#!/usr/bin/env python3
"""DAY300 [PROTEGIDOS-D300] tanda 2b: cableado de los rangos protegidos en el firewall-acl-agent.
config (firewall.json -> ConfigLoader -> suscriptor), ALERTA_PROTEGIDO en la sombra antes de add_drop
(el origen protegido no entra en el episodio), linea propia de resumen, aviso periodico si rige el
defecto, guia de operaciones y BACKLOG. --check | --apply desde la raiz del repo. Atomico."""
import os
import sys

M = "[PROTEGIDOS-D300]"
HPP = "firewall-acl-agent/include/firewall/ddos_protegidos.hpp"
CLH = "firewall-acl-agent/include/firewall/config_loader.hpp"
CLC = "firewall-acl-agent/src/core/config_loader.cpp"
ZSH = "firewall-acl-agent/include/firewall/zmq_subscriber.hpp"
ZSC = "firewall-acl-agent/src/api/zmq_subscriber.cpp"
MAIN = "firewall-acl-agent/src/main.cpp"
JSN = "firewall-acl-agent/config/firewall.json"
GUIA = "docs/operaciones/GUIA_OPERACIONES.md"
BACK = "docs/BACKLOG.md"

CLC_NEW = r'''        config.ddos_shadow = d;
    }
    {   // [PROTEGIDOS-D300] DEBT-FW-PROTECTED-RANGES-001: rangos protegidos de la cabeza DDoS
        const Json::Value p = root.isMember("ddos_protegidos") ? root["ddos_protegidos"] : Json::Value(Json::nullValue);
        std::vector<std::string> dmz, intranet, externos;
        if (!p.isObject()) {
            std::cerr << "[CONFIG-DEFAULT] ddos_protegidos ausente o no es un objeto (formato: {\"dmz\": [CIDR, ...], "
                         "\"intranet\": [...], \"externos_criticos\": [...]})" << std::endl;
        } else {
            auto lista = [&p](const char* nombre, std::vector<std::string>& out) {
                if (!p.isMember(nombre)) {
                    std::cerr << "[CONFIG-DEFAULT] ddos_protegidos." << nombre << " ausente: lista vacia" << std::endl;
                    return;
                }
                if (!p[nombre].isArray()) {
                    std::cerr << "[CONFIG-DEFAULT] ddos_protegidos." << nombre
                              << " no es una lista de cadenas CIDR: se ignora" << std::endl;
                    return;
                }
                for (const auto& it : p[nombre]) {
                    if (it.isString()) {
                        out.push_back(it.asString());
                    } else {
                        std::cerr << "[CONFIG-DEFAULT] ddos_protegidos." << nombre
                                  << ": entrada que no es una cadena, descartada" << std::endl;
                    }
                }
            };
            lista("dmz", dmz);
            lista("intranet", intranet);
            lista("externos_criticos", externos);
        }
        std::ostringstream plog;
        config.ddos_protegidos = ::mldefender::firewall::construir_rangos_protegidos(dmz, intranet, externos, plog);
        std::cout << plog.str() << std::flush;
    }
'''

MAIN_NEW = r'''        zmq_config.ddos_shadow = config.ddos_shadow;
        zmq_config.ddos_protegidos = config.ddos_protegidos;  // [PROTEGIDOS-D300]
        {
            std::cout << "[SOMBRA-DDOS] rangos protegidos ("
                      << (config.ddos_protegidos.por_defecto ? "DEFECTO RFC 1918 + fc00::/7" : "JSON") << "):";
            for (const auto& r : config.ddos_protegidos.rangos) {
                std::cout << " " << ::mldefender::firewall::nombre_categoria(r.cat) << "=" << r.texto;
            }
            std::cout << " (DROP de la cabeza DDoS con origen protegido = ALERTA_PROTEGIDO, nunca bloqueo)" << std::endl;
        }
'''

ZSC_DROP_ANCLA = ("        ddos_shadow_.add_drop(nf2.destination_ip(), static_cast<uint32_t>(nf2.protocol_number()), "
                  "ts_s, nf2.source_ip(),\n")
ZSC_DROP_NEW = r'''        {   // [PROTEGIDOS-D300] origen protegido: ALERTA_PROTEGIDO; no entra en el episodio ni se bloquea nunca
            const auto cat = config_.ddos_protegidos.categoria_de(nf2.source_ip());
            if (cat != ::mldefender::firewall::CategoriaProtegida::NINGUNA) {
                ++prot_alertas_[static_cast<std::size_t>(cat)];
                if (prot_detalle_ < static_cast<uint64_t>(config_.ddos_shadow.anomalias_detalle_max)) {
                    ++prot_detalle_;
                    std::cout << "[SOMBRA-DDOS] ALERTA_PROTEGIDO origen=" << nf2.source_ip()
                              << " categoria=" << ::mldefender::firewall::nombre_categoria(cat)
                              << " victima=" << nf2.destination_ip() << " proto=" << nf2.protocol_number()
                              << " ts_s=" << ts_s << " ratio=" << ratio << " p1=" << p1 << " modelo=" << modelo
                              << " evento=" << event.event_id() << " (no se bloquea)" << std::endl;
                }
                return;
            }
        }
''' + ZSC_DROP_ANCLA

ZSC_RES_ANCLA = '                          << " victimas_activas=" << ddos_shadow_.victims() << std::endl;\n'
ZSC_RES_NEW = ZSC_RES_ANCLA + r'''                {   // [PROTEGIDOS-D300] linea propia (no altera [SOMBRA-DDOS] resumen); alertas acumuladas
                    const uint64_t* pa = prot_alertas_;
                    std::cout << "[SOMBRA-DDOS] protegidos: alertas=" << (pa[1] + pa[2] + pa[3]) << " dmz=" << pa[1]
                              << " intranet=" << pa[2] << " externos_criticos=" << pa[3]
                              << " por_defecto=" << (config_.ddos_protegidos.por_defecto ? 1 : 0) << std::endl;
                    if (config_.ddos_protegidos.por_defecto) {
                        std::cerr << "[CONFIG-DEFAULT] ddos_protegidos: rigen los rangos privados por defecto (RFC 1918 + "
                                     "fc00::/7 como intranet); configure los de ESTE despliegue (GUIA_OPERACIONES, "
                                     "seccion DDOS-PROTEGIDOS)" << std::endl;
                    }
                    prot_detalle_ = 0;
                }
'''

JSN_ANCLA = '    "anomalias_detalle_max": 10\n  },\n'
JSN_NEW = JSN_ANCLA + r'''  "ddos_protegidos": {
    "_doc": "[PROTEGIDOS-D300] DEBT-FW-PROTECTED-RANGES-001. Rangos cuyo trafico NUNCA bloquea automaticamente la cabeza DDoS: un DROP cuyo ORIGEN cae aqui se registra como [SOMBRA-DDOS] ALERTA_PROTEGIDO (categoria, victima, evento) y no cuenta para el episodio de la victima. Tres listas de cadenas CIDR, IPv4 o IPv6 con prefijo opcional (/0-32 o /0-128; sin prefijo = un solo host): dmz (servidores publicados), intranet (redes internas), externos_criticos (resolvedores DNS, servidores NTP, operador, socios). Se comprueban en ese orden y gana la primera coincidencia. Una entrada mal formada se descarta con [CONFIG-DEFAULT] y el resto sigue protegiendo. Si NO queda ningun rango valido (bloque ausente, listas vacias o todas las entradas invalidas) se protegen por defecto los rangos privados RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) y fc00::/7 como intranet, avisando con [CONFIG-DEFAULT] en el arranque y en cada resumen: un olvido nunca deja la intranet expuesta a un bloqueo automatico. Cada valor valido se registra con [CONFIG] en el arranque. Guia: docs/operaciones/GUIA_OPERACIONES.md, seccion DDOS-PROTEGIDOS.",
    "_doc_laboratorio": "VALORES DE LABORATORIO, NO DE PRODUCCION. En el lab Vagrant toda la red es privada (192.168.100.0/24) y la VM client simula INTERNET: 192.168.100.50 (atacante) y 192.168.100.51 (origen benigno) NO deben estar protegidos, porque entonces no se podria medir la cabeza DDoS. 192.168.100.61 simula un host INTERNO y se protege para probar ALERTA_PROTEGIDO. En un despliegue real estos valores los calcula o los pide el script de despliegue de cada instalacion (plantillas por instalacion: BACKLOG DEBT-DEPLOY-TEMPLATES-001). Nunca copiar estos valores a produccion.",
    "dmz": [],
    "intranet": ["192.168.100.61/32"],
    "externos_criticos": []
  },
'''

GUIA_TEXTO = r'''

## DDOS-PROTEGIDOS [PROTEGIDOS-D300]

Rangos protegidos de la cabeza DDoS (`firewall.json`, bloque `ddos_protegidos`: `dmz`, `intranet`,
`externos_criticos`). Un DROP de la cabeza DDoS cuyo ORIGEN cae en uno de ellos nunca se convierte en bloqueo
automatico.

| Linea en el log del firewall | Que significa | Que hacer |
|---|---|---|
| `[SOMBRA-DDOS] rangos protegidos (JSON): ...` | Rangos efectivos al arrancar | Comprobar que son los de esta instalacion |
| `[SOMBRA-DDOS] rangos protegidos (DEFECTO RFC 1918 + fc00::/7)` y `[CONFIG-DEFAULT] ddos_protegidos: rigen los rangos privados por defecto` en cada resumen | El JSON no tiene ningun rango valido; se protege todo el espacio privado | Configurar `dmz`, `intranet` y `externos_criticos` reales y reiniciar el firewall-acl-agent. Mientras tanto ningun origen privado se bloquea |
| `[CONFIG-DEFAULT] ddos_protegidos.<lista>: entrada '...' descartada` | Entrada mal formada; el resto sigue protegiendo | Corregir el formato (CIDR IPv4 o IPv6, p. ej. `10.20.0.0/16`) |
| `[SOMBRA-DDOS] ALERTA_PROTEGIDO origen=... categoria=...` | Un host protegido se comporta como origen de un ataque segun la cabeza DDoS. No se bloquea | Investigar ese host con el evento y la victima: comprometido (bot interno, posible movimiento lateral), reflector legitimo mal configurado (DNS/NTP propio o de un proveedor critico) o error del modelo. Si es un externo critico, avisar al proveedor |
| `[SOMBRA-DDOS] protegidos: alertas=N dmz=.. intranet=.. externos_criticos=.. por_defecto=0/1` | Contadores acumulados en cada resumen | Una cifra que crece de forma sostenida merece investigacion aunque no haya bloqueo |

El detalle `ALERTA_PROTEGIDO` se limita a `ddos_shadow.anomalias_detalle_max` lineas por periodo de resumen; el
resto se cuenta en la linea `protegidos:`.
'''

BACK_TEXTO = r'''

### DEBT-DEPLOY-TEMPLATES-001 — ABIERTA (vision de Alonso DAY300) [PROTEGIDOS-D300]
Plantillas de despliegue por instalacion: cada instalacion tendra su propia tarea de despliegue (Jenkinsfile)
escrita a partir de plantillas que aRGus provee (hoy solo existe una muy generica: todo on premise en la misma VM
Vagrant). El script de despliegue debe calcular o pedir al admin los rangos protegidos (dmz, intranet, externos
criticos) en lugar de dejar los valores del laboratorio. Objetivo: plantillas para despliegue distribuido real en
maquinas fisicas, con un motor mas avanzado que Vagrant e imagen segura minima Debian por maquina; por ejemplo,
sniffers en maquinas propias, una maquina mayor con dos o tres ml-detector dando servicio a varios sniffers, el
firewall-acl-agent en la maquina a proteger de la DMZ, y la parte de grafo (Suricata, Zeek, Wazuh, Falco y Kuzu)
en otras maquinas. Requiere hardware de pruebas. Poner especial atencion a los rangos protegidos en las plantillas.

### DEBT-FW-PROTECTED-RANGES-001 — tandas 2a y 2b DAY300 [PROTEGIDOS-D300]
2a (3c273162): ddos_protegidos.hpp y test_ddos_protegidos. Correccion: el test tiene 38 comprobaciones (medido),
no 36 como dice el mensaje del commit. 2b: cableado en config y sombra (ALERTA_PROTEGIDO, el origen protegido no
entra en el episodio), JSON con valores de laboratorio documentados y guia. Pendiente 2c (con el paso 3b): ipset de
whitelist en hash:net cargado con los rangos protegidos y barrera en batch_processor (camino real).
'''

EDITS = [
    (HPP, "#include <ostream>\n", "#include <ostream>\n#include <sstream>  // " + M + "\n"),
    (CLH, '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n',
     '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n'
     '#include "firewall/ddos_protegidos.hpp"  // ' + M + '\n'),
    (CLH, "    DdosShadowParams ddos_shadow;  // [DDOS-SHADOW-D293] política por víctima en sombra\n",
     "    DdosShadowParams ddos_shadow;  // [DDOS-SHADOW-D293] política por víctima en sombra\n"
     "    ::mldefender::firewall::RangosProtegidos ddos_protegidos;  // " + M + " rangos protegidos de la cabeza DDoS\n"),
    (CLC, "        config.ddos_shadow = d;\n    }\n", CLC_NEW),
    (ZSH, '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n',
     '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n'
     '#include "firewall/ddos_protegidos.hpp"  // ' + M + '\n'),
    (ZSH, "        ::mldefender::firewall::DdosShadowParams ddos_shadow;  ///< [DDOS-SHADOW-D293] política por víctima en sombra\n",
     "        ::mldefender::firewall::DdosShadowParams ddos_shadow;  ///< [DDOS-SHADOW-D293] política por víctima en sombra\n"
     "        ::mldefender::firewall::RangosProtegidos ddos_protegidos;  ///< " + M + " rangos protegidos\n"),
    (ZSH, "    bool sombra_primer_drop_ = false;\n",
     "    bool sombra_primer_drop_ = false;\n"
     "    uint64_t prot_alertas_[4] = {};  // " + M + " ALERTA_PROTEGIDO acumuladas por CategoriaProtegida\n"
     "    uint64_t prot_detalle_ = 0;      // " + M + " lineas de detalle del periodo (tope anomalias_detalle_max)\n"),
    (MAIN, "        zmq_config.ddos_shadow = config.ddos_shadow;\n", MAIN_NEW),
    (ZSC, ZSC_DROP_ANCLA, ZSC_DROP_NEW),
    (ZSC, ZSC_RES_ANCLA, ZSC_RES_NEW),
    (JSN, JSN_ANCLA, JSN_NEW),
]
APPENDS = [(GUIA, GUIA_TEXTO), (BACK, BACK_TEXTO)]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d300_patch_protegidos_b.py --check | --apply")
        return 2
    files = sorted({e[0] for e in EDITS} | {a[0] for a in APPENDS})
    text = {}
    errores = []
    for f in files:
        if not os.path.isfile(f):
            errores.append(f + ": no existe")
            continue
        with open(f, encoding="utf-8") as fh:
            text[f] = fh.read()
    if not errores:
        for f in (CLH, CLC, ZSH, ZSC, MAIN, JSN, GUIA):
            if M in text[f]:
                errores.append(f + ": ya contiene " + M + " (ya aplicado)")
        if "sstream" in text[HPP]:
            errores.append(HPP + ": ya incluye <sstream> (ya aplicado)")
    if errores:
        print("\n".join(errores))
        return 1
    for i, (f, old, new) in enumerate(EDITS, 1):
        n = text[f].count(old)
        if n != 1:
            errores.append("edicion %d en %s: el ancla aparece %d veces (se esperaba 1)" % (i, f, n))
            continue
        text[f] = text[f].replace(old, new, 1)
    if errores:
        print("\n".join(errores))
        print("NADA aplicado")
        return 1
    for f, t in APPENDS:
        text[f] = text[f] + t
    if sys.argv[1] == "--check":
        print("OK --check: %d ediciones y %d anexos en %d ficheros, todas las anclas unicas"
              % (len(EDITS), len(APPENDS), len(files)))
        return 0
    tmps = []
    for f in files:
        tmp = f + ".tmp_d300"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text[f])
        os.chmod(tmp, os.stat(f).st_mode)
        tmps.append((tmp, f))
    for tmp, f in tmps:
        os.replace(tmp, f)
    print("OK --apply: %d ediciones y %d anexos en %d ficheros con marca %s" % (len(EDITS), len(APPENDS), len(files), M))
    return 0


if __name__ == "__main__":
    sys.exit(main())
