# ADR-057: Capa de consulta del grafo (Kuzu), bitemporalidad y acceso NL→plantilla

- **Estado:** 🟡 BORRADOR (DAY 180) — refinamiento iterativo Alonso ↔ Claude antes del Consejo.
- **Contexto previo:** ADR-052 (identidad de flujo), schema.cypher (DAY 180), backend KuzuGraphSink (DAY 180).
- **No convocado al Consejo todavía.** Este documento es un embrión; las secciones marcadas
  con ❓ son preguntas abiertas a resolver antes de pasarlo por los 8 modelos.

---

## 1. Contexto

DAY 180 cerró la ESCRITURA al grafo: el correlation-engine materializa
`(:NetworkFlow)`, `(:Alert|:TelemetryEvent)` y aristas `*_ABOUT` en Kuzu embebido,
como vista derivada del bronce. Pero **escribir no es consultar**. Falta definir cómo
se LEE el grafo de forma segura, útil y temporalmente correcta. Tres problemas distintos
que conviene abordar juntos porque se condicionan:

1. **Capa de consulta** — quién consulta el grafo y cómo, sin exponer Cypher crudo.
2. **Bitemporalidad** — el grafo hoy solo conoce el tiempo del evento, no el de su conocimiento.
3. **Acceso NL→plantilla** — traducir lenguaje natural a consultas acotadas y auditables.

---

## 2. Decisión (provisional, a refinar)

### 2.1 Capa de consulta

El grafo NO se expone como endpoint Cypher libre. Se expone mediante un **catálogo de
plantillas de consulta parametrizadas** (Cypher pre-escrito, auditado, con huecos tipados).
Razones: seguridad (sin inyección Cypher), auditabilidad (cada plantilla es revisable),
estabilidad (la forma del grafo puede evolucionar sin romper consumidores).

❓ ¿La capa de consulta es una librería C++ (in-process, como el sink) o un servicio
con su propia superficie de red? Lo segundo reabre el problema de autenticación.
❓ ¿Quién es consumidor legítimo del grafo? (ligado a las reglas Falco de lectura de
argus_graph.yaml, que hoy alertan de cualquier lector ≠ correlation-engine).

### 2.2 Bitemporalidad

El grafo actual registra **tiempo de evento** (`flow_start_window`, cuándo ocurrió el
flujo). Falta el **tiempo de sistema/decisión** (cuándo el engine lo materializó y supo
de él). Sin este segundo eje no se pueden responder consultas como "¿qué sabíamos a las
03:00?" ni reconstruir el estado de conocimiento en un instante pasado — crítico para
forense e informes de incidente reproducibles (infraestructura crítica: hospitales).

❓ ¿Dónde vive el tiempo de sistema? ¿Propiedad nueva en los nodos (`ingested_at`,
`decided_at`), en las aristas, o en una capa de versionado aparte?
❓ Relación con DEBT-ARGUSPP-CLOCK-INJECTION-001: el tiempo de evento depende de un reloj
hoy no-reproducible. La bitemporalidad agrava o ayuda a acotar ese problema (a decidir).
❓ ¿Kuzu soporta bitemporalidad de forma idiomática o hay que modelarla a mano? (investigar).

### 2.3 Acceso NL→plantilla

Lenguaje natural → SELECCIÓN de una plantilla del catálogo + extracción de parámetros.
**NUNCA** NL→Cypher libre (riesgo de inyección/consulta destructiva, alucinación de
estructura inexistente). El NL solo elige entre plantillas auditadas y rellena sus huecos.

❓ ¿El intérprete NL es un modelo local (TinyLlama del RAG ya presente) o se delega?
❓ ¿Cómo se valida que la plantilla elegida + parámetros responde lo que el usuario pidió?
❓ Catálogo inicial de plantillas: ¿cuáles son las 5-10 consultas que de verdad importan?
(p.ej. "alertas de categoría X en ventana T", "vecindario a N saltos de un host",
"flujos correlacionados con esta alerta"). Definirlas guía el resto del diseño.

---

## 3. Consecuencias

- (+) El grafo se vuelve consultable de forma segura y auditable, no solo escribible.
- (+) La bitemporalidad habilita forense reproducible y informes "a fecha de".
- (+) NL→plantilla baja la barrera de uso sin abrir un agujero de inyección.
- (−) Complejidad: tres subsistemas nuevos. Riesgo de sobre-ingeniería si se aborda de golpe.
- (−) La bitemporalidad puede requerir cambios de schema (ALTER TABLE / re-modelado).

---

## 4. Alternativas consideradas (a desarrollar)

- Exponer Cypher crudo con allowlist de operaciones → descartado (frágil, inseguro).
- NL→Cypher libre con un LLM → descartado (inyección, alucinación de estructura).
- Sin bitemporalidad (solo tiempo de evento) → insuficiente para forense reproducible.

---

## 5. Pendiente antes del Consejo

- [ ] Definir el catálogo inicial de plantillas (§2.3) — es lo que ancla todo lo demás.
- [ ] Investigar soporte bitemporal idiomático en Kuzu v0.11.3.
- [ ] Decidir in-process vs servicio (§2.1).
- [ ] Resolver la dependencia con DEBT-ARGUSPP-CLOCK-INJECTION-001 (§2.2).
- [ ] Refinar iterativamente y CONVOCAR al Consejo de Sabios (medir, no votar).