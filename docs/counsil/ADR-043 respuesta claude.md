## Revisión del Consejo de Sabios — Claude
### ADR-0043 v3 — Memoria Episódica Distribuida con Coherencia Temporal

---

### Veredicto general

**APROBADO.** La v3 cierra todas las condiciones que puse en v2 y absorbe correctamente el dictamen del Consejo. Es el documento más sólido de las tres versiones y puede pasar a estado `Aceptado` sin nuevas rondas de revisión, con una salvedad menor que detallo abajo.

---

### Lo que la v3 resuelve correctamente respecto a v2

**C1 resuelta**: `DEBT-KPSEUDO-ROTATION-MIGRATION-001` registrada, y además se añade el mecanismo de key versioning con `:PREVIOUS_IDENTITY` que hace la rotación menos catastrófica. Mejor de lo que pedí.

**C2 resuelta**: OQ-1 registrada formalmente. No se resuelve en este ADR (correcto, no hay datos reales aún) pero ya no es un agujero silencioso.

**C3 resuelta**: la ontología mínima viable aparece en D5 antes del schema Parquet, y los próximos pasos invierten el orden correctamente: ontología primero, schema después.

**El hallazgo de Kimi sobre DHCP** está absorbido de forma limpia. La jerarquía MAC → hostname → IP con la distinción semántica `Host` vs `NetworkPresence` es exactamente la solución correcta. Y la explicación de por qué la MAC no conflictúa con GDPR (lo que viaja es `HMAC(K_pseudo, MAC)`, no la MAC) está bien argumentada y es legalmente defensible.

**La eliminación de `PRECEDES`** es una mejora real del modelo de grafo. Menos aristas materializadas, queries más simples, mismo poder expresivo.

---

### Una salvedad menor

El campo `installation_id` en D4d se especifica como "identificador opaco generado por Jenkins". Correcto. Pero el schema Parquet candidato no incluye ese campo en ninguno de los dos ficheros. Si el servidor central recibe un fichero Parquet sin `installation_id` embebido, la única forma de saber a qué instalación pertenece es por el nombre del fichero o por los metadatos JSON del batch.

Eso es frágil: si el fichero Parquet se desacopla de su batch JSON por cualquier razón (reenvío parcial, procesamiento manual, auditoría futura), pierde su contexto de instalación. Recomiendo añadir `installation_id` y `node_id` como columnas en ambos Parquet. Son metadatos de partición, no datos personales, y hacen el fichero autocontenido.

---

### Observaciones de otros miembros del Consejo que merecen atención específica

**Qwen — jerarquía HKDF para K_pseudo**: la propuesta de derivar `K_pseudo_host`, `K_pseudo_flow`, `K_pseudo_model` desde una `K_root` es elegante y alineada con NIST SP 800-108. La v3 no la incorpora, y es razonable no hacerlo: añade complejidad en la primera implementación. Pero merece registrarse como mejora futura, especialmente para instalaciones de alto valor (hospitales universitarios, municipios grandes). Propongo `DEBT-KPSEUDO-HKDF-HIERARCHY-001` como deuda de baja prioridad para no perder el concepto.

**DeepSeek — almacenamiento duradero de batches crudos antes de ingesta Neo4j**: el punto es válido. Si el pipeline de ingesta falla a mitad de un batch, hay que poder reprocesarlo sin pedirle al nodo edge que reenvíe. La idempotency_key de D4a resuelve el reenvío, pero no resuelve el caso donde el batch llegó, se almacenó parcialmente, y el ingestor falló. Un almacenamiento duradero de batches crudos en el servidor central (antes de tocar Neo4j) convierte el sistema en event-sourcing real: Neo4j puede reconstruirse desde cero a partir de los batches si fuera necesario. Esto no bloquea nada ahora, pero debería aparecer en el diseño del paso 5 de próximos pasos.

**Mistral — ataque de repetición**: la mitigación propuesta (nonce + validación de `period_start/end`) es correcta y complementa la idempotency_key. Un batch con firma válida pero con período fuera del rango esperado debería rechazarse. Esto puede añadirse como regla de validación en el pipeline de ingesta del servidor central sin cambiar el ADR.

---

### Resumen

| Item | Estado |
|------|--------|
| C1 v2: migración K_pseudo | ✅ Resuelto |
| C2 v2: conectividad intermitente | ✅ Registrado como OQ-1 |
| C3 v2: ontología antes de schema | ✅ Resuelto |
| Hallazgo Kimi: identidad bajo DHCP | ✅ Resuelto |
| Salvedad menor: installation_id en Parquet | Pendiente, no bloqueante |
| DEBT-KPSEUDO-HKDF-HIERARCHY-001 | Sugerido, baja prioridad |
| Almacenamiento duradero de batches crudos | A incorporar en diseño del paso 5 |

El documento está listo para `Aceptado`. La salvedad del `installation_id` en Parquet puede resolverse en el momento de implementar `DEBT-PARQUET-SCHEMA-001` sin necesidad de una v4.

---

*Claude — Consejo de Sabios, DAY 147*
*Via Appia Quality*