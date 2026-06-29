# ADR-052 — Registro de deliberación del Consejo de Sabios (8/8)

| Campo | Valor |
|---|---|
| **ADR** | 052 — Multi-node Flow Identity & Host↔Net Correlation |
| **Versión deliberada** | v1 (borrador) |
| **Fecha** | DAY 173 |
| **Consejeros (8/8)** | Claude (CL), ChatGPT (GPT), DeepSeek (DS), Gemini (GE), Grok (GR), Qwen (QW), Kimi (KI), Mistral (MI) |
| **Árbitro final** | Alonso (pendiente) |
| **Veredicto agregado** | APROBADO CON MODIFICACIONES — ningún consejero pide rechazo ni rediseño de dirección. Los reparos son de *especificación*, no de *rumbo*. |

> **Nota de método.** Este documento *recoge* la deliberación; no decide. Las filas marcadas **[ÁRBITRO]** son disensos reales que el Consejo no resuelve por sí mismo y requieren tu decisión. El voto de Claude se trata aquí como uno más de los ocho, sin peso especial.

---

## 1. Mapa de votación (un vistazo)

| Pregunta | Consenso | CL | GPT | DS | GE | GR | QW | KI | MI |
|---|---|---|---|---|---|---|---|---|---|
| **Q1** Rate-limit: ubicación primaria | **correlation-engine, antes de Neo4j** (8/8) | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Q1** Umbral adaptativo (no fijo) | Mayoría 7/8 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✖ (1000 fijo) |
| **Q1** Nunca descartar evidencia (colapsar/marcar) | 8/8 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Q2** ARP/NDP primera clase | **Unánime 8/8** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Q2** Modelar *estado de binding*, no paquete crudo | Mayoría fuerte | ✔ | ✔ | ~ | ~ | ~ | ✔ | ✔ | ~ |
| **Q3** Sí, marca de confianza | **Unánime 8/8** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Q3** Forma de la marca | **[ÁRBITRO]** — disenso | señales | 0-100 | count | 0-1 | enum | señales | enum | enum |
| **Q4** Etiquetar, nunca borrar | **Unánime 8/8** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Q5** bettercap = vector MITRE; 052 = su threat model | **Unánime 8/8** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Q6** Descartar CrisisWindow para identidad | **Unánime 8/8** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Q6** Mecanismo de identidad intra-nodo | **[ÁRBITRO]** — 3 familias | N fijo+tol | timestamp fino | bucket+seq | session_counter | híbrido | sensor_id nativo | bucket 60s inmut. | bucket 300s |
| **Q7** P1+P3 juntos en ADR-052 | **Unánime 8/8** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |

`✔` a favor · `✖` en contra · `~` compatible con matices

---

## 2. Síntesis pregunta por pregunta

### Q1 — Rate-limit / cardinalidad de `community_id`

**Consenso.** El control **primario vive en el correlation-engine, antes de la ingesta a Neo4j**. Neo4j nunca es el rate-limiter primario (cuando el grafo te frena, el daño ya ocurrió) — a lo sumo backstop vía constraint. Métrica = **cardinalidad de `community_id` distintos por ventana por `node_id`** (DS, GE, QW lo precisan; no nº de eventos). Umbral **adaptativo sobre baseline por nodo** (CL/rol, GPT 10×p95, DS ~media+σ, GE/QW 3σ, GR media+3-5σ, KI 10× histórico) — solo MI propone fijo (1000). **Nunca se descarta evidencia**: al superar el cap, el flujo se marca y/o colapsa en un meta-nodo de primera clase (GE `:GraphFloodingAnomaly`, QW `:HighCardinalityFlowCluster`, GPT degrade-priority, CL `rate_limited:true` + evento). El flooding *es* el ataque: que salte el cap es una detección.

**Implementación sugerida (convergente).** Estructura probabilística en stream para medir cardinalidad sin reventar memoria: **Count-Min Sketch** (GE, QW) o **HyperLogLog** (DS, QW) por `node_id`, ventana deslizante. Conecta con `orphan_rate` (ADR-051).

**[ÁRBITRO] — ¿rate-limit también en el sensor?** KI (dos capas: publicación en sensor + aceptación en ingest), CL (autolímite grueso para proteger el IPC), GPT (sensor solo telemetría, no bloquea), DS (feedback al sensor) dicen sí. **MI dice no**: un sensor comprometido no respeta su propio límite. *Reconciliación posible:* el límite en sensor es **backpressure** para proteger el bus IPC y al motor (defensa frente a sensor sano desbocado o carga), **no** un control de seguridad; el control de seguridad real es el del motor. Si aceptas esta distinción, ambas posturas coexisten.

---

### Q2 — Señal ARP/NDP: primera clase o enriquecimiento

**Consenso unánime: primera clase.** Es el único detector del vector A (MITM L2 sigiloso); como enriquecimiento embebido en `:NetworkFlow` se pierde la consulta temporal y la capacidad de observar ARP sin flujo asociado (KI lo argumenta con rigor).

**Cómo modelarlo (consenso fuerte): estado de binding, no volcado de paquetes.** No un nodo por paquete ARP (colapsaría el grafo — irónico dado Q1). Un nodo de **estado** de binding IP↔MAC con propiedades temporales, y el **re-binding (cambio de MAC para una IP) como la señal**:
- Nombres propuestos: `:IpMacBinding` con `valid_from`/`valid_to` (QW), `:L2Resolution` con `previous_mac` (KI), `:L2Binding` (GE), `:MACBinding`/`:ARPEvent` (GR), `:NeighborBinding`/`:ARPObservation` (GPT), `:ArpCacheEntry` (DS). Mismo concepto, nombre a fijar.
- Encaja con el inventario de endpoints de ADR-046 §3.9.

**Dos límites que el Consejo añade al borrador (no estaban en §3.4):**
- **[LÍMITE FUNDAMENTAL — KI]** ARP/NDP solo detecta el vector A **bajo el supuesto de host sano**. Si el atacante tiene root en el endpoint, la señal ARP que reporta Wazuh *también* miente. Para host comprometido se necesita **una tercera fuente out-of-band** (switch con port-security, sensor en modo promiscuo que vea las solicitudes ARP). Sin ella, vector A con host comprometido es **indetectable por diseño**. → debe constar como nota de límite en §3.4.
- **[ALCANCE — QW]** El vector A no es solo L2. MITM por **rogue gateway / DNS poisoning / BGP hijack** no cambia la MAC. La señal de host debería incluir también **anomalías de estado TCP** (RST inesperados, saltos de seqnum = inyección en conexión) y **mismatches TLS** (certificado distinto al esperado), vía Wazuh/osquery.

---

### Q3 — Marca de confianza de flujo

**Consenso unánime: sí.** Basada en corroboración cross-sensor + método NAT + `orphan_rate`.

**[ÁRBITRO] — forma de la marca.** Tres opciones:
- **Score continuo** — GPT (0-100), GE (0-1). Filtra fácil (`WHERE confidence > 50`).
- **Enum ordinal** — KI (`CORROBORATED`/`SINGLE_SENSOR`/`ORPHAN`/`INJECTED`/`CONFLICT_NAT`), MI (`HIGH`/`MEDIUM`/`LOW`/`INJECTED`), GR, DS (`corroboration_count` entero).
- **Vector de señales primitivas + tier derivado** — QW (`is_cross_sensor_corroborated`, `is_host_plane_anchored`, `nat_resolution_method`, `trust_tier`), CL (guardar `witness_count`/evidencia, derivar confianza como vista computada, no congelar).

*Aviso de dos consejeros:* GPT y CL advierten explícitamente contra un único valor que **envejece mal** / es opaco (`trusted=true`, float congelado al ingestar). La opción "señales primitivas + tier derivado" las subsume: guardas lo medible, recomputas el verdicto cuando evolucione la semántica.

**[OBJECIÓN CL+DS — depende de una pieza que falta]** "Visto por 1 sensor" **no** es sospechoso por sí mismo: es lo normal en **cobertura no solapada**. Sin un **mapa de cobertura/visibilidad de sensores** (qué sensor puede ver qué segmento/VLAN/subred), `orphan_rate` queda dominado por flujos benignos de cobertura única y es ruido como señal de compromiso; y la regla "flujo sin sensor de borde trazable = anomalía" (§3.1/§3.4) no tiene contra qué validarse. → **nueva DEBT** (ver §4, A-NEW-1). Doble respaldo.

**Categoría `INJECTED` en `acceptance_criteria.md`.** Consenso de que debe existir. **[MATIZ CL]**: no metas `INJECTED` *dentro* del enum congelado DROP/CONFIG/POLICY/BUG/UNKNOWN — ese enum responde "por qué observado ≠ esperado en corrida benigna"; `INJECTED` es otro eje (procedencia adversaria). Ponlo en un eje `provenance` separado para no descongelar el artefacto ni cometer error de categoría. (Resuelve también Q4.)

---

### Q4 — Etiquetar inyección sin excluir del dataset

**Consenso unánime: etiquetar (label/taint), nunca borrar.** Filtrar por defecto en queries de producción (`WHERE NOT n:SuspiciousFlow`), incluir explícitamente en MITRE/threat-hunt (GE, QW, DS, MI, GPT). El atacante es parte del ground truth.

**Dos aportes que elevan la integridad científica (recogerlos ambos):**
- **[CL] Separar dos campos ortogonales que NUNCA se colapsan:** `INJECTED_SUSPECTED` (heurística runtime: cid huérfano, `node_id` sin sensor de borde trazable, re-binding correlado) vs `INJECTED_GROUND_TRUTH` (del manifiesto del escenario MITRE, no del detector). Si los fundes, **validas el detector contra su propia salida (circular)**. El *delta* entre ambos campos *es* tu precision/recall.
- **[KI] Procedencia trazable y no repudiable del etiquetado:** no basta `injected=true`. Arista `:TAGGED_AS {method, source: 'ADR-050-SESSION-N', timestamp, analyst}` → `:Tag`, append-only, para que un motor comprometido no pueda "des-etiquetar".

Combinados: campo suspected-vs-ground-truth (CL) + provenance del tag (KI) = etiquetado científicamente honesto **y** auditable.

---

### Q5 — Relación con ADR-050 (sesión MITRE)

**Consenso unánime.** Uno de los 6 vectores debe ser **MITM con bettercap**, y ADR-052 es su **modelo de amenaza / ground truth arquitectónico**. ADR-050 debe citar a ADR-052 como threat model subyacente.

**Aportes a recoger:**
- **Mapeo MITRE ATT&CK** (GE, QW): Vector A → **T1557** (Adversary-in-the-Middle); Vector B → **T1565** (Data Manipulation) o **T1090** (Proxy) según inyecte o tunelice.
- **[CL+DS] Dos vectores, no uno:** vector A (bettercap, L2) **y** vector B (scapy/nfqueue, L3/L4) como escenarios separados. El vector A es el único cuya detección depende *enteramente* del cruce host↔red — un camino de detección sin ground truth es un pasivo, no un activo. DS añade: los tests de ADR-050 deben verificar las dos líneas de defensa por separado.

---

### Q6 — Granularidad de `flow_start_window` (la decisión central)

**Consenso negativo unánime: CrisisWindow queda descartada como componente de identidad** (variable y dependiente de contenido → rompe determinismo cross-sensor e invalida `flow_uid` históricos si cambia la config). CL, GPT, KI explícitos; el resto, al sustituirla, implícito.

**Consenso de propiedades (lo que todos quieren, aunque difieran en cómo):**
1. La identidad debe ser **estable e inmutable una vez fijada al inicio del flujo** (KI explícito "timestamp de *inicio*, no de *actualización*"; flujos largos se extienden con aristas de duración de ADR-046, no fragmentan su identidad).
2. El bucket fijo y rígido es frágil por **skew de reloj en frontera** (el "Box-Car problem" de GE/QW).
3. **Calibrar el valor sobre golden pcap**, no fijarlo a ojo (CL percentil-1 del intervalo de reúso, GR, MI, DS test no-colisión UDP).

**[ÁRBITRO] — mecanismo. Tres familias en disputa:**

| Familia | Quién | Idea | A favor | En contra |
|---|---|---|---|---|
| **(a) Consumir `flow_id`/`uid` nativo del sensor** | QW | `flow_uid = hash(node_id ‖ sensor_native_flow_id)`; elimina la ventana para identidad | Suricata/Zeek ya resuelven la unicidad de instancia | No existe para el sniffer propio de aRGus (eBPF/XDP, paquetes crudos) — QW lo admite y cae a bucket 5min |
| **(b) `session_counter` estatal en el motor** | GE | El motor mantiene flujos activos por `(node_id, community_id)`; +1 al reciclar | Robusto a skew | Mete **estado** (Redis) en el correlation-engine; pierde cómputo local determinista; el propio GE pregunta si el motor está listo |
| **(c) `N` fijo epoch-aligned + tolerancia de match** | CL (+ GPT timestamp fino, KI/MI/DS bucket fijo) | `floor(epoch/N)`, determinista, local por sensor; el match de correlación admite ±tolerancia desacoplada de la frontera | Sin estado, computable en el sensor; NTP (DEBT-NTP cerrada DAY 167) lo sostiene | Hay que calibrar `N` y la tolerancia |

**Clarificación que conviene que zanjes primero (puede disolver medio disenso) — [CL]:** con `node_id` *dentro* del hash, dos sensores que ven el mismo flujo físico **ya producen `flow_uid` distinto por diseño** — no deben coincidir en identidad; coinciden por `community_id` (arista `FLOW_IDENTITY`). Por tanto la "fragmentación de un flujo legítimo en múltiples nodos" del §7 **no es un bug, es el modelo intencionado**, y el Box-Car (GE/QW) amenaza solo el **match de correlación** (arista), no la **identidad** (nodo). Si aceptas esta lectura: la familia (b) resuelve un problema que el diseño no tiene; el reto real se parte en dos sub-problemas con solución independiente:
- **Cortar reciclaje *intra-nodo*** → componente temporal/secuencial de inicio. Para **UDP de reúso instantáneo de puerto** (objeción válida de DS), añadir `seq_in_window`: `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window ‖ seq_in_window)`.
- **No romper el match *cross-nodo*** → tolerancia ± en correlación, desacoplada de fronteras (CL), apoyada en NTP.

**[P0 INCONTESTABLE — KI, único pero crítico] Codificación canónica del `flow_uid`.** El borrador no fija función de hash, codificación, endianness ni delimitador. Dos implementaciones (sensor C++ vs motor Python) producirán `flow_uid` distintos para el mismo flujo → rompe la unicidad. Propuesta KI: `base64(sha3-256(utf8(node_id) ‖ 0x00 ‖ utf8(community_id) ‖ 0x00 ‖ uint64_be(flow_start_window)))`. Delimitador `0x00` para evitar *prefix collision*. **Debe entrar como §3.1.1 antes de tocar Neo4j.**

---

### Q7 — ¿P1 y P3 juntos o separar a ADR-053?

**Consenso unánime: juntos en ADR-052.** Comparten esquema Neo4j (constraint compuesto, `node_id` obligatorio), modelo de amenaza (data-plane hostil) y validación (golden pcap MITRE). Separar ahora generaría deuda de esquema y referencias cruzadas frágiles.

**Condición de escisión futura (CL, DS, QW, KI):** separar **por madurez/tamaño, no por concepto** — si el trabajo de host↔red/NAT/ARP crece (varias DEBTs, su propia calibración, bloqueo por Wazuh), se escinde el *detalle de implementación* de P1 a ADR-053 dejando 052 como decisión unificadora que lo referencia. En código, QW sugiere ya separar paquetes (`correlation-engine/identity` vs `correlation-engine/host_net_bridge`).

---

## 3. Hallazgos fuera de las 7 preguntas (deben entrar a ADR-052 v2)

| # | Hallazgo | Origen | Por qué importa |
|---|---|---|---|
| H1 | **`node_id` no está definido.** ¿UUID? ¿hash de config? Propuesta: `SHA256(public_key del sensor)` ligado a certificado (SPIFFE/SPIRE) o serial de hardware. Debe estar en inventario de endpoints (ADR-046 §3.9) + cert Noise (ADR-027). | MI (fuerte), KI 2.3, DS 2.1 | Sin `node_id` inmutable y verificable, `flow_uid` colisiona y la defensa anti-inyección se reduce a "confiar en que el `node_id` es honesto". **`flow_uid` prueba autenticidad de origen, no honestidad de contenido** (KI). |
| H2 | **Codificación canónica del hash** (ver Q6, P0). | KI 2.1 | Determinismo cross-implementación. Bloqueante de esquema. |
| H3 | **Mapa de cobertura/visibilidad de sensores** (qué sensor puede ver qué segmento). | CL Q3, DS 2.1 | Sin él, `orphan_rate` y "single-sensor = sospechoso" son ruido. Habilita la defensa anti-inyección topológica. |
| H4 | **Resolución de conflictos entre mecanismos NAT del menú.** Si dos mecanismos discrepan (translation-node dice IP_A, proc+puerto dice IP_B) → consenso por mayoría ponderada por confianza; marcar `CONFLICT_NAT`; **nunca** fallback silencioso al mecanismo 4. | KI 2.4 | El §3.2 ordena el menú pero no dice qué pasa con respuestas inconsistentes. |
| H5 | **Terminología "causal-bidireccional" (§3.2) → "coincidencia temporal asimétrica".** Causalidad real (relojes de Lamport/vectoriales) es cara y frágil. | QW Riesgo B | El host plane (Wazuh) tiene mucha más latencia de ingest que el data-plane; la ventana host↔red debe ser tolerante a ese lag, no implementar causalidad. |
| H6 | **Cuantificar ventanas host↔red asimétricas.** Red→Host ~5 s; Host→Red ~30 s (configurable). | MI, QW | El §4 deja `host_bridge_window` en 15-30 s sin distinguir dirección. |
| H7 | **Definir `orphan_rate` concretamente en ADR-051** (fórmula + umbral), pero **condicionado a H3**. MI propone `cid_sensor / cid_cluster` con umbral 0.9; CL objeta que el umbral debe ser relativo a cobertura esperada, no absoluto. | MI, DS, CL | Cierra el bucle de "detección de sensor comprometido" de §3.4 línea 3. |
| H8 | **(Opcional, GPT) Documentar la distinción `FlowObservation` vs `FlowIdentity`** aunque hoy ambas sean el mismo `flow_uid`. | GPT | `flow_uid` identifica "la observación de un flujo por un sensor", no "el flujo lógico". Dejarlo escrito evita una migración dolorosa si en 1-2 años correláis múltiples observaciones del mismo flujo lógico. No obligatorio ahora. |

---

## 4. Tabla consolidada de acciones

Prioridad: **P0** = bloquea esquema Neo4j (antes de poblar) · **P1** = motor/stream · **P2** = host plane / validación · **P3** = MITRE/ground-truth.

| ID | Acción | Prio | Consenso | Depende de |
|---|---|---|---|---|
| **A1** | Ratificar `DEBT-NEO4J-FLOW-KEY-001`: `flow_uid` + `node_id` obligatorio + constraint compuesto Neo4j 5.x en `:NetworkFlow`/`:Alert`/`:TelemetryEvent`. | P0 | 8/8 | A2, A3, H1 |
| **A2** | Fijar **codificación canónica del `flow_uid`** (§3.1.1): función de hash, delimitador `0x00`, endianness, longitud. | P0 | KI (incontestable) | — |
| **A3** | **[ÁRBITRO]** Decidir mecanismo de identidad intra-nodo (familia a/b/c de Q6) y, si aplica, `seq_in_window` para UDP. | P0 | parcial | clarificación cross-node |
| **A4** | Definir **`node_id`** como identidad criptográfica verificable (clave pública del sensor / cert), no string arbitrario. | P0 | MI+KI+DS | ADR-027, ADR-046 §3.9 |
| **A5** | Schema enforcement en ingest: rechazar a DLQ todo evento sin `node_id`. | P0 | 8/8 | A1 |
| **A6** | Rate-limit de cardinalidad en **correlation-engine** (Count-Min Sketch / HyperLogLog por `node_id`, ventana deslizante, umbral adaptativo sobre baseline). Superar cap → meta-nodo `:GraphFloodingAnomaly`/`:HighCardinalityFlowCluster`, nunca drop. | P1 | 8/8 (ubicación) | ADR-051 |
| **A7** | **[ÁRBITRO]** ¿Backpressure de publicación en el sensor además del control del motor? (Kimi/CL sí como backpressure; MI no como seguridad). | P1 | disenso | A6 |
| **A8** | Menú NAT con **anotación obligatoria de método+confianza** en grafo y log + **regla de conflicto** (`CONFLICT_NAT`, mayoría ponderada, sin fallback silencioso). | P1 | 8/8 + KI(H4) | — |
| **A9** | Ventanas host↔red **asimétricas cuantificadas** (Red→Host ~5 s, Host→Red ~30 s) y renombrar "causal-bidireccional" → "coincidencia temporal asimétrica". | P1 | MI, QW | — |
| **A10** | **Marca de confianza**: guardar señales primitivas (`witness_count`, `is_host_plane_anchored`, `nat_method`+confianza) y derivar `trust_tier` como vista. **[ÁRBITRO]** forma final (score vs enum vs señales). | P1 | sí marca (8/8); forma en disputa | A11 |
| **A11** | **Nueva DEBT: mapa de cobertura/visibilidad de sensores** (sensor↔segmento). Sin él, `orphan_rate` y la defensa anti-inyección topológica son ruido. | P1 | CL+DS | — |
| **A12** | ARP/NDP como **nodo de estado de primera clase** (`:IpMacBinding` con `valid_from`/`valid_to`); el **re-binding** es la señal. `DEBT-ARGUSPP-ARP-MONITOR-001` emite *cambios de estado*, no paquetes crudos. | P2 | 8/8 (1ª clase) | Wazuh, DEBT-ARGUSPP-WAZUH-001 |
| **A13** | Nota de **límite fundamental** en §3.4: ARP/NDP detecta vector A solo con **host sano**; host comprometido requiere fuente out-of-band (switch port-security). | P2 | KI | A12 |
| **A14** | Ampliar señal de host más allá de L2: **anomalías TCP** (RST/seqnum) y **mismatch TLS** vía Wazuh/osquery (MITM L3: rogue gw/DNS/BGP). | P2 | QW | A12 |
| **A15** | Etiquetado de inyección con **dos campos ortogonales**: `INJECTED_SUSPECTED` (heurística) ≠ `INJECTED_GROUND_TRUTH` (manifiesto MITRE). Eje `provenance` **separado** del enum congelado de `acceptance_criteria.md`. | P2/P3 | CL (+ etiquetar 8/8) | A11 |
| **A16** | **Provenance del tag**: arista `:TAGGED_AS {method, source, timestamp, analyst}` append-only → `:Tag`. Filtrar por defecto en producción, incluir en threat-hunt. | P2 | KI + GE/QW/DS/MI | — |
| **A17** | Alinear ADR-050: vector A (bettercap, **T1557**) y vector B (scapy/nfqueue, **T1565/T1090**) como escenarios separados; citar ADR-052 como threat model; los flujos del red team se etiquetan `INJECTED_GROUND_TRUTH`. | P3 | 8/8 | ADR-050 |
| **A18** | Tests EMECAS++ adicionales: no-colisión UDP con reúso inmediato de puerto (DS), `orphan_rate` con sensor comprometido simulado (MI), escala (1M flujos, constraint + rate-limit) (MI/GR). | P2 | DS, MI, GR | A1, A6 |
| **A19** | (Opcional) Documentar `FlowObservation` vs `FlowIdentity` para evitar migración futura. | P3 | GPT | — |

---

## 5. Lo que te toca decidir como árbitro

Tres nudos que el Consejo deja abiertos (todo lo demás tiene consenso suficiente para implementar):

1. **A3 — mecanismo de identidad `flow_uid` intra-nodo.** Recomendación implícita del mapa: zanjar primero la clarificación cross-node (identidad ≠ correlación); si la aceptas, (c) `N` fijo + tolerancia de match queda como la opción sin estado y determinista, con (a) `sensor_native_flow_id` como refuerzo *cuando el sensor lo provea* (Suricata/Zeek) y `seq_in_window` para UDP. (b) `session_counter` estatal solo si rechazas la clarificación.

2. **A10 — forma de la marca de confianza.** Señales primitivas + tier derivado reconcilia a 6 de 8 y respeta la advertencia (GPT/CL) contra el float opaco que envejece mal.

3. **A7 — backpressure en el sensor.** Resoluble tratándolo como backpressure de IPC (no control de seguridad), lo que hace compatibles a Kimi/CL con Mistral.

Veredicto agregado del Consejo: **APROBADO CON MODIFICACIONES**. Incorporando A2, A4 y A3 (los tres P0 de esquema), se desbloquea `DEBT-NEO4J-FLOW-KEY-001` y se puede poblar el grafo.