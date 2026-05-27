# RISKS.md

Este documento recoge los **riesgos arquitectónicos y limitaciones técnicas** del sniffer C++20 híbrido kernel/user-space (v3.1), desarrollado para kernels ≥6.12 y eBPF/XDP.

---

## 1. Dependencia excesiva de eBPF en kernel-space
- **Descripción:** El sniffer asume que el programa eBPF (`sniffer_xdp.o`) puede cargarse correctamente en el kernel.
- **Riesgo:** Si falla la carga (`bpf_prog_load`) por incompatibilidad de kernel, hardening de seguridad, o falta de permisos, se pierden **features críticas** del kernel-space.
- **Impacto:** Alto — puede dejar inoperante el pipeline de captura, ya que muchas features baratas y críticas viven en el kernel.
- **Mitigación propuesta:**
    - Clasificar features por criticidad: `critical / optimized / experimental`.
    - Implementar fallback en user-space para features críticas.
    - Detectar fallos en runtime y avisar/loguear para recalibración.

---

## 2. Dependencia del kernel moderno
- **Descripción:** El sniffer aprovecha características de kernels ≥6.12 (AF_XDP, RING_BUFFER, eBPF avanzado).
- **Riesgo:** Instalación en kernels antiguos o configuraciones limitadas de distribuciones cloud podría fallar o degradar severamente el rendimiento.
- **Impacto:** Medio-Alto — algunas features avanzadas no estarán disponibles y el rendimiento será menor.
- **Mitigación:**
    - Verificar la versión del kernel al iniciar.
    - Documentar requisitos mínimos en README y en el paquete `.deb`.
    - Posible fallback en user-space con coste de CPU adicional.

---

## 3. Multiplicidad de interfaces de red
- **Descripción:** La configuración original tenía la interfaz repetida en múltiples secciones (`kernel_space.interface`, `capture.interface`, `interface`).
- **Riesgo:** Inconsistencias y errores de configuración, especialmente si se intenta capturar tráfico de múltiples interfaces o en entornos virtualizados.
- **Impacto:** Medio — puede provocar captura incompleta o tráfico "raquítico".
- **Mitigación:**
    - Consolidar a **una sola interfaz configurable**.
    - Revisar scripts de provisión (`Vagrantfile`) y JSON config.

---

## 4. Backpressure y ZeroMQ avanzado
- **Descripción:** El pipeline depende de ZeroMQ para enviar eventos a la siguiente etapa.
- **Riesgo:**
    - Saturación del ring buffer o colas de usuario puede provocar pérdida de eventos.
    - Reconexiones de ZeroMQ mal configuradas pueden bloquear el pipeline.
- **Impacto:** Medio — afecta a la fiabilidad de entrega y rendimiento.
- **Mitigación:**
    - Configuración de HWM (`sndhwm`, `rcvhwm`) y batching cuidadosamente tunada.
    - Circuit breakers y adaptive rate limiting ya implementados.
    - Logs y alertas en caso de saturación.

---

## 5. Hardware desconocido en producción
- **Descripción:** Actualmente, el sniffer está diseñado para un entorno genérico de laboratorio.
- **Riesgo:** Si se despliega en hardware específico (NICs con offload, virtualización extrema, contenedores limitados), podría comportarse de forma impredecible.
- **Impacto:** Medio — afecta al rendimiento y precisión de features.
- **Mitigación:**
    - Documentar claramente los entornos soportados.
    - Implementar tests automáticos de benchmark en hardware objetivo.
    - Fallback configurable de features críticas a user-space.

---

## 6. Feature placement y auto-tuner
- **Descripción:** El auto-tuner para decidir qué features van a kernel o user-space está deshabilitado (`auto_tuner.enabled = false`).
- **Riesgo:** Si se habilita sin suficiente calibración, podría sobrecargar el kernel o degradar la agregación de features.
- **Impacto:** Bajo-Medio — afecta a rendimiento, no funcionalidad.
- **Mitigación:**
    - Mantener auto-tuner deshabilitado hasta pruebas controladas.
    - Ejecutar benchmark extensivo antes de habilitar en producción.
      risk
---

### Notas finales
- Este documento refleja riesgos **técnicos y arquitectónicos**, no bugs puntuales.
- Todos los riesgos deben considerarse en cualquier publicación, paper o despliegue industrial.
- La intención es mantener la **integridad del pipeline** y asegurar que las decisiones de diseño estén justificadas.


# RISKS.md - Visual Version

Este documento recoge los **riesgos arquitectónicos y limitaciones técnicas** del sniffer C++20 híbrido kernel/user-space (v3.1), desarrollado para kernels ≥6.12 y eBPF/XDP.

| #  | Riesgo / Limitación                                   | Prioridad | Impacto | Descripción | Mitigación |
|----|------------------------------------------------------|-----------|---------|-------------|------------|
| 1  | Dependencia de eBPF en kernel-space                 | High      | Alto    | Si falla la carga del programa eBPF (`sniffer_xdp.o`), se pierden features críticas del kernel. | Clasificar features por criticidad, fallback en user-space, detectar fallos en runtime y loguear. |
| 2  | Dependencia del kernel moderno                        | High      | Medio-Alto | Requiere kernels ≥6.12; en kernels antiguos el sniffer puede degradar o fallar. | Verificar versión del kernel al inicio, documentar requisitos, fallback en user-space. |
| 3  | Multiplicidad de interfaces de red                   | Medium    | Medio   | Interfaz repetida en varias secciones del JSON puede provocar captura incompleta o inconsistencias. | Consolidar a una sola interfaz configurable, revisar scripts y config JSON. |
| 4  | Backpressure y ZeroMQ avanzado                        | Medium    | Medio   | Saturación del ring buffer o colas de usuario puede provocar pérdida de eventos o bloqueos. | Tunear HWM y batching, circuit breakers, adaptive rate limiting, logs y alertas. |
| 5  | Hardware desconocido en producción                   | Medium    | Medio   | Desempeño impredecible en NICs específicas, virtualización o contenedores limitados. | Documentar entornos soportados, tests de benchmark, fallback a user-space para features críticas. |
| 6  | Feature placement / Auto-tuner                       | Low       | Bajo-Medio | Habilitar auto-tuner sin calibración puede sobrecargar kernel o degradar agregación de features. | Mantener auto-tuner deshabilitado hasta pruebas controladas, ejecutar benchmarks antes de habilitar. |

---

## Notas generales
- Este documento refleja riesgos **técnicos y arquitectónicos**, no bugs puntuales.
- Todos los riesgos deben considerarse en cualquier publicación, paper o despliegue industrial.
- La intención es mantener la **integridad del pipeline** y asegurar que las decisiones de diseño estén justificadas.

---

**Leyenda de prioridad:**
- **High:** Riesgo crítico que puede inutilizar el pipeline.
- **Medium:** Riesgo importante que degrada rendimiento o confiabilidad.
- **Low:** Riesgo menor, principalmente de optimización o rendimiento.
