# DAY261 — Arqueología del contrato de features DDoS (hallazgos medidos)

**Propósito:** apoyo para `docs/continuity/PROMPT_CONTINUE_CLAUDE.md`.
Todo lo de aquí está MEDIDO en la sesión DAY261 salvo lo marcado **SOSPECHADO**.
Origen: sesión de arqueología para responder "¿cómo entrenar correctamente la
cabeza DDoS?". El plan previo (Fase 2 = features reales + labels) se refina con esto.

---

## El mapa: TRES contratos DDoS conviven en `protobuf/network_security.proto`

1. **`ddos_features = 100`** (repeated double, comentado "83 features") → **FANTASMA.**
   Único uso en producción: `sniffer/src/userspace/feature_logger.cpp` lo LEE para
   imprimir por pantalla. Nadie hace `set/add`. Nadie lo consume para inferir.
   Contenedor vacío — la intención de diseño (83 ≈ CICFlowMeter) nunca se cableó.
   **Descartado como raíl de Fase 2.**
2. **`ddos_embedded = 112`** (submensaje `DDoSFeatures`) → **VIVO.** Es la cabeza de
   9 features de Fase 1. Este es el raíl real.
3. **Las 9 de `DDOSFeatures.py`** → el contrato lógico que consume `ddos_embedded`.

## Circuito de `ddos_embedded` (vivo, extremo a extremo, medido)

- **Escribe** (sniffer, aguas arriba): `ml_defender_features.cpp:730`
  `mutable_ddos_embedded()` + `extract_ddos_features(flow, ddos)`.
- **DOS inferencias** (OBSERVADO, no diagnosticado): `ring_consumer.cpp:1554-1562`
  corre `predict()` DENTRO del sniffer, y `zmq_handler.cpp:568-595` corre otro
  `predict()` en el ml-detector. ¿Duplicación intencional o legado? **Pendiente de entender.**
- **Consume las 9 reindexadas de Fase 1**: `zmq_handler.cpp:583-592` monta el struct
  `syn_ack_ratio … resource_saturation_score` (orden Fase 1 sin geo), con guard
  `size() != 9` en la 571. La reparación de Fase 1 está viva y corriendo.

## Las 9 features SON el invariante DDoS (la buena noticia del día)

Medido en `sniffer/src/userspace/ml_defender_features.cpp:23-120`. NO son placeholders:
física de red real desde `flow`, escritas por MECANISMO, no por técnica:

- `syn_ack_ratio` → SYN flood (ratio SYN/ACK; normal ≈1, flood >5)
- `packet_symmetry` → asimetría direccional (DDoS satura en una dirección)
- `traffic_amplification_factor` → DNS/NTP/LDAP amplification (reflexión por mecanismo)
- `protocol_anomaly_score` → handshakes incompletos / RST excesivo
- `packet_size_entropy` → uniformidad de tamaños (entropía baja)
- `resource_saturation_score` / `traffic_escalation_rate` → saturar un recurso

El invariante "detectar la traza de un DDoS, no el nombre de la técnica" YA está
codificado en las features. Responde la aspiración de fondo sin trabajo extra de diseño.

---

## GRIETA A (medida) — geo VIVO en el PRODUCTOR (sniffer)

`ml_defender_features.cpp:34` → `ddos->set_geographical_concentration(...)`.
`extract_ddos_features` del sniffer aún setea **10** features (geo incluida).
Fase 1 reindexó a 9 en el CONSUMIDOR (ml-detector), **NO en el PRODUCTOR** (sniffer).
Confirmado por el sentinel `0.5f` en `sniffer/tests/test_proto3_embedded_serialization.cpp:98-100`
(no era fixture inventado: el sniffer produce geo de verdad).
No es fatal (el ml-detector ignora geo al reindexar), pero es "el contrato no es
único" un piso por debajo. **Fase 1 quedó a medias en el lado que produce.**

## GRIETA B (medida) — `source_ip_dispersion` NO es función del flujo

`ml_defender_features.cpp:65-73`: el parámetro `flow` está comentado (`/*flow*/`).
Se computa desde `aggregator_` — una ventana global de 30s de TODO el tráfico del
sensor. Sin aggregator → `MISSING_FEATURE_SENTINEL`.

**Consecuencia para Fase 2:** es función del ESTADO DEL SENSOR, no del flujo.
CICDDoS2019 trae flujos, no estado de aggregator. Computarla offline sobre el dataset
≠ servirla en vivo desde la ventana de 30s → dos distribuciones distintas =
**covariate shift**. Es un skew tipo-geo pero más sutil: la feature está "viva" en
train y en serve, solo que mide cosas distintas en cada lado. **LA pregunta de diseño
de Fase 2.** No votar: medir la distribución dataset-offline vs serve-en-vivo antes de decidir.

## Nota lateral: `level1` (23 features) tiene su PROPIA grieta, INDEPENDIENTE de DDoS

`extract_level1_features` (`feature_extractor.cpp:83`): el orden de las 23 CASA con
`xgboost_cicids2017_metadata.json`. PERO `features[14]` (`Init_Win_bytes_forward`)
`= 0.0f` hardcodeado (`// TODO`). `Init_Win` NO existe en el protobuf `NetworkFeatures`
(medido: mensaje entero leído, 101 al cierre) → no es cableado olvidado, es feature
NO modelado. Para el level1 = **P0** (decide en producción con un feature muerto,
threshold 0.65). Para DDoS = marginal (fingerprinting de pila, no volumétrico).
Además 3 pares alias que colapsan a la misma fuente protobuf (pos 1/9 →
`total_forward_bytes`, 8/15 → `total_forward_packets`, 12/18 → `total_backward_bytes`)
= distribución deformada suave.
**SOSPECHADO:** conviven DOS level1 — el config carga `level1_attack_detector.onnx`,
el plugin carga `xgboost_cicids2017.ubj`. Cuál decide de verdad en serve = SIN MEDIR.

---

## Plan confirmado (3 pasos, en orden)

1. **Cerrar grieta A.** Quitar geo de `extract_ddos_features` del sniffer
   (`ml_defender_features.cpp:34`), dejar 9. Termina el reindex de Fase 1 en el
   productor. Rama de trabajo fuera de main. Árbitro = el compilador + los tests de
   serialización (el `0.5f` de geo debe desaparecer del test, o actualizarlo).
   OJO: es el sniffer → la manivela gira DENTRO de la VM, push desde el HOST.

2. **Grieta B: MEDIR `source_ip_dispersion`.** Opciones: (a) replicar la ventana de
   30s sobre el dataset; (b) sacarla del contrato de train+serve (como se hizo con
   geo); (c) reformularla como función del flujo. Ninguna es obvia. Candidata a
   Consejo de Sabios. Material de paper. Medición previa: distribución de la feature
   en dataset-offline vs serve-en-vivo — el número decide, no la corazonada.

3. **CICDDoS2019 por las 9** (menos las que caigan en el paso 2). El trabajo grande,
   ahora sobre raíl sano. Verificar acceso/URL del dataset como con el binetflow de
   Neris. Demostrar POR MEDICIÓN que cada feature mide lo mismo en train y serve — no asumir.

## Aviso honesto (para el paper, no sobre-vender)

Raíl sano ≠ detector útil. Las 9 se entrenan hoy sobre Betas sintéticas y se sirven
sobre tráfico sin DDoS etiquetado. El contrato sano es condición NECESARIA, no
suficiente. La inequivocidad se gana en el paso 3 (ground-truth real por el mismo
extractor), no en la fontanería. Hallazgo de método fuerte para la tesis: el patrón
de skew de Fase 1 GENERALIZA (reaparece en el sniffer y en el level1) — la enfermedad
es sistémica y el método la caza.

## Limpieza pendiente de la sesión

- **DEBT-GATE-BARE-CTEST-PASSES-UNCONFIGURED-001** YA pegada al final de
  `docs/BACKLOG.md` (sin commitear). FORMATO a arreglar: usa `##` (H2) en
  Síntoma/Causa/Fix/Bloqueante → alinear al molde de la entrada vecina
  (negrita `**Síntoma:**`). Falta newline final.
- `docs/BACKLOG.md` + `docs/continuity/PROMPT_CONTINUE_CLAUDE.md` modificados sin commitear.
- Untracked conocidos de antes: `Cierre day255 reparacion ddos.md`, `seed-repro/*.json`.
- `scratch/` (unmask/verify/crank) aparcado en `.git/info/exclude`. Limpio.
- Ramas del gate borradas (PR #141 merged, `2c5f8f4a` en main).

## Invariantes (recordatorio)

main PROTEGIDA (PR only). Un commit una idea. `add` explícito por fichero.
`git grep` o fichero concreto — NUNCA `grep -rn` desde raíz (`site/search/search_index.json`
y `build/` te comen la noche). Salidas grandes en bloques separados. Manivela en la
VM, push desde el HOST. Compilador/ctest = árbitro. Revert → recompilar. vboxsf: sha
host↔VM antes de compilar. sed BSD peligroso: contar el match o editar con Python.