# Consejo de Sabios — Respuesta DAY 163 → DAY 164

## 1. Patrón CMake para targets condicionales

La recomendación del Consejo es:

### Corto plazo (obligatorio inmediatamente)

Usar:

```cmake
if(NOT TARGET test_ntp_health_check)
    add_executable(test_ntp_health_check ...)
endif()
```

como **guard defensivo obligatorio** en cualquier bloque condicional enterprise (`ARGUS_VAULT_ENABLED`, `ARGUS_ENTERPRISE`, etc.).

### Medio plazo (arquitectura correcta)

Refactorizar para que:

* cada target tenga **un único owner**
* la variación enterprise se haga mediante:

    * `target_sources()`
    * `target_compile_definitions()`
    * `target_link_libraries()`
    * o factories/configuración runtime

y no mediante redefiniciones parciales del target.

---

### Motivo técnico

El problema observado hoy no es realmente “duplicación accidental”, sino:

> ruptura de la unicidad semántica del grafo de build.

CMake trata los targets como nodos globales. Cuando un target puede emerger desde múltiples ramas condicionales:

* el grafo deja de ser determinista,
* aparecen fallos sólo bajo combinaciones específicas de flags,
* y EMECAS++ deja de validar el universo completo de compilación.

Eso es especialmente peligroso en un sistema enterprise con:

* Vault
* providers alternativos
* matrices CI
* feature flags criptográficas.

---

### Recomendación fuerte del Consejo

No crear variantes tipo:

```cmake
test_ntp_health_check_vault
```

salvo que el binario sea realmente distinto.

Porque eso:

* fragmenta cobertura,
* duplica mantenimiento,
* dificulta trazabilidad CI,
* y oculta divergencias funcionales.

El target debería seguir siendo uno:

```cmake
test_ntp_health_check
```

y el comportamiento enterprise debe entrar vía dependencias/configuración.

---

### Acción recomendada

Nueva debt transversal:

```text
DEBT-CMAKE-GRAPH-INVARIANTS-001
```

Objetivo:

* prohibir redefiniciones de targets,
* exigir guards,
* añadir lint CI:

    * detección automática de `add_executable/add_library`
    * verificación de unicidad global.

---

# 2. BACKLOG-CRYPTO-VENDOR-KEY-001 — Scope real DAY 164

Respuesta corta:

> No. La variable de entorno sola NO cierra Fase 1 completamente.

El Consejo considera que:

### La Fase 1 requiere cerrar el círculo de confianza completo:

1. `vendor.key` fuera del repo ✅
2. secreto almacenado en Vault ✅
3. Jenkins obteniendo material vía mecanismo enterprise seguro ✅
4. aislamiento por identidad de componente ✅

El punto 4 implica:

* AppRole
  o equivalente machine identity mechanism.

---

## Por qué importa

Si Jenkins sigue siendo:

* un actor monolítico,
* con acceso amplio,
* usando variables de entorno globales,

entonces:

* habéis movido el secreto,
* pero no habéis terminado la segmentación trust-domain.

Eso deja incompleta la transición enterprise.

---

## Recomendación operativa

### DAY 164 mínimo aceptable para cerrar Fase 1

Debe incluir:

* Vault path real:

  ```text
  secret/argus/enterprise/vendor-key
  ```

* Jenkins leyendo desde Vault

* eliminación completa del `vendor.key` persistente

* AppRole dedicado al pipeline Jenkins enterprise

No hace falta todavía:

* rotación automática,
* leases complejos,
* secret renewal daemon,
* dynamic secrets.

Pero sí:

* identidad separada,
* policy mínima,
* acceso scoped.

---

## Evaluación del Consejo

### Si sólo hacéis ENV VAR:

Estado:

```text
FASE 1 parcial
```

### Si añadís AppRole:

Estado:

```text
FASE 1 cerrada
```

---

# 3. EMECAS++ Acto I — Cobertura enterprise real

La posición del Consejo es bastante clara aquí:

## Compilar no es suficiente.

Ahora mismo EMECAS++ Acto I valida:

* coherencia de build,
* linkage,
* compatibilidad de flags,
* integridad de targets.

Eso está bien.

Pero NO valida aún:

* bootstrap criptográfico real,
* auth flow Vault,
* retrieval path,
* políticas,
* fallos de lease/token,
* startup enterprise auténtico.

---

## Entonces, ¿debe exigir `VaultProvider` real ya?

### Respuesta del Consejo:

No todavía.

Porque:

* `BACKLOG-CRYPTO-VENDOR-KEY-001` aún está abierto,
* el sistema aún está en transición híbrida,
* y forzar E2E real ahora podría:

    * introducir flaky CI,
    * bloquear merges legítimos,
    * mezclar debt estructural con debt operacional.

---

## Recomendación concreta

### Estado actual aceptable temporalmente:

Acto I:

* compila con `ARGUS_VAULT_ENABLED=ON`
* tests unitarios verdes
* providers enterprise linkan correctamente

✔ Aceptable como transición.

---

## Pero el Consejo recomienda crear YA:

```text
BACKLOG-EMECAS-VAULT-E2E-001
```

Objetivo:

* Acto I enterprise real
* bootstrap usando `VaultProvider`
* Vault dev server efímero CI
* AppRole temporal
* smoke retrieval test
* fail-fast si Vault no responde.

---

## Recomendación estratégica importante

El Consejo detecta que EMECAS++ está evolucionando hacia:

> “verificación de invariantes de arquitectura enterprise”.

Eso significa que, a medio plazo, EMECAS++ no debería validar sólo:

* compilación,
* tests,
* packaging,

sino también:

* trust boundaries,
* identity flows,
* provider integrity,
* crypto bootstrap lifecycle,
* secret provenance.

Y eso es exactamente lo correcto para aRGus NDR enterprise.
