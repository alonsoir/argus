#!/usr/bin/env python3
# DAY305 — BACKLOG: cabecera, cierre de DEBT-HEADS-SWITCH-001 y DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001 (titulos) y
# seccion "Cierre DAY305" al final. Comprueba la cabecera, los dos titulos y la ultima linea EXACTOS y respeta el
# salto final (leccion DAY303). Valida todo antes de escribir.
# Uso, raiz del repo:  python3 d305_backlog.py --check | --apply
import sys

P = "docs/BACKLOG.md"
MARK = "[BACKLOG-CIERRE-D305]"
HEAD_OLD = "*Última actualización: DAY 304 — 2026-10-22*"
HEAD_NEW = "*Última actualización: DAY 305 — 2026-10-23*"
T1_OLD = "### DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001 — ABIERTA (va con el interruptor de cabezas) [BACKLOG-PARADA-D300]"
T1_NEW = ("### DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001 — CERRADA DAY305 (feat/heads-switch, 01bcadb8, "
          "[HEADS-SNIFFER-D305]) [BACKLOG-PARADA-D300]")
T2_OLD = "### DEBT-HEADS-SWITCH-001 — ABIERTA, rama propia tras el merge (decisiones de Alonso DAY300)"
T2_NEW = "### DEBT-HEADS-SWITCH-001 — CERRADA DAY305 (feat/heads-switch; ver seccion Cierre DAY305)"
LAST = "target que fallo contra la VM viva (un minuto en vez de dos horas)."

SECCION = f"""
## Cierre DAY305 {MARK}

Rama `feat/heads-switch`. Documento: docs/ml-heads/day305_interruptor_cabezas.md.

### DEBT-HEADS-SWITCH-001 — CERRADA DAY305
Modelo decidido por Alonso: el sniffer recoge rasgos SIEMPRE y su unica cabeza es el fast-path
(fast_detector.enabled: alerta por paquete y ventanas de ransomware). La inferencia de las cabezas vive solo en el
ml-detector, con un enabled por cabeza. Regla de enabled en todos los componentes: booleano o texto true/false sin
distinguir mayusculas; ausente o invalido -> APAGADA con [CONFIG-DEFAULT]. Linea [HEADS] con el estado EFECTIVO al
arrancar y cada monitoring.heads_log_interval_seconds (10-3600, def 60) en ml-detector y sniffer. level1 apagada ya
no mata el ml-detector. Laboratorio: solo ddos_v2 encendida, fast-path apagado. Retirada la inferencia duplicada
del sniffer (run_ml_detection, ~20 us por evento). Pruebas: test_heads_config (71 comprobaciones por componente).
Regresion: lab-e2e-protegidos PASA 5/5 (FIN 10770 de .50, alertas 5384 de .61, identidad exacta, 0 del inocente).
El cambio EN CALIENTE queda en DEBT-ETCD-REMOTE-ADMIN-001.

### DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001 — CERRADA DAY305
El procesador de ransomware se para y libera DESPUES de unir los hilos que lo usan; antes se emite la ventana
pendiente (si el fast-path esta encendido) y se vacia la cola de envio. ransomware_enabled_ ya no se toca al parar:
las estadisticas finales ya no dicen "DISABLED" en falso. Medido en vivo: parada limpia.

### DEBT-ETCD-REMOTE-ADMIN-001 — ABIERTA (diseno; decision de Alonso DAY305)
Administracion remota de una instalacion a traves de su etcd-server: un admin autorizado (interfaz futura, junto a la
del grafo) pide un cambio; el etcd-server, que conoce todos los componentes y su JSON, modifica esa parte y avisa al
componente. El JSON de cada componente da los defectos; manda el mensaje del etcd-server. Un proceso superior podria
hablar con varias instalaciones. Primer caso de uso: encender/apagar cabezas en caliente. Apagar cabezas es una
accion de seguridad critica: mensaje firmado, registrado en el receptor y visible en [HEADS].
Segundo caso de uso, SI LA MEDIDA LO JUSTIFICA: recogida selectiva de rasgos en el sniffer (solo los de las cabezas
activas en sus ml-detector, union si son varios). Puede ser una gran mejora o infima: medir antes el coste de
populate por evento y el tamano del protobuf (hoy los campos sin recoger viajan igual: centinela NaN, DAY77).
Nunca como interruptores sueltos en el JSON del sniffer (fuente de verdad duplicada).
Medido DAY305: etcd-server es propio (httplib: /register, /unregister, /components, /seed, /validate, /health,
/info, /secrets/keys; config bajo /config/<componente>), sin watch; los componentes no releen su config tras
registrarse. Requisito previo: etcd-server distribuido, con protocolo de consenso y eleccion de lider.

### DEBT-DDOS-V1-RETIRE-001 — ABIERTA, rama siguiente (decision de Alonso DAY305)
Retirar la cabeza DDoS v1 entera para que no interfiera con ddos_v2: DDoSDetector, ddos_trees_inline.hpp, bloque
ml.level2.ddos del JSON (aun declara 10 rasgos con geo), su paso en zmq_handler, el test_detectors que la compila y
sus rasgos v1 en el recolector del sniffer (packet_symmetry, source_ip_dispersion, protocol_anomaly,
amplification, geo, escalation, saturation). En el protobuf los campos quedan marcados obsoletos, sin reutilizar.
La historia de git la conserva.

### DEBT-FW-MITIGACION-ATADA-A-SOMBRA-001 — ABIERTA
La mitigacion real de ddos_v2 en el firewall solo se ejecuta con ddos_shadow.enabled: apagar la sombra apaga la
mitigacion (zmq_subscriber.cpp, return antes del bloque [DDOS-MITIGACION-B2-D302]). Separar las dos llaves.

### DEBT-SNIFFER-RANSOMWARE-PARAMS-001 — ABIERTA
Numeros fijos en RansomwareFeatureProcessor::initialize: FlowTracker(100000, 300), DNSAnalyzer(1000),
IPWhitelist(10000, 24 h), max_events 10000 (agregador y extractor) y cleanup_old_events(600 s). Al JSON con _doc,
rango y defecto validado.

### DEBT-SNIFFER-STOP-PROCESSING-QUEUE-001 — ABIERTA
Al parar, flush_current_batch() mete el lote pendiente en processing_queue_, pero los hilos de rasgos ya estan
saliendo: esos eventos de flujo no se procesan ni se envian. La cola de ENVIO si se vacia desde DAY305.

### DEBT-REPO-RESIDUOS-001 — ampliada DAY305
etcd-server/src/{{component_registry.cpp.backup, etcd_server.cpp.backup, etcd_server.cpp.backup.day62,
main.cpp.backup}}, sniffer/src/userspace/ml_defender_features.cpp.bak.day79, sniffer/include/payload_analyzer.hpp.v1.0,
ml-detector/tests/CMakeLists.txt.backup, ml-detector/tests/unit/test_detectors.cpp.backup,
scripts/timebase/__pycache__/ (sin trackear; anadir a .gitignore).

### Leccion DAY305
Antes de poner un interruptor, medir QUE hace de verdad lo que se va a apagar: el sniffer ejecutaba cabezas que
nadie sabia que corrian alli (y tiraba el resultado). Y un interruptor que solo cambia un mensaje es peor que no
tenerlo: fast_detector.enabled y "Ransomware Detection: DISABLED" decian algo que el codigo no hacia.
"""

def die(m):
    print("ABORTA (no se ha escrito nada): " + m)
    sys.exit(1)

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        die("uso: python3 d305_backlog.py --check | --apply")
    t = open(P, encoding="utf-8").read()
    if MARK in t:
        die("el BACKLOG ya contiene la seccion de cierre DAY305")
    if not t.endswith("\n"):
        die("el BACKLOG no termina en salto de linea")
    L = t[:-1].split("\n")
    if L[1] != HEAD_OLD:
        die(f"linea 2 = {L[1]!r}")
    if L[-1] != LAST:
        die(f"ultima linea = {L[-1]!r}")
    for old in (T1_OLD, T2_OLD):
        if L.count(old) != 1:
            die(f"titulo no encontrado exactamente una vez: {old}")
    L[1] = HEAD_NEW
    L[L.index(T1_OLD)] = T1_NEW
    L[L.index(T2_OLD)] = T2_NEW
    n = "\n".join(L) + "\n" + SECCION
    if not n.endswith("\n") or n.count(MARK) != 1:
        die("resultado inesperado")
    print(f"OK: cabecera DAY 305, 2 titulos cerrados, seccion de cierre +{SECCION.count(chr(10))} lineas")
    if sys.argv[1] == "--check":
        print("--check: no se ha escrito nada")
        return
    open(P, "w", encoding="utf-8").write(n)
    print("--apply: escrito")

if __name__ == "__main__":
    main()
