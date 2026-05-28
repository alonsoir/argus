**Consejo de Sabios — Respuesta Day 164**

Entendido el resumen del Day 163. Buen catch y fix quirúrgico. El `sed` fue efectivo, pero refuerza que este tipo de regresiones son síntoma de deuda estructural en el CMake.

---

### Respuestas del Consejo

**1. Patrón CMake para targets condicionales**

Recomendamos **fuertemente** el guard `if(NOT TARGET <nombre>)` como **invariante obligatorio** en todos los bloques condicionales que definan targets.

Razones:
- Es más resiliente a reorganizaciones futuras de los CMakeLists.
- Permite mantener un único nombre canónico (`test_ntp_health_check`) en todo el proyecto, lo que simplifica la lectura y los `add_dependencies`, `target_link_libraries`, etc.
- Evita proliferación de nombres (`_vault`, `_enterprise`, `_extra`…) que terminan siendo ruido cognitivo.
- Es el patrón que usa la mayoría de proyectos grandes (incluyendo partes de LLVM, Qt, etc.).

**Decisión del Consejo**:  
Adoptar como estándar el guard `if(NOT TARGET xxx)` + comentario claro encima del bloque.  
Crear ticket `DEBT-CMAKE-GUARD-PATTERN-001` y aplicarlo retroactivamente a todos los targets condicionales en las próximas dos semanas.

La alternativa de nombres distintos solo se acepta cuando hay diferencias semánticas reales en el comportamiento del target (no solo en la configuración).

**2. BACKLOG-CRYPTO-VENDOR-KEY-001 — scope Day 164**

La **Fase 1 se considera cerrada** cuando:
- `vendor.key` ya no existe en el repositorio (ni en history, idealmente con un commit de purga si fue sensible).
- La clave pública se lee **exclusivamente** desde la variable de entorno `ARGUS_VENDOR_PUBKEY_HEX` en Jenkins.
- El código fallback a SeedFileProvider está eliminado o claramente deprecado con warning en runtime.
- AppRole por componente (Jenkins) está **implementado y probado** en el entorno de staging (no necesariamente en prod aún).

Si mañana solo conseguís mover la clave y leerla desde la variable, pero el AppRole queda pendiente, marcad la tarea como **"Fase 1.1 completada"** y dejadla en **Review** hasta tener el AppRole. No mergeéis a main con AppRole pendiente si el roadmap de 8 fases tenía veto explícito.

**Recomendación**: Intentad cerrar las dos cosas (lectura + AppRole básico) en el Day 164. Es más seguro cerrar el ciclo completo.

**3. EMECAS++ Acto I — cobertura enterprise**

**Posición del Consejo**:  
El Acto I actual (compila + unitarios con `ARGUS_VAULT_ENABLED=ON`) es **suficiente** por ahora.

Razones:
- El Modelo B efímero todavía usa `SeedFileProvider` porque el flujo completo de Vault (AppRole + vendor-key + token renewal) aún no está listo.
- Forzar `VaultProvider` real en Acto I antes de cerrar BACKLOG-CRYPTO-VENDOR-KEY-001 generaría tests flaky o que requieran Vault de staging en cada run.

**Criterio de salida propuesto para Acto I completo**:
- Compila con la flag ON.
- Todos los unitarios relevantes pasan.
- Existe **al menos un test E2E** (puede ser en Acto II) que valide el camino feliz de `VaultProvider` + vendor key desde entorno.

Cuando cerréis la tarea de vendor-key + AppRole, subid el Acto I a exigir `VaultProvider` real.

---

### Recomendaciones adicionales para Day 164

- Al mover `vendor.key` → Vault, considera hacer un commit separado de “security: remove vendor.key plaintext” para que quede claro en el historial.
- Documenta en el README de crypto/ o en el ADR correspondiente el nuevo flujo de claves.
- Si podéis, dejad preparado el skeleton del `DEBT-CONFIG-JINJA2-PIPELINE-001` aunque no lo completéis.

**Pregunta de vuelta del Consejo**:  
¿Tenéis ya claro el nombre del secreto en Vault (`secret/argus/enterprise/vendor-key` o `secret/data/argus/...` con KV v2)? Esto afecta cómo montáis el AppRole + policy.

Estamos listos para el próximo update.

¡Buen avance hoy!