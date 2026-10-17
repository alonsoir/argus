#!/usr/bin/env python3
"""DAY300: BACKLOG de [SIGWAIT-D300] + ampliacion de la regla de config + observacion abierta. --check | --apply."""
import sys

M = "[BACKLOG-SIGWAIT-D300]"
BACK = "docs/BACKLOG.md"
TEXTO = """
### DEBT-SNIFFER-MAIN-LOOP-POLL-001 — RESUELTA DAY300 """ + M + """
[SIGWAIT-D300]: SIGINT/SIGTERM/SIGHUP se bloquean con pthread_sigmask en main antes de crear ningun hilo
(mascara heredada) y el hilo principal las espera con sigwait(); sin manejador asincrono, sin sondeo, sin
numero fijo. Medido: 15 de 16 hilos con SigBlk & 0x4003 = 0x4003 y el principal dormido en do_sigtimedwait
(dentro de sigwait el kernel le desbloquea temporalmente las senales esperadas y /proc muestra SigBlk=0 en
ese hilo: es lo correcto; d300_sigblk.sh lo comprueba asi). Paradas 4/4 en 123-231 ms (antes 337-1086 ms).
Hijos: solo dos system("sysctl -w ...") cortos en dual_nic_manager, que heredan la mascara sin efecto.

### DEBT-SNIFFER-CONFIG-SILENT-DEFAULTS-001 — AMPLIACION (decision de Alonso DAY300) """ + M + """
Un valor correcto leido del JSON tambien se registra en el log (campo=valor, fuente JSON), no solo los
defectos: el log de arranque debe recoger la configuracion efectiva completa, campo a campo.

### OBS-DDOS-PRESION-BASE-MINIMA-001 — ABIERTA (medir en el E2E del reinicio) """ + M + """
DAY300, sin trafico de ataque, una victima entro en bajo_presion durante unos 4 min de vida del sniffer
(volcado de parada: "1 bajo presion"); la restauracion la conservo y salio sola en menos de 60 ventanas
(el primer volcado periodico ya la escribio con 0). Hipotesis NO medida: victima con EWMA casi nula (en
el CSV hay bases de 0,33 pps) y K_in=3: una rafaga de 1-2 paquetes cruza el umbral. En sombra solo afecta
a la etapa 1. Medir que victima y con que tasas antes de decidir nada (p. ej. suelo minimo de pps).
"""


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d300_backlog_sigwait.py --check | --apply")
        return 2
    with open(BACK, encoding="utf-8") as fh:
        t = fh.read()
    if M in t:
        print("ya aplicado: " + M + " presente en " + BACK)
        return 1
    if sys.argv[1] == "--check":
        print("OK --check: se anadiran 3 entradas a " + BACK)
        return 0
    with open(BACK, "a", encoding="utf-8") as fh:
        fh.write(TEXTO)
    print("OK --apply: 3 entradas anadidas a " + BACK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
