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
---

## Resumen en una frase

El veredicto de producción es **`max(fast_path, L1)`**. Las cuatro cabezas
especializadas (DDoS, ransomware, traffic, interno) **se ejecutan y rellenan
`ml_analysis`, pero su salida NO entra en `overall_threat_score`**. No es
"monocapa" ni "cabezas muertas": es **bicapa en el veredicto, tetracapa en la
telemetría**.

---

## Correcciones a hipótesis previas (dejar constancia, para no repetir el error)

1. **La sobrescritura de DAY 11–12 YA NO EXISTE.** En algún punto se arregló.
   `zmq_handler.cpp:352` lee `fast_detector_score()`, `:410` hace
   `std::max(fast_score, ml_score)`, `:411` `set_overall_threat_score(final_score)`.
   El fast-path se preserva; no se pisa. La vieja hipótesis "el ML sobrescribe el
   score" está obsoleta.

2. **Las cuatro cabezas SÍ se invocan** (corrige una hipótesis intermedia de esta
   misma sesión, que las daba por no ejecutadas). Ejecución confirmada:
  - DDoS — línea 558 (`ddos_detector_->predict`, 596)
  - Ransomware — línea 626 (`ransomware_detector_->predict`, 665)
  - Traffic — línea 697 (`traffic_detector_->predict`, 733)
  - Interno — línea 756 (`internal_detector_->predict`, 780)
    Todas predicen y hacen `add_level2/3_specialized_predictions()` sobre `ml_analysis`.

---

## Los DOS defectos apilados de `DEBT-VERDICT-MONOCAPA-001`

### Defecto A — Secuencia (el veredicto se sella demasiado pronto)
- Línea 408: `double ml_score = label_l1 == 1 ? confidence_l1 : (1.0 - confidence_l1);`
  → **`ml_score` ES L1 y solo L1.** Comentario del código: *"Dual-Score Architecture"*
  (el propio autor documentó que aquí hay dos scores, no tres).
- Línea 410: `final_score = std::max(fast_score, ml_score);`
- Línea 411: `set_overall_threat_score(final_score);` → **veredicto sellado aquí.**
- Las cabezas 2/3/4 corren en 558–802, **150 líneas después**, y solo escriben en
  `ml_analysis`. Ninguna vuelve a tocar `overall_threat_score`.
- **Efecto:** las tres cabezas especializadas son *observadores que escriben un
  informe que nadie lee para decidir* (el "observador silencioso" del Consejo DAY 81,
  ahora fosilizado y en contradicción con el paper).

### Defecto B — Gate (causa raíz; es H4 hecho código)
- Línea 552: `if (label_l1 == 1 && confidence_l1 >= config_.ml.thresholds.level1_attack) {`
  → **las cuatro especializadas solo corren si L1 dijo ATTACK.** L1 es un *gate*, no
  un compañero de ensemble.
- **Falso negativo estructural:** un flujo que el interno vería clarísimo como
  exfiltración/lateral, pero que L1 (genérico, CICIDS2017) marca BENIGN, **sale BENIGN
  y el interno nunca llega a ejecutarse.** La cabeza fiable (H5/H7) está subordinada a
  la cabeza que menos sabe de las fases de red del ransomware.

### Consecuencia crítica para el plan
**Mover el punto de veredicto (arregla A) NO arregla B.** Si las cabezas fiables
siguen bajo `if L1==ATTACK`, la mejor fórmula de combinación no ve los flujos que L1
se traga. **B condiciona A** y hay que decidirlo primero.

---

## Detalle de arquitectura que valida la tesis (cascada existente)

- Línea 749: `if (traffic_result.is_internal(...) && internal_detector_ && ...)`
  → el **interno solo corre si traffic dice que el flujo es interno**. Está anidado
  dentro de traffic (697 → 748 → 756).
- Flujo real: **L1 general → traffic decide dominio → interno mira dentro.** Es *casi*
  la tricapa que promete el paper, salvo que la salida de la cascada nunca sube al `max`.
  La estructura jerárquica existe en ejecución; **falta el cable de vuelta al veredicto.**

---

## DEBT nuevo detectado hoy

### `DEBT-RAG-ATTACKFAMILY-HARDCODED-001` (P2 — anotar antes de que contamine)
- Línea 505: `ml_context.attack_family = "RANSOMWARE";  // TODO: Get from detector`
- **Todo lo que se registra en el RAG sale etiquetado "RANSOMWARE"**, sea lo que sea.
- Riesgo: si el RAG entra en el circuito de reentrenamiento o se usa como fuente de
  verdad para inspeccionar clasificaciones, la etiqueta es basura constante.
- Fix: sacar `attack_family` del detector que realmente disparó (una vez B esté resuelto,
  la cabeza ganadora ya se conoce).

---

## Activo aprovechable (no partimos de cero)

- Bloque 414–424: la lógica de `authoritative_source`
  (`DIVERGENCE` / `CONSENSUS` / `FAST_PRIORITY` / `ML_PRIORITY`) **ya razona sobre
  fast vs ml** y escribe `decision_metadata` de trazabilidad. Es el germen de la lógica
  de combinación: pensada para dos fuentes, extensible a cinco. La parte de provenance
  (`add_verdicts`, `discrepancy_score`) también existe ya.

---

## Orden de trabajo corregido (reemplaza el mapa "cuatro tareas de cablear")

Las invocaciones YA existen con features, umbrales de config y predicción. Las
probabilidades ya están calculadas y colgando en variables vivas dentro de la función:
`ddos_result.ddos_prob`, `ransomware_result.ransomware_prob`, `internal_result.suspicious_prob`,
`traffic_result`. **Reconectar = recogerlas y meterlas en la combinación, no reescribir
la extracción.**

1. **Decidir el gate (Defecto B) ANTES que la fórmula (Defecto A).**
   Pregunta que lo decide, medible: correr **interno + traffic incondicionalmente**
   (en todos los flujos, no solo los que L1 marca ATTACK), ¿cabe en el presupuesto de
   **<10 ms** recepción→clasificación→firewall?
  - Esto convierte 5.2b en una medición doble: *(i)* ¿el interno separa clases sobre
    tráfico etiquetado? *(ii)* ¿cuánto cuesta dejarlo suelto de L1?

2. **Mover el punto de veredicto** de la línea 410 a *después* de 802, cuando las
   cabezas ya han hablado. Reordenamiento de flujo, no lógica nueva.

3. **Sustituir `max(fast, ml_score)` por combinación NO-SUPRESORA** sobre las cinco
   señales. Operador acordado: **noisy-OR**
   `P = 1 − ∏(1 − pᵢ)`, con `pᵢ_efectivo = fiabilidad_i · score_crudo_i`.
  - Monótono (nadie suprime a nadie), corroboración incorporada (ransomware + interno
    se refuerzan), siempre ≥ que el `max` (fast-path domina cuando dispara).
  - **Pesos = fiabilidad MEDIDA, no votada** ("medir no votar"): salen de 5.2b y del
    F1 por cabeza, no de intuición.
  - Fiabilidades provisionales conocidas: interno y traffic ALTAS (H5/H7); ransomware
    y ddos ≈0 hasta medir/reconstruir (features rotas). Una cabeza con fiabilidad ≈0
    aporta `pᵢ≈0` y **no puede envenenar** aunque siga capturando telemetría.

---

## Punto de entrada para la próxima sesión

**5.2b (pulso del interno) sigue siendo el paso que decide más con menos** — ahora
decide DOS cosas: si el interno clasifica bien Y si puede correr desacoplado de L1.
Sin resolver el gate (B), reordenar la fórmula (A) es cosmético.

---

## Impacto en el paper (arXiv:2604.04952)

El paper afirma tricapa + recogida de todas las señales. La realidad es
**fast-path ⊕ L1** en el veredicto. Este bloque (líneas 408–411 vs 552) es la prueba
literal que justifica `DEBT-VERDICT-MONOCAPA-001` → corregir arXiv. No es simplificar
la redacción: dos de los tres niveles no influyen en el score final.

# DAY 210 — Auditoría del cableado del veredicto (cierre diagnóstico de `DEBT-VERDICT-MONOCAPA-001`)

> Anexar esta sección al PLAN DE CAMPAÑA local. Fichero auditado:
> `ml-detector/src/zmq_handler.cpp`. Números de línea del estado del repo a DAY 210
> (`/Users/aironman/CLionProjects/test-zeromq-docker/`).

---

## Resumen en una frase

El veredicto de producción es **`max(fast_path, L1)`**. Las cuatro cabezas
especializadas (DDoS, ransomware, traffic, interno) **se ejecutan y rellenan
`ml_analysis`, pero su salida NO entra en `overall_threat_score`**. No es
"monocapa" ni "cabezas muertas": es **bicapa en el veredicto, tetracapa en la
telemetría**.

---

## Correcciones a hipótesis previas (dejar constancia, para no repetir el error)

1. **La sobrescritura de DAY 11–12 YA NO EXISTE.** En algún punto se arregló.
   `zmq_handler.cpp:352` lee `fast_detector_score()`, `:410` hace
   `std::max(fast_score, ml_score)`, `:411` `set_overall_threat_score(final_score)`.
   El fast-path se preserva; no se pisa. La vieja hipótesis "el ML sobrescribe el
   score" está obsoleta.

2. **Las cuatro cabezas SÍ se invocan** (corrige una hipótesis intermedia de esta
   misma sesión, que las daba por no ejecutadas). Ejecución confirmada:
  - DDoS — línea 558 (`ddos_detector_->predict`, 596)
  - Ransomware — línea 626 (`ransomware_detector_->predict`, 665)
  - Traffic — línea 697 (`traffic_detector_->predict`, 733)
  - Interno — línea 756 (`internal_detector_->predict`, 780)
    Todas predicen y hacen `add_level2/3_specialized_predictions()` sobre `ml_analysis`.

---

## Los DOS defectos apilados de `DEBT-VERDICT-MONOCAPA-001`

### Defecto A — Secuencia (el veredicto se sella demasiado pronto)
- Línea 408: `double ml_score = label_l1 == 1 ? confidence_l1 : (1.0 - confidence_l1);`
  → **`ml_score` ES L1 y solo L1.** Comentario del código: *"Dual-Score Architecture"*
  (el propio autor documentó que aquí hay dos scores, no tres).
- Línea 410: `final_score = std::max(fast_score, ml_score);`
- Línea 411: `set_overall_threat_score(final_score);` → **veredicto sellado aquí.**
- Las cabezas 2/3/4 corren en 558–802, **150 líneas después**, y solo escriben en
  `ml_analysis`. Ninguna vuelve a tocar `overall_threat_score`.
- **Efecto:** las tres cabezas especializadas son *observadores que escriben un
  informe que nadie lee para decidir* (el "observador silencioso" del Consejo DAY 81,
  ahora fosilizado y en contradicción con el paper).

### Defecto B — Gate (causa raíz; es H4 hecho código)
- Línea 552: `if (label_l1 == 1 && confidence_l1 >= config_.ml.thresholds.level1_attack) {`
  → **las cuatro especializadas solo corren si L1 dijo ATTACK.** L1 es un *gate*, no
  un compañero de ensemble.
- **Falso negativo estructural:** un flujo que el interno vería clarísimo como
  exfiltración/lateral, pero que L1 (genérico, CICIDS2017) marca BENIGN, **sale BENIGN
  y el interno nunca llega a ejecutarse.** La cabeza fiable (H5/H7) está subordinada a
  la cabeza que menos sabe de las fases de red del ransomware.

### Consecuencia crítica para el plan
**Mover el punto de veredicto (arregla A) NO arregla B.** Si las cabezas fiables
siguen bajo `if L1==ATTACK`, la mejor fórmula de combinación no ve los flujos que L1
se traga. **B condiciona A** y hay que decidirlo primero.

---

## Detalle de arquitectura que valida la tesis (cascada existente)

- Línea 749: `if (traffic_result.is_internal(...) && internal_detector_ && ...)`
  → el **interno solo corre si traffic dice que el flujo es interno**. Está anidado
  dentro de traffic (697 → 748 → 756).
- Flujo real: **L1 general → traffic decide dominio → interno mira dentro.** Es *casi*
  la tricapa que promete el paper, salvo que la salida de la cascada nunca sube al `max`.
  La estructura jerárquica existe en ejecución; **falta el cable de vuelta al veredicto.**

---

## DEBT nuevo detectado hoy

### `DEBT-RAG-ATTACKFAMILY-HARDCODED-001` (P2 — anotar antes de que contamine)
- Línea 505: `ml_context.attack_family = "RANSOMWARE";  // TODO: Get from detector`
- **Todo lo que se registra en el RAG sale etiquetado "RANSOMWARE"**, sea lo que sea.
- Riesgo: si el RAG entra en el circuito de reentrenamiento o se usa como fuente de
  verdad para inspeccionar clasificaciones, la etiqueta es basura constante.
- Fix: sacar `attack_family` del detector que realmente disparó (una vez B esté resuelto,
  la cabeza ganadora ya se conoce).

---

## Activo aprovechable (no partimos de cero)

- Bloque 414–424: la lógica de `authoritative_source`
  (`DIVERGENCE` / `CONSENSUS` / `FAST_PRIORITY` / `ML_PRIORITY`) **ya razona sobre
  fast vs ml** y escribe `decision_metadata` de trazabilidad. Es el germen de la lógica
  de combinación: pensada para dos fuentes, extensible a cinco. La parte de provenance
  (`add_verdicts`, `discrepancy_score`) también existe ya.

---

## Orden de trabajo corregido (reemplaza el mapa "cuatro tareas de cablear")

Las invocaciones YA existen con features, umbrales de config y predicción. Las
probabilidades ya están calculadas y colgando en variables vivas dentro de la función:
`ddos_result.ddos_prob`, `ransomware_result.ransomware_prob`, `internal_result.suspicious_prob`,
`traffic_result`. **Reconectar = recogerlas y meterlas en la combinación, no reescribir
la extracción.**

1. **Decidir el gate (Defecto B) ANTES que la fórmula (Defecto A).**
   Pregunta que lo decide, medible: correr **interno + traffic incondicionalmente**
   (en todos los flujos, no solo los que L1 marca ATTACK), ¿cabe en el presupuesto de
   **<10 ms** recepción→clasificación→firewall?
  - Esto convierte 5.2b en una medición doble: *(i)* ¿el interno separa clases sobre
    tráfico etiquetado? *(ii)* ¿cuánto cuesta dejarlo suelto de L1?

2. **Mover el punto de veredicto** de la línea 410 a *después* de 802, cuando las
   cabezas ya han hablado. Reordenamiento de flujo, no lógica nueva.

3. **Sustituir `max(fast, ml_score)` por combinación NO-SUPRESORA** sobre las cinco
   señales. Operador acordado: **noisy-OR**
   `P = 1 − ∏(1 − pᵢ)`, con `pᵢ_efectivo = fiabilidad_i · score_crudo_i`.
  - Monótono (nadie suprime a nadie), corroboración incorporada (ransomware + interno
    se refuerzan), siempre ≥ que el `max` (fast-path domina cuando dispara).
  - **Pesos = fiabilidad MEDIDA, no votada** ("medir no votar"): salen de 5.2b y del
    F1 por cabeza, no de intuición.
  - Fiabilidades provisionales conocidas: interno y traffic ALTAS (H5/H7); ransomware
    y ddos ≈0 hasta medir/reconstruir (features rotas). Una cabeza con fiabilidad ≈0
    aporta `pᵢ≈0` y **no puede envenenar** aunque siga capturando telemetría.

---

## Punto de entrada para la próxima sesión

**5.2b (pulso del interno) sigue siendo el paso que decide más con menos** — ahora
decide DOS cosas: si el interno clasifica bien Y si puede correr desacoplado de L1.
Sin resolver el gate (B), reordenar la fórmula (A) es cosmético.

---

## Impacto en el paper (arXiv:2604.04952)

El paper afirma tricapa + recogida de todas las señales. La realidad es
**fast-path ⊕ L1** en el veredicto. Este bloque (líneas 408–411 vs 552) es la prueba
literal que justifica `DEBT-VERDICT-MONOCAPA-001` → corregir arXiv. No es simplificar
la redacción: dos de los tres niveles no influyen en el score final.

---

## Decisión de alcance de la rama `fix/verdict-multihead-honest` (DAY 210 → 211)

**Opción elegida: reconectar las CUATRO cabezas al veredicto, con ransomware y ddos
entrando con peso ≈0 (fiabilidad medida), y su arreglo real DIFERIDO a post-FEDER.**

Razón: "honesto" ≠ "las cuatro fiables". Un clasificador es honesto cuando el veredicto
usa cada señal según su fiabilidad medida y el paper describe exactamente eso — lo que
incluye una cabeza con fiabilidad ≈0 entrando con peso ≈0. Meter "las cuatro fiables"
como precondición de la rama sería recomprometerse con el Camino B (reentrenar
ransomware/ddos contra ground truth de red), que NO cabe antes del go/no-go del 1-ago.
La opción honesta y entregable es: **usar las cuatro, pesarlas por lo que valen medido,
y decir en el paper que dos aún no valen mucho.**

**La puerta queda abierta por construcción.** Reconectar ransomware/ddos ya arreglados
post-FEDER = cambiar un peso de ≈0 a su valor medido. Una línea de config por cabeza. No
reabre la arquitectura, no toca el cableado del veredicto, no es un segundo
`DEBT-VERDICT`. El hueco donde entrarán las cabezas buenas queda construido y esperando.
Esta opción es precisamente la que MÁS abierta deja la puerta.

---
# DAY 216 — LA MEDICIÓN QUE FALSIFICA H5 Y H7

> Anexar al PLAN DE CAMPAÑA. **Este anexo no añade hallazgos al plan: retira dos de sus
> pilares.** Evidencia completa en `docs/debt/DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001.md`.

---

## Resumen en una frase

**El extractor de features del ml-detector está roto, y las tres cabezas que el plan daba
por fiables no clasifican nada.** El modelo L1 es perfecto sobre CIC-IDS2017 (200/200 DDoS,
0/200 FP, verificado hoy contra el ONNX de producción); el pipeline en ejecución detecta
**0 de 100 ataques sintéticos**. La brecha está en `ml-detector/src/feature_extractor.cpp`:
**6 de las 23 features de L1 son incorrectas** (duplicadas, o constantes a `0.0f`).

---

## 1. H5 QUEDA FALSIFICADA

> *H5 — "Traffic (externo) e Internal: **FIABLES**. Datasets generados por Alonso… Ground
> truth propio y controlado. Corolario: un futuro ensemble debe construirse sobre señales
> fiables (L1 + traffic + internal)."*

**Medido en ejecución, 200 eventos (100 ruido uniforme + 100 ataque DDoS sintético):**

| cabeza | ruido | ataque | veredicto |
|---|---|---|---|
| **L1** | class1=0, conf∈[0.74,0.88] | class1=0, conf∈[0.83,0.86] | 🔴 **CONSTANTE.** No reacciona. Y la conf está *más concentrada* en ataque que en ruido. |
| **internal** | class1=**69**, susp∈[0.72,0.85] | class1=**0**, susp∈[0.097,0.14] | 🔴 **INVERTIDA.** Dispara en ruido, calla en ataque. |
| **traffic** | 100/100, `internal_prob` ∈ {0.955, 0.96, 0.97} | 100/100, ∈ {0.96, 0.965} | 🔴 **CONSTANTE.** σ≈0.005 en 200 eventos de poblaciones opuestas. |

**Las tres señales que H5 llamaba fiables no llevan señal.** El ensemble que el plan
propone construir sobre "L1 + traffic + internal" se construiría sobre nada.

⚠️ **La procedencia del dataset no garantiza la fiabilidad del clasificador en ejecución.**
H5 razonaba sobre el origen de los *datos de entrenamiento*; el fallo está en el *puente*
entre el paquete y el modelo. Un dataset impecable no salva un extractor roto. Esta es la
lección epistémica de DAY 216, y es exactamente el error que H6 advirtió que no cometiéramos
(ver §3).

---

## 2. H7 QUEDA FALSIFICADA — el extractor "8/10 honesto" no era el que corre

> *H7 — "el interno es el más sano de todos… `[5]` lateral_movement_score y
> `[7]` data_exfiltration son REALES. ⭐ CLAVE."*

**Hay DOS extractores distintos y la auditoría de DAY 209 miró el que no corre:**

- `sniffer/src/userspace/feature_extractor.cpp` → 83 features CIC-IDS2017.
- **`ml-detector/src/feature_extractor.cpp` → reconstruye las features desde el PROTOBUF.
  ES EL QUE CORRE EN PRODUCCIÓN. ES EL ROTO.**

Y en el que corre, la cabeza interna tiene **más constantes de las que H7 contó**:

```cpp
:383  features[6] = normalize(1.0f, 0.0f, 10.0f);          // → 0.1 SIEMPRE
:386  features[7] = 1.0f - normalize(1.0f, 0.0f, 10.0f);   // → 0.9 SIEMPRE
```

⚠️ **`features[7]` es `data_exfiltration_indicators` — la feature que H7 marcó con ⭐ como
"REAL, ratio bytes salientes/entrantes, CLAVE para ransomware-por-red". En el extractor que
corre es la constante `0.9`.** Y `zmq_handler.cpp:415` la loguea como
`"exfil={:.3f}"` en el mensaje de "hueco de cobertura L3". **El indicador de exfiltración
del que dependía la estrategia entera no mide nada.**

⟹ **El "cambio estratégico" de H7** (*"el camino más corto a ransomware-por-red es arreglar
las 2 constantes del interno + reconectarlo"*) **queda sin base.** No son 2 constantes: la
cabeza está ciega.

---

## 3. H6 QUEDA VINDICADA — y era la advertencia correcta

> *H6 — "mezcla TRES fallos: (1) el modelo, (2) el adaptador de features, (3) el cableado.
> Puede que el modelo esté bien y solo el adaptador/cableado estén rotos. **No afirmar
> 'fracaso de modelado' hasta medir el pulso.**"*

**Es exactamente eso, y ahora está probado:**
- **(1) El modelo: SANO.** L1 da 200/200 sobre DDoS real de CIC-IDS2017, 0 FP, sin escalar.
  Su `f1_score=0.9968` declarado es cierto.
- **(2) El adaptador: ROTO.** 6/23 features incorrectas. Causa raíz.
- **(3) El cableado: era el frente de DAY 209–215** (monocapa, gate, hoist, noisy-OR). Correcto
  como diagnóstico, pero **irrelevante mientras (2) esté roto.**

H6 fue la única hipótesis del plan que sobrevivió intacta. **La disciplina de separar los
tres fallos antes de autoinculparse es lo que ha permitido llegar aquí.**

---

## 4. FASE 0.3 (ablación del F1) — PRE-RESPONDIDA, y hay que decirlo

> *0.3 — "¿el F1 histórico mide el fast-path o el ml-detector?"*
> *Interpretación: si F1(a) ≈ F1(c) y F1(b) ≪ ambos → el fast-path hace el trabajo.*

**Con L1 ciego en el pipeline, la configuración (b) — ml-detector solo — no puede detectar
nada.** No hace falta correr la ablación para saber que `F1(b) ≈ 0`.

⟹ **H0 apunta a CONFIRMADA:** el fast-path hacía el trabajo. El `max(fast_score, ml_score)`
de `zmq_handler.cpp:410` se resolvía **siempre** por `fast_score`, porque `ml_score` es
`1 − confidence_l1` con `label_l1 = 0` **siempre** — un valor casi constante (~0.15).

⚠️ **NO dar esto por cerrado sin correr 0.3.** El razonamiento es sólido pero es inferencia,
no medición. **Correr la ablación DESPUÉS de arreglar el extractor** es lo que la convierte
en el resultado que el paper necesita: el F1 del ml-detector reparado, aislado, contra el
del fast-path.

⚠️ **Y la reducción de FPR "~15.500×" (DAY 83, citada en H2 y 5.4) hay que re-verificar de
dónde salió.** Si L1 en pipeline está ciego, ¿qué redujo esos FP? Puede que la medición
fuera del modelo aislado (correcta) y no del pipeline. **Es una claim del paper. Medirla.**

---

## 5. IMPACTO EN EL PAPER — el hallazgo se cuenta (coherente con H2 y DAY 215)

El paper reporta **F1=0.9985 / Recall=1.000** para aRGus NDR. Esos números salen de evaluar
**el modelo** contra el dataset, y **son ciertos** — los hemos reproducido hoy (200/200).
**Pero el pipeline en ejecución no los reproduce.** Es la brecha entre *"el modelo detecta"*
y *"el sistema detecta"*, y hay que declararla.

**Es el TERCER caso del mismo patrón**, y eso lo convierte en el argumento central de §6:

1. `entropy` del ransomware = varianza de longitud ÷ 100.000 (DEBT-RANSOMWARE-ML-HEAD-INERT-001).
2. `level3_web`/`level3_internal` nunca parseados del JSON (DAY 215, `8e03a264`).
3. **6/23 features de L1 duplicadas o constantes (DAY 216).**

**Tres instancias ⟹ no es mala suerte, es una CLASE de defecto**: *el pipeline funcionando,
produciendo números, sin significado*. Ninguna la cazó el testing convencional (13 tests
verdes, EMECAS+++ verde, libFuzzer 2.4M runs). Todas se cazaron **midiendo el verde en vez
de celebrarlo**. Ése es el resultado metodológico del paper, y ahora tiene tres casos con
`file:line`.

**Decisión Alonso (DAY 215, ratificada hoy):** se cuenta. *"Es mejor ser honesto que no
serlo; el paper cuenta cómo estamos construyendo esto tratando de ser buenos científicos."*
Un revisor que descubra la brecha por su cuenta hunde el trabajo; el autor que la mide, la
localiza, la publica y la arregla **demuestra lo que el paper afirma sobre método.**

---

## 6. REORDENACIÓN DEL PLAN — el extractor es P0 ABSOLUTO

**Decisión Alonso DAY 216:** *"No tiene sentido trabajar aguas abajo si aguas arriba tenemos
estos problemas. No pienso entregar nada que no esté bien fundamentado."*

### Lo que SE PARA

| trabajo | estado | razón |
|---|---|---|
| **Commit 2 — noisy-OR** | 🟡 **APARCADO** (stash intacto, header+tests `-Werror` verdes) | Combinar señales de cabezas sin señal = andamiaje sin edificio. |
| **`correlation_v2` / grafo** | 🟡 APARCADO | Fontanería para un grifo sin agua. |
| **DEBT-VERDICT-WEIGHTS-CALIBRATION-001** | 🔴 **INDECIDIBLE** | Con las 3 cabezas ciegas, `reliability` = 0.0 para las tres. Un noisy-OR de todo ceros es `P=0`. **No falta el instrumento: no hay nada que calibrar.** |
| **MITRE (Fase 4)** | 🟡 APARCADO, no cancelado | Imprescindible para fundamentar `reliability` por técnica. Pero **con las cabezas ciegas, MITRE tampoco mediría nada.** Va DESPUÉS del extractor. |

### Lo que SE HACE

**P0 — Reparar `ml-detector/src/feature_extractor.cpp`.**

1. **Auditar el protobuf**: ¿existen `Init_Win_bytes_forward`, `Subflow Fwd Bytes`,
   `act_data_pkt_fwd`? El comentario de `:142` (*"TODO: Añadir campo al protobuf si es
   crítico"*) dice que alguien ya lo sabía.
    - **Si NO existen** → subir al **sniffer**, que sí produce las 83 features de CIC-IDS2017.
      **El dato puede existir y estar perdiéndose en el camino al protobuf.**
2. **Reparar las 6 features de L1**, una a una, contra `rf_23_features.json`.
3. **Test de PROPIEDAD, no de espejo** (lección DAY 215):
   > *"N filas de CIC-IDS2017 → protobuf → extractor → ONNX reproducen la etiqueta del CSV."*
   **RED→GREEN obligatorio**: romper una feature a propósito debe ponerlo ROJO.
   Este test es la red que **nunca existió** — y es exactamente la que habría cazado esto.
4. **Repetir con `traffic` e `internal`.** Sus contratos NO EXISTEN:
   `internal_4_features.json` no está; los 5 `*_metadata.json` de
   `ml-detector/models/metadata/` están **a 0 bytes**; `ml-detector/config/feature_mapping.json`
   está **a 0 bytes**. **Toda la capa de metadatos son placeholders vacíos del 27-may.**
5. **Sólo entonces**: ablación 0.3, calibración de pesos, retomar commit 2, seguir aguas abajo.

### Lo que SOBREVIVE del trabajo de DAY 209–215

**Nada se tira.** El diagnóstico del cableado (monocapa, gate, hoist, `decide_l3_verdict`
puro, noisy-OR) **es correcto y sigue siendo necesario**. Simplemente estaba resolviendo el
problema #3 de H6 mientras el #2 seguía roto. Cuando las cabezas vean, el cableado ya está.

---

## 7. DEUDAS NUEVAS

- **`DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001`** (P0) — el hallazgo. Documento completo con
  evidencia reproducible y el script de CIC-IDS2017 íntegro.
- **`DEBT-STATS-E2E-COUNTERS-001`** (menor) — `check_e2e_pipeline.py` reporta
  `ml-detector: received 0 → 0` mientras los contadores internos cuentan 100 eventos
  procesados. Los contadores del snapshot mienten.
- **`rf_23_features.json` se contradice a sí mismo**: `usage_notes.normalization` dice que NO
  hace falta escalar; `validation.scaler_required` dice `true` y apunta a un
  `level1/scaler.json` **que no existe**. Su `_source` confiesa: *"Reconstructed from … and
  feature_extractor.cpp"* — **se documentó leyendo el código que debía validar. Circular.**
  (La prueba de §1 del DEBT resuelve la contradicción: **NO hace falta escalar.**)

---

## 8. CORRECCIÓN AL RELATO DE DAY 215 — antes de que llegue al paper

El prompt de DAY 215 afirma: *"`is_internal(0.0f)` → SIEMPRE true. Guard de traffic abierto:
TODO flujo era interno."*

**Es FALSO.** `traffic_detector.hpp:57`:
```cpp
bool is_internal(float threshold) const noexcept {
    return class_id == 1 && probability >= threshold;   // ← el && de CLASE siguió aplicándose
}
```
Con `threshold = 0`, la condición colapsa a `class_id == 1`. **Lo que se perdió no fue el
guard: fue el SUELO DE CONFIANZA.** Y como `probability` es la de la clase ganadora
(`traffic_detector.cpp:33-39`), en binario `class_id==1 ⟹ probability ≥ 0.5` — así que el
umbral real de 0.6 sólo mordía en `[0.5, 0.6)`. **Impacto estrecho, no total.**

La otra mitad del P0 **se sostiene entera**: `is_suspicious(1.09e27)` nunca fue true ⟹
`SUSPICIOUS_INTERNAL` jamás se selló. Eso sigue en pie, y es lo grave.

**Corregir ANTES de escribirlo.** Un revisor abre `traffic_detector.hpp:57` y ve el
`class_id == 1`. Sobrevender un hallazgo en un paper cuyo argumento **es** la honestidad
metodológica sería el peor sitio posible para exagerar.

---

## MÉTODO — lo que funcionó (DAY 216)

- **El contador que SEPARA hipótesis vale más que el que cuenta.** `dbg_l1_class1` vs
  `dbg_l1_gate_open`: sin los dos, *"el gate no se abre"* y *"L1 no detecta"* son
  indistinguibles — y son diagnósticos **opuestos**.
- **La tabla de lectura se escribe ANTES de ver el número.** Elimina el margen para
  interpretar a conveniencia. Se escribió, y el resultado **no fue ninguna de las hipótesis**.
- **Verificar el `.cpp`, no el comentario.** Tres veces esta sesión hubo que bajar al `.cpp`
  para confirmar lo que un comentario o un JSON afirmaban. Una de las tres, mentían.
- **Ir al artefacto que no puede mentir.** Metadata vacía, contrato circular, comentarios
  ambiguos ⟹ se leyó **el grafo del ONNX** y **el CSV de entrenamiento**. Fin de la discusión.
- **El verde hay que interrogarlo. Y el rojo también.** El gate L1 filtró 69 falsos positivos
  del interno. Eso es evidencia **EN CONTRA** de la posición de Alonso de DAY 215 (*"el gate
  es un vestigio"*) — y se anota igual. **No queremos tener razón: queremos medir.**
- **Corregir el relato cuando el dato lo contradice** (§8). Dos veces hoy: el `is_internal`
  del prompt de DAY 215, y la propia hipótesis del scaler (descartada por la prueba, no por
  argumento).
## Formulación honesta de la limitación para el paper (hueco de cobertura, NO divergencia predicha)

⚠️ **Corrección de un salto lógico a evitar en el paper.** Con ransomware y ddos pesando
≈0, esas dos cabezas **no entran en el veredicto**. Por tanto **no pueden *causar*
divergencia con Suricata/Zeek** — el veredicto de aRGus ni las mira (es noisy-OR de
fast-path, L1, interno y traffic).

Lo que producen las cabezas rotas **no es divergencia, es un hueco de cobertura**: aRGus
no tiene hoy un clasificador dedicado funcional para esas dos clases; su detección de
ransomware/ddos descansa en las OTRAS señales (heurístico del fast-path para ransomware,
que sí funciona; fases de red — lateral, exfil — que ve el interno).

**Por qué importa (sesgo de confirmación, tipo Q1):** escribir "veremos divergencias con
Suricata/Zeek *porque* nuestras dos cabezas son malas" es **pre-explicar** una divergencia
aún no medida con la causa que se tiene a mano. La divergencia entre los tres es
multicausal — Suricata dio F1=0.000 y Zeek F1=0.042 en Neris por razones de **paradigma**
(firma vs comportamiento), no por las cabezas de aRGus. Atribuir una divergencia observada
a la debilidad conocida, sin aislarla flujo a flujo, es agarrar la explicación cómoda en
vez de medir.

**Formulación que sí aguanta un Consejo adversario:**
- Declarar el **hueco de cobertura** como limitación: dos cabezas dedicadas no contribuyen
  al veredicto (peso ≈0 por fiabilidad medida); la detección de esas clases recae en
  fast-path + señales de fase de red; arreglo diferido a post-FEDER.
- Tratar cualquier divergencia con Suricata/Zeek como **hallazgo a reportar e investigar**,
  no como algo a explicar de antemano. Si al medir la divergencia se concentra en flujos
  ransomware/ddos, *entonces* hay evidencia para atribuirla — y es un resultado, no una
  excusa escrita antes de mirar.

**Regla de oro:** la limitación es una frase sobre **aRGus** ("aún no tenemos estas dos
cabezas"), NO una predicción sobre **la comparativa** ("por eso divergiremos"). La primera
es honestidad; la segunda es adivinar el resultado antes del experimento.