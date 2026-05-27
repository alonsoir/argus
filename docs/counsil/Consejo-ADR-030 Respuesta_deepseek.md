## Respuesta del Consejo de Sabios – Revisión de ADR-026 (Borrador)

El Consejo ha analizado el borrador de ADR-026 *“aRGus Hardened Variant over Debian + seL4 (Genode)”* y agradece la iniciativa de abordar el impacto de Claude Mythos Preview y las vulnerabilidades de AppArmor. A continuación, se emiten observaciones estructuradas para mejorar el ADR antes de su formalización.

---

### 1. Problemas estructurales y de claridad

#### 1.1. La variante AppArmor está mal definida
El ADR menciona una **tercera variante** denominada `aRGus-apparmor-Hardened` con una stack reducida (Debian 13 + kernel hardened + AppArmor), pero no queda claro si esta variante es parte de la misma decisión o un ADR separado.  
**Recomendación:**
- Convertir la variante AppArmor en un **ADR independiente** (ADR-026b) o justificar por qué se incluye en el mismo documento.
- Si se mantiene unida, renombrar el ADR a algo como *“aRGus Hardened Variants: Genode/seL4 and AppArmor-only”* y añadir una tabla comparativa.

#### 1.2. La stack seL4/Genode necesita más precisión técnica
- No se especifica **qué versión de Genode** (¿23.05, 23.11, 24.02?).
- No se indica **cómo se integra aRGus** con el sistema de construcción de Genode (¿portar el pipeline a Genode's libc? ¿ejecutar aRGus en una VM Linux? ¿como proceso nativo Genode?).
- El diagrama muestra “Debian 12 + kernel Linux 6.1.x (guest no priv)”, pero ¿es una máquina virtual completa o un proceso Linux ejecutándose sobre la capa `linux` de Genode? La diferencia en overhead es abismal.

**Recomendación:** Añadir un apartado *“Implementation Sketch”* que describa la aproximación concreta:
- Usar `base-linux` de Genode (ejecutar aRGus como proceso nativo Genode con syscall emulación) o
- Usar `virtualbox` o `seoul` (VM) sobre Genode.  
  Sin esa decisión, las métricas de overhead no serán interpretables.

#### 1.3. Vagrantfile para seL4/Genode no es realista
> “irán cada una con su Vagrantfile, para comprobar que todo compila, arranca, etc.”

**Problema:** Genode no funciona dentro de Vagrant (requiere KVM con anidamiento muy específico, y seL4 necesita acceso directo a hardware o al menos QEMU con aceleración). Vagrant está orientado a máquinas virtuales Linux completas, no a microkernels.

**Recomendación:**
- Para la variante AppArmor, Vagrant sí es viable.
- Para la variante Genode/seL4, sustituir por un script de QEMU + `genode-build` toolchain. Proponer un `Makefile` que descargue Genode, compile la custom run script y lance QEMU con KVM.

---

### 2. Métricas y umbrales: falta realismo y contexto

| Métrica | Umbral propuesto | Crítica del Consejo |
|---------|------------------|----------------------|
| Latencia paquete E2E | < 2x baseline | ¿Baseline sobre qué? ¿x86 nativo sin ninguna hardening? Debe definirse claramente. Además, en seL4 la latencia puede ser >10x si se usa virtualización completa. |
| Throughput XDP | > 50% baseline | XDP **no funcionará** dentro de un guest Linux sin acceso directo a la NIC. Genode no pasa el driver de la NIC al guest de forma eficiente. Habrá que usar DPDK o un driver de Genode para la NIC, y aRGus debería ser adaptado. Este es un punto crítico que el ADR ignora. |
| Latencia ZeroMQ | < 3x baseline | ZeroMQ sobre el socket de Genode (que a su vez emula sockets Linux) puede ser mucho más lento. El umbral de 3x parece optimista. |

**Recomendación:**
- Cambiar la redacción: *“Umbrales orientativos, no vinculantes. El objetivo es documentar el overhead real, no pasar un test.”*
- Añadir una columna *“Riesgo de viabilidad”* para cada métrica (ej. XDP → incompatible).
- Incluir una métrica **“Complexity of porting aRGus (person-days)”** – estimación alta para seL4.

---

### 3. Dependencias y hardware: demasiado vagas

> “Hardware bare-metal para benchmarks (actualmente BLOCKED)”

**Problema:** ¿Qué hardware? Se necesita al menos una Raspberry Pi 4/5 (ARMv8) o una placa i.MX8. El ADR no especifica modelo, ni memoria, ni NIC.

**Recomendación:**
- Listar plataformas soportadas por Genode/seL4: `hw` (x86_64, ARM), `imx8q_evk`, `rpi4`, `rpi5`.
- Elegir una plataforma concreta para los benchmarks (ej. Raspberry Pi 5 con 8 GB RAM, NIC Gigabit Eth via PCIe).
- Definir un *“benchmark environment specification”* (kernel version, toolchain, switches de compilación).

---

### 4. Consecuencias negativas subestimadas

El ADR menciona “complejidad de setup” y “documentación escasa”, pero no aborda:

- **Mantenimiento a largo plazo:** ¿Quién actualizará la variante seL4 cuando Genode o seL4 cambien? ¿Se aceptarán regresiones?
- **Compatibilidad con plugins:** Los plugins asumen un sistema de ficheros Linux, syscalls, dlopen(). En Genode, `dlopen()` no existe; los plugins deberían ser componentes Genode compilados estáticamente. Esto rompe la arquitectura de plugins actual.
- **Seguridad real vs. percibida:** Un kernel seL4 verificado no garantiza que el guest Linux (Debian) esté libre de vulnerabilidades. La superficie de ataque sigue siendo enorme. El ADR debería reconocer que la ganancia real es limitada (aislamiento de compromiso del kernel guest, pero el guest sigue siendo Linux).

**Recomendación:**
- Añadir un apartado *“Limitaciones fundamentales”* que explique que seL4 protege el microkernel y el supervisor, pero **no** el guest Linux. La mejora principal es que si el guest es comprometido, no puede salirse de su jaula. Eso ya es valioso, pero no es “kernel seguro para aRGus”.
- Añadir un riesgo: *“Fragmentation de la codebase: dos variantes pueden divergir y duplicar esfuerzos de testing.”*

---

### 5. Estilo y formato

- **Fecha incorrecta:** “DAY 108 (2026-04-08)” – pero DAY 108 fue en realidad 2026-04-06 según actas anteriores. Revisar.
- **LaTeX/ASCII art:** El diagrama de stack usa caracteres simples, pero se puede mejorar para legibilidad.
- **Referencias externas:** Incluir enlaces a:
    - Claude Mythos Preview (red.anthropic.com)
    - Genode OS Framework (genode.org)
    - seL4 (sel4.systems)
    - Vulnerabilidad AppArmor (enlace al análisis de Hugo Vázquez Caramés)

---

### 6. Recomendación final del Consejo

**El ADR es prometedor pero necesita una revisión mayor antes de ser aceptado como BACKLOG.** Se sugiere:

1. **Dividir** en dos ADRs:
    - ADR-026a: Variante AppArmor (fácil, Vagrant, baja complejidad)
    - ADR-026b: Variante Genode/seL4 (compleja, hardware dedicado, investigación pura)

2. Para ADR-026b, añadir un **spike técnico** de 2-3 semanas para responder preguntas clave:
    - ¿Puede aRGus ejecutarse como proceso nativo Genode sin modificar el código?
    - ¿Cómo se manejan los plugins (dlopen, syscalls)?
    - ¿Qué rendimiento preliminar se obtiene con QEMU en x86?

3. **Aplazar la decisión final** hasta que el spike esté completo y se tengan datos preliminares (no solo promesas).

4. **Cambiar el estado** de BACKLOG a **RESEARCH** (nuevo estado propuesto) para reflejar que es experimental, no solo pendiente de recursos.

---

### Veredicto del Consejo

**No se aprueba el ADR en su forma actual.** Se invita al autor a presentar una versión revisada que incorpore las observaciones anteriores. El Consejo valora mucho la motivación ética y científica, pero la viabilidad técnica y la claridad deben ser sólidas antes de comprometer recursos.

*Quedamos a la espera de un ADR-026 revisado, o de una consulta adicional para discutir puntos específicos.*

**Votación:** Unanimidad (7/7) en las observaciones.  
**Responsable de la revisión:** Alonso Isidoro Román (autor).  
**Fecha límite para la nueva versión:** 15 Abril 2026 (próximo Consejo ordinario).

---

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta de revisión – 9 Abril 2026*