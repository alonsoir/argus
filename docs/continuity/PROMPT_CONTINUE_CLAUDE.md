# CONTINUIDAD DAY272 — B MEDIDO. Con la compuerta level1 forzada (`FORCE_ALL_HEADS=1`), la cabeza DDoS clasifica ~21% del flood real como DDOS (988/4661), con `ddos_prob` hasta 0.44 en los NORMAL. La cabeza NO es ciega al flujo aislado. El discriminador es `packet_size_entropy` (por-flujo, VARÍA); `source_ip_dispersion` está CLAVADA en 0.100 (agregación no discrimina aquí). Resultado de arquitectura firme: el veto de level1 mataba recall real → paralelo-fusión justificado por el dato, no por teoría.

## EL VEREDICTO DE B (medido, no re-litigar)
Flood CICDDoS2019 (`_0125_50k_lab.pcap`, 50k pkts, `--pps=100`) por el pipeline íntegro con
`make pipeline-start VERBOSE=1 FORCE_ALL_HEADS=1`. Reparto del veredicto de `DDoSDetector::predict`:
```
3673 DDoS: class=0 (NORMAL)
 988 DDoS: class=1 (DDOS)      → ~21% recall a nivel de veredicto
```
Primer flujo NORMAL: `conf=0.5617, ddos_prob=0.4383` (P(ddos) alta, pegada al umbral, NO ≈0).

### Quién ganó la apuesta (medir, no votar)
- **Claude: DOBLE DERROTA.** Predijo `class=0` en todos con `ddos_prob≈0` → falso (21% DDOS). Y su
  mecanismo (agregación vía `source_ip_dispersion`) → muerto: disp CLAVADA.
- **Alonso: acierta.** La cabeza discrimina sobre el flujo aislado, sin necesidad de la ventana.

### El mecanismo, MEDIDO (cierra la duda de DAY271)
`grep -oE 'disp=[-0-9.]+' | uniq -c` → **13258 × disp=0.100** (un único valor). El aggregator de
ransomware está VIVO (no es -9999, confound de ventana-muerta DESCARTADO), pero el cap de 10000 muerde
bajo flood → `event_count` saturado → la fórmula log se vuelve constante. **`source_ip_dispersion` no
aporta señal aquí.**
`grep -oE 'syn_ack=..., entropy=..., amp=...' | uniq -c` → syn_ack y amp CLAVADOS en 0.000, pero
**`entropy` VARÍA** (0.019, 0.055, 0.127…). → el discriminador del 21/79 es **`packet_size_entropy`,
feature POR-FLUJO**. La cabeza dispara por contenido de flujo, no por agregación.

## RESULTADO DE ARQUITECTURA — FIRME, independiente del feature que dispare
Compuerta cerrada (DAY270, veto de level1): recall DDoS ≈ 0%. Compuerta forzada (DAY271): ~21%.
**El veto de level1 mataba detecciones que la cabeza SÍ sabía hacer.** → el fork de DAY269 se cierra:
**paralelo-fusión NECESARIO, justificado por dato medido.** level1 pasa a cabeza que puntúa, sin poder
de veto; fórmula de fusión posterior. Política de respuesta graduada/reversible de DAY269 sigue en pie.
Ver [[reparacion-cabeza-ddos]].

## LO QUE HA QUEDADO CABLEADO (compilado, verde, en rama `docs/ml-heads-grieta-b`)
- Flag debug `--force-all-heads` (CLI → `ZMQHandler::set_force_all_heads` → miembro `force_all_heads_=false`),
  propagado por Makefile (`FORCE_ALL_HEADS=1`), patrón VERBOSE. Un `pipeline-start` normal NUNCA abre la compuerta.
- Compuerta como predicado puro `l2_gate_open(force, label, conf, thr)` en `ml-detector/include/l2_gate.hpp`
  (SIN dependencias). `zmq_handler.cpp` guard 549 lo llama. Test `test_l2_gate` (7/7, ctest #13) — regresión
  del camino no-forzado cubierta.
- Instrumentación: `disp={:.3f}` (source_ip_dispersion, idx 2) en el log de features; `ddos_prob={:.4f}`
  en el log del veredicto (P(ddos), lo que `conf`=P(clase ganadora) NO da en un NORMAL).
- `make ml-detector` verde con `-Werror`; `make test-components` 82/82 + test_l2_gate.
- Patcher reproducible: `patch_force_all_heads.py` (idempotente, atómico, --dry/--apply/--check).

## PENDIENTE DAY272 (en orden)
1. **Confirmar el discriminador con más features.** Loguear también las 5 sin loguear (packet_symmetry,
   protocol_anomaly_score, flow_completion_rate, traffic_escalation_rate, resource_saturation_score) y ver
   cuáles varían. Sospecha: entropy manda; las de ventana (escalation/saturation) probablemente clavadas
   como disp. Cierra "¿qué separa el 21/79" del todo.
2. **Recall LIMPIO por 5-tupla.** Los 4661 incluyen ambiente + re-extracción (13258 líneas features ≈ 3×
   veredictos). Filtrar por la 5-tupla del flood (src 192.168.100.50 → dst 192.168.100.1) para un recall
   sólido, no solo orden de magnitud.
3. **Arrancar el diseño paralelo-fusión** (ya NECESARIO, no opcional): level1 como cabeza sin veto + fórmula
   de fusión + pesos por cabeza (parámetro crítico nuevo, ver DAY269). Coste conocido: expone el FPR de cada
   cabeza sobre TODO el volumen (fp_benign_cic=0.0878 deja de estar amortiguado por la compuerta).
4. **Backlog agregación (NO muerto, aparcado):** la cabeza recupera 21%, no 100% — se le escapan 4/5. Si la
   vía DDoS necesita también unidad AGREGADA por víctima es pregunta abierta, pero exige el pcap **multi-origen**
   (el `_lab.pcap` colapsa origen a 1 → disp inútil). Otro experimento.

## MÉTODO DE REPLAY (reusar, ver [[reparacion-cabeza-ddos]] DAY270)
`_0125_50k_lab.pcap` a `--pps=100` (a 1000pps el ring pierde ~86%). MACs reescritas CAMBIAN en destroy→up →
rehacer `tcprewrite` si hubo destroy→up. Truncar log con `truncate -s 0` (pipeline vivo), NUNCA logs-lab-clean.
Vocabulario real del log: `DDoS: class=[01] (NORMAL|DDOS)`, `ddos_prob=`, `disp=` (una línea arriba, en features).

## INVARIANTES
`main` protegida (PR only). Rama = `docs/ml-heads-grieta-b`. Flags por Makefile, NUNCA JSON a mano
(muere en destroy→up). `git grep`/fichero concreto, NUNCA `grep -rn` desde raíz. No encadenar salidas
grandes. El compilador es el árbitro. HECHO ≠ SOSPECHADO.

## BACKLOG (anotar, NO perseguir)
- Config `ml_detector_config.json`: `"features_count": 10` mientras el código sirve **9** (post-skew DAY255).
  Metadato muerto (el runtime hardcodea `!= 9`), pero inconsistencia de honestidad para paper/README.
- El `disp=0.100` constante bajo flood es hallazgo de paper por sí mismo: la única feature agregada de la
  cabeza degenera exactamente cuando más falta hace (cap de 10000 muerde). Refuerza construir sobre features
  reales (Fase 2, CICDDoS2019 + labels) en vez del contrato sintético-9.
- Recall del throughput: ring consumer pierde a >100pps; el consumer, no el modelo, acota la detección.