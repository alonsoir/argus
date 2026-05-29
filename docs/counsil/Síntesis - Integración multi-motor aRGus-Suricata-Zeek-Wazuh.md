# Consejo de Sabios — Síntesis de la Pasada 1 y agenda de la Pasada 2

**Proyecto:** aRGus NDR (arXiv:2604.04952)
**Sesión:** DAY 169 — viernes 29 de mayo de 2026
**Redacta:** Claude (Anthropic), a partir de las ocho posiciones recibidas
**Posiciones leídas (8/8):** Claude, ChatGPT, DeepSeek, Gemini, Grok, Qwen, Kimi, Mistral
**Objeto:** separar lo que ya es consenso (adoptable) de lo que tiene discrepancia real (requiere otra pasada), sin atajos.

---

## 0. Notas de procedimiento

1. **Atribución a verificar.** El fichero etiquetado `DEEPSEEK` está firmado como *ChatGPT (OpenAI)*, y existe un fichero `CHATGPT` independiente. Una de las dos posiciones está mal rotulada. En la matriz se tratan por nombre de fichero; Alonso debe confirmar la autoría real antes de cerrar votos.
2. **Decisividad desigual.** La posición de Mistral es de tipo survey (apela a prácticas de industria sin fuentes verificables y se abstiene en Q6 y Q9). Se computa donde compromete postura; no se usa para inflar unanimidad donde no la hay.

---

## 1. Matriz de consenso

| Q | Tema | Estado | Detalle |
|---|------|--------|---------|
| Q1 | Dos claves vs PK única | **UNÁNIME (8/8)** | Modelo dual `community_id` + `host_key`. |
| Q2 | Grafo de correlación | **UNÁNIME (8/8)** | Grafo temporal heterogéneo, aristas tipadas. Asimetría flujo/host: consenso fuerte. |
| Q3 | Fuentes esperadas | **UNÁNIME en el principio (8/8)** | Computadas dinámicamente, nunca `expected = ALL`. (Predicado fino: discrepancia menor.) |
| Q4 | Wazuh ingiere eve.json | **UNÁNIME (8/8)** | No. Adapter por motor + dedup `(source_engine, native_event_id)`. |
| Q5 | Timestamp canónico | **DISCREPANCIA (7 vs 1)** | 7 = tiempo de ocurrencia; Qwen = tiempo de emisión. Tolerancia ≈50 ms (Grok 100 ms). |
| Q6 | Recursos / VMs | **CONSENSO (8/8)** | Perfil ligero + arranque secuencial + caja CI para el tier pesado/vivo. |
| Q7 | Cota + evicción | **PRINCIPIO UNÁNIME / POLÍTICA DISCREPANTE (≈4 vs 4)** | Cota dura + degradar-emitir-parcial + nunca bloquear: unánime. Política de evicción: dividida. |
| Q8 | Alcance protocolo | **UNÁNIME (8/8)** | TCP/UDP/SCTP dentro; ICMP diferido (DEBT firmado); `community_id` opcional. |
| Q9 | Corpus vs pipeline | **CONSENSO FUERTE (6 corpus / 1 pipeline / 1 abstención)** | Decisión estratégica de Alonso; el Consejo se inclina a corpus-first. |

---

## 2. Bloque de adopción inmediata (sin más pasadas)

Estas resoluciones tienen respaldo unánime o de consenso fuerte y pueden bajarse ya a contrato (`network_security.proto`) y a **ADR-046 v4**.

**R1 — Modelo dual de claves.** `community_id` (clave de flujo, **opcional**) + `host_key` (clave de host). Para LAB `host_key = IP interna`; el diseño **debe** admitir `agent_id`/`hostname` para FEDER/producción. La premisa P3 (IP = identidad de host) queda marcada `ASSUMPTION-LAB-ONLY` (catch de Kimi): colapsa bajo segmentación L3, DHCP dinámico o contenedores; no usarla como invariante silenciosa.

**R2 — Grafo temporal heterogéneo con aristas tipadas y asimétricas.**
- *Identidad-de-flujo* (mismo `community_id`): equivalencia exacta → **fusiona** crisis.
- *Localidad-de-host* (mismo `host_key` interno gestionado, en ventana): temporal, **no transitiva**, con peso → **anota/enlaza**, no fusiona. (Evita la "crisis-monstruo" por IP ocupada.)
- *Puente temporal cross-clave* (flujo toca IP interna + evento host en ventana): peso configurable.
- **Invariante (Kimi):** no se admiten crisis puramente temporales; toda crisis exige al menos un anclaje estructural (flujo o host). *(Pendiente menor: consolidar si son 2 o 3 tipos de arista — ver §4.D4.)*

**R3 — Fuentes esperadas dinámicas.** Nunca `expected = ALL`. `source_wait_timeout` se aplica **solo** a fuentes esperadas ya armadas; los *late arrivals* se admiten hasta `crisis_idle_timeout`. Una fuente se arma cuando una arista conecta la crisis con su dominio (p. ej., Wazuh se arma cuando la crisis toca un host gestionado — entonces, y solo entonces, corre su ventana de 90 s).

**R4 — Ingesta sin eco.** Wazuh **no** ingiere `eve.json`. Cada motor entra por su adapter; deduplicación por `(source_engine, native_event_id)` como cinturón-y-tirantes.

**R5 — Disciplina de reloj** *(la mitad de monitorización es unánime; la definición del campo va a §4.D1).* NTP/chrony como gate de arranque P0 **y** monitorización continua (`chronyc tracking` en health-check). Ante skew > tolerancia, el engine **degrada** a "correlación débil" (ventanas ampliadas + `confidence = LOW_DUE_TO_CLOCK_SKEW`), no falla en silencio. Tolerancia LAB ≈ 50 ms.

**R6 — Validación por tiers.**
- *Tier determinista (golden):* pcap fijo + `tcpreplay` + `community_id` precalculados; aserciones inmutables en CI. Wazuh entra por **fixtures de `alerts.json` reproducidos**, no por manager vivo (saca 2–4 GB del camino crítico y mejora el determinismo).
- *Tier realismo:* `nmap`/`hydra`/atomic-red-team en vivo; smoke/fidelity, sin aserciones deterministas.
- VMs con perfil ligero (Wazuh sin Elasticsearch/indexer, salida a fichero), arranque secuencial; caja CI dedicada para el multi-VM pesado.

**R7 — Resiliencia del engine** *(la política de evicción va a §4.D2).* Cota dura de crisis abiertas + degradación que **emite parcial** + **nunca bloquea la ingesta**. Métricas instrumentadas desde el día 1: `open_crisis_count`, `evictions_total`, `late_arrivals_total`, `dropped_correlations_total`, `correlation_latency_ms`, `memory_rss`. (Son, además, lo que permite *dimensionar* la cota y *demostrar* ADR-047.)

**R8 — Alcance de protocolo.** TCP/UDP/SCTP dentro para FEDER; ICMP diferido → firmar `DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001`. El golden pcap **incluye** ICMP y el test asegura que aRGus se **abstiene** correctamente (no emite `community_id` erróneo). `community_id` opcional en el contrato.

**R9 — Envelope plano, sin `oneof`** (consenso de Qwen, Kimi, Grok, ChatGPT, DeepSeek; los motores de streaming y query optimizan mal `oneof`):
```protobuf
message SecurityEvent {
  string source_engine      = 1;   // argus | suricata | zeek | wazuh
  string native_event_id    = 2;   // para dedup
  uint64 event_time_unix_ns = 3;   // CANÓNICO (ver D1) — tiempo de OCURRENCIA, UTC
  optional string community_id = 4;
  optional string host_key     = 5;
  EventDomain domain         = 6;   // NETWORK | HOST | HYBRID
  uint32 severity            = 7;
  bytes  raw_payload         = 8;
  map<string,string> metadata = 9; // ingested_at, emitted_at, agent_id, hostname...
}
```

**R10 — Inventario de endpoints como estado de primera clase** (Qwen, Kimi, DeepSeek, Grok, Mistral). Registro `IP ↔ agent_id ↔ hostname ↔ managed_since`, alimentado desde Wazuh, consultado en caliente para decidir `expected_sources` y el lado correcto del join asimétrico. *(Forma — servicio gRPC/HTTP vs config recargable — a decidir en §4.)*

---

## 3. Lo que NO es discrepancia, solo dimensionado empírico

No requieren debate, sino una medición o un valor de arranque parametrizable:

- **Cota de crisis (Q7):** arranque en **10.000** (cluster mayoritario; Kimi da la cuenta: ~2 KB/crisis → ~20 MB). El `1.000` de DeepSeek queda como conservador; se eleva salvo defensa. Valor final = `memory_limit / avg_crisis_size`, medido.
- **Tolerancia de reloj LAB (Q5):** 50 ms (Grok propone 100 ms como margen). Medir offset real con chrony y fijar.
- **`bridge_window` host↔flujo:** arranque 15 s (Qwen) / 30 s (DeepSeek). Configurable, distinta de las ventanas de crisis; tunear con el golden pcap.
- **Número de tipos de arista (R2):** 2 vs 3 — cosmético sobre el mismo modelo; consolidar al escribir ADR-046 v4.

---

## 4. Discrepancias para la Pasada 2

### D1 — Timestamp canónico: ocurrencia vs emisión *(7 vs 1)*
**Split:** siete miembros = tiempo de **ocurrencia** del evento en la fuente (captura libpcap para sensores; generación de alerta para Wazuh). Qwen = tiempo de **emisión** al adapter, conservando `ts_capture`/`ts_event` como metadato.
**Problema técnico:** el tiempo de emisión incorpora la latencia interna de detección de cada motor (el pipeline de Wazuh log→decoder→alerta puede tardar segundos), que es **variable por motor y por evento**. Usarlo para el *windowing* emborrona la ventana y sabotea justo la correlación que construimos.
**Reconciliación propuesta:** el campo canónico para *windowing* es la **ocurrencia**; la **emisión** (lo que Qwen quiere preservar) y la **ingesta** van en `metadata` como `emitted_at`/`ingested_at` para telemetría de latencia. Esto **no descarta** el dato de Qwen — solo decide cuál gobierna las ventanas. La propuesta de Qwen ya guardaba `ts_event` como metadato; basta invertir cuál es el canónico.
**Pregunta a Qwen:** ¿concedes ocurrencia-para-windowing + emisión-como-metadato, o defiendes emisión para las ventanas? Si lo segundo, expón el caso contra el emborronamiento por latencia variable.

### D2 — Política de evicción: neutral-por-recencia vs ponderada-por-severidad *(≈4 vs 4)* — **la discrepancia con filo de seguridad**
**Split:**
- *Neutral / recencia:* Claude (LRU puro), Gemini (LRU), Mistral (LRU/FIFO), Kimi (LRU + protección de crisis "calientes", < 5 s).
- *Ponderada por severidad:* ChatGPT (severidad + LRU), DeepSeek (LRU + shedding de baja severidad), Grok (score = severidad × fuentes × edad⁻¹), Qwen (**nunca** evictar `HIGH`/`FEDER_CRITICAL`).
  **Hallazgo que nadie desarrolló del todo:** la inmunidad absoluta por severidad (Qwen) **es un vector de DoS de memoria**. Un atacante que sepa disparar firmas de severidad alta puede *fijar* (pin) estado en el correlador y forzar la evicción de **todas las demás** crisis — incluida la que de verdad importa. En un NDR, la propia política de protección se convierte en arma. El enfoque por recencia es neutral al ataque pero puede tirar una crisis importante de construcción lenta.
  **Reconciliación propuesta (síntesis de los dos bandos):**
1. Proteger crisis **calientes** por recencia (Kimi) — neutral al ataque.
2. En el conjunto **frío**, usar severidad como **criterio de orden** de evicción, **nunca** como inmunidad absoluta.
3. **Cuota anti-pinning:** ningún `source_ip` ni clase de severidad puede ocupar más de una fracción X de la cota total. Esto neutraliza el vector de Qwen conservando su intención (que lo grave no se pierda primero).
   **Pregunta al Consejo (en especial Qwen, Grok, ChatGPT, DeepSeek):** ¿aceptáis severidad-como-orden-no-inmunidad + cuota anti-pinning, en lugar de inmunidad absoluta? ¿Y la protección por recencia de Kimi como capa base?

### D3 — Transporte de los outputs externos: push vs tail-durable
**Split (entre los que se mojan):** push-based = Grok (ZeroMQ/Redis streams/Filebeat), Kimi (ZeroMQ PUB/SUB con topics tipados, coherente con ADR-026/027 del propio proyecto); tail-durable = Qwen (inotify + rename atómico + offset en SQLite/leveldb, exactly-once idempotente), DeepSeek (tail + offset durable). Mistral tiende a push vía Filebeat. Claude/ChatGPT/Gemini no se comprometieron.
**Matiz que cambia el marco:** no es una decisión global. (a) El sniffer **propio** de aRGus ya emite por **ZeroMQ nativo** (ADR-026/027) — ahí no hay debate. (b) Suricata/Zeek/Wazuh escriben **ficheros** (`eve.json`, `conn.log`, `alerts.json`); el dilema es solo cómo sacarlos de ahí. (c) El **tier determinista** necesita leer un **fichero fijo replayable** — un stream push no es trivialmente reproducible. El tier vivo prima resiliencia.
**Reconciliación propuesta (por tier y por motor):**
- *Tier determinista:* leer fichero/replay (es el punto entero de la reproducibilidad).
- *Tier vivo:* push nativo donde el motor lo soporta (Suricata `eve`→redis/unix-socket; Zeek→Kafka/Redis vía plugin; Wazuh→socket output); si no, tail-durable (inotify + offset persistente + dedup idempotente).
- Ambos transportes deben cumplir un **`AdapterSpec v1`** común (Qwen): persistencia de offset o equivalente, idempotencia, retry con backoff, health endpoint.
  **Pregunta a Grok/Kimi (push) y Qwen/DeepSeek (tail):** ¿aceptáis la resolución por-tier-y-por-motor bajo un `AdapterSpec v1` único, o alguien defiende un transporte único para todo?

### D4 — Precisión del predicado de "fuente esperada" (refinamiento de Q3)
El **principio** (dinámico) es unánime. Quedan dos refinamientos:
- **(a) Separar `correlation_window` de `late_arrival_window`** (ChatGPT): no usar un solo timeout para "esperar correlación" y "admitir rezagados". *Inclinación Claude: adoptar — es limpio.*
- **(b) Condición extra de Qwen:** "Wazuh es esperado solo si existe una **regla Wazuh que cubra el protocolo/puerto** en esa IP". *Inclinación Claude: rechazar* — acopla el correlation-engine al estado interno del ruleset de Wazuh (frágil, violación de capas); basta con "host gestionado + dentro de `bridge_window`".
  **Pregunta a Qwen:** ¿defiendes la condición de regla-Wazuh, o basta con host-gestionado? **Pregunta al Consejo:** ¿adoptamos la separación correlation/late-arrival window?

### D5 — Q9: corpus vs pipeline como entregable duro del 22-sep *(decisión de Alonso)*
**Estado:** seis miembros corpus-first (Claude, ChatGPT, DeepSeek, Gemini, Qwen, Kimi), Grok se inclina a pipeline-como-entregable-principal, Mistral se abstiene. **Matiz unificador:** incluso Grok quiere el corpus en paralelo desde la Fase 0, y todos coinciden en que el corpus es el **sustrato de validación contra el que se prueba el pipeline**. Es decir, *corpus-como-cimiento* es de facto unánime; lo único abierto es si el **pipeline vivo** es entregable **duro** del 22-sep o una **demo grabada** complementaria.
**Argumento de Grok (a tener en cuenta):** el Dr. Caro Lindo puede querer evidencia de funcionamiento **en vivo**, no solo un dataset estático.
**Pregunta a Alonso (la que reordena las fases):** para el 22-sep, ¿el pipeline vivo es requisito de entrega o demostración complementaria? Tu respuesta fija si el golden-pcap+etiquetado sube a Fase 0/1 (corpus-first) o si las Fases 5–6 se invierten.

---

## 5. Agenda de la Pasada 2

Para no dispersar, la Pasada 2 debería cerrar **solo** estos cinco puntos:

1. **D1** — Qwen responde sobre timestamp (probable cierre rápido: ocurrencia + emisión-metadato).
2. **D2** — el Consejo vota severidad-como-orden + cuota anti-pinning + protección por recencia. *(El de mayor enjundia; lleva implicación de seguridad.)*
3. **D3** — validar `AdapterSpec v1` + transporte por-tier.
4. **D4** — separar ventanas (sí/no) y zanjar la condición regla-Wazuh.
5. **D5** — **decide Alonso**; el Consejo solo ejecuta el reordenamiento de fases que se derive.

Todo lo de §2 puede empezar a bajarse a `network_security.proto` y al borrador de **ADR-046 v4** en paralelo, porque no depende de las discrepancias abiertas.

— Claude (Anthropic), Consejo de Sabios. *Piano, piano — pero el contrato wire ya tiene cimiento.*

# Consejo de Sabios — Pasada 2: mociones para cierre

**Proyecto:** aRGus NDR (arXiv:2604.04952)
**Sesión:** DAY 169 — viernes 29 de mayo de 2026
**Redacta:** Claude (Anthropic)
**Objeto:** cerrar las cinco discrepancias abiertas de la Pasada 1. Cada punto se presenta como **moción con resolución propuesta**; cada miembro **ratifica** o **rebate con argumento técnico concreto**. El bloque de adopción de la Pasada 1 (R1–R10) no se reabre.

> Regla de la pasada: una moción se considera **cerrada** si obtiene ratificación sin objeción técnica sustantiva. Una objeción debe proponer alternativa, no solo señalar un defecto.

---

## Moción M1 (D1) — Timestamp canónico

**Resolución propuesta:** el campo canónico para *windowing* es el **tiempo de ocurrencia** en la fuente (`event_time_unix_ns`, UTC). El tiempo de **emisión** (propuesta de Qwen) y el de **ingesta** se conservan en `metadata` como `emitted_at`/`ingested_at`, exclusivamente para telemetría de latencia. Las ventanas de correlación **nunca** usan emisión ni ingesta.

**Razonamiento:** el tiempo de emisión incorpora la latencia interna de detección de cada motor —el pipeline de Wazuh (log → decoder → alerta) puede tardar segundos, variable por evento—. Usarlo para *windowing* introduce ruido no acotado justo en la dimensión que la correlación necesita limpia.

**Steelman de la objeción (Qwen) y respuesta:** es cierto que el tiempo de ocurrencia es tan fiable como el reloj de la fuente, y que para eventos de host (p. ej. FIM) "ocurrencia" es difuso —syscheck reporta cuando *escanea*, no cuando el fichero cambió—. Respuesta: (1) la fiabilidad del reloj ya la gobierna R5 (gate NTP + monitorización + degradación a `confidence=LOW`); la emisión es *también* una lectura de reloj y no escapa a ese problema, solo le **suma** latencia variable; (2) la incertidumbre de cuantización de host (intervalo de escaneo de syscheck) se **absorbe por diseño** en el `bridge_window` host↔flujo (15–30 s), que precisamente por esto es ancho y no estrecho. Conclusión: la emisión va a metadato; la ocurrencia gobierna las ventanas; la incertidumbre de host queda documentada y absorbida.

**Cierre si:** Qwen concede emisión-como-metadato, o defiende emisión-para-windowing exhibiendo un caso donde la latencia variable de detección *no* emborrone la ventana.

---

## Moción M2 (D2) — Política de evicción *(la de mayor enjundia; lleva implicación de seguridad)*

**Resolución propuesta — evicción en tres capas, severidad como orden y nunca como inmunidad:**

1. **Capa 1 — Protección por recencia (Kimi).** Una crisis "caliente" (con eventos en los últimos `HOT_WINDOW`, p. ej. 5 s) **nunca** se evicta. Es neutral al ataque y evita destruir crisis en construcción activa.
2. **Capa 2 — Severidad como orden en el conjunto frío.** Entre crisis frías, se evicta por severidad ascendente y, a igual severidad, por `last_event_ts` ascendente. Lo grave se evicta **el último**, pero **no es inmune**: si todo es de severidad alta, se evicta la más fría de severidad alta. (Esto recupera la intención del bando "severidad" — no perder lo grave primero — sin su defecto.)
3. **Capa 3 — Cuota anti-pinning sobre anclajes externos/no confiables.** Ningún `source_ip` externo (ni `/24`) puede ocupar más de una fracción `Q` de `MAX_OPEN_CRISES` (p. ej. 1–5 %). Las crisis ancladas **solo** a un origen que excede su cuota pasan a **eviction-first**, con independencia de su severidad. Las crisis ancladas a un **host interno gestionado** (la víctima) están **exentas** de cuota.

**El hallazgo de seguridad que esto resuelve:** la inmunidad absoluta por severidad (propuesta de Qwen: "nunca evictar `HIGH`/`FEDER_CRITICAL`") es un **vector de DoS de memoria**. Un atacante que sepa disparar firmas de severidad alta fija (pin) estado en el correlador y fuerza la evicción de todo lo demás — la protección se convierte en arma. La Capa 3 lo neutraliza: el atacante no puede fijar más allá de su cuota; y como las crisis de **host interno** están exentas, lo que el atacante *no* puede tirar es precisamente a la víctima.

**Interacción con R2 (coherencia, no coincidencia):** un único origen ruidoso *debería* producir **menos** crisis, no más, porque sus eventos correlacionan entre sí (aristas de localidad-de-host / mismo-origen). Si un origen genera muchas crisis **no correlacionables**, eso ya **es** la señal — y acotarlo por cuota es correcto, no una pérdida. La asimetría interno/externo de R2 se hereda en la evicción: el host interno se protege; el origen externo se acota.

**Demostración en EMECAS++ (amplía el test de Kimi):**
- (a) Inyección de 100.000 flujos únicos en 60 s → RSS acotado, sin leak, todas las crisis cierran.
- (b) **Escenario de pinning:** un único origen externo genera N crisis de severidad alta → asegurar que las crisis de host interno **sobreviven**, que la cuota se aplica, y que la memoria sigue acotada.
- Las crisis evictadas por saturación emiten parcial con flag `SATURATED_EVICTION`.

**Cierre si:** los bandos severidad (Qwen, Grok, ChatGPT, DeepSeek) y recencia/neutral (Claude, Gemini, Kimi, Mistral) aceptan "severidad-orden + cuota anti-pinning + protección por recencia". Objeción válida = un escenario donde esta política pierde una crisis que *debía* conservar, o un vector de pinning que la cuota no cubre.

---

## Moción M3 (D3) — Transporte de adapters

**Reencuadre que disuelve el desacuerdo:** el debate "push vs tail" mezclaba **dos tramos distintos**:
- **Tramo interno (adapter → engine):** siempre **ZeroMQ** (invariante del proyecto, ADR-026/027; regla de slow-joiner: PUB hace `bind()` antes de que SUB haga `connect()`). Aquí no hay debate — la propuesta ZMQ de Kimi *ya es* la arquitectura. El adapter, lea como lea, **publica el envelope R9** al bus interno.
- **Tramo externo (herramienta → adapter):** es el único en disputa, y se resuelve **por tier y por motor**.

**Resolución propuesta:**

| Tramo / contexto | Transporte |
|---|---|
| Interno adapter→engine (siempre) | ZeroMQ PUB/SUB, envelope R9 |
| Sniffer propio aRGus | ZeroMQ nativo (sin cambios) |
| Tier determinista (golden) | Lectura de fichero fijo / replay (reproducible) |
| Tier vivo — Suricata | `eve` → redis / unix-socket nativo; *fallback*: tail durable |
| Tier vivo — Zeek | Kafka/Redis vía plugin; *fallback*: tail durable |
| Tier vivo — Wazuh | socket de salida; *fallback*: tail durable |

Todo adapter, sea cual sea el tramo externo, cumple **`AdapterSpec v1`** (Qwen): offset/checkpoint durable o posición de replay equivalente, idempotencia por `(source_engine, native_event_id)`, retry con backoff exponencial, *health endpoint*, buffer acotado con backpressure-sin-pérdida (o contabilidad explícita de pérdida).

**Cierre si:** push (Grok, Kimi) y tail-durable (Qwen, DeepSeek) aceptan que hablaban de tramos distintos y ratifican `AdapterSpec v1` + tabla por-tier. Objeción válida = un motor donde ni push nativo ni tail-durable cumplen el spec.

---

## Moción M4 (D4) — Predicado de "fuente esperada"

**M4.a — Separar ventanas. Resolución: ADOPTAR.** Distinguir `correlation_window` (ventana activa en que la crisis espera a sus fuentes armadas) de `late_arrival_window` (gracia posterior en que un evento rezagado aún se adjunta pero **no** reabre la espera completa). Cierre de crisis = `idle ≥ crisis_idle_timeout` (120 s, se resetea con actividad) **O** (todas las fuentes armadas-esperadas reportaron **y** vencida `correlation_window`).

**M4.b — Condición "regla Wazuh cubre proto/puerto" (Qwen). Resolución: RECHAZAR, pero reconociendo que ataca un problema real ya mitigado.**
- *Por qué se rechaza la implementación:* acopla el correlation-engine al estado interno del ruleset de Wazuh — frágil, viola la separación de capas, y rompe en cuanto alguien edita reglas sin tocar el engine.
- *Por qué la preocupación es legítima:* armar Wazuh como "esperado" en *todo* flujo que toque un host gestionado crea expectativas muertas (Wazuh podría no tener nada que decir sobre ese flujo) — es el problema de INQ-3 en pequeño.
- *Por qué ya está mitigado sin acoplar:* por M4.a + R3, una fuente armada-pero-silenciosa **no bloquea** el cierre; su coste máximo es el timeout, no un *hang*. Por tanto, "host gestionado + dentro de `bridge_window`" basta como predicado; la precisión que busca Qwen la da la estructura de ventanas acotadas, no el conocimiento del ruleset.

**Cierre si:** se adopta M4.a y Qwen concede que las ventanas acotadas resuelven su preocupación sin el acoplamiento, o defiende por qué el coste-timeout de una expectativa muerta es inaceptable pese a estar acotado.

---

## D5 (Q9) — En espera de decisión de Alonso

No es una moción del Consejo: es decisión estratégica de Alonso. El Consejo se inclina 6-a-1 a **corpus-como-cimiento** (y hasta Grok lo quiere en paralelo desde Fase 0), de modo que *corpus-foundational* es de facto unánime. Lo único abierto:

> Para el 22-sep, ¿el **pipeline vivo** es **requisito de entrega** o **demostración complementaria** al corpus?

Las dos ramas de ordenamiento de fases están listas para instanciarse en cuanto Alonso responda:
- **Pipeline = demo complementaria** → golden-pcap + etiquetado suben a Fase 0/1; correlación determinista contra corpus es el núcleo; el vivo es E2E sin aserciones.
- **Pipeline = entregable duro** → se invierten Fases 5–6; los E2E vivos pasan a tener aserciones (probabilísticas, con repeticiones para estabilidad estadística).

---

## Estado tras la Pasada 2

- **M1, M3, M4** son reconciliaciones de bajo riesgo; espero cierre rápido salvo defensa de Qwen en M1/M4.b.
- **M2** es la que merece deliberación real — lleva la decisión de seguridad. Es donde pido al Consejo que más apriete.
- **D5** desbloquea el ordenamiento de fases en firme; pende de Alonso.
- En paralelo, R1–R10 ya pueden bajarse a `network_security.proto` y al borrador de **ADR-046 v4**.

— Claude (Anthropic), Consejo de Sabios. *Piano, piano.*