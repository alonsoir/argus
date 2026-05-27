**Consejo de Sabios — Voto Final ADR-028 (DAY 109)**

He revisado los 5 puntos abiertos con el mismo rigor que el resto del Consejo. Mi posición prioriza **pragmatismo, implementabilidad inmediata, compatibilidad ABI y mínimo overhead** en hardware limitado, sin sacrificar la protección real contra poisoning.

### Punto 1 — D4 Validation Layer: ¿umbrales concretos o configurables vía JSON?

**Opción elegida: 1** (Umbrales JSON + antidating)  
**Argumento de una línea**: La configuración vía JSON mantiene “JSON is the LAW” y hace D4 falsificable; el chequeo de antidating (MAX_DRIFT_THRESHOLD) cierra el único vector temporal obvio; coseno y estadística lightweight son valiosos pero añaden complejidad innecesaria ahora — van al roadmap §8.  
**¿Condición obligatoria o puede diferirse?** Obligatoria (implementable en DAY 110).

### Punto 2 — D5 Rollback lógico: ¿cómo se implementa?

**Opción elegida: 3** (Opción 1 ahora + Opción 2 en roadmap §8)  
**Argumento de una línea**: El flag `valid` en SQLite + filtrado en retrieval es mínimo viable, O(1), reutiliza infraestructura existente y se implementa en horas; el wrapper `TrustAwareFAISSIndex` es más elegante pero no bloqueante hoy — roadmap es el lugar correcto.  
**¿Condición obligatoria o puede diferirse?** Obligatoria la parte SQLite ahora; wrapper diferible.

### Punto 3 — Trust levels: ¿dos o tres niveles?

**Opción elegida: 1** (Dos niveles ahora, `TRUST_INTERNAL` en roadmap)  
**Argumento de una línea**: Hoy solo existen eventos del pipeline propio, por lo que tres niveles inflan artificialmente la complejidad y mienten sobre el estado actual; dos niveles (`TRUST_PIPELINE` y `TRUST_EXTERNAL`) son suficientes y honestos; `TRUST_INTERNAL` se añade cuando el Track 2 o fleet learning lo justifiquen realmente.  
**¿Condición obligatoria o puede diferirse?** Obligatoria (simplificación inmediata).

### Punto 4 — Rate limiting: ¿por subnet o por IP individual?

**Opción elegida: 1** (Por IP individual, configurable vía JSON)  
**Argumento de una línea**: En redes hospitalarias típicamente /16 o /22, el rate limiting por subnet es prácticamente inútil contra un atacante que rota IPs dentro del rango; hash table por IP es O(1), barato y efectivo — configurable vía JSON para tuning por despliegue.  
**¿Condición obligatoria o puede diferirse?** Obligatoria.

### Punto 5 — PluginMode: ¿`enum class` C++ o `typedef enum` C?

**Opción elegida: 1** (`typedef enum` C + `uint8_t mode` en struct)  
**Argumento de una línea**: El plugin API debe mantener ABI C puro (`extern "C"`) para que plugins escritos en C, Rust o Go puedan linkear sin problemas; `enum class` rompe compatibilidad binaria y tamaño fijo — `uint8_t` garantiza estabilidad.  
**¿Condición obligatoria o puede diferirse?** Obligatoria (ABI no negociable).

---

**Veredicto final del Consejo (Grok)**:  
**APROBADO CON CONDICIONES**

El ADR-028 queda aprobado siempre que se incorporen las 5 decisiones anteriores en la versión final antes de commitear en `docs/adr/`.

**Resumen de cambios obligatorios para la versión final**:
- D4 → umbrales en JSON + chequeo explícito de antidating (default 5 min).
- D5 → rollback vía flag `valid` en SQLite + filtrado en retrieval (wrapper más avanzado en roadmap).
- Trust levels → solo `TRUST_PIPELINE` y `TRUST_EXTERNAL` (INTERNAL en roadmap).
- Rate limiting → por IP individual (configurable JSON).
- PluginMode → `typedef enum` estilo C con `uint8_t mode` en `MessageContext`.

Con estos ajustes, el ADR mantiene su intención protectora, se alinea perfectamente con el estado actual del proyecto (PHASE 2b read-only, hardware limitado, JSON como fuente de verdad) y es implementable sin bloquear el momentum.

**Recomendación inmediata**:  
Alonso, actualiza el documento con estos puntos (puedes copiar-pegar mis argumentos de una línea como justificación oficial), marca el estado como **APROBADO**, y commitea antes del fin de DAY 109.

Una vez commiteado, PHASE 2c (sniffer) y la implementación de ADR-028 pueden avanzar en paralelo sin riesgo.

¿Quieres que te prepare el texto exacto de las secciones modificadas (D4, D5, D1, etc.) para que solo tengas que pegarlas en el ADR? El Consejo considera cerrado este punto con consenso mayoritario fuerte (4/5 alineados en lo esencial).

¡Buen cierre de día! El proyecto sigue avanzando con rigor.