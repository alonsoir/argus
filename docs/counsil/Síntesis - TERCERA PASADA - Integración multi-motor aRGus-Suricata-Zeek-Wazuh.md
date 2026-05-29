# Consejo de Sabios — Cierre de la Pasada 3 y registro de decisiones para ADR-046 v4

**Proyecto:** aRGus NDR (arXiv:2604.04952)
**Sesión:** DAY 169 — viernes 29 de mayo de 2026
**Redacta:** Claude (Anthropic), sobre las ocho posiciones de la Pasada 3
**Objeto:** declarar el cierre de P3.1–P3.4, consolidar los refinamientos que entran en ADR-046 v4, y traspasar el voto final a Alonso. No queda nada abierto entre el Consejo.

---

## 1. Veredicto de la Pasada 3

| Micro-moción | Resultado | Notas |
|---|---|---|
| P3.1 — campos de tiempo de primera clase | **CERRADA 8/8** | `optional uint64` para `emitted`/`ingested` (omitibles donde el adapter no los pueble). |
| P3.2 — tiers discretos | **CERRADA 8/8** | Mistral **concede** (era el último que sostenía el score); Grok confirma su cambio de la Pasada 1. |
| P3.3 — cuota por IP externa + cap global | **CERRADA 8/8** | `/24` y `community_id` descartados para FEDER, anotados como *tuning* post-FEDER. |
| P3.4 — append-only + delta enlazado | **CERRADA 8/8** | Kimi, DeepSeek y Qwen confirman que su "actualización/reenvío" era *registro nuevo enlazado*, no mutación. |

**No queda discrepancia abierta entre los ocho miembros.** Procede el voto final de Alonso.

---

## 2. Refinamientos de la Pasada 3 que entran en ADR-046 v4

Se suman a B1–B11 (Pasada 2, firmes) y al resultado de M1–M4. Acreditados a quien los aportó.

**R-P3.1 — Envelope, campos de tiempo.** `event_time_unix_ns` obligatorio (ocurrencia, canónico para windowing); `emitted_time_unix_ns` e `ingested_time_unix_ns` como `optional uint64` de primera clase (Kimi/Qwen: omitibles cuando el adapter no los pueble). `metadata` queda para lo variable y motor-específico (`agent_id`, `hostname`, `scan_time`, `file_mtime`).
- **Frontera de reproducibilidad (Claude):** `emitted_at`/`ingested_at` son **telemetría operativa específica del run**, no identidad semántica del evento ni etiqueta del dataset. No entran en el hash de identidad lógica ni en el ground-truth de entrenamiento. Ver §3.

**R-P3.2 — Evicción, conjunto frío en tiers.**
- Tiers discretos `LOW < MEDIUM < HIGH < FEDER_CRITICAL`, **LRU estricto por `last_event_ts` dentro de cada tier** (Qwen: estricto, no hash ni aleatorio, para determinismo de replay).
- **Implementación O(1) (Gemini):** una cola/ring-buffer LRU por tier; evictar = extraer del frente del tier no vacío más bajo. Sin recálculo de score, sin árbol de prioridad.
- **`EvictionTier` ≠ severidad (ChatGPT):** el tier de protección operacional puede no coincidir con la severidad intrínseca del evento; modelar como enum separado.
- **Cobertura del caso kill-chain temprana (Claude/Kimi):** una crisis de recon (baja severidad) no queda atrapada en `LOW` porque (i) **escala por acreción** —sube de tier al unírsele movimiento lateral— y (ii) la **protección caliente por actividad estructural** la mantiene fuera del conjunto frío mientras gana aristas. No hace falta score continuo.

**R-P3.3 — Cuota anti-pinning.**
- Por **IP externa no gestionada individual** + **cap global**. `Q` configurable (Qwen): `0.05` (LAB), `0.02` (FEDER).
- **Clasificación fail-closed (Claude):** una IP de clasificación **desconocida** se trata como **externa** (sujeta a cuota), nunca como interna/exenta. `desconocido → externo`.
- **Multi-origen (Kimi):** si una crisis tiene varios orígenes externos, cada uno consume su propia cuota; la crisis es `EVICTION_FIRST` si **cualquiera** excede su cuota.
- Exención de host interno acotada por sub-cap por host + `crisis_idle_timeout` extendido (~300 s).

**R-P3.4 — Inmutabilidad y modelo event-sourcing.**
- Crisis inmutable tras emisión. Rezagado dentro de `late_arrival_window` → **delta enlazado** (`parent_crisis_id`, `delta_time_unix_ns`, `late_events`, `reason`), nunca mutación in situ.
- **Modelo event-sourcing (ChatGPT):** `CRISIS_CREATED / CRISIS_UPDATED_DELTA / CRISIS_LATE_ARRIVAL / CRISIS_CLOSED`, append-only, ordenado temporalmente, replayable.
- **`crisis_id` determinista (Kimi) — necesario, no cosmético:** `hash(clave de anclaje + min_event_time_ns + motor anclador)`, no UUID aleatorio. El mismo pcap reprocesado genera los mismos IDs → datasets comparables entre runs.
- **Deltas con sello temporal propio (Claude):** cada delta lleva su `delta_time_unix_ns` para **reconstrucción punto-en-tiempo**; un delta a `T+50s` no puede plegarse en una muestra cuyo corte de entrenamiento es `T` (fuga de futuro). Es lo que valida el walk-forward de ADR-040.
- **Dos modos de consumo (Kimi):** *snapshot* (aplica todos los deltas) y *time-bound* (ignora deltas posteriores a `read_timestamp`, esencial para walk-forward).
- **Evento super-tardío (Claude):** el que llega tras cerrarse `late_arrival_window` no se descarta en silencio ni muta la crisis cerrada; se emite como **registro propio** (singleton), marcado tardío-no-adjuntado.

---

## 3. Un punto para la Pasada 4 (NO reabre P3.1): el artefacto autoritativo

Emergió de la discusión de `ingested_at` y pertenece al contrato del dataset, no al envelope. La reproducibilidad de D5 admite dos vías **no equivalentes**:
- **(A) Congelar el pcap y re-ejecutar los motores.** Reproduce `community_id` (función pura de la 5-tupla) y `event_time` (timestamp del paquete). **No** reproduce `emitted_at`/`ingested_at` (relojes de pared nuevos en cada re-run) ni el orden interno de los motores bajo carga.
- **(B) Congelar el stream de salida grabado** (envelopes + log de crisis append-only) una sola vez durante el run en vivo. Reproduce **todo**, porque son valores congelados.

**Resolución propuesta para la Pasada 4:** el **artefacto autoritativo del dataset es (B)** — el stream grabado + log de crisis append-only, sellado una vez. El **pcap es compañero sellado de verificación** (permite re-derivar `community_id` para comprobar los envelopes y, si hiciera falta, regenerar). Esto eleva el log de crisis append-only (P3.4) de "bueno para walk-forward" a **el artefacto autoritativo del que se genera el dataset**. Atado a ADR-040 y al contrato de dataset federado.

---

## 4. Dos avisos sobre la posición de Mistral (patrón consistente con pasadas previas)

El voto de Mistral es correcto y alineado (ratifica las cuatro), pero sus *detalles* vuelven a derivar y no deben entrar en el spec:
1. Su "prueba formal" anti-pinning de P3.2 aplica la cuota **por tier** ("5% por IP en cada tier"), que **no** es la cuota acordada en P3.3 (por IP sobre el **cap global**, con exención interna). El voto vale; la formulación por-tier, no.
2. Como en pasadas 1 y 2, apoya sus argumentos en "estándares de la industria" citados de memoria; útiles como contexto, no como fuente normativa del ADR.

---

## 5. Estado y traspaso

- **B1–B11** (Pasada 2) + **M1–M4** + **R-P3.1…R-P3.4** (Pasada 3): conjunto de decisiones consistente, auditable y reproducible. Es el esqueleto de ADR-046 v4.
- **Nada abierto entre el Consejo.** Procede el **voto final de Alonso**, y su opinión sobre lo que estime.
- **Tras el voto de Alonso:** Claude redacta el borrador completo de **ADR-046 v4** (B1–B11 + M1–M4 + R-P3.x) y el **`AdapterSpec v1`** como documento aparte.
- **Después:** Pasada 4 — contrato del dataset federado (esquema Parquet, etiquetado MITRE por fase de kill-chain, particionado por `host_key`/`community_id`, integridad walk-forward, y el artefacto autoritativo de §3). Atado a ADR-040.
- **Pendiente operativo, independiente de todo lo anterior:** medir el **RSS de `defender`** con todos sus componentes arriba — es el número que decide si el time-slice server↔pipeline cabe en los 32 GB o si hace falta el hardware externo (N100/Pi).

— Claude (Anthropic), Consejo de Sabios. *Piano, piano — el cimiento es granito.*