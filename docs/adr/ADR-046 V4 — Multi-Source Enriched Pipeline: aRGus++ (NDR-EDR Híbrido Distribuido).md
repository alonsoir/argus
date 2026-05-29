# ADR-046 v4 — Multi-Source Enriched Pipeline: aRGus++ (NDR-EDR Híbrido Distribuido)

| Campo | Valor |
|---|---|
| **ADR** | 046 |
| **Versión** | v4 (sustituye a ADR-046 v3) |
| **Fecha** | 2026-05-29 (DAY 169) |
| **Estado** | Aceptado |
| **Decisión final** | Alonso |
| **Deliberación** | Consejo de Sabios (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen) — 4 pasadas |
| **Depende de / relaciona** | ADR-040 (ML Plugin Retraining Contract), ADR-044 (ICryptoProvider), ADR-047 (resiliencia en capas), ADR-048 (etcd HA / correlación F2), ADR-026/027 (ZeroMQ PUB/SUB) |
| **Artefactos derivados** | `network_security.proto` (envelope), `AdapterSpec v1` (documento normativo aparte), contrato de dataset federado (Pasada 4, pendiente) |

---

## 1. Estado

Aceptado. Sustituye a ADR-046 v3, que fijaba `community_id` como clave primaria única. Esta versión abandona la PK única en favor de un modelo de dos claves, y formaliza el correlador como un **runtime de grafo temporal de eventos con event-sourcing**, orientado a producir un dataset reproducible para entrenamiento distribuido federado.

---

## 2. Contexto

### 2.1 El problema de las dos ontologías

La integración de cuatro motores no es un problema, sino dos de naturaleza distinta:

- **Correlación de flujo** (aRGus, Suricata, Zeek): tres sensores de red que observan el mismo segmento L2 y emiten `community_id`, un identificador de flujo direccional-independiente. Es ingeniería esencialmente resuelta; el riesgo es de implementación.
- **Puente host↔red** (Wazuh): un HIDS/EDR basado en host. La mayoría de sus eventos nativos (FIM/syscheck, rootcheck, análisis de logs, SCA) **no poseen 5-tupla de red** y, por tanto, **no pueden tener `community_id`**. Es una incompatibilidad de modelo, no de implementación; el riesgo es de diseño.

### 2.2 Por qué ADR-046 v3 es insuficiente

Forzar `community_id` como clave primaria única sobre eventos de host obliga a una de dos patologías: `community_id` nulos/placeholder en la mayoría de eventos Wazuh (rompiendo la integridad referencial del grafo), o `community_id` sintéticos que no correlacionan con nada (contaminando el espacio de claves). En ambos casos, un NDR-EDR construido sobre PK única de flujo queda ciego a la mitad host de la kill-chain (persistencia, escalada, integridad de proceso, autenticación) — exactamente la telemetría por la que se integró Wazuh.

### 2.3 Marco FEDER (decisión D5)

El entregable para el hito FEDER (22-sep-2026) es **el pipeline funcional ejecutando un MITRE ATT&CK exigente y produciendo un dataset etiquetado, variado y reproducible**, cuyo fin es demostrar la **plausibilidad del entrenamiento distribuido federado** con argumentos científicos (potencialidad, no algoritmo final).

La aparente contradicción "ataque impredecible vs dataset reproducible" se resuelve separando el ataque de su captura:
1. El ataque MITRE se ejecuta **una vez, en vivo** (impredecible: demostración de intención y de detección realista).
2. Se **captura todo** y se sella. La captura es el artefacto inmutable.
3. El **dataset autoritativo** se genera por **reproceso offline de la captura sellada**, no del run en vivo.

Esto convierte la inmutabilidad, los timestamps canónicos, el replay reproducible y la estabilidad temporal en **requisitos estructurales**, no preferencias.

---

## 3. Decisión

### 3.1 Modelo dual de claves

Se adoptan dos claves de anclaje independientes:

- `community_id` — **clave de flujo**, opcional. Algoritmo Community ID v1 (`corelight/community-id-spec`): `"1:" + base64(SHA1(seed · addr_ordenada · addr_ordenada · proto · 0x00 · port_ordenado · port_ordenado))`, con canonicalización direccional (par menor primero), seed de 2 bytes en NBO (default 0, **idéntico en los tres sensores**), SHA1 vía OpenSSL/libcrypto (libsodium no expone SHA1), base64 estándar. Alcance: TCP/UDP/SCTP. ICMP diferido (`DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001`).
- `host_key` — **clave de host**. Intra-LAB = IP interna. El diseño admite `agent_id`/`hostname` para FEDER/producción. La premisa "IP = identidad de host estable" se marca `ASSUMPTION-LAB-ONLY` (colapsa bajo segmentación L3, DHCP dinámico o contenedores).

El puente entre dominios es temporal: un flujo con `community_id` que toca una IP interna gestionada se une a eventos host con `host_key` igual dentro de una ventana acotada (`bridge_window`).

### 3.2 Grafo temporal heterogéneo con aristas tipadas y asimétricas

El correlador opera sobre un **grafo unificado de eventos** con aristas tipadas y asimétricas:

- **`FLOW_IDENTITY`** (mismo `community_id`): equivalencia exacta → **fusiona** crisis.
- **`HOST_LOCALITY`** (mismo `host_key` interno gestionado, en ventana): no transitiva, con peso → **anota/enlaza**, no fusiona. (Previene la "crisis-monstruo" por IP ocupada.)
- **`TEMPORAL_BRIDGE`** (cross-clave, dentro de `bridge_window`): peso configurable.

El join host↔flujo es **asimétrico**: un evento de host se une al endpoint **interno/gestionado** del flujo (la víctima), no al atacante; requiere el inventario de §3.9.

**Invariante:** no se admiten crisis puramente temporales. Toda crisis exige al menos un anclaje estructural (`FLOW_IDENTITY` o `HOST_LOCALITY`).

### 3.3 Timestamp canónico y disciplina de reloj

`event_time_unix_ns` (tiempo de **ocurrencia** en la fuente, UTC) es el único campo que gobierna el *windowing*. No se usa tiempo de emisión ni de ingesta para las ventanas: incorporan latencia de detección variable por motor (el pipeline de Wazuh puede tardar segundos) que emborronaría la correlación.

Semántica por motor (a respetar en `AdapterSpec v1`):

| Motor | `event_time_unix_ns` |
|---|---|
| aRGus / Suricata / Zeek | timestamp de captura del paquete (Suricata `eve.timestamp`, Zeek `ts` = inicio de conexión) |
| Wazuh (alerta de red) | `timestamp` del evento fuente; fallback `alert.timestamp` |
| Wazuh (FIM/syscheck/rootcheck) | `alert.timestamp` (detección, no cambio); `scan_time` y `file_mtime` → `metadata` |

**Disciplina de reloj (R5):** NTP/chrony como gate de arranque P0 + monitorización continua (`chronyc tracking` en health-check). Ante skew > tolerancia, el engine degrada a **correlación débil** (ventanas ampliadas + `confidence = LOW_DUE_TO_CLOCK_SKEW`), nunca falla en silencio. La incertidumbre de cuantización de host (intervalo de escaneo) se absorbe por diseño en `bridge_window`.

> Latencia de pipeline (legítimamente grande; la maneja `source_wait_timeout`) ≠ skew de reloj (debe ser minúsculo; lo maneja el gate NTP). No confundirlas.

### 3.4 Fuentes esperadas dinámicas y ventanas separadas

Nunca `expected_sources = ALL`. Una fuente se **arma** cuando una arista conecta la crisis con su dominio. Wazuh se arma **solo** si la crisis toca un host gestionado; predicado = `host gestionado + dentro de bridge_window` (**no** cobertura de ruleset — ver §5). Tres ventanas distintas:

- `correlation_window`: espera activa de las fuentes armadas.
- `late_arrival_window`: gracia para rezagados; **no** reabre la espera.
- `crisis_idle_timeout`: cierre por inactividad; se resetea con actividad.

Cierre = (todas las fuentes armadas reportaron **y** vencida `correlation_window`) **O** `idle ≥ crisis_idle_timeout`.

### 3.5 Política de evicción en tres capas

Bajo saturación, la degradación **nunca bloquea la ingesta** y **siempre emite parcial**. Tres capas:

1. **Recencia.** Una crisis "caliente" (actividad estructural en `HOT_WINDOW`) no se evicta. El estado caliente se refresca con **actividad estructural** (nuevas aristas), no con goteo de baja severidad. `HOT_WINDOW` puede extenderse por severidad, nunca a inmunidad.
2. **Severidad como orden, nunca inmunidad.** En el conjunto frío, evicción por **tiers discretos** `LOW < MEDIUM < HIGH < FEDER_CRITICAL`, y **LRU estricto por `last_event_ts`** dentro de cada tier (determinismo de replay). Implementación O(1): una cola/ring-buffer LRU por tier. El `EvictionTier` operacional se modela como enum **separado** de la severidad intrínseca. (Una kill-chain temprana de baja severidad no queda atrapada: escala de tier por acreción al unírsele fases posteriores, y la protección caliente la mantiene fuera del frío mientras gana aristas.)
3. **Cuota anti-pinning.** Por **IP externa no gestionada individual** + **cap global** (`MAX_OPEN_CRISES`). Clasificación **fail-closed**: IP de clasificación desconocida → tratada como externa (sujeta a cuota), nunca exenta. Multi-origen: cada origen externo consume su cuota; la crisis es `EVICTION_FIRST` si **cualquiera** la excede. Las crisis ancladas a host interno (la víctima) están **exentas** de cuota y de evicción por severidad, pero acotadas por sub-cap por host + `crisis_idle_timeout` extendido.

> **Decisión de seguridad central:** la inmunidad absoluta por severidad es un vector de DoS de memoria (un atacante que dispare firmas graves fija estado y fuerza la evicción de todo lo demás). Las tres capas neutralizan el pinning *concentrado* (cuota) y el flood *distribuido* (cap global), protegen la víctima (exención interna) y conservan calidad (severidad como orden).

**Telemetría obligatoria:** enum `eviction_reason = {HOT_PROTECTED, SEVERITY_ORDER, QUOTA_EXCEEDED, GLOBAL_CAP, IDLE_TIMEOUT}`; métricas `open_crisis_count`, `evicted_by_anti_pin_quota`, `memory_rss`, `dedup_drops`. Memoria pre-asignada en chunks (sin fragmentación).

### 3.6 Horizonte de reordenamiento del engine

Como las ventanas se rigen por **ocurrencia** pero los eventos **llegan** en orden de arribo, el engine mantiene un buffer de reorden acotado y **no finaliza** una crisis hasta `ahora − latencia_de_la_fuente_armada_más_lenta`. La fuente más lenta (Wazuh, `source_wait_timeout` 90 s) fija el **horizonte de reorden** de todo el engine. Esta es la **razón** de que `crisis_idle_timeout` (120 s) > espera Wazuh (90 s): horizonte de reorden + margen, no coincidencia.

### 3.7 Inmutabilidad de crisis y modelo event-sourcing

Una crisis emitida es **inmutable**. El log de crisis es **append-only, ordenado temporalmente, replayable** — modelo event-sourcing:

```
CRISIS_CREATED  →  CRISIS_UPDATED_DELTA*  →  CRISIS_LATE_ARRIVAL*  →  CRISIS_CLOSED
```

- Un rezagado dentro de `late_arrival_window` genera un **delta enlazado** (`parent_crisis_id`, `delta_time_unix_ns`, `late_events`, `reason`), **nunca** mutación in situ. Varios rezagados → varios deltas, cada uno con su sello temporal.
- **`crisis_id` determinista** (no UUID aleatorio): `hash(clave_de_anclaje + min_event_time_ns + motor_anclador)`. El mismo input reprocesado genera los mismos IDs → datasets comparables entre runs.
- **Deltas con sello temporal propio** (`delta_time_unix_ns`): permiten reconstrucción **punto-en-tiempo**. Un delta a `T+50 s` no puede plegarse en una muestra cuyo corte de entrenamiento es `T` (fuga de futuro) — es lo que valida el split walk-forward de ADR-040.
- **Evento super-tardío** (llega tras cerrarse `late_arrival_window`): no se descarta en silencio ni muta la crisis cerrada; se emite como **registro propio** (singleton), marcado tardío-no-adjuntado.

**Dos modos de consumo, ambos configurables, uno activo por defecto, jamás mezclados** (leen el mismo log inmutable sin pisarse):
- *snapshot*: aplica todos los deltas → estado final.
- *time-bound*: ignora deltas posteriores a `read_timestamp` → "qué sabíamos en el momento X" (esencial para walk-forward).

### 3.8 Envelope común (`network_security.proto`)

Envelope plano, sin `oneof` (los motores de streaming y query optimizan mal `oneof`):

```protobuf
enum EventDomain { NETWORK = 0; HOST = 1; HYBRID = 2; }

message SecurityEvent {
  string source_engine                  = 1;   // argus | suricata | zeek | wazuh
  string native_event_id                = 2;   // dedup; determinista para golden pcap
  uint64 event_time_unix_ns             = 3;   // OCURRENCIA — canónico para windowing
  optional uint64 emitted_time_unix_ns  = 4;   // telemetría operativa (run-específica)
  optional uint64 ingested_time_unix_ns = 5;   // telemetría operativa (run-específica)
  optional string community_id          = 6;   // clave de flujo
  optional string host_key              = 7;   // clave de host
  EventDomain domain                    = 8;
  uint32 severity                       = 9;
  bytes  raw_payload                    = 10;
  map<string,string> metadata           = 11;  // agent_id, hostname, scan_time, file_mtime...
}
```

> Los números de campo definitivos deben evitar colisión con los campos ya existentes en `network_security.proto`; proto3 es backwards-compatible con campos nuevos no retirados. `emitted/ingested` son `optional`: el adapter que no los pueble (p. ej. tier determinista leyendo captura histórica) los omite. **Frontera de reproducibilidad:** `emitted_at`/`ingested_at` son telemetría operativa específica del run; no entran en el hash de identidad lógica ni en el ground-truth/etiquetas del dataset.

### 3.9 Inventario de endpoints como estado de primera clase

Registro `IP ↔ agent_id ↔ hostname ↔ managed_since`, alimentado desde Wazuh, consultado en caliente para: (a) armar fuentes (§3.4), (b) resolver el lado correcto del join asimétrico (§3.2), (c) clasificar interno/externo en la cuota anti-pinning (§3.5, fail-closed). Su correcto poblado **sostiene una propiedad de seguridad**, no es solo metadato.

### 3.10 Transporte y `AdapterSpec v1`

- **Tramo interno (adapter → engine): siempre ZeroMQ PUB/SUB** (invariante ADR-026/027; regla slow-joiner: PUB `bind()` antes de SUB `connect()`). El adapter publica el envelope `SecurityEvent`.
- **Tramo externo (herramienta → adapter): por tier y por motor.** Tier determinista = lectura de fichero/replay (reproducible). Tier vivo = push nativo donde el motor lo soporte (Suricata `eve`→redis/unix-socket; Zeek→Kafka/Redis vía plugin; Wazuh→socket), fallback tail-durable. **Congelado por motor y entorno**: nada de fallback silencioso en runtime. El camino push vivo no es replayable → libre de aserciones por construcción.
- **`AdapterSpec v1`** (documento normativo aparte): at-least-once + idempotencia por `(source_engine, native_event_id)`; **NO exactly-once** (declarado explícito; ya mitigado por dedup); checkpoint **monotónico** por transporte (offset de fichero / offset de topic / sequence number en envelope); `native_event_id` **determinista** para el golden pcap (offset-en-pcap + índice de evento); retry backoff exponencial; buffer acotado con `on_overflow = log_and_drop_with_metric`, nunca bloquear; health endpoint + métricas.

### 3.11 Reproducibilidad: artefacto autoritativo y `config_hash`

Existen dos vías de replay **no equivalentes**:
- **(A)** Congelar el pcap y **re-ejecutar los motores** → reproduce `community_id` (función pura) y `event_time`; **no** reproduce `emitted/ingested` ni el orden interno bajo carga.
- **(B)** Congelar el **stream de salida grabado** (envelopes + log de crisis append-only) → reproduce **todo**.

**Decisión:** el **artefacto autoritativo del dataset es (B)**, sellado una vez. El **pcap es compañero sellado de verificación** (re-derivar `community_id` para comprobar B; regenerar si hace falta). Ambos se retienen; no es un toggle. El log de crisis append-only (§3.7) es, por tanto, el artefacto autoritativo del que se genera el dataset.

**`config_hash`:** dado que los parámetros son configurables (§4), la reproducibilidad es **relativa a una configuración**. El contrato JSON se versiona y se hashea; el `config_hash` se **sella junto al dataset**. Definición operativa: *mismo stream de entrada congelado + mismo `config_hash` → mismo output bit-a-bit*. Esta es la concreción de la "frontera de reproducibilidad".

**Pluralidad de configuraciones / HA:** se permite correr varias configuraciones en paralelo (incluida una topología HA con nodos en modos distintos) como **streams auxiliares segregados, etiquetados y jamás fundidos**. Para FEDER, **exactamente una** configuración es la **canónica** (su `config_hash` es el de referencia del corpus); las demás son material de investigación/observabilidad, no corpus. Tras la experimentación, la mejor configuración se congela como canónica.

### 3.12 Parámetros por JSON vs estructura por código

- **Escalares configurables por contrato JSON** desde el día uno (validado al cargar: esquema + cotas, **fail-closed**): los de §4.
- **Estructura por código + revisión de ADR**, no por JSON: el comparador de evicción (tier → LRU), la máquina de ventanas, el modelo event-sourcing, las definiciones de aristas. El `config_hash` cubre lo que esté en vigor; la disciplina previene de raíz datasets no comparables por un cambio de estructura encubierto en config.

---

## 4. Parámetros configurables (defaults de arranque)

> Adoptados como punto de partida; se ajustarán con evidencia tras la experimentación virtualizada y en hardware real. Un valor que se demuestre estable puede congelarse a compilado en una revisión futura.

| Parámetro | Default LAB | Nota |
|---|---|---|
| `community_id.seed` | 0 | Idéntico en aRGus/Suricata/Zeek |
| `bridge_window` | 15–30 s | Join host↔flujo; absorbe cuantización de host |
| `correlation_window` | por fuente | aRGus 5 s / Suricata 10 s / Zeek 20 s / Wazuh 90 s |
| `late_arrival_window` | a fijar | Separada de `correlation_window` |
| `crisis_idle_timeout` | 120 s; ~300 s host interno | > espera Wazuh por horizonte de reorden (§3.6) |
| `HOT_WINDOW` | 5 s (extensible por severidad) | Refrescado por actividad estructural |
| `MAX_OPEN_CRISES` | 10 000 | ≈ 20 MB a ~2 KB/crisis |
| `Q` (cuota anti-pinning) | 0.05 LAB / 0.02 FEDER | Fracción de `MAX_OPEN_CRISES` por IP externa |
| sub-cap por host interno | generoso, configurable | Anti spoofing de IP interna |
| tolerancia de reloj | gate 50 ms / warning 10 ms | Degradación a `confidence=LOW` si se excede |
| modo de consumo | snapshot \| time-bound | Ambos disponibles; uno por defecto |

---

## 5. Alternativas consideradas y rechazadas

| Alternativa | Por qué se rechazó |
|---|---|
| `community_id` como PK única (ADR-046 v3) | Excluye estructuralmente a Wazuh-host; ceguera a la mitad host de la kill-chain. |
| Timestamp de **emisión** para windowing | Incorpora latencia de detección variable por motor; emborrona las ventanas. |
| Acoplar el predicado de "fuente esperada" al **ruleset de Wazuh** | Viola separación de capas; frágil ante cambios de reglas. La expectativa muerta ya está acotada por `correlation_window`. |
| **Inmunidad absoluta por severidad** en evicción | Vector de DoS de memoria (severity pinning). |
| **Score continuo** (`severidad × fuentes × 1/edad`) para evicción | Opaco, no demostrable anti-pinning; el factor `fuentes` es inflable por el atacante. |
| Cuota anti-pinning por `/24` o por `community_id` | `/24` agrupa orígenes legítimos co-ubicados; `community_id` es redundante con la cuota por IP. (Anotados como tuning post-FEDER.) |
| **Mutación in situ** de crisis emitidas | Hace el dataset función del momento de lectura; rompe reproducibilidad y walk-forward. |
| Re-ejecutar motores (vía A) como fuente autoritativa del dataset | No reproduce timestamps de emisión/ingesta ni el orden interno bajo carga. (Se retiene como verificación.) |

---

## 6. Consecuencias

**Positivas.** Wazuh recupera rol de primera clase sin contaminar el espacio de claves. El correlador es un runtime de grafo temporal con event-sourcing, naturalmente replayable y serializable a Neo4j (post-FEDER). La política de degradación es demostrable y resistente a DoS. El dataset es reproducible (relativo a `config_hash`), apto para walk-forward y para particionado federado. El acuerdo `community_id` cross-motor es, en sí, un resultado publicable.

**Negativas / coste.** Mayor complejidad que una PK única: dos claves, inventario de endpoints como estado de primera clase, buffer de reorden, log event-sourcing. El horizonte de reorden (90 s) impone latencia de finalización de crisis. La reproducibilidad exige sellar B + pcap + `config_hash` en cada run.

**Riesgos.** (1) El inventario de endpoints sostiene propiedades de seguridad; un inventario mal poblado degrada la cuota anti-pinning (mitigado: fail-closed). (2) Reloj adversarial: un host comprometido que mienta sobre su tiempo evade la correlación temporal — fuera de alcance FEDER (`DEBT-ARGUSPP-CLOCK-ADVERSARIAL-001`). (3) Recursos: el pipeline + server puede no caber concurrente en 32 GB; mitigación primaria = time-slice server↔pipeline (server asíncrono y aguas abajo del horizonte NTP); pendiente medir RSS de `defender`.

---

## 7. Validación (EMECAS++)

Nuevo tier determinista sobre golden pcap, además del tier de realismo. Tests obligatorios:

- **Acuerdo cross-motor:** mismo flujo → `community_id` idéntico en aRGus, Suricata, Zeek y `community-id.py --seed 0`. ICMP presente en el pcap con aserción de **abstención** (no emitir `community_id` erróneo).
- **Determinismo de replay:** mismo input congelado + mismo `config_hash` → mismo output bit-a-bit (incluidos `crisis_id`).
- **Evicción:** (a) 100 000 flujos únicos/60 s → RSS acotado, sin leak, todas las crisis cierran; (b) pinning concentrado desde un origen externo → las crisis de host interno sobreviven, cuota aplicada (`evicted_by_anti_pin_quota`); (c) escenario mixto (fondo normal + pinning + incidente real sobre host interno) → el incidente real nunca se evicta.
- **Degradación:** matar la VM Wazuh a mitad de run → las crisis siguen cerrando, sin crecimiento ilimitado, correlación de flujo intacta, marcador de degradación presente.
- **Inmutabilidad:** un rezagado genera delta enlazado, no muta el original; super-tardío → registro propio.

---

## 8. Deudas y diferidos

- `DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001` — soporte ICMP (type/code → pseudo-puertos). Post-FEDER.
- `DEBT-ARGUSPP-CLOCK-ADVERSARIAL-001` — reloj adversarial; sellar eventos de host en el manager de Wazuh, no en el agente. Post-FEDER.
- Optimización no acoplada de expectativas muertas (heartbeat asíncrono de Wazuh / filtro por metadatos de regla). Post-FEDER.
- Cuota por `/24` y por `community_id` como tuning. Post-FEDER.
- **Pasada 4 — Contrato del dataset federado:** esquema Parquet, etiquetado MITRE por fase de kill-chain, particionado por `host_key`/`community_id`, integridad walk-forward, y formalización del artefacto autoritativo (§3.11). Atado a ADR-040.

---

## 9. Referencias

- `corelight/community-id-spec` (algoritmo Community ID v1).
- ADR-040 (ML Plugin Retraining Contract: walk-forward, golden set inmutable, guardrail −2 %, IPW+exploración).
- ADR-047 (resiliencia en capas), ADR-048 (etcd HA / correlación F2), ADR-026/027 (ZeroMQ PUB/SUB).
- Deliberación del Consejo de Sabios, DAY 169: Pasadas 1–3 (síntesis, mociones M1–M4, micro-mociones P3.1–P3.4) y voto final de Alonso.