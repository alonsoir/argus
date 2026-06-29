## Veredicto del Consejo — DAY 128

El trabajo de hoy consolida correctamente dos cosas importantes:

1. el modelo de seguridad (invariantes fuertes, no negociables)
2. el modelo de verificación (property testing como capa adicional real)

Además, el hallazgo sobre `resolve_seed()` no es un problema: es una **confirmación de que la invariante se está aplicando correctamente**.

---

## P1 — Invariante `0400` vs portabilidad

**Veredicto: la invariante es correcta, pero la solución actual (sudo generalizado) no es óptima**

La decisión de:

* `0400`
* `root:root`
* sin symlinks

es **correcta y debe mantenerse**.

El problema no es la invariante, sino el modelo de ejecución.

### Riesgo actual

* Ejecutar múltiples componentes con `sudo` amplía superficie de ataque
* rompe principio de mínimo privilegio
* dificulta aislamiento futuro

### Solución correcta (estándar en sistemas reales)

**Separar acceso a secretos del proceso principal**

Opciones válidas:

#### Opción A — proceso lector privilegiado (recomendada)

* Un único proceso (root) lee seeds
* expone el material vía:

   * socket UNIX
   * memoria compartida protegida
* resto de procesos → sin privilegios

#### Opción B — capabilities Linux

* usar `CAP_DAC_READ_SEARCH`
* más fino que `sudo`, pero más complejo

#### Opción C — group-based access (menos estricta)

* `0400` → `0440`
* grupo dedicado (`argus-secrets`)
* trade-off: menor aislamiento

---

### Conclusión

* Mantener `0400 root:root`
* **Eliminar sudo generalizado en el futuro**
* evolucionar hacia “privileged secrets loader”

---

## P2 — Property testing como gate

**Veredicto: correcto, pero no universal**

Ya habéis visto el valor (F17). Ahora toca aplicarlo con criterio.

### Prioridad ALTA

1. `compute_memory_mb` → ya hecho
2. `safe_path` → ya hecho
3. `config_parser`
4. **serialización/deserialización (CRÍTICO)**

### Prioridad MEDIA

* ZeroMQ message framing
* parsing de inputs externos

### Prioridad BAJA / innecesario

* HKDF (criptografía estándar bien definida)
* wrappers simples sin lógica

---

### Regla práctica

Aplicar property testing cuando:

* hay espacio grande de inputs
* hay invariantes claras
* hay riesgo de overflow / parsing / normalización

---

### Conclusión

Sí como patrón, pero **selectivo**, no dogmático.

---

## P3 — `DEBT-IPTABLES-INJECTION-001` (CWE-78)

Aquí hay que ser contundente.

**Veredicto: (b) execve SIN shell — obligatorio mínimo
Mejor opción: (c) libiptc si es viable**

### Comparativa real

#### (a) Whitelist

* insuficiente
* difícil de mantener
* fácil de romper

#### (b) `execve(argv[])` — RECOMENDADO mínimo

* sin shell → no hay expansión
* elimina inyección por diseño

```cpp
execve("/sbin/iptables", argv, envp);
```

#### (c) `libiptc` — MEJOR a largo plazo

* sin fork/exec
* sin parsing de strings
* pero:

   * más compleja
   * menos portable

---

### Recomendación del Consejo

1. **Inmediato (bloqueante):**

   * migrar a `execve`
   * argumentos como array, no string

2. **Futuro:**

   * evaluar `libiptc`

---

## P4 — Cleanup EtcdClient vs ADR-024

**Veredicto: limpiar EtcdClient ANTES**

Motivo:

* el comportamiento actual es incorrecto (lee seeds localmente)
* introduce confusión conceptual
* añade superficie de ataque innecesaria

ADR-024 no es prerequisito para eliminar código muerto.

---

### Secuencia correcta

1. Eliminar dependencia de seeds en EtcdClient
2. Asegurar que:

   * no accede a filesystem
   * no usa `resolve_seed()`
3. Después:

   * implementar ADR-024

---

### Principio

> No construyas encima de comportamiento incorrecto, aunque sea temporal.

---

## P5 — Scope demo FEDER

**Veredicto: NO necesitas federación completa**

### Scope mínimo viable recomendado

* NDR standalone funcional
* pipeline completo:

   * ingestión tráfico
   * detección
   * reacción (iptables)
* demo reproducible (PCAP + replay)

---

### NO necesario para FEDER

* federación completa (ADR-038)
* P2P avanzado
* auto-reentrenamiento en vivo

---

### Lo que sí importa

* reproducibilidad
* estabilidad
* narrativa clara

---

### Riesgo real

Intentar meter federación:

* aumenta complejidad exponencialmente
* riesgo alto de fallo en demo

---

### Conclusión

> Mejor demo simple que funciona siempre, que demo compleja que falla una vez.

---

## Evaluación global DAY 128

Puntos clave:

* Invariante de seguridad validada en entorno real
* Property testing formalizado correctamente
* Hallazgos técnicos bien interpretados (symlink + canonical)

### Riesgo principal actual

* ejecución con `sudo` extendida
* `iptables` injection (crítico, bien identificado)

---

## Prioridades DAY 129

1. **CWE-78 (iptables) → FIX inmediato**
2. Reducir superficie `sudo`
3. Cleanup EtcdClient
4. Snyk findings restantes

---

## Veredicto final

* Arquitectura: sólida
* Seguridad: bien encaminada
* Metodología: madura
* Riesgos: identificados y controlables

El sistema ya no solo implementa seguridad:
**empieza a comportarse como un sistema que desconfía de sí mismo.**

Ese es el punto de inflexión correcto.
