El ADR está **muy bien planteado a nivel de intención y honestidad técnica**. Se nota que no es humo: hay hipótesis falsables, métricas y consciencia de trade-offs. Eso ya lo coloca por encima de la mayoría de ADRs.

Dicho eso, para llevarlo a nivel “niquelado Consejo + paper-grade”, hay varios puntos donde puedes **refinar precisión, evitar ambigüedad y blindar críticas técnicas**.

Voy directo a lo importante.

---

# 🧠 1. Problema principal: mezcla de decisiones

Ahora mismo el ADR mezcla **2 decisiones distintas**:

1. Variante **seL4/Genode (cambio de TCB)**
2. Variante **AppArmor hardened (hardening incremental Linux)**

Esto genera ambigüedad:

> ¿ADR-026 trata de un cambio de modelo de seguridad o de hardening comparativo?

👉 Recomendación fuerte:

### 🔧 Divide o explicita claramente:

**Opción A (mejor):**

* ADR-026 → solo **seL4/Genode**
* ADR-026b (o ADR-030) → **Linux hardened baseline**

**Opción B (si quieres mantenerlo):**
Añade sección explícita:

```md
## Alcance de la decisión

Este ADR define dos variantes diferenciadas:

1. Variante A (Experimental): seL4 + Genode
2. Variante B (Baseline Hardened): Linux + AppArmor

Ambas existen únicamente para evaluación comparativa.
```

👉 Ahora mismo eso está implícito, pero no contractual.

---

# ⚠️ 2. Axioma demasiado fuerte (te lo van a atacar)

Esto:

> “Todo kernel Linux en producción debe asumirse potencialmente comprometido”

Es potente, pero **académicamente atacable**.

Problema:

* Es una afirmación absoluta
* No está matizada por threat model

👉 Mejor versión:

```md
Axioma operativo:
En entornos de amenaza avanzada (APT, zero-days, kernel exploits),
no puede asumirse la integridad del kernel Linux como garantía de seguridad base.

Por tanto, aRGus define sus garantías como válidas por encima del kernel,
no dependientes de él.
```

👉 Mantienes fuerza, pero evitas crítica fácil.

---

# 🧩 3. Falta definición clara del TCB

Estás hablando de seguridad seria, pero no defines explícitamente:

> **qué entra en el Trusted Computing Base**

👉 Añade sección:

```md
## Trusted Computing Base (TCB)

Variante estándar:
- Kernel Linux
- aRGus runtime
- Dependencias críticas (glibc, etc.)

Variante seL4:
- seL4 microkernel (formalmente verificado)
- Genode framework
- Linux guest (NO parte del TCB)
- aRGus runtime (parcialmente confiable)

Objetivo: reducir el TCB efectivo que puede comprometer la integridad del sistema.
```

👉 Esto le da mucha más solidez académica.

---

# 🔬 4. Métricas: falta una crítica

Las métricas están bien, pero falta algo clave:

👉 **definir carga de trabajo realista**

Ahora mismo dices:

* tcpreplay
* pktgen
* CTU13

Pero no defines:

* PPS esperado
* tamaño medio de paquetes
* mezcla de tráfico

👉 Añade:

```md
## Workload Definition

Las pruebas se ejecutarán sobre:
- Dataset CTU13 (botnet traffic)
- Tráfico sintético con distribución:
  - 60% TCP
  - 30% UDP
  - 10% ICMP
- Tamaño medio de paquete: 512 bytes
- Target: 10k–100k PPS (ajustado a hardware)
```

👉 Sin esto, los benchmarks son difíciles de reproducir/comparar.

---

# ⚙️ 5. Problema técnico serio (muy importante)

Esto:

> “El código de aRGus no requiere modificación”

⚠️ Esto es **optimista** y te lo pueden tumbar.

En Genode + seL4:

* networking no es igual
* acceso a interfaces no es trivial
* eBPF/XDP probablemente no funcione igual
* ZeroMQ puede comportarse distinto

👉 Mejor:

```md
Hipótesis de portabilidad:
Se espera que aRGus pueda ejecutarse sin cambios funcionales.
Sin embargo, se anticipan adaptaciones en:
- acceso a interfaces de red
- soporte de eBPF/XDP
- mecanismos de IPC

Estas adaptaciones se documentarán como parte del experimento.
```

👉 Esto te blinda.

---

# 🧪 6. Falta criterio de éxito (muy importante)

Ahora mismo dices:

> “publicar aunque sea malo”

Eso está bien, pero falta:

👉 ¿cuándo es viable?

Añade:

```md
## Criterio de viabilidad

La variante se considera viable para producción si:
- Latencia E2E ≤ 2x baseline
- Throughput ≥ 70% baseline
- Consumo de memoria ≤ 2x baseline

Si no se cumplen, la variante se clasifica como:
- "Experimental / Research-only"
```

---

# 🔐 7. AppArmor: ojo con el argumento

Citas el bug de Hugo Vázquez → bien
Pero cuidado:

👉 No implica que AppArmor sea inútil
👉 Solo que tiene limitaciones

Mejor redacción:

```md
El bug identificado en AppArmor evidencia limitaciones en modelos LSM
basados en políticas dinámicas, especialmente en escenarios de confused deputy.
No invalida su uso, pero refuerza la necesidad de evaluar modelos con
garantías formales en el kernel.
```

---

# 🧱 8. Mejora estructural (muy recomendada)

Añade esta sección:

```md
## Alternativas consideradas

1. Linux hardened únicamente
   - Pros: simplicidad, soporte completo
   - Contras: sin garantías formales

2. Hypervisor-based isolation (KVM)
   - Pros: aislamiento fuerte
   - Contras: mayor overhead, TCB mayor

3. seL4 + Genode (seleccionada)
   - Pros: kernel verificado formalmente
   - Contras: complejidad, tooling limitado
```

👉 Esto es obligatorio en ADRs sólidos.

---

# 🧠 9. Insight importante (esto es lo mejor de tu ADR)

Lo más potente que tienes es esto:

> separar seguridad de ejecución vs seguridad del conocimiento (ADR-025 vs ADR-028)

👉 Aquí estás añadiendo:

> seguridad de la **plataforma**

Eso te da un stack completo:

* ADR-025 → ejecución
* ADR-028 → memoria
* ADR-026 → plataforma

👉 Esto es paper-level.

---

# ✅ Veredicto

**Estado actual:**

* Muy sólido conceptualmente
* Bien motivado
* Científicamente honesto

**Para dejarlo perfecto:**

1. Separar variantes o clarificarlas
2. Suavizar axioma
3. Definir TCB explícito
4. Añadir workload reproducible
5. Corregir “sin cambios”
6. Añadir criterio de viabilidad
7. Incluir alternativas

---

Si quieres, en el siguiente paso puedo devolverte una **versión ADR-026 v2 ya reescrita** incorporando todo esto lista para pasar por Consejo sin fricción.
