Revisión del Consejo centrada en decisiones de ingeniería sostenibles en un sistema que ya está en fase **pre-producción crítica**.

---

# Evaluación general DAY 139–140

**Conclusión:**
El salto de calidad es real. Pasar de *192 → 0 warnings + -Werror* no es cosmético, es un cambio estructural.

Has eliminado una clase entera de fallos futuros:

* conversiones implícitas
* UB silencioso
* drift entre compiladores

Y el punto más importante:

> **ODR verificado con LTO y limpio**

Esto coloca el proyecto en un nivel que muchos sistemas productivos no alcanzan.

---

# Q1 — `-Werror` en código de terceros

## Veredicto

La política actual (supresión por fichero) es correcta **a corto plazo**, pero incompleta como política general.

---

## Regla industrial (muy clara)

Separar tres categorías:

### 1. Código propio

→ **Nunca suprimir warnings**
→ siempre arreglar

### 2. Código generado (protobuf, trees)

→ supresión permitida ✔

### 3. Código de terceros (como llama.cpp)

→ **depende del coste de actualización**

---

## Decisión en tu caso concreto (`llama.cpp`)

API deprecated:

* `llama_new_context_with_model` → `llama_init_from_model`

### Si el cambio es:

* trivial
* documentado
* sin impacto en arquitectura

→ **ACTUALIZA YA**

### Si implica:

* cambios en lifecycle
* cambios en memoria/contexto
* riesgo de regresión

→ **suprime temporalmente y agenda deuda**

---

## Política recomendada

```text
third_party/
  - allowed warnings: yes
  - must track upstream version
  - must document suppressions
```

Y añadir:

```cmake
# TODO: remove suppression when upgrading to llama.cpp >= X.Y
```

---

## Conclusión

* Supresión ✔ válida
* Pero debe ser **temporal y trazable**
* No convertirlo en norma silenciosa

---

# Q2 — ODR verification scope

## Veredicto

El gap actual **NO es aceptable** para infraestructura crítica.

---

## Problema

Hoy tienes:

* debug build diario ❌ sin LTO
* production build ocasional ✔ con LTO

→ ventana donde ODR puede colarse

---

## Riesgo real

ODR bugs:

* no aparecen en debug
* aparecen solo en ciertos link layouts
* pueden tardar semanas

---

## Práctica industrial

### Mínimo obligatorio:

**Gate pre-merge:**

```bash
make PROFILE=production all
```

---

### Recomendado:

CI pipeline:

1. debug (rápido)
2. production (LTO)
3. opcional: ASAN/TSAN

---

### Alternativa intermedia (si build es lento)

* production build:

    * nightly ✔
    * pre-release ✔
    * PR críticos ✔

---

## Conclusión

> ODR es un fallo de clase “no detectable en runtime fácilmente”

→ debe estar en CI, no en validación manual

---

# Q3 — `/*param*/` vs `[[maybe_unused]]`

## Veredicto

`[[maybe_unused]]` es la opción correcta en C++20.

---

## Comparación

### `/*param*/`

* hack visual
* no semántico
* no escala
* no detectable por tooling

### `[[maybe_unused]]`

* estándar C++20 ✔
* explícito ✔
* soportado por compilador ✔
* documenta intención ✔

---

## Caso especial: interfaces virtuales

Aquí la política cambia ligeramente:

```cpp
virtual void foo(int /*unused*/) override;
```

es aceptable si:

* override obligatorio
* no controlas firma

Pero mejor:

```cpp
virtual void foo([[maybe_unused]] int x) override;
```

---

## Recomendación del Consejo

* Código nuevo → `[[maybe_unused]]`
* Código legacy → migrar progresivamente
* Interfaces virtuales → también usar atributo

---

# Q4 — Benchmark sin hardware FEDER

## Veredicto

QEMU **NO es metodológicamente válido** para resultados publicables de rendimiento.

---

## Por qué

QEMU introduce:

* latencias artificiales
* comportamiento de caché irreal
* sin NIC real
* sin IRQ real
* sin DMA real

→ invalida cualquier métrica de:

* throughput
* latency
* drops

---

## Qué sí puedes hacer

### 1. Fase 1 — Benchmark x86 (válido)

Publicable como:

> “baseline reference platform”

---

### 2. Fase 2 — ARM sin hardware

Opciones:

#### Cloud ARM (RECOMENDADO)

* AWS Graviton
* Oracle ARM
* Ampere

✔ CPU real
❌ NIC no equivalente (pero aceptable)

---

### 3. Fase 3 — hardware FEDER

* RPi5 / N100
* resultados finales

---

## Estrategia científica sólida

Paper:

1. x86 baseline
2. ARM cloud indicative
3. ARM edge (final)

---

## Conclusión

* QEMU → ❌ no publicable
* ARM cloud → ✔ válido intermedio
* hardware físico → ✔ obligatorio final

---

# Q5 — `-Werror` y código generado

## Veredicto

La supresión por fichero **NO es suficiente**.

---

## Problema real

Cuando regeneras:

* protobuf
* XGBoost trees

→ puedes introducir warnings nuevos

Y con `-Werror`:
→ build roto sin aviso previo

---

## Solución industrial

### 1. Target de verificación explícito

```bash
make check-generated-clean
```

---

### 2. CI step

* regenerar código
* compilar SIN supresiones
* verificar warnings

---

### 3. Alternativa más estricta

Separar flags:

```cmake
target_compile_options(generated_code PRIVATE -w)
```

Pero entonces:

→ pierdes visibilidad total ❌

---

## Recomendación del Consejo

* mantener supresión ✔
* añadir test CI ✔ obligatorio

---

# Conclusión final del Consejo

## Estado del sistema

Has cruzado un umbral importante:

> ya no estás construyendo funcionalidades
> estás eliminando fuentes de fallo sistémico

---

## Riesgos restantes (priorizados)

1. 🔴 ODR no en CI
2. 🟠 código generado sin verificación
3. 🟡 política inconsistente en terceros
4. 🟡 uso de hacks (`/*param*/`)

---

## Recomendación DAY 141

Orden óptimo:

1. Gate CI con PROFILE=production
2. Test de código generado
3. Migrar a `[[maybe_unused]]`
4. Cerrar config Variant B

---

## Veredicto

El proyecto está entrando en fase donde:

> **los errores ya no serán visibles, sino estadísticos o esporádicos**

Y eso exige exactamente el tipo de disciplina que estás empezando a aplicar.

La dirección es correcta. El siguiente paso es hacer que estos controles sean automáticos, no manuales.
