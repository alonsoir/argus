# Informe de auditoría del veredicto del `ml-detector` — para el Consejo de Sabios

**Proyecto:** aRGus NDR · **Repositorio:** todo lo citado está en `main`, corroborable línea a línea
**Fichero principal auditado:** `ml-detector/src/zmq_handler.cpp` (`ZMQHandler::process_event`, líneas 322–875)
**Sesiones de medición:** DAY 209 → DAY 212 (auditoría, sin cambios de código)
**Método:** *medir, no votar* — cada afirmación se traza hacia atrás desde el binario / el fichero, nunca desde la memoria.

---

## 0. Propósito y encuadre (léase antes que nada)

Este documento no busca aprobación para una fecha. **No hay fecha límite en este documento.** El criterio es uno solo: el `ml-detector` debe quedar **fiable y determinista**, o debemos saber —con prueba medida, no con excusa— qué parte no podemos dejar bien todavía y **por qué técnico**.

Reglas que gobiernan esta auditoría y que pedimos al Consejo respetar:

1. **La calidad del pipeline no se negocia.** O funciona bien, o no se presenta. No presentaremos ante nadie —ni FEDER, ni la comunidad, ni un hospital— algo que funcione a medias.
2. **"No hay tiempo" no es una razón válida** para descartar una cabeza de clasificación. La única razón válida para no proveer una cabeza es **técnica**: features irrecuperables, dato de entrenamiento inexistente, o un coste que rompa el determinismo. Si una cabeza no puede quedar bien, necesitamos saberlo con esa razón técnica explícita.
3. **Separamos dos sentidos de "arreglar"**, y el Consejo debe mantenerlos separados en toda su deliberación:
    - **(A) Cablear bien** — que la arquitectura de ejecución coincida con la arquitectura que el diseño promete, y que la señal llegue correcta aguas abajo hasta el grafo. Esto está **en nuestras manos y es medible ahora**.
    - **(B) Cabezas fiables** — que cada clasificador discrimine de verdad sobre tráfico real. Esto **depende de datos** (algunos aún no generados) y no puede prometerse por decreto.
      Prometer (B) para una fecha sería sesgo de confirmación. Lo honesto es: **(A) ya, con cada cabeza entrando según su fiabilidad medida; (B) con un plan nombrado para elevar esa fiabilidad cuando el dato exista.**
4. **Somos honestos. No mentimos ni tergiversamos.** Damos lo mejor que tenemos con humildad y trabajo. Este documento distingue en todo momento tres categorías: **HECHO MEDIDO**, **PREGUNTA ABIERTA**, **SUPUESTO DECLARADO**.

> **A quién sirve esto.** El destino último del `ml-detector` es proteger hospitales y organizaciones que no pueden pagar seguridad de nivel empresarial. Una señal falsa o un veredicto a medias no es un bug abstracto: es un escudo que dice "protegido" cuando no lo está. Ese es el listón.

---

## 1. Resumen ejecutivo — qué está roto, medido

El veredicto del `ml-detector` (`final_classification`: MALICIOUS/BENIGN) tiene **dos defectos apilados**, y la auditoría destapó un **tercer problema de persistencia** que no estaba en el diagnóstico inicial. Los tres están medidos sobre fichero.

| # | Hallazgo | Categoría | Evidencia | Gravedad |
|---|----------|-----------|-----------|----------|
| **A** | El veredicto se sella (`set_overall_threat_score`, L402) **antes** de que corran las 4 cabezas especializadas (L558–819). Las cabezas escriben un informe que el veredicto ya no lee. | HECHO MEDIDO | `zmq_handler.cpp:399–402` vs `558–819` | Alta |
| **B** | **Causa raíz.** Las 4 cabezas solo corren si L1 dijo ATTACK (`if label_l1==1 …`, L552). L1 es un *portero*, no un compañero de ensemble. Un flujo que el interno vería como exfiltración pero que L1 (genérico) marca BENIGN, sale BENIGN y el interno **nunca se ejecuta**. | HECHO MEDIDO | `zmq_handler.cpp:552` | Crítica |
| **C** | **Nuevo (DAY 212).** Las escrituras a disco (bronce, RAG, CSV) ocurren **antes** del gate y de las cabezas (L525–542). El dato histórico que alimenta el grafo se sella **pre-inferencia-especializada**. | HECHO MEDIDO | `zmq_handler.cpp:525–542` + fila de bronce real (§4) | Crítica (envenena la fuente de verdad del grafo) |

**Consecuencia conjunta:** el `ml-detector` es hoy, en ejecución, un clasificador **monocapa** (`max(fast_path, L1)`) que contradice la arquitectura **tricapa** que el paper (arXiv:2604.04952) dibuja. Las cuatro cabezas especializadas existen, se ejecutan (cuando L1 abre el portón) y rellenan telemetría — pero **ni deciden el veredicto ni llegan al grafo**.

**Además, dos de las cuatro cabezas están medidas como no-fiables** por la salud de su extractor de features (ransomware 1/10, traffic 5/10 — §3). Esto es problema **(B)**, distinto de **(A)**, y es el que necesita la deliberación técnica del Consejo.

---

## 2. Anatomía del flujo real de `process_event` (medido)

Secuencia de ejecución tal como está en el fichero, **no** como la dibuja el diseño. Cada línea es verificable en `main`.

```
322   ZMQHandler::process_event(message)         ← inicio
351   fast_score = event.fast_detector_score()   ← se LEE y se PRESERVA (el bug viejo DAY 11-12 NO existe)
358   extract_level1_features + validate
375   level1_model_->predict → label_l1, confidence_l1
393   enrich ml_analysis con L1
399   ml_score = (label_l1==1) ? confidence_l1 : (1-confidence_l1)   ← "Dual-Score": ml_score ES L1 y SOLO L1
400   event.set_ml_detector_score(ml_score)      ← ⚠ el campo del wire se rellena con SOLO L1 (DEBT-5)
401   final_score = max(fast_score, ml_score)    ← COMBINADOR: max de 2 fuentes
402   event.set_overall_threat_score(final_score) ← ★ VEREDICTO SELLADO AQUÍ (Defecto A)
404   authoritative_source = DIVERGENCE|CONSENSUS|FAST_PRIORITY|ML_PRIORITY  ← razona fast-vs-ml
416   decision_metadata (score_divergence, requires_rag)
433   final_classification = (final_score >= malicious_threshold) ? MALICIOUS : BENIGN
445   provenance = event.mutable_provenance()    ← ★ COLECCIÓN de veredictos (ADR-002), acepta N
452   provenance->add_verdicts() ← "random-forest-level1"   ← hoy: sniffer + L1 = 2 veredictos
481   provenance->set_final_decision(DROP|ALLOW)
505   ml_context.attack_family = "RANSOMWARE"    ← ⚠ HARDCODED (DEBT-4)
525   correlation_writer_->write_record(event)   ← ★ ESCRITURA BRONCE (Defecto C — pre-cabezas)
530   rag_logger_->log_event(event, ml_context)  ← ★ ESCRITURA RAG   (Defecto C — pre-cabezas)
541   csv_writer_->write_event(event)            ← ★ ESCRITURA CSV   (Defecto C — pre-cabezas)
549   if (label_l1==1 && confidence_l1 >= level1_attack) {  ← ★ GATE L1 (Defecto B — causa raíz)
550     event.set_threat_category("ATTACK")                 ←   (ATTACK va DENTRO del gate)
558       DDoS      → predict (596)  → add_specialized_predictions
626       Ransomware→ predict (665)  → add_specialized_predictions
697       Traffic   → predict (733)  → decide dominio interno/internet
748         if (traffic.is_internal())
756           Internal → predict (780) → set_threat_category("SUSPICIOUS_INTERNAL") (795)
819     else: event.set_threat_category("NORMAL")
823   plugins invoke_all (ADR-012)
850   send_enriched_event(event)                 ← ★ EMISIÓN ZMQ
875   fin process_event
```

**Tres fronteras de no-retorno**, no una. El plan previo (DAY 211) asumía que bastaba "mover el veredicto tras 802". La medición demuestra que hay **tres puntos donde el estado del evento escapa** de `process_event`:

- **Disco (bronce/RAG/CSV):** L525–542 — **antes** de las cabezas.
- **ZMQ:** L850 — después de las cabezas.

Para que el arreglo llegue **al grafo** (no solo al ZMQ), la persistencia a disco debe reubicarse después de la inferencia completa. Esto es el núcleo de por qué (C) es crítico.

---

## 3. Salud de las cuatro cabezas — extractores de features (medido)

Una cabeza no vale más que su extractor. Medimos, feature a feature, cuántas leen datos reales de `NetworkFeatures` y cuántas son constantes o proxies mal nombrados. Fichero: `ml-detector/src/feature_extractor.cpp`.

### 3.1 Ranking de salud (medido sobre fichero)

| Cabeza | Extractor | Reales / Constantes | Veredicto |
|--------|-----------|:---:|-----------|
| **Internal (L3)** | `extract_level3_internal_features` (404–448) | **7 / 2** (1 discutible) | **Mejor candidato.** `[5]` lateral, `[7]` exfil, `[6]` scanning, `[9]` size-std leen `nf`. `[1]`,`[2]` constantes. |
| DDoS (L2) | (medido DAY 209) | 6 / 3 (1 real de peso) | Degradado pero vivo. |
| Traffic (L3) | `extract_level3_traffic_features` (347–403) | **5 / 5** | **Roto.** `[6]`,`[7]`,`[8]` son literal `1.0f`; `[4]`,`[5]` son proxies mal nombrados. |
| Ransomware (L2) | (medido DAY 194–209) | **1 / 9** | **Roto por diseño.** `entropy` = varianza de longitud de paquete ÷ 100.000, no Shannon. |

### 3.2 Evidencia — Internal (el bueno), features de peso

```cpp
// [5] Lateral Movement Score — REAL (lee syn_flag_count, fin_flag_count)
float syn_rate = safe_divide(nf.syn_flag_count(), total_packets);
float completion_rate = safe_divide(nf.fin_flag_count(), max(nf.syn_flag_count(),1));
features[5] = syn_rate * (1.0f - completion_rate);

// [7] Data Exfiltration — REAL (lee total_forward_bytes / total_backward_bytes)
float outbound_ratio = safe_divide(nf.total_forward_bytes(), max(nf.total_backward_bytes(),1));
features[7] = (outbound_ratio > 2.0f) ? normalize(outbound_ratio, 2.0f, 10.0f) : 0.0f;

// [1],[2] — CONSTANTES (no leen nf)
features[1] = 1.0f - normalize(1.0f, 0.0f, 5.0f);   // "service port consistency"
features[2] = 1.0f - normalize(1.0f, 0.0f, 3.0f);   // "protocol regularity"
```

### 3.3 Evidencia — Traffic (el roto), 5 de 10 constantes

```cpp
features[6] = normalize(1.0f, 0.0f, 10.0f);          // "source IP entropy"      — CONSTANTE
features[7] = 1.0f - normalize(1.0f, 0.0f, 10.0f);   // "dst IP concentration"   — CONSTANTE
features[8] = normalize(1.0f, 0.0f, 10.0f);          // "protocol variety"       — CONSTANTE
features[4] = min(normalize(nf.flow_iat_std()...),1); // "port entropy" ← ES IAT std, MAL NOMBRADO
features[5] = normalize(nf.flow_duration.../1e6, ...); // "flow duration std" ← ES duración cruda
```

### 3.4 El cable aguas arriba SÍ está poblado (medido — cierra un caveat importante)

Verificamos que el sniffer **rellena con valores reales de flujo** los campos que lee el extractor Internal. No son campos muertos:

```
sniffer/src/userspace/ml_defender_features.cpp:
  919  set_syn_flag_count(flow.syn_count)
  918  set_fin_flag_count(flow.fin_count)
  920  set_rst_flag_count(flow.rst_count)
  752  set_total_forward_bytes(flow.sbytes)
  753  set_total_backward_bytes(flow.dbytes)
  787  set_packet_length_std(std_dev)
  848-851 set_flow_inter_arrival_time_{min,max,mean,std}
```

**Distinción honesta:** esto prueba que el cable llega a un campo **poblado con telemetría real** (sniffer→extractor verificado end-to-end). **NO** prueba que esos valores **discriminen** clases sobre tráfico interno real — eso es medición pendiente (§6, MITRE). El peso alto provisional del Internal descansa en "cable verificado", no en "calidad demostrada".

> **Nota (flanco, no-DEBT aún):** existe un segundo camino de poblado en `ring_consumer.cpp:908` que hace `set_total_backward_bytes(0)` hardcodeado (fast-path). En ese camino, `[7]` exfil (ratio forward/backward) se dispararía artificialmente. El camino principal (`ml_defender_features.cpp:753`) usa `flow.dbytes` real. **Dos caminos de poblado, uno real y uno degradado.** Hay que medir cuál domina en producción antes de elevarlo a DEBT.

---

## 4. La prueba cruda — el bronce está sellado monocapa (medido, no inferido)

`DEBT-BRONZE-WRITTEN-PRE-HEADS-001` no se apoya en "leímos el orden de las líneas". Se apoya en una **fila real de bronce** de producción:

```
Fichero: /vagrant/logs/correlation/argus/2026-07-06-211714.csv

1,argus,55699877993945_547895546,cpp_sniffer_v33_day12,1:ciqxbXnDl7bVdFSSI2s2iLJixUM=,
55699,877993945,1.56.168.192,251.0.0.224,5353,5353,UDP,BENIGN,RAW_CAPTURE,
0.000000,0.068406,0.068406,DETECTOR_SOURCE_ML_PRIORITY,6243e4ca...
                          ▲            ▲
              final_classification   threat_category = "RAW_CAPTURE"
                    = BENIGN          (etiqueta del SNIFFER, no del ml-detector)
```

**Lectura medida:**
- `threat_category = RAW_CAPTURE` → es la etiqueta que pone el **sniffer** (`ring_consumer.cpp:943`), no ninguna de las del `ml-detector` (ATTACK/DDOS/RANSOMWARE/SUSPICIOUS_INTERNAL/NORMAL). Confirma que la fila se escribió **antes** de que el `ml-detector` etiquetara nada.
- Las cuatro cabezas nunca tocaron esta fila. El grafo (bronce→AVRO→Parquet→Kuzu) ingiere el estado **pre-inferencia-especializada**.

**Y el RAG remacha `DEBT-RAG-ATTACKFAMILY-HARDCODED-001`:**

```
Fichero: /vagrant/logs/rag/artifacts/2025-12-14/event_fast-alert-5018010314181.json
  "attack_family":    "RANSOMWARE"              ← hardcoded en zmq_handler.cpp:505
  "threat_category":  "RANSOMWARE_FAST_DETECTION"
```

En este caso concreto (una detección rápida de ransomware del sniffer) el `attack_family="RANSOMWARE"` coincide **por accidente**. Cualquier evento no-ransomware saldría igualmente etiquetado "RANSOMWARE". El defecto se sostiene.

---

## 5. La señal aguas abajo — cómo consume el firewall (medido)

Rastreamos `threat_category` (campo 17 del wire, `network_security.proto:595`) hasta sus consumidores. Clasificación en tres grados: **(a)** solo se escribe · **(b)** se lee para registrar · **(c)** se lee para decidir.

| Consumidor | Fichero:línea | Grado | Qué hace |
|-----------|---------------|:---:|----------|
| Firewall STEP 5 | `zmq_subscriber.cpp:610` | **(c) acotado** | Modula `timeout` (DDOS→600s, RANSOMWARE→3600s, resto→300s) y `DetectionType`. **NO decide si-bloquear.** |
| Firewall logger | `logger.cpp:348` | (b) | Etiqueta `threat_type`/`detector_name` en log estructurado. |
| Bronce | `correlation_writer.cpp:97` | (b) | Columna 13. Contamina el dato del grafo (§4). |
| RAG | `rag_logger.cpp:239` | (b) | JSON artifact. |
| CSV | `csv_event_writer.cpp:256` | (b) | Columna 9. |

**El gate de L1 está cableado DOS veces** (hallazgo GAP 4, medido). El firewall filtra la entrada **antes** de STEP 5:

```cpp
// firewall-acl-agent/src/api/zmq_subscriber.cpp (~583)
if (!ml.attack_detected_level1()) {
    FIREWALL_LOG_DEBUG("No Level 1 attack detected, skipping");
    return;   // ← el firewall DESCARTA el evento si L1 no marcó ataque
}
```

**Consecuencia para el arreglo:** reconectar las cabezas al veredicto **en el `ml-detector` no basta**. Aunque el `ml-detector` emitiera `SUSPICIOUS_INTERNAL` en un flujo que L1 marcó BENIGN, el firewall lo descartaría en `attack_detected_level1()`. **El des-gateo es de dos componentes** (`ml-detector` + `firewall-acl-agent`), no uno.

Confirmación de "(c) acotado": como el bloqueo lo decide el filtro L1 (no `threat_category`), un `threat_category` erróneo **modula la respuesta** (duración, tipo) pero **no crea ni suprime bloqueos**. `DEBT-TRAFFIC-EXTRACTOR-CONSTANTS-001` queda en **P2-alto**, no P1: el traffic 5/10 constante puede producir un `SUSPICIOUS_INTERNAL` espurio con timeout de 300s — sobre-bloqueo leve y temporal, no fallo de seguridad.

---

## 6. El combinador ya existe como colección (medido — corrige diagnóstico previo)

**Corrección honesta:** en sesiones previas afirmé que el combinador eran "dos escalares sueltos, sin colección de fuentes". La lectura completa del tramo 432–486 (que no habíamos leído) **lo refuta**. Existe `provenance` (ADR-002), una estructura de **N veredictos**:

```cpp
// zmq_handler.cpp:445–481
auto* provenance = event.mutable_provenance();
bool sniffer_verdict_exists = (provenance->verdicts_size() > 0);   // ya soporta N
auto* rf_verdict = provenance->add_verdicts();                     // añade veredicto
rf_verdict->set_engine_name("random-forest-level1");
rf_verdict->set_classification(...); rf_verdict->set_confidence(confidence_l1);
rf_verdict->set_reason_code(...);    rf_verdict->set_timestamp_ns(...);
...
provenance->set_discrepancy_score(discrepancy);
provenance->set_final_decision(final_score >= malicious_threshold ? "DROP" : "ALLOW");
```

**Implicación para fase 2 (buena noticia):** el noisy-OR **se injerta**, no se reescribe. Cada cabeza añade su `add_verdicts()` con su `engine_name` y `confidence`; el combinador lee `provenance->verdicts()` como colección y cambia la fórmula de agregación de `max` a noisy-OR. La estructura de provenance ya existe y acepta N. `provenance->set_final_decision()` (L481) ya es el punto único de decisión.

**Operador de combinación acordado (a ratificar por el Consejo):**

```
noisy-OR:   P = 1 − ∏(1 − pᵢ)      con   pᵢ = fiabilidad_i · score_crudo_i
```

Propiedades: monótono (ninguna cabeza suprime a otra — a diferencia de la media ponderada, que deja que vecinos callados voten a la baja una cabeza fiable que dispara); corroboración incorporada (ransomware+interno se refuerzan); siempre ≥ que `max` (el fast-path sigue dominando cuando dispara). Pesos = fiabilidad **medida** (§3 + F1 por cabeza), no votada.

---

## 7. Coste y determinismo — lo medido y lo pendiente

### 7.1 HECHO MEDIDO — latencia de inferencia del Internal

Micro-benchmark con flags de **producción** (`-O3 -march=native -DNDEBUG -flto`), header desplegado, 16 inputs distintos (no solo caché caliente), `volatile sink` contra dead-code elimination, doble corrida:

```
Internal::predict  N=1000000  sink=87875000
  media: 0.584 us/pred  (1.713.354 preds/s)   ← corrida 1
  media: 0.583 us/pred  (1.716.691 preds/s)   ← corrida 2 (estable a la 3ª cifra)
```

Entorno: VM de desarrollo (VirtualBox), recursos limitados. **0.58 μs sobre un presupuesto de 10 ms = 0.006%.** Aunque las 4 cabezas corrieran en el 100% de los flujos, la suma de inferencias es ruido frente al presupuesto. **El Defecto B no tiene coartada de coste en la parte de inferencia.**

> **Para el paper:** este 0.58 μs es el *suelo de latencia de inferencia en hardware de desarrollo con recursos limitados*, dato publicable. **Hueco declarado:** falta el número en "hardware base de producción barato" — se anotará cuando dispongamos de ese hardware, para poder afirmar "en hardware suelo el rendimiento es X".

### 7.2 SUPUESTO DECLARADO — coste de la extracción de features

**No benchmarkeado.** Leído sobre fichero, `extract_level3_traffic_features` y `extract_level3_internal_features` son **aritmética escalar** sobre ~10 getters de proto: sumas, `safe_divide`, `normalize`, comparaciones. **Cero bucles, cero paso sobre paquetes.** Coste manifiestamente de nanosegundos, verificable en el fichero por cualquier revisor. Lo declaramos supuesto, no medición oculta. Si el Consejo lo exige, una ronda de bench (requiere construir un `NetworkFeatures` realista).

### 7.3 Falso positivo de medición que evitamos (lección de método)

La primera corrida del bench dio `0.00 μs` / `inf preds/s`: `-O3 -flto` eliminó el cálculo como dead-code porque el resultado no se usaba. **Un verde que no significaba nada.** Se corrigió forzando el consumo del resultado. Lo documentamos porque es *medir no votar* aplicado al propio instrumento de medida: un número verde no es una medición hasta que se prueba que mide algo.

---

## 8. Registro de deudas técnicas (para volcar a `docs/BACKLOG.md`)

Seis deudas medidas en esta auditoría, más una nota. Prioridad según impacto en **fiabilidad/determinismo**, no según fecha.

| ID | P | Descripción | Evidencia |
|----|---|-------------|-----------|
| `DEBT-VERDICT-MONOCAPA-001` | **P0** | El veredicto es `max(fast, L1)`; las 4 cabezas no lo deciden. Defectos A (secuencia) + B (gate L1). Contradice la tricapa del paper. | `zmq_handler.cpp:401,552` |
| `DEBT-BRONZE-WRITTEN-PRE-HEADS-001` | **P1** | Bronce/RAG/CSV se escriben antes del gate y las cabezas. El grafo ingiere estado pre-inferencia. Envenena la fuente de verdad del reentrenamiento. | `zmq_handler.cpp:525–542` + fila `RAW_CAPTURE` (§4) |
| `DEBT-FIREWALL-L1-GATE-DUPLICATE-001` | **P2** | El firewall filtra por `attack_detected_level1()` antes de STEP 5. El des-gateo requiere tocar dos componentes. | `zmq_subscriber.cpp:~583` |
| `DEBT-TRAFFIC-EXTRACTOR-CONSTANTS-001` | **P2-alto** | Traffic L3: 5/10 features constantes + 2 proxies mal nombrados. Clasificador de dominio no fiable; gatea al interno vía cascada L748. | `feature_extractor.cpp:347–403` |
| `DEBT-RAG-ATTACKFAMILY-HARDCODED-001` | **P2** | `attack_family="RANSOMWARE"` fijo en todo evento RAG. | `zmq_handler.cpp:505` + entrada RAG (§4) |
| `DEBT-ML-SCORE-FIELD-L1-ONLY-001` | **P3** | El campo del wire `ml_detector_score` se rellena con solo L1, no con la combinación de cabezas. Engaña por nombre. | `zmq_handler.cpp:400` |
| *Nota (no-DEBT)* | — | Doble camino de poblado de `backward_bytes`: real (`ml_defender_features.cpp:753`) vs `0` hardcodeado (`ring_consumer.cpp:908`). Medir cuál domina. | — |

**Housekeeping pendiente (arrastrado):** `git rm` de `proto_aligned` con su DEBT; corregir narrativa tricapa→realidad en el paper; actualizar `README.md` y `docs/BACKLOG.md`.

---

## 9. Preguntas al Consejo

Las que necesitan deliberación adversaria de nueve modelos. Ordenadas por lo que bloquean.

### Bloque 1 — Las cabezas rotas (el corazón del asunto)

**P1.** Ransomware (1/10 real: `entropy` = varianza de longitud de paquete, no Shannon) y Traffic (5/10 constante) están medidas como no-fiables. **¿Son recuperables mediante reentrenamiento honesto contra ground-truth de dominio de red, o hay una razón técnica por la que alguna de ellas no debe existir como cabeza dedicada?** Necesitamos la respuesta técnica, no la temporal. Si una cabeza no puede quedar bien, queremos presentarnos diciendo exactamente por qué, con la cabeza alta.

**P2.** Si una cabeza entra al veredicto con **fiabilidad medida ≈0** (peso ≈0 en el noisy-OR), ¿es eso honesto y determinista, o es preferible **no cablearla en absoluto** hasta que su reentrenamiento la haga fiable? Es decir: ¿"cabeza presente con peso 0" vs "cabeza ausente" — cuál es la postura científica correcta para un sistema que se presenta como tricapa?

**P3.** El Traffic detector decide el dominio (interno/internet) que **gatea** al Internal (cascada L748). Si Traffic es 5/10 constante, el clasificador que decide "esto es interno, activa al Internal" es él mismo poco fiable. **¿Debe la cascada L748 sobrevivir al rediseño, o el Internal debe correr desacoplado de la decisión de dominio de Traffic?**

### Bloque 2 — El cableado (arquitectura de fase 2)

**P4.** ¿Ratifica el Consejo el operador **noisy-OR** `P = 1 − ∏(1 − pᵢ)` con `pᵢ = fiabilidad_i · score_i`, frente a alternativas (media ponderada — descartada por dilución; max de N; Dempster-Shafer)? El razonamiento de monotonía y corroboración está en §6.

**P5.** Sobre `provenance` (la colección de veredictos, §6): ¿se injertan las 4 cabezas como `add_verdicts()` adicionales (N fuentes homogéneas), o se conserva el eje fast-vs-ml de `authoritative_source` y el noisy-OR se calcula aparte? La primera opción es más limpia pero cambia la semántica de `authoritative_source` (que hoy habla de 2 fuentes).

**P6.** El des-gateo es de **dos componentes** (§5): `ml-detector` (reconectar cabezas) + `firewall-acl-agent` (relajar `attack_detected_level1()`). ¿Cómo se coordina esto sin romper el contrato del wire ni la lógica de bloqueo existente? ¿Un solo PR atómico o dos secuenciados?

### Bloque 3 — La persistencia y el grafo

**P7.** Reubicar las escrituras de bronce/RAG/CSV **después** de las cabezas (arreglar Defecto C) cambia **qué** se escribe al bronce — que tiene tests golden (`test_correlation_roundtrip`, `correlation_v1_golden_vectors`). **¿Cómo garantizamos que el reordenamiento no rompe el contrato `correlation_v1`?** ¿Se regeneran los golden vectors, o el contrato debe ser invariante al reordenamiento?

**P8.** Mover `log_event` después de las cabezas exige mover (o repoblar) la construcción de `ml_context` (L505–517), cuyos campos `level_2_category`/`level_3_subcategory` hoy son `"UNKNOWN"`. **¿El `ml_context` debe poblarse con lo que produzcan las cabezas?** Esa es justo la información que hoy se pierde.

---

## 10. Fase 2 — plan de acción propuesto (borrador de ADR)

Sujeto a la deliberación del Consejo. Estructura TDH: cada paso con gate de medición; nada sube al veredicto sin su pulso medido. Ningún paso está condicionado a una fecha.

### Precondición — decidir las cabezas rotas (Bloque 1)
Antes de escribir cableado, resolver P1–P3. **Si ransomware/traffic no son recuperables, el plan lo dice y esas cabezas entran con peso 0 explícito y documentado (o se retiran).** No se cablea una cabeza cuya fiabilidad no se ha decidido.

### Paso 1 — Pulso del Internal sobre datos etiquetados (5.2b-i)
Requiere **fuente de datos internos etiquetados** (ver §11). Mide si el Internal *discrimina* clases sobre tráfico interno real, no solo sobre vectores de juguete. **Gate:** sin este número, el peso del Internal en el noisy-OR es provisional, no confianza.

### Paso 2 — Reconexión del cableado (Defectos A + B + C)
1. **Mover el bloque combinador** (399–416) y las **tres escrituras de persistencia** (525–542) a **después** de la sección de cabezas (post-819), antes de `send_enriched_event` (850).
2. **Sacar Internal + (Traffic, según P3) del gate de L1** — corren siempre, desacoplados.
3. **Sustituir `max` por noisy-OR** sobre `provenance->verdicts()`, poblado con las 4 cabezas.
4. **Poblar `ml_context`** con la salida de las cabezas (P8).
5. **Relajar `attack_detected_level1()` en el firewall** (P6), coordinado.

**Tests unitarios del combinador (TDH):** (a) una cabeza dispara → veredicto sube; (b) dos cabezas corroboran → refuerzo; (c) cabeza con fiabilidad-0 NO envenena; (d) golden vectors de bronce siguen verdes tras el reordenamiento (P7).

### Paso 3 — Integración + stress con medición de latencia por cabeza
El stress test que sustituye al sniffer, con latencia recepción→clasificación→firewall por cabeza. Verificar que el nuevo flujo de `SUSPICIOUS_INTERNAL` (que hoy L1 traga) no dispara sobre-bloqueo masivo.

### Paso 4 — pcap relay e2e en hardware propio
TTL real recepción→clasificación→firewall. Aquí entra el número de "hardware base" para el paper (§7.1).

### Paso 5 — Números al paper, con la config honesta
Qué cabeza pesa cuánto, ransomware/traffic con su fiabilidad medida. La limitación se formula como **hueco de cobertura** ("aún no tenemos estas cabezas fiables"), **no** como divergencia predicha. No pre-explicamos divergencias no medidas.

---

## 11. Lo que aún no podemos medir, y por qué (honestidad sobre los límites)

- **Calidad discriminante de las cabezas sobre tráfico real (5.2b-i).** Requiere tráfico **etiquetado** de dominio interno (movimiento lateral, exfiltración). NERIS (CTU-13) es C2 de botnet externo: ejercita las features de red genéricas pero **no valida** lateral/exfil. La fuente de datos es MITRE ATT&CK / Atomic Red Team en entorno controlado, generando señal suficiente y etiquetada (no unos pocos `curl`, que no harían saltar el pipeline). **Este es el trabajo de datos que condiciona (B), y no puede sustituirse por tiempo ni por decreto.**
- **Reentrenamiento de ransomware/traffic contra ground-truth de red.** Depende de tener ese dato etiquetado primero.
- **Coste en hardware de producción.** Depende de tener el hardware base definido.

Ninguno de estos límites bloquea el **cableado honesto (A)**, que sí está en nuestras manos ahora. Lo que bloquean es poder *afirmar* que las cuatro cabezas son fiables — y por eso no lo afirmaremos hasta medirlo.

---

## 12. Cierre

El `ml-detector` tiene defectos, algunos serios, todos medidos y corroborables en `main`. No pedimos aprobar una versión a medias: pedimos la deliberación adversaria de nueve modelos para dejar la pieza **fiable y determinista**, o para saber con prueba técnica qué cabeza no podemos dejar bien todavía y por qué.

El fin no es una fecha. El fin es un escudo que hace lo que dice que hace, para hospitales y organizaciones que no pueden pagar otro. Ese es el listón, y no lo bajamos.

*Via Appia Quality — medir quién clasifica, no solo cómo de bien. Un escudo que conoce sus propias sombras, incluida la sombra entre su código y su diagrama.*

---

### Anexo — recordatorio para el Consejo
Todo lo citado (líneas de fichero, filas de bronce/RAG, salida de benchmarks) está en `main` y es verificable directamente en el repositorio. Los números de línea son de DAY 212; si al abrir no cuadran por deriva entre sesiones, re-grepear `set_overall_threat_score`, `label_l1 == 1 &&`, `mutable_provenance`, `correlation_writer_->write_record`.