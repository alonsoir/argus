# Dictamen del Consejo — ADR-052 v1 (borrador)

## Resumen ejecutivo

El borrador es **sólido conceptualmente** y corrige un error de categoría común en sistemas de correlación de red: confundir una clave de correlación (`community_id`) con una clave de identidad. La separación de vectores A (MITM pasivo/L2) y B (inyección activa/L3-L4) es aguda. La decisión de no delegar la defensa al hash es correcta desde el punto de vista de la teoría de sistemas distribuidos tolerantes a fallas bizantinas.

Sin embargo, hay **tres grietas estructurales** que deben cerrarse antes de ratificar: (1) la elección de `flow_start_window` tiene efectos de borde no analizados sobre flujos de larga duración y NAT; (2) la propuesta de `hash(node_id ‖ community_id ‖ flow_start_window)` no especifica la función de hash ni la codificación, lo que introduce riesgo de colisión y de orden de bytes; (3) el modelo de amenaza asume que el sensor de borde es honesto hasta que se demuestre lo contrario, pero no hay mecanismo de "prueba de vida" del sensor en el `flow_uid`.

A continuación: fortalezas consolidadas, debilidades con propuesta de parche, y respuesta a las 7 preguntas abiertas.

---

## 1. Fortalezas a apuntalar (no tocar)

### 1.1 La separación A/B es un marco de amenaza valioso
La taxonomía **Vector A (ciego al hash) vs. Vector B (manipulable en el hash)** es la contribución más fuerte de este ADR. Debe conservarse textualmente y exportarse a un documento de threat model del proyecto. Es aplicable más allá de `community_id`: cualquier función de resumen determinista sobre cabeceras es vulnerable a la misma dicotomía.

### 1.2 "Garbage in, garbage hashed" como lema de arquitectura
La frase §3.5 debe convertirse en un principio de diseño del proyecto. Es la contraposición correcta al "hash como sello de garantía" que se ve en muchos SIEMs. La integridad criptográfica de un hash no traslada integridad semántica al pre-imagen.

### 1.3 El menú NAT con anotación obligatoria
El §3.2 es un diseño de ingeniería robusto: menú ordenado por confianza, fallback degradado, y **prohibición explícita de fallo silencioso**. Esto evita el "NAT hole" que mata la correlación en entornos contenedorizados. La anotación de método+confianza en el grafo es compatible con grafos de conocimiento probabilísticos.

### 1.4 Etiquetado sin exclusión
La decisión de no borrar flujos inyectados del dataset (§8, último bullet) es correcta desde la metodología científica. El sesgo de "solo guardar lo limpio" destruye la validez externa de cualquier modelo de detección entrenado sobre el grafo.

---

## 2. Debilidades y parches propuestos

### 2.1 Especificación incompleta de `flow_uid` — riesgo de colisión y orden de bytes

**Problema:** La fórmula `hash(node_id ‖ community_id ‖ flow_start_window)` no define:
- ¿Qué función de hash? (SHA-256, SHA-3, Blake2b, CityHash, xxHash…)
- ¿Concatenación de strings, de bytes, de structs serializados?
- ¿Endianness del `flow_start_window`?
- ¿Longitud fija o delimitador entre campos? (riesgo de *prefix collision*: `node="A‖B"`, `cid="C"` vs `node="A"`, `cid="B‖C"`)

**Impacto:** En un grafo distribuido, dos implementaciones (sensor en C++ vs. correlation-engine en Python) pueden producir `flow_uid` distintos para el mismo flujo si usan codificaciones diferentes. Esto rompe la unicidad de nodo y la detección de inyección.

**Parche propuesto:**
```text
flow_uid = base64(sha3-256(utf8(node_id) ‖ 0x00 ‖ utf8(community_id) ‖ 0x00 ‖ 
                           uint64_be(flow_start_window)))
```
- `sha3-256` por resistencia a length-extension (aunque no sea un ataque directo aquí, es buena higiene).
- Delimitador de byte nulo `0x00` entre campos para evitar ambigüedad de concatenación.
- `uint64_be` para `flow_start_window` (timestamp UNIX o bucket ID).
- `base64` para compatibilidad con Neo4j `STRING` sin caracteres de control.

**Tarea accionable:** Añadir un §3.1.1 "Codificación canónica de `flow_uid`" al ADR.

---

### 2.2 `flow_start_window`: el dilema del flujo de larga duración

**Problema:** El documento reconoce el riesgo de fragmentación (§7, riesgo 2), pero no propone una política de ventana deslizante o de "extensión". Un flujo TCP que dure 2 horas (e.g., SSH, VPN) cruzará múltiples ventanas. ¿Se genera un `flow_uid` nuevo? ¿Se mantiene el original? ¿Se crea una arista `TEMPORAL_EXTENSION`?

Si se genera un nuevo `flow_uid` por cada ventana, un atacante que inyecte una 5-tupla clonada en una ventana posterior podría parecer una "extensión legítima" en lugar de una inyección.

**Parche propuesto:** Definir que `flow_start_window` es **inmutable una vez fijado al inicio del flujo**. El flujo se extiende en el tiempo con aristas de duración (como en ADR-046 §3.2), pero su identidad de nodo (`flow_uid`) permanece anclada a la ventana de nacimiento. Esto implica que el sensor debe emitir un evento de "inicio de flujo" con el `flow_start_window`, y eventos de "continuación" que referencian el mismo `flow_uid`.

**Tarea accionable:** Especificar en §3.1 que `flow_start_window` es timestamp de *creación*, no de *actualización*, y que los flujos de larga duración mantienen identidad estable.

---

### 2.3 Asimetría en la confianza del `node_id`

**Problema:** El `flow_uid` ancla a un `node_id`, pero el documento no define cómo se certifica que un `node_id` es legítimo. En un modelo de amenaza hostil, un atacante que comprometa un sensor puede emitir flujos con `node_id` válido y `community_id` fabricados. El `flow_uid` no detectaría esto; solo el `orphan_rate` (ADR-051) lo haría *a posteriori*.

**Parche propuesto:** Añadir una nota en §3.1 de que `flow_uid` es **condición necesaria pero no suficiente** para la integridad. La suficiencia requiere la triada:
1. `flow_uid` bien formado (sintaxis).
2. `node_id` en el inventario de endpoints (ADR-046 §3.9) y con certificado/Noise_IKpsk3 válido (ADR-027).
3. `community_id` corroborado por al menos otro sensor o dentro del `orphan_rate` tolerable (ADR-051).

**Tarea accionable:** Aclarar que `flow_uid` es una prueba de *autenticidad de origen*, no de *honestidad de contenido*.

---

### 2.4 El menú NAT carece de criterio de degradación explícito

**Problema:** El §3.2 lista 4 mecanismos, pero no dice qué pasa cuando varios mecanismos del menú producen respuestas *inconsistentes* (e.g., translation node dice IP interna = 10.0.0.5, pero el puente por proceso+puerto apunta a 10.0.0.6). ¿Se descarta el flujo? ¿Se crean dos aristas host↔flujo con confianzas distintas? ¿Se dispara una alerta de "inconsistencia NAT"?

**Parche propuesto:** Añadir una regla de resolución de conflicto: **consenso por mayoría ponderada por confianza**. Si los mecanismos de mayor confianza (1, 2) discrepan, se marca el flujo como `CONFLICT_NAT` y se eleva a análisis humano/ML. No se hace fallback silencioso al mecanismo 4.

**Tarea accionable:** Añadir §3.2.1 "Resolución de conflictos entre mecanismos NAT".

---

### 2.5 La señal ARP/NDP no tiene modelo de falsificación

**Problema:** El §3.4 y §6 Q2 plantean ARP/NDP como detector del vector A, pero ARP spoofing es *precisamente* el ataque que el vector A describe. Si el atacante controla la tabla ARP del host, la "señal ARP" que envía Wazuh al grafo es también una mentira. El documento asume implícitamente que el host plane es más confiable que el data-plane, pero no lo justifica.

**Parche propuesto:** Aclarar que la correlación host↔red detecta el vector A **solo si el host plane está parcialmente comprometido** (e.g., atacante en red local hace ARP spoof, pero el endpoint Wazuh/Agent sigue funcionando y reporta el cambio de MAC). Si el atacante tiene root en el endpoint, la señal ARP también es falsa. Por tanto, ARP/NDP es **detector de vector A en escenario de red comprometida, host sano**, no en escenario de host comprometido.

Esto conecta con la necesidad de una **tercera fuente**: la tabla ARP debe ser observable por un agente *fuera* del host (e.g., switch con port-security, o sensor de red en modo promiscuo que vea las solicitudes ARP). Si no hay tercera fuente, el vector A con host comprometido es **indetectable por diseño** (límite fundamental de la observabilidad).

**Tarea accionable:** Añadir una nota de límite fundamental en §3.4: "ARP/NDP como señal de primera clase solo detecta vector A bajo el supuesto de host sano. Host comprometido requiere fuente externa (switch, out-of-band)."

---

## 3. Respuestas a las preguntas abiertas (§6)

### Q1 — Rate-limit de cardinalidad de `community_id` nuevos por ventana por nodo

**Respuesta:** Aplicar en **dos lugares**, con dos umbrales distintos:

1. **Sensor (edge):** Un límite por ventana por `node_id` en el *sensor* previene que un sensor comprometido o un atacante con acceso al sensor inunde el bus de mensajes. Esto es un *rate limit de publicación*. Umbral sugerido: `max_new_cid_per_window_per_node` = 10× la cardinalidad histórica media del nodo (aprendido adaptativamente). Si se excede, el sensor entra en modo "throttle" y alerta.

2. **Correlation-engine (ingest):** Un límite en el *ingestor* protege Neo4j contra escritura masiva. Este es un *rate limit de aceptación*. Umbral más alto que el del sensor (factor 2×), para no descartar tráfico legítimo de burst.

**Razonamiento:** El rate-limit en el sensor es defensa (evita que un nodo comprometido abuse del sistema). El rate-limit en el ingest es protección de infraestructura (evita que el grafo colapse). Separar ambos evita que un atacante que eluda el sensor (e.g., inyección directa al bus) aún encuentre un muro en el ingest.

**Tarea:** Crear `ADR-052-APPENDIX-RATE-LIMIT` o absorber en ADR-046 v5.

---

### Q2 — ARP/NDP: ¿nodo/arista de primera clase o enriquecimiento?

**Respuesta:** **Nodo de primera clase**, no enriquecimiento.

**Razonamiento:** En un grafo de conocimiento, "enriquecimiento" es información que mejora la descripción de una entidad existente pero no altera la topología. ARP/NDP es una **observación causal independiente** que puede existir sin flujo (e.g., un host que responde ARP pero no genera tráfico IP relevante). Si es enriquecimiento, no se puede correlacionar con flujos ausentes. Como nodo `:ArpObservation` (o `:L2Resolution`) con aristas `RESOLVES_TO` hacia `:Endpoint` y `OBSERVED_BY` hacia `:Sensor`, permite consultas del tipo:

```cypher
MATCH (a:ArpObservation)-[:OBSERVED_BY]->(s:Sensor {node_id: 'X'})
WHERE a.mac <> a.previous_mac
RETURN a.ip, a.mac, a.timestamp
```

Esto es necesario para detectar el vector A. Si fuera enriquecimiento, estaría embebido en un nodo `:NetworkFlow` y perderías la capacidad de observar ARP sin flujo asociado.

**Tarea:** Crear nodo `:L2Resolution` con propiedades `ip`, `mac`, `previous_mac`, `timestamp`, `resolution_method` (ARP/NDP/STATIC), y aristas `RESOLVES_TO` → `:Endpoint`, `OBSERVED_BY` → `:Sensor`.

---

### Q3 — Marca de confianza de flujo

**Respuesta:** **Sí, propiedad `confidence_score` en el nodo-flujo**, con semántica de fuentes.

**Razonamiento:** No es suficiente un booleano "confiable/no confiable". Se necesita un score continuo o categórico ordinal:

- `CORROBORATED` — visto por ≥2 sensores independientes, `community_id` coincide.
- `SINGLE_SENSOR` — visto por 1 sensor, dentro del `orphan_rate` tolerable.
- `ORPHAN` — visto por 1 sensor, fuera del `orphan_rate` (alerta ADR-051).
- `INJECTED` — etiquetado por ground truth MITRE (ADR-050).
- `CONFLICT_NAT` — resolución NAT inconsistente (ver §2.4 arriba).

**Conexión con `acceptance_criteria.md`:** Añadir `INJECTED` como categoría de presencia. No es un bug, no es una política, no es desconocido: es **ground truth de ataque** y debe ser tratado como dato de primera clase para entrenamiento.

**Tarea:** Modificar esquema Neo4j para incluir `confidence_score:ENUM` y actualizar `acceptance_criteria.md`.

---

### Q4 — Etiquetado de flujo sospechoso de inyección sin excluirlo

**Respuesta:** El mecanismo ya está bien descrito en §8, pero falta la **procedencia del etiquetado**.

**Razonamiento:** El etiquetado debe ser **no repudiable y trazable**. No basta con una propiedad `injected=true`. Se necesita:

```cypher
(:NetworkFlow)-[:TAGGED_AS {method: 'MITRE_GROUND_TRUTH', 
                            source: 'ADR-050-SESSION-7', 
                            timestamp: t, 
                            analyst: 'auto'}]->(:Tag {label: 'INJECTED'})
```

Esto permite auditoría y evita que un atacante que comprometa el correlation-engine "des-etiquete" flujos. La arista de etiquetado es inmutable (append-only log en el grafo).

**Tarea:** Añadir nodo `:Tag` y arista `:TAGGED_AS` con propiedades de provenance al esquema.

---

### Q5 — Relación con ADR-050 (sesión MITRE)

**Respuesta:** **Sí, uno de los 6 vectores debe ser MITM con bettercap**, y ADR-052 es su modelo de amenaza formal.

**Razonamiento:** ADR-050 define el ground truth de la sesión MITRE. Si el vector MITM no está incluido, ADR-052 pierde su principal caso de validación. La nota de amenaza DAY 171 ya describe el escenario. ADR-052 debe ser citado en ADR-050 como "modelo de amenaza subyacente al vector MITM".

**Tarea:** Añadir referencia cruzada en ADR-050 cuando se redacte.

---

### Q6 — Granularidad de `flow_start_window`

**Respuesta:** **Bucket de 60 segundos (1 minuto)** como default LAB, con política de "extensión inmutable" (ver §2.2 arriba).

**Razonamiento:**
- **CrisisWindow** (variable) es peligrosa como componente de identidad: si la ventana cambia por configuración, los `flow_uid` históricos se invalidan. La identidad debe ser estable ante cambios de política.
- **N segundos fijos** es predecible. 60 segundos es un compromiso:
    - Reciclaje de 5-tupla en TCP: un puerto efímero típico en Linux tiene `net.ipv4.tcp_tw_reuse` y `tcp_tw_recycle` (aunque este último está deprecado). El tiempo mínimo de reutilización de un puerto en estado TIME-WAIT es ~60s. Un bucket de 60s corta la mayoría de reciclajes legítimos.
    - Flujos de larga duración: un SSH que dure horas no se fragmenta porque la ventana es de *inicio*, no de *actualización*.

**Tarea:** Fijar default `flow_start_window = 60s` en §4, con nota de que es timestamp de inicio inmutable.

---

### Q7 — ¿Mantener P1 y P3 juntos o separar en ADR-053?

**Respuesta:** **Mantener juntos (ADR-052 único)**.

**Razonamiento:** Aunque conceptualmente separables, comparten:
- El esquema Neo4j (constraint compuesto, `node_id` obligatorio).
- El modelo de amenaza (data-plane hostil).
- La validación (golden pcap MITRE).

Separarlos generaría duplicación de contexto y riesgo de inconsistencia en el esquema. El ADR actual ya tiene una delimitación clara con ADR-046 (§1). Si la longitud es preocupación, se puede mover el menú NAT a un apéndice, pero no a un ADR independiente.

**Tarea:** No dividir. Añadir nota en §1 de que P1 y P3 son co-dependientes en el esquema y por tanto se deliberan conjuntamente.

---

## 4. Tareas accionables derivadas (para backlog)

| ID | Tarea | Prioridad | Dueño sugerido |
|---|---|---|---|
| **ADR-052-A1** | Especificar codificación canónica de `flow_uid` (función de hash, delimitador, endianness) | P0 | Arquitectura |
| **ADR-052-A2** | Definir `flow_start_window` como timestamp inmutable de inicio; política de extensión de flujos largos | P0 | Arquitectura |
| **ADR-052-A3** | Añadir nodo `:L2Resolution` (ARP/NDP) de primera clase al esquema Neo4j | P1 | Backend/Grafo |
| **ADR-052-A4** | Implementar rate-limit dual: sensor (publicación) + ingest (escritura) | P1 | Infraestructura |
| **ADR-052-A5** | Añadir propiedad `confidence_score:ENUM` y categoría `INJECTED` al esquema y a `acceptance_criteria.md` | P1 | Data/ML |
| **ADR-052-A6** | Implementar arista `:TAGGED_AS` con provenance para etiquetado de ground truth | P2 | Backend/Grafo |
| **ADR-052-A7** | Redactar apéndice de resolución de conflictos NAT | P2 | Arquitectura |
| **ADR-052-A8** | Actualizar ADR-050 para incluir vector MITM con bettercap y citar ADR-052 como threat model | P2 | Red Team/Arquitectura |
| **ADR-052-A9** | Documentar límite fundamental: vector A con host comprometido requiere fuente externa (switch/OOB) | P2 | Arquitectura |

---

## 5. Veredicto del Consejo

**Estado recomendado:** `APROBADO CON MODIFICACIONES` (no ratificación directa de v1).

**Condiciones de cierre:**
1. Incorporar los parches de las secciones 2.1–2.5.
2. Responder formalmente las 7 preguntas del §6 con las respuestas del Consejo (esta respuesta).
3. Añadir las tareas A1–A9 al backlog vinculado.
4. Una vez incorporado, elevar a `APROBADO` y desbloquear `DEBT-NEO4J-FLOW-KEY-001`.

El borrador es **técnicamente competente y estratégicamente correcto**. Los puntos débiles son de especificación, no de dirección. La dirección —identidad compuesta, defensa arquitectónica, hash no como control de seguridad— es la correcta para un sistema distribuido bajo modelo de amenaza hostil.

---

*Dictamen emitido por Kimi (Consejo de Sabios), DAY 173.*

KIMI