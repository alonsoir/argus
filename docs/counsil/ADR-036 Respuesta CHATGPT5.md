Evaluación directa: este ADR está **muy bien planteado conceptualmente**, pero aún no está listo para ejecutarse sin riesgo de sobrecoste, bloqueo o deriva académica sin impacto práctico. La base es sólida; faltan decisiones de alcance más agresivas.

---

# Veredicto global

**CONDICIONAL — aprobar como dirección estratégica, pero reducir alcance y endurecer foco**

Tal como está, el ADR es correcto pero **demasiado ambicioso para un solo desarrollador** en un proyecto operativo.

---

# Puntos fuertes (muy buenos)

### 1. Momento elegido: correcto

Plantearlo como **última fase** es exactamente lo adecuado:

* arquitectura estable
* invariantes ya descubiertas (seed_family, fail-closed, etc.)

Esto evita el error clásico: intentar verificar código que aún cambia.

---

### 2. Separación C / C++ muy acertada

* C → formal real (Frama-C / modelo matemático)
* C++ → “formal-ish” (sanitizers + contratos)

Esto es realista y alineado con la industria.

---

### 3. Checklist excelente

El checklist adaptado es **de nivel profesional alto**:

* especialmente buenos: 6 (modelo de entorno), 7 (aislamiento), 9 (bucles)

Esto sí es reutilizable y valioso.

---

### 4. Propiedades bien elegidas

Las P1–P5 son correctas y relevantes:

* P2 (fail-closed) y P3 (seed invariant) son especialmente críticas

---

# Problemas críticos (donde debes actuar)

## 1. ❌ Alcance demasiado amplio (riesgo de no terminar nunca)

Estás intentando verificar:

* múltiples componentes
* dos variantes (A y C)
* concurrencia (sniffer)
* ML (ml-detector)

Esto en la práctica → **6–12 meses se convierten en 18–24 o abandono**

---

### Corrección obligatoria: reducir a “núcleo verificable”

Define explícitamente:

```text
FORMAL CORE (v1):
- seed_client
- crypto-transport
- plugin_loader (parcial)
```

TODO lo demás:

```text
OUT OF SCOPE v1
```

---

## 2. ❌ Mezcla de objetivos: seguridad vs certificación

Estás mezclando:

* verificación técnica
* objetivos de certificación (IEC, CC, etc.)

### Problema:

Cada certificación implica procesos organizativos, no solo técnicos.

---

### Corrección:

Separar claramente:

```text
ADR-036 → verificación técnica
ADR-037 (futuro) → certificación
```

---

## 3. ❌ Propiedad P5 (terminación del pipeline) es inviable

```text
∀ input_rate ≤ MAX_MBPS: pipeline terminates within bounded time
```

### Problema:

Esto implica:

* análisis de rendimiento
* concurrencia
* IO
* kernel

→ **no es verificable formalmente en este contexto**

---

### Corrección:

Eliminar o degradar a:

```text
P5' — Terminación de funciones críticas aisladas
```

---

## 4. ❌ Frama-C en código “mixto” C/C++ puede bloquearte

Frama-C funciona bien en:

* C puro
* código controlado

No en:

* wrappers C++ complejos
* código híbrido sin aislamiento claro

---

### Corrección obligatoria:

Crear capa explícita:

```text
C verification boundary:
- funciones C puras
- sin STL
- sin exceptions
```

---

Claro, continúo y cierro el análisis.

---

## 5. ❌ Variante C (seL4) está inflando el ADR (continuación)

### Problema real

Incluir seL4 aquí introduce:

* otro modelo mental (capabilities)
* otra toolchain
* otro tipo de pruebas (proof obligations)

→ duplica complejidad sin aportar valor inmediato al pipeline actual.

### Corrección obligatoria

```text
ADR-036 scope:
→ SOLO Variante A (Linux + AppArmor)

Variante C:
→ ADR separado (ADR-0XX-seL4-verification)
→ tratado como investigación
```

---

## 6. ❌ Falta definición de “qué es suficiente”

Ahora mismo no hay criterio claro de cierre.

### Problema

Puedes estar verificando indefinidamente sin saber cuándo parar.

### Corrección

Definir un **Definition of Done formal**:

```text
DONE cuando:
- P1, P2, P3 demostradas formalmente
- 0 warnings + 0 ASan + 0 UBSan en P0
- 100% funciones críticas anotadas con contratos
- Frama-C WP sin obligaciones pendientes en core
```

---

# Respuestas a las preguntas (OQ-1 a OQ-4)

---

## OQ-1 — Frama-C vs CBMC

### Veredicto: **CONDICIONAL (usar ambos, con roles distintos)**

### Recomendación técnica

* **Frama-C/WP** → invariantes, contratos, propiedades globales
* **CBMC** → propiedades concretas tipo:

    * buffer overflow
    * límites de arrays
    * casos edge

Uso ideal:

```text
Frama-C → demostrar que el sistema es correcto
CBMC → demostrar que no rompe en casos concretos
```

### Riesgo si no se hace así

Frama-C solo → demasiado pesado
CBMC solo → cobertura incompleta

---

## OQ-2 — Verificación formal en C++20

### Veredicto: **ACEPTAR limitación (no hay tooling maduro suficiente)**

### Recomendación técnica

Para C++:

1. Sanitizers obligatorios:

    * ASan
    * UBSan
2. clang-tidy (subset de reglas, no “*”)
3. Contratos manuales (como propones)

Opcional (muy recomendable):

* `-fno-exceptions` en partes críticas si es viable
* wrappers C para lógica crítica

### Riesgo si se ignora

Intentar verificación formal completa en C++ → bloqueo del proyecto

---

## OQ-3 — Certificación realista

### Veredicto: **IEC 62443 (realista) + ENS (necesario en España)**

### Recomendación técnica

* **Primario:** IEC 62443-4-2
* **Complementario:** ENS (Esquema Nacional de Seguridad)
* **NO objetivo inmediato:** Common Criteria (demasiado costoso)

### Nota importante

Para hospitales europeos:

* certificación ≠ adopción
* documentación + hardening + reproducibilidad pesan más

### Riesgo si se ignora

Perseguir Common Criteria → consume años sin retorno práctico

---

## OQ-4 — Variante A vs C

### Veredicto: **SEPARAR — Variante C como investigación**

### Recomendación técnica

```text
Variante A:
→ producción
→ verificación formal completa

Variante C:
→ paper
→ prototipo
→ no bloquea roadmap principal
```

### Riesgo si se ignora

Diluir esfuerzo → no cerrar ninguna de las dos correctamente

---

# Recomendación estructural final

## ADR-036 (versión corregida)

### Scope realista:

```text
IN SCOPE:
- seed_client (completo)
- crypto-transport (core)
- plugin_loader (fail-closed path)

OUT OF SCOPE:
- sniffer (concurrencia)
- ML
- RAG
- etcd
- Variante C
```

---

## Orden de ejecución recomendado

1. seed_client → P1 + P3
2. crypto-transport → integridad + key derivation
3. plugin_loader → P2

Solo si esto se completa:
→ expandir scope

---

# Evaluación final

## Nivel del ADR

* Conceptualmente: **alto**
* Ejecutabilidad actual: **media (requiere ajuste)**

---

## Lo más valioso que has hecho aquí

Has identificado correctamente que:

> “hay un punto donde el software debe demostrar que es correcto”

Eso no es común en proyectos open-source de este tipo.

---

## Riesgo principal ahora mismo

No es técnico, es estratégico:

> intentar hacer verificación formal “completa” en lugar de “suficiente”

---

# Conclusión clara

Si reduces el scope como se indica:

→ puedes conseguir una **baseline formal real** (muy valiosa, publicable, útil)

Si mantienes el scope actual:

→ alto riesgo de no terminar o generar documentación sin garantías reales

---

Si quieres, puedo devolverte el ADR-036 ya reescrito en versión **“aprobable por el Consejo”**, con scope reducido y Definition of Done claro.

