## Consejo de Sabios — Respuestas DAY 132

Evaluación bajo método científico reproducible: cada recomendación incluye hipótesis, verificación y criterio de aceptación.

---

## Q1 — Makefile targets de producción

**Decisión: ✅ Mantener en `Makefile` raíz (con restricciones formales)**

### Hipótesis

Un único Makefile:

* reduce duplicación
* evita divergencia de targets
* mejora trazabilidad

### Riesgo observado

* Confusión entre targets dev vs producción
* Ejecución accidental en entorno incorrecto

### Solución (recomendada)

Mantener en raíz, pero añadir:

```makefile
# Guard obligatorio
guard-dev-vm:
	@if [ ! -f /.argus-dev-vm ]; then \
		echo "ERROR: production targets must run inside dev VM"; exit 1; \
	fi
```

Y hacer que todos los targets de producción dependan de ello:

```makefile
build-production-x86: guard-dev-vm
sign-production: guard-dev-vm
```

### Verificación reproducible

* Ejecutar en host → debe fallar
* Ejecutar en hardened → debe fallar
* Ejecutar en dev VM → debe pasar

### Alternativa rechazada

`Makefile.production`:

* introduce duplicación
* rompe coherencia del pipeline

---

## Q2 — Debian 12 vs 13

**Decisión: ✅ Mantener `bookworm` (Debian 12)**

### Hipótesis

* Estabilidad > novedad en entorno crítico
* tooling Vagrant depende de boxes maduras

### Evidencia

* Debian 12 → soporte LTS estable
* Debian 13 → aún sin ecosistema Vagrant consolidado

### Recomendación formal

1. Mantener:

  * `debian/bookworm64` en Vagrant
2. Documentar:

  * “target production baseline: Debian 12 (validated), Debian 13 (planned)”

### Criterio de aceptación

* provisioning reproducible sin fallos
* CI estable

### Nota para paper

No afirmar Debian 13 como baseline si no está validado empíricamente.

---

## Q3 — Verificación BSR (compiladores)

**Decisión: ⚠️ Añadir segunda capa obligatoria**

### Problema identificado

`dpkg`:

* detecta paquetes instalados
* NO detecta binarios copiados manualmente

### Solución propuesta (mínima)

```bash
# capa 1
dpkg -l | grep -qE 'gcc|g\+\+|clang|cmake|make' && exit 1

# capa 2
command -v gcc   && exit 1
command -v clang && exit 1
command -v cc    && exit 1
command -v make  && exit 1
```

### Mejora recomendada (nivel alto rigor)

Añadir:

```bash
find /usr /bin /usr/local -type f \
  \( -name "gcc" -o -name "clang" -o -name "cc" \) 2>/dev/null | grep . && exit 1
```

### Criterio científico

* cobertura parcial > falsa sensación de seguridad
* defensa en profundidad

---

## Q4 — Draft v17 (secciones §5)

**Decisión: 🟡 AÚN NO LISTO para arXiv (requiere refuerzo empírico)**

Las ideas son sólidas, pero arXiv cs.CR exige:

* reproducibilidad
* evidencia cuantitativa
* comparación con baseline

---

### Evaluación por sección

#### §6.5 — RED→GREEN Gate

**Estado:** sólido conceptualmente
**Falta:**

* métricas:

  * tasa de fallos pre/post gate
  * tiempo medio de detección

---

#### §6.8 — Fuzzing

**Estado:** correcto pero incompleto

**Requiere:**

* número de inputs ejecutados
* coverage (%)
* bugs encontrados

---

#### §6.10 — CWE-78 (execv)

**Estado:** bueno

**Mejora necesaria:**

* comparación directa:

  * `system()` vs `execv()`
  * exploit reproducible

---

#### §6.12 — BSR Axiom

**Estado:** interesante pero debe formalizarse más

**Problema actual:**

* suena a afirmación, no a resultado

**Requiere:**

* métrica concreta:

  * reducción de paquetes
  * CVEs eliminados
* experimento:

  * entorno con vs sin toolchain

---

## Recomendación global para paper

Antes de arXiv:

Añadir sección experimental:

```text
§7 — Empirical Validation
```

Con:

| Experimento       | Métrica                 |
| ----------------- | ----------------------- |
| Toolchain removal | CVEs eliminados         |
| Fuzzing           | bugs encontrados        |
| RED→GREEN         | defect rate reduction   |
| execv vs system   | exploit reproducibility |

---

## Evaluación global DAY 132

### Estado

* Documentación rigurosa
* Sin regresión técnica
* Preparación correcta para producción

### Riesgos

1. Falta de validación empírica (paper)
2. Verificación BSR incompleta (resuelto con Q3)
3. Confianza en entorno dev no formalizada

---

## Directiva del Consejo

Para DAY 133:

1. Implementar guard-dev-vm en Makefile
2. Añadir doble verificación BSR
3. Introducir métricas reales en §5
4. No subir a arXiv aún

---

## Veredicto final

* Arquitectura → **correcta**
* Seguridad → **bien encaminada**
* Paper → **prometedor pero incompleto**

---

El sistema evoluciona correctamente hacia un estado auditable y defendible científicamente.
