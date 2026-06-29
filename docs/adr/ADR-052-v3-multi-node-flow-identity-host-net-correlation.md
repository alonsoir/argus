# ADR-052 — Multi-node Flow Identity & Host↔Net Correlation

| Campo | Valor |
|---|---|
| **ADR** | 052 |
| **Versión** | **v3 (candidata a ratificación)** — incorpora la 2ª pasada del Consejo (DAY 173) y el arbitraje de Alonso |
| **Fecha** | DAY 173 (rev. v3) |
| **Estado** | CANDIDATA A RATIFICACIÓN — pendiente confirmación de fidelidad del Consejo (no se prevé 3ª deliberación completa) |
| **Decisión final** | Alonso |
| **Deliberación** | Consejo de Sabios (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen) — 1ª y 2ª pasada cerradas |
| **Recoge** | P3 (identidad de flujo multi-nodo) + P1 (correlación host↔red) del Consejo DAY 170 |
| **Depende de / relaciona** | ADR-046 v4 (modelo dual de claves, grafo temporal, inventario de endpoints), ADR-051 (`orphan_rate`), ADR-050 (sesión MITRE — ground truth), ADR-048 (etcd HA / Raft — soporte del WAL de etiquetado), ADR-040 (ML Retraining Contract — IPW/walk-forward/golden set), ADR-027 (identidad criptográfica del sensor) |
| **Ratifica** | DEBT-NEO4J-FLOW-KEY-001 (P0 esquema, constraint Neo4j 5.x antes de poblar el grafo) |

### Cambios v2 → v3

1. **§3.1.2 reescrito (N1):** `node_id` es identidad de corpus **estable y declarada**, desacoplada de la clave efímera del sensor. Corrige el conflicto con el ciclo `vagrant destroy+up` de EMECAS++.
2. **§3.1.4 (N2):** `seq_in_window` se computa en el sensor y se **transporta en el evento**; no se recomputa offline.
3. **§3.1.4 (N3, voto Kimi):** `sensor_native_flow_id` es **propiedad de trazabilidad, NUNCA componente del `flow_uid`**.
4. **§3.7 (N4):** el no-repudio del etiquetado vive en un **WAL externo append-only con hash-chain** (soportado por el plano etcd HA / ADR-048); Neo4j es **vista materializada**.
5. **§3.1.1 (N5, arbitraje):** la función de hash es **la que provea la versión congelada de libsodium del pipeline**, idéntica en todo el pipeline. Cero drift entre versiones de libsodium.
6. **§3.10 (N6):** cardinalidad **exacta** para la etiqueta `rate_limited`; estructuras probabilísticas (HLL) solo para observabilidad.
7. **§3.2.2 (N7):** ventanas host↔red en **event time** con watermark.
8. **§3.1.4 / pruebas (arbitraje 6):** `flow_start_window` calibrado **por protocolo** (TCP/UDP por separado) con tests dedicados.
9. **§3.11 NUEVA (arbitraje 7 — ANULACIÓN DE ÁRBITRO):** las señales de host TCP/TLS (vector A ampliado) **entran en ADR-052**, en contra de la mayoría 6/8 del Consejo que pedía diferirlas a ADR-053. Decisión explícita de Alonso, con alcance delimitado.
10. **§3.8 (Q2):** modelo de datos del mapa de cobertura: tabla/cache declarada, versionada, fuente = orquestador, validación por beacons.
11. **§3.6 (Q4):** `trust_tier` enum en el grafo + score IPW continuo en el pipeline ML (no en Neo4j), normalizado por `expected_witnesses`.
12. **§0.1 NUEVA (N10):** métricas de calidad del corpus. **§3.2 (N11):** definición de `agent_id`. **§7 (N12):** almacenamiento por niveles. **§9 (N9):** deuda `FlowObservation` vs `FlowIdentity`.
13. Q1 (§3.1.3) y Q5 (provenance ortogonal) **ratificadas en el cuerpo**.

---

## 0. Misión primaria (principio ordenador)

> **El grafo no es el producto. El producto es el corpus.**

aRGus existe para producir, validar y firmar **modelos ensemble en formato plugin** que hayan demostrado —con honestidad científica— ser mejores que sus predecesores. El grafo de correlación que define este ADR es **el aparato que fabrica el corpus de entrenamiento enriquecido** del que salen esos modelos. La correlación en vivo es un beneficio secundario; la razón de ser del grafo es el dataset.

**Invariante de proyecto (permanente):**
> *El grafo de aRGus es, antes que nada, un corpus de entrenamiento que además hace correlación en vivo. Cuando ambos fines chocan, ganan la **retención** y la **integridad de la etiqueta**. No se borra evidencia; se etiqueta con procedencia. El atacante es ground truth, no ruido a limpiar.*

Esto se alinea con dos decisiones ya tomadas y las explica retroactivamente:

1. **El marco de los tres paradigmas** (CTU-13 Neris: Suricata F1=0.000, Zeek F1=0.042, aRGus F1=0.9985). Suricata, Zeek y Wazuh **no pueden ser activadores primarios** contra el firewall —ni por capacidad de detección demostrada, ni por soberanía digital (ENS/NIS2/GDPR). Esa acción se delega en aRGus. El grafo los reconvierte: dejan de ser **gatillos** y pasan a ser **testigos, oráculos de etiquetado y corroboradores** —**maestros del modelo de aRGus.** Ése es el sentido último del `community_id` como clave de correlación cross-tool.
2. **El bucle adversarial (ACRL/Caldera) y el sesgo de los datasets académicos** (covariate shift, documentado en el paper). Un corpus production-grade necesita capturar al atacante real y retenerlo etiquetado.

**El ciclo de vida del corpus y la disciplina de desarrollo son mundos distintos.** El `vagrant destroy+up` de EMECAS++ es un **instrumento de calidad de la fase de construcción**, no una operación de producción. En producción, **Neo4j NO se destruye jamás**: contiene la inmunidad aprendida, que es **secreto industrial adquirido**; su pérdida sería catastrófica. Por tanto producción exige mantenimiento y **copias de seguridad que garanticen que esa información global nunca se pueda perder**. Esta distinción tiene una consecuencia directa de diseño (§3.1.2): la identidad de corpus debe **sobrevivir a los ciclos `destroy+up` de EMECAS++ durante el desarrollo** —un corpus capturado hoy debe seguir siendo reproducible y enlazable tras un rebuild de mañana—, lo que prohíbe anclar la identidad de flujo a cualquier estado efímero que el ciclo de desarrollo regenere (como el keypair del sensor).

**Consecuencia de diseño que recorre todo el ADR.** Cada decisión de esquema se juzga contra: *¿mejora la calidad, la trazabilidad o la reproducibilidad del corpus?* En particular: la integridad de la etiqueta (§3.7) es el producto; la marca de confianza (§3.6) son features/pesos IPW (ADR-040); el mapa de cobertura (§3.8) es prerrequisito de la honestidad estadística; la identidad de flujo (§3.1) debe ser **reproducible offline** desde el pcap archivado.

### 0.1 Métricas de calidad del corpus (N10)

Para que §0 sea medible y no una intención, el corpus se evalúa con KPIs (objetivos LAB de arranque, revisables):

| KPI | Objetivo inicial | Por qué |
|---|---|---|
| % flujos con `provenance_ground_truth` validado contra manifiesto MITRE | > 90 % en escenarios MITRE | Honestidad de la etiqueta. |
| % flujos con `witness_count ≥ 2` (en segmentos de cobertura solapada) | > 70 % donde la cobertura lo permite | Corroboración cross-sensor; medido **relativo a la cobertura esperada** (§3.8), nunca absoluto. |
| Tiempo de reconstrucción de un `flow_uid` desde pcap archivado | < 1 s | Reproducibilidad offline. |
| Cobertura de técnicas MITRE ATT&CK representadas | crecer por sesión (ADR-050) | Validez externa del modelo. |
| Balance de clases benigno/malicioso | documentado por dataset | Evitar sesgo de entrenamiento. |

---

## 1. Estado

CANDIDATA A RATIFICACIÓN. Formaliza dos decisiones de ADR-046 v4, subordinadas a §0: la identidad de nodo-flujo (`flow_uid`, P3) y la defensa arquitectónica contra un data-plane hostil (modelo de amenaza DAY 171), incluida la correlación host↔red (P1).

> **Delimitación con ADR-046 v4 (anti-duplicación).** ADR-052 NO redefine el modelo dual de claves (§3.1 de ADR-046), el grafo temporal con aristas tipadas (§3.2), el inventario de endpoints (§3.9) ni la cuota anti-pinning fail-closed (§3.5). ADR-052 *consume* esas decisiones y añade: (a) la identidad de nodo `flow_uid`, (b) el modelo de amenaza, (c) la lente del corpus (§0). Donde haya solape, ADR-046 v4 es la fuente.

---

## 2. Contexto

### 2.1 El community_id no es identidad de nodo

`community_id` es clave de **correlación**: sensores honestos que ven el mismo paquete coinciden (validado DAY 171, diana `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`). Como identidad de nodo es insuficiente por reciclaje temporal de 5-tupla (dos flujos legítimos no relacionados producen el mismo `community_id`; como identidad se fundirían → corrupción de estructura **y del corpus**) y por el mundo multi-nodo (NAT/rangos solapados → misma 5-tupla en sensores distintos). Conclusión: `community_id` es **propiedad indexada**, nunca identidad.

### 2.2 El data-plane es hostil, no solo ruidoso

ADR-046 v4 modela latencia/reorden/pérdida. ADR-052 añade **adversario activo con capacidad de modificar paquetes en runtime** (bettercap, scapy, nfqueue, eBPF/tc). Todo lo observado puede ser una mentira fabricada; el `community_id` —función pura de la 5-tupla— hereda esa hostilidad (*garbage in, garbage hashed*). Para el corpus, la procedencia de cada muestra debe ser trazable.

### 2.3 Por qué hay que decidir esto ANTES de poblar Neo4j

El esquema de identidad (constraint, propiedades obligatorias, codificación del hash) es doloroso de retrofitear con datos en producción y gratis con el grafo vacío. Un corpus construido sobre un esquema defectuoso está envenenado desde el origen. ADR-052 ratifica el esquema para desbloquear DEBT-NEO4J-FLOW-KEY-001.

---

## 3. Decisión

### 3.1 Identidad de nodo-flujo: `flow_uid` (P3)

```
flow_uid = H( node_id ‖ community_id ‖ flow_start_window [‖ seq_in_window] )
```

- **`community_id`** — propiedad indexada (correlación + verificable). NUNCA identidad.
- **`node_id`** — identidad de corpus estable del sensor (§3.1.2). Obligatorio.
- **`flow_start_window`** — componente temporal de **inicio inmutable** (§3.1.4).
- **`seq_in_window`** — contador anti-colisión UDP, transportado en el evento (§3.1.4).

**Propiedades obligatorias en el grafo:** `node_id` en `:NetworkFlow`, `:Alert`, `:TelemetryEvent`. Constraint compuesto nativo Neo4j 5.x sobre la identidad de nodo-flujo.

**Triple justificación del `flow_uid`:** (1) unicidad de nodo en mundo multi-nodo con reciclaje temporal; (2) defensa anti-inyección (un flujo sin sensor de borde trazable = anomalía); (3) integridad del corpus: una muestra por instancia de flujo real, **reproducible offline** desde el pcap archivado.

#### 3.1.1 Codificación canónica y función de hash (P0 — bloqueante de esquema)

> *Resuelve el hueco detectado por el Consejo (Kimi) y el arbitraje de Alonso sobre la función de hash (N5).*

```
flow_uid = base64( H(
    utf8(node_id)            ‖ 0x00 ‖
    utf8(community_id)       ‖ 0x00 ‖
    uint64_be(flow_start_window)
    [‖ 0x00 ‖ uint32_be(seq_in_window)]
) )
```

**Función de hash `H` — invariante de proyecto (N5):**
> La función de hash es **la que provea la versión congelada de libsodium del pipeline**, y debe ser **idéntica en todo el pipeline** (sensor C++ y correlation-engine Python). **No se permite drift entre versiones de libsodium.** No se introduce ninguna dependencia de hash fuera de esa libsodium.

En la versión actual del proyecto (libsodium 1.0.19) esto es **BLAKE2b vía `crypto_generichash`** (nativo, rápido, sin dependencia nueva). El invariante se enuncia anclado a "lo que da *esta* libsodium" y no a un algoritmo por nombre, para que sobreviva a un futuro cambio de versión —siempre que el cambio sea simultáneo en todo el pipeline. *(Nota: SHA3-256 se descartó porque no lo provee la libsodium congelada; y el argumento de length-extension no aplica, ya que el `flow_uid` no es un control de seguridad — §3.5.)*

- **Delimitador `0x00`** entre campos: evita *prefix collision*.
- **`base64`** para `STRING` Neo4j sin caracteres de control.
- **Test de paridad cross-implementación obligatorio** (EMECAS++): C++ y Python producen `flow_uid` idéntico sobre el mismo vector **Y enlazan la misma versión de libsodium** (el test verifica ambas cosas). Mismo patrón que la paridad `pycommunityid`.

#### 3.1.2 `node_id`: identidad de corpus estable (P0 — reescrito en v3, N1)

> *Corrige el conflicto detectado: `node_id = SHA256(public_key)` se rompía contra la regla permanente "el keypair se regenera en cada `vagrant destroy+up`" → los `flow_uid` cambiarían en cada rebuild de EMECAS++ → un corpus capturado durante el desarrollo dejaría de ser reproducible y enlazable (viola §0).*

Se separan **dos identidades del sensor que v2 conflató**:

- **Identidad de corpus (`node_id`) — estable, declarada, persistente.** Es un identificador del sensor **declarado en el manifiesto del orquestador** (Vagrant/Ansible) y registrado en el **inventario de endpoints** (ADR-046 §3.9). Sobrevive a los ciclos `destroy+up` de EMECAS++ y a la vida en producción. No se deriva de ningún estado efímero.
  ```
  node_id = base64( H( utf8(declared_sensor_id) ‖ 0x00 ‖ uint64_be(deployment_epoch) ) )
  ```
  donde `declared_sensor_id` es un nombre estable (p. ej. `argus-sensor-gw-lan-01`) y `deployment_epoch` es un entero **declarado y persistido** que solo cambia cuando *deliberadamente* se quiere marcar una nueva generación de despliegue (nunca por un rebuild de desarrollo). `H` es la misma función de §3.1.1.

- **Identidad de autenticación (keypair del sensor) — puede rotar.** La clave del sensor (Ed25519/Noise, ADR-027) **firma los eventos de flujo** para autenticidad de origen, y puede regenerarse en cada `destroy+up` sin afectar al `node_id` ni al `flow_uid`. La firma es una propiedad del evento, no un componente de la identidad de corpus.

**Aclaración de alcance (Kimi):** `flow_uid` es prueba de **autenticidad de origen**, NO de **honestidad de contenido**. Un sensor comprometido con `node_id` válido puede emitir `community_id` fabricados; eso lo detecta `orphan_rate` (§3.6, ADR-051) *a posteriori*, interpretado contra la cobertura esperada (§3.8). Suficiencia = tríada: (1) `flow_uid` bien formado, (2) `node_id` en inventario con evento firmado por clave válida, (3) `community_id` corroborado o dentro del `orphan_rate` tolerable.

#### 3.1.3 `node_id` distingue por diseño: identidad ≠ correlación cross-nodo (RATIFICADO 8/8)

Como `node_id` está **dentro del hash**, dos sensores que observan el mismo flujo físico producen **`flow_uid` distinto por diseño**. **No deben coincidir en identidad**; se relacionan por la arista `FLOW_IDENTITY` vía `community_id` (§3.2). Por tanto:

- La "fragmentación de un flujo legítimo en múltiples nodos" **no es un fallo: es el modelo intencionado.** Cada observación de cada sensor es una muestra de entrenamiento distinta y legítima (enriquece el corpus).
- El skew de reloj amenaza **únicamente el *match* de correlación** (la arista), **nunca la identidad** (el nodo). La defensa contra el skew vive en la tolerancia de correlación (§3.2.2).

Esto descarta el `session_counter` estatal (resolvería un problema que el diseño no tiene, a costa de introducir estado y romper la reproducibilidad offline). **Ratificado por unanimidad en la 2ª pasada.** Test EMECAS++: dos sensores ven el mismo flujo → `flow_uid` distintos + arista `FLOW_IDENTITY` correcta.

#### 3.1.4 `flow_start_window` y `seq_in_window` (resolución Q6 + N2 + N3 + arbitraje 6)

**CrisisWindow queda descartada** como componente de identidad (variable, dependiente de contenido → rompe determinismo cross-sensor y reproducibilidad).

1. **`flow_start_window = floor(flow_start_epoch / N)`** — bucket fijo alineado a epoch, **determinista, computable localmente, reproducible offline**.
2. **Timestamp de *inicio*, inmutable.** Los flujos de larga duración (SSH, VPN, C2) NO fragmentan su identidad: se extienden con aristas de duración (ADR-046 §3.2):
   ```cypher
   (:NetworkFlow {flow_uid:"abc", flow_start_window:T0})-[:CONTINUES]->(... referencia el mismo flow_uid ...)
   ```
3. **`seq_in_window` — transportado, no recomputado (N2).** Contador monótono por `(node_id, community_id)` dentro del bucket, que resuelve el reúso instantáneo de puerto UDP. **Se computa en el sensor en el orden de la primera observación del flujo y se transporta como campo del evento serializado (Protobuf).** NO se recomputa en el correlation-engine ni en la reconstrucción offline. Esto hace el `flow_uid` reproducible **dado el evento**, inmune a reordenado de NIC, drops de ring buffer o diferencias de tcpreplay. El sensor persiste el contador para recuperación tras crash (deuda de implementación).
4. **`sensor_native_flow_id` — propiedad de trazabilidad, NUNCA componente del hash (N3, voto Kimi).** El `flow_id` (uint64) de Suricata y el `uid` (string) de Zeek se guardan como **propiedad obligatoria** del nodo para trazabilidad y dedup interno de la herramienta, pero **el `flow_uid` mantiene su fórmula canónica tool-independiente**. Motivo: Suricata reinicia `flow_id` (colisión con históricos) y normalizar `uint64` con `string` en el hash es ambiguo. Así el esquema se unifica venga el flujo de Suricata, Zeek o del sniffer propio.
5. **Calibración por protocolo (arbitraje 6).** `N` se calibra **por protocolo separado** (TCP y UDP reciclan de forma distinta; un único `N` es un error) midiendo sobre golden pcap la distribución del intervalo de reúso de 5-tupla intra-nodo y fijando `N` bajo un percentil bajo. Se crean **tests dedicados** para hallar esos valores. Default LAB de arranque: **60 s** (TIME-WAIT TCP típico), explícitamente provisional hasta que los tests den el número por protocolo.

**El gate NTP/chrony (DEBT-ARGUSPP-NTP-001, cerrada DAY 167) es load-bearing:** la ventana viable solo existe si `skew ≪ N ≪ intervalo_reúso`.

### 3.2 Correlación host↔red: doble arista (P1)

Dos aristas de naturaleza distinta sobre el grafo temporal de ADR-046 §3.2:

- **Arista flujo↔flujo** — por `community_id`. Determinista (`FLOW_IDENTITY` de ADR-046).
- **Arista host↔flujo** — por `agent_id` **canónico** (§3.2.3, nunca IP cruda) + **coincidencia temporal asimétrica** (§3.2.2). El evento de host se une al endpoint interno/gestionado (la víctima), no al atacante (join asimétrico).

**Valor para el corpus (§0):** un flujo anclado a un evento de host (Wazuh) es una **muestra estrictamente más rica**. P1 es lo que pone el *enriquecido* en "dataset enriquecido".

**NAT — menú de mecanismos con anotación obligatoria**, en orden de confianza: (1) translation node con logs NAT; (2) `agent_id`/hostname canónico; (3) (proceso, puerto_local, timestamp); (4) fallback temporal degradado. **Invariante:** SIEMPRE se anota método + confianza en grafo y log. **Nunca fallo silencioso.**

#### 3.2.1 Resolución de conflictos NAT (Kimi) + peso IPW (N8, Gemini)

Si dos mecanismos producen respuestas inconsistentes: **consenso por mayoría ponderada por confianza**. Si los de mayor confianza (1, 2) discrepan → `CONFLICT_NAT`, elevado a análisis humano/ML, **sin fallback silencioso al mecanismo 4**. Para el corpus, un `CONFLICT_NAT` recibe **peso IPW nulo o penalizado** (ADR-040) para no meter ruido en las fronteras de decisión del modelo.

#### 3.2.2 Coincidencia temporal asimétrica en event time (terminología corregida + N7)

No es "causal-bidireccional" (la causalidad real —Lamport/vectoriales— es cara y frágil). Es **coincidencia temporal asimétrica** sobre **event time** (timestamps de los eventos originales), NO processing time: Wazuh puede bufferizar logs minutos. El correlation-engine mantiene una **ventana de retención con watermark** (estándar en stream processing) esperando eventos de host atrasados. Las ventanas asimétricas (defaults §4) —Red→Host ~5 s, Host→Red ~30 s— son **tolerancia de skew de reloj**, no latencia de ingest.

#### 3.2.3 Definición de `agent_id` (N11, Mistral)

`agent_id` canónico, estable bajo DHCP/contenedores:
```
agent_id = base64( H( utf8(hostname) ‖ 0x00 ‖ utf8(domain) ‖ 0x00 ‖ utf8(os_uuid) ) )
```
con `os_uuid` = `/etc/machine-id` en Linux. Bajo DHCP, la clave del puente host↔flujo es `agent_id` (+ MAC si aplica), nunca la IP cruda.

### 3.3 Modelo de amenaza: dos vectores opuestos

| Vector | Capa | Efecto sobre community_id | Detectable por | MITRE |
|---|---|---|---|---|
| **A — MITM** (ARP spoof L2; **y rogue gateway/DNS/BGP en L3; hijack en L4; mismatch en L7**) | L2 (MAC) / **L3-L7** | **CIEGO** en L2 (mismo flujo → mismo hash) | Host plane: ARP/NDP (L2) **+ anomalías TCP/TLS (L3-L7), §3.11** | **T1557** |
| **B — Inyección/reescritura** (scapy, nfqueue, eBPF/tc) | L3/L4 | **CAMBIA** — atacante fabrica community_id | flow_uid + node_id + ventana temporal | **T1565 / T1090** |

El community_id es **ciego al vector A** y **manipulable en el vector B**. Ninguna defensa vive en el hash. **El vector A no es solo L2:** rogue gateway, DNS poisoning o BGP hijack hacen MITM sin tocar la MAC → la señal de host debe ir más allá de ARP/NDP (§3.11).

### 3.4 Las tres líneas de defensa (arquitectónicas, NO del hash)

1. **`flow_uid` ancla a nodo + ventana** — anti-inyección (vector B). Requiere el mapa de cobertura (§3.8).
2. **Correlación host↔red** — único detector del MITM sigiloso (vector A): ARP/NDP en L2 (§3.9) **+ anomalías TCP/TLS en L3-L7 (§3.11)**. La detección vive **en el cruce**.
3. **community_id como dato no confiable** — entra en `orphan_rate` (§3.6, ADR-051), interpretado contra la cobertura esperada (§3.8), nunca en absoluto.

#### 3.4.1 Límite fundamental de la detección del vector A (Kimi, generalizado por ChatGPT)

El host plane detecta el vector A **solo bajo el supuesto de host sano**. Si el atacante tiene root en el endpoint, **toda la telemetría de host miente** —no solo ARP/NDP, también osquery, Wazuh, eBPF local y la tabla ARP—; el host plane pierde su independencia observacional por completo. Para host comprometido se requiere una **fuente out-of-band** (switch con port-security/DHCP snooping/Dynamic ARP Inspection, SPAN/TAP, o Canary Host). **Sin fuente externa, el vector A con host comprometido es indetectable por diseño** — límite de la observabilidad, documentado honestamente ("escudo, nunca espada": no prometemos lo que no podemos detectar). La fuente out-of-band **no elimina** el problema, **reubica** la confianza al elemento menos comprometible (DEBT, §9).

### 3.5 El community_id NO es un control de seguridad — y nunca lo será

Función pura y honesta de la 5-tupla. Vector A: hashea fielmente IPs/puertos intactos → mismo ID. Vector B: hashea fielmente la 5-tupla falsa → ID nuevo controlado por el atacante. La integridad del hash ≠ integridad del contenido. La defensa es **arquitectónica, no criptográfica-de-flujo.** *(Esto es además por qué la elección de `H` en §3.1.1 es de higiene/disciplina de stack, no de seguridad.)*

### 3.6 Marca de confianza: features del corpus, no veredicto opaco (resolución Q3/Q4)

**Guardar señales primitivas, derivar el tier como vista.** NO un `float` opaco congelado al ingestar. Primitivas obligatorias en el nodo-flujo: `witness_count`/`corroboration_count`, `is_host_plane_anchored` (bool), `nat_resolution_method` (enum `LOG`/`AGENT_ID`/`PROC_PORT`/`TEMPORAL_FALLBACK`/`CONFLICT_NAT`) + `nat_confidence`, enlace a `orphan_rate` (ADR-051).

**Dos vistas derivadas, segregadas por capa (Q4):**
- **`trust_tier`** (enum `CORROBORATED`/`SINGLE_SENSOR`/`ORPHAN`/`CONFLICT_NAT`) — vista en el grafo para queries/UI/threat-hunt.
- **Score IPW continuo** — computado en el **pipeline de features ML (ADR-040), NO congelado en Neo4j**:
  ```
  score = min( 1.0, corroboration_count / expected_witnesses )
  ```
  con `expected_witnesses` del mapa de cobertura (§3.8). Si un segmento tiene 1 sensor, `expected_witnesses = 1` → `SINGLE_SENSOR` da score 1.0 (**no se penaliza la cobertura única por diseño**).

**El rol de `witness_count` en el IPW es el inverso del intuitivo:** `witness_count` alto = más confianza PERO más duplicación de la misma muestra física → el peso por muestra debe **bajar**, no subir, o el modelo sobre-aprende los segmentos bien cubiertos (covariate shift por la puerta de atrás). La normalización por `expected_witnesses` resuelve ambos extremos. **Esto ata §3.6 a §3.8: el score IPW no es computable sin el mapa de cobertura.**

**Objeción incorporada (Claude + DeepSeek):** "visto por 1 sensor" NO es sospechoso por sí mismo — es lo normal en cobertura no solapada. `SINGLE_SENSOR`/`orphan_rate` solo significan algo *relativo a la cobertura esperada* (§3.8).

### 3.7 Etiquetado de procedencia: la integridad de la etiqueta ES el producto (resolución Q4/Q5 + N4)

**Dos campos ortogonales que NUNCA se colapsan:**
- **`provenance_suspected`** — sospecha de runtime (heurística: `community_id` huérfano relativo a cobertura, `node_id` sin sensor de borde trazable, re-binding ARP correlado, anomalía TCP/TLS), con la evidencia que la disparó.
- **`provenance_ground_truth`** — verdad de escenario, del **manifiesto MITRE** (ADR-050), NO del detector.

Si se funden, se valida el detector contra su propia salida (circular) y la misión —demostrar que el modelo es mejor— se vuelve irrealizable. **El delta entre ambos campos ES la métrica honesta de precision/recall.**

**Eje separado del enum congelado (RATIFICADO 8/8, Q5):** `provenance` es eje distinto de DROP/CONFIG/POLICY/BUG/UNKNOWN de `acceptance_criteria.md`. NO se mete `INJECTED` en ese enum (error de categoría + descongelaría el artefacto).

**No-repudio del etiquetado: WAL externo con hash-chain (N4).** La garantía append-only **no puede vivir en Neo4j** (mutable; un motor comprometido borra aristas). El etiquetado se escribe primero en un **WAL externo append-only con hash-chain** —responsabilidad del **componente de log inmutable, soportado por el plano etcd HA (ADR-048, Raft nativo)** o un servicio dedicado que Alonso designe—; **Neo4j es vista materializada, no fuente de verdad del etiquetado.** El ADR define la *interfaz* (el etiquetado habla con el componente WAL), no el binding concreto. Test de integridad del corpus: el grafo contiene todas las entradas del WAL. En el grafo, el tag se refleja como arista append-only:
```cypher
(:NetworkFlow)-[:TAGGED_AS {method:'MITRE_GROUND_TRUTH', source:'ADR-050-SESSION-N',
                            timestamp:t, wal_offset:N, analyst:'auto'}]->(:Tag {label:'INJECTED'})
```

**Uso dual:** producción/online filtra por defecto (`WHERE NOT n:SuspiciousFlow`); construcción de corpus y threat-hunt MITRE incluyen explícitamente. La retención (§0) hace posible el segundo.

### 3.8 Mapa de cobertura/visibilidad de sensores (prerrequisito — resolución Q2)

Modelo explícito de **qué sensor puede observar qué segmento** (VLAN/subred/interfaz). Sin él, `orphan_rate`, `SINGLE_SENSOR` y el score IPW son ruido, y el covariate shift vuelve a morder.

**Modelo de datos (Q2 + N):**
- **Forma:** tabla/mapa de adyacencia declarativa `node_id → {segmentos}`, con **lookup rápido en el correlation-engine (cache Redis/etcd)**. **NUNCA `MATCH` en Neo4j por paquete** (colapsaría el throughput). Representación en grafo, si se desea, solo para visualización.
- **Declarado, no auto-descubierto:** bajo data-plane hostil, auto-descubrir la cobertura es circular (el atacante podría falsearla para esconder su inyección). **Fuente de verdad = orquestador (Vagrant/Ansible)**, derivada del inventario de endpoints (ADR-046 §3.9).
- **Versionado y timestampeado:** los pesos IPW dependen del mapa; si la cobertura cambia a mitad de captura sin versión, los pesos se computan contra topología equivocada. **El mapa es, él mismo, ground truth que se archiva junto al corpus.**
- **Validación runtime:** beacons/heartbeats verifican que la cobertura real coincide con la declarada (cable desconectado, NIC caída).

### 3.9 Señal ARP/NDP: nodo de estado de primera clase (resolución Q2 1ª pasada)

Primera clase, **estado de binding, no volcado de paquetes** (un nodo por paquete ARP inundaría el grafo — irónico dado §3.10). Nodo `:IpMacBinding` (estado actual IP↔MAC) con `valid_from`/`valid_to` y `previous_mac`; el **re-binding (cambio de MAC para una IP) es la señal** del vector A en L2. Encaja con el inventario de endpoints (ADR-046 §3.9). `DEBT-ARGUSPP-ARP-MONITOR-001` emite **eventos de cambio de estado**, no logs crudos. Sujeto al límite de §3.4.1.

### 3.10 Rate-limit de cardinalidad (resolución Q1 1ª pasada + N6)

**Enforcement primario en el correlation-engine, antes de Neo4j.** Neo4j nunca es el rate-limiter primario; a lo sumo backstop. Métrica: **cardinalidad de `community_id` distintos por ventana por `node_id`**, umbral **adaptativo sobre baseline por nodo/rol**.

**Cardinalidad exacta para la etiqueta (N6).** La decisión de marcar `rate_limited` —que entra al corpus— se computa con **cardinalidad exacta** en el motor (docenas de sensores, ventana pequeña → contador exacto en memoria factible y preferible). Las estructuras probabilísticas (HyperLogLog) tienen ~2 % de error y Count-Min Sketch estima frecuencia, no cardinalidad de elementos nuevos: **solo se usan para observabilidad/dashboards, jamás para la etiqueta del corpus.**

**Nunca se descarta evidencia (§0):** superar el cap marca (`rate_limited:true`) y/o colapsa en meta-nodo de primera clase (`:GraphFloodingAnomaly`/`:HighCardinalityFlowCluster` con muestra de `flow_uid`). El flooding *es* el ataque: que salte el cap es una detección y una muestra de corpus.

**Backpressure en el sensor:** autolímite grueso = **backpressure de IPC, no control de seguridad** (un sensor comprometido no respeta su propio límite). El control real vive en el motor.

### 3.11 Señales de host extendidas: anomalías TCP/TLS (vector A ampliado) — **DECISIÓN DE ÁRBITRO**

> **ANULACIÓN DE ÁRBITRO.** La mayoría del Consejo (6/8) recomendó **diferir** estas señales a ADR-053, manteniendo solo el gancho conceptual. Alonso **anula esa recomendación** y las incorpora a ADR-052. Justificación: el vector A **no es solo L2** (rogue gateway, DNS poisoning, BGP hijack, TCP hijack no tocan la MAC); dejar la señal TCP/TLS fuera dejaría la detección del **vector A ampliado sin ground truth en el mismo ADR que define el modelo de amenaza** (§3.3). El threat model y su detección deben viajar juntos. Se asume conscientemente el coste de mayor alcance de este ADR, con la sección delimitada para que no se desborde.

**Alcance delimitado (qué entra ahora):** señales de host de primera clase, recolectadas vía Wazuh/osquery, modeladas como nodo `:HostAnomaly` enlazado al `agent_id` y correlacionado con flujos en su ventana temporal (§3.2.2):

| Señal | Capa | Indica | Fuente |
|---|---|---|---|
| RST TCP inesperados | L4 | inyección/hijack en conexión | Wazuh/osquery, contador kernel |
| Saltos anómalos de `seq_num` | L4 | inyección en medio de conexión | host stack |
| Mismatch de certificado TLS (esperado ≠ presentado) | L7 | MITM con interceptación TLS / proxy | osquery + expectativa TLS declarada |

**Qué se reserva (NO entra en v3, va a ADR-053 o backlog):** fingerprinting JA3/JA4, análisis profundo de cadena TLS, detección de anomalías de ruta L3 (traceroute/BGP) — superficie de implementación que crecería el ADR sin necesidad para cerrar el esquema.

**Conexión con el corpus:** estas señales alimentan `provenance_suspected` (§3.7) y son features de host plane para el modelo. Sujetas al límite de §3.4.1 (host comprometido → también mienten).

---

## 4. Parámetros configurables (defaults de arranque)

| Parámetro | Default LAB | Nota |
|---|---|---|
| `flow_start_window` (N) | **60 s, por protocolo** | Provisional; calibrar TCP/UDP por separado (§3.1.4 pto 5). |
| `seq_in_window` | activo, transportado | §3.1.4 pto 3. |
| `host_bridge_window` Red→Host | **5 s** (tolerancia de skew, event time) | §3.2.2. |
| `host_bridge_window` Host→Red | **30 s** (tolerancia de skew, event time) | §3.2.2; ventana de retención/watermark mayor. |
| `nat_confidence_floor` | por mecanismo, calibrado | Contra escenarios NAT/MITRE etiquetados, no pcap benigno. Conflicto → `CONFLICT_NAT`. |
| `max_new_cid_per_window_per_node` | adaptativo, baseline por nodo/rol | Cardinalidad exacta (§3.10). |
| `orphan_rate` umbral | relativo a cobertura | §3.8, nunca absoluto. |

---

## 5. Alternativas consideradas y rechazadas

| Alternativa | Por qué se rechazó |
|---|---|
| `community_id` como identidad de nodo | Reciclaje y multi-nodo funden flujos → corrupción de estructura y corpus. |
| `(node_id, community_id)` sin componente temporal | La 5-tupla se recicla intra-nodo (objeción DeepSeek). |
| `community_id` como control de seguridad | Función pura: ciego al vector A, manipulable en el B. |
| HMAC con secreto en el hash | No resuelve vector A y rompe paridad cross-sensor con Suricata/Zeek (SHA1 estándar). |
| **`node_id = SHA256(public_key)`** (v2) | El keypair se regenera en cada `destroy+up` de EMECAS++ → `flow_uid` inestable → corpus no reproducible (§0). Reemplazado por identidad de corpus declarada (§3.1.2). |
| **SHA3-256** (v2) | No lo provee la libsodium congelada del pipeline → dependencia nueva y riesgo de drift entre versiones; length-extension no aplica (§3.5). Reemplazado por la función de la libsodium del proyecto (§3.1.1). |
| `session_counter` estatal en el motor (Gemini) | Resuelve un problema que el diseño no tiene (§3.1.3); introduce estado y rompe reproducibilidad offline. |
| `sensor_native_flow_id` como componente del hash | Suricata reinicia `flow_id`; normalización uint64/string ambigua (§3.1.4 pto 4, voto Kimi). |
| Append-only solo en Neo4j | Neo4j es mutable; el no-repudio exige WAL externo (§3.7). |
| HLL/CMS para la etiqueta `rate_limited` | Error ~2 % / estiman frecuencia, no cardinalidad; el corpus exige exactitud (§3.10). |
| CrisisWindow como componente de identidad | Variable y dependiente de contenido → rompe determinismo y reproducibilidad. |
| IP cruda como clave del puente host↔red | Colapsa bajo NAT/DHCP/contenedores; usar `agent_id` (§3.2.3). |
| Borrar flujos inyectados | Destruye la validez externa del corpus (§0). Se etiqueta. |
| **Diferir TCP/TLS a ADR-053** (mayoría Consejo) | Anulado por árbitro: el vector A ampliado debe tener detección en el mismo ADR que su threat model (§3.11). |

---

## 6. Estado de las preguntas del Consejo

**1ª pasada (Q1–Q7):** resueltas en §3 (v2). **2ª pasada:** Q1 (§3.1.3) y Q5 (§3.7) **ratificadas 8/8 e incorporadas al cuerpo**; Q2 (§3.8), Q3 (§3.1.4 pto 5 / §4), Q4 (§3.6) resueltas; Q6 (§3.4.1 + DEBT) documentada; Q7 **resuelta por arbitraje en contra de la mayoría** (§3.11).

**Para la confirmación de fidelidad (no deliberación nueva):** ¿refleja la v3 fielmente el consenso de la 2ª pasada y deja claras las dos anulaciones de árbitro (función de hash anclada a libsodium §3.1.1; TCP/TLS dentro del ADR §3.11)?

---

## 7. Consecuencias

**Positivas.** Identidad de nodo-flujo robusta, estable entre rebuilds de EMECAS++ y **reproducible offline**. Defensa MITM/inyección explícita y arquitectónica, ahora cubriendo el vector A ampliado (L2–L7) con su ground truth en el mismo ADR. Confianza como features/pesos IPW. Etiquetado con no-repudio real (WAL). Suricata/Zeek/Wazuh reconvertidos en maestros del modelo. Desbloquea DEBT-NEO4J-FLOW-KEY-001.

**Negativas / coste.** `node_id` declarado + época de despliegue como nueva disciplina de inventario. WAL externo de etiquetado como nuevo componente. Mapa de cobertura versionado como prerrequisito. Señales TCP/TLS amplían el alcance del ADR (asumido conscientemente, §3.11). Cardinalidad exacta y resolución de conflictos NAT como mecanismos nuevos. Calibración por protocolo.

**Riesgos.** (1) Sin host plane (ARP/NDP + TCP/TLS), el vector A queda indetectable; sin fuente out-of-band, indetectable con host comprometido (§3.4.1). (2) `N` mal calibrado. (3) Sin mapa de cobertura, `orphan_rate` y pesos IPW son ruido — riesgo directo sobre la misión. (4) Fallback NAT degradado sin umbral claro.

**Almacenamiento por niveles (N12).** La retención de §0 hace crecer el grafo; se resuelve con **storage por niveles** (grafo caliente + archivo frío en data lake/Parquet/grafo histórico), **NUNCA con borrado**. En producción, el grafo y su WAL son secreto industrial: copias de seguridad obligatorias, destrucción prohibida (§0).

---

## 8. Validación (EMECAS++)

Sobre golden pcap (tier determinista, ADR-046 §7):

- **Paridad de `flow_uid`:** C++ y Python producen `flow_uid` idéntico **y enlazan la misma versión de libsodium** (§3.1.1). *(Bloqueante.)*
- **Estabilidad del `node_id`:** `flow_uid` idéntico antes y después de un `vagrant destroy+up` (el keypair rota, el `node_id` declarado no) (§3.1.2). *(Test de cierre de N1.)*
- **Unicidad de `flow_uid`:** misma 5-tupla en nodos distintos → distinto (por diseño); reciclada en el tiempo en el mismo nodo → distinto.
- **No-colisión UDP:** ráfaga UDP con reúso inmediato de puerto → `seq_in_window` transportado evita colisión; reconstrucción offline desde el evento reproduce el `flow_uid` (§3.1.4).
- **Constraint Neo4j:** nodo-flujo sin `node_id` → rechazado (DLQ).
- **Anti-inyección (vector B):** 5-tuplas fabricadas → ancladas al `node_id` que las vio; flujo sin sensor de borde trazable *según el mapa de cobertura* → `provenance_suspected`.
- **MITM L2 (vector A):** ARP spoof → la red NO levanta señal (control negativo); el cruce host↔red detecta el re-binding (§3.9). Sin señal ARP, el test documenta la ceguera (§3.4.1).
- **MITM L3-L7 (vector A ampliado):** inyección TCP / mismatch TLS simulados → `:HostAnomaly` correlado dispara `provenance_suspected` (§3.11).
- **NAT con anotación y conflicto:** método+confianza anotados; conflicto → `CONFLICT_NAT` + peso IPW penalizado, sin fallback silencioso.
- **No-repudio del etiquetado:** entradas del WAL = aristas `:TAGGED_AS` en el grafo; borrar una arista en Neo4j → detectado por divergencia con el WAL (§3.7).
- **Etiquetado de procedencia:** flujo inyectado MITRE → `provenance_ground_truth` (manifiesto) Y, si el detector lo pilla, `provenance_suspected`; se mide el delta. No excluido.
- **`orphan_rate` con sensor comprometido simulado:** anómalo *relativo a su cobertura esperada* (§3.8).
- **Escala:** 1M flujos → constraint y rate-limit exacto se sostienen.

---

## 9. Deudas y diferidos

| DEBT | Prio | Estado |
|---|---|---|
| `DEBT-NEO4J-FLOW-KEY-001` | P0 | **Ratificada.** Se cierra al aplicar §3.1.1 + constraint + `node_id` obligatorio. |
| `DEBT-FLOWUID-CANONICAL-ENCODING-001` | P0 | Codificación + función de libsodium congelada + test de paridad (incl. misma versión libsodium) + caso dos-sensores. |
| `DEBT-NODEID-CRYPTO-IDENTITY-001` | P0 | **Reescrita (N1):** identidad de corpus declarada/persistente; clave efímera firma, no es el `node_id`. |
| `DEBT-SENSOR-COVERAGE-MAP-001` | P1 | Tabla/cache declarada, versionada; fuente = orquestador; validación = beacons (§3.8). |
| `DEBT-LABEL-WAL-001` (NUEVA) | P1 | WAL externo append-only con hash-chain (soporte etcd HA / ADR-048); Neo4j vista materializada (§3.7). |
| `DEBT-ARGUSPP-ARP-MONITOR-001` | P1 | Eventos de cambio de estado `:IpMacBinding` (§3.9). |
| `DEBT-ARGUSPP-HOST-TCP-TLS-001` (NUEVA) | P1 | Señales TCP/TLS de host → `:HostAnomaly` (§3.11). *(Dentro de ADR-052 por arbitraje.)* |
| `DEBT-SEQWINDOW-PERSIST-001` (NUEVA) | P2 | Persistencia/recuperación post-crash del contador `seq_in_window` en el sensor (§3.1.4). |
| `DEBT-ARGUSPP-OOB-MITM-001` (NUEVA) | P2/P3 | Fuente out-of-band (port-security/SPAN/Canary) en el switch FEDER (§3.4.1). |
| `DEBT-CORPUS-QUALITY-METRICS-001` (NUEVA) | P2 | KPIs de §0.1. |
| `DEBT-ARCH-FLOW-OBSERVATION-001` (NUEVA) | P3 | Documentar `FlowObservation` vs `FlowIdentity`: `flow_uid` identifica la *observación*, no el *flujo lógico*; evitar que se reutilice como identidad global de sesión (N9, GPT). |
| ADR-053 (diferido) | — | JA3/JA4, cadena TLS profunda, anomalía de ruta L3 (§3.11). |

---

## 10. Referencias

- §0 — misión primaria: tres paradigmas (CTU-13), ACRL/Caldera, covariate shift (paper arXiv:2604.04952), ADR-040 (IPW/walk-forward/golden set).
- ADR-046 v4 (modelo dual de claves, grafo temporal, inventario de endpoints, cuota anti-pinning).
- ADR-051 (`orphan_rate`). ADR-050 (sesión MITRE, ground truth). ADR-048 (etcd HA / Raft — soporte del WAL). ADR-027 (identidad criptográfica del sensor).
- `corelight/community-id-spec`; oráculo `pycommunityid`. libsodium 1.0.19 (función de hash del pipeline).
- Nota de amenaza DAY 171 (MITM e inyección en runtime). MITRE ATT&CK T1557, T1565, T1090.
- Consejo de Sabios DAY 170 (P1, P3), DAY 173 (1ª y 2ª pasada, 8/8).
- bettercap, scapy, nfqueue/libnetfilter_queue, eBPF/tc — adversarios contemplados.