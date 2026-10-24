#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_adr058_v2.py — Genera ADR-058 V2 a partir del V1 local.

Invariantes respetados:
  - Lectura -> memoria -> escritura. NUNCA open(p,'w') y read() en la misma expresión.
  - El original NO se toca. La V2 se escribe en un fichero separado.
  - medir, no votar: cada bloque ANTES debe aparecer EXACTAMENTE UNA VEZ en el
    original. Si alguno no casa (0 o >1), el script ABORTA sin escribir nada y
    reporta cuál falló. No hay reemplazos silenciosos.
  - Idempotencia defensiva: si la V2 ya contiene un marcador de la V2, avisa.

Uso:
    python3 build_adr058_v2.py [ruta_original] [ruta_salida]

Defaults:
    ruta_original = ADR-058-circuito-completo-aguas-abajo.md
    ruta_salida   = ADR-058-circuito-completo-aguas-abajo-v2.md
"""

import sys
import os

DEFAULT_IN = "ADR-058-circuito-completo-aguas-abajo.md"
DEFAULT_OUT = "ADR-058-circuito-completo-aguas-abajo-v2.md"

# ---------------------------------------------------------------------------
# Cada edición es (etiqueta, ANTES, DESPUES). Las cadenas ANTES están copiadas
# byte a byte del ADR V1 (DAY 199). Si tu fichero local difiere, el script lo
# dirá nombrando la etiqueta.
# ---------------------------------------------------------------------------

EDITS = []

# --- E1: §1, "6 verificaciones" -> "9 verificaciones" (A3, fósil) -----------
EDITS.append((
    "E1-contexto-conteo-verificaciones",
    "añade la evidencia medida en el gate de DAY 198 (6 verificaciones contra bytes).",
    "añade la evidencia medida en el gate de DAY 198 (9 verificaciones contra bytes).",
))

# --- E2: cabecera, marca de revisión V2 -------------------------------------
EDITS.append((
    "E2-cabecera-estado",
    "- **Estado:** PROPUESTO (pendiente ratificación final del Consejo)\n"
    "- **Fecha:** DAY 199 (hoy)",
    "- **Estado:** PROPUESTO (v2 — pendiente confirmación del Consejo de las correcciones medidas)\n"
    "- **Fecha:** DAY 199 (hoy)\n"
    "- **Revisión:** v2 (DAY 199) — §3.1 reescrita tras revisión adversarial del Consejo (8 modelos).\n"
    "  Las objeciones se midieron contra `fichero:línea`: tres bloqueantes propuestos cayeron contra\n"
    "  el binario (window/seq YA materializadas L101/110; `event_id`=bronce col 2; scores YA `DOUBLE`\n"
    "  en `schema.cypher`); el resto se incorporó. Detalle por edición en §9 (changelog).",
))

# --- E3: §3.1 — reemplazo del bloque del predicado EQUIV --------------------
# El predicado V1 mete hmac_row e ingested-derivados implícitos. La V2 particiona.
EDITS.append((
    "E3-predicado-equiv",
    """```
EQUIV(Camino0, FlujoA+B) :=
   set(flow_uid)_C0                  == set(flow_uid)_AB         # NetworkFlow
 ∧ set(event_id)_C0                  == set(event_id)_AB         # Alert ∪ TelemetryEvent
 ∧ ∀ uid: props_identidad(uid)_C0    == props_identidad(uid)_AB  # node_id, community_id,
                                                                 #   flow_start_window, seq_in_window
 ∧ ∀ eid: props_veredicto(eid)_C0    == props_veredicto(eid)_AB  # cols 12-17; los 3 scores
                                                                 #   double BIT-EXACTOS por defecto (ver nota)
 ∧ aristas {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW} coinciden (con method/confidence)
 ∧ ∀ fila: hmac_row preservado de bronce
```""",
    """El predicado compara solo propiedades **deterministas-de-dato** (derivan del
bronce; idénticas entre ejecuciones). Excluye explícitamente las propiedades
**deterministas-de-ejecución** (derivan del reloj/orden del run; divergen entre
corridas **por diseño, no por bug**). La partición está trazada a `fichero:línea`
(ver «Partición de propiedades» más abajo).

```
EQUIV(Camino0, FlujoA+B) :=
   set(flow_uid)_C0                  == set(flow_uid)_AB         # NetworkFlow (PK, V9)
 ∧ set(event_id)_C0                  == set(event_id)_AB         # Alert ∪ TelemetryEvent
                                                                 #   (event_id = bronce col 2, ver nota)
 ∧ ∀ uid: props_identidad(uid)_C0    == props_identidad(uid)_AB  # node_id, community_id,
                                                                 #   flow_start_window, seq_in_window
                                                                 #   (materializadas L101/110, ver nota)
 ∧ ∀ eid: props_veredicto(eid)_C0    == props_veredicto(eid)_AB  # final_classification, threat_category,
                                                                 #   3 scores double, authoritative_source
                                                                 #   double BIT-EXACTOS por defecto (ver nota)
 ∧ aristas {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW} coinciden (con method/confidence)
 # EXCLUIDAS (clase determinista-de-ejecución, NO van al predicado):
 #   ingested_at      — wall-clock per-fila (kuzu_graph_sink.hpp:47)
 #   temporal_anomaly — deriva de ingested_at (cypher_builder.hpp:86)
 # hmac_row NO está en este predicado: no vive en la proyección Kuzu (0 hits en
 # schema.cypher). Se verifica aparte como integridad bronce↔oro (ver nota HMAC).
```

**Partición de propiedades (medido DAY 199 contra `cypher_builder.hpp`,
`kuzu_graph_sink.hpp`, `correlation_reader.cpp`, `schema.cypher`):**

| Clase | Propiedades | Traza | En predicado |
|-------|-------------|-------|--------------|
| **D — determinista-de-dato** | `flow_uid`, `event_id`, `node_id`, `community_id`, `flow_start_window`, `seq_in_window`, `final_classification`, `threat_category`, `fast_detector_score`, `ml_detector_score`, `overall_threat_score`, `authoritative_source`, `method`, `confidence` | `cypher_builder.hpp:101-103,110-112`; `event_id`=`correlation_reader.cpp:85` (col 2); aristas=`schema.cypher:71-73` | **SÍ** (`==`, bit-exacto en doubles) |
| **E — determinista-de-ejecución** | `ingested_at`, `temporal_anomaly` | `kuzu_graph_sink.hpp:47` (`ingest_now_ns()` per-fila); `cypher_builder.hpp:86` (`window_to_epoch_nanos(window) > ingested_at_ns + margen`) | **NO** (divergen entre corridas por diseño) |

Razón de la exclusión: la equivalencia de dos **caminos** debe definirse sobre lo que
deriva del **dato**, no sobre cuándo corrió cada camino. `ingested_at` se sella con
`CLOCK_REALTIME` a la entrada del sink (per-fila); dos ejecuciones producen relojes
distintos. `temporal_anomaly` es un `bool` que **parece** determinista-de-dato (deriva
de `window`) pero su fórmula toca `ingested_at` (`cypher_builder.hpp:86`), luego hereda
el no-determinismo para flujos cuya window cae cerca del instante de ingestión. Incluir
cualquiera de las dos en el predicado lo haría fallar entre Camino 0 y Flujo A+B **sin
que exista bug alguno en el converter**. La verificación correcta de `temporal_anomaly`
no es equivalencia-entre-caminos sino un **test unitario de la fórmula** (mismo `window`
+ mismo `ingested_at` fijo ⇒ mismo bool); se traza en
`DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (P2).""",
))

# --- E4: §3.1 — nota bit-exacta: añadir event_id + window/seq medidos -------
# Insertamos un bloque de "hechos medidos que derriban objeciones" justo antes
# de la nota de igualdad bit-exacta (que se mantiene intacta).
EDITS.append((
    "E4-nota-bitexacta-cabecera",
    "**Nota — igualdad de los scores: BIT-EXACTA por defecto (medido DAY 198):** los 3",
    """**Nota — `event_id` y window/seq son datos del bronce, no generados aguas abajo
(medido DAY 199):** objeción del Consejo (varios modelos): «`event_id` podría ser UUID
v4 → los sets nunca coinciden» y «Camino 0 no escribe `flow_start_window`/`seq_in_window`
→ el predicado falla por construcción». **Ambas caen contra el binario.**
`event_id` se lee como **columna 2 del bronce** (`correlation_reader.cpp:85`:
`r.event_id = f[2]`; struct `correlation_record.hpp:14` lo marca `// 2`): viaja como
dato, igual que `flow_uid`; ambos caminos leen el mismo `f[2]` → mismo set por
construcción. (Matiz: `ingest_clock.hpp:6` indica que el wall-clock compone el
`event_id` en el **productor**, aguas arriba del bronce; irrelevante para la
equivalencia, que empieza una vez el valor ya está escrito en bronce.)
`flow_start_window` y `seq_in_window` **sí se materializan** como propiedades del nodo
en Camino 0 (`cypher_builder.hpp:101,110`: `ON CREATE SET f.flow_start_window=...,
f.seq_in_window=...`): no se computan-y-tiran, se computan en read-time **y** se
escriben. El predicado `props_identidad ==` se sostiene porque ambos caminos las emiten.

**Nota — igualdad de los scores: BIT-EXACTA por defecto (medido DAY 198):** los 3""",
))

# --- E5: §3.1 — guarda NaN: regla canónica única (NaN + -0.0) ---------------
EDITS.append((
    "E5-guarda-nan",
    """> **Guarda NaN (independiente de ε, P2):** bajo IEEE 754 `NaN != NaN`. Si algún score
> puede ser NaN (ML head inerte, score sin inicializar), el predicado `==` necesita regla
> explícita — canonicalizar NaN o comparar patrón de bits (`memcmp` de los 8 bytes). Con
> ε pasaba igual (`|NaN−NaN| < ε` también es falso), solo que quedaba oculto. Acción: el
> converter Flujo A normaliza el patrón de NaN. No bloquea el cierre del predicado.""",
    """> **Guarda de comparación: una sola regla canónica para los bordes IEEE 754
> (medido DAY 199, P2).** Pasar de `≈ε` a `==` aflora dos bordes que con ε quedaban
> ocultos (igual de rotos, pero invisibles). **No pueden tratarse con la misma
> primitiva** — y este es el error que hay que evitar:
> - **NaN:** `NaN != NaN`. Un `==` crudo falla aunque ambos lados sean NaN.
> - **Cero con signo:** `-0.0` y `+0.0` son **bit-distintos** (`0x8000…0` vs `0x0`) pero
>   numéricamente iguales. Un `==` crudo los iguala (oculta divergencia de bits); un
>   `memcmp` crudo de 8 bytes los **separa** (falsa divergencia). Por eso `memcmp` solo
>   —como se proponía— es incorrecto: rompe el caso `-0.0`.
>
> **Regla única:** comparar sobre el **patrón de bits canonicalizado**, donde
> canonicalización = { todo NaN → un único patrón quiet `0x7ff8000000000000`;
> `-0.0` → `+0.0` }. Sobre ese patrón, `==` bit a bit. Una sola regla coherente para
> los tres casos (finitos, NaN, ceros). Ambos caminos deben canonicalizar **antes** de
> comparar; el converter Flujo A aplica la misma canonicalización. (Apunte medido: la
> serialización a AVRO/Parquet puede mutar el *payload*/signo del NaN —signaling→quiet—,
> por eso la canonicalización a un patrón único es necesaria, no opcional.)
> No bloquea el cierre del predicado.""",
))

# --- E6: §3.1 — degradar robustez sobre-afirmada de la colisión MERGE -------
# La nota de colisión afirma robustez "mágica"; la condicionamos a orden determinista.
EDITS.append((
    "E6-merge-orden",
    """Por tanto la **equivalencia se
sostiene** ante colisión — Camino 0 y Flujo A+B producen el mismo grafo. La colisión es
deuda de **fidelidad** (se pierde un flujo real, P2), NO de **equivalencia** (ambos
caminos pierden el mismo). El predicado §3.1 es robusto a la colisión; el medallón **no
queda bloqueado** por ella.""",
    """Por tanto la **equivalencia se
sostiene** ante colisión — Camino 0 y Flujo A+B producen el mismo grafo, **bajo una
precondición medida** (ver abajo). La colisión es deuda de **fidelidad** (se pierde un
flujo real, P2), NO de **equivalencia** (ambos caminos pierden el mismo). El medallón
**no queda bloqueado** por ella.

> **Precondición de la robustez (objeción del Consejo, aceptada): orden de inserción
> determinista.** El argumento «ambos descartan idénticamente» solo se sostiene si, ante
> colisión `flow_uid`, **el mismo flujo gana el `ON CREATE SET` en ambos caminos** — y eso
> depende del **orden de inserción**. Camino 0 es `ifstream` secuencial (orden = líneas
> del bronce). Flujo B (Parquet→Kuzu, greenfield) podría insertar en paralelo/bulk, en cuyo
> caso ganaría un flujo distinto y el predicado rompería **por carrera de arquitectura, no
> por bug del converter**. **Decreto:** el Flujo B inserta en orden determinista por
> `(flow_start_window, seq_in_window)` antes del sink Kuzu; el test de equivalencia asume y
> verifica esta precondición. Sin orden determinista, el predicado mide la convergencia del
> sink bajo un orden concreto, no la equivalencia de los caminos.""",
))

# --- E7: §2 corolario 6 / §6 ref "§2.6" -> "§2 corolario 6" (A4) ------------
EDITS.append((
    "E7-ref-2.6",
    "`DEBT-DOCS-MEDALLION-DUALITY-001` (firma del oro HMAC ≠ Ed25519 RAG — ver §2.6)",
    "`DEBT-DOCS-MEDALLION-DUALITY-001` (firma del oro HMAC ≠ Ed25519 RAG — ver §2 corolario 6)",
))

# --- E8: §3.1 — añadir nota HMAC (sale del predicado, va a integridad) ------
# Anclamos tras la cláusula de caducidad §3.2 abriendo con su encabezado, para
# insertar la nota HMAC al final de §3.1 sin tocar §3.2. Anclamos al título §3.2.
EDITS.append((
    "E8-nota-hmac",
    "### 3.2 Cláusula de caducidad (atada a 10.8)",
    """**Nota — HMAC: integridad bronce↔oro, NO cláusula del predicado (medido DAY 199):**
objeción del Consejo (DeepSeek), **aceptada**. El predicado V1 incluía
`∀ fila: hmac_row preservado`, pero `hmac` tiene **0 ocurrencias en `schema.cypher`**: el
grafo Kuzu **no almacena HMAC**, ni por Camino 0 ni por Flujo A+B. Una cláusula sobre la
proyección Kuzu que referencia un campo ausente de Kuzu es **inverificable** donde estaba.
Corrección: `hmac_row` **sale del predicado de equivalencia** (§3.1) y se reubica como
**control de integridad bronce↔oro-ledger** — se verifica que cada fila del oro conserva el
HMAC heredado del bronce (§2 corolario 6), de forma independiente al test
Camino-0 ≡ Flujo-A+B. La definición del mecanismo (clave, alcance por-fila vs por-artefacto)
vive en `DEBT-GOLD-INTEGRITY-HMAC-001` (P0).

### 3.2 Cláusula de caducidad (atada a 10.8)""",
))

# --- E9: §6 — nueva deuda P2 temporal_anomaly parity ------------------------
EDITS.append((
    "E9-deuda-temporal-anomaly",
    """- `DEBT-FLOWUID-CANONICAL-ENCODING-001` (**resuelta de facto** — medida DAY 198;
  encoding inyectivo length-prefixed + BE + tag versión, paridad C++/Python congelada;
  acción residual: converter Flujo A reusa `encode_flow_input`, no reimplementa)""",
    """- `DEBT-FLOWUID-CANONICAL-ENCODING-001` (**resuelta de facto** — medida DAY 198;
  encoding inyectivo length-prefixed + BE + tag versión, paridad C++/Python congelada;
  acción residual: converter Flujo A reusa `encode_flow_input`, no reimplementa)
- `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (**nueva DAY 199** — medida; `temporal_anomaly`
  excluida del predicado §3.1 por derivar de `ingested_at` (`cypher_builder.hpp:86`). Su
  verificación es un test unitario de la fórmula —mismo `window` + `ingested_at` fijo ⇒ mismo
  bool—, no equivalencia-entre-caminos. El converter Flujo A debe portar la fórmula 1:1.)""",
))

# --- E10: §8 — reescritura del cierre con framing "confirmar lo medido" -----
EDITS.append((
    "E10-cierre-ratificacion",
    """## 8. Pendiente de ratificación

Decisión VIVA para el Consejo (una, consciente): **ratificar la igualdad BIT-EXACTA por
defecto en los 3 scores double (cols 14-16) del predicado §3.1**, con ε degradada a
cláusula de escape condicionada a medición (se deriva de una cuantización concreta del
Flujo-A real, o no se introduce). Con esto el predicado queda **uniforme**: `==` para
todas las columnas, ε como única excepción documentada. El cambio respecto a la versión
previa es deliberado: presentar una ε "ya cerrada" para una pérdida **no medible hasta
que exista el Flujo A** sería votar, no medir. Se sube como punto consciente, no como
hueco. 10.8 diferida con ticket (`DEBT-JOIN-CONFIDENCE-001`). Con esta ratificación, el
plan cierra como ADR.""",
    """## 8. Estado de ratificación

**Bit-exacto por defecto: RATIFICADO** (ronda DAY 199, Consejo 8 modelos). La sub-decisión
abierta en la v1 — `==` bit-exacto en los 3 scores double con ε degradada a cláusula de
escape condicionada a medición — se sometió al Consejo y **no fue objetada de fondo** (voto
explícito a favor; el resto refinó los bordes, no la decisión). Queda cerrada.

**Lo que esta v2 lleva al Consejo NO es re-litigación, sino confirmación de las correcciones
medidas.** La revisión adversarial de la v1 produjo objeciones de calidad. Cada una se
**midió contra `fichero:línea`**, no se debatió:

- **Cayeron contra el binario** (la medición refuta la objeción):
  - «window/seq no las escribe Camino 0» → **falso**: `cypher_builder.hpp:101,110` las
    materializa (`ON CREATE SET`).
  - «`event_id` indefinido / posible UUID v4» → **falso**: es bronce col 2
    (`correlation_reader.cpp:85`).
  - «el schema podría declarar FLOAT en los scores» → **falso**: `schema.cypher:42-44,62-64`
    son `DOUBLE`; refuerza bit-exacto.
- **Incorporadas a §3.1** (la medición confirma la objeción):
  - `hmac_row` sale del predicado → integridad bronce↔oro (0 hits de `hmac` en
    `schema.cypher`). [DeepSeek]
  - **Partición D/E**: `ingested_at` (`kuzu_graph_sink.hpp:47`) y `temporal_anomaly`
    (`cypher_builder.hpp:86`) excluidas por deterministas-de-ejecución. [hallazgo de la
    medición; ningún modelo lo vio, tampoco la v1]
  - NaN + `-0.0`: una sola regla canónica (canonicalizar, no `memcmp` crudo ni `==` crudo).
  - MERGE robusto a colisión **bajo precondición** de orden de inserción determinista.
    [Gemini/Kimi/Qwen]
- **Diferidas como deuda trazada** (fuera del alcance de este ADR, no gold-plating dentro):
  oro-ledger como multiset bajo at-least-once; HMAC scope full-row vs columnas-grafo;
  `inotify` + NFS/contenedor → fallback polling. Punteros en §6 y backlog.

Petición concreta al Consejo: **confirmar** que las correcciones de §3.1 reflejan
fielmente lo medido. No se reabre la forma del oro (ratificada DAY 197) ni bit-exacto
(ratificado DAY 199). 10.8 diferida con ticket (`DEBT-JOIN-CONFIDENCE-001`). Con esta
confirmación, el plan cierra como ADR.

---

## 9. Changelog v1 → v2 (DAY 199)

Trazabilidad de cada cambio respecto a la v1 presentada al Consejo. El original v1 se
conserva intacto; esta v2 es un fichero separado.

| # | §  | Cambio | Origen | Veredicto medido |
|---|----|--------|--------|------------------|
| 1 | 1  | "6 verificaciones" → "9" | A3 (Claude) | fósil de versión previa |
| 2 | 3.1| Predicado particionado D/E; `ingested_at`+`temporal_anomaly` EXCLUIDAS | medición DAY 199 | `kuzu_graph_sink.hpp:47`, `cypher_builder.hpp:86` |
| 3 | 3.1| `hmac_row` fuera del predicado → integridad bronce↔oro | DeepSeek | 0 hits `hmac` en `schema.cypher` |
| 4 | 3.1| Nota: `event_id`=bronce col 2; window/seq YA materializadas | GLM/Kimi (refutadas) | `correlation_reader.cpp:85`, `cypher_builder.hpp:101,110` |
| 5 | 3.1| Guarda canónica única NaN + `-0.0` (no `memcmp` crudo) | Claude/Gemini/DeepSeek/Qwen | IEEE 754 |
| 6 | 3.1| MERGE robusto **bajo** orden de inserción determinista | Gemini/Kimi/Qwen | `cypher_builder.hpp` MERGE/ON CREATE |
| 7 | 6  | Nueva `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (P2) | hallazgo medición | `cypher_builder.hpp:86` |
| 8 | 6  | Ref `§2.6` → `§2 corolario 6` | A4 (Claude) | higiene interna |
| 9 | 8  | Cierre: "confirmar lo medido", no re-litigar; bit-exacto RATIFICADO | árbitro | — |

> Nota de scope: objeciones de gold-plating del lote (backpressure/HWM, schema evolution,
> SLA del test, key management, RBAC, retention, rollback, timezone, hash-grafo-completo)
> se declinan en este ADR por violar "una batalla" / ya cubiertas por deuda existente.
> No son defectos del circuito; son trabajo post-FEDER o de otra capa.""",
))


def fail(msg):
    sys.stderr.write("\n[ABORTADO] " + msg + "\n")
    sys.exit(1)


def main():
    path_in = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IN
    path_out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    if not os.path.exists(path_in):
        fail("No existe el original: %s" % path_in)

    # Lectura -> memoria (handle cerrado antes de cualquier escritura).
    with open(path_in, "r", encoding="utf-8") as fh:
        text = fh.read()
    original_len = len(text)

    if "## 9. Changelog v1 → v2" in text:
        fail("El original ya parece una v2 (contiene el changelog). "
             "Pásame el v1 limpio o revisa la ruta de entrada.")

    # Verificación previa: TODOS los ANTES deben casar exactamente una vez.
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
        lines.append("No se ha escrito nada. El original está intacto.")
        fail("\n".join(lines))

    # Aplicación (solo si TODO casó).
    applied = []
    for label, before, after in EDITS:
        text = text.replace(before, after, 1)
        applied.append(label)

    # Escritura a fichero separado (el original NO se toca).
    with open(path_out, "w", encoding="utf-8") as fh:
        fh.write(text)

    sys.stdout.write("OK — V2 generada: %s\n" % path_out)
    sys.stdout.write("  original : %s (%d chars, intacto)\n" % (path_in, original_len))
    sys.stdout.write("  salida   : %s (%d chars)\n" % (path_out, len(text)))
    sys.stdout.write("  ediciones aplicadas (%d):\n" % len(applied))
    for label in applied:
        sys.stdout.write("    + %s\n" % label)


if __name__ == "__main__":
    main()