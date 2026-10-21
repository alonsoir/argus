#!/usr/bin/env python3
# DAY298: cierre de la jornada en el BACKLOG. Solo anade una seccion al final; aborta si ya esta.
# Uso, desde la raiz del repo: --check | --apply
import os, sys

F = "docs/BACKLOG.md"
MARCA = "## DAY298 — etapa 1 con histéresis"
SECCION = """

## DAY298 — etapa 1 con histéresis (rama fix/ddos-etapa1-histeresis; medidos antes y después)

**Resueltas en la rama (pendiente de merge):**
- DEBT-DDOS-V2-LONG-ATTACK-001 — RESUELTA (pasos 2+3). Antes: la EWMA aprendía con alfa lento dentro de
  bajo_presion y la etapa 1 (ratio crudo) dejaba de pasar a t = tau·ln(3(r−1)/(2r)); A5 en vivo 888,6 s
  (885,7 predichos con r medido 6,786), 84,3 % marcado. Después: EWMA congelada en presión; A5 en vivo
  sin corte, FIN a fin_ataque + 30 s, 62978/63000 = 99,97 % marcado; .51 legítimo 0 DROP (10510 pases de la
  etapa 1 rechazados por el RF). Offline: test_ddos_victim_board 13a (2 h sostenido, ratio mín 7,0).
- DEBT-DDOS-COLDSTART-ETAPA1-001 — RESUELTA salvo persistencia (paso 4). La etapa 1 consume
  DDoSFeatures.victim_state (proto campo 16): FRIO nunca pasa (frío benigno 50 pps: 200 pases antes → 0);
  clave fría con pps >= ddos_victim_ewma_abs_pps (defecto 200, seguro no óptimo) entra en presión desde la
  primera ventana (frío 300 pps: 13373 pases = 13373 marcados). Precio documentado: frío 60 pps se aprende
  como base (antes 1,2 % marcado, después 0). El pico de 140 pps de DAY297 fue tráfico real puntual (Wazuh),
  no artefacto: la primera ventana del agregador se descarta (window_ms = 0).

**Nuevas o pendientes de la misma rama (siguiente sesión, DAY299):**
- DEBT-DDOS-ESTADO-ARRANQUE-001: los eventos sellados en la ventana de arranque del lector salen sin
  victim_state (≈ 1 s de tráfico por arranque: 53 / 66 / 298 / 2 medidos). Decisión de Alonso (b): sellar
  FRIO en esa ventana y renombrar el aviso para que diga sin ambigüedad que es una anomalía de la cabeza
  DDoS (propuesta: [DDOS-V2-ANOMALIA] estado_victima_ausente). Test incluido.
- DEBT-DDOS-STATE-PERSIST-001 (paso 4): volcar el estado por víctima (ewma, seen, bajo_presion, instante)
  cada snapshot_s y en la parada si llega; restaurar al arrancar con caducidad; fallo de lectura o
  escritura = aviso y arranca igual. Sin esto, tras un reinicio todas las víctimas vuelven a frío.
- DEBT-DDOS-STATE-HMAC-001: integridad del fichero de estado (un fichero manipulado podría precargar una
  base alta y cegar la detección). Depende de la provisión de claves HMAC.
- DEBT-FW-PROTECTED-RANGES-001 (paso 5): DMZ, intranet y externos críticos en el JSON del firewall; DROP de
  la cabeza DDoS sobre un origen protegido = ALERTA_PROTEGIDO, nunca bloqueo automático.
- DEBT-DDOS-AUTO-EXIT-001: salida automática de presión si en N horas el RF no da ningún positivo para la
  víctima (requiere realimentación ml-detector → sniffer; N en el JSON). Abierta, rama de medidas y modelo.
- DEBT-DATASET-WRITER-VICTIM-STATE-001: el volcado del dataset del ml-detector no lleva victim_state ni el
  resultado de la etapa 1; hoy se miden con el resumen [DDOS-V2] del ml-detector.
- Tests de la PR: integración sniffer → proto → ml-detector en test-components; objetivo make del E2E del
  laboratorio con criterios PASA/FALLA automáticos; EMECAS+++ desde cero (recompila tools/build-production,
  que conserva el proto anterior).

**Cifras nuevas para deudas existentes:**
- DEBT-TIMEBASE-SEQ-DELIVERY-ORDER-001: seq_desorden crece con el ritmo: 0,03 % de los eventos a 60 pps,
  5,1 % (1417/27785) a 300 pps (frio_atq300_despues). seq_ventana ya es configurable en el JSON del firewall.
- DEBT-SNIFFER-FLOW-EXPIRY-001 + DEBT-SNIFFER-FLOWTABLE-CONFIG-001: confirmado DAY298 que cleanup_expired_flows
  no se llama nunca (A5 en vivo exigió pcaps sin 5-tuplas repetidas, gen_disjunto.py). Rama propia
  inmediatamente después del merge de esta (decisión de Alonso DAY298), antes de la vía rápida XDP.
- Observación del laboratorio: el sniffer arranca ~145 s después del inicio de pipeline-start; la primera
  fila del dataset llega a +140 s.
"""

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_backlog.py --check | --apply")
    txt = open(F).read()
    if MARCA in txt:
        sys.exit(f"NO APLICABLE: {F} ya contiene la seccion DAY298")
    if sys.argv[1] == "--check":
        print("CHECK OK: se anadira la seccion DAY298 al final del BACKLOG")
        return
    with open(F + ".tmp", "w") as o:
        o.write(txt.rstrip("\n") + SECCION)
    os.replace(F + ".tmp", F)
    print("APLICADO: seccion DAY298 en el BACKLOG")

main()
