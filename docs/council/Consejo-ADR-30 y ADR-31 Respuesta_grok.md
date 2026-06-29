La división en **ADR-030** (pragmático, orientado a producción) y **ADR-031** (investigación pura) es una **excelente decisión**. Mejora mucho la claridad, evita mezclar objetivos contradictorios (producción vs. ciencia) y permite avanzar de forma más ordenada. Ambas ADRs están muy bien escritas, honestas y alineadas con la filosofía “La verdad por delante, siempre”.

A continuación, mi opinión detallada con puntos fuertes, riesgos reales (basados en el estado actual de Genode/seL4 en 2026) y propuestas concretas de mejora.

### Puntos fuertes generales (ambas ADRs)
- **Separación clara de objetivos**: ADR-030 es realista y accionable para hospitales/municipios con hardware modesto. ADR-031 es honesta sobre su carácter académico. Esto evita frustración futura.
- **Axioma operativo compartido** — muy potente y realista.
- **TCB explícito** en ambas — gran madurez. Especialmente bueno en ADR-031 al distinguir TCB del supervisor vs. guest.
- **Mitigación concreta del bug AppArmor (CrackArmor / confused deputy)** en ADR-030 → excelente, cierra directamente el vector documentado por Qualys en marzo 2026.
- **Benchmarks comparables** entre ambas (mismo workload CTU-13 Neris) → permite una comparación científica limpia.
- **Criterios de viabilidad y aceptación de resultados negativos** — muy profesional.
- **Notas finales** — refuerzan la ética del proyecto.

### Opinión específica sobre ADR-030 (AppArmor-Hardened)

**Muy sólido y listo para avanzar** (con pequeños ajustes).

**Fortalezas**:
- Enfoque incremental y productizable.
- Perfiles AppArmor + deny explícito a apparmor_parser y /sys/kernel/security/apparmor/** es una mitigación inteligente y directa del CrackArmor.
- Flags de kernel y compilación del pipeline bien elegidos.
- Vagrant + bare-metal Raspberry Pi es un plan realista.

**Mejoras recomendadas**:
1. **Kernel version**: Debian 13 (Trixie) se liberó en agosto 2025 con kernel 6.12 LTS y ya está en 13.4 (marzo 2026). Usa **6.12** como base (no menciones 6.12 como si fuera futuro). Si hay backports necesarios para drivers ARM64 específicos de Pi 4/5, menciónalo como riesgo menor.
2. **Umbrales de viabilidad**: Subir ligeramente el throughput a **> 70-75%** es razonable, pero considera añadir un umbral más suave para entornos sanitarios de baja velocidad de red (ej. < 1 Gbps). Por ejemplo: “Viable para enlaces ≤ 500 Mbps si latencia p50 < 1.5x y drop rate < 0.1%”.
3. **Añadir una métrica**: “**Superficie de ataque reducida**” (número de syscalls permitidas por seccomp, número de perfiles AppArmor, servicios deshabilitados). Es fácil de medir y muy comunicable.
4. **En Alternativas consideradas**: Puedes mencionar brevemente “Landlock + seccomp sin AppArmor” como opción aún más ligera (menor overhead, pero menos granular).

**Riesgo menor**: La calibración de perfiles AppArmor en modo complain requiere tiempo. Sugiero añadir en “Alcance” una fase explícita de “audit → generate → enforce” con herramientas como aa-genprof y aa-logprof.

### Opinión específica sobre ADR-031 (seL4-Genode)

**Bien estructurada, pero con realismo técnico necesario**. El spike técnico previo es **imprescindible** — has hecho bien en marcarlo como MUST.

**Fortalezas**:
- Honestidad brutal sobre limitaciones (XDP casi seguro inviable, overhead esperado, TCB del guest sigue siendo Linux).
- Distinción clara: seL4 protege el aislamiento del guest, pero no la integridad del guest.
- Alternativas consideradas (DDE-Linux, componentes nativos Genode, etc.) son muy completas.
- Infraestructura de validación con QEMU + KVM es correcta (Vagrant no sirve aquí).

**Realismo técnico actual (abril 2026)**:
- Genode 26.02 ya existe y sigue avanzando (DDE-Linux actualizado a kernel 6.18, mejoras en VMs).
- Soporte de **Linux guest virtualizado** sobre Genode+seL4 sigue siendo experimental en muchos escenarios, especialmente ARM64. En x86 es más maduro (Seoul VMM), pero en Raspberry Pi 5 el soporte de virtualización (EL2) está mejorando, aunque no es tan fluido como en x86.
- **XDP/eBPF en guest**: Muy probable que no funcione nativamente. El datapath pasa por el supervisor Genode → fallback a libpcap (o posiblemente AF_XDP si hay algún bridge) es realista. Tu sección “Riesgo crítico: XDP” es perfecta y debe mantenerse fuerte.
- Overhead: Tus estimaciones de 40-60% (o más en red) son conservadoras y realistas según literatura histórica de Genode/seL4 + VMs.

**Mejoras recomendadas**:
1. **Diagrama de stack** → hazlo aún más preciso:
   ```
   ┌─────────────────────────────────────────┐
   │      aRGus NDR pipeline                 │
   │      (adaptaciones mínimas documentadas)│
   ├─────────────────────────────────────────┤
   │  Linux guest (Debian 13 minimal)        │
   │  kernel 6.12 LTS hardened               │
   │  (VM via Seoul VMM u otro)              │
   │  Red: fallback libpcap / virtio-net     │
   ├─────────────────────────────────────────┤
   │      Genode OS Framework                │
   │      (capability-based, sandboxing)     │
   ├─────────────────────────────────────────┤
   │         seL4 Microkernel                │
   │    (formalmente verificado)             │
   └─────────────────────────────────────────┘
   ```
   Añade nota: “El Linux guest se ejecuta como VM no privilegiada. El supervisor Genode+seL4 proporciona aislamiento fuerte, pero el datapath de red pasa por virtualización.”

2. **Spike técnico** → amplía ligeramente los puntos a validar:
   - Soporte concreto de virtualización en ARM64 (RPi5 preferida por mejor EL2).
   - Posibilidad de pasar NIC vía passthrough o virtio-net de alto rendimiento.
   - Comportamiento de dlopen(), ZeroMQ y ONNX Runtime en el guest.
   - Overhead baseline solo de red (iperf3 + pktgen) antes de meter aRGus completo.

3. **En Riesgos** → añade:
   - Soporte de seL4/Genode en Raspberry Pi 5 sigue siendo más limitado que en x86 (virtualización dinámica menos madura en 2026).
   - Mantenimiento: actualizaciones de Genode/seL4 requieren recompilación completa de la imagen y re-validación del guest.

4. **Métricas** → está bien que sean “documentar” en vez de umbrales duros. Añade opcionalmente “**Tamaño del TCB supervisor** (líneas de código efectivas de seL4 + componentes Genode críticos)” como métrica cualitativa.

5. **Estado en roadmap**: Está correcto que se active **después de ADR-030**. El baseline de AppArmor-Hardened será oro para comparar.

### Sugerencias transversales
- **Consistencia entre ADRs**:
   - Usa el mismo nombre exacto para el workload (“CTU-13 Neris pcap replay con tráfico sintético 60/30/10”).
   - En ambas, menciona explícitamente que los resultados se publicarán (paper, blog, repositorio reproducible) independientemente del outcome.
- **Hardware**: Raspberry Pi 5 es claramente la mejor opción para ADR-031 (mejor soporte virtualización). Para ADR-030, Pi 4/5 son equivalentes.
- **Futuro a largo plazo** (puedes añadir una nota compartida): Si ADR-031 muestra overhead inaceptable, el siguiente paso lógico sería portar componentes críticos (sniffer, detector ML) como componentes nativos Genode (sin Linux guest), reduciendo aún más el TCB.

### Conclusión
- **ADR-030**: Casi listo para pasar a **PROPOSED**. Es la variante que realmente puede llegar a producción en hardware realista.
- **ADR-031**: Excelente como investigación. El spike decidirá si vale la pena invertir más o si el resultado negativo ya es una contribución valiosa por sí solo (“las garantías formales cuestan X en rendimiento hoy”).

La pareja de ADRs posiciona muy bien a **aRGus** como proyecto serio que responde con ingeniería + ciencia a amenazas reales como Mythos Preview y CrackArmor.

¿Quieres que te re-escriba alguna sección concreta (por ejemplo, el diagrama de stack, la sección de Riesgos de ADR-031, o el spike técnico)? ¿O prefieres que preparemos el template del informe del spike para ADR-031?

Estoy listo para la siguiente iteración. ¡Buen trabajo!