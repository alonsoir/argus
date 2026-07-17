# PROMPT DE CONTINUIDAD — DAY 221 (17-jul-2026)

Rama: `fix/verdict-multihead-honest`. HEAD al cierre: `3f9be4bf` (+ apendice
y report pendientes de commit si no se hicieron a las 03:00).
FEDER: go/no-go ~1 agosto. Calidad no negociable sobre deadline.

## EL RESULTADO DE LA NOCHE (via A ejecutada — COMPLETA)

El replay Neris corrio entero y limpio: 323.152/323.154 pkts (Failed: 2,
despreciable), 17.298s a timing original. Bronce del run: 765 segmentos,
519.397 eventos, 286.420 con IPs CTU.

| metrica | valor |
|---|---|
| GT (cids botnet unicos, derivado y commiteado) | 8.935 |
| coverage | **0.886** (7.916 cubiertos; 1.019 perdidos rio-arriba) |
| **recall** | **0.0** (detected: 0 de 8.935) |
| recall_over_covered | 0.0 |
| max(ml_score) de TODO el run | 0.626477 (threshold: 0.65) |
| scores unicos | 11.261 (top-12 formas ~76% de eventos) |
| eventos >=0.6 / >=0.5 / >=0.4 | 47 / 756 / 62.763 (de 519.397) |

Report: `tools/eval/out/eval_level1_neris_report.json`.

## EL HALLAZGO — DEBT-L1-PARTIAL-FLOW-SCORING-001 (P0)

**El pipeline puntua POR EVENTO con features de flujo PARCIAL; el modelo se
entreno con agregados de flujo COMPLETO** (CICFlowMeter sobre flujos
terminados). Resultado: distribucion de scores desplazada con techo empirico
0.626 < 0.65 → recall 0.0 pese a coverage 0.886.

Tenaza probatoria (cada eslabon exonerado por medida, no por opinion):
- **El modelo NO es el problema**: via B (mismas 23 features, flujo completo)
  → recall 0.9987. Commiteada en `73fac317`.
- **La captura NO es el problema**: coverage 0.886.
- **El threshold NO es el fix**: techo 0.626; bajar a 0.5 rescataria <=756
  eventos de 519K → recall seguiria ~0 y abriria FPs. Puerta clavada con
  numero — NO reabrir sin evidencia nueva.
- **Hay señal comprimida**: 12% de eventos en la banda 0.4-0.626. El modelo
  parcial esta desalineado, no ciego — relevante para elegir fix.

## LA CONVERSACION DE DAY 221 (la importante — con cafe, no improvisar)

Que significa "puntuar un flujo" en un NDR de tiempo real. Opciones sobre la
mesa (probablemente combinables; candidata a ronda del Consejo 8/8):
1. **Puntuar al cierre/timeout del flujo** (features completas, deteccion
   tardia — ¿aceptable para botnet C&C? ¿inaceptable para ransomware?).
2. **Re-puntuar por ventanas/hitos** (N paquetes, T segundos): deteccion
   progresiva, features "tan completas como sea posible hasta ahora".
3. **Reentrenar con features parciales** (truncar flujos de CICIDS a
   prefijos): el modelo aprende la pista en la que jugara → conecta con
   ADR-040 y con DEBT-L1-TRAINER-MISSING-001 (el entrenador hay que
   reconstruirlo IGUAL — matar dos deudas de un ADR).
   Implicacion para el paper: la comparativa Suricata/Zeek/aRGus y cualquier
   claim de deteccion del pipeline vivo quedan condicionados por esta deuda.
   El paper honesto cuenta la tenaza (0.9987 modelo / 0.0 desplegado / por que)
   — es MEJOR paper que el que habia.

## COMMITS PENDIENTES DE LA MADRUGADA (verificar con git log/status)

1. Apendice al DAY220_FINDINGS.md: §13-18 (fichero DAY220_FINDINGS_APPENDIX
   preparado) + §19 (resultado via A — bloque redactado en el chat de las
   03:0x, con la tabla de arriba y las dos trampas nuevas).
2. `tools/eval/out/eval_level1_neris_report.json`.
3. Fix del Makefile: el comentario inline de NERIS_BRONZE_GLOB inyectaba
   espacios y rompia el glob (comentario a linea aparte).
4. El placeholder `<hash>` de §8 del findings → `73fac317`.
5. La discrepancia 21/22 del DAY219 (§3 vs §6) sigue pendiente de corregir.

## ESTADO DEL ENTORNO

- Replay TERMINADO → la VM client puede apagarse (`vagrant halt client`).
- MTU 9000 y modo dual: sin nada que revertir (dual es el estado commiteado;
  la MTU se pierde sola en el proximo reboot — irrelevante ya).
- Bronce del run en `/vagrant/logs/correlation/argus/*.csv`; todo lo previo
  en `archive-pre-neris/`. Decidir si archivar el run tambien (es el dato
  primario del report — NO borrar; candidato a comprimir y guardar).
- Sin commitear a proposito: zmq_handler.{hpp,cpp} (instrumentacion DAY216,
  patch en docs/), commit-message.txt, tools/temporal.md.
- STASH intacto: `stash@{0}: commit2-noisy-or WIP`.

## TRAMPAS NUEVAS DE LA SESION (ya en el apendice; reglas desde hoy)

- `nohup &` bajo `vagrant ssh -c` muere con la sesion → `sudo sh -c 'setsid
  nohup CMD > log 2>&1 < /dev/null &'`.
- Frames CTU >1500 bytes: MTU 9000 en ambos extremos; NUNCA --mtu-trunc
  (altera features de longitud).
- Comentario inline en asignacion Make → espacios finales en el valor.
- **awk en la VM con locale es_ES compara numeros como TEXTO** ("0,5"):
  aritmetica en VM SIEMPRE con `LC_ALL=C` y `$1+0`. (Los conteos por umbral
  de las 02:5x fueron basura hasta corregirlo; max y uniq -c verificados
  como no afectados.)
- `| head -N` puede amputar la linea decisiva (caso 25); grep sin eje
  temporal en logs acumulativos mezcla eras (caso 26) → MARCA + awk.

## PATRON DE FALSA EVIDENCIA: 26 casos

22-24: arqueologia (commit "1.67M" sin contar; md5 bf0dd7e9 mal atribuido a
un pcap; notebooks-esqueleto como procedencia fantasma). 25-26: de Claude
(head truncado → diagnostico falso de mono-interfaz; grep sin tiempo →
falsa regresion). La sospecha de regresion eth2 quedo DESCARTADA: el modo
`dual` funciono siempre (events CSVs de abril-junio lo prueban);
`gateway-only` no consume eth2 → DEBT-SNIFFER-GATEWAY-ONLY-NO-CONSUMER-001
(P3).

## HITOS DE DAY 220 (no re-litigar)

- "Wednesday es holdout" REFUTADO: split 80/20 sobre los 8 dias juntos
  (aritmetica exacta 566149 = 0.2*2830743 + notebook 02, seed 42).
- Via B: recall 0.9987 / FPR 0.00025 (scope: sanity in-sample). El fosil del
  2,4% DEMOSTRADO como autopsia del XGBoost (misma base de 252.672 ataques).
- Procedencia: 02 probado (f53c676a); entrenador/conversor NUNCA versionados
  (03/06 = esqueletos de 216 bytes; sesion Jupyter 15-oct-2025 09:50-10:06)
  → DEBT-L1-TRAINER-MISSING-001 (P2).
- GT646 de Table 11 NO reconstruible bajo 8 criterios →
  DEBT-NERIS-GT646-UNPROVENANCED-001 (P1). El GT nuevo (8.935) es el
  denominador con procedencia.
- Deudas nuevas del dia: PARTIAL-FLOW-SCORING (P0), NERIS-GT646 (P1),
  L1-TRAINER-MISSING (P2), BRONZE-IP-BYTEORDER (P2, confirmada en vivo:
  165.84.32.147), MAKEFILE-MLDETECTOR-START-PROFILE (P2),
  SNIFFER-GATEWAY-ONLY-NO-CONSUMER (P3), extension XGBOOST-FOSSIL al
  Makefile (deploy/sign solo tocan XGBoost).
- El 2.517 sigue SIN PROCEDENCIA. level2/level3 siguen SIN AUDITAR.

Reglas permanentes: medir no votar; un commit/un cambio/una razon; git add
explicito (NUNCA -u/-a); verificar la ruta antes de concluir del contenido;
la premisa heredada tambien es un artefacto a verificar; EMECAS antes de
cualquier merge.