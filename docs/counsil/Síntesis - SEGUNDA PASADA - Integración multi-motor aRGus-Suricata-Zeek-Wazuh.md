# Consejo de Sabios — Cierre de la Pasada 2, contenido firme de ADR-046 v4, y Pasada 3 (residual)

**Proyecto:** aRGus NDR (arXiv:2604.04952)
**Sesión:** DAY 169 — viernes 29 de mayo de 2026
**Redacta:** Claude (Anthropic), sobre las ocho posiciones de la Pasada 2
**Objeto:** (A) declarar el resultado de M1–M4; (B) fijar el contenido firme que entra en ADR-046 v4; (C) abrir una Pasada 3 mínima con las cuatro micro-bifurcaciones que aún no están cerradas entre los miembros; (D) estado de D5.

---

## A. Resultado de la Pasada 2

| Moción | Resultado | Notas |
|---|---|---|
| M1 — Timestamp de ocurrencia | **RATIFICADA 8/8** | Qwen **concede** (era el disidente). |
| M2 — Evicción en tres capas | **RATIFICADA 8/8** | Hallazgo de pinning validado por todos, incl. Qwen, que originó la idea de inmunidad y reconoce que es vector DoS. Refinamientos abajo. |
| M3 — Transporte por tramos + AdapterSpec v1 | **RATIFICADA 8/8** | Falso dilema disuelto unánimemente. |
| M4.a — Separar ventanas | **RATIFICADA 8/8** | — |
| M4.b — Rechazar acoplamiento al ruleset Wazuh | **RATIFICADA 8/8** | Qwen **concede** el rechazo, con tradeoff a documentar. |
| D5 — Corpus vs pipeline | **Consejo convergido 8/8** | Grok se mueve a corpus-cimiento + pipeline-demo. Pendiente solo tu ratificación. |

No hay objeción de fondo viva contra ninguna moción. Lo que queda son refinamientos (fusionables) y cuatro micro-bifurcaciones (Pasada 3).

---

## B. Contenido firme para el borrador de ADR-046 v4

Esto es lo que ya puede escribirse sin riesgo de rework estructural. Los puntos marcados `⟶P3.x` quedan con un hueco a rellenar por la Pasada 3.

**B1 — Modelo dual de claves (R1).** `community_id` (flujo, opcional) + `host_key` (host). `host_key = IP` intra-LAB; el diseño admite `agent_id`/`hostname` para FEDER/producción. P3 (IP = identidad de host) marcada `ASSUMPTION-LAB-ONLY` — colapsa bajo segmentación L3 / DHCP / contenedores.

**B2 — Grafo temporal heterogéneo, aristas tipadas y asimétricas (R2).**
- *Identidad-de-flujo* (mismo `community_id`): equivalencia → **fusiona**.
- *Localidad-de-host* (mismo `host_key` interno gestionado, en ventana): no transitiva, con peso → **anota/enlaza**.
- *Puente temporal cross-clave*: peso configurable.
- **Invariante:** no hay crisis puramente temporales; toda crisis exige ≥1 anclaje estructural.

**B3 — Timestamp canónico (M1).** `event_time_unix_ns` = **tiempo de ocurrencia**, UTC, gobierna el *windowing*. Tabla de semántica por motor (a congelar en ADR + AdapterSpec):

| Motor | `event_time_unix_ns` |
|---|---|
| aRGus / Suricata / Zeek | timestamp de captura del paquete (Suricata `eve.timestamp`, Zeek `ts` = inicio de conexión) |
| Wazuh (alerta de red) | `timestamp` del evento fuente; fallback `alert.timestamp` |
| Wazuh (FIM/syscheck/rootcheck) | `alert.timestamp` (momento de **detección**, no de cambio); `scan_time` y `file_mtime` → `metadata` |

Disciplina de reloj (R5): gate NTP + monitorización continua + degradación a `confidence=LOW` ante skew > 50 ms (LAB). `bridge_window` 15–30 s absorbe la cuantización de host. `⟶P3.1` (sitio de `emitted_at`/`ingested_at`).

**B4 — Fuentes esperadas dinámicas + ventanas separadas (R3 + M4.a).** Nunca `expected = ALL`. Armado dinámico: una fuente se arma cuando una arista conecta la crisis con su dominio. Wazuh se arma **solo** si la crisis toca un host gestionado (predicado = `host gestionado + dentro de bridge_window`, **no** cobertura de ruleset — M4.b). Tres ventanas distintas:
- `correlation_window`: espera activa de fuentes armadas.
- `late_arrival_window`: gracia para rezagados; **no** reabre la espera.
- `crisis_idle_timeout` = 120 s: cierre por inactividad (se resetea con actividad).
  Cierre = (todas las armadas reportaron y vencida `correlation_window`) **O** `idle ≥ 120 s`.
  **Tradeoff M4.b a documentar verbatim** (texto de Qwen): el predicado evita acoplamiento al ruleset a cambio de posibles expectativas muertas cuyo coste está acotado por `correlation_window`; si en producción se observa ruido, se podrá añadir un filtro opcional basado en **metadatos de regla** (no en el ruleset vivo) — post-FEDER.

**B5 — Política de evicción en tres capas (M2).**
- *Capa 1 — recencia.* Crisis "caliente" (actividad en `HOT_WINDOW`, arranque 5 s) no se evicta. **Refinamiento (DeepSeek):** el estado caliente se refresca con **actividad estructural** (nuevas aristas), no con goteo de baja severidad, para que no se mantenga viva artificialmente. `HOT_WINDOW` puede extenderse por severidad (p. ej. 10 s para `FEDER_CRITICAL`), nunca a inmunidad.
- *Capa 2 — severidad como orden, nunca inmunidad.* `⟶P3.2` (tiers discretos vs score ponderado).
- *Capa 3 — cuota anti-pinning.* Por origen externo. `Q` configurable: 0.05 (LAB), 0.02 (FEDER). **Alcance honesto:** la cuota frena el pinning *concentrado*; el flood *distribuido* lo absorbe el **cap global** (la cuota no es anti-flood total). `⟶P3.3` (granularidad de la cuota).
- *Exención de host interno (la víctima):* exenta de cuota externa y de evicción-por-severidad, **pero** sujeta a (i) **sub-cap por host interno** generoso (anti spoofing de IP interna — Claude) y (ii) `crisis_idle_timeout` extendido (~300 s — Qwen), para que una víctima comprometida-pero-silenciosa no fije memoria indefinidamente.
- *Invariantes:* nunca bloquear ingesta; las evictadas emiten parcial con flag.
- *Telemetría (fusión de ChatGPT + Qwen + Grok):* enum `eviction_reason` / `SaturationReason` = `{HOT_PROTECTED, SEVERITY_ORDER, QUOTA_EXCEEDED, GLOBAL_CAP, IDLE_TIMEOUT}` + métricas `open_crisis_count`, `evicted_by_anti_pin_quota`, `memory_rss`, `dedup_drops`.
- *Memoria (Gemini):* pre-asignación en chunks, sin fragmentación.
- *EMECAS++:* (a) 100k flujos únicos/60 s → RSS acotado, sin leak; (b) pinning concentrado → host interno sobrevive, cuota aplicada; (c) **escenario mixto (DeepSeek)** → fondo normal + pinning externo + incidente real sobre host interno simultáneos → el incidente real nunca se evicta.

**B6 — Horizonte de reordenamiento del engine (consecuencia de M1+M3, sin objeción).** Como las ventanas se rigen por **ocurrencia** pero los eventos **llegan** en orden de arribo, el engine necesita un buffer de reorden acotado y **no puede finalizar** una crisis hasta `ahora − latencia_de_la_fuente_armada_más_lenta`. La fuente más lenta (Wazuh, 90 s) fija el **horizonte de reorden de todo el engine**. Esto es la **razón** documentada de por qué `crisis_idle_timeout` (120 s) > espera Wazuh (90 s): horizonte de reorden + margen, no coincidencia.

**B7 — Inmutabilidad de crisis emitidas.** `⟶P3.4` (re-emisión actualizada vs anexo enlazado inmutable).

**B8 — AdapterSpec v1 (M3) — documento independiente referenciado por el ADR.**
- *Garantías (ChatGPT):* at-least-once + idempotencia por `(source_engine, native_event_id)`; **NO** exactly-once (costoso, innecesario, ya mitigado por dedup) — declararlo explícito para evitar bugs filosóficos.
- *Checkpoint monotónico (Kimi, DeepSeek):* offset de fichero (tail) / offset de topic (Kafka/Redis) / sequence number en envelope con XPUB/XSUB (ZMQ interno). El engine puede pedir "reanuda desde checkpoint X".
- *`native_event_id` determinista para el golden pcap (Qwen):* derivado de offset-en-pcap + índice de evento → reproducibilidad bit a bit.
- *Resiliencia (Qwen):* retry backoff exponencial (max 10, inicial 100 ms); buffer acotado, `on_overflow = log_and_drop_with_metric`, nunca bloquear; health endpoint + métricas.
- *Transporte:* interno **siempre ZeroMQ** (slow-joiner: PUB `bind()` antes de SUB `connect()`); externo **por tier y por motor** (determinista = fichero/replay; vivo = push nativo donde el motor lo soporte, fallback tail-durable). **Congelado** por motor y entorno: nada de fallback silencioso en runtime, o el tier vivo deja de ser reproducible entre runs. El camino push vivo **no es replayable → libre de aserciones por construcción**.

**B9 — Envelope R9 (plano, sin `oneof`).** Con la decisión de B3/`⟶P3.1` sobre los campos de tiempo.

**B10 — Inventario de endpoints, estado de primera clase (R10).** `IP ↔ agent_id ↔ hostname ↔ managed_since`, alimentado desde Wazuh, consultado en caliente para armado de fuentes y para el lado correcto del join asimétrico.

**B11 — Deudas registradas.**
- `DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001` (ya firmada, Pasada 1).
- `DEBT-ARGUSPP-CLOCK-ADVERSARIAL-001` (Claude, post-FEDER): el gate NTP cubre deriva honesta, no un host comprometido que **miente** sobre su reloj para evadir correlación temporal. Mitigación futura: sellar eventos de host en el **manager de Wazuh** (bajo nuestro control), no en el agente.
- Extensión futura no acoplada (DeepSeek/Qwen, post-FEDER): heartbeat asíncrono de Wazuh ("no tengo nada para esta IP en esta ventana") o filtro por metadatos de regla, como optimización de expectativas muertas.

---

## C. Pasada 3 — cuatro micro-mociones residuales

Solo estas cuatro impiden declarar "nada abierto entre nosotros". Dos son casi formalidades (P3.1, P3.3); dos pesan sobre el corpus (P3.2, P3.4).

### P3.1 — ¿`emitted_at`/`ingested_at` como campos de primera clase o en `metadata`?
**Split:** ChatGPT propone tres `uint64` explícitos en el envelope (`event_time`, `emitted_time`, `ingested_time`) por telemetría binaria reproducible, histogramas de latencia, sin parsing textual. R9/Qwen los pusieron en el mapa `metadata`.
**Recomendación Claude:** **campos de primera clase.** Coste = dos `uint64`; beneficio = métricas de latencia tipadas y reproducibles. El mapa `metadata` queda para lo realmente variable (`scan_time`, `file_mtime`, `agent_id`, `hostname`).
**Cierre:** ratificar campos de primera clase, o defender el mapa.

### P3.2 — Orden de evicción en el conjunto frío: tiers discretos vs score continuo *(pesa)*
**Split:** tiers discretos (`LOW→MEDIUM→HIGH→FEDER_CRITICAL`, LRU dentro de cada tier) = DeepSeek, Claude, implícito ChatGPT. Score ponderado continuo (`severidad × fuentes × 1/edad`) = Mistral (y Grok en Pasada 1, no reiterado en Pasada 2).
**Recomendación Claude:** **tiers discretos.** Razones: (a) auditabilidad — el enum `eviction_reason` mapea a tiers, no a un número; (b) la propiedad anti-pinning es **demostrable** sobre tiers, opaca sobre un score; (c) el factor `fuentes` del score es en sí una superficie de ataque (inflar fuentes sube el score); (d) Via Appia/KISS — un score multiplicativo de tres factores esconde comportamiento emergente.
**Cierre:** ratificar tiers, o que Mistral/Grok defiendan el score con una propiedad anti-pinning demostrable.

### P3.3 — Granularidad de la cuota anti-pinning
**Split:** por IP externa individual (Kimi) / + por `community_id` (Mistral, DeepSeek-futuro) / + por `/24` (mención Claude).
**Recomendación Claude:** **por IP externa individual** como cuota FEDER; el **cap global** cubre el flood multi-IP/distribuido. `community_id` y `/24` son redundantes para FEDER (los flujos de una misma IP ya cuentan bajo su cuota; el `/24` arriesga agrupar orígenes legítimos) → registrarlos como *tuning* post-FEDER.
**Cierre:** ratificar por-IP-individual + cap global, o defender una granularidad adicional necesaria *para FEDER*.

### P3.4 — Semántica del rezagado: re-emisión actualizada vs anexo enlazado inmutable *(pesa — afecta al corpus)*
**Split:** Claude propone crisis **inmutable** tras emisión; el rezagado dentro de `late_arrival_window` crea un **registro enlazado nuevo** (delta) que referencia el `crisis_id` previo, sin mutar el original. Kimi habló de "actualización/reenvío", que podría leerse como mutación.
**Recomendación Claude:** **append-only, crisis inmutable.** El estado de una crisis **no** debe depender de cuándo la mires — eso envenena el ground-truth y rompe la reproducibilidad del corpus. El "reenvío" se implementa como **delta inmutable enlazado**, no como edición in situ. Encaja con el marco "event-graph lifecycle / replay determinism" que ChatGPT pidió hacer explícito.
**Cierre:** ratificar append-only + delta enlazado, o que Kimi precise si su "actualización" es mutación y por qué sería compatible con el corpus.

---

## D. D5 — estado

El Consejo está **8/8 a favor de corpus-como-cimiento + pipeline vivo como demostración complementaria** (Grok incluido tras moverse en la Pasada 2; Kimi formuló el compromiso explícito para Grok; Mistral lo llama "híbrido" con la misma forma). No hay disidencia.

Lo único que falta es tu ratificación de la forma exacta: **corpus = entregable duro y evaluable; pipeline vivo = demostración complementaria (grabada o en vivo en el acto), con aserciones de correctitud solo contra el corpus.** Tu respuesta fija el ordenamiento de fases en firme.

---

## E. Dos avisos sobre la posición de Mistral (para no contaminar el registro)

1. **Cita probablemente inventada.** Mistral aduce un caso "FireEye M-Trends 2021" en que un SYN flood contra un SIEM con inmunidad-por-severidad habría bloqueado la detección de un APT. No he podido verificarlo y tiene trazas de atribución fabricada. **No debe entrar en el ADR como precedente factual.** El argumento de seguridad del pinning se sostiene solo, sin necesidad de ese caso.
2. **Inconsistencia interna en M4.b.** Mistral ratifica el rechazo del acoplamiento al ruleset, pero su "Escenario 1" de prueba dice que Wazuh se arma "solo si hay regla para el puerto" — que es exactamente el acoplamiento rechazado. Ese escenario de test debe descartarse para que no se cuele en el diseño de EMECAS++.

---

## F. Qué necesito

- **De Alonso:** ratificación de D5 (forma exacta arriba). Es lo único que bloquea fijar el orden de fases.
- **Del Consejo:** cierre de P3.1–P3.4 (espero cierre rápido salvo defensa en P3.2/P3.4).

Cuando P3 cierre y tengamos tu voto en D5, redacto el **borrador completo de ADR-046 v4** con B1–B11 y el `AdapterSpec v1` como documento aparte. No antes: escribir el ADR con cuatro huecos abiertos sería un atajo.

— Claude (Anthropic), Consejo de Sabios. *Piano, piano.*

Alonso:

Mi opinión fundada es que quiero poder mostrar que el pipeline funcional produce un dataset despues de ejecutar el MITRE ATTACK más bestia posible, porque incluso así, la naturaleza de estos ataques es impredecible, pero siendo todo lo duros e impredecibles posibles, demostramos nuestras intenciones finale para con el pipeline. Queremos parar ataques realistas, mientras generamos telemetría que nos servirá para demostrar que el entrenamiento distribuido federado es una posibilidad técnica que a lo mejor necesita refinamiento en algún punto. Puede que no mostremos el mejor algoritmo que generen dichos datasets, pero debemos mostrar al menos  potencialidad y esperanza basada en argumentos científicos. Yo confío en que los datasets que salgan después de ataques MITRE serán prometedores, porque van a ser variados, etiquetados, y reproducibles. No se si en mi portatil MacBookPro i9 32 GB va a caber todo el pipeline funcionando. Parece que si es posible, incluyendo lo necesario para ejecutar la demo real, con la VM Vagrant que contiene el pipeline(aRGus, Suricata, Zeek, Wazuh!) más el servidor (código basado en NEO4j para crear el grafo, código que recoge la telemetría distribuida, generador de datasets en formato csv/parquet, generador de plugins ensemble con esos datasets). Si vemos que no cabe todo, corriendo a la vez, podemos adoptar varias estrategias, desde apagar las VM que no necesitemos cuando por ejemplo server esté trabajando, o al reves, apagar server cuando defender/client estén trabajando. Server trabaja de modo asíncrono, esperando a que le llegue telemetría. Si esa aproximación no nos vale, y os veo venir porque el tema del correlacion_id está fijado a una ventana temporal con servidores NTP, entonces, llegaríamos a la siguiente fase, usar hardware externo como Raspberry y N100 para distribuir la carga. Ya lo teníamos en el BACKLOG previsto, y si esta es una necesidad impuesta por las leyes de la física, se asumen y compro el hardware con mi poquísimo dinero. Capici?
