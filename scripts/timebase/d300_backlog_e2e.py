#!/usr/bin/env python3
"""DAY300: BACKLOG del E2E del reinicio. Idempotente por marca. --check | --apply."""
import sys

M = "[BACKLOG-E2E-REINICIO-D300]"
BACK = "docs/BACKLOG.md"
TEXTO = """
### DEBT-DDOS-STATE-PERSIST-001 — E2E HECHO DAY300 """ + M + """
Reinicio del sniffer a mitad de un ataque de 60 pps (bajo abs_pps): sin estado, 0 marcados tras el rearranque
(razon 0,000, DROP/cable 0,416); con parada ordenada, razon 1,305 y DROP/cable 0,924; con kill -9 (volcado
periodico de hace 34 s), razon 1,236 y 0,920. Un solo episodio de sombra cuando hay estado. Inocente .51: 0 DROP.
Detalle: docs/ml-heads/day300_reinicio_e2e.md. Scripts: d300_reinicio_e2e.sh / _client.sh / _analisis.sh.

### DEBT-SNIFFER-ZMQ-DROP-ARRANQUE-001 — ABIERTA """ + M + """
En los primeros 10 s tras cada rearranque del sniffer con trafico aparece [ZMQ-DROP] (15 y 4 eventos medidos
DAY300). Medir la causa (conexion al ml-detector, HWM, cola) antes de decidir.

### DEBT-SNIFFER-LOG-INTERLEAVE-001 — ABIERTA """ + M + """
Varios hilos escriben en std::cout sin exclusion y las lineas se mezclan (DAY300: "[ZMQ-DROP] descartados="
seguido de "[ML-PHASE] ..." en la misma linea). Rompe los grep de diagnostico. Escribir cada linea completa
de una vez (buffer local + una sola escritura, o logger con cerrojo).

### OBS-FW-SOMBRA-DROP-FUERA-EPISODIO-001 — ABIERTA """ + M + """
antes2 (DAY300): los resumenes [SOMBRA-DDOS] suman 8980 DROP y el FIN cuenta 8976; los 4 de la diferencia son
de ts=17472 (el "primer DROP", ratio 3,3), anteriores al inicio del episodio (17473). Hipotesis NO verificada:
la ventana tuvo menos de m=5 DROP, no fue positiva y el FIN no la incluye. Comprobar en DdosShadowPolicy.
"""


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d300_backlog_e2e.py --check | --apply")
        return 2
    with open(BACK, encoding="utf-8") as fh:
        t = fh.read()
    if M in t:
        print("ya aplicado: " + M + " presente en " + BACK)
        return 1
    if sys.argv[1] == "--check":
        print("OK --check: se anadiran 4 entradas a " + BACK)
        return 0
    with open(BACK, "a", encoding="utf-8") as fh:
        fh.write(TEXTO)
    print("OK --apply: 4 entradas anadidas a " + BACK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
