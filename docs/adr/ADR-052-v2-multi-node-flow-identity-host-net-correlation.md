# ADR-052 — Multi-node Flow Identity & Host↔Net Correlation

| Campo | Valor |
|---|---|
| **ADR** | 052 |
| **Versión** | **v2 (borrador)** — incorpora deliberación del Consejo (DAY 173) y subordina el diseño a la misión primaria (§0) |
| **Fecha** | DAY 173 (rev. v2) |
| **Estado** | BORRADOR v2 — pendiente segunda pasada del Consejo de Sabios |
| **Decisión final** | Alonso (pendiente) |
| **Deliberación** | Consejo de Sabios (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen) — primera pasada cerrada; segunda pendiente |
| **Recoge** | P3 (identidad de flujo multi-nodo) + P1 (correlación host↔red) del Consejo DAY 170 |
| **Depende de / relaciona** | ADR-046 v4 (modelo dual de claves, grafo temporal, inventario de endpoints), ADR-051 (Seed Parity Gate / `orphan_rate`), ADR-050 (sesión MITRE — ground truth), ADR-048 (etcd HA / correlación), **ADR-040 (ML Plugin Retraining Contract — walk-forward, golden set, IPW)**, **ADR-027 (identidad criptográfica de sensor)** |
| **Ratifica** | DEBT-NEO4J-FLOW-KEY-001 (P0 esquema, constraint Neo4j 5.x antes de poblar el grafo) |
| **Cambios v1 → v2** | (1) Nuevo §0: misión primaria como principio ordenador. (2) Resueltas Q1–Q7 con el consenso del Consejo. (3) Codificación canónica del `flow_uid` (§3.1.1, P0). (4) Definición criptográfica de `node_id` (§3.1.2). (5) `node_id` ≠ identidad cross-nodo aclarada (§3.1.3). (6) Confianza como *features* y no como veredicto opaco (§3.6). (7) Etiquetado en dos campos ortogonales suspected/ground-truth (§3.7). (8) Mapa de cobertura de sensores como prerrequisito (§3.8). (9) Resolución de conflictos NAT (§3.2.1). (10) Terminología "causal-bidireccional" → "coincidencia temporal asimétrica". |

---

## 0. Misión primaria (principio ordenador)

> **El grafo no es el producto. El producto es el corpus.**

aRGus existe para producir, validar y firmar **modelos ensemble en formato plugin** que hayan demostrado —con honestidad científica— ser mejores que sus predecesores. El grafo de correlación que define este ADR es **el aparato que fabrica el corpus de entrenamiento enriquecido** del que salen esos modelos. La correlación en vivo es un beneficio secundario y bienvenido; la razón de ser del grafo es el dataset.

**Invariante de proyecto (nuevo, a añadir a los permanentes):**
> *El grafo de aRGus es, antes que nada, un corpus de entrenamiento que además hace correlación en vivo. Cuando ambos fines chocan, ganan la **retención** y la **integridad de la etiqueta**. No se borra evidencia; se etiqueta con procedencia. El atacante es ground truth, no ruido a limpiar.*

Esto se alinea con dos decisiones ya tomadas en el proyecto y las explica retroactivamente:

1. **El marco de los tres paradigmas** (CTU-13 Neris: Suricata F1=0.000, Zeek F1=0.042, aRGus F1=0.9985). Suricata, Zeek y Wazuh **no pueden ser activadores primarios** contra el firewall —ni por capacidad de detección demostrada, ni por soberanía digital (ENS/NIS2/GDPR). Esa acción se delega en aRGus. Pero el grafo los reconvierte: dejan de ser **gatillos** y pasan a ser **testigos, oráculos de etiquetado y corroboradores**. Las tres herramientas que *no* pueden apretar el gatillo se convierten en **maestros del modelo de aRGus**. Ése es el sentido último del `community_id` como clave de correlación cross-tool.

2. **El bucle adversarial (ACRL/Caldera) y el sesgo de los datasets académicos** (covariate shift, documentado en el paper). Un corpus production-grade necesita capturar al atacante real y retenerlo etiquetado, no un dataset "limpio" que destruye la validez externa del modelo.

**Consecuencia de diseño que recorre todo el ADR.** Cada decisión de esquema se juzga contra la pregunta: *¿mejora la calidad, la trazabilidad o la reproducibilidad del corpus de entrenamiento?* En particular:

- La **integridad de la etiqueta** (§3.7) es el producto, no una nota metodológica.
- La **marca de confianza** (§3.6) son *features* de entrenamiento y *pesos de muestra* (IPW, ADR-040), no un filtro de queries.
- El **mapa de cobertura de sensores** (§3.8) es prerrequisito de la honestidad estadística (sin él, los pesos IPW son basura y el covariate shift vuelve a morder).
- La **identidad de flujo** (§3.1) debe ser **reproducible offline**: poder reconstruir el `flow_uid` desde un pcap archivado es condición para reconstruir el dataset. Esto descarta cualquier identidad que dependa de estado efímero no reproducible.

---

## 1. Estado

BORRADOR v2. Formaliza dos decisiones que ADR-046 v4 dejó abiertas o solo esbozadas, ahora subordinadas a §0:

1. **Identidad de nodo-flujo en el grafo** (P3 DAY 170): `flow_uid` cierra el hueco de unicidad en despliegue multi-nodo con reciclaje de 5-tuplas.
2. **El community_id ante un data-plane hostil** (modelo de amenaza DAY 171): la defensa contra MITM/inyección es arquitectónica, nunca del hash.

> **Delimitación con ADR-046 v4 (anti-duplicación).** ADR-052 NO redefine el modelo dual de claves (§3.1 de ADR-046), el grafo temporal con aristas tipadas (§3.2), el inventario de endpoints como estado de primera clase (§3.9) ni la cuota anti-pinning fail-closed (§3.5). ADR-052 *consume* esas decisiones y añade: (a) la identidad de nodo `flow_uid`, (b) el modelo de amenaza como justificación de segundo orden, y (c) **la lente del corpus (§0) sobre todas ellas**. Donde haya solape, ADR-046 v4 es la fuente; ADR-052 referencia, no reescribe.

---

## 2. Contexto

### 2.1 El community_id no es identidad de nodo

`community_id` es clave de **correlación**: tres sensores honestos que ven el mismo paquete coinciden (validado DAY 171, diana `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`). Como identidad de nodo en Neo4j es insuficiente por dos razones independientes:

- **Reciclaje de 5-tupla en el tiempo.** La misma 5-tupla se reutiliza en sesiones distintas. Dos flujos legítimos no relacionados producen el mismo `community_id`; como identidad se fundirían en un nodo — corrupción de estructura **y contaminación del corpus** (dos muestras de entrenamiento distintas colapsadas en una).
- **Mundo multi-nodo.** Dos sensores en nodos físicos distintos pueden ver flujos con la misma 5-tupla (NAT, rangos privados solapados). Mismo `community_id`, flujos distintos.

Conclusión: `community_id` es **propiedad indexada** (clave de correlación + verificable contra oráculo `pycommunityid`), nunca identidad de nodo.

### 2.2 El data-plane es hostil, no solo ruidoso

ADR-046 v4 modela latencia, reorden y pérdida (ruidoso). ADR-052 añade **adversario activo con capacidad de modificar paquetes en runtime**: bettercap (ARP/NDP spoofing, inyección), scapy/ad hoc (fabricación de cabeceras), nfqueue/libnetfilter_queue (mutación en el kernel), eBPF/tc (reescritura a velocidad de línea).

Bajo este supuesto, **todo lo observado puede ser una mentira fabricada.** El `community_id` —función pura de la 5-tupla— hereda esa hostilidad: *garbage in, garbage hashed*. La integridad del hash ≠ integridad del contenido hasheado. **Para el corpus, esto significa que la procedencia de cada muestra debe ser trazable: una muestra inyectada es ground truth valioso solo si está etiquetada como tal con su origen.**

### 2.3 Por qué hay que decidir esto ANTES de poblar Neo4j

El esquema de identidad (constraint, propiedades obligatorias, codificación del hash) es doloroso de retrofitear con datos en producción y gratis con el grafo vacío. DEBT-NEO4J-FLOW-KEY-001 es P0 de esquema porque bloquea el correlation-engine. **Y porque un corpus construido sobre un esquema de identidad defectuoso es un corpus envenenado desde el origen.** ADR-052 ratifica ese esquema para desbloquearlo.

---

## 3. Decisión

### 3.1 Identidad de nodo-flujo: `flow_uid` (P3)

```
flow_uid = H( node_id ‖ community_id ‖ flow_start_window )
```

- **`community_id`** — propiedad indexada del nodo (correlación + verificable). NUNCA identidad.
- **`node_id`** — identificador criptográfico del sensor emisor (§3.1.2). Obligatorio. Ancla cada flujo a su origen físico.
- **`flow_start_window`** — componente temporal de **inicio inmutable** del flujo (§3.1.4). Corta el reciclaje de 5-tuplas en el tiempo.

**Propiedades obligatorias en el grafo:** `node_id` en `:NetworkFlow`, `:Alert`, `:TelemetryEvent`. Constraint compuesto nativo Neo4j 5.x sobre la identidad de nodo-flujo.

**Triple justificación del `flow_uid` (v2):**
1. **Identidad / dedup** (P3): unicidad de nodo en mundo multi-nodo con reciclaje temporal.
2. **Defensa anti-inyección** (§5): un flujo que aparece sin emisión del sensor de borde correspondiente es anomalía detectable; `flow_start_window` corta el clonado temporal.
3. **Integridad del corpus (§0):** una muestra de entrenamiento por instancia de flujo real, reproducible offline desde el pcap archivado.

#### 3.1.1 Codificación canónica (P0 — bloqueante de esquema)

> *Resuelve el hueco detectado por el Consejo (Kimi): sin codificación canónica, el sensor (C++) y el correlation-engine (Python) producen `flow_uid` distintos para el mismo flujo, rompiendo la unicidad en silencio y corrompiendo el corpus.*

```
flow_uid = base64( SHA3-256(
    utf8(node_id)            ‖ 0x00 ‖
    utf8(community_id)       ‖ 0x00 ‖
    uint64_be(flow_start_window)
) )
```

- **Función:** SHA3-256 (resistencia a length-extension; higiene, no control de seguridad — el hash NUNCA es control de seguridad, §3.5).
- **Delimitador `0x00`** entre campos para evitar *prefix collision* (`node="A‖B",cid="C"` vs `node="A",cid="B‖C"`).
- **`flow_start_window`** como `uint64` big-endian (bucket ID o epoch, según §3.1.4).
- **`base64`** para `STRING` Neo4j sin caracteres de control.
- **Test de paridad cross-implementación obligatorio** (EMECAS++): C++ y Python deben producir `flow_uid` idéntico sobre el mismo vector. Mismo patrón que la paridad `pycommunityid` ya en uso.

#### 3.1.2 Definición de `node_id` (P0)

> *Resuelve el hueco detectado por el Consejo (Mistral, Kimi, DeepSeek): el borrador v1 no definía qué ES `node_id`.*

`node_id` es **identidad criptográfica verificable del sensor**, no un string arbitrario:

```
node_id = base64( SHA256( sensor_public_key ) )
```

ligada al certificado/par de claves del sensor (compatible con la infraestructura Ed25519/Noise de ADR-027) y registrada en el **inventario de endpoints** (ADR-046 §3.9). Esto garantiza unicidad global, trazabilidad criptográfica del origen y la posibilidad futura de que el sensor **firme** sus flujos.

**Aclaración de alcance (Kimi):** `flow_uid` es prueba de **autenticidad de origen**, NO de **honestidad de contenido**. Un sensor comprometido con `node_id` válido puede emitir `community_id` fabricados; eso lo detecta `orphan_rate` (§3.6, ADR-051) *a posteriori*, no el `flow_uid`. La suficiencia requiere la tríada: (1) `flow_uid` bien formado, (2) `node_id` en inventario con certificado válido, (3) `community_id` corroborado o dentro del `orphan_rate` tolerable.

#### 3.1.3 `node_id` distingue por diseño: identidad ≠ correlación cross-nodo

> *Aclaración que resuelve la mitad del disenso del Consejo en Q6 (el "Box-Car problem" de Gemini/Qwen). **Pendiente de ratificación explícita del Consejo en la 2ª pasada.***

Como `node_id` está **dentro del hash**, dos sensores que observan el mismo flujo físico producen **`flow_uid` distinto por diseño**. **No deben coincidir en identidad**; se relacionan por la arista `FLOW_IDENTITY` vía `community_id` (§3.2). Por tanto:

- La "fragmentación de un flujo legítimo en múltiples nodos" que v1 listaba como riesgo **no es un fallo: es el modelo intencionado.** Cada observación de cada sensor es una muestra de entrenamiento distinta y legítima (enriquece el corpus, no lo fragmenta).
- El skew de reloj entre sensores amenaza **únicamente el *match* de correlación** (la arista), **nunca la identidad** (el nodo). La defensa contra el skew vive en la tolerancia de correlación (§3.2.2), no en la identidad.

Esta lectura descarta la necesidad de un `session_counter` estatal en el motor (propuesta Gemini): resolvería un problema que el diseño no tiene, a costa de introducir estado en Redis **y de romper la reproducibilidad offline del corpus** (no se puede replayar un contador de Redis desde un pcap archivado — viola §0).

#### 3.1.4 `flow_start_window`: componente temporal (resolución Q6)

> *Resuelve Q6 con el consenso del Consejo + la lente del corpus.*

**Consenso unánime: CrisisWindow queda descartada** como componente de identidad (variable, dependiente de contenido → rompe el determinismo cross-sensor e invalida `flow_uid` históricos si cambia la config; viola la reproducibilidad de §0).

**Decisión v2 (familia (c) del Consejo, reforzada por §0):**

1. **`flow_start_window = floor(flow_start_epoch / N)`** — bucket fijo alineado a epoch, **determinista y computable localmente por cada sensor**, sin estado. Es **reproducible offline** desde el pcap (requisito §0).
2. **`flow_start_window` es timestamp de *inicio*, inmutable.** Los flujos de larga duración (SSH, VPN, C2 persistente) NO fragmentan su identidad: se extienden con aristas de duración (ADR-046 §3.2). El sensor emite un evento de "inicio de flujo" que fija el `flow_uid`, y eventos de "continuación" que lo referencian.
3. **Reúso instantáneo de puerto (UDP) dentro del mismo bucket** (objeción válida DeepSeek): añadir un contador monótono por `(node_id, community_id)` dentro del bucket:
   ```
   flow_uid = H( node_id ‖ community_id ‖ flow_start_window ‖ seq_in_window )
   ```
   `seq_in_window` se reinicia al cambiar de bucket. Elimina la colisión sin afinar la ventana. *(El `seq_in_window` es local al sensor y reproducible desde el orden de paquetes del pcap.)*
4. **`sensor_native_flow_id` como refuerzo cuando esté disponible** (propuesta Qwen): Suricata (`flow_id` uint64) y Zeek (`uid`) ya garantizan unicidad de instancia por sensor. Cuando el evento provenga de ellos, se incorpora como propiedad y puede sustituir a `(flow_start_window ‖ seq_in_window)` en el componente intra-nodo. Para el **sniffer propio de aRGus** (eBPF/XDP, paquetes crudos) no existe tal ID → se usa el mecanismo (1)–(3).
5. **Calibrar `N` sobre golden pcap** (consenso Claude/Grok/Mistral/DeepSeek): medir la distribución del intervalo de reúso de 5-tupla intra-nodo y fijar `N` por debajo del percentil 1. Default LAB de arranque: **60 s** (TIME-WAIT TCP típico ~60 s; corta la mayoría de reciclajes legítimos), revisable con evidencia.

**El gate NTP/chrony (DEBT-ARGUSPP-NTP-001, cerrada DAY 167) es load-bearing:** la ventana viable solo existe si `skew ≪ N ≪ intervalo_reúso`. Buen NTP la ensancha.

### 3.2 Correlación host↔red: doble arista (P1)

Sobre el grafo temporal de ADR-046 v4 §3.2, se formaliza la correlación host↔red con **dos aristas de naturaleza distinta** (refinan las aristas `FLOW_IDENTITY`/`HOST_LOCALITY`/`TEMPORAL_BRIDGE` de ADR-046 para el caso host↔red):

- **Arista flujo↔flujo** — por `community_id`. Determinista. Equivalencia exacta de flujo entre sensores de red (es la `FLOW_IDENTITY` de ADR-046).
- **Arista host↔flujo** — por `host_id`/`agent_id` **canónico** (nunca IP cruda) + **coincidencia temporal asimétrica** (§3.2.2). El evento de host se une al endpoint interno/gestionado del flujo (la víctima), no al atacante (join asimétrico de ADR-046 §3.2).

**Valor para el corpus (§0):** un flujo de red anclado además a un evento de host de Wazuh es una **muestra de entrenamiento estrictamente más rica** que un flujo visto solo por la red. P1 es literalmente lo que pone el *enriquecido* en "dataset enriquecido".

**NAT — menú de mecanismos con anotación obligatoria.** Cuando la IP interna que ve Wazuh ≠ la IP observada por el sensor de red (NAT, contenedores), el puente se resuelve por un menú en orden de confianza:
1. Translation node con logs NAT (mayor confianza).
2. Identidad `agent_id`/hostname canónico (`hostname` + `domain`, o UUID Wazuh — nunca hostname desnudo, que colisiona).
3. Puente por (proceso, puerto_local, timestamp).
4. Fallback temporal degradado (menor confianza).

**Invariante:** SIEMPRE se anota en grafo y log el método usado y su confianza. **Nunca fallo silencioso por IP no coincidente.** (Conecta con BACKLOG-RESEARCH-NAT-HOSTNET-001 y DEBT-ARGUSPP-WAZUH-001.)

#### 3.2.1 Resolución de conflictos entre mecanismos NAT (nuevo, Kimi)

Si dos mecanismos del menú producen respuestas **inconsistentes** (translation-node dice IP interna 10.0.0.5, puente proc+puerto apunta a 10.0.0.6): **consenso por mayoría ponderada por confianza**. Si los mecanismos de mayor confianza (1, 2) discrepan, el flujo se marca `CONFLICT_NAT` y se eleva a análisis humano/ML. **No hay fallback silencioso al mecanismo 4.** *(Para el corpus, un puente NAT en conflicto es una muestra etiquetada de baja confianza, no una muestra a descartar.)*

#### 3.2.2 Coincidencia temporal asimétrica (terminología corregida, Qwen)

v1 decía "causal-bidireccional". Se corrige: la causalidad real (relojes de Lamport/vectoriales) es cara y frágil. Lo que se implementa es **coincidencia temporal asimétrica**: el host plane (Wazuh) tiene mucha más latencia de ingest que el data-plane. Ventanas asimétricas (defaults §4): **Red→Host ~5 s**, **Host→Red ~30 s** (configurable; los logs de host bufferean).

### 3.3 Modelo de amenaza: dos vectores opuestos

| Vector | Capa que toca | Efecto sobre community_id | Detectable por | MITRE |
|---|---|---|---|---|
| **A — MITM clásico** (ARP spoof, bettercap base) | L2 (MAC), IP/puerto INTACTOS | **CIEGO** — mismo flujo → mismo hash | Host/ARP plane (cambio MAC↔IP), NO la red | **T1557** |
| **B — Inyección/reescritura** (scapy, nfqueue, módulos bettercap) | L3/L4 (IP, puerto) | **CAMBIA** — atacante fabrica community_id a voluntad | flow_uid + node_id + ventana temporal | **T1565 / T1090** |

El community_id es **ciego al vector A** (la MAC no entra en el hash) y **totalmente manipulable en el vector B** (función pura de la 5-tupla). La defensa de cada vector es distinta y ninguna vive en el hash.

**Ampliación de alcance del vector A (Qwen):** el MITM no es solo L2. Rogue gateway, DNS poisoning o BGP hijack hacen MITM sin cambiar la MAC. La señal del host plane debe incluir, además de ARP/NDP: **anomalías de estado TCP** (RST inesperados, saltos de seqnum = inyección en conexión) y **mismatches TLS** (certificado distinto al esperado), vía Wazuh/osquery.

### 3.4 Las tres líneas de defensa (arquitectónicas, NO del hash)

1. **`flow_uid` ancla a nodo + ventana** — anti-inyección (vector B). Un flujo sin emisión del sensor de borde correspondiente = anomalía. **Requiere el mapa de cobertura (§3.8) para saber qué sensor "debería" haber visto el flujo.**
2. **Correlación host↔red** — único detector del MITM sigiloso (vector A). La detección vive **en el cruce**, no en ninguna capa sola. Implica vigilancia ARP/NDP en el host plane (§3.9).
3. **community_id como dato no confiable del data-plane** — un sensor que emite community_id que ningún otro corrobora puede ser sensor comprometido O tráfico inyectado. Entra en `orphan_rate` (§3.6, ADR-051), **interpretado contra la cobertura esperada (§3.8), nunca en absoluto.**

#### 3.4.1 Límite fundamental de la detección del vector A (nuevo, Kimi)

ARP/NDP detecta el vector A **solo bajo el supuesto de host sano**. Si el atacante tiene root en el endpoint, la señal ARP que reporta Wazuh *también* miente. Para host comprometido se requiere una **tercera fuente out-of-band** (switch con port-security, sensor en modo promiscuo que vea las solicitudes ARP). **Sin fuente externa, el vector A con host comprometido es indetectable por diseño** — límite de la observabilidad, documentado honestamente (coherente con §0 y con "escudo, nunca espada": no prometemos lo que no podemos detectar).

### 3.5 El community_id NO es un control de seguridad — y nunca lo será

`community_id = "1:" + base64(sha1(seed ‖ saddr ‖ daddr ‖ proto ‖ 0x00 ‖ sport ‖ dport))` es función **pura y honesta** de la 5-tupla, diseñada para que sensores honestos coincidan. Vector A: hashea fielmente IPs/puertos intactos → mismo ID. Vector B: hashea fielmente la 5-tupla falsa → ID nuevo "válido" controlado por el atacante. La integridad del hash no implica integridad del contenido. La defensa es **arquitectónica, no criptográfica-de-flujo.**

### 3.6 Marca de confianza: *features* del corpus, no veredicto opaco (resolución Q3)

> *Resuelto a la luz de §0: la confianza no es un filtro de queries, son las **features de entrenamiento** y los **pesos de muestra (IPW, ADR-040)** del modelo ensemble.*

**Decisión v2: guardar señales primitivas, derivar el tier como vista computada.** NO un `float` opaco congelado al ingestar (advertencia de ChatGPT y Claude: envejece mal, y el modelo necesita las señales crudas, no un veredicto pre-cocinado que no puede recomputar).

Propiedades primitivas obligatorias en el nodo-flujo:
- `witness_count` / `corroboration_count` — nº de sensores independientes que corroboran el `community_id`.
- `is_host_plane_anchored` (bool) — si tiene arista host↔flujo.
- `nat_resolution_method` (enum: `LOG` / `AGENT_ID` / `PROC_PORT` / `TEMPORAL_FALLBACK` / `CONFLICT_NAT`) + `nat_confidence`.
- enlace a `orphan_rate` del sensor (ADR-051).

`trust_tier` (`CORROBORATED` / `SINGLE_SENSOR` / `ORPHAN` / `CONFLICT_NAT`) se **deriva** de las primitivas como vista, recomputable cuando evolucione la semántica.

**Conexión IPW (ADR-040):** la corroboración de un flujo es su peso de propensión. Estas primitivas son directamente los pesos de muestra del entrenamiento walk-forward. **Por eso se guardan crudas: son ingredientes del modelo, no metadatos de UI.**

**Objeción crítica incorporada (Claude + DeepSeek):** "visto por 1 sensor" **NO** es sospechoso por sí mismo — es lo normal en cobertura no solapada. `SINGLE_SENSOR` solo significa algo *relativo a la cobertura esperada* (§3.8). Sin el mapa de cobertura, `orphan_rate` queda dominado por flujos benignos de cobertura única y es ruido como señal de compromiso —**y como peso IPW**.

### 3.7 Etiquetado de procedencia: la integridad de la etiqueta ES el producto (resolución Q4)

> *Elevado a eje central por §0: si el grafo alimenta el corpus, la integridad de la etiqueta es el producto. Etiquetar, nunca borrar (consenso unánime).*

**Dos campos ortogonales que NUNCA se colapsan (Claude):**

- **`provenance_suspected`** — sospecha de *runtime*, heurística: `community_id` huérfano relativo a la cobertura esperada, `node_id` sin sensor de borde trazable, re-binding ARP correlado. Acompañada de la evidencia que la disparó.
- **`provenance_ground_truth`** — verdad de *escenario*, tomada del **manifiesto del ejercicio MITRE** (ADR-050), NO del detector. En un ejercicio sabes que lanzaste bettercap.

**Por qué no se funden:** si los colapsas, validarías el detector contra su propia salida (circular) y la misión primaria —demostrar que el modelo es mejor— se vuelve irrealizable: medirías una ilusión. **El delta entre ambos campos ES la métrica honesta de precision/recall** del corpus. Nada se borra; todo se retiene con su procedencia.

**Eje separado del enum congelado (Claude):** `provenance` es un eje distinto de la taxonomía de presencia DROP/CONFIG/POLICY/BUG/UNKNOWN de `acceptance_criteria.md` (que responde "por qué observado ≠ esperado en corrida benigna"). NO se mete `INJECTED` dentro de ese enum congelado (error de categoría + obliga a descongelar el artefacto). Se añade el eje `provenance` aparte.

**Procedencia trazable y no repudiable del etiquetado (Kimi):** el tag no es una propiedad `injected=true`, sino una arista append-only:
```cypher
(:NetworkFlow)-[:TAGGED_AS {method: 'MITRE_GROUND_TRUTH',
                            source: 'ADR-050-SESSION-N',
                            timestamp: t,
                            analyst: 'auto'}]->(:Tag {label: 'INJECTED'})
```
Append-only para que un motor comprometido no pueda des-etiquetar. **Auditabilidad del corpus** = condición de su validez científica.

**Uso dual:** en producción/correlación-online, las queries filtran por defecto (`WHERE NOT n:SuspiciousFlow`). En construcción de corpus y threat-hunt MITRE, se incluyen explícitamente. El mismo grafo sirve ambos fines; la retención (§0) hace posible el segundo.

### 3.8 Mapa de cobertura/visibilidad de sensores (nuevo, prerrequisito — Claude + DeepSeek)

> *Promovido por §0 de "DEBT cómoda" a **prerrequisito de la honestidad estadística del corpus**.*

Un modelo explícito de **qué sensor puede observar qué segmento** (VLAN, subred, interfaz) — grafo de topología o tabla de adyacencia sensor↔segmento, como entrada de primera clase del correlation-engine. Sin él:

- `orphan_rate` y `SINGLE_SENSOR` (§3.6) son ruido: no se distingue "cobertura única por diseño" (muestra válida) de "posible inyección".
- La defensa anti-inyección de §3.4 línea 1 ("flujo sin sensor de borde trazable = anomalía") no tiene contra qué validarse.
- Los **pesos IPW (ADR-040) son basura** y el **covariate shift** documentado en el paper vuelve a morder el corpus.

El correlation-engine consulta este modelo para validar que `(node_id, community_id)` tiene sentido topológico.

### 3.9 Señal ARP/NDP: nodo de estado de primera clase (resolución Q2)

**Consenso unánime: primera clase**, no enriquecimiento. Como enriquecimiento embebido en `:NetworkFlow` se pierde la consulta temporal y la capacidad de observar ARP sin flujo asociado.

**Modelado: estado de binding, no volcado de paquetes** (consenso fuerte; coherente con Q1 — un nodo por paquete ARP inundaría el grafo). Nodo `:IpMacBinding` (estado actual del binding IP↔MAC) con propiedades temporales `valid_from`/`valid_to` y `previous_mac`; el **re-binding (cambio de MAC para una IP) es la señal** del vector A. Encaja con el inventario de endpoints (ADR-046 §3.9).

`DEBT-ARGUSPP-ARP-MONITOR-001` debe emitir **eventos de cambio de estado**, no logs crudos de ARP. Sujeto al límite fundamental de §3.4.1.

---

## 4. Parámetros configurables (defaults de arranque)

> Punto de partida; se ajustarán con evidencia sobre golden pcap. Coherentes con ADR-046 v4 §4.

| Parámetro | Default LAB | Nota |
|---|---|---|
| `flow_start_window` (N) | **60 s** | Bucket epoch-aligned inmutable de inicio. Calibrar bajo percentil-1 del intervalo de reúso (§3.1.4). |
| `seq_in_window` | activo | Contador monótono por `(node_id, community_id)` intra-bucket; anti-colisión UDP. |
| `host_bridge_window` Red→Host | **5 s** | Coincidencia temporal asimétrica (§3.2.2). |
| `host_bridge_window` Host→Red | **30 s** | Logs de host con buffering/latencia. |
| `nat_confidence_floor` | a fijar | Confianza mínima para aceptar puente sin marcar baja-confianza. Conflicto → `CONFLICT_NAT` (§3.2.1). |
| `max_new_cid_per_window_per_node` | **adaptativo** | Baseline por nodo/rol (no fijo). Enforcement en correlation-engine (§3.10 / Q1). |
| `orphan_rate` umbral | relativo a cobertura | Interpretado contra el mapa de cobertura (§3.8), nunca absoluto. |

### 3.10 Rate-limit de cardinalidad (resolución Q1)

**Consenso: enforcement primario en el correlation-engine, antes de Neo4j.** Neo4j nunca es el rate-limiter primario (cuando el grafo te frena, el daño ya ocurrió); a lo sumo, backstop vía constraint. Métrica: **cardinalidad de `community_id` distintos por ventana por `node_id`** (Count-Min Sketch / HyperLogLog), umbral **adaptativo sobre baseline por nodo/rol**.

**Nunca se descarta evidencia (§0):** superar el cap NO borra el flujo —se marca (`rate_limited:true`) y/o colapsa en un meta-nodo de primera clase (`:GraphFloodingAnomaly` / `:HighCardinalityFlowCluster`). El flooding *es* el ataque: que salte el cap es una detección, **y una muestra de corpus**.

**Backpressure en el sensor (reconciliación del disenso Q1):** un autolímite grueso en el sensor protege el bus IPC y al motor —es **backpressure, no control de seguridad**. El control de seguridad real vive en el motor (un sensor comprometido no respeta su propio límite). Ambas posturas (Kimi/Claude sí; Mistral no) son compatibles bajo esta distinción.

---

## 5. Alternativas consideradas y rechazadas

| Alternativa | Por qué se rechazó |
|---|---|
| `community_id` como identidad de nodo | Reciclaje temporal funde flujos; multi-nodo colisiona 5-tuplas. Corrupción de estructura **y del corpus**. |
| `(node_id, community_id)` sin componente temporal | La 5-tupla se recicla en el tiempo en el MISMO nodo → mismo par para flujos distintos (objeción DeepSeek DAY 170). |
| `community_id` como control de integridad/seguridad | Función pura de la 5-tupla: ciego al vector A, manipulable en el B. *Garbage in, garbage hashed.* |
| Defensa anti-inyección en el hash (HMAC con secreto) | No resuelve el vector A (MAC fuera del hash) y rompe la paridad cross-sensor con Suricata/Zeek (SHA1 estándar). Debe ser arquitectónica. |
| `session_counter` estatal en el motor (Gemini, Q6) | Resuelve un problema que el diseño no tiene (§3.1.3); introduce estado en Redis y **rompe la reproducibilidad offline del corpus** (§0). |
| CrisisWindow como componente de identidad | Variable y dependiente de contenido → rompe determinismo cross-sensor e invalida `flow_uid` históricos. |
| IP cruda como clave del puente host↔red | Colapsa bajo NAT/DHCP/contenedores. Debe ser `agent_id`/hostname canónico. |
| Fallo silencioso cuando IP host ≠ IP red | Oculta el caso (NAT, MITM) que más importa observar. Se exige anotación de método + confianza. |
| Borrar flujos inyectados del dataset | Destruye la validez externa del corpus (§0). El atacante es ground truth. Se etiqueta, no se borra. |
| TLS Fingerprinting (JA3) en `flow_uid` (Mistral) | Añade complejidad, no resuelve vector A (MITM intercepta TLS), no todos los flujos son TLS. |

---

## 6. Preguntas abiertas para el Consejo (2ª pasada)

Las siete preguntas de v1 quedan resueltas en §3. Residuales para la segunda pasada:

1. **Ratificación de §3.1.3** (identidad ≠ correlación cross-nodo). ¿El Consejo confirma que dos sensores NO deben compartir `flow_uid` y que el skew solo amenaza el match? Esto cierra definitivamente Q6.
2. **Diseño del mapa de cobertura de sensores** (§3.8). ¿Grafo de topología, tabla de adyacencia, o derivado del inventario de endpoints de ADR-046 §3.9? Es prerrequisito de los pesos IPW.
3. **Calibración de `N`** (§3.1.4) y `nat_confidence_floor` (§4): metodología sobre golden pcap.
4. **Forma final del `trust_tier`** (§3.6): ¿el enum derivado es suficiente, o el entrenamiento (ADR-040) pide también un score continuo derivado para IPW?
5. **`provenance` y `acceptance_criteria.md`** (§3.7): confirmar que el eje `provenance` se añade SIN tocar el enum congelado de presencia.
6. **Fuente out-of-band para vector A con host comprometido** (§3.4.1): ¿se asume el límite y se documenta, o se abre DEBT para port-security en el switch del `ml_defender_gateway_lan`?
7. **Señal de host más allá de L2** (§3.3): ¿anomalías TCP/TLS entran en v2 o se difieren a ADR-053?

---

## 7. Consecuencias

**Positivas.** Identidad de nodo-flujo robusta y **reproducible offline** (corpus reconstruible desde pcap). Defensa MITM/inyección explícita y arquitectónica. La marca de confianza son features/pesos de entrenamiento, no metadatos muertos. El corpus retiene tráfico inyectado como ground truth con procedencia trazable y no repudiable. Suricata/Zeek/Wazuh quedan reconvertidos en maestros del modelo de aRGus. Desbloquea DEBT-NEO4J-FLOW-KEY-001.

**Negativas / coste.** `node_id` criptográfico y codificación canónica obligatorios (esquema más estricto). Mapa de cobertura de sensores como nueva infraestructura prerrequisito. Vigilancia ARP/NDP y señal TCP/TLS como nuevas fuentes. Rate-limit de cardinalidad y resolución de conflictos NAT como mecanismos nuevos. Calibración de `N` y ventanas.

**Riesgos.** (1) Sin vigilancia ARP/NDP, el vector A queda indetectable; sin fuente out-of-band, indetectable con host comprometido (§3.4.1). (2) `N` mal calibrado fragmenta o no corta el reciclaje. (3) Sin mapa de cobertura, `orphan_rate` y los pesos IPW son ruido — **riesgo directo sobre la misión primaria**. (4) Fallback NAT degradado sin umbral claro contamina la correlación.

---

## 8. Validación (EMECAS++)

Tests obligatorios sobre golden pcap (tier determinista, coherente con ADR-046 v4 §7):

- **Paridad de codificación `flow_uid`:** C++ (sensor) y Python (motor) producen `flow_uid` idéntico sobre el mismo vector (§3.1.1). *(Bloqueante; protege el corpus.)*
- **Unicidad de `flow_uid`:** misma 5-tupla en nodos distintos → `flow_uid` distinto (por diseño, §3.1.3); misma 5-tupla reciclada en el tiempo en el mismo nodo → `flow_uid` distinto. (Cierre de DEBT-NEO4J-FLOW-KEY-001.)
- **No-colisión UDP:** ráfaga UDP con reúso inmediato de puerto dentro del mismo bucket → `seq_in_window` evita colisión (§3.1.4).
- **Constraint Neo4j:** nodo-flujo sin `node_id` → rechazado (a DLQ).
- **Anti-inyección (vector B):** 5-tuplas fabricadas → ancladas al `node_id` que las vio; flujo sin sensor de borde trazable *según el mapa de cobertura* → marcado `provenance_suspected`.
- **MITM sigiloso (vector A):** ARP spoof (MAC cambia, IP/puerto intactos) → la red NO levanta señal (esperado, control negativo); el cruce host↔red SÍ detecta el re-binding MAC↔IP. Si la señal ARP no está, el test documenta la ceguera (§3.4.1).
- **NAT con anotación y conflicto:** flujo bajo NAT → puente resuelto por mecanismo del menú con método+confianza anotados; mecanismos en conflicto → `CONFLICT_NAT`, sin fallback silencioso (§3.2.1).
- **Etiquetado de procedencia:** flujo inyectado en escenario MITRE → `provenance_ground_truth` (del manifiesto) Y, si el detector lo pilla, `provenance_suspected`; el delta se mide. NO excluido del corpus (§3.7).
- **`orphan_rate` con sensor comprometido simulado:** sensor que emite `community_id` no corroborados → `orphan_rate` anómalo *relativo a su cobertura esperada* (§3.8), no en absoluto.
- **Escala:** 1M flujos → constraint y rate-limit adaptativo se sostienen.

---

## 9. Deudas y diferidos

- `DEBT-NEO4J-FLOW-KEY-001` — **ratificada.** `flow_uid` + codificación canónica + `node_id` criptográfico obligatorio + constraint Neo4j 5.x. P0 esquema.
- `DEBT-SENSOR-COVERAGE-MAP-001` (**NUEVA, P1**) — mapa de cobertura/visibilidad sensor↔segmento. Prerrequisito de `orphan_rate` e IPW (§3.8). *Sin ella, la misión primaria (corpus de calidad) está comprometida.*
- `DEBT-ARGUSPP-ARP-MONITOR-001` — vigilancia ARP/NDP como eventos de cambio de estado (§3.9). Prereq: Wazuh integrado. Sujeta al límite de §3.4.1.
- `DEBT-FLOWUID-CANONICAL-ENCODING-001` (**NUEVA, P0**) — especificación e implementación de la codificación canónica + test de paridad cross-implementación (§3.1.1).
- `DEBT-NODEID-CRYPTO-IDENTITY-001` (**NUEVA, P0**) — `node_id = SHA256(sensor_public_key)` ligado a ADR-027 e inventario ADR-046 §3.9 (§3.1.2).
- Rate-limit de cardinalidad (§3.10) — implementación post-Consejo.
- Fuente out-of-band para vector A con host comprometido (§3.4.1) — pendiente decisión (§6 Q6).
- Señal de host TCP/TLS más allá de L2 (§3.3) — pendiente v2/ADR-053 (§6 Q7).
- Relación con ADR-050: vector A (bettercap, T1557) y vector B (scapy/nfqueue, T1565/T1090) como escenarios separados; sus flujos se etiquetan `provenance_ground_truth`.
- (Opcional) Documentar `FlowObservation` vs `FlowIdentity` (GPT) — `flow_uid` identifica la *observación* de un flujo por un sensor; reservar `logical_flow_uid` futuro si se correlacionan múltiples observaciones del mismo flujo lógico a escala.

---

## 10. Referencias

- **§0 — misión primaria:** marco de tres paradigmas (CTU-13: Suricata F1=0.000, Zeek F1=0.042, aRGus F1=0.9985), bucle ACRL/Caldera, covariate shift (paper arXiv:2604.04952), ADR-040 (IPW/walk-forward/golden set).
- ADR-046 v4 (modelo dual de claves, grafo temporal, inventario de endpoints, cuota anti-pinning) — fuente de las decisiones que ADR-052 consume.
- ADR-051 (Seed Parity Gate & Correlation Health — `orphan_rate`).
- ADR-050 (sesión MITRE — ground truth del vector MITM, pendiente).
- ADR-027 (identidad criptográfica Ed25519/Noise del sensor).
- `corelight/community-id-spec` (Community ID v1); oráculo `pycommunityid`.
- Nota de amenaza DAY 171 (MITM e inyección en runtime).
- Consejo de Sabios DAY 170 (P1, P3) y DAY 173 (1ª pasada, 8/8).
- bettercap, scapy, nfqueue/libnetfilter_queue, eBPF/tc — adversarios contemplados (§2.2).