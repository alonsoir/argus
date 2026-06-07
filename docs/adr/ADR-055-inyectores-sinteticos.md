# ADR-055 — Inyectores Sintéticos: Fidelidad al Componente, Determinismo de Bronce y Semántica de Entrega

| Campo | Valor |
|---|---|
| **ADR** | 055 |
| **Versión** | **v1 (borrador)** — incorpora la 1ª pasada del Consejo (DAY 177) |
| **Fecha** | DAY 177 (2026-06-07) |
| **Estado** | BORRADOR — pendiente confirmación de fidelidad del Consejo sobre la anulación de árbitro en Q1 (semántica de entrega) |
| **Decisión final** | Alonso |
| **Deliberación** | Consejo de Sabios (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen) — 1ª pasada cerrada |
| **Recoge** | Decisiones de injectors / golden de DAY 176–177 (camino A/B), y el reencuadre de DEBT-INJECTOR-ROWGAP-001 |
| **Depende de / relaciona** | ADR-052 (`flow_uid`, `node_id` como identidad de corpus declarada), ADR-051 (Oracle Divergence / N-version, `orphan_rate`), ADR-046 (`community_id` como P0 join key), ADR-054 *pendiente* (modelo de confianza bronce multi-nodo), cableado bronce DAY 175 |
| **Cierra** | DEBT-INJECTOR-NODEID-001 (P0); DEBT-INJECTOR-ROWGAP-001 (reencuadrada y cerrada como característica) |
| **Numeración** | ADR-053 RESERVADO (JA3/JA4 + TLS + BGP); ADR-054 PENDIENTE (confianza bronce multi-nodo). ADR-055 = este. |

---

## 0. Principio ordenador (invariante de las herramientas de `tools/`)

> **Una herramienta de `tools/` es un suplantador fiel, no un simulador libre. Reproduce el comportamiento NÚCLEO del componente oficial que sustituye. No puede divergir de él por conveniencia de test.**

Las herramientas de `tools/` (`synthetic_sniffer_injector` suplanta al sniffer; `synthetic_ml_output_injector` suplanta a ml-detector; etc.) existen para **ejercitar al siguiente componente del pipeline con un contrato idéntico al de producción**, de forma determinista y reproducible. Su valor histórico es doble:

1. **Ejercitar** un componente aislado sin levantar toda la cadena real.
2. **Revelar** discrepancias de contrato. Precedente: con `synthetic_ml_output_injector` se detectó que los mensajes protobuf llegaban con **menos features de las diseñadas** — un hallazgo real sobre el contrato, no un defecto de la herramienta.

**Invariante de proyecto (permanente):**
> *El suplantador sigue el comportamiento núcleo del componente oficial. Si el componente oficial cambia (transporte, contrato, semántica), su suplantador se actualiza con él — la propagación es **bidireccional**. Hacer el suplantador más fiable, más limpio o más "correcto" que el componente real lo invalida como espejo. Medir mejor lo que la herramienta recoge es **aditivo**: no altera el comportamiento, y de paso nos dice qué esperar del componente oficial.*

Consecuencia que recorre el ADR: ante cualquier decisión sobre una herramienta de `tools/`, la pregunta no es *"¿qué haría más robusta la herramienta?"* sino *"¿se comporta como el componente que suplanta?"*. La instrumentación de medida es la única adición que escapa a esa regla, porque no toca el comportamiento.

---

## 1. Estado

BORRADOR v1. Formaliza las decisiones de injector/golden de DAY 176–177, subordinadas a §0. Cierra dos deudas (NODEID, ROWGAP). Una decisión (Q1, semántica de entrega) se resuelve por **arbitraje de Alonso en contra del mecanismo que pedía la mayoría del Consejo**, y se marca como tal para la confirmación de fidelidad.

> **Delimitación con ADR-054 (anti-duplicación).** ADR-055 NO define el modelo de confianza del bronce (HMAC/Ed25519, validación cross-nodo) — eso es ADR-054. ADR-055 cubre el **lado productor de test** (injectors) y la **disciplina del bronce determinista**. El contrato `correlation_v1` en sí (cableado DAY 175) es referencia, no se redefine aquí.

---

## 2. Contexto

### 2.1 El camino A/B y el orden resuelto por medición (no por voto)

DAY 176 dejó dos batallas: (A) injectors poblando `community_id`, (B) col 17 `authoritative_source` → string simbólico. El orden B-vs-A se resolvió en DAY 177 **midiendo**, no votando (precedente "medir, no votar"): se inspeccionó cómo construye sus filas `test_correlation_roundtrip` y se confirmó que es **injector-independiente** (fabrica su propio `NetworkSecurityEvent` con valores literales). Por tanto B podía ir primero sin riesgo, y A se construiría después contra el contrato ya final. **B antes que A.**

### 2.2 Tres hallazgos de DAY 177

1. **node_id vacío (P0).** El injector dejaba col 3 (`originating_node_id`) sin poblar → `flow_uid = hash(node_id ‖ community_id ‖ window)` degenerado (ADR-052).
2. **Proto benigno no correlacionable.** En modo benigno el injector ponía `protocol_number = rand_uint(1,255)`. `compute_community_id()` devuelve `nullopt` si `proto ∉ {TCP(6), UDP(17)}` (solo protocolos con puertos). Probabilidad de caer en {6,17} ≈ 0.78%. → `community_id` vacío → el hook `!community_id().empty()` descartaba → **bronce a 0 filas**, pese a que ml-detector procesó los 100 eventos (delta=100 en stats). Además, `protocol_number` (aleatorio) y `protocol_name` (TCP/UDP aleatorio) **no concordaban entre sí** (bug latente).
3. **Semántica de entrega del injector.** Con el proto arreglado, una corrida de 100 produjo **102 filas, 102 `community_id` únicos, 2 `event_id` duplicados** (`synthetic-8`, `synthetic-29`) con `community_id` distinto. El `publisher_.send(msg, zmq::send_flags::dontwait)` sin comprobar return no ofrece garantía *once-only*: el síntoma es **bidireccional** (a veces pierde — el "row-gap" original ~8/50 —, a veces reenvía). El sniffer real usa el mismo `dontwait`.

---

## 3. Decisiones

### 3.1 node_id sintético por eje de modo (cierra DEBT-INJECTOR-NODEID-001)

El injector puebla `originating_node_id` (col 3):

- **Isomorfo:** `synth-node-00` — **fijo**. Modela UN punto de captura (un sensor) observando muchos flujos. La unicidad del `flow_uid` la aporta el `community_id` distinto por 5-tupla, no la variabilidad del node_id (coherente con ADR-052 §2.1: `community_id` es correlación, no identidad).
- **Mock:** `synth:node:<event_id>` — auto-identificable; el correlation-engine lo descarta antes de Kuzu.

*Multi-nodo sintético (`--multi-node N`) se difiere a cuando lo necesite ADR-054.* **Ratificación Consejo: 8/8.**

### 3.2 Tráfico benigno correlacionable + cobertura del camino de descarte (Q2)

**Fix de fondo (no del síntoma):** se corrige el injector irrealista, no se parchea el target E2E. Un único `use_tcp` gobierna número y nombre de protocolo:

```cpp
const bool use_tcp = is_attack ? true : (rand_uint(0, 1) == 1);
nf->set_protocol_number(use_tcp ? 6 : 17);
nf->set_protocol_name(use_tcp ? "TCP" : "UDP");
```

Modo ataque intacto por construcción (`is_attack → use_tcp=true`). Resultado: `community_id` poblado del 0% al **100%** (159/159, formato Corelight `1:...=`).

**Dos perillas (Consejo 8/8), con determinismo por semilla fija (refinamiento DeepSeek):**

- **Modo `deterministic` (default CI):** 100% TCP/UDP coherente. Aserción: `count(escritos) == count(enviados correlacionables)`.
- **Modo `realistic` (suites profundas):** fracción **fija** (~5%, p.ej. 5 ICMP sobre 100) de protocolos sin puertos, con **semilla fija** → mismos `event_id` no-correlacionables en cada corrida. Aserción explícita: esos `event_id` **NO** aparecen en bronce. Esto ejercita el *discard path* (`nullopt` → descarte) como **test duro**, no como fuzz best-effort.

Fórmula de validación (Gemini): `{escritos en bronce} == {inyectados} \ {inyectados sin puertos}`.

Implementación sugerida: env var / flag (`ARGUS_PROTO_MIX=deterministic|realistic`), default `deterministic`.

### 3.3 Semántica de entrega — INSTRUMENTAR, no re-arquitecturar (Q1) ⚠️ ANULACIÓN DE ÁRBITRO

**Decisión: el `send(dontwait)` se mantiene** (fidelidad al sniffer real, §0). NO se adopta (a) reintento, NI (b) bloqueante con timeout, NI (c) cambio de patrón PUSH/PULL. Lo único que se añade es el **instrumento de medida**:

- **Métrica oficial: diff de conjuntos** — `{event_id enviados}` (log del injector) vs `{event_id escritos}` (bronce). Separa pérdidas de reenvíos sin ambigüedad. Es el mismo gesto con el que se detectaron los gaps de features (medir lo recogido contra lo esperado).
- El comportamiento bidireccional de ZMQ PUSH se documenta como **característica revelada**, no como defecto a corregir.

**DEBT-INJECTOR-ROWGAP-001 se reencuadra y se cierra como característica:** no es "se pierden filas", es "el injector reproduce fielmente la semántica de entrega no-garantizada de ZMQ PUSH; se instrumenta para hacerla visible". Si el instrumento revelara en el futuro una pérdida que rompe el gate de CI de verdad (hoy el gate mide deltas de stats, dio 100 limpio — no está roto), *entonces* se reconsidera el mecanismo. **Medir antes de arreglar.**

> **Nota de arbitraje (para confirmación de fidelidad).** La 1ª pasada del Consejo NO alcanzó mayoría en el *mecanismo*: (a)+(d) → Grok, Mistral, Claude; (b) → Gemini, Qwen, Kimi; (a)+(b) → ChatGPT, DeepSeek. **Consenso 8/8 únicamente en**: rechazar (d) como solución única, rechazar (c) ahora, y adoptar la métrica de conjuntos. Alonso **anula la adición de maquinaria de entrega (a/b)** sobre el argumento de fidelidad de §0: el suplantador no debe ser más fiable que el sniffer que imita; si algún día se cambia el transporte del sniffer, se cambiará también el del injector (propagación bidireccional). Precedente de anulación: ADR-052 §3.11.

### 3.4 col 17 `authoritative_source` como string simbólico (referencia — ratificado)

Decisión de contrato de bronce (writer/reader), sellada en DAY 177: `DetectorSource_Name()` en vez de `static_cast<int>`; reader almacena string; engine **limpio de protobuf** (decisión DAY-174 #5). **Ratificación Consejo 8/8.** Se referencia aquí porque ADR-055 registra su **sello desde el injector**: bronce real con `150 DETECTOR_SOURCE_ML_PRIORITY` + `9 DETECTOR_SOURCE_DIVERGENCE` (strings, no `"4"`).

### 3.5 Oracle Divergence preservada en bronce (Q5 — aviso, sin acción hoy)

Que 9/159 filas lleven `DETECTOR_SOURCE_DIVERGENCE` (ADR-051) confirma que el bronce **preserva** la procedencia real, no un valor fijo — **señal de éxito**, no defecto. La interpretación gold se **aplaza** hasta cablear el consumidor. **Directriz temprana (Gemini), registrada para el cargador gold:** el atributo de divergencia **NO debe aplanarse** al entrar en Kuzu; tratar el registro con heurística de "voto de calidad" o bifurcar aristas. La trazabilidad de procedencia debe ser **extremo a extremo** (ChatGPT). Decisión efectiva → ADR-054 / lado consumidor.

---

## 4. Alternativas rechazadas

| Alternativa | Por qué se rechaza |
|---|---|
| Parchear el target E2E para que inyecte `--attack` (Q2) | Resuelve el síntoma, no la causa (injector benigno irrealista). |
| (a)/(b)/(c) en la entrega del injector (Q1) | Hace el suplantador más fiable que el sniffer → menos fiel (§0). Sobreingeniería para herramienta de test. |
| (d) confiar solo en dedup por `flow_uid` sin medir | Deja la pérdida/reenvío **silenciosa**. El instrumento (3.3) es obligatorio. Rechazo (d)-solo: 8/8. |
| Un único modo de proto que mezcle determinismo y ruido sin semilla (Q2) | Degrada ambos fines; el determinismo de CI exige semilla fija (DeepSeek). |
| Abrir DEBT nuevo para el fix de proto (Q4) | Era un bug de implementación corregido en el mismo ciclo, no deuda arquitectónica. 7/8 + Alonso. |
| ADR separado para el reencuadre de ROWGAP (Q3) | Es decisión de injector; pertenece a ADR-055. 8/8. |
| node_id sintético variable por defecto | Añade ruido innecesario; el injector modela UN sensor (§3.1). |
| Aplanar / normalizar la divergencia en bronce (Q5) | Destruye la procedencia, contra ADR-051 y §0. |

---

## 5. Estado de las preguntas del Consejo (1ª pasada)

| Q | Tema | Resolución |
|---|---|---|
| Ratif. | B/Opción 1, node_id, proto | **8/8** ratificadas (§3.1, §3.2, §3.4). |
| Reencuadre | ROWGAP → semántica de entrega | **8/8** avalado (§3.3). |
| Q1 | Mecanismo de entrega | **Sin mayoría** (3/3/2). Consenso solo en métrica + rechazo de (c)/(d)-solo. **Arbitraje Alonso → solo instrumento** (§3.3). *Requiere confirmación de fidelidad.* |
| Q2 | Realismo vs cobertura | **8/8** dos perillas + semilla fija (§3.2). |
| Q3 | ¿ADR-055 absorbe? | **8/8** sí (§3.1–3.3, 3.5). |
| Q4 | DEBT para proto | **7/8** no (Claude votó sí, se retractó). Cierra como "completar A" (§3.2). |
| Q5 | Divergence en bronce | **8/8** preservar + aplazar + directriz "no aplanar" (§3.5). |

**Para la confirmación de fidelidad (no deliberación nueva):** ¿refleja esta v1 fielmente el consenso de la 1ª pasada, y deja clara la anulación de árbitro en Q1 (§3.3, solo instrumento sobre el argumento de fidelidad de §0)?

---

## 6. Consecuencias

**Positivas.** Bronce determinista alcanzable en CI (modo `deterministic`) + cobertura dura del *discard path* (modo `realistic` con semilla). `flow_uid` ya no degenera (node_id poblado). Contrato col 17 auto-descriptivo sellado E2E. Métrica de entrega honesta (diff de conjuntos) que sirve a la vez de oráculo del comportamiento del sniffer real. Suplantadores fieles por invariante (§0).

**Negativas / coste.** Una bifurcación de modo más en el injector. La métrica de conjuntos es trabajo a implementar (no hecho hoy). Disciplina nueva: cualquier cambio de transporte/contrato en sniffer/ml-detector/firewall obliga a actualizar su suplantador (propagación bidireccional, §0).

**Riesgos.** (1) Si el instrumento de conjuntos no se implementa, la pérdida/reenvío vuelve a ser invisible. (2) `seq_in_window` (ADR-052 §3.1.4): el injector hoy no lo transporta; con `community_id` únicos no hubo colisión, pero una ráfaga con reúso de 5-tupla podría exponerlo — **considerar, no resuelto aquí**. (3) El modo `realistic` con semilla mal fijada reintroduce no-determinismo.

---

## 7. Validación (EMECAS++)

Sobre el pipeline sintético (`make pipeline-start` + `make test-e2e-synthetic-full`):

- **node_id poblado:** col 3 == `synth-node-00` en modo isomorfo. *(Cierre de DEBT-INJECTOR-NODEID-001.)* — **verificado DAY 177** (102 filas `synth-node-00`).
- **community_id 100% en determinista:** col 4 con formato `1:...=` para todo flujo TCP/UDP. — **verificado DAY 177** (159/159).
- **Discard path (modo realistic):** los `event_id` ICMP de semilla fija NO aparecen en bronce; `count(escritos) == count(enviados) − count(ICMP)`. *(Pendiente: requiere modo `realistic` + métrica.)*
- **col 17 simbólica E2E:** bronce contiene nombres de enum (`DETECTOR_SOURCE_*`), nunca enteros. — **verificado DAY 177** (150 ML_PRIORITY + 9 DIVERGENCE).
- **Diff de conjuntos:** `{enviados} \ {escritos}` reportado; pérdidas y reenvíos distinguibles. *(Pendiente: requiere instrumento.)*
- **Fidelidad de transporte:** el injector usa el mismo `send(dontwait)` que el sniffer; no se le añade garantía de entrega que el sniffer no tenga.

---

## 8. Deudas y diferidos

| DEBT | Prio | Estado |
|---|---|---|
| `DEBT-INJECTOR-NODEID-001` | P0 | **Cerrada** (§3.1). Verificada E2E DAY 177. |
| `DEBT-INJECTOR-ROWGAP-001` | P1 | **Reencuadrada y cerrada como característica** (§3.3). El comportamiento bidireccional de ZMQ PUSH es fiel al sniffer; se instrumenta, no se corrige. |
| `DEBT-INJECTOR-DELIVERY-METRIC-001` (NUEVA) | P2 | Instrumento de diff de conjuntos `{enviados}` vs `{escritos}` en el E2E sintético. Trabajo aditivo, no toca comportamiento. *(Reemplaza el "fix" de ROWGAP.)* |
| `DEBT-INJECTOR-PROTO-MIX-001` (NUEVA) | P2 | Modo `realistic` con semilla fija + aserción de ausencia en bronce (§3.2). |
| Fix de proto benigno (Q4) | — | **NO es deuda.** Cerrado como "completar A". Comentario `DAY 177 (A)` en código + cita en el MR. |
| `DEBT-LIB-001` (extraer `libs/flow-identity/`) | P1 | **NO deliberada en esta pasada** — no estaba en la consulta. Dentro del ámbito de ADR-055 (lib); se trae a una pasada futura. |
| `DEBT-INJECTOR-SEQWINDOW-001` (propuesta) | P3 | ¿Transporta el injector `seq_in_window` (ADR-052 §3.1.4)? Hoy no; sin colisiones observadas. Considerar. |

---

## 9. Referencias

- ADR-052 (`flow_uid`, `node_id` como identidad de corpus declarada; precedente de anulación de árbitro §3.11).
- ADR-051 (Oracle Divergence / N-version reasoning; `orphan_rate`). ADR-046 (`community_id` como P0 join key). ADR-054 *pendiente* (confianza bronce multi-nodo).
- Cableado bronce DAY 175 (CorrelationWriter, contrato `correlation_v1`, hook punto único).
- `corelight/community-id-spec`; `sniffer::flow::compute_community_id` (corte proto ∈ {6,17}).
- Consejo de Sabios DAY 177 (1ª pasada, 8 modelos): ratificaciones 8/8; Q1 split 3/3/2 + arbitraje; Q2/Q3/Q5 8/8; Q4 7/8.
- Precedente herramientas de `tools/`: detección de gaps de features vía `synthetic_ml_output_injector`.
