Este **ADR-026** es una declaración de intenciones de alto nivel. Muestra que **aRGus** no solo quiere ser una herramienta útil, sino una arquitectura defensiva de vanguardia que responde a las amenazas de la "Era de la IA Autónoma" (Mythos Preview).

Como **Consejo de Sabios**, aplaudimos la honestidad técnica de reconocer las limitaciones del kernel Linux. Sin embargo, para que este ADR pase de ser una aspiración a un plan de ingeniería ejecutable en el futuro, sugerimos los siguientes ajustes y precisiones:

---

### 🏛️ Recomendaciones del Consejo de Sabios

#### 1. Clarificación del Modelo de Aislamiento (Genode/seL4)
Para que la variante **Genode-Hardened** tenga sentido, no basta con "correr Debian encima". El valor real de Genode es la **micro-componentización**.
* **Propuesta:** En lugar de una VM Debian monolítica sobre seL4, el objetivo a largo plazo debería ser que cada componente de aRGus (`sniffer`, `ml-detector`, etc.) corra en su propio **componente Genode aislado**.
* **Razón:** Si el kernel Linux "guest" se compromete, el atacante sigue teniendo acceso a todo el pipeline. Si cada componente está aislado por seL4, un compromiso en el `sniffer` no permite escalar al `firewall-acl-agent`.



#### 2. El Problema del "I/O Path" (Rendimiento)
Has identificado correctamente que el overhead será serio. En arquitecturas de microkernel, el paso de mensajes (IPC) y el acceso a hardware (NIC) son los cuellos de botella.
* **Sugerencia:** Añade a las métricas de evaluación el impacto de **"Context Switches"**. En seL4, el paso de paquetes desde la red física al `sniffer` (pasando por el monitor de Genode) puede multiplicar la latencia.
* **Técnica:** Considera mencionar el uso de **VirtIO** o **Direct Device Assignment** si el hardware lo permite, para mitigar la penalización de throughput.

#### 3. AppArmor: Del "Confused Deputy" al "Strict Enforcement"
Respecto a la variante **aRGus-apparmor-Hardened**:
* **Mejora:** No basta con aplicar AppArmor. El ADR debería especificar que se usará el modo **"Complain/Enforce"** con perfiles generados por aprendizaje previo (audit mode).
* **Fix específico:** Para mitigar el problema de Hugo Vázquez Caramés, la política debe prohibir explícitamente que los agentes de aRGus puedan invocar herramientas de gestión de AppArmor (`/sbin/apparmor_parser`), cerrando el círculo del "confused deputy".

#### 4. Hardware Target: El factor ARM
Pasar a ARM para el test bare-metal (Raspberry Pi 4/5) es una decisión brillante porque:
1. seL4 tiene un soporte excelente en ARM.
2. Es el hardware real de tus usuarios (hospitales rurales, escuelas).
* **Punto crítico:** Genode en ARM tiene particularidades con los drivers de red. Asegúrate de incluir en "Riesgos" la posible necesidad de escribir/adaptar drivers de red específicos para el microkernel.

---

### 🛡️ Análisis de Riesgos y Viabilidad

| Desafío | Nivel de Riesgo | Mitigación Propuesta |
| :--- | :--- | :--- |
| **Curva de aprendizaje** | Muy Alta | Iniciar con una "Hello World" de Genode antes de intentar portar el pipeline. |
| **Latencia ML** | Media | Medir si el IPC de seL4 afecta la comunicación ZeroMQ entre el detector y el ingester. |
| **XDP/eBPF** | Crítica | Linux como guest en Genode suele perder el acceso directo a XDP. Podría ser necesario un fallback a `libpcap` estándar. |

---

### 📝 Resumen de Cambios Sugeridos al ADR

1.  **D11 (Nuevo):** Especificar que la variante Genode buscará la **descomposición del pipeline** en componentes nativos de Genode a largo plazo.
2.  **Métricas:** Añadir "IPC Latency" y "Packet Drop Rate under Load".
3.  **Hardware:** Priorizar la Raspberry Pi 5 por su mejor soporte de virtualización (instrucciones EL2) que facilitará la ejecución del Linux guest sobre seL4.



### 🏁 Veredicto Preliminar
**ESTADO: ACEPTADO EN EL BACKLOG.**

Es un ADR ambicioso que sitúa a **aRGus** en la "Champions League" de la seguridad OS. La comparación entre Debian 13 (AppArmor) vs seL4 (Genode) será un paper científico por sí solo de altísimo impacto.

**¿Quieres que preparemos un pequeño "Checklist de Pre-requisitos" para cuando decidas activar este ADR del backlog?** 🏛️🛡️🚀