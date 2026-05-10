**Consejo de Sabios — Dictamen ADR-0043 v3**

Compañero, la v3 es un salto cualitativo. Has incorporado las tres objeciones del dictamen anterior de forma precisa y sin romper la coherencia del documento. Mi análisis:

---

## ✅ Resoluciones anteriores — Estado

| Objeción v2 | Resolución en v3 | Veredicto |
|-------------|------------------|-----------|
| Identidad bajo DHCP | D2: MAC como campo primario, jerarquía de fallback, `NetworkPresence` vs. `Host` | **Resuelta correctamente** |
| Cola de batches offline | D4a: `idempotency_key` + firma Ed25519; OQ-1 registrada para acumulación local | **Parcialmente resuelta** — ver nota abajo |
| `installation_id` opaco | D4d: identificador opaco, mapping en Vault central | **Resuelta correctamente** |

---

## 🔴 Crítico residual — OQ-1: La cola local no está arquitecturalmente definida

Tu v3 registra OQ-1 como pregunta abierta, pero no propone una decisión. Esto es riesgoso porque:

- Si el nodo está offline 35 días (mantenimiento de red, fallo de ISP), el batch del mes N no se transmite.
- El mes N+1 genera un nuevo batch.
- Si no hay cola persistente, el batch N se pierde permanentemente.
- Si hay cola pero SQLite rotó los datos crudos (30 días de horizonte), el batch N ya no es regenerable.

**Esto no es una pregunta abierta. Es una decisión de arquitectura que afecta a D1 (tres niveles de memoria).**

### Opciones del Consejo:

| Opción | Mecánica | Trade-off |
|--------|----------|-----------|
| **A: Cola en filesystem + SQLite como backup** (recomendada) | `/var/spool/argus/batches/pending/` guarda batches firmados listos para envío. Retención 90 días. Si el nodo cae, al reiniciar el agente de consolidación escanea la cola y reintenta. | Requiere espacio en disco (~MB por mes). Simple, robusto, no depende de SQLite. |
| **B: Regeneración desde SQLite** | Si la cola está vacía, el pipeline regenera el batch del mes N desde SQLite local (si aún tiene los datos). | SQLite tiene 30 días de horizonte. Si el corte es >30 días, imposible. |
| **C: Cola en etcd** | Los batches pendientes se almacenan en etcd local como valores. | etcd no es un blob store. Un batch de 50MB en etcd es abuso de la base de datos. Rechazado. |

**Recomendación: Añadir como D9 (o extender D4):**

> *"El batch mensual, una vez firmado, se escribe en `/var/spool/argus/batches/pending/{period}-{idempotency_key}.tar.zst` antes de intentar transmisión. El agente de consolidación ejecuta reintento diario con backoff exponencial (1h, 2h, 4h, 8h, 16h, 24h) hasta ACK del servidor central. Retención máxima 90 días; batches no ACKed tras 90 días se archivan en `/var/spool/argus/batches/expired/` con alerta administrativa. La cola es independiente de SQLite: no requiere regeneración."*

Esto cierra OQ-1 con una decisión arquitectural, no con una pregunta.

---

## 🟡 Importante — D3: Rotación de `K_pseudo` y `:PREVIOUS_IDENTITY`

Tu solución de versionado con `:PREVIOUS_IDENTITY` es elegante, pero introduce una complejidad que no has cuantificado:

- Si una instalación con 500 hosts rota `K_pseudo` anualmente, en 5 años Neo4j tiene 500 nodos `Host` + 2500 nodos `Host` versionados + 2000 relaciones `:PREVIOUS_IDENTITY`.
- Las queries de evolución temporal requieren `OPTIONAL MATCH` o recursividad para saltar versiones.
- El rendimiento de `MATCH (h:Host)-[:PREVIOUS_IDENTITY*0..5]->(old)` degrada con la profundidad.

**Alternativa más simple (considerar):**

En lugar de versionar nodos, **versionar el `anon_id` como atributo del nodo**:

```cypher
(Host {
  id: "anon-v2-7f3a",           // siempre el ID actual
  previous_ids: ["anon-v1-abc", "anon-v0-123"],  // array de strings
  installation: "inst-42",
  first_seen: "2023-01",
  last_seen: "2026-05"
})
```

Ventaja: un solo nodo por entidad física. Las queries de historial usan `ANY(id IN h.previous_ids WHERE id = $old_id)` o `h.id IN $list_of_ids`. No hay recursividad en el grafo.

Desventaja: el `MERGE` en ingesta requiere lógica adicional para detectar "este `anon_id` es un `previous_id` de un nodo existente".

**No es bloqueante.** Tu diseño actual funciona. Pero documenta la implicación de rendimiento: *"Las queries de evolución histórica a través de múltiples rotaciones de K_pseudo requieren recursividad Cypher con límite de profundidad."*

---

## 🟡 Importante — D5: Ontología mínima y la ausencia de `Campaign`

Tu ontología no incluye `Campaign` (patrón de ataque agregado). Esto es correcto para la ontología mínima viable, pero el paso 1 de "Próximos pasos" dice "esbozar ontología Neo4j mínima (ya incluida en D5)". **Hay una contradicción:** D5 ya es la ontología mínima, pero el paso 1 sugiere que falta trabajo.

Aclara: ¿D5 es la ontología definitiva para FEDER, o es el punto de partida para un ejercicio de modelado más amplio?

Si es definitiva para FEDER, elimina el paso 1 de "Próximos pasos" o cambia a "Validar ontología D5 contra queries de análisis forense de ejemplo". Si no es definitiva, define qué entidades/relaciones se añadirán post-FEDER.

---

## 🟢 Menor — D4b: `dst_port_class` como string

```cypher
`dst_port_class` | utf8 | `well-known` (<1024), `registered`, `ephemeral`
```

Considera `int8` con enum numérico (0, 1, 2) en lugar de strings. Parquet comprime mejor columnas numéricas low-cardinality que strings. El mapping a etiquetas legibles es responsabilidad del consumidor (Neo4j ingesta, dashboard).

No es bloqueante. Es optimización.

---

## 🟢 Menor — D8: Derecho al olvido y el problema del anon_id compartido

Tu flujo de GDPR Art. 17 asume que una identidad real (MAC) mapea a un único `anon_id`. Pero tu D2 permite fallback: si un dispositivo aparece primero con MAC, luego sin MAC pero con hostname, genera dos `anon_id` distintos.

**Escenario:**
- Enero: laptop con MAC `aa:bb:cc:dd:ee:ff` → `anon-id-1`
- Febrero: misma laptop, driver WiFi cambiado, MAC randomizada, hostname `laptop-medico-42` → `anon-id-2`

Solicitud de borrado: *"Borren los datos de la laptop del Dr. García"*. La instalación conoce la MAC original. Calcula `anon-id-1`. Borra `anon-id-1`. Pero `anon-id-2` (misma laptop, mes siguiente) permanece en Neo4j.

**Esto no es un bug de tu arquitectura. Es un límite fundamental de la pseudonimización sin identidad estable.** Pero debe documentarse como limitación conocida:

> *"El derecho al olvido opera sobre identidades resueltas. Si un dispositivo cambia de identidad primaria (MAC → hostname → IP) entre períodos, cada identidad genera un `anon_id` independiente. El borrado de una identidad no alcanza a los `anon_id` derivados de identidades alternativas del mismo dispositivo. La mitigación es política, no técnica: las instalaciones deben mantener inventario de dispositivos autorizados con MAC estática."*

---

## Resumen de acciones para aprobación final

| Item | Severidad | Acción |
|------|-----------|--------|
| OQ-1 → D9 | **Bloqueante** | Convertir pregunta en decisión: cola filesystem + reintento + retención 90 días |
| `:PREVIOUS_IDENTITY` vs. array | Importante | Documentar implicación de recursividad, o considerar array de previous_ids |
| Ontología definitiva vs. WIP | Menor | Clarificar si D5 es MVP-FEDER o punto de partida |
| `dst_port_class` numérico | Optimización | Considerar int8 enum |
| GDPR fallback identities | Menor | Añadir nota de limitación en D8 |

---

**Veredicto preliminar:** A una enmienda de OQ-1, este ADR está listo para pasar a estado **Aprobado — Consejo de Sabios** y puede ser referenciado como autoridad arquitectural por ADR-035, ADR-038, y el paper v20.

**¿Quieres que proponga el texto exacto de D9 para cerrar OQ-1?**