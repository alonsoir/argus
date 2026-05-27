## DeepSeek — Retroalimentación DAY 105 (Implementación ADR-023 PHASE 2a)

La implementación en `firewall-acl-agent` y el gate TEST-INTEG-4a representan el primer paso real de la migración a la arquitectura multicapa de plugins. El trabajo es sólido, pero las preguntas planteadas revelan puntos que deben refinarse antes de extender la misma estrategia a otros componentes.

---

### Respuestas a las preguntas del Consejo

**Q1 — Snapshot D8: comparación de punteros vs contenido byte a byte**

**Recomendación:** La comparación de punteros **no es suficiente**. Debe complementarse con una comprobación de integridad del contenido.

**Razonamiento:**
- Comparar punteros detecta si el plugin modificó el puntero (`payload` apuntando a otra región), pero **no detecta** modificaciones in-place dentro del buffer apuntado. Un plugin malicioso o con errores podría escribir dentro del buffer sin cambiar el puntero, y D8 no lo detectaría.
- La modificación in-place es el riesgo real, porque el componente host reutiliza ese buffer (por ejemplo, para enviar el mensaje cifrado).
- **Solución propuesta:** Mantener la comparación de punteros (rápida) y añadir **una checksum o hash** (ej. CRC32 o SHA-256) del buffer antes y después de la invocación, calculada por el host. La comparación de hashes es más costosa, pero el gate TEST-INTEG-4a puede ejecutarla solo en modo debug/testing. En producción, se puede desactivar o ejecutar muestreo.

**Acción:** Añadir a D8: *"Post-invocation validation SHALL include either (a) a byte-by-byte comparison of the payload buffer (testing/debug) or (b) a cryptographic hash comparison (production, optional). Pointer comparison alone is insufficient."*

---

**Q2 — Suficiencia de TEST-INTEG-4a con hello plugin que no exporta `plugin_process_message`**

**Recomendación:** **No es suficiente.** Se requiere un plugin de test que exporte el símbolo para validar D8 y la política de degradación D1 en el caso de error.

**Razonamiento:**
- El gate actual solo verifica que el componente no crashea cuando el plugin no implementa la función de cifrado (caso de degradación elegante).
- No verifica el contrato de `MessageContext` (campos read-only, modificación de `result_code`, etc.).
- Tampoco verifica que `result_code != 0` provoca `std::terminate()` (fail-closed).

**Solución propuesta:** Añadir un plugin de prueba (ej. `libplugin_test_crypto.so`) que:
- Exporte `plugin_process_message`
- En una primera variante, devuelva siempre 0 (éxito) y no modifique nada → debe pasar.
- En una segunda variante, modifique un campo read-only (ej. `direction`) → el host debe detectarlo y fallar (con D8 mejorado).
- En una tercera variante, devuelva `result_code = -1` → el host debe llamar a `std::terminate()` (comprobar con un test que lanza señal SIGABRT).

**Acción:** Crear `TEST-INTEG-4a-advanced` que use este plugin de prueba y ejecutarlo como gate adicional antes de dar por validado PHASE 2a.

---

**Q3 — `nonce` y `tag` `nullptr` en test-config mode**

**Recomendación:** El contrato debe documentar explícitamente que estos punteros pueden ser `NULL` en contextos donde no hay cifrado (tests, modos de diagnóstico). En producción, nunca deben ser `NULL`.

**Razonamiento:**
- El contrato actual no especifica el comportamiento cuando `nonce` o `tag` son `NULL`. Un plugin que intente leerlos sin comprobar causaría segfault.
- Es legítimo tener modos de test donde el cifrado no está disponible (ej. pruebas unitarias que no requieren el stack completo).

**Solución propuesta:** Añadir en `plugin_api.h` un comentario:
```c
/* WARNING: In production, nonce and tag are never NULL.
 * In test/debug configurations (e.g., when MLD_TEST_CONFIG_MODE=1),
 * they may be NULL. Plugins MUST check for NULL before dereferencing. */
```

**Acción:** Documentar esta condición en el ADR-023 y en el código.

---

**Q4 — Dependencia explícita de plugin-loader en otros componentes**

**Recomendación:** **Sí, deben tener la misma dependencia explícita** en el Makefile principal, o bien el sistema de builds de cada componente debe garantizar el orden mediante una dependencia común.

**Razonamiento:**
- El problema de orden de instalación (plugin-loader debe estar compilado antes de que los componentes intenten enlazar con él) es general, no solo para `firewall-acl-agent`.
- Si `sniffer`, `ml-detector`, etc. ya tienen la dependencia implícita (por ejemplo, porque el `CMakeLists.txt` de esos componentes usa `find_library` y falla si no existe), entonces el Makefile no necesita explicitarla; pero el orden de compilación en el Makefile principal debe garantizar que `plugin-loader` se construye antes que cualquier componente que lo use.

**Solución propuesta:** Revisar el Makefile principal (`/Makefile`) y asegurar que la receta `plugin-loader` se ejecuta antes que `firewall`, `sniffer`, `ml-detector`, etc. Actualmente, es probable que el orden esté bien por la lista de dependencias, pero conviene explicitarlo con una variable `COMPONENTS_ORDER` o con dependencias `: plugin-loader` en cada componente.

**Acción:** Añadir en el Makefile: `firewall: plugin-loader` (y similar para los demás) para hacer explícito el orden. No solo para `firewall`.

---

**Q5 — Tamaño de `reserved[60]` para ADR-024**

**Recomendación:** 60 bytes es suficiente para las necesidades actuales de ADR-024, pero conviene documentar la asignación prevista para evitar conflictos.

**Razonamiento:**
- ADR-024 requiere: X25519 public key (32 bytes), session_id (8 bytes), flags (4 bytes) = 44 bytes. Sobran 16 bytes para futuras extensiones.
- El tamaño es adecuado. El riesgo no es el tamaño, sino que dos versiones de ADR-024 puedan interpretar los mismos bytes de forma diferente.

**Solución propuesta:** En el ADR-024 (cuando se especifique), definir un layout concreto para los primeros 44 bytes de `reserved`, por ejemplo:
```c
/* reserved[0..31]  : X25519 public key (if used) */
/* reserved[32..39] : session_id (uint64_t) */
/* reserved[40..43] : flags (uint32_t) */
/* reserved[44..59] : reserved for future use */
```  
De esta forma, diferentes implementaciones de ADR-024 pueden coexistir sin conflicto, siempre que respeten el layout.

**Acción:** Añadir esta especificación de layout en el ADR-024 (borrador) y referenciarla en ADR-023 como "reserved layout defined in ADR-024".

---

### Resumen de hallazgos y acciones recomendadas

| ID | Hallazgo | Acción | Prioridad |
|----|----------|--------|-----------|
| F1 | D8 (snapshot pointer) es insuficiente | Mejorar D8 con checksum/hash del contenido | 🔴 Alta (antes de extender a otros componentes) |
| F2 | TEST-INTEG-4a no valida el comportamiento de `plugin_process_message` | Crear plugin de prueba con variantes (éxito, modificación ilegal, error) | 🔴 Alta |
| F3 | `nonce`/`tag` pueden ser NULL en test | Documentar en API y ADR | 🟡 Media |
| F4 | Dependencias de plugin-loader no explícitas en Makefile | Añadir dependencias explícitas en todos los componentes | 🟡 Media |
| F5 | `reserved[60]` tamaño suficiente, pero falta layout | Especificar layout en ADR-024 | 🟢 Baja (no bloqueante) |

---

### Veredicto sobre la implementación actual

- **Aspectos positivos:** D1 (degradación elegante), D2/D3 (contrato de campos), D10 (modo desarrollo) están bien implementados. El gate TEST-INTEG-4a es funcional y pasa.
- **Debilidades críticas:** La validación post-invocation (D8) es insuficiente, y el conjunto de pruebas no cubre el caso de uso real de un plugin de cifrado. **No se debe extender esta implementación a otros componentes (rag-ingester, etc.) sin resolver F1 y F2 primero.**

**Recomendación al equipo:**
1. Implementar las mejoras sugeridas para D8 (checksum) y crear el plugin de prueba con exportación de `plugin_process_message`.
2. Validar que el firewall-acl-agent se comporta correctamente (fail-closed en caso de error, modificación ilegal detectada).
3. Una vez validado, aplicar el mismo patrón a los siguientes componentes.

Con estos ajustes, la arquitectura estará sólida para PHASE 2a y el gate TEST-INTEG-4b (rag-ingester) será realmente significativo.

— DeepSeek, miembro del Consejo de Sabios