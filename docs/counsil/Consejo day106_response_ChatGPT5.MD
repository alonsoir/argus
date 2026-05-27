El DAY 106 cierra correctamente los huecos de PHASE 2a. La incorporación de D8-v2 y el plugin de test específico elevan el nivel de garantía de forma clara. Paso a responder a las tres preguntas.

---

# **Q1 — PHASE 2b (rag-ingester)**

**Respuesta:**
Seguir el mismo patrón base (los “tres puntos”) es correcto, pero **rag-ingester necesita dos adaptaciones específicas**.

### Patrón que SÍ se mantiene

* `MessageContext` como contrato único
* `plugin_process_message()` como punto de entrada
* D8/D8-v2 aplicado igual (antes/después)

---

### Ajustes necesarios para rag-ingester

**1. Boundary claro antes de FAISS**
El plugin debe ejecutarse **antes de cualquier operación de ingestión en FAISS**.

Motivo:

* Evitar que datos corruptos o manipulados entren en el índice
* Permitir rechazo temprano (fail-fast)

---

**2. Inmutabilidad fuerte del payload**
En firewall el riesgo es decisión → acción
En rag-ingester es **persistencia → propagación**

Por tanto:

* El payload no solo debe ser “no modificado”
* Debe considerarse **input crítico de indexación**

Recomendación:

* Tratar cualquier violación D8 como **hard reject del documento**

---

**3. Control de tamaño / estructura**
FAISS puede amplificar problemas si recibe input inválido.

Añadir en rag-ingester:

* validación de tamaño máximo
* validación de formato antes de indexar

---

**Conclusión Q1**

✔ Reutilizar patrón
⚠ Añadir pre-ingest validation boundary
⚠ Endurecer política ante violaciones (rechazo total)

---

# **Q2 — CRC32 en Release**

**Respuesta corta:**
Sí, pero **no CRC32**. Mantener una versión más barata.

---

### Evaluación actual

* CRC32 en debug → correcto
* En release → coste innecesario en hot path

---

### Recomendación

En Release mantener:

```text
pointer identity check
+ length check
+ (opcional) canary ligero
```

Ejemplo conceptual:

* guardar `payload_len` snapshot
* verificar:

  * mismo puntero
  * mismo tamaño

---

### Alternativa intermedia (si quieres más seguridad)

* CRC32 muestreado (ej: 1 de cada N mensajes)
* o solo para payloads pequeños

---

### Importante

El sistema ya tiene:

* firma criptográfica previa (ADR-025)
* boundary de entrada confiable

Por tanto:
👉 D8 en runtime es **detección de comportamiento malicioso del plugin**, no integridad de origen

---

**Conclusión Q2**

✔ Debug: CRC32 completo
✔ Release: pointer + length (ligero)
✔ Opcional: muestreo si quieres más cobertura

---

# **Q3 — test_config.json vs factory**

**Respuesta:**
Formalizar `test_config.json` como patrón estándar.

---

### Por qué es la decisión correcta ahora

**Ventajas actuales:**

* Aislamiento total de producción
* Reproducibilidad inmediata
* Bajo coste cognitivo
* Debug sencillo

---

### Problema de una factory ahora

* Añade complejidad prematura
* Introduce lógica de generación (más superficie de bugs)
* Menos transparente para debugging

---

### Cuándo sí tendría sentido una factory

* Cuando tengas:

  * decenas de plugins
  * combinaciones complejas de config
  * tests parametrizados masivos

Ahora mismo:
👉 Estás en fase de arquitectura, no de escalado masivo de tests

---

**Recomendación concreta**

Formalizar convención:

```text
/plugins/<plugin_name>/test_config.json
/plugins/<plugin_name>/test_variants.cpp
```

Y añadir:

* regla: nunca tocar configs de producción
* ejecución aislada obligatoria

---

# Observación adicional (importante)

## D8-v2 con CRC32

Muy buen movimiento. Solo un matiz:

* CRC32 es **detectable pero no resistente a colisiones**
* aquí es suficiente (no es mecanismo criptográfico)

Pero deja claro en ADR-023 o docs:

> “CRC32 is used for accidental/malicious mutation detection, not for cryptographic integrity”

---

# Evaluación final DAY 106

* PHASE 2a: **cerrada correctamente**
* D8: **ya es un mecanismo real, no simbólico**
* Testing: **muy bien enfocado (variants A/B/C)**
* ADR-025 + implementación: **coherentes entre sí**

---

# Veredicto del Consejo

* PHASE 2b puede comenzar sin bloqueos
* No hay deuda crítica pendiente
* Las decisiones tomadas escalan bien hacia fases posteriores

---

Si quieres, el siguiente paso lógico sería revisar **rag-ingester antes de tocar código**, porque ahí es donde el modelo cambia (de firewall reactivo a persistencia semántica), y es donde suelen aparecer errores sutiles.
