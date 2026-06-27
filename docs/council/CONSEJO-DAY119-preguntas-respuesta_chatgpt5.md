Evaluación técnica directa del DAY 119, con foco en robustez operativa y sostenibilidad del pipeline.

---

# Evaluación global

**Muy buen movimiento hoy.**
Has atacado uno de los mayores riesgos reales de cualquier sistema serio:
👉 **la reproducibilidad completa desde cero**

Lo que has hecho en DAY 119 transforma el proyecto de:

* “funciona”
  a
* “se puede desplegar y mantener”

Eso es un salto de madurez importante.

---

## Fortalezas clave

1. **Detección correcta del problema estructural**

   > “todo lo manual es deuda”

   Esto es exactamente el patrón que rompe sistemas en producción.

2. **Secuencia canónica explícita**

    * Esto ya es **operación documentada**, no tribal knowledge.

3. **Corrección de dependencias invisibles**

    * `tmux`, `xxd`, `libsodium`, rutas plugins → típicos fallos reales.

4. **Introducción de `sync-pubkey`**

    * Soluciona un problema real derivado del diseño (clave hardcodeada).

---

## Riesgo principal actual

👉 **Estás empezando a crear lógica distribuida entre host (macOS) y VM**

Esto aparece en:

* `sync-pubkey` (VM → host → recompilación)
* rutas compartidas implícitas
* dependencia de estado cruzado

Si no se controla, esto rompe reproducibilidad a medio plazo.

---

# Respuestas a las preguntas

---

## Q1 — Robustez de `sync-pubkey`

**Veredicto: CONDICIONAL (válido, pero incompleto)**

### Problema real

Ahora mismo el flujo es:

```
VM genera clave → host la lee → modifica CMake → recompila
```

Esto introduce:

* dependencia bidireccional VM ↔ host
* posible desincronización
* riesgo de builds inconsistentes

---

### Riesgos concretos

1. **Race condition**

    * plugin-loader compilado con pubkey A
    * plugins firmados con pubkey B

2. **Estado oculto**

    * CMakeLists modificado sin control de versión real

3. **No determinismo**

    * mismo commit → builds distintos

---

### Recomendación (muy importante)

**Mover la fuente de verdad de la pubkey a fichero, no a CMake.**

---

### Diseño recomendado

```bash
/etc/ml-defender/crypto/plugin_pubkey.hex
```

---

### CMake

```cmake
# En lugar de hardcode
file(READ "/etc/ml-defender/crypto/plugin_pubkey.hex" PUBKEY_HEX)
add_definitions(-DMLD_PLUGIN_PUBKEY_HEX="${PUBKEY_HEX}")
```

---

### Ventajas

* Elimina `sync-pubkey`
* 100% reproducible
* No mezcla host/VM
* Compatible con producción real

---

### Sobre Continuity Prompt

**No automatizar.**

Motivo:

* Es documentación humana
* No debe depender de estado dinámico

---

### Riesgo si no cambias esto

Sistema frágil y difícil de reproducir fuera de Vagrant.

---

## Q2 — Vagrantfile vs Makefile

**Veredicto: ACEPTAR (separación correcta)**

---

### Regla clara (formalízala)

```text
Vagrantfile:
- Dependencias del sistema
- Librerías externas
- Paths del sistema

Makefile:
- Código del proyecto
- Build
- Tests
- Orquestación lógica
```

---

### Anti-patrón a evitar

❌ Instalar librerías en Makefile
❌ Compilar código en Vagrantfile

---

### Excepción válida

Cuando algo requiere ambos:

Ejemplo: XGBoost

* Vagrantfile → instala lib
* Makefile → linka y valida

✔ correcto

---

## Q3 — `make bootstrap`

**Veredicto: IMPLEMENTAR (obligatorio)**

---

### Diseño recomendado

```bash
make bootstrap
```

Debe ejecutar:

```bash
make up
make set-build-profile
make install-systemd-units
make sync-pubkey   # temporal hasta refactor
make sign-plugins
make test-provision-1
make pipeline-start
make pipeline-status
```

---

### Añade modo seguro

```bash
make bootstrap SAFE=1
```

* no arranca pipeline
* solo valida

---

### Riesgos

1. Ocultar errores → solución: logs claros
2. Debug difícil → solución: `set -x` opcional

---

### Beneficio

* Onboarding inmediato
* Reproducibilidad real
* CI local replicable

---

## Q4 — Contrato mínimo `MessageContext`

**Veredicto: DEFINIR contrato explícito YA**

---

### Contrato mínimo recomendado

```cpp
struct FeatureVectorV1 {
    uint32_t version;        // =1
    uint32_t feature_count;
    float values[FEATURE_MAX];
};
```

---

### Reglas obligatorias

```text
1. version == 1
2. feature_count == N esperado por modelo
3. orden fijo (documentado)
4. sin NaN ni inf
```

---

### Validación en plugin

```cpp
if (ctx->features.version != 1) return -1;
if (ctx->features.feature_count != EXPECTED) return -1;
```

---

### MUY IMPORTANTE

El modelo XGBoost depende del orden exacto de features.

Define:

```text
docs/ml/feature_schema_v1.md
```

---

### Riesgo si no haces esto

* Inferencias incorrectas silenciosas
* Imposible reproducir resultados

---

## Q5 — Puntos ciegos tras `vagrant destroy`

**Veredicto: HAY VARIOS riesgos todavía**

---

### 1. Rutas hardcodeadas

Buscar:

```bash
grep -r "/usr/local" .
```

---

### 2. Cache de pip

Puede romper reproducibilidad:

```bash
pip cache purge
```

---

### 3. Orden de provisioning

libsodium antes que dependientes → ya detectaste uno, puede haber más.

---

### 4. Permisos

Especialmente:

* `seed.bin`
* `.sk`
* `/usr/lib/ml-defender/plugins`

---

### 5. ldconfig

Asegúrate de:

```bash
ldconfig -p | grep xgboost
```

tras cada provision.

---

### 6. systemd reload

Falta típico:

```bash
systemctl daemon-reexec
systemctl daemon-reload
```

---

### 7. Tiempo / reloj

Crypto + firmas:

```bash
timedatectl
```

---

### 8. Orden de firma

Plugins firmados **antes** de pubkey sync → posible fallo.

---

# Recomendación estratégica clave

---

## Eliminar acoplamiento VM ↔ host

Esto es lo único que ahora mismo te puede romper el sistema a medio plazo.

---

## Objetivo

```text
git clone
make bootstrap
→ sistema funcional
```

SIN depender de:

* estado previo
* host
* sincronizaciones manuales

---

# Conclusión

Estado del proyecto:

* Seguridad → alta
* Operabilidad → muy buena
* Reproducibilidad → buena, pero con un punto débil (pubkey sync)

---

## Prioridad para DAY 120

1. Eliminar `sync-pubkey` (mover a fichero runtime)
2. Crear `make bootstrap`
3. Definir `feature_schema_v1`

Si haces esas tres cosas, el sistema pasa a ser:

👉 mantenible por terceros sin contexto previo

---

Si quieres, en el siguiente paso puedo darte:

* implementación exacta de eliminación de `sync-pubkey`
* o el esquema completo versionado de features para ML

sin añadir complejidad innecesaria.
