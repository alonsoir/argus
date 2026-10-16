#!/usr/bin/env python3
"""DAY299 cierre: entradas de BACKLOG de la tarde (parada colgada, tests del ipset sin root en el gate, E2E
pendientes). Anexo idempotente. --check | --apply desde la raiz."""
import os
import sys

P = "docs/BACKLOG.md"
M = "[D299-CIERRE]"
TXT = """
### DEBT-SNIFFER-SHUTDOWN-HANG-001 — ABIERTA (P1) """ + M + """
Con sniffer-stop (SIGTERM), el sniffer ejecuta su limpieza ([Cleanup], parada del lector y volcado de
parada medidos), pero NO termina en 15 s y acaba en SIGKILL (2 de 2 paradas, DAY299). Se cuelga en algún
paso posterior al lector: anillo, thread manager, ZMQ (linger) o loader eBPF. Medir qué paso es la última
línea del log antes del SIGKILL. Además, el aviso de sniffer-stop dice «sin volcado de parada», y es falso
cuando el volcado ya se hizo: corregir el texto (p. ej. «parada incompleta»). Y medir por qué la
restauración dice «volcado de hace 60 s» cuando el rearranque fue inmediato.

### DEBT-FW-IPSET-TESTS-SIN-ROOT-001 — ABIERTA (P1) """ + M + """
Los 21 IPSetWrapperTest, test_recidivism_e2e y los dos *_injection_integration hacen GTEST_SKIP sin root:
en test-components se saltan siempre. make test-firewall-e2e existe (Makefile:3058), pero ni test-all ni
EMECAS lo llaman. El camino real del ipset no lo valida ningún gate. Va con el punto 3b de la rama.

### PENDIENTE de la rama (punto 3b): drop temporal real de punta a punta """ + M + """
Decisión de Alonso DAY299: un test E2E con dry_run apagado solo durante el test, donde una IP entra en el
ipset con un drop temporal calculado y sale al vencer (basta probar el mecanismo). Antes de diseñar,
medir: (1) soporte de ipset en el kernel del defender (ver [FW-DRYRUN-VERIF-D294]); (2) qué camino toma
un DROP de ddos_v2 con dry_run=false (la sombra decide por víctima; el ipset guarda orígenes con el
timeout de RECIDIVISM-D276); (3) conmutador del JSON del firewall que se restaure siempre.

### Nota DAY299 — calibración de los valores por defecto """ + M + """
Decisión de Alonso: los defectos de la persistencia, el plazo de arranque y abs_pps son seguros, no
óptimos. Más adelante se diseñarán experimentos para hallar los óptimos de cada instalación (dependen de su
topología); los lanzarán los administradores, y aRGus dará el método y una guía.
"""


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    t = open(P, encoding="utf-8").read()
    if M in t:
        print("[YA-APLICADO]")
        return 0
    if sys.argv[1] == "--check":
        print("[CHECK-OK] 1 anexo pendiente")
        return 0
    tmp = P + ".d299tmp"
    open(tmp, "w", encoding="utf-8").write(t.rstrip("\n") + "\n" + TXT)
    os.replace(tmp, P)
    print(f"[APLICADO] {M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
