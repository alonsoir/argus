# Prompt de continuidad — aRGus NDR, DAY278 → DAY279

Reglas de trabajo: las mismas de DAY278 (medir, no votar; predicción escrita antes de medir;
comandos separados o cada salida a su fichero; nunca `grep -rn` desde la raíz; los scripts los
ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo no da lo esperado, parar).
Foco (Alonso, DAY278): validar la cabeza DDoS POR SEPARADO; las demás cabezas quedan fuera de foco.

## 1. Medido en DAY278

| Corrida | Condición | Resultado |
|---|---|---|
| Neris (ctu-start) | pipeline normal | 1 IP en el set = 147.32.84.165 (el bot, TP). Cabeza DDoS: 3 veredictos, 3 class=0 (sin FP). Grafo: suricata 286 / zeek 11609 / argus 279, invariante 0, 122 corroborados |
| cic1 (flood CICDDoS2019, 100 pps, 02:17:30–02:25:50) | compuerta level1 activa | level1 3592 BENIGN / 0 ATTACK; 3472 flujos de .50 vetados; cabeza DDoS 0 veredictos; .50 nunca llega al firewall; DROP 0. Reproduce DAY270 |
| cic2 (mismo flood, 03:12:49–03:21:09) | FORCE_ALL_HEADS=1 | 2546 flujos de .50; cabeza DDoS 538 class=1 / 2328 class=0 (18,8 %; DAY272: 21,2 %), 530 "DDoS ATTACK". .50 NUNCA llega al firewall; DROP 0 |

- **P2 CONFIRMADA (con Neris):** 147.32.84.165 recorre 60→300→3600→86400→604800→2073600 en ~2 min
  de un único episodio; strikes sigue subiendo sin techo (7, 8, 9). Sin timeout 0 ni Batch flush failed (P4 ok).
- **Firewall bloquea con threat_category=NORMAL:** Neris → 12179 eventos NORMAL + 3 ATTACK (todos .165);
  el bloqueo de .165 fue por eventos NORMAL (conf 0.58–0.64).

## 2. Hallazgo principal (código leído, zmq_handler.cpp)

- L411: `final_score = max(fast, ml)` se calcula ANTES de nivel 2. De él salen `final_classification`
  (L442) y `provenance.final_decision` DROP/ALLOW (L483).
- La cabeza DDoS (L612) solo pone `threat_category="DDOS"`; NO toca final_score ⇒ su nota no influye
  en la recomendación. Ejemplo en el log: DDoS 88,33 % → evento enviado → "✅ BENIGN, confidence=64.32%".
- `send_enriched_event` (≈L851) se llama para TODOS los eventos: el ml-detector no filtra; el que
  descarta es el firewall.
- Con FORCE_ALL_HEADS todo evento sale con categoría "ATTACK" (L551).
- Firewall: candidato a filtro `batch_processor.cpp:287` (confidence < min_confidence 0.5 &&
  !block_low_confidence). Para .50: fast≈0, ml=1−0.90=0.10 ⇒ final 0.10.
- Conclusión para el paper: quitar el veto de level1 no basta; la nota de cada cabeza tiene que entrar
  en la fórmula que decide la recomendación. Alonso: decide el ml-detector, el firewall ejecuta.

## 3. Aviso antes de fusionar
El primer class=1 de la ventana de cic2 (03:12:19) es ANTERIOR al replay ⇒ tráfico de fondo: la cabeza
DDoS también dispara sobre el ambiente. Los 538/530 mezclan flood y fondo. Hay que medir el FP sobre
el fondo ANTES de meter la nota de la cabeza en final_score, o se bloquearán IPs del propio lab.

## 4. Pendiente inmediato (lecturas sobre datos ya guardados)
1. [defender] Veredictos DDoS por IP (recall limpio sobre .50 + FP sobre el fondo):
   grep -E '^\[2026-09-24 03:(1[2-9]|2[01])' /vagrant/logs/lab/ml-detector.log | awk '/Flow: /{split($0,a,"Flow: "); split(a[2],b,":"); ip=b[1]} /DDoS: class=/{match($0,/class=[01]/); n[ip" class="substr($0,RSTART+6,1)]++} END{for(k in n) print n[k], k}' | sort -k2 > /tmp/d278_ddos_by_ip.txt; cat /tmp/d278_ddos_by_ip.txt
   (ojo: si los hilos intercalan líneas, la atribución por "última línea Flow" no es exacta)
2. [Mac] De dónde sale la `confidence` del firewall y qué filtra antes de "Processing threat event":
   sed -n '540,630p' firewall-acl-agent/src/api/zmq_subscriber.cpp > /tmp/d278_fw_sub.txt; cat /tmp/d278_fw_sub.txt
   Predicción: confidence = overall_threat_score (o ml_detector_score) + corte temprano silencioso.
3. Con 1 y 2: diseñar la fusión en el ml-detector (nota de la cabeza DDoS → final_score →
   clasificación/decisión), con test, medir FP de fondo y repetir cic2 esperando que .50 entre en el set.

## 5. Deuda nueva (registrar en BACKLOG)
- DEBT-ML-DETECTOR-L2-NOT-IN-FINAL-SCORE-001 — lo de la sección 2 (P0 de la vía DDoS).
- DEBT-FIREWALL-BLOCKS-NORMAL-CATEGORY-001 — bloqueos con threat_category=NORMAL.
- DEBT-RECIDIVISM-SAME-EPISODE-001 — P2: tope en ~2 min dentro de un episodio; strikes sin techo.
  Propuesta: reincidencia = volver DESPUÉS de cumplir la condena.
- DEBT-FIREWALL-IPTABLES-RULES-NOT-IDEMPOTENT-001 — cada reinicio duplica las reglas de INPUT
  (tras cic2: posiciones 4–6 = copia de 1–3).
- DEBT-FORCE-ALL-HEADS-MISLABELS-ATTACK-001 — L551.
- Preflight corregido: el DROP vive en INPUT regla 2 (tras el ACCEPT de whitelist en pos 1);
  ML_DEFENDER_TEST tiene 0 referencias.
- Siguen abiertas las de DAY277: H3 overflow retry, stale binary, comment flag, autonomy whitelist (H7),
  procedencia del _lab.pcap, higiene .old/.orig.

## 6. Artefactos DAY278
- /vagrant/scripts/d278_snap_blacklist.sh (CHAIN=INPUT por defecto, comment completo, packets por entrada)
- CSV: d278_snaps_neris.csv, d278_snaps_cic1.csv (cic2 no llegó a grabarse)
- Offsets: d278_fwlog_offset.txt (antes de pipeline-start), d278_fwlog_offset2.txt (antes de cic2)
- Ventanas: cic1 02:17:30–02:25:50; cic2 03:12:49–03:21:09 (epoch 1790219569–1790220069)
- NO usar logs-lab-clean (mueve los logs y rompe el fd del proceso vivo); para rotar, truncate -s 0.
## 7. Estrategia acordada al cierre de DAY278 (Alonso + Claude)

- Orden: primero cada cabeza por separado (arreglar sus problemas internos); DESPUÉS revisar el
  algoritmo del ml-detector que produce clasificación + recomendación al firewall (fusión, L411).
  La fusión se retrasa a propósito: meter hoy notas no calibradas en final_score cambiaría falsos
  negativos por falsos positivos sobre el tráfico del propio lab.
- Contrato que debe entregar cada cabeza antes de entrar en la fusión: (a) probabilidad calibrada,
  (b) FP medido sobre tráfico de fondo, (c) recall medido con dataset etiquetado.
- Level1 (ataque general) está mal afinada para DDoS: trabajo pendiente CUANDO se cierre la DDoS.
  Matiz medido (DAY270): los flujos del flood son de 1 paquete UDP, indistinguibles uno a uno de
  un datagrama legítimo ⇒ endurecer level1 no basta; la solución de fondo para DDoS es la unidad agregada.
- El ~20 % de la cabeza DDoS NO es su techo: aún clasifica flujo a flujo. El agregador por víctima
  del kernel (DAY274, ddos_victims → CSV) NO está conectado a la cabeza; source_ip_dispersion clavada
  en 0.100; el 20 % sale de packet_size_entropy; modelo entrenado con datos sintéticos. La palanca
  principal está sin probar. Alonso esperaba más detección de la cabeza DDoS.
- Los scores de las cabezas no son "malos" en sí (la DDoS dio 88 % y acertaba): el bug es que se
  ignoran al fijar final_score (L411). Dos problemas distintos.

## 8. Plan de la cabeza DDoS (siguiente sesión)
1. Recall limpio sobre 192.168.100.50 + FP sobre el tráfico de fondo (awk por IP de la sección 4).
2. Leer el filtro del firewall (zmq_subscriber.cpp 540–630).
3. Conectar el agregador del kernel a la cabeza DDoS.
4. Volver a medir con cic2 (FORCE_ALL_HEADS=1).
5. Decidir: seguir incidiendo en la DDoS o pasar EMECAS+++, mergear a main y empezar otra cabeza.
