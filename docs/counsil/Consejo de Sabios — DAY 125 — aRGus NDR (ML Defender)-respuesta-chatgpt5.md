## Veredicto del Consejo — DAY 125

El trabajo de hoy es sólido y, más importante, **ha mejorado el proceso**, no solo el código. Detectar un bug en el propio fix (F17) mediante property testing es exactamente el tipo de señal que indica que el pipeline empieza a ser fiable de verdad.

Respuestas directas:

---

### P1 — `double` vs `int64_t` en `compute_memory_mb`

**Veredicto: ACEPTAR `double`, con una condición mínima**

La elección es correcta por dos razones:

* `int64_t` no cubre el espacio completo si los operandos vienen de `long`
* el dominio real (memoria de proceso) está muy por debajo del límite de precisión de `double`

**Análisis de precisión:**

* `double` → 53 bits de mantisa
* Precisión exacta hasta ~9e15 bytes (~9 PB)
* Muy por encima de cualquier memoria realista de proceso

**Riesgos reales:**

* No overflow → correcto
* Posible pérdida de precisión → irrelevante para métricas en MB

**Recomendación mínima:**

Añadir un guard lógico, no por seguridad sino por sanidad:

```cpp
assert(result >= 0);
assert(result < 1e9); // ~1 exabyte en MB, margen enorme
```

No hace falta `EXPECT_LE(MAX_REALISTIC_MEMORY_MB)` salvo que quieras convertirlo en invariante documentado.

**Conclusión:** decisión correcta, respaldada matemáticamente.

---

### P2 — `config_parser` con prefix fijo

**Veredicto: CORREGIR — diseño actual es inseguro**

Tu diagnóstico es completamente acertado:

> si el prefix deriva del input, no existe control real

Eso rompe el modelo de seguridad.

**Solución correcta:**

```cpp
load(config_path, allowed_prefix="/etc/ml-defender/")
```

**Consideraciones:**

* No rompe bootstrapping si:

    * el valor por defecto es válido
    * los tests pueden overridearlo

* En dev:

    * usar variable de entorno (`ARGUS_CONFIG_PREFIX`)
    * o inyección explícita en tests

**No aceptable:**

* derivar prefix del propio path (circular trust)

**Conclusión:** cambio obligatorio antes de considerar el componente como endurecido.

---

### P3 — Symlinks en `resolve_seed()`

Aquí conviene ser claro: la opción “configurable” parece razonable, pero es peligrosa.

**Veredicto: RECHAZAR TODOS los symlinks (estricto)**

Motivo:

* `seed.bin` = material criptográfico
* symlink = vector clásico de exfiltración / TOCTOU
* no hay caso legítimo fuerte que justifique el riesgo

**Sobre CI/CD:**
Si el entorno usa symlinks:

* es el entorno el que debe adaptarse
* no el control de seguridad

**Regla:**

> En superficies criptográficas, la ergonomía nunca gana a la seguridad.

**Implementación correcta:**

* `lstat()` → rechazar `S_ISLNK`
* `open(..., O_NOFOLLOW)`

**Conclusión:** no introducir flag `allow_symlink`. Sería deuda futura.

---

### P4 — Cobertura de tests de producción

**Veredicto: COMPLETAR antes de ADR-038**

No es opcional.

Razón:

* `rag-ingester` ha demostrado el patrón
* pero no garantiza que otros componentes no tengan variaciones sutiles

**Principio:**

> Cada punto de entrada externo debe tener su propio test de explotación.

Componentes pendientes:

* `seed-client` (crítico)
* `firewall-acl-agent`

**No suficiente:**

* confiar en `safe_path` tests

**Conclusión:** bloquear avance hasta cerrar esta cobertura.

---

### P5 — Property testing sistémico

**Veredicto: SÍ, pero con disciplina**

Lo ocurrido con F17 no es anecdótico: es exactamente donde property testing aporta valor.

**Dónde usarlo:**

* funciones puras
* lógica matemática
* validaciones de seguridad

**Dónde NO:**

* parsing complejo
* integración
* IO

**Librerías:**

* opción ligera: escribir loops propios (como ya hacéis)
* opción formal: RapidCheck (válida en Debian Bookworm)

**Recomendación:**

* no introducir dependencia aún
* estandarizar patrón interno

```cpp
for (...) {
    // generar inputs
    // verificar invariantes
}
```

**Conclusión:** adoptar como práctica, no como framework obligatorio.

---

### P6 — Paper (§5)

**Veredicto: INCLUIRLO**

Pero con framing técnico, no narrativo.

Estructura sugerida:

**§5.1 — Failure Mode**

* fixes sin tests de demostración

**§5.2 — Methodological Correction**

* TDH (Test-Driven Hardening)
* RED→GREEN en seguridad

**§5.3 — Empirical Evidence**

* F17: fix incorrecto detectado por property test

**§5.4 — General Principle**

> “Security fixes must be validated against adversarial inputs, not only expected ones”

Esto no es “diario de desarrollo”:
es una contribución metodológica clara.

---

## Evaluación global DAY 125

Lo importante no es que hayas cerrado deuda.

Es que el sistema ahora:

* detecta errores en fixes de seguridad
* obliga a demostrar vulnerabilidades
* reduce confianza implícita en el código

Eso es exactamente lo que diferencia:

* software funcional
  de
* software de seguridad confiable

---

## Prioridades DAY 126 (orden recomendado)

1. **DEBT-CONFIG-PARSER-FIXED-PREFIX-001** (crítico)
2. **DEBT-SAFE-PATH-SEED-SYMLINK-001** (crítico)
3. **Tests producción restantes (P4)** (crítico)
4. **Snyk web verification** (validación externa)

---

## Veredicto final

* Dirección: correcta
* Ejecución: rigurosa
* Riesgos detectados: bien identificados
* Próximo paso: cerrar consistencia entre componentes

El documento está listo para enviarse.
