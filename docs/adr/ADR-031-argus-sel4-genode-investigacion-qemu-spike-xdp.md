# ADR-031: aRGus-seL4-Genode Variant (Investigación Pura)

**Status:** BACKLOG — RESEARCH — No bloqueante para roadmap actual  
**Fecha:** DAY 109 (2026-04-09)  
**Versión:** v3 — aprobada por Consejo de Sabios, sesión DAY 109  
**Autor:** Alonso Isidoro Román  
**Revisores:** Consejo de Sabios (ChatGPT5, DeepSeek, Gemini, Grok, Qwen) — unanimidad 5/5  
**Relacionado con:** ADR-030 (variante AppArmor, baseline de producción)

---

## Contexto

Ver ADR-030 §Contexto para motivación completa. Este ADR aborda la pregunta
científica que ADR-030 no puede responder:

> **¿Cuánto cuesta realmente la seguridad formal en rendimiento medible
> para un NDR como aRGus corriendo en hardware modesto?**

Mythos Preview demostró que el kernel Linux, con todas sus mitigaciones activas,
es vulnerable a encadenamiento de exploits que obtienen root completo. La única
arquitectura con garantías formales de corrección del kernel disponible hoy es
seL4, verificado en Isabelle/HOL con ~12.000 líneas de C probadas. El proyecto
Genode permite ejecutar Linux como guest no privilegiado supervisado por seL4.

Esta ADR es **investigación pura**. No es una variante de producción. El resultado
del benchmark — favorable o no — es la contribución científica.

### Axioma operativo (compartido con ADR-030)

> En entornos de amenaza avanzada, no puede asumirse la integridad del kernel Linux.
> aRGus define sus garantías como válidas dentro de su capa de detección.
>
> seL4 reduce el TCB del supervisor a ~12.000 líneas verificadas formalmente.
> Pero el guest Linux sigue siendo Linux: si el guest está comprometido, un
> atacante no puede escapar de la jaula seL4, pero las garantías de detección
> de aRGus se invalidan dentro del guest.
>
> **seL4 garantiza aislamiento, no integridad del guest.**

---

## Límite fundamental de la arquitectura (declaración crítica)

Este punto debe entenderse antes de leer el resto del ADR:

> seL4 garantiza que un guest comprometido no puede escapar a otros guests
> ni al supervisor. Pero **no garantiza la integridad del guest mismo**.
>
> Para aRGus, cuya misión es detección de comportamiento anómalo *dentro
> del guest*, esta distinción es crítica:
>
> - Si el guest Linux es comprometido, el atacante puede inyectar paquetes
    >   falsos en el datapath libpcap, corromper la memoria del ml-detector,
    >   o manipular el firewall-acl-agent para generar reglas incorrectas.
> - En todos estos casos, **las garantías de detección de aRGus se invalidan**,
    >   aunque el atacante permanezca confinado en el guest.
>
> Por tanto, seL4/Genode **no resuelve el threat model de aRGus** — reduce
> el blast radius de un compromiso. El hardening del guest (ADR-030) sigue
> siendo necesario incluso en esta arquitectura.
>
> Esta limitación se documentará explícitamente en el paper.

---

## Decisión

Crear la variante **aRGus-seL4-Genode** como experimento académico:

```
┌─────────────────────────────────────────┐
│      aRGus NDR pipeline                 │
│      (adaptaciones documentadas)        │
│      Red: fallback libpcap / virtio-net │
├─────────────────────────────────────────┤
│  Linux guest (Debian 13 minimal)        │
│  kernel 6.12 LTS hardened               │
│  (VM via Seoul VMM u equivalente)       │
│  XDP: ver §Hipótesis H1 — probablemente │
│  inviable, fallback libpcap obligatorio │
├─────────────────────────────────────────┤
│      Genode OS Framework 24.02+         │
│      (capability-based, sandboxing)     │
│      supervisor no verificado form.     │
├─────────────────────────────────────────┤
│         seL4 Microkernel                │
│    (~12.000 líneas C, Isabelle/HOL)     │
│    plataforma: hw (ARM64 / x86-64)      │
└─────────────────────────────────────────┘
```

**El Linux guest se ejecuta como VM no privilegiada.** El supervisor
Genode+seL4 proporciona aislamiento fuerte, pero el datapath de red pasa
por virtualización. Esto tiene consecuencias críticas para XDP — ver
§Hipótesis y §Riesgo crítico.

Arquitecturas objetivo: **ARM64** (Raspberry Pi 5 preferida) y **x86-64**.  
Validación inicial: **QEMU directamente** — Vagrant no es viable aquí.  
Benchmarks definitivos: bare-metal Raspberry Pi.

Nota: Se unifica en kernel 6.12 LTS para consistencia con ADR-030.

---

## Trusted Computing Base (TCB)

```
TCB del supervisor (verificado formalmente):
  - seL4 microkernel (~12.000 líneas C, proof en Isabelle/HOL)

TCB del supervisor (NO verificado formalmente):
  - Genode OS Framework (supervisor de componentes)

Guest (NO parte del TCB verificado):
  - Kernel Linux 6.12 LTS (guest no privilegiado)
  - aRGus runtime + dependencias
  - Debian 13 minimal userspace

Garantía real que ofrece seL4:
  Si el guest Linux es comprometido, el atacante está confinado
  en la jaula seL4/Genode. No puede afectar al supervisor ni a
  otros guests.

  Lo que seL4 NO garantiza:
  La integridad del pipeline aRGus dentro del guest comprometido.
  Un atacante dentro del guest puede manipular detección, memoria
  del ml-detector, y reglas del firewall.
```

---

## Hipótesis formales

Estas hipótesis serán validadas en el spike técnico.

**H1 — XDP inviable en guest:**
> XDP no es funcional en el guest Linux bajo Genode porque el datapath
> de red pasa por el supervisor (virtio-net), sin acceso directo a
> los descriptores DMA de la NIC física.

**H2 — Overhead de fallback libpcap:**
> El fallback a libpcap introduce una degradación de throughput del
> 40-60% respecto al baseline libpcap en Linux nativo, atribuible
> principalmente al overhead de virtualización Genode.

**H3 — Pipeline ejecutable con adaptaciones mínimas:**
> aRGus puede ejecutarse en el guest Linux con adaptaciones limitadas
> al mecanismo de captura (XDP→libpcap). ZeroMQ, ONNX Runtime y los
> plugins no requieren cambios funcionales dentro del guest.

Cada hipótesis tiene resultado binario GO/NO-GO en el spike.

---

## Alternativas consideradas

**1. Componentes nativos Genode (sin Linux guest)**
- Pros: TCB mínimo real, máximo aislamiento por componente
- Contras: reescritura completa del pipeline en C++ Genode, años de trabajo
- Decisión: descartada. Objetivo futuro a largo plazo si los benchmarks
  justifican la inversión.

**2. Linux guest completo (esta decisión)**
- Pros: pipeline aRGus ejecutable con adaptaciones mínimas
- Contras: TCB del guest sigue siendo Linux, XDP inviable (H1), overhead

**3. Linux DDE (Driver Development Environment de Genode)**
- Pros: drivers Linux en userspace sin VM completa, overhead potencialmente menor
- Contras: no ejecuta Debian completo, complejidad similar a reescritura parcial
- Decisión: evaluar como opción en el spike si VM completa es inviable

**4. KVM sobre Linux hardened**
- Pros: aislamiento fuerte, tooling maduro
- Contras: TCB mayor (kernel Linux + KVM), sin garantías formales
- Decisión: fuera de scope

---

## Riesgo crítico: XDP/eBPF

**Este es el punto técnico más importante del ADR.**

El sniffer de aRGus usa XDP hooks en el kernel Linux. En la variante seL4/Genode,
el kernel Linux guest no tiene acceso directo a la NIC física — el datapath
pasa por el supervisor Genode (virtio-net). Consecuencias:

- XDP en el guest **fallará** sin acceso directo a descriptores DMA — H1
- El fallback obligatorio es **libpcap** sobre la interfaz virtualizada
- Overhead esperado: 40-60% en throughput según benchmarks publicados
  de arquitecturas similares (papers Genode Foundation, L4Ka)

Esto invalida la afirmación "sin cambios en el código". Las adaptaciones
necesarias son:

```
1. sniffer: detección en runtime de disponibilidad XDP;
   fallback automático a libpcap si XDP no disponible
2. ZeroMQ: verificar comportamiento sobre socket virtualizado Genode
3. ONNX Runtime: verificar en guest ARM64 con kernel hardened
```

`dlopen()` dentro del guest Linux funciona con normalidad —
no es un punto de riesgo. Los plugins son accesibles desde el
filesystem del guest sin adaptación.

---

## Spike técnico previo (condición GO/NO-GO)

**Obligatorio antes de cualquier implementación.** Duración estimada: 2-3 semanas.
Si el spike da GO/NO-GO negativo, el ADR se archiva como "inviable" con
conclusiones publicables — ese también es un resultado científico válido.

### Preguntas a responder

1. ¿Arranca un Linux guest minimal sobre Genode+seL4 en x86-64 con QEMU+KVM?
2. ¿Confirma H1? ¿XDP inviable en el guest — fallback libpcap definitivo?
3. ¿Confirma H3? ¿ZeroMQ, ONNX Runtime, dlopen() funcionales en el guest?
4. ¿Qué versión de Genode tiene mejor soporte Linux guest en ARM64 (Pi 5)?
5. ¿Es viable Linux DDE como alternativa a VM completa?
6. ¿Cuál es el jitter de context switches bajo ZeroMQ? ¿Afecta al ml-detector?

### Deliverables del spike

- Script QEMU funcional reproducible que arranque Linux guest sobre Genode+seL4 x86-64
- Informe de viabilidad XDP (confirmación H1) con evidencia técnica
- Medición baseline de red en guest: `iperf3` + `pktgen` guest vs nativo
- Benchmark libpcap vs XDP en Linux nativo (baseline de comparación)
- Análisis de ZeroMQ latency y jitter bajo carga en guest virtualizado
- Confirmación de dlopen() y ONNX Runtime funcionales
- Informe GO/NO-GO con recomendación explícita

### Condición GO/NO-GO

**GO** si:
- Linux guest arranca y el pipeline es ejecutable con adaptaciones ≤ H3
- Overhead estimado < 5x baseline en latencia
- libpcap viable con > 10k PPS en hardware objetivo

**NO-GO** (archivar como "inviable") si:
- Overhead > 10x o libpcap < 1k PPS en hardware objetivo
- Pipeline fundamentalmente no ejecutable sin reescritura mayor

En caso de NO-GO: publicar el informe del spike como contribución científica.
"Las garantías formales cuestan X en rendimiento hoy y no son viables para
hardware de 150-200 USD" es un resultado honesto y publicable.

---

## Infraestructura de validación

**Vagrant NO es viable para esta variante.** Genode+seL4 requiere QEMU con
KVM habilitado y configuración específica del hipervisor. Vagrant abstrae
estas capas de forma incompatible.

```bash
# Validación x86-64 (portátil desarrollo, primera fase)
qemu-system-x86_64 \
  -machine q35 \
  -enable-kvm \
  -cpu host \
  -m 4G \
  -kernel genode-image.elf \
  -nographic

# Validación ARM64 bare-metal (segunda fase, tras spike x86)
# Imagen Genode compilada para hw/rpi4 o hw/rpi5
# Pi 5 preferida por soporte EL2 (virtualización ARM)
# NIC: Gigabit Ethernet integrada (Pi 5) o USB3 Gigabit (Pi 4)
```

**Estrategia de plataforma:**
- Fase 1: x86-64 con QEMU — validar concepto antes de comprar hardware
- Fase 2: Raspberry Pi 4 si soporte Genode estable en ARM64
- Fase 3: Raspberry Pi 5 si soporte EL2 maduro — mejor virtualización

Plataformas seL4 verificadas con soporte Genode:
- `x86-64` (verificación completa, más maduro)
- `ARM64 Raspberry Pi 4` (hw_rpi4, soporte parcial)
- `ARM64 Raspberry Pi 5` (virtualización EL2 más capaz, soporte en maduración)

---

## Baseline de referencia

Para atribuir correctamente el overhead observado, se medirán **tres puntos**:

```
Punto A: aRGus + XDP    en Linux nativo x86/ARM  → baseline máximo
Punto B: aRGus + libpcap en Linux nativo x86/ARM  → baseline libpcap
Punto C: aRGus + libpcap en Linux guest Genode/seL4 → experimento

Overhead XDP→libpcap     = (A - B) / A
Overhead de virtualización = (B - C) / B
Overhead total seL4        = (A - C) / A
```

Esto permite separar el coste del cambio de mecanismo de captura del coste
real de la virtualización seL4. Es esencial para la honestidad científica.

---

## Workload de benchmarks

Idéntico a ADR-030 para comparabilidad directa:

- **Dataset:** CTU-13 Neris pcap replay (Sebastian Garcia, stratosphereips.org)
- **Tráfico sintético:** 60% TCP / 30% UDP / 10% ICMP, tamaño medio 512 bytes
- **PPS objetivo:** 10k–100k (ajustado a capacidad hardware)
- **Herramienta de replay:** tcpreplay en modo timing preciso
- **Duración:** mínimo 10 minutos por run, 3 runs por métrica

---

## Métricas de evaluación

| Métrica | Herramienta | Umbral orientativo |
|---------|-------------|-------------------|
| Latencia paquete E2E (p50) | tcpreplay + timestamp | documentar (esperado 2-4x) |
| Latencia paquete E2E (p99) | tcpreplay + timestamp | documentar |
| Throughput libpcap (p50) | pktgen + iperf3 | documentar (esperado 40-60%) |
| Latencia ZeroMQ (p50) | benchmark interno | documentar |
| Jitter ZeroMQ bajo carga | benchmark interno | documentar |
| Inferencia ONNX | ml-detector benchmark | documentar |
| IPC latency Genode | genode benchmark | documentar |
| Context switches/s | perf stat en guest | documentar |
| Memoria RSS total | /proc/meminfo guest | documentar |
| Boot time total | cronómetro externo | documentar |
| Packet drop rate bajo carga | tcpreplay stats | documentar |
| Tamaño TCB supervisor | LOC seL4 + componentes Genode críticos | documentar |
| Complejidad de porting | person-days reales | documentar |

**Los umbrales son orientativos, no vinculantes.** El objetivo es documentar
la realidad, no pasar un test.

**Criterio de clasificación del resultado:**
- Overhead total < 2x Y libpcap > 50% baseline → "Viable con restricciones"
- Overhead 2-5x → "Experimental, solo hardware dedicado de alta gama"
- Overhead > 5x o pipeline inviable → "Research only, no recomendado
  para producción en hardware modesto"

En todos los casos: publicar. Esta clasificación se incluirá explícitamente
en el paper y documentación pública.

---

## Consecuencias

**Positivas:**
- Primer NDR open source con benchmark documentado sobre kernel formalmente verificado
- Contribución científica independiente del resultado — especialmente si confirma
  inviabilidad para hardware modesto (resultado honesto y publicable)
- Respuesta directa y medible a las implicaciones de Mythos Preview
- Desglose científico del overhead: virtualización vs cambio XDP→libpcap
- Posiciona aRGus en comunidades cs.CR, sistemas embebidos seguros,
  infraestructura crítica, y potencialmente comunidad Genode
- Potencial segundo paper independiente

**Negativas / Riesgos:**
- XDP probablemente inviable — fallback libpcap con overhead significativo
- Complejidad de setup Genode+seL4 con Linux guest (documentación escasa
  para este caso de uso específico)
- Overhead esperado 40-60% hace inviable para hardware de 150-200 USD
- Comunidad Genode pequeña (< 10k usuarios activos) — soporte limitado
- Mantenimiento: actualizaciones Genode/seL4 requieren recompilación y
  revalidación manual completa
- Soporte ARM64 (Pi 5) en Genode en maduración — puede requerir Pi 4 como
  primera plataforma ARM64
- Pérdida de tooling de debug dentro del guest
- Fragmentación potencial de codebase

**Oportunidad:** el trabajo de aRGus puede ser un caso de estudio relevante
para la comunidad Genode en cargas de trabajo de red intensivas. Colaboración
potencial con Genode Foundation.

---

## Dependencias

- ADR-030 completado — baseline AppArmor necesario para comparación
- ADR-025 (Plugin Integrity Verification) — DONE
- ADR-023 (Multi-Layer Plugin Architecture) — DONE
- Spike técnico (2-3 semanas) — MUST antes de implementación
- Hardware Raspberry Pi 5 (preferida) — BLOCKED
- Genode OS Framework 24.02+ — disponible, open source

---

## Estado en el roadmap

```
FASE ACTUAL:    PHASE 2b (rag-ingester integration)
FASE SIGUIENTE: PHASE 3 (fleet telemetry, XGBoost)
ADR-030:        BACKLOG — activar post PHASE 3
ESTA ADR:       BACKLOG/RESEARCH — activar post ADR-030 + spike GO
```

Se activa cuando:
1. Paper arXiv publicado y estabilizado
2. ADR-030 completado y baseline medido
3. Hardware Raspberry Pi disponible
4. Spike técnico completado con resultado GO

---

## Resultados (placeholder)

*Esta sección se completará tras el spike técnico y los benchmarks.*

| Punto | Métrica | Valor | Delta vs A |
|-------|---------|-------|-----------|
| A: XDP nativo | Throughput | — | baseline |
| B: libpcap nativo | Throughput | — | — |
| C: libpcap guest | Throughput | — | — |
| Clasificación final | — | — | — |

---

## Referencias

- Claude Mythos Preview: https://red.anthropic.com/2026/mythos-preview
- seL4 Foundation: https://sel4.systems
- Genode OS Framework: https://genode.org
- CTU-13 dataset: https://www.stratosphereips.org/datasets-ctu13
- seL4 formal verification paper: Klein et al., SOSP 2009
- AppArmor confused deputy analysis: Hugo Vázquez Caramés (LinkedIn, abril 2026)
- ADR-025: Plugin Integrity Verification
- ADR-030: aRGus-AppArmor-Hardened Variant

---

## Notas

Esta ADR nació de la misma conversación del DAY 108 que ADR-030. La pregunta
que motivó ambas es la misma — ¿qué significa asumir el kernel inseguro? —
pero las respuestas son diferentes:

- ADR-030 responde con ingeniería pragmática para el mundo real
- ADR-031 responde con ciencia honesta sobre el límite teórico alcanzable hoy

Si el spike muestra overhead > 5x y XDP inviable sin reescritura mayor, ese
resultado es igualmente valioso: demuestra que las garantías formales tienen
un coste real que el hardware de infraestructura crítica modesta no puede
pagar hoy. Eso es verdad medible y publicable.

Si el resultado sorprende — overhead aceptable, fallback libpcap funcional —
eso cambia la conversación completa sobre seguridad en infraestructura crítica
de organizaciones sin recursos.

Al publicar estos resultados — sean los que sean — estaremos definiendo el
coste real de la verdad. Eso es más que el 90% de los vendors comerciales.

*"La verdad por delante, siempre."*