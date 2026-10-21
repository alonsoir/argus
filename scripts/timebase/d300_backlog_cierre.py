#!/usr/bin/env python3
"""DAY300: BACKLOG de cierre del dia. Idempotente por marca. --check | --apply."""
import sys

M = "[BACKLOG-CIERRE-D300]"
BACK = "docs/BACKLOG.md"
TEXTO = """
## Cierre DAY300 """ + M + """

### DEBT-FW-PROTECTED-RANGES-001 — SOMBRA HECHA DAY300
E2E (.50 a 60 pps + .61 protegido a 30 pps, misma victima, 180 s): FIN solo .50 (10742 de 10800), 5371
ALERTA_PROTEGIDO intranet, .61 y .51 0 DROP, identidad 16113 = 10742 + 5371 (diferencia 0). Pendiente 2c con el
paso 3b: ipset de whitelist en hash:net (hoy hash:ip y whitelist.json vacio) cargado con los rangos protegidos y
barrera en batch_processor.

### DEBT-HEADS-SWITCH-001 — ABIERTA, rama propia tras el merge (decisiones de Alonso DAY300)
Interruptor por JSON/etcd de cada cabeza (ddos, ransomware, fast-path y las demas), todas o ninguna, con aviso
del estado en el log. Configuracion en etcd (un solo sitio) y activable en RUNTIME. Con todas apagadas: ningun
calculo (tampoco fast-path), ninguna recomendacion del ml-detector y el firewall no actua sobre el ipset aunque
dry_run este apagado. El sniffer sigue capturando y enviando su senal al grafo (solo se apaga la clasificacion de
aRGus). El fast-path es una cabeza propia en el sniffer. Medido DAY300: ransomware se inicializa siempre sin
interruptor; [ML-PHASE] muestra ransomware/traffic/internal calculando por evento; los intervalos de ransomware
(RANSOMWARE_EXTRACTION_INTERVAL_SEC y extraction_interval_seconds_, 30 s fijos) pasan al JSON del bloque de la
cabeza con la constante como respaldo; arreglar a la vez DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001 y el
"Ransomware Detection: DISABLED" falso. Riesgo a medir antes de apagar ransomware: el TimeWindowAggregator de las
features DDoS embebidas es el de la ruta ransomware (grieta B, DAY263).

### Paso 3b — NOTA DE DISENO DAY300
Medido: la sombra de ddos_v2 hace return antes de cualquier bloqueo (zmq_subscriber.cpp, [DDOS-SHADOW-D293]);
hoy no existe el camino ddos_v2 -> ipset. El 3b empieza por el diseno con Alonso.
"""


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d300_backlog_cierre.py --check | --apply")
        return 2
    with open(BACK, encoding="utf-8") as fh:
        t = fh.read()
    if M in t:
        print("ya aplicado: " + M)
        return 1
    if sys.argv[1] == "--check":
        print("OK --check")
        return 0
    with open(BACK, "a", encoding="utf-8") as fh:
        fh.write(TEXTO)
    print("OK --apply: cierre DAY300 anadido a " + BACK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
