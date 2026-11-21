#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_adr058_v3.py — Genera ADR-058 V3 a partir del V2 local.

Invariantes (idénticos al script v2):
  - Lectura -> memoria -> escritura. El handle de lectura se cierra ANTES de
    cualquier escritura. NUNCA open(p,'w') + read() en la misma expresión.
  - El V2 NO se toca. La V3 se escribe en un fichero separado.
  - medir, no votar: cada bloque ANTES debe aparecer EXACTAMENTE UNA VEZ. Si
    alguno no casa (0 o >1), ABORTA sin escribir y nombra la etiqueta.
  - Guarda de idempotencia: si la entrada ya contiene el marcador V3, aborta.

Uso:
    python3 build_adr058_v3.py [entrada_v2] [salida_v3]

Defaults:
    entrada_v2 = ADR-058-circuito-completo-aguas-abajo-v2.md
    salida_v3  = ADR-058-circuito-completo-aguas-abajo-v3.md
"""

import sys
import os

DEFAULT_IN = "ADR-058-circuito-completo-aguas-abajo-v2.md"
DEFAULT_OUT = "ADR-058-circuito-completo-aguas-abajo-v3.md"

EDITS = []

# ===========================================================================
# E11 — Aristas: "coinciden (con method/confidence)" -> igualdad de conjuntos
#       explícita sobre la tupla. (GLM B2 / DeepSeek #1 / Mistral #1)
#       Toca DOS sitios: (a) la línea del predicado, (b) reforzar en prosa NO
#       hace falta — la línea del predicado es el contrato. Solo (a).
# ===========================================================================
EDITS.append((
    "E11-aristas-igualdad-conjuntos",
    " ∧ aristas {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW} coinciden (con method/confidence)",
    " ∧ set((tipo, from_uid, to_eid, method, confidence))_C0                  # aristas: IGUALDAD\n"
    "      == set((tipo, from_uid, to_eid, method, confidence))_AB            #   DE CONJUNTOS,\n"
    "                                                                 #   bidireccional (ver nota aristas)\n"
    "                                                                 #   tipo ∈ {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW}",
))

# Nota de aristas (insertada tras la nota HMAC, antes de §3.2).
EDITS.append((
    "E11b-nota-aristas",
    "### 3.2 Cláusula de caducidad (atada a 10.8)",
    """**Nota — aristas: igualdad de conjuntos, no «coinciden» (medido DAY 199, objeción
GLM/DeepSeek/Mistral aceptada):** la v2 escribía «aristas coinciden (con
method/confidence)», ambiguo entre *subconjunto* (∀ arista ∈ C0 → ∃ en AB; AB puede
tener aristas extra) e *igualdad de conjuntos* (bidireccional). La lectura débil es
insuficiente: si Flujo A+B produjera aristas fantasma (correlaciones que Camino 0 no
tiene), un test de subconjunto pasaría y el dashboard mostraría relaciones falsas.
**Especificación exacta:** el predicado exige **igualdad de conjuntos bidireccional**
sobre la tupla `(tipo, from_uid, to_eid, method, confidence)` que identifica unívocamente
cada arista (campos medidos en `schema.cypher:71-73`: las tres REL TABLE llevan `method
STRING, confidence DOUBLE`; `CORRELATES_FLOW` añade `community_id STRING`). `method` y
`confidence` son clase D (determinista-de-dato): hoy `cypher_builder.hpp:105,114` los fija
constantes (`method='direct'`, `confidence=1.0`); cuando el join los module
(`DEBT-JOIN-CONFIDENCE-001`) seguirán siendo deterministas mientras el join lo sea (atado
a §3.2). `confidence` se compara **bit-exacto** como los demás doubles (misma guarda
canónica NaN/`-0.0`).

### 3.2 Cláusula de caducidad (atada a 10.8)""",
))

# ===========================================================================
# E12 — Reconciliar B1: "no existe en ningún extremo" (V1, sobre columna del
#       oro-ledger Parquet greenfield) vs "se materializa L101/110" (propiedad
#       del nodo Kuzu, ya escrita). Son dos sitios distintos. Frase en V1.
# ===========================================================================
EDITS.append((
    "E12-reconciliar-window-oro-vs-kuzu",
    "  hash. Es **precondición de Via Appia**, no preferencia. Greenfield puro (nada que\n"
    "  migrar — no existe en ningún extremo).",
    "  hash. Es **precondición de Via Appia**, no preferencia.\n"
    "  > **Precisión (DAY 199, reconcilia §3.1):** «no existe en ningún extremo» se refiere\n"
    "  > a la **columna del oro-ledger Parquet** (Flujo A, greenfield: nada que migrar ahí).\n"
    "  > NO contradice §3.1: `flow_start_window` **sí** se materializa hoy como **propiedad\n"
    "  > del nodo Kuzu** en Camino 0 (`cypher_builder.hpp:101,110`, `ON CREATE SET`). Son dos\n"
    "  > sitios distintos — proyección Kuzu (ya escrita) ≠ columna del Parquet oro (greenfield).\n"
    "  > La decisión V1 materializa la columna **del Parquet oro**; la propiedad del nodo ya\n"
    "  > existe. Ambas afirmaciones son ciertas sobre sitios distintos.",
))

# ===========================================================================
# E13 — Nota B5: scores placeholder (0.5f, ML head inerte) -> test
#       necesario-no-suficiente. Insertada al final de la nota bit-exacta,
#       anclando al cierre de esa nota.
# ===========================================================================
EDITS.append((
    "E13-nota-scores-degenerados",
    "pérdida real es texto, y ahí ya está cubierto.)",
    """pérdida real es texto, y ahí ya está cubierto.)

> **Necesario, no suficiente, mientras el ML head esté inerte (medido DAY 199, P1).**
> El supuesto operativo (§1, `DEBT-RANSOMWARE-ML-HEAD-INERT-001`) es que la inferencia
> está incompleta. Medido: hoy hay scores **placeholder** en el pipeline ML
> (`ml-detector/src/main.cpp:419`: `.temporal_anomaly_score = 0.5f` constante). Si las
> columnas de score del bronce son valores fijos o degenerados, el predicado bit-exacto
> sobre ellas **pasa trivialmente** (`0.5 == 0.5` por ambos caminos) y **no ejercita el
> camino de scores que varían**. El test es por tanto **necesario** (cualquier divergencia
> de serialización lo rompe) pero **no suficiente** para declarar el path de scores
> verificado: prueba que el converter no corrompe un double, no que preserve la *variación*
> de scores reales que hoy no existen. **Cláusula:** el cierre del medallón sobre scores
> no-triviales se **re-valida** cuando la inferencia esté viva (post-`ML-HEAD-INERT`), con
> un dataset de scores variados. Trazado en `DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001` (P1).""",
))

# ===========================================================================
# E14 — Parser cross-language como PRECONDICIÓN (no bloqueante). Anclado en la
#       acción residual de §3.1 que ya menciona "si es Python". (GLM B1)
# ===========================================================================
EDITS.append((
    "E14-parser-precondicion",
    "Acción residual: el converter Flujo A **reusa**\n"
    "`encode_flow_input` (o, si es Python, los vectores golden congelados), no reimplementa.",
    """Acción residual: el converter Flujo A **reusa**
`encode_flow_input` (o, si es Python, los vectores golden congelados), no reimplementa.

> **Precondición de bit-exacto en el tramo texto→double (DAY 199, objeción GLM, aceptada
> como precondición trazada — no bloqueante):** la justificación bit-exacta asume que ambos
> caminos parten del **mismo** double al parsear el **mismo** texto del bronce. Eso exige
> que ambos usen un parser texto→double con **el mismo redondeo**. Camino 0 usa C++
> `std::from_chars` (C++17: *correct rounding* garantizado). Si el converter Flujo A es
> **Python**, `float()` delega en `strtod` de la libc del sistema, que **no** garantiza
> correct-rounding en todos los bordes (subnormales, >17 dígitos significativos) según la
> libc (glibc histórico, vs musl). Para esos valores límite, ambos lados pueden producir
> bits distintos del **mismo** texto, y el predicado `==` fallaría **sin bug del converter**.
> Este tramo (CSV→double) es distinto del tramo AVRO→Parquet (que sí está analizado por
> tipo). **Decreto:** el converter Flujo A usa un parser texto→double con correct-rounding
> equivalente a `from_chars` (p.ej. C++ reusando `parse_double`; o, si es Python,
> `numpy`/`fast_float`/parser correct-rounding **no** `float()` ingenuo en bordes). Si por
> diseño acaba siendo Python con parser no garantizado, el gate añade un paso previo:
> parsear todos los doubles del bronce con ambos runtimes y medir `max|d_cpp − d_py|`; si
> `> 0 ULP`, se deriva `ε_parse` de esa medición (cláusula de escape ε, §3.1) **con causa
> medida**. Trazado en `DEBT-CIRCUIT-PARSER-CROSSLANG-001` (P1). No bloquea: el lenguaje del
> Flujo A aún no está decidido; la precondición viaja con la decisión.""",
))

# ===========================================================================
# E15 — temporal_anomaly: subir P2->P1 + ampliar alcance a procedencia.
#       Reemplaza la entrada de deuda en §6.
# ===========================================================================
EDITS.append((
    "E15-temporal-anomaly-p1-procedencia",
    """- `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (**nueva DAY 199** — medida; `temporal_anomaly`
  excluida del predicado §3.1 por derivar de `ingested_at` (`cypher_builder.hpp:86`). Su
  verificación es un test unitario de la fórmula —mismo `window` + `ingested_at` fijo ⇒ mismo
  bool—, no equivalencia-entre-caminos. El converter Flujo A debe portar la fórmula 1:1.)""",
    """*(Esta deuda se reclasifica a P1 — ver bloque P1.)*""",
))

# E15b — añadir la versión P1 ampliada al final del bloque P1.
EDITS.append((
    "E15b-temporal-anomaly-en-p1",
    "- `DEBT-CIRCUIT-FS-DROP-001`",
    """- `DEBT-CIRCUIT-FS-DROP-001`
- `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (**nueva DAY 199, reclasificada P2→P1 en v3**
  tras objeción Kimi/Gemini/GLM). Dos partes. **(a) Paridad de fórmula:** `temporal_anomaly`
  excluida del predicado §3.1 por derivar de `ingested_at` (`cypher_builder.hpp:86`,
  determinista-de-ejecución); su verificación es un test unitario —mismo `window` +
  `ingested_at` fijo ⇒ mismo bool— y el converter Flujo A porta la fórmula 1:1. **(b)
  Procedencia de `ingested_at` (ampliación v3):** un unit test de la fórmula NO caza que el
  converter Flujo A alimente la fórmula con el `ingested_at` *correcto*. Escenario de fallo
  no cubierto por el predicado: el converter usa el timestamp de procesamiento del Parquet
  en vez del de ingestión del bronce → la fórmula da un bool «correcto» sobre un input
  *wrong*, el unit test pasa, y la detección de anomalía temporal (señal anti-evasión, crítica
  en ransomware lento) falla silenciosamente en producción. **Acción:** el test de aceptación
  del Flujo A+B verifica *procedencia* — dado un bronce con timestamps conocidos, que el
  `ingested_at` persistido sea coherente con las filas del bronce (banda esperada / monotonía
  con el orden de filas), inyectable con mock clock. No es bit-exacto: es coherencia de origen.)""",
))

# ===========================================================================
# E16 — Tres cosas en un bloque:
#   (1) canonicalización punto único (frase en la guarda canónica)
#   (2) decreto orden Flujo B -> DEBT-PARQUET-KUZU-CONNECTOR-001 (ampliar deuda)
#   (3) frase de proceso en §7 (ADR prospectivo-en-decisión / retrospectivo-en-evidencia)
#   (4) bloque de gold-plating declinado-por-nombre en §8
# ===========================================================================

# E16a — canonicalización: punto único, en la guarda canónica.
EDITS.append((
    "E16a-canon-punto-unico",
    "> comparar; el converter Flujo A aplica la misma canonicalización. (Apunte medido: la\n"
    "> serialización a AVRO/Parquet puede mutar el *payload*/signo del NaN —signaling→quiet—,\n"
    "> por eso la canonicalización a un patrón único es necesaria, no opcional.)\n"
    "> No bloquea el cierre del predicado.",
    "> comparar; el converter Flujo A aplica la misma canonicalización. (Apunte medido: la\n"
    "> serialización a AVRO/Parquet puede mutar el *payload*/signo del NaN —signaling→quiet—,\n"
    "> por eso la canonicalización a un patrón único es necesaria, no opcional.)\n"
    ">\n"
    "> **Punto único de canonicalización (DAY 199, objeción Qwen/ChatGPT/Gemini):** para no\n"
    "> dejar el grafo Kuzu con valores no-canónicos (que romperían cualquier consulta posterior\n"
    "> que compare scores sin canonicalizar), la canonicalización se aplica **una sola vez, en\n"
    "> el converter Flujo A al escribir** (no solo en el test). Una **única función compartida**\n"
    "> (no dos implementaciones que puedan divergir con el tiempo). El test de equivalencia\n"
    "> **asume grafos ya canónicos** y no re-canonicaliza. Tensión consciente registrada por\n"
    "> Gemini: canonicalizar en escritura significa que un `-0.0` legítimo del bronce se\n"
    "> persiste como `+0.0` — se acepta como pérdida benigna y documentada (el signo del cero\n"
    "> no porta semántica de score), NO como divergencia a cazar. No bloquea el cierre.",
))

# E16b — orden Flujo B: ampliar DEBT-PARQUET-KUZU-CONNECTOR-001 con el decreto verificable.
EDITS.append((
    "E16b-orden-flujo-b-deuda",
    "- `DEBT-PARQUET-KUZU-CONNECTOR-001` (greenfield, Eslabón 2)",
    """- `DEBT-PARQUET-KUZU-CONNECTOR-001` (greenfield, Eslabón 2). **Ampliada v3:** porta la
  precondición de orden determinista del §3.1 (decreto MERGE). El conector Flujo B **debe**
  insertar ordenado por `(flow_start_window, seq_in_window)` antes del sink Kuzu — Parquet es
  columnar y los loaders bulk/paralelos no preservan orden de fila salvo `ORDER BY` explícito.
  El **cómo** (sort previo, `ORDER BY` en la lectura, o writer single-thread durante el test)
  es implementación del conector greenfield, no de este ADR. **Verificación (no circular):**
  un test independiente, **previo** al de equivalencia, intercepta las sentencias MERGE/INSERT
  del conector y verifica orden `(flow_start_window ASC, seq_in_window ASC)`; si no pasa, el
  test de equivalencia **no se ejecuta** (evita diagnóstico ambiguo orden-vs-bug).""",
))

# E16c — frase de proceso en §7.
EDITS.append((
    "E16c-proceso-prospectivo-retrospectivo",
    "- El ADR entra en el mismo PR que el Eslabón 0 (commit de doc no pasa gate de build,\n"
    "  va con la implementación) — coherente con la regla de rama del plan.",
    """- El ADR entra en el mismo PR que el Eslabón 0 (commit de doc no pasa gate de build,
  va con la implementación) — coherente con la regla de rama del plan.
- **Naturaleza del ADR (objeción de proceso, Kimi):** este ADR es **prospectivo en la
  decisión** (forma del oro, predicado §3.1, bit-exacto — decisiones a futuro) y
  **retrospectivo en la evidencia** (el gate DAY 198 mide binario ya existente: Camino 0,
  schema, cypher_builder). La ratificación del Consejo confirma la *decisión* y la *fidelidad
  de la evidencia medida*; no pretende ser un gate pre-merge sobre código inexistente (Flujo
  A/B greenfield). Que el doc viaje con el Eslabón 0 es regla de rama consciente, no
  ratificación post-hoc encubierta.""",
))

# E16d — bloque gold-plating declinado por nombre en §8 (tras la lista "Diferidas").
EDITS.append((
    "E16d-gold-plating-declinado",
    """- **Diferidas como deuda trazada** (fuera del alcance de este ADR, no gold-plating dentro):
  oro-ledger como multiset bajo at-least-once; HMAC scope full-row vs columnas-grafo;
  `inotify` + NFS/contenedor → fallback polling. Punteros en §6 y backlog.""",
    """- **Diferidas como deuda trazada** (fuera del alcance de este ADR, no gold-plating dentro):
  oro-ledger como multiset bajo at-least-once; HMAC scope full-row vs columnas-grafo;
  `inotify` + NFS/contenedor → fallback polling. Punteros en §6 y backlog.
- **Declinadas por alcance, nombradas explícitamente (no por omisión — por diseño):** el
  lote de revisión V2 propuso, en contexto «salva vidas», un conjunto de mejoras que **no
  son defectos del circuito** sino trabajo de otra capa o post-FEDER. Se declinan en este
  ADR, con nombre, para que quede trazado que se vieron y se decidieron fuera de alcance —
  no que se pasaron por alto:
  - **Hash determinista del grafo completo** (Mistral): da un booleano sin diagnóstico, peor
    que el predicado por-propiedad que ya localiza la divergencia. Rechazado por inferior.
  - **Recovery/backup/restore de Kuzu, snapshot diario** (Qwen/Mistral): Kuzu es proyección
    reconstruible desde el oro-ledger por diseño (§2); el procedimiento operativo es post-FEDER.
  - **Observabilidad/Prometheus/Grafana, métricas de circuito** (Qwen/Grok): capa de operación,
    no del predicado. Backlog post-circuito (`DEBT-CIRCUIT-OBSERVABILITY-001` si se abre).
  - **Performance/throughput SLA, query budgeting** (Qwen/Mistral/Grok): el circuito se cierra
    por correctitud primero (Camino 0 existe); el benchmark es ADR-029, no éste.
  - **Backpressure/HWM en ZMQ** (Qwen): ya hay `DEBT-ZMQ-DELIVERY-GUARANTEE-001` (P0); el
    detalle de HWM es de Eslabón 1, no del cierre del predicado.
  - **HMAC lifecycle (rotación, versión de clave, revalidación)** (Kimi/ChatGPT/Grok/Mistral):
    ya es `DEBT-GOLD-INTEGRITY-HMAC-001` (P0); el ciclo de vida cripto es trabajo propio, no
    de este ADR. La infraestructura epoch/rotación ya existe (crypto DAY 156-162).
  - **Schema evolution, RBAC, retention, timezone** (Qwen): post-FEDER, otra capa.
  > El criterio de cierre: este ADR documenta **una decisión medible contra binario
  > existente**. Specs de un binario que aún no existe (Flujo A/B) van a deuda trazada, no al
  > cuerpo del ADR — documentarlas aquí sería votar contra un binario inexistente, el anti-
  > patrón inverso de «medir, no votar».""",
))

# ===========================================================================
# E17 — event_id: decisión de contrato (UUID único por instalación; fusión de
#       grafos fuera de alcance) en §2 + DEBT-EVENT-ID-FACTORY-001 (P1) en §6.
# ===========================================================================

# E17a — corolario de contrato event_id en §2 (tras corolario 6).
EDITS.append((
    "E17a-event-id-contrato-corolario",
    "    correlación-19/HMAC (grafo). El converter del circuito **no** llama al firmador RAG.",
    """    correlación-19/HMAC (grafo). El converter del circuito **no** llama al firmador RAG.
7. **`event_id` = identidad de evento, contrato de unicidad por instalación (decisión
   consciente DAY 199).** Medido: `correlation_writer.cpp:84` **copia** `event.event_id()`
   (no lo genera); el `event_id` nace en el productor del evento, aguas arriba del bronce, y
   viaja como dato (col 2). **Decisión de contrato:** `event_id` debe ser un identificador
   único por evento dentro de una **instalación**, emitido por una fuente única (factoría tipo
   inyección de dependencia) que todos los componentes usan. Se toleran `event_id` iguales
   **entre instalaciones distintas** (cada uno pertenece a su instalación; no se cruzan).
   **Límite declarado:** este contrato NO contempla **fusión de grafos de instalaciones
   distintas**; si algún día se requiere, se vuelve a la pizarra (no se hace overengineering
   ahora para un caso no contemplado). El «es UUID único de facto» es hoy un *deber-ser* del
   contrato, no un *medido*; la verificación de que todos los productores lo cumplen se traza
   en `DEBT-EVENT-ID-FACTORY-001` (P1). Para el predicado §3.1 esto es irrelevante: ambos
   caminos leen el mismo `event_id` del mismo bronce (col 2) → mismo set por construcción,
   sea cual sea su cardinalidad real.""",
))

# E17b — DEBT-EVENT-ID-FACTORY-001 en §6 P1.
EDITS.append((
    "E17b-event-id-factory-deuda",
    "- `DEBT-HOST-DOMAIN-CONTRACT-001` (pre-Eslabón 1; contrato Wazuh host↔red por definir)",
    """- `DEBT-HOST-DOMAIN-CONTRACT-001` (pre-Eslabón 1; contrato Wazuh host↔red por definir)
- `DEBT-EVENT-ID-FACTORY-001` (**nueva DAY 199** — decisión de contrato §2 corolario 7).
  Verificar/garantizar que **todos** los productores de evento obtienen `event_id` de una
  fuente única con unicidad por instalación. Medir dónde nace hoy (`correlation_writer.cpp:84`
  solo lo copia; el origen está aguas arriba, sin medir aún). Si hay productores que generan
  `event_id` por caminos distintos sin unicidad garantizada, abrir el mecanismo de factoría.
  Análogo a `DEBT-FLOWUID-SEQ-COLLISION-001`: un `event_id` duplicado sería fidelidad
  (MERGE descarta el segundo idéntico en ambos caminos), no equivalencia; no bloquea el
  medallón. Fusión de grafos inter-instalación: explícitamente fuera de alcance.""",
))

# ===========================================================================
# E18 — Cabecera + estado: marcar v3, y un §10 changelog v2->v3.
# ===========================================================================
EDITS.append((
    "E18-cabecera-v3",
    "- **Estado:** PROPUESTO (v2 — pendiente confirmación del Consejo de las correcciones medidas)\n"
    "- **Fecha:** DAY 199 (hoy)",
    "- **Estado:** PROPUESTO (v3 — cierre con deudas abiertas registradas; pendiente confirmación del Consejo)\n"
    "- **Fecha:** DAY 199 (hoy)\n"
    "- **Revisión v3 (DAY 199):** segunda ronda adversarial del Consejo incorporada. Lo medible\n"
    "  entró (aristas=igualdad de conjuntos; reconciliación window oro↔Kuzu; scores placeholder\n"
    "  necesario-no-suficiente); las specs de Flujo A/B inexistente se convirtieron en deudas\n"
    "  trazadas (parser cross-language, orden Flujo B, procedencia temporal_anomaly, factoría\n"
    "  event_id); el gold-plating se declinó por nombre (§8). Cierre con deudas registradas, no\n"
    "  espera de unanimidad incondicional. Detalle en §10.",
))

# E18b — §10 changelog v2->v3 al final del documento (tras la nota de scope del §9).
EDITS.append((
    "E18b-changelog-v3",
    """> Nota de scope: objeciones de gold-plating del lote (backpressure/HWM, schema evolution,
> SLA del test, key management, RBAC, retention, rollback, timezone, hash-grafo-completo)
> se declinan en este ADR por violar "una batalla" / ya cubiertas por deuda existente.
> No son defectos del circuito; son trabajo post-FEDER o de otra capa.""",
    """> Nota de scope: objeciones de gold-plating del lote (backpressure/HWM, schema evolution,
> SLA del test, key management, RBAC, retention, rollback, timezone, hash-grafo-completo)
> se declinan en este ADR por violar "una batalla" / ya cubiertas por deuda existente.
> No son defectos del circuito; son trabajo post-FEDER o de otra capa.

---

## 10. Changelog v2 → v3 (DAY 199, segunda ronda adversarial)

Criterio de cierre aplicado: **entra lo medible contra binario existente; las specs de un
binario inexistente (Flujo A/B greenfield) van a deuda trazada; el gold-plating se declina
con nombre.** El V2 se conserva intacto; esta v3 es fichero separado.

| # | §  | Cambio | Origen | Clase |
|---|----|--------|--------|-------|
| 11 | 3.1 | Aristas: «coinciden» → **igualdad de conjuntos** bidireccional sobre `(tipo, from, to, method, confidence)` + nota | GLM/DeepSeek/Mistral | medible, del predicado |
| 12 | 4-V1 | Reconciliación B1: «no existe en ningún extremo» = columna Parquet-oro (greenfield) ≠ propiedad nodo Kuzu (ya escrita L101/110) | Claude (auto-adversario) | contradicción interna corregida |
| 13 | 3.1 | Nota: test **necesario-no-suficiente** con scores placeholder (`0.5f`, `main.cpp:419`); re-valida con ML vivo → `DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001` (P1) | Claude (A5, recuperada) | medible, grieta de fondo |
| 14 | 3.1 | Precondición parser texto→double correct-rounding cross-language → `DEBT-CIRCUIT-PARSER-CROSSLANG-001` (P1) | GLM | precondición trazada, no bloqueante |
| 15 | 6 | `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` P2→**P1** + alcance ampliado a **procedencia de `ingested_at`** | Kimi/Gemini/GLM | deuda reclasificada |
| 16a | 3.1 | Canonicalización IEEE 754: **punto único** (converter, función compartida), test asume grafos canónicos | Qwen/ChatGPT/Gemini | spec converter |
| 16b | 6 | Orden Flujo B → `DEBT-PARQUET-KUZU-CONNECTOR-001` ampliada; verificación no-circular (test previo intercepta orden) | Gemini/Kimi/Qwen/DeepSeek | spec Flujo inexistente → deuda |
| 16c | 7 | Naturaleza: ADR **prospectivo-en-decisión / retrospectivo-en-evidencia** | Kimi (proceso) | aclaración |
| 16d | 8 | Gold-plating **declinado por nombre** (hash-grafo, recovery, observabilidad, perf SLA, backpressure, HMAC lifecycle, schema evol) | lote V2 | scope explícito |
| 17 | 2,6 | `event_id`: contrato de unicidad por instalación (corolario 7) + `DEBT-EVENT-ID-FACTORY-001` (P1); fusión de grafos fuera de alcance | Alonso (decisión) / Kimi | decisión + deuda |

> **Deudas nuevas en v3 (4):** `DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001` (P1),
> `DEBT-CIRCUIT-PARSER-CROSSLANG-001` (P1), `DEBT-EVENT-ID-FACTORY-001` (P1), y la
> reclasificación de `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` a P1 con alcance ampliado.
> Todas registradas en §6; pendiente volcado a `docs/backlog.md` (primera tarea post-cierre).

> **Postura de cierre:** este ADR no espera unanimidad incondicional del Consejo. La segunda
> ronda confirmó que el patrón adversarial genera bordes nuevos indefinidamente (cada ronda
> resuelve los previos y encuentra otros). El criterio de cierre lo fija el arbitraje: lo
> medible entra, lo inexistente va a deuda, el gold-plating se nombra y se declina. Lo que
> aparezca al tratar las deudas se estudia entonces, con humildad, contra el binario de ese
> momento. **Via Appia: cada piedra medida en su sitio; las que aún no existen, señalizadas
> en el mapa, no inventadas en la calzada.**""",
))


def fail(msg):
    sys.stderr.write("\n[ABORTADO] " + msg + "\n")
    sys.exit(1)


def main():
    path_in = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IN
    path_out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    if not os.path.exists(path_in):
        fail("No existe la entrada: %s" % path_in)

    with open(path_in, "r", encoding="utf-8") as fh:
        text = fh.read()
    original_len = len(text)

    if "## 10. Changelog v2 → v3" in text:
        fail("La entrada ya parece una v3 (contiene el changelog v2→v3). "
             "Pásame el v2 limpio o revisa la ruta.")

    problems = []
    for label, before, _after in EDITS:
        n = text.count(before)
        if n != 1:
            problems.append((label, n))
    if problems:
        lines = ["%d edición(es) no casan exactamente una vez contra %s:" %
                 (len(problems), path_in)]
        for label, n in problems:
            lines.append("  - %s : encontrado %d veces (se esperaba 1)" % (label, n))
        lines.append("No se ha escrito nada. El V2 está intacto.")
        fail("\n".join(lines))

    applied = []
    for label, before, after in EDITS:
        text = text.replace(before, after, 1)
        applied.append(label)

    with open(path_out, "w", encoding="utf-8") as fh:
        fh.write(text)

    sys.stdout.write("OK — V3 generada: %s\n" % path_out)
    sys.stdout.write("  entrada (v2): %s (%d chars, intacto)\n" % (path_in, original_len))
    sys.stdout.write("  salida  (v3): %s (%d chars)\n" % (path_out, len(text)))
    sys.stdout.write("  ediciones aplicadas (%d):\n" % len(applied))
    for label in applied:
        sys.stdout.write("    + %s\n" % label)


if __name__ == "__main__":
    main()