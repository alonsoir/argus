## Consejo de Sabios — Respuestas DAY 133

Evaluación basada en seguridad operativa real, principio de mínimo privilegio y verificabilidad empírica.

---

## Q1 — AppArmor (6 perfiles)

**Veredicto: 🟡 Correctos en dirección, requieren ajuste fino tras ejecución real**

### Observaciones críticas

#### 1. `deny` explícitos

* AppArmor es *default-deny*, pero:

  * `deny` explícitos **sí son útiles** para:

    * logging claro
    * evitar herencia accidental de permisos
* Recomendación:

  * Mantener `deny` en rutas sensibles:

    * `/root/**`
    * `/home/**`
    * `/sys/fs/bpf/**`

#### 2. Riesgo detectado: `network inet tcp`

* Demasiado amplio
* Recomendación:

  * restringir por:

    * puerto
    * rol del componente

---

#### 3. Ejecución entre componentes

```text
deny /opt/argus/bin/* x
```

✔ Correcto → evita lateral movement interno

---

#### 4. `/tmp` ejecución

```text
deny /tmp/** x
```

✔ Crítico mantener → evita dropper execution

---

### Punto crítico: sniffer + eBPF

El perfil debe asegurar:

* acceso mínimo a:

  * `/sys/fs/bpf`
  * `/proc`
* sin acceso generalizado a filesystem

---

## Q2 — Linux Capabilities

**Veredicto: ⚠️ Hay privilegios excesivos (especialmente `cap_sys_admin`)**

---

### 1. `cap_sys_admin` (ALERTA)

> Es esencialmente “root disfrazado”

#### Estado actual:

* usado para eBPF/XDP

#### En kernels ≥ 5.8:

✔ Existe alternativa:

* **CAP_BPF**
* **CAP_PERFMON**

### Recomendación obligatoria

| Caso           | Acción                               |
| -------------- | ------------------------------------ |
| Kernel ≥ 5.8   | usar CAP_BPF + CAP_PERFMON           |
| Kernel antiguo | fallback CAP_SYS_ADMIN (documentado) |

---

### 2. `cap_ipc_lock`

✔ Correcto para `mlock()`

Pero:

* puede requerir:

  * **CAP_SYS_RESOURCE**
    si RLIMIT_MEMLOCK es bajo

✔ Recomendación:

* probar sin `CAP_SYS_RESOURCE`
* añadir solo si falla

---

### 3. `cap_net_bind_service`

✔ No necesario si:

* puerto ≥ 1024 (2379 lo es)

✔ Alternativa:

* no cambiar sysctl global
* mantener puerto alto

---

## Q3 — Falco

**Veredicto: 🟢 Bien planteado, falta estrategia de maduración**

---

### Driver

✔ Elección correcta:

* `modern_ebpf`
  Motivo:
* compatibilidad
* menor fricción en VM

---

### Cobertura de reglas

Faltan dos patrones críticos:

#### 1. Exfiltración

```text
unexpected outbound connection
```

#### 2. Escalada de privilegios

```text
setuid/setcap inesperado
```

---

### Gestión de falsos positivos

**NO desactivar reglas**

Estrategia correcta:

1. Fase inicial:

  * Falco en modo alerta (no bloqueo)
2. Registrar:

  * baseline comportamiento normal
3. Refinar reglas
4. Solo entonces:

  * activar alertas críticas como blocking (si procede)

---

## Q4 — dist/ y flujo BSR

**Veredicto: 🟡 Aceptable en dev, débil en modelo de amenaza**

---

### 1. Shared folder (Vagrant)

✔ Aceptable para:

* desarrollo local
* demo FEDER

❗ Riesgo:

* no garantiza integridad
* posible manipulación desde host

---

### Recomendación mínima

Añadir verificación en hardened VM:

```bash
sha256sum -c SHA256SUMS || exit 1
```

✔ Ya previsto → correcto

---

### 2. Firma Ed25519

Problema:

* misma clave para:

  * plugins
  * binarios core

❗ Riesgo:

* compromiso de una clave → compromete todo

---

### Recomendación

Separar:

| Tipo          | Keypair   |
| ------------- | --------- |
| Core binaries | keypair A |
| Plugins       | keypair B |

---

## Q5 — Frase de fuzzing

> “Fuzzing misses nothing within CPU time”

**Veredicto: ❌ Incorrecta científicamente**

---

### Problema

Implica:

* cobertura completa
* exploración exhaustiva

Esto es falso.

---

### Qué hace realmente el fuzzing

* muestreo estocástico del espacio de inputs
* guiado por cobertura (coverage-guided fuzzing)
* explora zonas interesantes, no todo el espacio

---

### Reformulación propuesta (publicable)

> “Fuzzing does not guarantee full input space coverage, but it systematically explores input variations guided by code coverage, making it effective at discovering edge-case bugs and parser-level vulnerabilities that are difficult to reach with unit or property-based tests.”

---

### Versión más técnica (opcional)

> “Coverage-guided fuzzing provides probabilistic exploration of the input space, prioritizing paths that increase code coverage, but cannot prove the absence of defects.”

---

## Evaluación global DAY 133

### Fortalezas

* Separación BSR bien implementada
* Defensa en capas:

  * AppArmor (prevención)
  * Falco (detección)
* Pipeline reproducible

---

### Riesgos principales

1. `cap_sys_admin` → crítico reducir
2. firma unificada → punto único de fallo
3. fuzzing mal descrito en paper → riesgo reputacional

---

## Directiva del Consejo

Para DAY 134:

1. Migrar a CAP_BPF si kernel lo permite
2. Separar keypairs (plugins vs core)
3. Añadir reglas Falco de exfiltración
4. Corregir frase de fuzzing en paper
5. Ejecutar pipeline real → ajustar AppArmor iterativamente

---

## Veredicto final

* Arquitectura: **sólida**
* Seguridad: **avanzada pero no cerrada**
* Paper: **prometedor, requiere precisión**

---

El sistema está cruzando el punto clave: de diseño correcto a comportamiento real verificable.
