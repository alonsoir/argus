**REVISOR: Grok (xAI) — cs.CR / sistemas distribuidos**  
**FECHA: 2 de abril de 2026**

**VEREDICTO GLOBAL ADR-023 PHASE 2a:** **ACCEPTED CON CONDICIONES** (Gate TEST-INTEG-4a pasa, pero con mejoras obligatorias antes de cerrar PHASE 2a y avanzar a 2b).

**HALLAZGOS CRÍTICOS (bloquean cierre definitivo de PHASE 2a):**
- Q1: La validación D8 por comparación de punteros (`ctx.payload == snap_payload`) **no es suficiente**. Un plugin malicioso (o con bug) puede modificar el contenido del buffer sin cambiar el puntero. Debe añadirse comparación de contenido (memcmp o hash rápido) para los campos marcados como read-only.
- Q2: TEST-INTEG-4a **no es suficiente** como gate completo de PHASE 2a porque el camino crítico de `plugin_process_message()` + D8 nunca se ejecuta. Se necesita un plugin de test dedicado que exporte el símbolo y fuerce el flujo completo (incluyendo result_code != 0).

**HALLAZGOS RECOMENDADOS (mejoras fuertes, no bloquean pero muy aconsejables):**
- Q3: Documentar explícitamente en `plugin_api.h` que `nonce` y `tag` **pueden ser nullptr** en modos de test/configuración temprana. En producción deben ser siempre válidos (o el host debe fallar antes).
- Q5: `reserved[60]` es **suficiente** para los campos mencionados (32 pk + 8 session_id + 4 flags + padding), pero recomiendo subirlo a **reserved[64]** (alineación natural) y documentar la semántica exacta que ADR-024 usará (para evitar sorpresas en el layout).
- Q4: Sí, aplicar la dependencia explícita `plugin-loader-build` a **todos** los componentes (sniffer, ml-detector, rag-ingester, rag-security). Las dependencias implícitas en Make son frágiles; mejor explicitarlas para evitar races en builds paralelos o CI.

### RESPUESTAS A PREGUNTAS ESPECÍFICAS

**Q1:** No es suficiente.  
La comparación de punteros solo detecta si el plugin reasignó el puntero (cosa que el contrato ya prohíbe). No detecta modificaciones *in-place* del buffer (ej. overwrite de bytes, cambio de datos sensibles, etc.).  
**Recomendación:**
- Hacer snapshot de contenido (al menos de los primeros N bytes o un hash rápido tipo xxHash o SipHash).
- O mejor: copiar el payload read-only a un buffer temporal antes de llamar al plugin y comparar después.  
  Esto es estándar en sistemas de plugins de seguridad (evita TOCTOU y modificaciones silenciosas).

**Q2:** No es suficiente.  
El gate actual solo valida la degradación D1 (caso sin símbolo), pero la parte más crítica de PHASE 2a es el flujo completo con `plugin_process_message()` + validación post-invocación (D8) + manejo de `result_code != 0` → `std::terminate()`.  
**Acción obligatoria:** Crear un plugin de test `test-process-message` que exporte el símbolo, modifique annotation/result_code, y (opcionalmente) intente violar invariants read-only. Ejecutarlo en TEST-INTEG-4a o crear TEST-INTEG-4a-full.

**Q3:** Sí, debe documentarse explícitamente.  
En modo test (sin decrypt/etcd) es razonable que `nonce` y `tag` sean `nullptr`. Pero en producción esto no debe ocurrir nunca.  
**Propuesta de texto para el header:**
```c
/* 
 * nonce y tag:
 * - En producción: siempre apuntan a buffers válidos (12 y 16 bytes).
 * - En test/config mode: pueden ser nullptr (host no ha hecho decrypt aún).
 * El plugin NO debe desreferenciarlos si son nullptr.
 * Host valida antes de cifrar/descifrar.
 */
const uint8_t* nonce;   // 12 bytes o nullptr en test
const uint8_t* tag;     // 16 bytes o nullptr en test
```

**Q4:** Mejor hacerlas explícitas en el Makefile.  
Dependencias implícitas funcionan hasta que no lo hacen (builds paralelos `-j`, CI con caché, cambios en orden de targets). Añadir la dependencia a los cuatro componentes restantes evita dolores de cabeza futuros y hace el build más predecible.

**Q5:** Suficiente en tamaño, pero revisa antes.  
32 (X25519 pubkey) + 8 (session_id) + 4 (flags) + algo de padding = cabe en 60.  
Sin embargo, subir a `reserved[64]` es más limpio (alineación a 8 bytes) y deja margen para campos futuros sin romper ABI.  
Documenta en comentario:
```c
// reserved[64] — forward compatibility con ADR-024 (Noise session data)
```

### POSICIÓN DE MINORÍA (si aplica)
- Ser más estricto con D8: además de snapshot, añadir una **canary** o checksum simple dentro de `MessageContext` que el host verifica antes y después. Ayuda contra plugins que intentan corrupción sutil.
- En TEST-INTEG-4a incluir **ambos** casos: plugin sin símbolo + plugin con símbolo (incluso si es un stub mínimo).

**Conclusión y recomendación al árbitro (Alonso):**

PHASE 2a está muy cerca de estar sólida. El código implementado sigue el espíritu de las decisiones consolidadas del día anterior, pero la validación D8 y la cobertura del gate necesitan reforzarse antes de declarar PHASE 2a cerrada.

**Acciones mínimas para cerrar PHASE 2a:**
1. Mejorar D8 con comparación de contenido (o snapshot de buffer).
2. Añadir plugin de test que ejecute `plugin_process_message()` y valide D8.
3. Documentar nullptr en nonce/tag + subir reserved a 64 si quieres.
4. Propagar dependencia explícita del plugin-loader a todos los componentes.

Una vez hecho esto, TEST-INTEG-4a pasa con nota alta y se puede avanzar a PHASE 2b (rag-ingester).

Sigue muy bien el proyecto, compañero. El nivel de paranoia en el contrato del plugin y las invariants es el correcto para un NDR orientado a entornos sensibles.

¿Quieres que te proponga código concreto para el snapshot D8 mejorado, el plugin de test, o el texto exacto para actualizar `plugin_api.h` y el ADR?

Estoy aquí para la siguiente ronda cuando quieras. ¡Vamos por buen camino!