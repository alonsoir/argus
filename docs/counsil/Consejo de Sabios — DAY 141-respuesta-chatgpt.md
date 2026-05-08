A continuación se presenta la revisión técnica con criterio de ingeniería de sistemas distribuidos y despliegue en entornos críticos.

---

# Q1 — Identidad criptográfica compartida (Variant A vs B)

**Conclusión:**
No es recomendable compartir identidad criptográfica. Deben ser **identidades separadas**.

### Problema técnico

Compartir:

* mismo `component_id`
* mismas claves (`keys_dir`)
* mismo contexto (`CTX_SNIFFER_TO_ML`)

implica que **dos implementaciones distintas son indistinguibles criptográficamente**.

Esto rompe:

* **auditoría forense** → no puedes saber qué backend generó un evento
* **revocación selectiva** → no puedes deshabilitar solo libpcap o solo eBPF
* **principio de aislamiento de fallos** → un bug en Variant B afecta a la confianza de A

### Riesgo real

Si Variant B (libpcap) tiene:

* más drops
* parsing divergente
* latencias mayores

estarías contaminando la reputación criptográfica de Variant A (más fiable).

### Recomendación (estándar industria)

Separar identidad por **runtime variant**:

```
component_id:
  sniffer-ebpf
  sniffer-libpcap
```

Mantener:

* mismo esquema de mensajes
* mismo `CTX_SNIFFER_TO_ML` (si semánticamente equivalente)

Pero:

* **claves distintas**
* **rotación independiente**
* **revocación independiente**

### Patrón equivalente

Esto sigue el modelo de:

* sidecars en Kubernetes (identidades separadas)
* microservicios con mTLS (SPIFFE IDs distintos)

---

# Q2 — Buffer size en libpcap (pre vs post FEDER)

**Conclusión:**
Debe ser **pre-FEDER obligatorio (bloqueante)**.

### Razón técnica

`pcap_open_live()`:

* usa buffer por defecto del kernel (a veces 2MB en ARM)
* no controlas drops bajo carga

En RPi/N100:

* NIC + CPU limitada
* bursts → pérdida silenciosa de paquetes

### Impacto directo

Sin esto:

* benchmark FEDER es **inválido científicamente**
* no estás midiendo el sistema, sino la configuración por defecto del kernel

### Recomendación

Migrar a:

```cpp
pcap_create()
pcap_set_buffer_size()
pcap_set_immediate_mode()
pcap_activate()
```

Y exponer:

```
buffer_size_mb
```

### Buenas prácticas industria

* Suricata / Zeek permiten tuning explícito
* benchmarks sin control de buffer → **rechazables en peer review**

### Veredicto

No es una deuda. Es **requisito experimental**.

---

# Q3 — TinyLlama vs grep/awk (clasificador warnings)

**Conclusión:**
TinyLlama es **over-engineering** aquí.

### Naturaleza del problema

Clasificación de warnings es:

* determinista
* basada en patrones
* estable en el tiempo

### Solución óptima

`grep/awk` + reglas explícitas:

```bash
if path contains /third_party/ → IGNORE
if warning starts with defender:: → BLOCKER
```

### Problemas de usar LLM

* no determinista
* difícil de auditar
* introduce dependencia innecesaria
* latencia y coste

### Cuándo sí usar LLM

* análisis semántico complejo
* correlación entre logs heterogéneos
* triage de incidentes ambiguos

Esto no aplica aquí.

### Recomendación

Implementar:

* script determinista
* whitelist/blacklist versionada
* fail fast en CI

---

# Q4 — Auditoría automática de dependencias Makefile

**Conclusión:**
EMECAS **no es suficiente**. Se recomienda añadir verificación explícita.

### Problema detectado

El bug:

* oculto por artefactos persistentes
* detectado solo con destrucción manual

Esto indica:

* dependencia implícita no declarada

### Riesgo

En hardware real:

* fallo en primer deploy
* no reproducibilidad

### Recomendación (industria)

Combinar:

### 1. Build limpio obligatorio en CI

Equivalente a:

```bash
git clean -xfd
make all
```

o entorno efímero (Docker/VM)

### 2. Target explícito

`make check-deps` puede validar:

* orden topológico
* targets no declarados

Pero más robusto:

### 3. Estrategia recomendada

* CI siempre en entorno limpio
* nunca confiar en builds incrementales
* usar herramientas como:

    * `ninja` (mejor tracking de deps)
    * o `cmake --graphviz`

### Conclusión práctica

* Mantener EMECAS
* Añadir **CI limpio obligatorio**
* `check-deps` es útil pero secundario

---

# Evaluación global (DAY 141)

### Fortalezas claras

* disciplina de build excepcional (`-Werror`, 0 warnings)
* separación limpia Variant A/B
* pipeline reproducible
* enfoque correcto hacia paper científico

### Riesgos aún activos

1. Identidad compartida → problema de seguridad y trazabilidad
2. Buffer libpcap no controlado → invalida benchmark
3. Dependencias implícitas → riesgo en despliegue real

### Prioridad inmediata (orden)

1. **Q2 — buffer_size (bloqueante FEDER)**
2. **Q1 — identidad separada**
3. **Q4 — CI limpio obligatorio**
4. Q3 — opcional (resolver con grep)

---

Si se ejecutan estos ajustes, el sistema pasa de “correcto y bien diseñado” a **robusto en condiciones reales de infraestructura crítica**.
