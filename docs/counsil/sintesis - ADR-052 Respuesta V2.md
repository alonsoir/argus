# ADR-052 v2 — Síntesis de la 2ª pasada del Consejo (8/8) y plan de v3

| Campo | Valor |
|---|---|
| **ADR** | 052 — Multi-node Flow Identity & Host↔Net Correlation |
| **Versión deliberada** | v2 (borrador) |
| **Fecha** | DAY 173 — 2ª pasada |
| **Consejeros (8/8)** | Claude (CL), ChatGPT (GPT), DeepSeek (DS), Gemini (GE), Grok (GR), Qwen (QW), Kimi (KI), Mistral (MI) |
| **Árbitro final** | Alonso (pendiente) |
| **Veredicto agregado** | **Ratificada la dirección (8/8). Nadie pide rediseño.** Rango de estado: "APROBACIÓN DEFINITIVA" (QW) · "listo para ratificar" (DS, GR) · "v2→v2.1, no v3" (KI) · "aprobado con observaciones" (GPT). |
| **Recomendación de este registro** | **Generar una v3 incorporativa (no direccional)** como candidata a ratificación: mete los parches acordados + el arbitraje de Alonso en 3 divisiones. Probablemente no requiera otra pasada completa, solo confirmación de fidelidad. |

> **Por qué v3 y no ratificar v2 directamente.** El Consejo se inclina a "v2.1 menor", pero la 2ª pasada destapó **un bug de corrección** (N1, contradice una regla permanente del proyecto y §0) y **3-4 huecos que afectan a la integridad del corpus** con fix consensuado. Tocar el esquema antes de poblar Neo4j es gratis ahora y caro después (mismo argumento de §2.3 del propio ADR). La v3 es de *especificación*, la dirección queda intacta.

---

## 1. Ratificado por unanimidad (cerrar en v3)

| Punto | Estado |
|---|---|
| **§0 — misión primaria (corpus como producto)** | Elogio unánime. KI/MI piden elevar la frase a invariante permanente del proyecto. |
| **Q1 — §3.1.3 (identidad ≠ correlación cross-nodo)** | **RATIFICADO 8/8.** Dos sensores honestos producen `flow_uid` distinto por diseño; el skew solo amenaza la arista `FLOW_IDENTITY`. "Box-Car problem" = falsa alarma. `session_counter` estatal **enterrado**. Cierra Q6 de la 1ª pasada definitivamente. |
| **Q5 — `provenance` ortogonal al enum congelado** | **RATIFICADO 8/8.** Eje aparte; `acceptance_criteria.md` intacto. |
| **§3.6 — confianza como features primitivas (no float opaco)** | Ratificado 8/8 (con matiz Q4: añadir score continuo *derivado*). |
| **§3.7 — etiquetado dual suspected/ground_truth** | Ratificado 8/8 como la contribución metodológica más fuerte (con matiz N4: el append-only necesita WAL externo). |
| **§3.8 — mapa de cobertura como prerrequisito** | Ratificado 8/8 (con matiz Q2: falta modelo de datos). |
| **§3.9 — ARP/NDP como nodo de estado** | Ratificado 8/8. |

---

## 2. Respuestas Q1–Q7 de la 2ª pasada (consenso y divisiones)

### Q1 — Ratificar §3.1.3
**8/8 SÍ.** Sin matices. Cerrar en el cuerpo del ADR. Test EMECAS++ obligatorio (KI, GR): dos sensores ven el mismo flujo → `flow_uid` distintos + arista `FLOW_IDENTITY` correcta.

### Q2 — Diseño del mapa de cobertura (§3.8)
**Consenso de forma:** tabla de adyacencia declarativa `node_id → {segmentos/VLAN/subred}`, derivada del inventario de endpoints (ADR-046 §3.9), con **lookup rápido en el correlation-engine (cache Redis/etcd)** — NUNCA `MATCH` en Neo4j por paquete (colapsaría el throughput: QW, GR, KI explícitos).
- **División menor (dónde vive la autoridad):** 7/8 → autoridad es tabla/cache, Neo4j a lo sumo vista/visualización (GPT "tabla autoridad + grafo visualización"; QW "no aristas dinámicas en Neo4j"; GR "grafo ligero + tabla materializada cache"; KI/DS/GE tabla). **Solo MI** propone Neo4j como primario. → adoptar la mayoría.
- **Añadidos a recoger:** debe ser **declarado, no auto-descubierto** —auto-descubrir cobertura bajo data-plane hostil es circular (CL). Debe ser **versionado y timestampeado** —los pesos IPW dependen de él; si cambia a mitad de captura sin versión, los pesos se computan contra topología equivocada; se archiva junto al corpus como ground truth (CL). **Fuente de verdad = orquestador (Vagrant/Ansible)**, validación por **beacons/heartbeats** (KI).

### Q3 — Calibración de `N` y `nat_confidence_floor`
**Consenso de método:** medir sobre golden pcap la distribución del intervalo de reúso de 5-tupla intra-nodo; fijar `N` bajo un percentil bajo.
- **División menor (percentil):** P1 con margen (CL, DS, KI, GR, MI, GPT) vs **P5 conservador** (QW, para no fragmentar sesiones con pausas largas) vs `min(Δt)·0.5` con piso 60 s (GE). → calibrar, no hardcodear; 60 s queda como default LAB explícitamente provisional.
- **Añadidos:** calibrar **por protocolo separado** (TCP vs UDP reciclan distinto; un solo `N` es un error) (CL, GR). `nat_confidence_floor` **no** se calibra sobre pcap benigno: mide fiabilidad del *mecanismo* → contra escenarios NAT/MITRE etiquetados (CL, QW). Confianza **por mecanismo** (GR: LOG 0.9 / AGENT_ID 0.75 / PROC_PORT 0.5 / TEMPORAL 0.3; GE floor 0.70; KI 0.6; QW = precisión mínima medida). `CONFLICT_NAT` se marca **independientemente del floor**.

### Q4 — Forma del `trust_tier`
**Consenso fuerte (8/8): AMBOS, segregados por capa.** Enum en el grafo (`CORROBORATED`/`SINGLE_SENSOR`/`ORPHAN`/`CONFLICT_NAT`) para queries/UI/threat-hunt; **score continuo computado en el pipeline de features ML, NO congelado en Neo4j** (QW explícito: "no ensuciéis el esquema con scores de ML").
- **Añadido clave (CL, refinado por KI):** el rol de `witness_count` en el IPW es **el inverso del intuitivo** — `witness_count` alto = más confianza PERO más duplicación de la misma muestra física → el peso por muestra debe **bajar**, no subir, o el modelo sobre-aprende los segmentos bien cubiertos (covariate shift por la puerta de atrás). Fórmula KI que lo resuelve: `score = min(1, corroboration_count / expected_witnesses)` con `expected_witnesses` del mapa de cobertura → `SINGLE_SENSOR` en segmento de cobertura única da score 1.0 (no penalizado). **Esto ata Q4 a Q2: el score IPW no es computable sin el mapa de cobertura.**

### Q5 — `provenance` y `acceptance_criteria.md`
**8/8 confirmado.** Eje ortogonal, enum congelado intacto. Cerrar.

### Q6 — Fuente out-of-band para vector A con host comprometido (§3.4.1)
**Consenso:** documentar el límite honestamente (coherente con "escudo, nunca espada") + **no bloquea la ratificación**.
- **División de matiz (DEBT sí/no y prioridad):** abrir DEBT de baja prioridad (GPT `DEBT-OUTOFBAND-L2-001`, KI `DEBT-ARGUSPP-OOB-MITM-001` P2, MI `DEBT-ARGUSPP-PORT-SECURITY-001`, DS `DEBT-SWITCH-PORT-SECURITY-001` P3, CL "el switch ya está en la compra FEDER → documentar-y-reubicar, no documentar-y-aceptar", QW "Canary Host") **vs** GE "asumir el límite y CERRAR para FEDER, no abrir sumidero de tiempo". → mayoría 6/8: documentar + DEBT exploratoria de baja prioridad.
- **Añadido importante (GPT):** no es solo ARP lo que miente con host comprometido — osquery, Wazuh, eBPF local y la tabla ARP **también**. El host plane entero pierde independencia observacional. Generalizar la nota de §3.4.1.

### Q7 — Señal de host más allá de L2 (TCP/TLS) (§3.3)
**División real:** diferir a ADR-053 manteniendo el gancho conceptual (GPT, DS, QW "cerrad 052 y avanzad", KI, CL, GE "diferir parsing, reservar propiedades de anclaje") **vs** incluir lo básico en v2 (GR: RST/seqnum/TLS-mismatch sí, JA3 no; MI alta prioridad). → **mayoría 6/8: diferir a ADR-053**, mantener la mención de alcance en §3.3 (ya está) y reservar el punto de anclaje genérico (GE).

---

## 3. Hallazgos nuevos de la 2ª pasada (lo que decide la v3)

Prioridad de impacto: **🔴 fuerza v3** · **🟠 debería ir en v3** · **🟡 mejora, opcional**.

| # | Hallazgo | Origen | Impacto | Acción v3 |
|---|---|---|---|---|
| **N1** | **`node_id = SHA256(public_key)` se rompe contra la regla permanente "keypair se regenera en cada `vagrant destroy+up`"** → `flow_uid` inestable entre reconstrucciones → corpus no reproducible (viola §0). Los otros 7 ratificaron sin detectarlo (no conocen la regla). Separar identidad de *autenticación* (clave efímera) de identidad de *corpus* (estable: nombre de sensor + época declarada persistente). | CL | 🔴 **bug de corrección** | Reescribir §3.1.2: `node_id` estable y declarado; la clave pública firma, no *es* el `node_id`. |
| **N2** | **`seq_in_window` no reproducible desde pcap**: depende del orden de llegada al sensor; tcpreplay/NIC reorder/drops lo alteran → `flow_uid` divergente. Fix consensuado: **se computa en el sensor y se transporta en el evento (Protobuf), NO se recomputa offline.** El evento es la unidad de reproducibilidad. | KI, GE, GR | 🔴 integridad de corpus | §3.1.4: `seq_in_window` transportado, no recomputado. + nota crash-recovery/persistencia del contador (GR). |
| **N3** | **`sensor_native_flow_id` como componente del hash es peligroso**: Suricata reinicia `flow_id`; normalizar `uint64`(Suricata) con `string`(Zeek) en el hash es ambiguo. Fix: **propiedad de trazabilidad, NO componente de `flow_uid`** — el hash mantiene fórmula canónica tool-independiente. **Contradice v2 §3.1.4 pto 4.** | KI (MI discrepa) | 🟠 **[ÁRBITRO]** | Corregir §3.1.4 pto 4. Arbitraje: KI (propiedad) vs MI (priorizar nativo). Argumento KI más fuerte y pro-corpus. |
| **N4** | **Append-only del etiquetado (§3.7) es falso como está escrito**: Neo4j es mutable; motor comprometido borra aristas. No-repudio exige **WAL externo (etcd/ADR-048 o hash-chain)** como fuente de verdad; Neo4j = vista materializada. Toca la integridad del corpus. | KI | 🟠 integridad de corpus | §3.7: añadir WAL externo; Neo4j vista materializada. Test: grafo contiene todas las entradas del WAL. |
| **N5** | **SHA3-256 vs stack único**: libsodium no trae SHA3 → dependencia nueva contra la disciplina del proyecto; y length-extension no aplica (§3.5 dice que `flow_uid` no es control de seguridad). Usar **BLAKE2b** (nativo libsodium) o SHA-256. Los otros no objetan SHA3 pero **no conocen la restricción libsodium**. | CL | 🟠 **[ÁRBITRO]** | Decisión de Alonso con el dato de stack que solo él tiene. Si se cambia: `SHA3-256` → `BLAKE2b` en §3.1.1. |
| **N6** | **Rate-limit: cardinalidad exacta, no HLL, para la etiqueta**: HLL tiene ~2% error y CMS estima frecuencia, no cardinalidad de elementos nuevos. Para la etiqueta `rate_limited` que entra al corpus se necesita exactitud (docenas de sensores, N=60s → contador exacto en memoria factible). HLL solo para dashboards. | KI | 🟠 integridad de corpus | §3.10: cardinalidad exacta en el motor para la decisión; HLL solo observabilidad. |
| **N7** | **Event time vs processing time + watermark**: las ventanas host↔red (§3.2.2) deben ser **event time** con ventana de retención/watermark, no processing time (Wazuh bufferea minutos). Las ventanas 5s/30s son tolerancia de skew, no latencia de ingest. | KI | 🟠 define implementación | §3.2.2: aclarar event time + watermark. |
| **N8** | **`CONFLICT_NAT` → peso IPW nulo/penalizado**: los puentes NAT en conflicto deben recibir peso nulo o penalizado en el IPW para no meter ruido en las fronteras de decisión. | GE | 🟡 nota | §3.2.1/§3.6: nota de conexión con ADR-040. |
| **N9** | **`FlowObservation` vs `FlowIdentity`: de nota opcional a deuda documentada**: para que nadie en un año reutilice `flow_uid` como identidad global de sesión. `flow_uid` identifica la *observación*, no el *flujo lógico*. | GPT | 🟡 higiene | Abrir `DEBT-ARCH-FLOW-OBSERVATION-001` (P3). |
| **N10** | **§0.1 Métricas de calidad del corpus**: KPIs que hacen §0 medible — % flujos con `provenance_ground_truth` validado, % con `witness_count≥2`, tiempo de reconstrucción desde pcap, cobertura de técnicas MITRE, balance de clases. | MI | 🟡 valioso | Añadir §0.1 con KPIs objetivo. |
| **N11** | **Definición de `agent_id`** (paralelo al hueco de `node_id`): `agent_id = SHA256(hostname‖domain‖os_uuid)` con `/etc/machine-id`. + manejo DHCP (clave `agent_id`+MAC, no IP). | MI | 🟡 hueco de definición | §3.2: definir `agent_id` canónico. |
| **N12** | **Crecimiento del grafo / archivado**: la retención de §0 hace crecer el grafo sin límite. Resolver con **almacenamiento por niveles** (grafo caliente + archivo frío en data lake/Parquet), NO con borrado (§0 prohíbe borrar). | MI, GR | 🟡 tensión operativa | Nota en §7: tiered storage, no deletion. |

---

## 4. Plan de v3 (incorporativa, no direccional)

**Entra sí o sí (🔴/🟠):** N1 (reescribir `node_id`), N2 (`seq_in_window` transportado), N4 (WAL externo para append-only), N6 (cardinalidad exacta), N7 (event time/watermark), + cerrar Q1 y Q5 en el cuerpo, + Q2 (modelo de datos del mapa de cobertura: tabla/cache, declarado, versionado), + Q4 (score IPW derivado con normalización por cobertura y el matiz inverso de `witness_count`).

**Requiere tu arbitraje antes de redactar (3 divisiones reales):**
1. **N3 — `sensor_native_flow_id`:** ¿propiedad de trazabilidad (KI) o componente que puede sustituir el temporal (MI / v2 actual)? Recomendación: KI, por colisión + normalización + unificación de esquema, y es lo más pro-corpus.
2. **N5 — SHA3-256 → BLAKE2b:** tu decisión con el dato de libsodium que el resto del Consejo no tiene. Recomendación: BLAKE2b (nativo, sin dependencia nueva, y el argumento cripto de SHA3 no aplica aquí).
3. **Q7 — TCP/TLS:** diferir a ADR-053 (mayoría 6/8) o incluir lo básico ya (GR, MI). Recomendación: diferir, mantener gancho en §3.3.

**Mejoras opcionales (🟡) que recomiendo meter porque son baratas y pro-misión:** N9 (deuda FlowObservation), N10 (§0.1 métricas de corpus), N11 (definir `agent_id`), N12 (nota tiered storage), N8 (nota IPW de CONFLICT_NAT).

**Pregunta abierta que GE devuelve y conviene contestar en la implementación (no bloquea v3):** cómo estructurar el pipeline del sniffer C++20 para que `seq_in_window` se compute idéntico en vivo y en replay, independiente de la carga de CPU. Lo resuelve N2 (transportar, no recomputar), pero la mecánica del sensor es trabajo de implementación.

---

## 5. DEBTs actualizadas

| DEBT | Prio | Estado |
|---|---|---|
| `DEBT-NEO4J-FLOW-KEY-001` | P0 | Ratificada; se cierra al aplicar §3.1.1 corregido (N5) + constraint. |
| `DEBT-FLOWUID-CANONICAL-ENCODING-001` | P0 | Ajustar a la decisión N5 (función de hash) + test de paridad C++/Python + caso dos-sensores (N2). |
| `DEBT-NODEID-CRYPTO-IDENTITY-001` | P0 | **Reescribir** según N1 (identidad de corpus estable ≠ clave de autenticación efímera). |
| `DEBT-SENSOR-COVERAGE-MAP-001` | P1 | Especificar modelo de datos (tabla/cache declarada, versionada, fuente=orquestador, validación=beacons) — Q2/N. |
| `DEBT-ARGUSPP-ARP-MONITOR-001` | P1 | Eventos de cambio de estado `:IpMacBinding`. |
| `DEBT-LABEL-WAL-001` (NUEVA) | P1 | WAL externo (etcd) para no-repudio del etiquetado; Neo4j vista materializada — N4. |
| `DEBT-ARGUSPP-OOB-MITM-001` (NUEVA) | P2/P3 | Port-security/SPAN en el switch FEDER como fuente out-of-band — Q6. |
| `DEBT-ARCH-FLOW-OBSERVATION-001` (NUEVA) | P3 | Documentar `FlowObservation` vs `FlowIdentity` — N9. |
| `DEBT-CORPUS-QUALITY-METRICS-001` (NUEVA) | P2 | KPIs de calidad del corpus — N10. |
| ADR-053 (stub) | — | Señales de host extendidas (TCP/TLS) — Q7. |

---

## 6. Recomendación final

**Generar ADR-052 v3 incorporativa.** La dirección está ratificada 8/8; la v3 cierra Q1/Q5, incorpora los fixes de corpus-integridad consensuados (N2, N4, N6, N7), corrige el bug N1, y materializa tu arbitraje sobre N3, N5 y Q7. Hecho eso, la v3 es candidata a `APROBADO` y desbloquea la población de Neo4j —probablemente con una confirmación de fidelidad del Consejo en vez de una tercera deliberación completa.

El único punto que te pediría no dar por cerrado sin decisión explícita es **N1**: es el que ningún otro consejero vio y el único que, de no corregirse, mete un defecto silencioso en la reproducibilidad del corpus —que es, por §0, la misión.