# ADR-052 — Multi-node Flow Identity & Host↔Net Correlation

| Campo | Valor |
|---|---|
| **ADR** | 052 |
| **Versión** | v1 (borrador) |
| **Fecha** | 2026-06-02 (DAY 173) |
| **Estado** | BORRADOR — pendiente deliberación Consejo de Sabios |
| **Decisión final** | Alonso (pendiente) |
| **Deliberación** | Consejo de Sabios (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen) — pendiente |
| **Recoge** | P3 (identidad de flujo multi-nodo) + P1 (correlación host↔red) del Consejo DAY 170 |
| **Depende de / relaciona** | ADR-046 v4 (modelo dual de claves, grafo temporal, inventario de endpoints), ADR-051 (Seed Parity Gate / orphan_rate), ADR-050 (sesión MITRE — ground truth), ADR-048 (etcd HA / correlación) |
| **Ratifica** | DEBT-NEO4J-FLOW-KEY-001 (P0 esquema, constraint Neo4j 5.x antes de poblar el grafo) |
| **Artefactos derivados** | Esquema Neo4j (constraint compuesto), `flow_uid` en el correlation-engine, señal ARP/NDP del host plane (pendiente: enriquecimiento vs primera clase) |

---

## 1. Estado

BORRADOR. Formaliza dos decisiones que ADR-046 v4 dejó abiertas o solo esbozadas:

1. **Identidad de nodo-flujo en el grafo** (P3 DAY 170): ADR-046 v4 define `community_id` y `host_key` como claves de *correlación*, pero no fija la *identidad única* de un flujo como nodo de Neo4j en un despliegue multi-nodo donde las 5-tuplas se reciclan. ADR-052 cierra ese hueco con `flow_uid`.
2. **El community_id ante un data-plane hostil** (modelo de amenaza DAY 171): ADR-046 v4 trata el data-plane como ruidoso; ADR-052 lo trata como **hostil** y formaliza por qué la defensa contra MITM/inyección es arquitectónica, nunca del hash.

> **Delimitación con ADR-046 v4 (anti-duplicación).** ADR-052 NO redefine el modelo dual de claves (§3.1 de ADR-046), el grafo temporal con aristas tipadas (§3.2), el inventario de endpoints como estado de primera clase (§3.9) ni la cuota anti-pinning fail-closed (§3.5). ADR-052 *consume* esas decisiones y añade encima: (a) la identidad de nodo `flow_uid`, y (b) el modelo de amenaza como justificación de segundo orden de esas mismas decisiones. Donde haya solape aparente, ADR-046 v4 es la fuente; ADR-052 referencia, no reescribe.

---

## 2. Contexto

### 2.1 El community_id no es identidad de nodo

`community_id` es una clave de **correlación**: tres sensores honestos que ven el mismo paquete coinciden (validado DAY 171, diana `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`). Pero como identidad de nodo en Neo4j es insuficiente por dos razones independientes:

- **Reciclaje de 5-tupla en el tiempo.** La misma 5-tupla (mismas IPs/puertos/proto) se reutiliza en sesiones distintas a lo largo del tiempo. Dos flujos legítimos no relacionados producen el mismo `community_id`. Si fuera la identidad de nodo, se fundirían en un único nodo del grafo — corrupción de la estructura.
- **Mundo multi-nodo.** En un despliegue federado, dos sensores en nodos físicos distintos pueden ver flujos con la misma 5-tupla (NAT, rangos privados solapados). Mismo `community_id`, flujos distintos en realidades de red distintas.

Conclusión: `community_id` es **propiedad indexada** (clave de correlación intra-nodo + verificable contra oráculo `pycommunityid`), nunca identidad de nodo.

### 2.2 El data-plane es hostil, no solo ruidoso

ADR-046 v4 modela latencia, reorden y pérdida (data-plane ruidoso). ADR-052 añade el supuesto de **adversario activo con capacidad de modificar paquetes en runtime**: bettercap (ARP/NDP spoofing, inyección), scapy/ad hoc (fabricación de cabeceras), nfqueue/libnetfilter_queue (mutación en el path del kernel), eBPF/tc (reescritura a velocidad de línea, peor caso).

Bajo este supuesto, **todo lo que el sensor observa puede ser una mentira fabricada por el atacante.** El `community_id` —función pura de la 5-tupla— hereda esa hostilidad: garbage in, garbage hashed. La integridad del hash ≠ integridad del contenido hasheado.

### 2.3 Por qué hace falta decidir esto ANTES de poblar Neo4j

El esquema de identidad de nodo (constraint, propiedades obligatorias) es doloroso de retrofitear con datos en producción y gratis de decidir con el grafo vacío (consenso DAY 170). DEBT-NEO4J-FLOW-KEY-001 es P0 de esquema precisamente porque bloquea el diseño del correlation-engine. ADR-052 ratifica ese esquema para desbloquearlo.

---

## 3. Decisión

### 3.1 Identidad de nodo-flujo: `flow_uid` (P3)

```
flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)
```

- **`community_id`** — propiedad indexada del nodo (correlación + verificable contra oráculo). NUNCA identidad.
- **`node_id`** — identificador del sensor que emitió el flujo. Obligatorio. Ancla cada flujo a su origen físico.
- **`flow_start_window`** — bucket temporal del inicio del flujo (granularidad: ver §4, pendiente Consejo). Corta el reciclaje/clonado de 5-tuplas en el tiempo.

**Propiedades obligatorias en el grafo:** `node_id` en `:NetworkFlow`, `:Alert`, `:TelemetryEvent`. Constraint compuesto nativo Neo4j 5.x sobre la identidad de nodo-flujo.

**Doble justificación del `flow_uid`** (esto es nuevo respecto a P3 original):
1. **Identidad / dedup** (P3 DAY 170): garantiza unicidad de nodo en mundo multi-nodo con reciclaje temporal.
2. **Defensa anti-inyección** (modelo de amenaza, §5): un flujo que "aparece" en el grafo sin emisión del sensor de borde correspondiente (`node_id` sin trazabilidad a sensor real) es anomalía detectable. `flow_start_window` corta el clonado de 5-tuplas de sesiones legítimas.

### 3.2 Correlación host↔red: doble arista (P1)

Sobre el grafo temporal de ADR-046 v4 §3.2, se formaliza la correlación host↔red con **dos aristas de naturaleza distinta** (no confundir con las aristas `FLOW_IDENTITY`/`HOST_LOCALITY`/`TEMPORAL_BRIDGE` de ADR-046, que esta decisión refina para el caso host↔red):

- **Arista flujo↔flujo** — por `community_id`. Determinista. Equivalencia exacta de flujo entre sensores de red (es la `FLOW_IDENTITY` de ADR-046).
- **Arista host↔flujo** — por `host_id`/`agent_id` **canónico** (nunca IP cruda) + ventana temporal **más laxa** que la de red↔red y **causal-bidireccional**. El evento de host se une al endpoint interno/gestionado del flujo (la víctima), no al atacante (join asimétrico de ADR-046 §3.2).

**NAT — menú de mecanismos con anotación obligatoria.** Cuando la IP interna que ve Wazuh ≠ la IP observada por el sensor de red (NAT, contenedores), el puente host↔red se resuelve por un menú de mecanismos, en orden de confianza:
1. Translation node con logs NAT (mayor confianza).
2. Identidad `agent_id`/hostname.
3. Puente por (proceso, puerto_local, timestamp).
4. Fallback temporal degradado (menor confianza).

**Invariante:** SIEMPRE se anota en el grafo y en el log el método usado y su confianza. **Nunca fallo silencioso por IP no coincidente.** (Conecta con BACKLOG-RESEARCH-NAT-HOSTNET-001 y DEBT-ARGUSPP-WAZUH-001.)

### 3.3 Modelo de amenaza: dos vectores opuestos

El community_id reacciona de forma OPUESTA a los dos vectores de ataque. Confundirlos lleva a defensas equivocadas.

| Vector | Capa que toca | Efecto sobre community_id | Detectable por |
|---|---|---|---|
| **A — MITM clásico** (ARP spoof, bettercap base) | L2 (MAC), IP/puerto INTACTOS | **CIEGO** — mismo flujo → mismo hash | Host/ARP plane (cambio MAC↔IP), NO la red |
| **B — Inyección/reescritura** (scapy, nfqueue, módulos bettercap) | L3/L4 (IP, puerto) | **CAMBIA** — atacante fabrica community_id a voluntad | flow_uid + node_id + ventana temporal |

El community_id es **ciego al vector A** (la MAC no entra en el hash) y **totalmente manipulable en el vector B** (es función pura de la 5-tupla). La defensa de cada vector es distinta y ninguna vive en el hash.

### 3.4 Las tres líneas de defensa (arquitectónicas, NO del hash)

1. **`flow_uid` ancla a nodo + ventana** — anti-inyección (vector B). Ya en §3.1. Un flujo sin emisión del sensor de borde = anomalía. `flow_start_window` corta el clonado temporal.
2. **Correlación host↔red** — único detector del MITM sigiloso (vector A). La red reporta el flujo idéntico; el host (Wazuh / tabla ARP vigilada) reporta que la MAC asociada a la IP cambió. **La detección vive en el cruce, no en ninguna capa sola.** Implica vigilancia ARP/NDP en el host plane como señal (¿primera clase o enriquecimiento? — §6).
3. **community_id como dato no confiable del data-plane** — un sensor que emite community_id que **ningún otro corrobora** puede ser sensor comprometido O tráfico inyectado visible por una sola vía. Entra en `community_id.orphan_rate` (ADR-051). Nunca tratar el community_id como verdad; es input observado de un plano hostil.

### 3.5 El community_id NO es un control de seguridad — y nunca lo será

`community_id = "1:" + base64(sha1(seed ‖ saddr ‖ daddr ‖ proto ‖ 0x00 ‖ sport ‖ dport))` es una función **pura y honesta** de la 5-tupla, diseñada para que sensores honestos coincidan. Ante un atacante:

- Vector A: hashea fielmente IPs/puertos intactos → mismo ID, no nota nada.
- Vector B: hashea fielmente la 5-tupla falsa → ID nuevo "válido", el atacante controla el ID.

La integridad del hash no implica integridad del contenido. La defensa contra MITM es responsabilidad de la correlación multi-fuente, el anclaje a nodo, la ventana temporal y la vigilancia del host plane — **arquitectónica, no criptográfica-de-flujo.**

---

## 4. Parámetros configurables (defaults de arranque)

> Adoptados como punto de partida; se ajustarán con evidencia. Coherentes con ADR-046 v4 §4.

| Parámetro | Default LAB | Nota |
|---|---|---|
| `flow_start_window` | **PENDIENTE Consejo** | Granularidad del bucket temporal de `flow_uid`. Candidatos: bucket de la CrisisWindow / N segundos fijos. Debe cortar reciclaje sin fragmentar un mismo flujo legítimo. |
| `host_bridge_window` | 15–30 s (= `bridge_window` ADR-046) | Ventana host↔flujo, más laxa que red↔red. |
| `nat_confidence_floor` | a fijar | Confianza mínima para aceptar un puente NAT sin marcar el flujo como baja-confianza. |
| `max_new_cid_per_window_per_node` | **PENDIENTE Consejo** | Rate-limit de cardinalidad anti grafo-flooding (§6 Q1). ¿Dónde se aplica? |

---

## 5. Alternativas consideradas y rechazadas

| Alternativa | Por qué se rechazó |
|---|---|
| `community_id` como identidad de nodo en Neo4j | Reciclaje temporal de 5-tupla funde flujos no relacionados; mundo multi-nodo colisiona 5-tuplas entre nodos. Corrupción de estructura. |
| `(node_id, community_id)` sin componente temporal | Insuficiente: la 5-tupla se recicla en el tiempo en el MISMO nodo → mismo `(node_id, community_id)` para flujos distintos (objeción DeepSeek DAY 170). |
| Tratar el community_id como control de integridad / señal de seguridad | Es función pura de la 5-tupla: ciego al vector A, manipulable en el vector B. Garbage in, garbage hashed. |
| Defensa contra inyección en el propio hash (HMAC con secreto) | No resuelve el vector A (MAC fuera del hash) y rompe la paridad cross-sensor con Suricata/Zeek (que usan SHA1 estándar). La defensa debe ser arquitectónica. |
| IP cruda como clave del puente host↔red | Colapsa bajo NAT/DHCP/contenedores. Debe ser `agent_id`/hostname canónico. |
| Fallo silencioso cuando la IP host ≠ IP red | Oculta exactamente el caso (NAT, MITM) que más importa observar. Se exige anotación de método + confianza. |

---

## 6. Preguntas abiertas para el Consejo

1. **Rate-limit / cardinalidad.** ¿Cardinalidad máxima de `community_id` nuevos por ventana por nodo, para contener el grafo flooding? ¿Dónde se aplica — sensor, correlation-engine, o ingest a Neo4j? (ADR-046 v4 ya tiene cuota anti-pinning por crisis; esta es por cardinalidad de cid, complementaria.)
2. **Señal ARP/NDP del host plane.** ¿Nodo/arista de primera clase en el grafo, o enriquecimiento? Es el único detector del vector A. Conecta con DEBT-ARGUSPP-WAZUH-001 y BACKLOG-RESEARCH-NAT-HOSTNET-001.
3. **Marca de confianza de flujo.** ¿Propiedad "confianza" en el nodo-flujo? (corroborado por N sensores vs visto por 1 → menor confianza). Conecta con las categorías de presencia del `acceptance_criteria.md` congelado (DROP/CONFIG/POLICY/BUG/UNKNOWN → ¿añadir `INJECTED`?).
4. **Etiquetado de flujo sospechoso de inyección SIN excluirlo del dataset.** Integridad científica: no se borra, se etiqueta — el atacante es parte del ground truth en MITRE. ¿Cómo se marca?
5. **Relación con ADR-050 (sesión MITRE).** ¿Uno de los 6 vectores es MITM con bettercap? Si es así, este modelo de amenaza es el ground truth esperado de ese vector.
6. **Granularidad de `flow_start_window`** (§4). ¿Bucket de CrisisWindow, N segundos fijos, u otra? Debe cortar reciclaje sin fragmentar un mismo flujo legítimo de larga duración.
7. **¿ADR-052 mantiene P1 y P3 juntos o se separa P1 a ADR-053?** Comparten esquema Neo4j (argumento para juntarlos); pero P1 (host↔red) es conceptualmente separable de P3 (identidad de flujo). Decisión del Consejo.

---

## 7. Consecuencias

**Positivas.** Identidad de nodo-flujo robusta en mundo multi-nodo con reciclaje temporal. La defensa contra MITM/inyección queda explícita y arquitectónica, no delegada falsamente al hash. El `flow_uid` gana doble rol (identidad + defensa). El dataset puede etiquetar tráfico inyectado como ground truth sin contaminarse. Desbloquea DEBT-NEO4J-FLOW-KEY-001 (esquema ratificado antes de poblar).

**Negativas / coste.** `node_id` obligatorio en el esquema (propiedad en cada nodo-evento). Vigilancia ARP/NDP en el host plane como nueva señal a recolectar. Rate-limit de cardinalidad de community_id como nuevo mecanismo. Granularidad de `flow_start_window` debe calibrarse (mal elegida fragmenta flujos legítimos o no corta el reciclaje).

**Riesgos.** (1) Si la vigilancia ARP/NDP no se implementa, el vector A (MITM sigiloso) queda **indetectable** — la única línea de defensa contra él es la correlación host↔red. (2) `flow_start_window` mal calibrado: demasiado fino fragmenta un flujo legítimo en múltiples nodos; demasiado grueso no corta el reciclaje. (3) El menú de mecanismos NAT con fallback temporal degradado puede producir puentes de baja confianza que, sin umbral claro, contaminen la correlación.

---

## 8. Validación (EMECAS++)

Tests obligatorios sobre golden pcap (tier determinista, coherente con ADR-046 v4 §7):

- **Unicidad de `flow_uid`:** dos flujos con la misma 5-tupla en **nodos distintos** → `flow_uid` distinto. Misma 5-tupla **reciclada en el tiempo** en el mismo nodo → `flow_uid` distinto. (Test de cierre de DEBT-NEO4J-FLOW-KEY-001.)
- **Constraint Neo4j:** intento de insertar nodo-flujo sin `node_id` → rechazado por constraint.
- **Anti-inyección (vector B):** inyectar flujos con 5-tuplas fabricadas → quedan anclados a `node_id` del sensor que los vio; un flujo sin sensor de borde trazable → marcado anomalía.
- **MITM sigiloso (vector A):** simular ARP spoof (MAC cambia, IP/puerto intactos) → la red NO levanta señal (esperado, community_id ciego); el cruce host↔red SÍ detecta el cambio MAC↔IP. Si la señal ARP/NDP no está, el test documenta la ceguera.
- **NAT con anotación:** flujo bajo NAT simulado → puente host↔red resuelto por mecanismo del menú, con método + confianza anotados en grafo y log. Nunca fallo silencioso.
- **Etiquetado de inyección:** flujo inyectado en escenario MITRE → etiquetado `INJECTED` (o equivalente), NO excluido del dataset.

---

## 9. Deudas y diferidos

- `DEBT-NEO4J-FLOW-KEY-001` — **ratificada por este ADR.** flow_uid + node_id obligatorio + constraint Neo4j 5.x. P0 esquema, antes de poblar el grafo.
- `DEBT-ARGUSPP-ARP-MONITOR-001` (NUEVA, propuesta) — vigilancia ARP/NDP en el host plane como señal de detección del vector A. Sin ella, el MITM sigiloso es indetectable. Prereq: Wazuh integrado.
- Rate-limit de cardinalidad de community_id (§6 Q1) — pendiente decisión de ubicación. Post-Consejo.
- Marca de confianza de flujo y categoría `INJECTED` en acceptance_criteria.md (§6 Q3) — pendiente Consejo.
- Relación con ADR-050: si un vector MITRE es MITM bettercap, este modelo es su ground truth (§6 Q5).

---

## 10. Referencias

- ADR-046 v4 (modelo dual de claves, grafo temporal, inventario de endpoints, cuota anti-pinning) — **fuente de las decisiones que ADR-052 consume sin reescribir.**
- ADR-051 (Seed Parity Gate & Correlation Health — `orphan_rate` gana rol de detección de sensor comprometido / inyección).
- ADR-050 (sesión MITRE — ground truth del vector MITM, pendiente redacción).
- `corelight/community-id-spec` (algoritmo Community ID v1).
- Nota de amenaza DAY 171 (MITM e inyección en runtime) — material primario integrado en §3.3–§3.5.
- Consejo de Sabios DAY 170: P1 (host↔red), P3 (identidad de flujo multi-nodo).
- bettercap, scapy, nfqueue/libnetfilter_queue, eBPF/tc — adversarios contemplados (§2.2).