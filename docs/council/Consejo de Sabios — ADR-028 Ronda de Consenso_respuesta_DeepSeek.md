## DeepSeek — Voto en ADR-028 Ronda de Consenso

Voy a votar con criterio propio, priorizando implementabilidad, honestidad técnica y coherencia con el resto del sistema. No me alineo automáticamente con ninguna facción.

---

### Punto 1 — D4 Validation Layer

**Opción elegida:** **Opción 1** (umbrales JSON + anti‑backdating)

**Argumento:**  
La similitud coseno (Opción 2) y la validación estadística (Opción 3) son caras y proclives a FPs en hardware limitado; merecen estudio separado (roadmap). La anti‑backdating es barata y necesaria. JSON configurabilidad es obligatoria.

**¿Condición obligatoria?** Sí. Sin umbrales concretos (configurables) el contrato no es falsificable.

---

### Punto 2 — D5 Rollback lógico

**Opción elegida:** **Opción 3** (SQLite `valid` flag ahora; wrapper en roadmap)

**Argumento:**  
El `valid` flag es suficiente para PHASE 2, es inmediato, no requiere reindexar FAISS y ya hay infraestructura SQLite. El wrapper `TrustAwareFAISSIndex` es deseable pero no bloqueante.

**¿Condición obligatoria?** No es condición para aprobar el ADR; se puede implementar en DAY 110 sin cambiar el diseño.

---

### Punto 3 — Trust levels

**Opción elegida:** **Opción 2** (tres niveles desde el principio)

**Argumento:**  
Aunque hoy `TRUST_INTERNAL` apenas se use, el coste de añadirlo ahora es cero (un campo en metadatos) y eliminarlo después sería caro. El ADR mira a largo plazo (Track 2, Fleet). No es “documentación que miente” – es preparación para evolución.

**¿Condición obligatoria?** No. Si el equipo prefiere dos niveles, no invalida el ADR; pero voto por tres.

---

### Punto 4 — Rate limiting

**Opción elegida:** **Opción 1** (por IP individual, configurable vía JSON)

**Argumento:**  
Rate limiting por subnet en una red hospitalaria `/16` es inútil (un atacante cambia de IP). IP individual es el estándar en WAF y sistemas anti‑flood. La Opción 2 (híbrido) añade complejidad sin beneficio real.

**¿Condición obligatoria?** Sí. Si se implementa solo por subnet, el ADR tendría un agujero de seguridad.

---

### Punto 5 — PluginMode

**Opción elegida:** **Opción 1** (`typedef enum` C + `uint8_t mode` en struct)

**Argumento:**  
`plugin_api.h` es C ABI puro (por `dlopen`). `enum class` no es compatible. La Opción 2 (cosmética) sería confusa para implementadores. El ADR debe reflejar la implementación real.

**¿Condición obligatoria?** Sí. La API debe ser correcta desde el primer commit.

---

### Veredicto final

**APROBADO CON CONDICIONES**

Las condiciones son:

1. **P1 (D4):** La validation layer debe tener umbrales JSON configurables (con valores por defecto documentados) y la validación anti‑backdating. Lo demás (coseno, estadística) va al roadmap §8.
2. **P4 (Rate limiting):** Debe ser por IP individual, no solo por subnet. Configurable vía JSON.
3. **P5 (PluginMode):** La API debe usar `typedef enum` C + `uint8_t mode` en `MessageContext`.

Los puntos **P2** y **P3** quedan a criterio del implementador (Opción 3 para rollback y cualquiera de las dos para trust levels) sin invalidar el ADR.

Una vez incorporados estos tres requisitos, el ADR-028 puede cerrarse y committearse.

— DeepSeek, miembro del Consejo de Sabios