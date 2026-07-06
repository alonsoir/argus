# PLAN DE CAMPAÑA — Medición fast-path × ml-detector y ejecución del feedback del Consejo

**Origen:** DAY 209. Auditoría de features → feedback del Consejo (7-2) → duda de Alonso
sobre si el F1 histórico mide el ml-detector o el fast-path.
**Prioridad:** MÁXIMA. Este plan se antepone a todo el backlog hasta agotarlo o bloquearse.
**EMECAS+++ del test de equivalencia (`test_flujo_a_b_equivalence`): HECHO, verde,
mergeado a `main`.** Frente cerrado.

**Principio rector:** medir, no votar — y esta vez, medir *quién* clasifica, no solo
*cómo de bien*. El pecado raíz detectado por el Consejo adversario (ChatGPT + Claude,
por separado) es que la propuesta original, el voto de 7 consejeros y la validación
histórica del pipeline asumieron que el ml-detector clasifica, sin haberlo medido
aislado del fast-path.

---

## HALLAZGOS MEDIDOS (paso 0.1 completado — lectura completa de `process_event`)

*Confirmado por lectura de `ml-detector/src/zmq_handler.cpp` líneas 322–880, no por
inferencia. Estos ya NO son hipótesis: son hechos trazados al código.*

### H1 — El veredicto es MONOCAPA, no tricapa
El `final_classification` que fluye al firewall y al circuito bronce→gold→Kuzu se
calcula así y SOLO así (zmq_handler.cpp):
```
ml_score    = confianza de Level 1  (RandomForest ONNX 23 features, "ATTACK vs BENIGN")
final_score = max(fast_score, ml_score)          // línea 406
final_classification = final_score >= malicious_threshold ? MALICIOUS : BENIGN  // 432
```
Las CUATRO cabezas embebidas (DDoS, Ransomware en L2; Traffic/externo, Internal en L3)
se ejecutan DESPUÉS (líneas 558–794), calculan su probabilidad, y la escriben en
`ml_analysis.specialized_predictions` y en `threat_category`. **Ninguna toca `ml_score`,
`final_score` ni `final_classification`.** Son telemetría/enriquecimiento que viaja al
CSV y al bronce, no señal de veredicto.

### H2 — Implicación para el paper (DECISIÓN DE ALONSO: contar la verdad)
El F1 histórico del pcap relay salió de `max(fast_path, Level1)`. Level 2 y Level 3 NO
participaron. Presentar ese F1 como validación de arquitectura "tricapa" no se sostiene
contra el código.
**Decisión tomada:** actualizar el paper para reflejar la realidad. Reconocer el bug
explícitamente, con estos ficheros del repo como evidencia. Narrativa honesta: fast-path
heurístico (alto recall, alto FPR) validado por L1 (reduce FPR ~15.500× según medición
DAY 83), con cabezas L2/L3 como enriquecimiento categórico. NO inflar "tricapa".
Resultado de reducción de FP se sostiene por sí solo.

### H3 — Causa raíz del bug (medida + memoria recuperada)
NO es "desconfianza deliberada en los clasificadores". Es residuo de una **crisis de
concurrencia (agosto 2025)**: 7 modelos petaban el pipeline con race conditions; se
recortó a 4; se hardcodearon cosas para estabilizar; el veredicto quedó colgando de L1 y
nunca se revirtió. Combinado con la restricción dura del proyecto: **clasificación
submilisegundo** (el pipeline debe clasificar como el rayo). Documentar como
`DEBT-VERDICT-MONOCAPA-001`: causa = fiabilidad de ransomware/ddos + concurrencia +
latencia submilisegundo.

### H4 — El clasificador INTERNAL está desconectado, y es el más grave
El clasificador `internal` (L3: lateral movement, exfiltración) NO compite en el `max`
y pierde — **ni siquiera llega al `max`**: corre en línea 780, después de que el
veredicto se fijó en 432. Es el peor caso porque:
- Es FIABLE (dataset de procedencia propia, ver H5).
- Ve las FASES DE RED del ransomware (exfil, lateral) — justo lo que un NDR sí puede ver.
- Un flujo que L1 marca BENIGN pero que `internal` detecta como exfiltración clara HOY
  sale BENIGN. Falso negativo estructural.

### H5 — Jerarquía de confianza por procedencia de datasets (criterio de Alonso, sólido)
- **Traffic (externo) e Internal: FIABLES.** Datasets generados por Alonso — un script
  recorrió internet capturando tráfico web normal; otro capturó tráfico interno normal.
  Ground truth propio y controlado.
- **Ransomware y DDoS: DUDOSOS.** Modelos de origen externo/incierto. Ransomware: features
  de host fabricadas con proxies (§2 auditoría). DDoS: 3 features constantes (§3).
- Corolario: un futuro ensemble debe construirse sobre señales fiables (L1 + traffic +
  internal), NO heredar la basura de ransomware/ddos. Un ensemble sobre features malas
  hereda features malas — la fuerza viene de la diversidad de señales FIABLES.

### H6 — Precisión sobre "fracaso de clasificadores" (corrige premisa de Alonso)
"Fracasamos en generar los clasificadores ransomware/ddos" mezcla TRES fallos distintos
que hay que separar antes de autoinculparse:
1. El **modelo** (¿mal entrenado? — NO medido aún, es el paso 0.2 / prueba de pulso).
2. El **adaptador de features** (proxies basura / constantes — SÍ medido, roto).
3. El **cableado del veredicto** (desconectado del `max` — SÍ medido, H1).
   Puede que el modelo esté bien y solo el adaptador/cableado estén rotos. No afirmar
   "fracaso de modelado" hasta medir el pulso (0.2).

### H7 — El extractor INTERNAL es 8/10 honesto, y sus 2 features clave son REALES
*Medido: `extract_level3_internal_features`, feature_extractor.cpp líneas 404–448.*

Contraste con los otros tres extractores (ransomware 9/10 proxies; ddos 3/10 constantes):
**el interno es el más sano de todos.**

Features HONESTAS (8) — fórmulas reales sobre campos reales de `nf`:
- `[0]` connection_rate = paquetes/duración.
- `[3]` packet_size_consistency = 1/packet_length_std.
- `[4]` connection_duration_std = duración real.
- **`[5]` lateral_movement_score = syn_rate × (1 − completion_rate)** — SYN altos, FIN
  bajos = escaneo lateral. Fórmula con sentido de dominio. ⭐ CLAVE para ransomware-red.
- `[6]` service_discovery = rst_flag_count (RST = scanning). Real.
- **`[7]` data_exfiltration = ratio bytes salientes/entrantes, umbral >2×** — lógica real,
  NO constante (el `?:` es umbral legítimo, no lógica muerta). ⭐ CLAVE para ransomware-red.
- `[8]` temporal_anomaly = std/mean de IAT. Real y sofisticada.
- `[9]` access_pattern_entropy = packet_length_std. Real.

Features CONSTANTES (2) — mismo pecado que el DDoS:
- `[1]` service_port_consistency = `1 − normalize(1,0,5)` = **0.8 fijo** (falta el dato de
  variedad de puertos en `NetworkFeatures`).
- `[2]` protocol_regularity = `1 − normalize(1,0,3)` = **0.667 fijo** (falta variedad de
  protocolo).

**Ranking de salud de extractores (medido):**
| Cabeza | Extractor | Veredicto |
|---|---|---|
| Internal (L3) | 8/10 honesto, 2 constantes, features clave REALES | **mejor candidato** |
| DDoS (L2) | 6/10 honesto, 3 constantes, features de peso reales | degradado, vivo |
| Traffic (L3) | NO auditado aún | ? |
| Ransomware (L2) | 1/10 real, 9/10 proxies de host | roto por diseño |

**Cambio estratégico:** el camino más corto a "ransomware-por-red" quizá NO sea entrenar
un modelo nuevo con datos MITRE (volumen incierto), sino **arreglar las 2 constantes del
interno + reconectarlo al veredicto (H4) + medir su pulso.** Base ya fiable (dataset
propio H5 + extractor sano H7). Mucho menos trabajo que un modelo desde cero.

**Límites epistémicos (NO sobrevender):**
1. Extractor sano ≠ clasificador que clasifica bien. Falta la prueba de pulso (0.2) sobre
   el interno: ¿separa clases sobre tráfico etiquetado? Necesario antes de declararlo útil.
2. Las 2 constantes pueden causar desajuste train/inference si el modelo se entrenó con
   valores reales de `[1]`/`[2]`. Ver feature importance del interno antes de confiar.



**H0:** El fast-path del sniffer realiza la mayor parte del trabajo de clasificación;
el ml-detector tricapa aporta menos de lo que el F1 agregado le atribuye. La cabeza de
ransomware, además, está inerte por desajuste de dominio.

**Por qué importa:** si H0 es cierta, entonces (a) desactivar la cabeza de ransomware
no altera el F1 porque el fast-path ya provee el veredicto, (b) el F1 del paper mide el
fast-path, no el tricapa, y (c) la conversación con Andrés cambia de "detector ML
tricapa" a "detector estadístico ligero en fast-path + ML como complemento medido".

**Origen histórico:** esta duda quedó abierta el 2025-12-08 (conversación "Validación
del pipeline"): "cuando agregamos el fast path, está calculando un score… ¿cuál tiene
prioridad cuando llega al firewall?". Nunca se cerró con medición. Este plan la cierra.

---

## FASE 0 — Mediciones que desbloquean todo lo demás
*(Precede a cualquier decisión de Q1-Q5. Empieza HOY.)*

### Paso 0.1 — Trazar la fusión fast-path × ml-detector (lectura de código)
**Objetivo:** responder las 4 preguntas abiertas desde 2025-12-08.
- ¿Cuántos campos de score existen en el protobuf (`fast_detector_score`,
  `ml_detector_score`, `overall_threat_score`)? — ya vistos en `make_event`, confirmar
  semántica y quién escribe cada uno.
- ¿El ml-detector LEE el score del fast-path, lo sobrescribe, o lo ignora?
- ¿Cómo se calcula `final_classification` / `overall_threat_score` — fórmula tricapa,
  máximo, prioridad del fast-path?
- ¿Qué score usa el firewall / qué fluye al circuito bronce→gold→Kuzu?
  **Ficheros a rastrear:** el `EngineVerdict`/`provenance` (ADR-002 multi-engine
  provenance), `ml-detector/src/main.cpp` (fusión), el fast-path del sniffer
  (`sniffer/src/userspace/ring_consumer.cpp`, `fast_detector.hpp`).
  **Comando zsh correcto (lección: comillas en los globs):**
```
grep -rn --include='*.cpp' --include='*.hpp' "final_classification\|overall_threat_score\|provenance\|EngineVerdict" ml-detector/src sniffer/src -l
```
**Entregable:** diagrama de flujo del veredicto: quién escribe qué campo, quién gana.
**Estado:** este paso es DECIDIBLE hoy — es lectura. Bloquea Q1.

### Paso 0.2 — Prueba de pulso del detector de ransomware (aislado)
**Objetivo:** ¿el output varía con el input, o está clavado? Inercia empírica sin
necesitar ransomware etiquetado.
**Método:** harness que llame a `RansomwareDetector::predict` sobre las N filas del
CTU-13 que ya existen (Neris benigno + botnet), y grafique la distribución de
`ransomware_prob`.
- Distribución **degenerada** (scores apelotonados, no responden al input) → inercia
  PROBADA. H0 confirmada en esta parte.
- Distribución **dispersa** → "inerte" es la palabra equivocada; Q1 se replantea.
  **A VERIFICAR ANTES (no asumir):** firma exacta de `predict`, cómo se construye
  `Features` desde datos reales, si el harness puede reusar `test_ransomware_detector_unit`
  que ya existe en `ml-detector/tests/`.
  **Entregable:** histograma de scores + veredicto (degenerado/disperso).
  **Coste:** ~media hora si el harness reusa el test unitario existente.

### Paso 0.3 — Ablación de atribución del F1 (la medición clave)
**Objetivo:** ¿el F1 histórico mide el fast-path o el ml-detector? Ataca la duda raíz.
**Método:** replay CTU-13 Neris en TRES configuraciones, midiendo F1 + matriz de
confusión en cada una:
- **(a)** fast-path solo, ml-detector desactivado.
- **(b)** ml-detector solo, fast-path en passthrough (sin veredicto propio).
- **(c)** ambos (configuración actual / la del paper).
  **Interpretación:**
- Si F1(a) ≈ F1(c) y F1(b) ≪ ambos → **el fast-path hace el trabajo**. H0 confirmada.
  El F1 histórico medía el fast-path.
- Si F1(b) ≈ F1(c) → el ml-detector sí clasifica; H0 refutada en esta parte.
- Casos intermedios → cuantifican la contribución real de cada uno.
  **A VERIFICAR ANTES (no asumir):** ¿existe un modo "passthrough" del ml-detector, o
  hay que crearlo? ¿el fast-path se puede desactivar por config sin recompilar? ¿hay
  ground-truth etiquetado del Neris (147.32.84.165, 646 flows) reutilizable del
  experimento Suricata/Zeek?
  **Precedente favorable:** Grok (bando aprobador) ya pidió "corrida con ransomware
  activado vs desactivado para cuantificar la contaminación". Este paso lo generaliza.
  **Entregable:** tabla F1/precision/recall × 3 configuraciones + interpretación.
  **Nota:** este es el paso que puede tocar las claims del paper. Máxima prioridad
  dentro de Fase 0.

---

## FASE 1 — Lo unánime y seguro (9/9 del Consejo)
*(Sin dependencias. Ejecutable en paralelo a Fase 0. Rama de docs/DEBT, sin EMECAS+++.)*

### Paso 1.1 — DEBT + borrado del `proto_aligned`
- Crear `DEBT-RANSOMWARE-PROTO-ALIGNED-DEAD-001`: origen (intento de detector de red),
  causa de fallo (45 features anónimas `feature_0..feature_44`, `direct_conversion`,
  sin contrato), razón de abandono, referencia al commit original.
- `git rm` (NUNCA `rm`) de los artefactos en
  `models/production/level3/ransomware/*proto_aligned*`.
- Referenciar el DEBT en el mensaje de commit.
  **Consenso:** 9/9, incluidos los dos adversarios.

### Paso 1.2 — DEBT del DDoS constantes (sin acción)
- Crear `DEBT-DDOS-FEATURES-CONSTANT-001`: features [2] (`normalize(1.0f)` const),
  [3] (`(1.0f>5)` const-false por compilación), [7] (`0.5f` placeholder). Análisis:
  líneas 224-264 de `feature_extractor.cpp`. Impacto: degradación menor. Prioridad: baja.
- Comentario en código: `// DEBT-DDOS-FEATURES-CONSTANT-001: placeholder, pending` (GLM).
- NO desactivar el DDoS. NO asignar recursos. Revisar post-FEDER.
  **Consenso:** 9/9.

---

## FASE 2 — Q1 (desactivar cabeza ransomware) informada por medición
*(Depende de Fase 0. NO ejecutar antes.)*

### Paso 2.1 — Decisión del ADR según resultado de 0.1+0.2+0.3
- Si pulso degenerado (0.2) Y fast-path decide (0.3): escribir ADR de desactivación
  con evidencia: "desactivado, medido inerte, sin efecto en F1 porque el fast-path
  provee el veredicto". El 7-2 del Consejo se vuelve 9-0 legítimo.
- Si pulso disperso: NO escribir el ADR de defunción. Hallazgo que reabre Q1 → nueva
  ronda de Consejo.
  **Regla dura:** no firmar el certificado de defunción antes del pulso. Terreno común
  adversario (ChatGPT Ataque 3 + Claude síntesis).

### Paso 2.2 — Lenguaje del ADR (sobrevive a cualquier resultado)
- NO "irrescatable", NO "alucina". SÍ: "con la arquitectura actual y solo
  `NetworkFeatures`, no hay camino viable identificado; nivel de confianza: [X] según
  medición 0.2" (reformulación de ChatGPT).
- Incluir el radio de explosión medido en 0.1: qué le pasa al `final_classification`
  del circuito bronce→gold→Kuzu al desactivar. Si el fast-path rellena el hueco, decirlo.

---

## FASE 3 — Q4 reformulada (aportación adversaria ignorada por los 7)
*(Deliberación de Consejo, no bloquea Fases 0-2.)*

### Paso 3.1 — Llevar la tercera opción al Consejo
Junto a Opción A (modelo de red) y B (híbrido red+host), añadir la de ChatGPT:
- **Opción C — scorer de técnicas ATT&CK**: dejar de modelar "ransomware" como clase
  binaria. Modelar técnicas (Discovery T1046, C2 T1071, Lateral T1021, Exfil T1048).
  "Ransomware" pasa a ser inferencia de nivel superior que combina evidencias.
- Encaja con la arquitectura multicapa mejor que un clasificador monolítico. Gemini
  mencionó que ya existe un "modelo de probabilidad multi-señal" — terreno preparado.
- Requiere ADR propio. Decisión de Consejo, no de sesión.

---

## FASE 4 — MITRE / Atomic Red Team (aprobada 9/9, con cautelas de los 2)
*(Diseño, no bloquea. Depende de que Fase 0 aclare si genera datos de entrenamiento.)*

### Paso 4.1 — Medir la huella de red de un atomic ANTES de prometerlo como training
- Ejecutar un atomic de C2 (T1071) desde `client`, contar flujos/paquetes en `eth1`.
- Si son decenas (no miles): Atomic Red Team es fuente de VALIDACIÓN, no de
  ENTRENAMIENTO. Cambia lo que se le promete a Andrés y condiciona la Opción A de Q4.
  **Cautela de ChatGPT + Claude, ignorada por los 7 aprobadores.**

### Paso 4.2 — Diseño de la matriz con la aserción de silencio NDR
- Matriz técnica ATT&CK × sensor (aRGus con cabezas activables, Suricata, Zeek, Wazuh)
  × componente. Topología CTU-13: `client` inyecta, `defender` observa.
- **Aserción clave (GLM):** durante el atomic de cifrado (T1486), los tres NDR DEBEN
  callar. Si alguno dispara por ruido de protocolo del atomic, el experimento se
  contamina. El silencio de los NDR ante el cifrado ES el resultado que valida la tesis.
- Incluir corrida con cabeza ransomware activada vs desactivada (Grok) para cuantificar
  contaminación actual.

---

## Orden de ejecución y dependencias

```
HOY, en paralelo:
  Fase 0.1 (lectura, decidible ya) ──┐
  Fase 1.1 + 1.2 (unánime, sin deps) │
                                     │
Tras 0.1:                            │
  Fase 0.2 (pulso) ──────────────────┤
  Fase 0.3 (ablación F1) ────────────┤ ← paso que puede tocar el paper
                                     │
Tras Fase 0 completa:                │
  Fase 2 (ADR Q1 con evidencia) ◄────┘

No bloqueantes (deliberación/diseño):
  Fase 3 (Q4 reformulada → Consejo)
  Fase 4 (MITRE: medir huella + diseñar matriz)

INTOCABLE, independiente:
  EMECAS+++ de test_flujo_a_b_equivalence → merge a main (fin de día)
```

## FASE 5 — Derivados de los hallazgos H1–H6 (nuevos, DAY 209)

### Paso 5.1 — ¿Activa NERIS el clasificador interno? (medible en minutos)
**Pregunta de Alonso:** ¿el pcap relay NERIS ejerce las features internas (lateral,
exfil), o es tráfico externo que no las toca?
**Método:** correr relay NERIS con el pipeline actual, luego
`grep 'SUSPICIOUS_INTERNAL\|internal' /vagrant/logs/lab/detector.log`. Si aparece, NERIS
lo activa (aunque su salida hoy no cuente para el veredicto — H4). Si no, NERIS no
ejerce las features internas y hace falta otra fuente (MITRE).
**Valor:** dice si ya tenemos una fuente de datos internos, o si MITRE es imprescindible.

### Paso 5.2 — Auditar `extract_level3_internal_features` — ✅ HECHO (ver H7)
**Resultado:** 8/10 features honestas, 2 constantes (`[1]`, `[2]`), y las dos features
clave para ransomware-por-red (`[5]` lateral, `[7]` exfil) son REALES. Mejor extractor de
los cuatro. Abre tres mediciones nuevas:

- **5.2a — Feature importance del modelo interno:** ¿cuánto pesan las 2 constantes
  (`[1]`,`[2]`)? Si pesan poco, las constantes casi no dañan. Si pesan mucho, hay
  desajuste train/inference. (Buscar el metadata/JSON del modelo interno, como se hizo
  con el ransomware.)
- **5.2b — Pulso del interno (0.2 aplicado al interno):** ¿su distribución de scores
  separa clases sobre tráfico etiquetado? Extractor sano ≠ clasificador bueno.
- **5.2c — Auditar el extractor de Traffic** (`extract_level3_traffic_features`, ~línea
  347): el único de los cuatro sin auditar. Completa el ranking.

**Cambio de estrategia que H7 habilita:** evaluar RECONECTAR el interno al veredicto
(arreglar `[1]`/`[2]` + meterlo en el `max` o en un ensemble) como alternativa más barata
a entrenar un ransomware nuevo desde cero. Decisión de Consejo (toca el veredicto de
producción — radio de explosión al circuito bronce→gold, como en Q1).

### Paso 5.3 — Encuadre correcto de MITRE (corrige expectativa)
**MITRE/Atomic Red Team NO arregla clasificadores. Genera tráfico etiquetado.** Es
materia prima, no método de entrenamiento ni modelo. Con su telemetría se PUEDE entrenar
un clasificador nuevo, pero:
- **Medir volumen ANTES de prometerlo como training** (paso 4.1): un atomic de C2 puede
  ser un `curl` → decenas de flujos, no los miles que exige entrenar.
- **¿Está aRGus preparado para capturar esa telemetría?** Depende de 5.2: si el extractor
  interno es honesto, sí captura lateral/exfil. Si es basura como el de ransomware, hay
  que arreglarlo primero, o confiar en la telemetría de Suricata/Zeek/**Wazuh** para la
  matriz de ablación.
  **Sobre ensemble (idea de Alonso):** viable, pero solo sobre señales fiables (L1 +
  traffic + internal, H5). Un ensemble de regresión da OK/KO claro (lo que se necesita),
  pero hereda la calidad de sus entradas: basura dentro, basura fuera.

### Paso 5.4 — Actualizar el paper (DECISIÓN TOMADA, H2)
- Reescribir la sección de arquitectura/validación: de "tricapa detecta" a "fast-path +
  L1 validan, reducción FPR ~15.500×, cabezas L2/L3 = enriquecimiento".
- Reconocer el bug explícitamente (`DEBT-VERDICT-MONOCAPA-001`), con los ficheros del
  repo como evidencia. Honestidad epistémica: describir lo que el código HACE.
- Causa documentada: fiabilidad ransomware/ddos + concurrencia (ago 2025) + latencia
  submilisegundo.
- Camino A (pre-FEDER): corregir narrativa. Camino B (post-FEDER): integrar las 4 cabezas
  en el veredicto, re-medir. NO hacer B antes del FEDER.

---

## Criterios de parada
- Se avanza secuencialmente hasta agotar los pasos ejecutables o hasta bloquearse por
  una medición que requiera datos aún inexistentes (p. ej. 0.3 puede necesitar crear un
  modo passthrough; 4.1 debe preceder a prometer training data).
- Cada "A VERIFICAR ANTES" es un punto donde NO se inventa: se mide o se pregunta.

---

*Via Appia Quality — medir quién clasifica, no solo cómo de bien. Un escudo que audita
sus propias mediciones.*