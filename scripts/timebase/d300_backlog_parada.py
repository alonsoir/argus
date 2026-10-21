#!/usr/bin/env python3
"""DAY300: entradas de BACKLOG del paso 0 (parada del sniffer). Idempotente por marca. --check | --apply."""
import sys

M = "[BACKLOG-PARADA-D300]"
BACK = "docs/BACKLOG.md"
TEXTO = """
### DEBT-SNIFFER-SHUTDOWN-HANG-001 — RESUELTA DAY300 """ + M + """
Causa medida: cuatro hilos dormian con sleep_for(30 s) no interrumpible y su parada hacia join():
estadisticas y procesador ransomware (ring_consumer), extraccion ransomware (RansomwareFeatureProcessor) y
heartbeat (etcd-client, este retenia el final de main). La parada tardaba 0-30 s y sniffer-stop (15 s)
acababa en SIGKILL (2/2 en DAY299). Arreglo [PARADA-INMEDIATA-D300]: condition_variable::wait_for con
predicado y notify_all tras poner la bandera (sin despertar perdido); intervalos sin cambios. Medido DAY300:
3/3 paradas ordenadas (337, 1086, 448 ms), con [Cleanup], volcado de parada, All components stopped,
Heartbeat thread stopped y Sniffer stopped correctly. Edad de restauracion exacta: -0,64 s frente a
volcado_wall_ns del CSV y el arranque del proceso; el "volcado de hace 60 s" de DAY299 era el hueco real.
Criterio aceptado: parada ordenada, sin SIGKILL, < 2 s. stats_interval_seconds validado con
[CONFIG-DEFAULT]; aviso de sniffer-stop corregido (el volcado pudo hacerse antes del SIGKILL).

### DEBT-SNIFFER-MAIN-LOOP-POLL-001 — ABIERTA """ + M + """
El bucle principal (main.cpp, while g_running) sondea con sleep_for(1 s) fijo: la parada ve la senal con
hasta 1 s de retraso (explica la dispersion 337-1086 ms). Arreglo propuesto: esperar la senal en lugar de
sondear (sigwait/signalfd), que elimina el numero fijo en vez de llevarlo al JSON.

### DEBT-SNIFFER-CONFIG-SILENT-DEFAULTS-001 — ABIERTA """ + M + """
config_manager.cpp lee muchos campos con get(campo, defecto) sin aviso (p. ej.
zmq.queue_management.queue_timeout_ms, processing.user_processing.queue_timeout_seconds,
monitoring.performance_tracking). Incumple la regla del JSON (defecto validado + [CONFIG-DEFAULT] con
campo, formato y limites). Migrar campo a campo al patron de timebase/kernel_space.

### DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001 — ABIERTA (va con el interruptor de cabezas) """ + M + """
RingBufferConsumer::stop() libera ransomware_processor_ (shutdown_ransomware_detection) ANTES de
shutdown_consumers(): un consumidor aun vivo puede usar el procesador liberado. Ademas las estadisticas
finales dicen "Ransomware Detection: DISABLED" porque shutdown pone ransomware_enabled_=false antes de
print_stats (falso: estuvo activo toda la corrida). Ransomware se inicializa siempre, sin interruptor JSON.

### DEBT-ETCD-CLIENT-DEAD-VARIANTS-001 — ABIERTA (higiene) """ + M + """
etcd-client/src/etcd_client_base.cpp y etcd_client_manual.cpp estan trackeados pero no se compilan
(CMakeLists solo usa etcd_client.cpp) y conservan el sleep_for del heartbeat; tambien
etcd-client/include/etcd_client/etcd_client.hpp.day54_hmac_only. Borrar o documentar.

### DEBT-LAB-GDB-PROVISION-001 — ABIERTA """ + M + """
gdb no esta en el aprovisionamiento del defender (instalado a mano DAY300 para el volcado de pilas de
d300_parada.sh). Anadir al Vagrantfile si se quiere tener siempre a mano para diagnostico.
"""


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d300_backlog_parada.py --check | --apply")
        return 2
    with open(BACK, encoding="utf-8") as fh:
        t = fh.read()
    if M in t:
        print("ya aplicado: " + M + " presente en " + BACK)
        return 1
    if sys.argv[1] == "--check":
        print("OK --check: se anadiran 6 entradas a " + BACK)
        return 0
    with open(BACK, "a", encoding="utf-8") as fh:
        fh.write(TEXTO)
    print("OK --apply: 6 entradas anadidas a " + BACK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
