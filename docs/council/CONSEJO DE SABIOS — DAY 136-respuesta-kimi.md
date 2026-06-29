## Kimi — Respuesta al Consejo de Sabios — DAY 136

*Evaluación de riesgos pre-FEDER con criterios de disponibilidad 24/7 en hospitales, reproducibilidad científica, y resistencia a adversarios.*

---

### Q1 — Riesgos técnicos/arquitectónicos pre-FEDER

He identificado **5 riesgos críticos** que deben resolverse antes del 1 de agosto. Los ordeno por impacto en la demo y en la operación hospitalaria real.

#### R1 — Single point of failure: un nodo, cero redundancia

**Estado actual:** El pipeline hardened es un único nodo. Si `argus-apt-integrity-check` dispara poweroff, el hospital queda sin protección. La demo FEDER mostrará un sistema que "funciona" pero no "resiste".

**Impacto demo:** Un revisor puede preguntar: *"¿Y si este nodo falla?"* La respuesta actual es *"El hospital queda desprotegido"*. Eso descalifica aRGus como solución de infraestructura crítica.

**Mitigación mínima para FEDER:** Documentar explícitamente la limitación y mostrar el **diseño** de HA (High Availability) aunque no esté implementado. La narrativa debe ser: *"v0.6 es single-node por diseño de MVP; v1.0 introduce quorum de 3 nodos con Consul/etcd raft"*. Sin esta narrativa, la demo parece incompleta, no intencionalmente minimalista.

**Mitigación real:** Implementar `argus-standby-attest` (DEBT-IRP-standby-001) con un segundo nodo en Vagrant que reciba heartbeat. No necesita ser producción-ready, necesita ser **demostrable**.

#### R2 — `hardened-full-with-seeds` rompe el BSR axiom

**Estado actual:** El target `hardened-full-with-seeds` (FEDER ONLY) integra seeds en el EMECAS. Esto viola la separación build/runtime que el propio paper §6.12 defiende.

**Impacto demo:** Si un revisor lee el Makefile y ve `hardened-full-with-seeds`, puede argumentar que el BSR axiom es teórico, no práctico. La contradicción entre el paper y el código socava la credibilidad.

**Mitigación:** Eliminar `hardened-full-with-seeds` del Makefile antes de FEDER. En la demo, ejecutar `hardened-full` seguido de `prod-deploy-seeds` como dos pasos explícitos, justificando: *"La separación build/runtime es estructural; el deploy de material criptográfico es una operación consciente post-provisioning"*. Esto refuerza el axioma, no lo debilita.

#### R3 — Falta de métricas de rendimiento en condiciones de carga

**Estado actual:** `check-prod-all` verifica seguridad, no rendimiento. No hay throughput medido, no hay latencia bajo carga, no hay packet loss documentado.

**Impacto demo:** La demo FEDER debe responder a *"¿Cuánto tráfico puede procesar?"* con un número, no con *"No lo hemos medido"*. ADR-041 propone métricas pero no hay datos.

**Mitigación:** Antes de FEDER, ejecutar el harness de ADR-041 con `tcpreplay` + `iperf3` y documentar:
- Throughput máximo sin packet loss (Variant A)
- Latencia p50/p99 captura→alerta→iptables
- CPU% y RAM RSS a carga sostenida

Sin estos números, la demo es una demostración de funcionalidad, no de viabilidad operacional.

#### R4 — RF embedded fallback no validado (ADR-042 F3)

**Estado actual:** El ADR-042 asume RF embedded como fallback con F1≈0.97. No se ha ejecutado el golden set contra RF embedded.

**Impacto demo:** Si durante la demo se simula un plugin unload y el fallback produce falsos negativos masivos, la demo se convierte en un desastre público.

**Mitigación:** Ejecutar `test-irp-rf-fallback-quality` (propuesto en revisión ADR-042) y documentar el resultado real. Si F1 < 0.995, no declarar RF como fallback operacional; declararlo como "fallback de investigación" que requiere supervisión humana.

#### R5 — DEBT-SEEDS-SECURE-TRANSFER-001: seeds via Mac host

**Estado actual:** Las semillas pasan por el host macOS via `/vagrant` shared folder. Esto es aceptable en desarrollo pero documentado como deuda.

**Impacto demo:** Un revisor de seguridad puede señalar que el pipeline de despliegue de semillas no es seguro. La respuesta *"Es solo para Vagrant"* no es satisfactoria si la demo se ejecuta en Vagrant.

**Mitigación:** Implementar `argus-seed-init` (generación local en hardened VM) como opción por defecto para la demo. Documentar que `prod-deploy-seeds` es el método legacy pre-P2P. Esto alinea la demo con la recomendación del Consejo (Opción C, generación local).

---

### Q2 — Diferencias de diseño XDP vs libpcap para el paper

Las diferencias deben documentarse como **contribución científica** con datos empíricos, no como opiniones de arquitectura.

#### D1 — Modelo de memoria: zero-copy vs kernel→userspace copy

| Aspecto | XDP (Variant A) | libpcap (Variant B) | Métrica publicable |
|---------|----------------|---------------------|-------------------|
| Copias de paquete | 0 (DMA→XDP frame→userspace mmap) | 1–2 (NIC→kernel sk_buff→userspace buffer) | Latencia p50 de captura |
| Context switches | 0 por paquete | 1 por paquete (poll/recvmsg) | CPU% a mismo throughput |
| Batch processing | Sí (XDP_TX, XDP_REDIRECT) | No (paquete a paquete) | Throughput máximo |

**Contribución científica:** Medir y publicar el **overhead de la copia kernel→userspace** en NDR. No existe en la literatura para sistemas NDR de código abierto.

#### D2 — Punto de decisión: driver NIC vs userspace

XDP ejecuta el programa eBPF en el **driver de la NIC**, antes de que el paquete llegue al stack TCP/IP del kernel. libpcap recibe el paquete **después** de que el kernel lo ha procesado (o en paralelo via `AF_PACKET`).

**Implicación para NDR:** Un paquete malicioso que explota una vulnerabilidad del stack TCP/IP (ej. CVE-2024-XXXX en IPv4 fragmentation) llega al kernel **antes** de que libpcap lo vea. XDP puede droparlo antes de que el kernel lo toque.

**Contribución científica:** XDP como **primera línea de defensa** vs libpcap como **observador**. Esto es una propiedad de seguridad, no solo de rendimiento.

#### D3 — Dependencia de hardware: NIC offload vs CPU polling

XDP requiere NICs con soporte de driver (Intel i40e, ixgbe, Mellanox mlx5). libpcap funciona con cualquier NIC que el kernel soporte.

**Implicación para ARM/Raspberry Pi:** Los drivers genéricos de RPi no soportan XDP nativo. libpcap es la única opción viable.

**Contribución científica:** La **portabilidad** como dimensión de diseño. Un sistema que solo funciona en NICs enterprise no es asequible para municipios. La Variant B demuestra que aRGus es viable en hardware commodity sin NICs especiales.

#### D4 — Programabilidad: eBPF C vs API fija

XDP permite programar lógica de filtrado en eBPF C (compilado a bytecode verificado por el kernel). libpcap usa BPF clásico (cBPF) con expresiones de filtro limitadas.

**Implicación para NDR:** XDP permite filtrado stateful (conteo de paquetes, detección de scans) en kernel space. libpcap delega todo al userspace.

**Contribución científica:** El **trade-off programabilidad vs portabilidad** como decisión de diseño documentada.

#### Tabla de métricas para el paper

| Métrica | XDP (x86) | libpcap (x86) | libpcap (ARM64) | Unidad |
|---------|-----------|---------------|-----------------|--------|
| Throughput máximo | ? | ? | ? | Mbps |
| Latencia p50 captura | ? | ? | ? | µs |
| Latencia p99 end-to-end | ? | ? | ? | ms |
| CPU% a 100 Mbps | ? | ? | ? | % |
| RAM RSS sniffer | ? | ? | ? | MB |
| Packet loss @ 1 Gbps | ? | ? | ? | % |
| NICs soportadas | Limitado | Universal | Universal | — |

*Valores a completar en DAY 137-138.*

---

### Q3 — Deudas preocupantes para infraestructura crítica

De las 6 deudas en `KNOWN-DEBTS-v0.6.md`, ordenadas por riesgo institucional:

| Deuda | Riesgo hospitalario | Prioridad pre-FEDER |
|-------|---------------------|---------------------|
| **DEBT-IRP-NFTABLES-001** | Un atacante que modifica `sources.list` puede apagar el nodo. El hospital queda sin protección. | 🔴 **Crítica** — resolver antes de FEDER |
| **DEBT-SEEDS-SECURE-TRANSFER-001** | Seeds expuestas en host de desarrollo. Si el Mac es comprometido, las claves de la flota lo son. | 🔴 **Crítica** — implementar generación local |
| **DEBT-COMPILER-WARNINGS-001** | ODR violations pueden causar comportamiento indefinido en producción. | 🟡 **Alta** — no bloqueante para demo, sí para certificación |
| **DEBT-IRP-QUEUE-PROCESSOR-001** | Si el webhook falla, la cola local no se procesa. El admin no sabe que ocurrió un incidente. | 🟡 **Alta** — post-FEDER aceptable |
| **DEBT-SEEDS-LOCAL-GEN-001** | Prerequisito de DEBT-SEEDS-SECURE-TRANSFER. | 🟡 **Alta** — implementar junto con transfer segura |
| **DEBT-SEEDS-BACKUP-001** | Sin backup de seeds, un fallo de disco = pérdida de identidad del nodo. | 🟢 **Media** — post-FEDER |

**Acción inmediata:** Crear `feature/irp-nftables-isolate` y `feature/seeds-local-gen` como ramas paralelas al `variant-b-libpcap`. El IRP y la seguridad de seeds no pueden esperar a post-FEDER si la demo incluye una simulación de incidente.

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **Q1 — Riesgos pre-FEDER** | 5 riesgos críticos identificados | Priorizar R1 (HA diseño) y R3 (métricas rendimiento) para la demo; R2 (BSR consistencia) para el paper |
| **Q2 — XDP vs libpcap** | 4 dimensiones de contribución científica | Completar tabla de métricas en DAY 137-138 con datos reales |
| **Q3 — Deudas críticas** | DEBT-IRP-NFTABLES-001 y DEBT-SEEDS-SECURE-TRANSFER-001 son bloqueantes para contexto hospitalario | Crear ramas paralelas, no secuenciales |

**Moción:** Propongo que el DAY 137 divida el equipo (o el tiempo) en tres tracks:
1. **Track rendimiento:** `feature/variant-b-libpcap` + medición comparativa XDP/libpcap
2. **Track seguridad:** `feature/irp-nftables-isolate` — implementar `argus-network-isolate` con iptables mangle (corrección del fallo F1 de ADR-042)
3. **Track criptografía:** `feature/seeds-local-gen` — implementar generación local de seeds en hardened VM

El merge de cualquiera de estas ramas a `main` requiere EMECAS completo. La demo FEDER debe mostrar al menos Track 1 completado y Tracks 2-3 en progreso documentado.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*