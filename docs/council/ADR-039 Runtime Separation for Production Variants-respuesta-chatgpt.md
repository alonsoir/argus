## Consejo de Sabios — Revisión ADR-039

Evaluación bajo criterios de: seguridad estructural, reproducibilidad, auditabilidad y despliegue en entornos hospitalarios.

---

## Veredicto global

**Estado: ✅ APROBADO con ajustes menores (no bloqueantes)**

La decisión es **correcta para el contexto FEDER** y mantiene coherencia con los principios de seguridad definidos en ADR previos.

---

## P1 — ¿Opción B suficiente para FEDER?

**Respuesta: ✅ SÍ, suficiente (con condiciones)**

La Opción B cumple los objetivos clave:

* separación efectiva build/runtime
* eliminación de toolchain en producción
* pipeline reproducible para demo
* menor complejidad operativa

### Condición impuesta por el Consejo

Debe añadirse explícitamente:

> **Artefactos en `dist/` deben ser inmutables durante el ciclo de provisioning**

Recomendación:

* checksum (`sha256`) obligatorio
* fallo si mismatch en hardened VM

### Evaluación

* Opción A → correcta a largo plazo
* Opción B → correcta para deadline

No bloquea FEDER.

---

## P2 — Axioma de separación

**Respuesta: ✅ VÁLIDO y PUBLICABLE (con reformulación leve)**

El axioma es conceptualmente correcto, pero debe ajustarse para evitar ambigüedad científica.

### Versión recomendada (publicable)

> “A binary produced in a controlled build environment and deployed into a minimal runtime environment reduces attack surface compared to in-situ compilation, because the runtime environment cannot be repurposed for arbitrary code generation.”

### Justificación científica

* reducción de superficie de ataque → medible
* restricción estructural → verificable
* alineado con prácticas:

    * reproducible builds
    * supply chain security

---

## P3 — Flags de compilación

**Respuesta: 🟢 ADECUADOS (nivel producción real)**

Los flags definidos:

```id="sudn3t"
-O2 -DNDEBUG -fstack-protector-strong -fPIE -pie \
-D_FORTIFY_SOURCE=2 -fvisibility=hidden \
-Wl,-z,relro -Wl,-z,now
```

son correctos y alineados con:

* Debian hardening defaults
* prácticas industriales

### Recomendaciones del Consejo

1. **Añadir (si no rompe build):**

   ```bash
   -fstack-clash-protection
   ```

2. Evaluar:

   ```bash
   -fcf-protection=full   # (solo x86_64 moderno)
   ```

3. Confirmar:

    * binarios PIE efectivos (`checksec`)

---

## P4 — `-march=x86-64-v2` vs baseline

**Respuesta: ⚠️ RECOMENDACIÓN: usar `-march=x86-64`**

### Motivo principal: compatibilidad hospitalaria

Entornos hospitalarios reales incluyen:

* hardware antiguo (10–15 años)
* CPUs sin soporte v2 (SSE4.2, etc.)

### Riesgo de `x86-64-v2`

* binario no ejecutable en hardware legacy
* fallo silencioso en despliegue

### Recomendación final

| Contexto                       | Flag                |
| ------------------------------ | ------------------- |
| Producción hospitalaria        | `-march=x86-64`     |
| Optimización futura (opcional) | builds separados v2 |

---

## Observaciones adicionales del Consejo

### 1. Riesgo principal no cubierto

> Confianza implícita en VM de desarrollo

Mitigación mínima requerida:

* documentar claramente:

    * “trusted build environment assumption”
* añadir:

  ```bash
  make sign-production
  ```

  como paso obligatorio previo a deployment

---

### 2. `dist/` — control crítico

Debe añadirse al ADR:

* `.gitignore` obligatorio
* nunca versionar artefactos
* limpieza automática (`dist-clean`) antes de build

---

### 3. CI Gate adicional (recomendado)

Añadir:

```bash
CHECK-PROD-CHECKSEC
# valida:
# - PIE
# - RELRO full
# - NX enabled
```

Esto convierte hardening en **evidencia verificable**.

---

### 4. ARM64

Riesgo identificado:

* cross-compilation introduce complejidad
* toolchain adicional aumenta superficie en dev VM

No bloqueante, pero:

* documentar claramente toolchain usado
* fijar versión

---

## Evaluación para paper (§5)

El ADR aporta valor publicable real:

* reducción cuantificada de superficie
* separación estructural verificable
* metodología reproducible

Especialmente relevante en:

* entornos críticos (hospitales)
* auditorías de seguridad

---

## Conclusión final

* Decisión arquitectónica → **correcta y pragmática**
* Seguridad → **mejorada de forma estructural**
* Riesgos → **controlados y documentados**
* FEDER → **no bloqueado**

---

## Directiva del Consejo

Para continuar:

1. Implementar CHECK-PROD-CHECKSEC
2. Cambiar `-march=x86-64-v2` → `-march=x86-64`
3. Añadir checksum obligatorio en `dist/`
4. Formalizar confianza en entorno de build

---

**ADR-039 → APROBADO**
Listo para ejecución en DAY 131.
