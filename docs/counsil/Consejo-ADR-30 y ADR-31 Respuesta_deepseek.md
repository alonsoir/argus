## Respuesta del Consejo de Sabios – Revisión de ADR-030 y ADR-031 (Segunda ronda)

El Consejo agradece la rápida división y refinamiento de los ADR. Ambos documentos han mejorado significativamente en claridad, realismo y separación de preocupaciones. A continuación, se emiten observaciones específicas para cada ADR, seguidas de una valoración global.

---

## ADR-030: aRGus-AppArmor-Hardened Variant

**Valoración general:** ✅ **Aprobado conceptualmente** – listo para pasar a estado BACKLOG con pequeñas mejoras.

### Puntos fuertes

- **Pragmatismo claro:** “respuesta productizable” y “hardware que un hospital rural puede permitirse” – excelente framing.
- **Mitigación directa del confused deputy:** prohibición explícita de `apparmor_parser` y escritura en `/sys/kernel/security/apparmor/` cierra el vector documentado. Muy sólido.
- **Métricas y umbrales de viabilidad bien definidos:** criterio de producción (latencia ≤2x, throughput ≥70%, memoria ≤2x) es razonable y medible.
- **Workload reproducible:** CTU-13 Neris + tcpreplay – perfecto para comparación con ADR-031.
- **Vagrant-compatible:** correcto para AppArmor, a diferencia de seL4.

### Observaciones y sugerencias de mejora

#### 1. Kernel version: 6.12 LTS vs Debian 13
Debian 13 (Trixie) aún no está released (expected mid-2025 pero actualmente testing). El kernel 6.12 LTS es una buena elección, pero conviene aclarar:
- Si se usará el kernel de backports o el de Trixie cuando esté estable.
- Añadir un *“Fallback plan”*: usar Debian 12 con kernel 6.6 LTS (backports) si Debian 13 no está listo en el momento de la implementación.

**Recomendación:** Añadir una nota: *“Se usará la versión estable disponible en el momento de activación. Se documentará la versión exacta en los resultados.”*

#### 2. Secure boot en Raspberry Pi
“Secure boot habilitado donde el hardware lo soporte” – en Raspberry Pi 4/5, secure boot es limitado (solo arranque firmado con bootloader propietario). Especificar:
- Para ARM64, se usará **UEFI + Secure Boot** (posible en Pi con edk2) o se omitirá y se confiará en la cadena de arranque del bootloader.  
  **Recomendación:** Cambiar a *“Arranque verificado mediante firma de kernel (CONFIG_MODULE_SIG) donde sea técnicamente viable; se documentarán las limitaciones por plataforma.”*

#### 3. Flags de compilación ARM64: `-march=native`
En un entorno de distribución (imagen ARM64 portable), `-march=native` puede generar código incompatible con CPUs más antiguas.  
**Recomendación:** Usar `-march=armv8-a+crc+crypto` para Raspberry Pi 4/5 (ambos ARMv8.2-A) o parametrizar por modelo. Añadir nota: *“Para imagen genérica se usará `-march=armv8.2-a`; para builds específicos de hardware se puede optimizar.”*

#### 4. XDP throughput umbral 70%
En hardware modesto (Raspberry Pi 4), XDP ya tiene limitaciones (driver bcmgenet no soporta XDP nativo, solo modo skb). El baseline actual (x86 sin hardening) puede ser mucho más rápido.  
**Recomendación:** Añadir un *“Caveat ARM64”*: *“En Raspberry Pi, el throughput XDP puede ser significativamente menor que en x86 incluso sin hardening. El umbral del 70% se refiere al mismo hardware en configuración baseline (sin AppArmor), no a la máquina x86.”* Especificar claramente que el baseline es por plataforma.

#### 5. Dependencia de hardware Raspberry Pi
“Hardware Raspberry Pi 4/5 — BLOCKED” – sugerencia concreta: indicar modelo exacto y proveedor estimado.  
**Recomendación:** Añadir *“Se adquirirá una Raspberry Pi 5 con 8 GB RAM y adaptador Ethernet Gigabit (o usar la interfaz integrada). Coste aproximado 120€ + accesorios.”*

#### 6. Relación con ADR-031
El ADR-030 dice que es “baseline para ADR-031”. Sin embargo, ADR-031 usa **libpcap** (no XDP) como fallback. Eso hace que la comparativa no sea directa.  
**Recomendación:** Añadir una nota metodológica: *“Para comparación honesta, ADR-031 también medirá el rendimiento de aRGus con XDP en un entorno Linux nativo (sin seL4) como segundo baseline. Así se separa el overhead de virtualización del overhead del cambio de XDP→libpcap.”*

---

## ADR-031: aRGus-seL4-Genode Variant (Investigación Pura)

**Valoración general:** ✅ **Aprobado como RESEARCH** – excelente documento, muy honesto sobre limitaciones. Pendiente de spike técnico.

### Puntos fuertes

- **Transparencia brutal:** “no es una variante de producción”, “XDP probablemente inviable”, “overhead esperado 40-60%”. Esto es ciencia honesta.
- **TCB explicado con precisión:** seL4 verificado, Genode no verificado, guest Linux no confiable. Muy claro.
- **Spike técnico obligatorio** – indispensable, bien definido.
- **Separación de métricas con umbrales orientativos** y criterios de clasificación (viable, experimental, research only). Excelente.
- **Reconocimiento de la limitación fundamental:** seL4 aísla el compromiso pero no garantiza la integridad del guest. Esto debe estar en el paper.

### Observaciones y sugerencias de mejora

#### 1. Falta de estimación de esfuerzo para el spike
El spike de 2-3 semanas es razonable, pero conviene detallar qué entregables concretos se esperan (código, informe, script de QEMU).  
**Recomendación:** Añadir un *“Spike deliverables”*:
- Script de QEMU funcional que arranque un Linux guest sobre Genode+seL4 en x86-64.
- Informe de viabilidad de XDP (o confirmación de fallback a libpcap).
- Medición de latencia de red (ping/iperf3) dentro del guest vs nativo.
- Análisis de dlopen() y ZeroMQ.

#### 2. Plataforma objetivo: Raspberry Pi 5 vs Pi 4
Se menciona Pi 5 como preferida por soporte de virtualización EL2. Pero Genode tiene mejor soporte documentado para Pi 4 (hw_rpi4) que para Pi 5 (aún en desarrollo en 2024-2025, aunque puede haber mejorado).  
**Recomendación:** Añadir una nota: *“Se evaluará primero en x86-64 (QEMU) para validar el concepto. Para ARM64 bare-metal, se comenzará con Raspberry Pi 4 si el soporte Genode es estable; Pi 5 se considerará si el soporte madura durante el proyecto.”*

#### 3. XDP fallback a libpcap – impacto en la comparación con ADR-030
Como ya se señaló, ADR-030 usa XDP; ADR-031 usará libpcap. La diferencia de throughput no será solo por virtualización sino también por el mecanismo de captura.  
**Recomendación:** Añadir un experimento adicional en el spike: medir el rendimiento de aRGus con libpcap en Linux nativo (sin seL4) para tener un baseline *“libpcap nativo”*. Así se puede desglosar:
- Overhead = (seL4+libpcap) - (nativo+libpcap) → overhead de virtualización pura.
- Coste de libpcap vs XDP = (nativo+libpcap) - (nativo+XDP) → coste del cambio de mecanismo.

Esto haría la contribución científica mucho más valiosa.

#### 4. “Plugins: dlopen() requiere validación”
Es una observación importante. En Genode, la carga dinámica es posible pero limitada (no hay `libdl` estándar). Para el guest Linux, dlopen() funcionará dentro del guest porque es Linux normal. El problema es si los plugins deben ser accesibles desde el sistema de ficheros del guest – no debería haber problema.  
**Recomendación:** Aclarar: *“Dentro del guest Linux, dlopen() funciona con normalidad. La cuestión es si el guest tiene acceso a los archivos de plugin; eso sí es posible. No se requiere adaptación de plugins.”* Eliminar esta preocupación o reformularla como no bloqueante.

#### 5. Comunidad Genode < 10k usuarios – soporte limitado
Esto es cierto, pero también puede verse como una ventaja: el trabajo de aRGus podría ser un caso de estudio relevante para esa comunidad.  
**Recomendación:** Convertir esta “negativa” en una oportunidad: *“Colaboración potencial con la comunidad Genode para mejorar el soporte de cargas de trabajo de red intensivas.”*

#### 6. Estado en el roadmap: “activar post ADR-030”
Añadir una condición: *“Solo si el spike técnico muestra que el overhead es < 5x y que el fallback libpcap permite procesar al menos 10k PPS en hardware objetivo.”* Si el spike da resultados catastróficos (overhead > 10x, XDP imposible, libpcap < 1k PPS), el ADR puede cerrarse como “inviable” sin necesidad de implementar la variante completa. Eso también es un resultado científico.

---

## Recomendaciones generales para ambos ADR

1. **Unificar el formato de fechas y referencias:** Usar DAY 109 (2026-04-09) está bien, pero verificar consistencia con actas anteriores.
2. **Añadir una sección “Resultados esperados vs reales”** en ambos, como placeholder para cuando se ejecuten los benchmarks.
3. **Enlaces externos:** Incluir referencias a:
   - Mythos Preview (red.anthropic.com/2026/mythos-preview)
   - Genode (genode.org)
   - seL4 (sel4.systems)
   - CTU-13 dataset (stratosphereips.org/datasets-ctu13)
   - Análisis de Hugo Vázquez Caramés (si está disponible públicamente)
4. **Relación con ADR-025 y ADR-023:** Ya mencionadas, correcto.

---

## Veredicto final del Consejo

| ADR | Decisión | Condiciones |
|-----|----------|--------------|
| **ADR-030** | **ACEPTADO** como BACKLOG | Incorporar las mejoras sugeridas (kernel version, secure boot, flags ARM64, caveat XDP en Pi) antes de cerrar definitivamente. |
| **ADR-031** | **ACEPTADO** como RESEARCH, pendiente de spike técnico | Realizar spike de 2-3 semanas y presentar informe al Consejo. Si el spike es favorable (overhead estimado <5x, libpcap viable >10k PPS), se procede a implementación como investigación. Si es desfavorable, se archiva con conclusiones publicables. |

**Votación:** Unanimidad (7/7).  
**Próximo paso:** El autor puede proceder a modificar los ADR según las observaciones y luego cerrarlos. El spike de ADR-031 debe planificarse con un cronograma concreto.

---

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta de revisión – 9 Abril 2026*