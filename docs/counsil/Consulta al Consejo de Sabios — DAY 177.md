# Consulta al Consejo de Sabios — DAY 177

**Proyecto:** aRGus NDR · **Rama:** `feature/day170-community-id-protobuf` · **Fecha:** 2026-06-07
**Ámbito:** zona bronce `correlation_v1` + injector sintético (camino A/B de DAY 176).
**Naturaleza:** día de cableado y verificación E2E, no de ADR. Pide ratificación de
decisiones tomadas y feedback sobre una deuda reencuadrada.

---

## 1. Qué se hizo hoy (con evidencia)

Tres cambios, los tres verificados E2E sobre tráfico real (pipeline completo levantado,
100 eventos sintéticos inyectados, bronce inspeccionado).

### (B) col 17 `authoritative_source` → string simbólico
- `correlation_writer.cpp`: `static_cast<int>` → `DetectorSource_Name(...)`.
- `correlation_record.hpp`: campo `int` → `std::string`.
- `correlation_reader.cpp`: `parse_num(f[17])` → asignación directa de string.
- `test_correlation_roundtrip.cpp`: sello pasa de `== 4` a `== "DETECTOR_SOURCE_ML_PRIORITY"`.
- Motivo: contrato auto-descriptivo, estable frente a evolución del enum en el `.proto`.
- Decisión de diseño tomada: el reader **almacena el string** (Opción 1), no re-parsea a
  enum, para mantener el correlation-engine **limpio de protobuf** (decisión DAY 174 #5).
- **Sello:** round-trip unitario verde + bronce real con col 17 simbólica:
  `150 DETECTOR_SOURCE_ML_PRIORITY` + `9 DETECTOR_SOURCE_DIVERGENCE` (strings, no `"4"`).

### (node_id) DEBT-INJECTOR-NODEID-001 (P0)
- El injector dejaba col 3 (`originating_node_id`) **vacía** → `flow_uid =
  hash(node_id ‖ community_id ‖ window)` degenerado.
- Fix (Q1 del Consejo DAY 176): node_id sintético por eje de modo —
  isomorfo `synth-node-00` (UN punto de captura estable), mock `synth:node:<id>`.
- **Sello:** `102 synth-node-00` en bronce (más `57 cpp_sniffer_v33_day12` del sniffer
  real restaurado al final del E2E — ruido esperado, prueba de que el real también puebla node_id).

### (proto) hallazgo nuevo de hoy — tráfico benigno no correlacionable
- **Síntoma:** primera corrida del E2E → **0 filas en bronce** pese a que ml-detector
  procesó los 100 eventos (delta=100 en stats).
- **Causa raíz:** en modo benigno el injector ponía `protocol_number = rand_uint(1,255)`.
  `compute_community_id()` devuelve `nullopt` si `proto != TCP(6)/UDP(17)`
  (solo protocolos con puertos). Probabilidad de caer en {6,17} con rand[1,255] ≈ 0.78%.
  → community_id vacío → el hook `!community_id().empty()` descarta → bronce a 0.
- **Bug latente añadido:** en benigno `protocol_number` (aleatorio) y `protocol_name`
  (TCP/UDP aleatorio) **no concordaban entre sí**.
- **Fix (Opción 1):** un único coin flip `use_tcp` gobierna número y nombre;
  benigno pasa a TCP/UDP 50/50 coherente. Modo ataque intacto por construcción
  (`use_tcp = is_attack ? true : coinflip`).
- **Sello:** de 0% a **100% community_id poblado** (159/159 con formato Corelight `1:...=`).

---

## 2. Decisiones ya tomadas (se piden ratificación u objeción)

1. **B/Opción 1:** reader guarda col 17 como string; engine no incluye protobuf.
2. **node_id isomorfo fijo** (`synth-node-00`): todos los eventos de una corrida comparten
   node_id (= UN sensor), unicidad de `flow_uid` la da el community_id distinto por 5-tupla.
3. **proto benigno forzado a TCP/UDP:** se arregla la causa raíz (injector irrealista),
   no el síntoma (no se parchea el target E2E para que pase `--attack`).

---

## 3. Hallazgo principal para el Consejo — reencuadre de DEBT-INJECTOR-ROWGAP-001

La deuda decía: *"gap ~8 de 50, no determinista; sospechosos `dontwait` o threshold del
CorrelationWriter"*. Hoy, con el proto arreglado (ya sin enmascarar el conteo):

- **102 filas sintéticas, 102 community_id ÚNICOS, cero duplicados de community_id.**
- Pero **2 event_ids duplicados**: `synthetic-8` y `synthetic-29` aparecen 2 veces cada uno,
  con community_id **distinto** (5-tupla distinta) → para bronce/Kuzu son flujos diferentes,
  no corrupción. Rango exacto `synthetic-0`…`synthetic-99` (una sola tanda de 100).

**Interpretación:** el row-gap no se reprodujo como *pérdida*; se manifestó como *reenvío*.
El `publisher_.send(msg, zmq::send_flags::dontwait)` sin comprobar return code no garantiza
ni "at most once" ni "exactly once". El síntoma es **bidireccional** (a veces pierde, a veces
repite, según el estado del pipe PUSH). La causa raíz es la misma; cambia el signo.

**Propuesta de reencuadre:** de *"se pierden filas"* a *"el PUSH sin control de entrega no
ofrece garantía once-only"*. Y la **métrica de medición honesta** ya no es contar filas ni
event_ids, sino **diff de conjuntos**: `{event_id enviados}` (log del injector) vs
`{event_id escritos}` (bronce). Eso separa pérdidas de reenvíos sin ambigüedad.

---

## 4. Preguntas al Consejo

**Q1 (fondo — necesita criterio de los 8). Dirección del fix de ROWGAP-001.**
El injector es una **herramienta de prueba**, no el sniffer de producción. ¿Cuánto rigor de
entrega merece? Opciones (combinables):
- (a) comprobar return de `send()` + reintento acotado;
- (b) `send()` bloqueante con timeout en vez de `dontwait`;
- (c) reconsiderar el patrón PUSH/PULL;
- (d) aceptar el ruido y confiar en el dedup por `flow_uid` aguas arriba (los reenvíos son
  inocuos por diseño: distinto community_id = distinto flujo).
  ¿Es (d) defendible para una herramienta de test, o la determinismo de CI exige (a)/(b)?

**Q2 (fondo). Realismo del benigno vs cobertura del camino de descarte.**
Forzar 100% TCP/UDP da bronce determinista, pero **elimina la cobertura** del camino
`compute_community_id() == nullopt` (proto sin puertos → descarte). ¿Conviene que el benigno
incluya una fracción pequeña (p.ej. 5% ICMP) **precisamente para seguir ejercitando** que el
bronce descarta correctamente los flujos sin community_id? Disyuntiva: determinismo CI vs
cobertura del discard path. ¿Dos perillas (modo determinista / modo realista-con-ruido)?

**Q3 (alcance). ¿Esto alimenta ADR-055?**
El arranque sembró ADR-055 = decisiones de injectors/golden/lib. node_id + proto + reencuadre
de ROWGAP son decisiones de injector. ¿ADR-055 las absorbe, o el reencuadre de ROWGAP merece
tratamiento aparte? (Recordatorio numeración: ADR-053 RESERVADO JA3/JA4+TLS+BGP;
ADR-054 PENDIENTE modelo de confianza bronce multi-nodo.)

**Q4 (gobernanza — ratificación rápida). DEBT id para el hallazgo de proto.**
¿El fix de proto benigno merece id de deuda propio, o es simplemente "completar A" (cerrar
el objetivo de poblar community_id)? Hoy lleva solo un comentario `DAY 177 (A)` en el código.

**Q5 (aviso, no decisión). Oracle Divergence en bronce.**
9 de 159 filas llevan `DETECTOR_SOURCE_DIVERGENCE` (ADR-051) — el bronce **preserva** la
procedencia real, no un valor fijo. ¿Algo que el Consejo quiera fijar sobre cómo propaga la
divergencia hacia Kuzu / decisión gold, o se deja para cuando se cablee el lado consumidor?

---

## 5. Nota de método

Las preguntas van **sin respuesta pre-cargada** para no anclar a los 7 modelos restantes
(el asiento Claude dará su posición por separado si Alonso lo pide). Se busca convergencia
8/8 en Q1–Q3, ratificación en Q4, y registro del aviso en Q5.