# Consejo de Sabios — Respuesta DAY 144

El estado actual del proyecto muestra una mejora clara en disciplina de ingeniería: EMECAS está encontrando regresiones reales, `-Werror` ya actúa como guardián estructural y el cierre de las ODR violations antes del merge evita una clase de UB extremadamente peligrosa en C++20 distribuido. La decisión de hacer fallar el arranque si falta `auto_isolate` es especialmente correcta: elimina defaults implícitos en un dominio donde el silencio operacional es peligroso.

También hay una señal importante: el proyecto empieza a comportarse como un sistema reproducible y no como una colección de componentes. Eso cambia el nivel de exigencia.

---

# P1 — Diseño experimental ADR-029 (Variant A vs Variant B)

La contribución científica fuerte no es “libpcap vs eBPF” en abstracto. Eso ya existe en literatura. La contribución relevante es:

> “Impacto arquitectónico del backend de captura sobre un pipeline NDR hardened end-to-end.”

Por tanto, las métricas prioritarias no son solo PPS crudos.

## Prioridad real de métricas

### Tier 1 — Obligatorias para paper serio

| Métrica                            | Motivo                                           |
| ---------------------------------- | ------------------------------------------------ |
| Latencia end-to-end p50/p95/p99    | Es lo que afecta detección y respuesta           |
| Packet drop rate bajo carga        | Métrica crítica de NDR                           |
| CPU total por componente           | Infraestructura hospitalaria = hardware limitado |
| Throughput sostenible (no burst)   | Más importante que pico teórico                  |
| Detection fidelity bajo saturación | La métrica más importante                        |

La quinta es la más diferencial.

Muchos papers reportan PPS y CPU. Muy pocos muestran:

> “qué ocurre con la calidad de detección cuando el backend empieza a perder paquetes”.

Ese es el dato publicable.

---

## Métricas secundarias útiles

| Métrica                        | Valor                        |
| ------------------------------ | ---------------------------- |
| RSS memory                     | ARM64/RPi relevante          |
| Kernel→userspace jitter        | Interesante para Variant A   |
| Bootstrap/provision complexity | Muy valioso operacionalmente |
| Mean recovery time             | Útil para ADR-042            |

---

## Recomendación metodológica

No medir solo:

```text
captura → PPS
```

Medir:

```text
pcap replay
→ capture backend
→ serialize
→ crypto
→ zmq
→ ml-detector
→ decision latency
```

Porque ese es el sistema real.

---

# P2 — Scope ARM64 Variant C

El Consejo es bastante unánime aquí:

## Para arXiv v19

x86 eBPF + x86 libpcap es suficiente.

Ya permite:

* comparación controlada
* reproducibilidad
* baseline científico
* análisis arquitectónico

ARM64 no es necesario para validar la hipótesis científica principal.

---

## Para FEDER

ARM64 sí añade valor estratégico.

Especialmente porque:

* hospitales pequeños usan hardware limitado
* edge deployments ARM64 son realistas
* eficiencia energética importa
* RPi5/N100 son extremadamente defendibles como edge NDR nodes

---

## Recomendación concreta

### NO hacer Variant C completa antes del merge

Porque ahora mismo el riesgo principal es:

> dispersión arquitectónica antes de estabilizar la línea principal.

Primero:

1. merge Variant B
2. benchmark serio
3. paper reproducible
4. freeze parcial

Después:
5. ARM64 branch

---

## Sobre cross-compilation

No subestiméis esto.

Cross-compiling C++20 + protobuf + ONNX + FAISS + libbpf + AppArmor es:

* costoso
* frágil
* difícil de reproducir

Para FEDER probablemente será más robusto:

* build nativo ARM64
* runners dedicados
* no cross-toolchain inicialmente

---

# P3 — Modelo matemático multi-señal IRP

## Recomendación clara: regresión logística auditable

NO Naive Bayes.

Motivos:

* independencia de señales falsa
* difícil justificar operacionalmente
* comportamiento menos intuitivo para auditoría

---

## Tampoco modelos complejos inicialmente

Evitar:

* árboles boosting
* ensembles
* redes neuronales

Para aislamiento hospitalario importa:

* interpretabilidad
* auditabilidad
* reproducibilidad legal

No solo precisión.

---

## Recomendación arquitectónica

Modelo lineal ponderado:

P(incident)=\sigma(w_1x_1+w_2x_2+w_3x_3+b)

Donde:

* `x1` = confidence score ML
* `x2` = frecuencia temporal
* `x3` = criticidad evento
* etc.

Ventajas:

* pesos auditables
* fácil de explicar
* ajustable
* compatible con compliance
* científicamente defendible

---

## Recomendación adicional importante

Separar:

```text
Detection Confidence
```

de

```text
Isolation Confidence
```

No son la misma cosa.

Ejemplo:

* score ML alto
* activo crítico hospitalario
* horario quirúrgico
  → detección alta
  → aislamiento NO automático

Eso es arquitectura de safety.

---

# P4 — Experimento aRGus vs Suricata vs Zeek

Aquí es donde podéis cometer errores metodológicos graves si no se diseña bien.

## Error más peligroso

Comparar:

* Suricata con ET Open
  vs
* aRGus ML

sin controlar:

* firmas
* tuning
* contexto

Eso sería metodológicamente débil.

---

# Protocolo recomendado

## Dataset dividido en 3 categorías

### Grupo A — ataques conocidos con firma

Objetivo:

* validar baseline IDS clásico

Esperable:

* Suricata fuerte
* Zeek contextual
* aRGus comparable

---

### Grupo B — variaciones adversariales

Modificar:

* timing
* payload ordering
* fragmentación
* jitter

Objetivo:

* degradar firmas sin romper comportamiento

Aquí aparece vuestro valor científico.

---

### Grupo C — comportamiento lateral/anómalo

Sin IOC conocida.

Objetivo:

* mostrar límites de firmas estáticas

---

# Métricas importantes

No solo:

* TPR/FPR

También:

* detection latency
* CPU cost
* operational complexity
* provisioning complexity
* recovery behavior

---

# Recomendación crucial

NO afirméis:

> “aRGus supera a Suricata”.

Eso es una trampa científica enorme.

La afirmación defendible es:

> “aRGus explora un espacio arquitectónico distinto basado en análisis conductual hardened y respuesta integrada.”

Eso sí es sostenible.

---

# Observaciones adicionales del Consejo

## 1. `SA_NOCLDWAIT`

Correcto.

Mejor que polling periódico.
Menor complejidad.
Menos estados intermedios.

Buena decisión.

---

## 2. `/run/argus/irp`

Mucho mejor que `/tmp`.

En infraestructura crítica:

* `/tmp` debe considerarse hostil
* incluso con AppArmor

La dirección actual es correcta.

---

## 3. ODR violations reales

Muy importante:
las ODR aparecieron solo bajo LTO production.

Eso confirma que el gate production NO puede ser opcional.

Recomendación:

```text
make PROFILE=production all
```

debe ejecutarse:

* pre-merge obligatorio
* nightly
* antes de tags release

---

## 4. `assert()` en tests con `-UNDEBUG`

Correctísimo.

Muchos proyectos pierden cobertura real en tests release-like porque `assert()` desaparece silenciosamente.

Buena práctica.

---

# Recomendación estratégica final

El proyecto está entrando en una fase distinta.

Antes:

* velocidad
* construcción
* exploración

Ahora:

* estabilización
* reproducibilidad
* rigor experimental
* reducción de complejidad accidental

El mayor riesgo técnico actual ya no parece ser el rendimiento.

Es:

> complejidad arquitectónica creciente antes de consolidar interfaces y protocolos experimentales.

El merge de Variant B debería ocurrir pronto si el benchmark básico sale limpio. Retrasarlo demasiado aumenta el riesgo de divergencia estructural entre ramas.
