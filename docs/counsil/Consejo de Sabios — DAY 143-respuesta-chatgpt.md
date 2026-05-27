Revisión completa DAY 143 con criterio de sistemas críticos y despliegue real.

---

# Evaluación global del DAY 143

El sistema ha alcanzado un punto importante:
**el IRP ya no es teórico, es ejecutable, testeado y reproducible.**

Fortalezas claras:

* EMECAS detectando regresiones reales → señal de madurez
* separación correcta lógica pura (`should_auto_isolate`) vs efectos (`fork/exec`)
* validación numérica (bug IEEE754 detectado) → excelente práctica científica
* AppArmor en enforce desde hardened → coherente con BSR
* aislamiento transaccional con rollback → diseño sólido

Ahora: hay varios puntos donde el sistema aún puede fallar en producción hospitalaria.

---

# P1 — `fork()+execv()` sin `wait()`

**Conclusión:**
Sí, esto genera zombies. Y en carga sostenida, es un problema real.

### Qué ocurre exactamente

* el hijo termina (`_exit`)
* el padre no hace `wait()`
* queda entrada en la tabla de procesos (zombie)
* systemd no siempre limpia inmediatamente (depende del parent)

### Riesgo real

* fuga de PIDs en escenarios de ataque persistente
* agotamiento de tabla de procesos (extremo pero posible)
* degradación silenciosa

### Solución correcta (mínima)

Añadir recolección no bloqueante en el loop del agente:

```cpp
while (waitpid(-1, nullptr, WNOHANG) > 0) {}
```

### Alternativa superior (recomendada)

Delegar completamente a systemd:

```bash
systemd-run --unit=argus-isolate ...
```

Ventajas:

* systemd gestiona lifecycle
* no hay zombies
* logging automático
* integración con cgroups

### Veredicto

* mínimo aceptable: `waitpid(WNOHANG)`
* arquitectura correcta: **systemd-run**

---

# P2 — Tolerancia IEEE 754 vs tipos consistentes

**Conclusión:**
La tolerancia es un parche correcto, pero no la solución óptima.

### Problema de fondo

* `confidence_score` es `float`
* `threshold` es `double`
* conversión introduce error

### Mejor solución

Unificar tipos:

```cpp
float threshold;
```

y comparar directamente:

```cpp
confidence >= threshold
```

### Alternativa aún más robusta (recomendada)

Eliminar floats del criterio crítico:

```cpp
uint32_t score_scaled = (uint32_t)(confidence * 1000);
uint32_t threshold_scaled = 950;
```

→ comparación entera, determinista

### Industria

Sistemas críticos evitan floats en lógica de decisión (aviónica, trading HFT, etc.)

### Veredicto

* corto plazo: mantener tolerancia ✔
* medio plazo: **unificar a float o usar enteros escalados**

---

# P3 — `auto_isolate: true` por defecto

**Conclusión:**
Para hospitales: **incorrecto como default en producción**.

### Riesgo real

Instalación sin tuning:

* falso positivo → aislamiento
* impacto en:

    * ventiladores
    * monitores
    * sistemas PACS

Esto no es aceptable.

### Buen patrón (industria crítica)

Modo “safe onboarding”:

```json
auto_isolate: false
```

Pero con:

* alertas activas
* logging completo
* recomendación explícita de activación

### Alternativa equilibrada (muy buena opción)

Modo “armed but gated”:

```json
auto_isolate: true,
require_manual_confirm: true
```

→ primera vez no ejecuta, solo alerta

### Veredicto

* FEDER demo: `true` ✔
* producción hospitalaria: **false o gated obligatorio**

---

# P4 — AppArmor y uso de `/tmp`

**Conclusión:**
Sí, es demasiado permisivo para producción.

### Problema

Permitir:

```
/tmp/argus-*.nft rw
```

implica:

* namespace compartido
* posible interferencia de otros procesos
* riesgo de TOCTOU attacks

### Recomendación

Mover a:

```
/var/lib/argus/irp/
```

con:

* ownership: `root:argus`
* permisos: `750`

y en AppArmor:

```
/var/lib/argus/irp/** rw,
```

### Industria

* `/tmp` se evita en componentes críticos
* se usan directorios dedicados con control de permisos

### Veredicto

* FEDER: aceptable
* producción: **migrar fuera de /tmp obligatorio**

---

# P5 — Criterio de disparo (multi-señal)

**Conclusión:**
Dos señales no son suficientes en entorno hospitalario real.

### Problema

Actualmente:

```
score + tipo_evento
```

Esto sigue siendo:

* monocanal (modelo ML)
* vulnerable a:

    * falsos positivos sistemáticos
    * evasión adversarial

### Arquitectura recomendada (mínima viable)

Añadir una tercera señal independiente:

#### Opción A — Burst temporal

```
>= N eventos en ventana
```

#### Opción B — Segundo sensor

* Falco
* reglas heurísticas
* red anomaly

#### Opción C — Contexto de activo

* no aislar si IP ∈ whitelist crítica

### Configuración recomendada

```json
trigger:
  score >= 0.95
  AND event_type IN (...)
  AND burst >= 2
```

### Industria

* EDR/XDR nunca ejecutan acciones destructivas con una sola señal

### Veredicto

* FEDER: actual ✔
* producción: **mínimo 3 señales o 2 + burst obligatorio**

---

# Evaluación de lo que haréis en DAY 144

## Opción A — Merge a main

**Recomendación:**
Sí, pero con un gate adicional:

```bash
make PROFILE=production all
```

Motivo:

* detectar ODR + LTO issues
* evitar regresiones silenciosas

## Opción B — Benchmark

Muy importante para paper, pero:

* no bloquea estabilidad del sistema

## Opción C — etcd HA

Crítico para producción, pero:

* no bloquea FEDER demo

### Orden recomendado

1. **Merge (A)**
2. Benchmark (B)
3. HA etcd (C)

---

# Observaciones adicionales críticas

## 1. `fork()` sin límite

Debes proteger contra tormentas de forks:

```cpp
max_isolate_processes_per_minute
```

→ evita fork bomb accidental

---

## 2. Idempotencia del aislamiento

Si ya estás aislado:

* no lanzar otro isolate

→ check previo obligatorio

---

## 3. Logging del IRP

Necesitas:

* trace_id del evento que disparó aislamiento
* correlación completa

Esto será clave en forensics.

---

# Resumen ejecutivo del Consejo

### Decisiones correctas

* separación lógica pura / efectos ✔
* uso de tests para edge cases numéricos ✔
* AppArmor enforce ✔
* aislamiento transaccional ✔

### Cambios críticos antes de producción

1. Recolección de zombies (`waitpid` o systemd-run)
2. No usar `/tmp` para artefactos críticos
3. Desactivar `auto_isolate` por defecto en hospitales
4. Añadir tercera señal (burst mínimo)
5. Unificar tipos numéricos (float vs double)

---

Si se aplican estos ajustes, el sistema pasa de “robusto en laboratorio” a **seguro y defendible en infraestructura crítica real**.
