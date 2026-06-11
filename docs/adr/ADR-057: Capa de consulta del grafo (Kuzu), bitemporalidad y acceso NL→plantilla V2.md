# ADR-057: Capa de consulta del grafo (Kuzu), bitemporalidad y acceso NL→plantilla

- **Estado:** 🟡 BORRADOR v2 (DAY 181) — refinado tras 1ª vuelta del Consejo de Sabios (8/8) + arbitraje de Alonso.
- **Contexto previo:** ADR-052 (identidad de flujo), schema.cypher (DAY 180), backend KuzuGraphSink (DAY 180).
- **Historial:** v1 (DAY 180-181, embrión con `❓`) → **v2 (DAY 181, tras Consejo 8/8)**.
- **Principio:** *medir, no votar*. Donde hubo desacuerdo factual (concurrencia de Kuzu), se zanja
  con un smoke test contra `libkuzu` real, no con mayoría. Las decisiones de diseño que requieren
  juicio (no medición) las arbitra Alonso, marcadas **[ÁRBITRO]**.

---

## 1. Contexto

DAY 180 cerró la ESCRITURA al grafo: el correlation-engine materializa
`(:NetworkFlow)`, `(:Alert|:TelemetryEvent)` y aristas `*_ABOUT` en Kuzu embebido,
como vista derivada del bronce. Pero **escribir no es consultar**. Falta definir cómo
se LEE el grafo de forma segura, útil y temporalmente correcta. Tres problemas distintos
que conviene abordar juntos porque se condicionan:

1. **Capa de consulta** — quién consulta el grafo y cómo, sin exponer Cypher crudo.
2. **Bitemporalidad** — el grafo hoy solo conoce el tiempo del evento, no el de su conocimiento.
3. **Acceso NL→plantilla** — traducir lenguaje natural a consultas acotadas y auditables.

Estado de partida (schema.cypher DAY 180): `NetworkFlow` es identidad pura (`flow_uid` PK,
`node_id`, `community_id`, `flow_start_window`, `seq_in_window`). `Alert`/`TelemetryEvent`
llevan el veredicto desnormalizado (cols 12-17 de `correlation_v1`). Aristas: `CORRELATES_FLOW`
(flujo↔flujo por `community_id`), `ALERT_ABOUT`/`TELEMETRY_ABOUT` (evento→flujo, `method`/`confidence`).

**Riesgo de base — Kuzu archivado (planteado por Kimi, DeepSeek; CRÍTICO).** kuzudb archivó el
upstream el 10-oct-2025; v0.11.3 es el release final. Sin parches de seguridad ni bugfixes de
corrupción/locking. **Mitigación ya existente, no nueva:** la abstracción `IGraphSink` (DAY 180)
hace el backend intercambiable sin tocar el engine; el plan B es el fork `Vela-Engineering/kuzu`.
Registrado en **DEBT-KUZU-UPSTREAM-ARCHIVED-001** (P2, DAY 180). Este ADR NO acumula Cypher nativo
fuera de la capa de plantillas precisamente para que un swap de backend no rompa T1–T7. Consecuencia
de diseño: el catálogo de plantillas es la frontera de portabilidad; cuanto más Cypher viva fuera
de él, mayor el coste de migración futura.

---

## 2. Decisión

### 2.1 Capa de consulta — **in-process, librería dentro del engine** (probablemente obligatoria)

El grafo NO se expone como endpoint Cypher libre. Se expone mediante un **catálogo de plantillas
parametrizadas** (Cypher pre-escrito, auditado, huecos tipados), servido **in-process como librería
C++ dentro del correlation-engine** — NO como servicio con superficie de red propia.

**Por qué in-process:**
- **Lock de Kuzu.** La BD es un fichero `.kuzu` con un único dueño del lock de escritura.
- **Falco.** `argus_graph.yaml` (DAY 180) alerta de cualquier lector del graph store ≠ engine.
  In-process mantiene la regla intacta, sin excepciones. *Matiz de ChatGPT, aceptado:* Falco
  **refuerza** la decisión, no la **fundamenta** — la jerarquía es lock de Kuzu > rendimiento >
  seguridad > Falco. Falco es reconfigurable; el lock no.
- **Autenticación.** Un servicio reabre auth/TLS/rate-limiting. In-process lo evita.

**Honestidad sobre la naturaleza de la decisión (Kimi).** El in-process probablemente NO es una
elección arquitectónica sino una **restricción física del motor**: los issues primarios de Kuzu
**#3295 y #3872** documentan que un segundo proceso (incluso READ_ONLY) choca con el lock mientras
el writer está activo — que es exactamente el caso de aRGus (engine con handle READ_WRITE
permanente). Qwen sostiene lo contrario (MVCC permite RO concurrente); Grok y Mistral matizan
(RO+RO sí, RW+RO mezclados no). **No se resuelve por mayoría: se mide** (ver Fase 0).

**Aislamiento de recursos (Gemini, Qwen — enmienda obligatoria).** Como las consultas corren en el
mismo proceso que la ingesta, una consulta pesada mal acotada puede degradar el engine y provocar
**drop de paquetes en el sniffer** por contención. La capa de consulta ejecuta en un **thread pool
dedicado, con prioridad de scheduling inferior (`nice`) a los threads de mutación del grafo**,
`setrlimit`/timeout por consulta, de modo que una lectura nunca bloquee la escritura ni tumbe el
proceso por OOM.

**A MEDIR (Fase 0, adelantado) [ÁRBITRO: smoke se adelanta, NO se elimina].** El smoke mide DOS
cosas distintas que el Consejo mezcló:
1. **¿Multiproceso RW+RO?** Abrir `libkuzu` READ_ONLY desde un 2º proceso mientras el engine tiene
   handle READ_WRITE. Resuelve el desacuerdo Kimi↔Qwen con evidencia, no con voto. (Esperado: falla
   con lock error → in-process queda confirmado como obligatorio.)
2. **¿Contención in-process?** Ingesta continua (~10k nodos/s) mientras se ejecutan T1/T2/T3
   concurrentes. Métrica de aceptación (Qwen): latencia p95 de lectura no se degrada >20% vs BD en
   reposo, y el hilo de escritura no se bloquea >100ms. Esta pregunta es válida **aunque** la 1
   diga "no multiproceso" — es el riesgo de verdad peligroso.

**Consumidor legítimo = el correlation-engine.** Cualquier acceso externo (operador, RAG, informes)
pasa POR el engine vía plantillas, nunca tocando el `.kuzu`.

### 2.2 Bitemporalidad — **dos ejes, dos hogares; `ingested_at` es first_seen, no transaction-time completo**

Marco canónico (Snodgrass/Jensen, recordado por Kimi):
- **Valid-time** (cuándo el hecho fue verdad): `flow_start_window`, ya existe.
- **Transaction-time** (cuándo el sistema lo supo): FALTA.

**Decisión de reparto — no meter todo en Kuzu:**

1. **`ingested_at UINT64` en el grafo, `ON CREATE SET`, nanosegundos UTC.** La estampa el
   correlation-engine en el `MERGE`, con reloj NTP-disciplinado (DEBT-ARGUSPP-NTP-001, DAY 167).
   `ON CREATE SET`, nunca `ON MATCH SET`: es "cuándo lo supimos por primera vez", inmutable.
   **Es `first_seen`, NO transaction-time completo** (corrección del Consejo a la v1 — ChatGPT, Kimi):
   no captura cambios posteriores (reclasificación, parche de score). El transaction-time completo
   (updates, intervalos `[desde, hasta)`) vive en el WAL, no en el nodo.

2. **Reconstrucción histórica completa → WAL, no Kuzu (DEBT-LABEL-WAL-001, ADR-052 §3.7).** Kuzu da
   el "ahora"; el WAL da el "entonces" con hash-chain de no-repudio. **Jerarquía de fuentes
   ratificada (Qwen):** en escenarios de replay/backfill, el **WAL prevalece** como fuente de verdad
   del tiempo de conocimiento histórico; el campo `ingested_at` en Kuzu es solo una optimización del
   estado actual. Sin esta jerarquía explícita, un replay corrompería la forense "a fecha de"
   (el evento del día 1 reprocesado el día 5 aparecería como "conocido el día 5").

**Desacople de CLOCK-INJECTION — corregido (v1 lo vendió de más).** `ingested_at` desacopla el
**eje de transacción** del reloj envenenado del sniffer (eso es cierto y valioso: aporta un eje
temporal fiable HOY). Pero **NO inmuniza el eje de evento** (Gemini): si el sniffer estampa un
`flow_start_window` en el futuro por la deuda `bpf_ktime_get_ns()`, tendremos `T_evento > T_conocimiento`
= anomalía lógica bitemporal que rompería el orden cronológico en T4.
**Guard obligatorio (Gemini):** el engine marca `temporal_anomaly = TRUE` en el nodo cuando
`flow_start_window > ingested_at + margen_de_sincronización` (pocos segundos). Aísla el efecto de
CLOCK-INJECTION sin detener la ingesta, y hace la anomalía consultable.

**Enmiendas técnicas del Consejo (incorporadas):**
- **Monotonía (Qwen).** NTP puede dar *step jumps* (±1s) que violan monotonicidad. `ingested_at`
  debe garantizarse no-decreciente: `steady_clock` + offset UTC sincronizado, o usar el
  `transaction_id` de Kuzu como proxy monótono. A verificar con inyección NTP en el smoke.
- **Índice (Mistral, Qwen).** Crear índice sobre `ingested_at` para que los filtros temporales de
  T4 no degraden a barrido lineal.
- **Kuzu no tiene temporal nativo** (SQL:2011 system-versioned): modelado a mano, confirmado.

### 2.3 Acceso NL→plantilla — **rechazo duro, NL solo clasifica, params por gramática**

Lenguaje natural → SELECCIÓN de una plantilla del catálogo + extracción de parámetros tipados.
**NUNCA** NL→Cypher libre (inyección, consulta destructiva, alucinación de estructura).

**[ÁRBITRO] Comportamiento ante ambigüedad — RECHAZO DURO, no interactivo.** Decisión de Alonso:
*"no nos podemos permitir la ambigüedad"*. Si la confianza del clasificador no supera el umbral, el
sistema **rechaza y pide reformular** — NO devuelve plantillas candidatas para que el operador elija.
Razón: en infraestructura crítica, un "creo que querías esto" sobre el que se actúa es peor que un
"no lo tengo claro, reformula". (El Consejo estaba dividido 5/3 hacia interactivo; el árbitro elige
rechazo duro por seguridad. El umbral concreto se MIDE, no se inventa.)

**El NL NO se implementa todavía — se desacopla y se mide primero (Kimi, DeepSeek, ChatGPT, Qwen,
Mistral, convergencia fuerte).** TinyLlama (1.1B) es generativo, no un clasificador de intención
entrenado; la extracción estructurada de `community_id`/`$n`/ventanas es frágil en modelos pequeños.
Antes de integrar:
- **Params por gramática/regex, NO por LLM (Qwen, Kimi).** El LLM clasifica la PLANTILLA; los
  parámetros estrictos (IDs con forma `1:...=`, fechas, enteros acotados) se extraen con
  regex/grammar y se validan por tipo de forma determinista. El LLM nunca emite el parámetro final.
- **Benchmark obligatorio antes de implementar (DEBT-NL-BENCHMARK-001, nueva).** Corpus etiquetado
  (≥100–200 consultas operativas con ambigüedad/jerga/typos). Métricas a alcanzar (placeholders a
  calibrar, no dogma): precision@1 de clasificación y F1 de extracción de params; tasa de falso
  rechazo y de falso mapeo con alta confianza. Sin estos datos, no hay umbral defendible.
- **Riesgo de jailbreak (Kimi).** Un atacante podría craftear NL que fuerce la clasificación a una
  plantilla de menor escrutinio. El benchmark incluye adversarial examples (inyección, fuera de dominio).

**Firma del catálogo — solo en arranque, no por query (Qwen).** Si el catálogo se firma (Ed25519,
cadena ADR-025), la verificación ocurre al **arrancar el engine o recargar el catálogo**, jamás por
consulta (latencia). Y solo tiene sentido si el catálogo se vuelve cargable en runtime; mientras se
compile dentro del engine, la integridad ya la da branch protection. Diferida (ver §5).

---

## 3. Catálogo de plantillas (tras arbitraje)

> Numeración estable respecto al feedback del Consejo (todos discutieron T1–T7).

| ID | Nombre | Tipo | Estado | Notas del Consejo / arbitraje |
|----|--------|------|--------|-------------------------------|
| **T1** | Vecindario a N saltos de flujo/host | Graph-native | ✅ Activa | `CORRELATES_FLOW*1..$n`. **Obligatorio LIMIT de fan-out por salto + timeout** (no basta acotar `$n`): un supernode (DNS/NTP/LB) explota O(d^n). `$n` por defecto bajo. |
| **T2** | Contexto de una alerta | Graph-native | ✅ Activa | Flujo (`ALERT_ABOUT`) + vecindario + alertas vecinas. Valor core del grafo. |
| **T3** | Densidad de amenaza en vecindario | Graph-native | ✅ Activa | Agrega `overall_threat_score`. **Acotar a subgrafo por tiempo** (Gemini). Necesita `TelemetryEvent` enriquecido (benignos con score) para ser honesta. |
| **T4** | Retro-hunt de IOC (acotada) | Bitemporal-plana | ✅ Activa **[ÁRBITRO: acotada y honesta]** | Dado `$community_id`, devuelve apariciones del patrón con `flow_start_window` + `ingested_at`. **NO es point-in-time**; no responde "¿qué sabíamos a las 03:00?". Esa reconstrucción es T-hist (futura, WAL). |
| ~~T5~~ | ~~Alertas por threat_category en ventana~~ | — | ❌ **ELIMINADA** | 7/8 podan. Filtro tabular puro → plano ORO (Parquet/DuckDB). No saturar el grafo. |
| **T6** | Alertas de un `node_id` | Bridge-ORO | 🟡 Activa **[ÁRBITRO: sobrevive como puente a ORO]** | La capa **enruta a ORO**, no ejecuta en Kuzu. Riesgo asumido (Qwen: anti-patrón God Object, scope creep). **Condición de muerte:** si el benchmark muestra que el grafo no aporta (>2× lento/RAM vs DuckDB), se elimina. *"Aprenderemos."* |
| **T7** | Camino de propagación / attack path | Graph-native | ✅ **Activa (NUEVA — ChatGPT)** | Shortest path entre `Alert`s críticos vía `CORRELATES_FLOW`. Responde "¿cómo se comprometió este host?". Genuinamente graph-native; mejor justificada que T5/T6. |
| T-hist | Reconstrucción histórica "a fecha de" | Bitemporal point-in-time | ⏳ **Futura** | "¿Qué sabíamos a las 03:00?". Depende de **DEBT-LABEL-WAL-001**. NO se promete en el catálogo inicial (Kimi). |

---

## 4. Consecuencias

- (+) Grafo consultable de forma segura y auditable, no solo escribible.
- (+) `ingested_at` aporta un eje de transacción fiable HOY (estado actual), independiente del reloj
  envenenado del sniffer; `temporal_anomaly` detecta su corrupción residual.
- (+) Rechazo duro del NL: cero ambigüedad sobre la que actuar en infraestructura crítica.
- (+) In-process mantiene lock de Kuzu y Falco como invariantes, sin auth nueva.
- (+) El catálogo como frontera de portabilidad acota el coste de un futuro swap de Kuzu.
- (−) Complejidad: se aborda por fases, con smoke de viabilidad ANTES de comprometer plantillas.
- (−) `ingested_at` toca el schema → re-modelado, pero gratis ahora (grafo vacío).
- (−) Forense histórico real depende de DEBT-LABEL-WAL-001 (abierta). `ingested_at` es el primer
  paso, no la solución completa.
- (−) T6 (bridge-ORO) es un riesgo consciente de scope creep, con condición de muerte explícita.

---

## 5. Plan por fases (reordenado tras Consejo)

> Cambio clave vs v1: el smoke de viabilidad de Kuzu se ADELANTA a Fase 0 (Gemini, DeepSeek,
> Mistral, Qwen). No se escribe una plantilla hasta saber si el motor aguanta.

- **Fase 0 (hoy):**
    1. `ingested_at UINT64` (ns UTC) al schema (3 tablas) + `ON CREATE SET` en `cypher_builder.hpp`
        + flag `temporal_anomaly` + índice sobre `ingested_at`. NO toca bronce/protobuf/sniffer
          (contrato `correlation_v1` intacto).
    2. **Smoke ADELANTADO:** (a) multiproceso RW+RO contra `libkuzu` real; (b) contención lectura
       bajo carga de escritura (p95 < +20%, escritura no bloqueada >100ms); (c) inyección NTP step ±1s
       para verificar monotonía de `ingested_at`.
- **Fase 1:** catálogo podado (T1, T2, T3, T4, T6-bridge, T7) como librería in-process, params por
  gramática + validación de tipos, thread pool aislado. Tests por plantilla contra grafo sembrado +
  test de explosión combinatoria de T1. Presupuesto p95 por plantilla (a calibrar con hardware).
- **Fase 2:** benchmark T6 (y candidatas convenience) en Kuzu vs DuckDB → confirma/elimina el bridge.
- **Fase 3 (ADR separado — DEBT-NL-BENCHMARK-001):** NL como clasificador de plantilla (no generador
  de params), con corpus etiquetado y métricas de cierre. Rechazo duro bajo umbral medido.
- **Fase 4:** firma del catálogo (Ed25519, verificación solo en arranque, con revocación/rotación/TTL
  definidos — Kimi) + T-hist sobre WAL (depende de DEBT-LABEL-WAL-001) + `restore_from_wal_smoke_test`
  (ChatGPT: recuperación ante corrupción del WAL como criterio de aceptación).

---

## 6. Estado de las decisiones tras 1ª vuelta del Consejo

| Decisión | Veredicto | Quién |
|----------|-----------|-------|
| Default in-process | ✅ Ratificado 8/8 (probablemente obligatorio, a confirmar por smoke) | unánime |
| Aislamiento de recursos (thread pool, nice, rlimit) | ✅ Incorporado | Gemini, Qwen |
| `ingested_at` ON CREATE SET, Fase 0 | ✅ Ratificado 8/8 | unánime |
| `ingested_at` = first_seen, no transaction-time completo | ✅ Corregido (v1 lo vendía de más) | ChatGPT, Kimi |
| `temporal_anomaly` flag (T_v > T_t) | ✅ Incorporado | Gemini |
| WAL prevalece en replay; jerarquía de fuentes | ✅ Ratificado | Qwen |
| NL: rechazo duro ante ambigüedad | ✅ **[ÁRBITRO]** | Alonso (Consejo dividido 5/3) |
| NL: params por gramática, LLM solo clasifica | ✅ Incorporado | Qwen, Kimi |
| NL: desacoplado a ADR propio + benchmark | ✅ DEBT-NL-BENCHMARK-001 | Kimi, DeepSeek, ChatGPT, Mistral, Qwen |
| T5 eliminada | ✅ 7/8 | mayoría |
| T6 sobrevive como bridge-ORO | ✅ **[ÁRBITRO]** (con condición de muerte) | Alonso |
| T4 acotada y honesta (no point-in-time) | ✅ **[ÁRBITRO]** | Alonso (Kimi, DeepSeek) |
| T7 attack-path adoptada | ✅ **[ÁRBITRO]** | Alonso (ChatGPT) |
| T1 fan-out LIMIT + timeout | ✅ Incorporado | ChatGPT, Gemini, Qwen, Kimi |
| Smoke adelantado a Fase 0 (no eliminado) | ✅ **[ÁRBITRO]** | Alonso (Gemini, DeepSeek, Mistral, Qwen) |
| Firma Ed25519 diferida (Fase 4, verif. en arranque, con revocación) | ✅ | Kimi, Qwen, DeepSeek |
| Plan de contingencia Kuzu archivado | ✅ Referenciado DEBT-KUZU-UPSTREAM-ARCHIVED-001 + IGraphSink | Kimi, DeepSeek, Mistral |

**Nuevas deudas generadas por el Consejo:**
- `DEBT-NL-BENCHMARK-001` (P2) — dataset etiquetado + métricas del clasificador NL antes de Fase 3.
- `DEBT-KUZU-CONCURRENCY-SMOKE-001` (P1) — smoke de multiproceso + contención (Fase 0).
- `restore_from_wal_smoke_test` — bajo DEBT-LABEL-WAL-001 (recuperación ante corrupción).

---

## 7. Pendiente antes de 2ª vuelta / cierre

- [ ] Ejecutar el smoke de Fase 0 (concurrencia + contención + monotonía NTP) y **adjuntar resultados
  medidos al ADR** — es la condición que casi todo el Consejo pone para pasar de "buen diseño" a
  "diseño validado". *Medir, no votar.*
- [ ] Implementar Fase 0 (schema + builder) tras el smoke.
- [ ] Redactar el catálogo Cypher real de T1–T4, T6, T7 (parametrizado, con LIMIT/timeout).
- [ ] Definir presupuesto p95 por plantilla (placeholder hasta hardware FEDER).
- [ ] 2ª vuelta del Consejo con los datos del smoke, o cierre si Alonso considera Fase 0 con mandato.