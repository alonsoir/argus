# ADR-030: aRGus-AppArmor-Hardened Variant

**Status:** BACKLOG — No bloqueante para roadmap actual  
**Fecha:** DAY 109 (2026-04-09)  
**Versión:** v3 — aprobada por Consejo de Sabios, sesión DAY 109  
**Autor:** Alonso Isidoro Román  
**Revisores:** Consejo de Sabios (ChatGPT5, DeepSeek, Gemini, Grok, Qwen) — unanimidad 5/5  
**Relacionado con:** ADR-031 (variante seL4/Genode, investigación pura)

---

## Contexto

El 7 de abril de 2026, Anthropic publicó la evaluación de Claude Mythos Preview
(red.anthropic.com/2026/mythos-preview), demostrando capacidad autónoma de identificar
y encadenar vulnerabilidades del kernel Linux para obtener escalada de privilegios local,
incluyendo encadenamiento de múltiples CVEs para obtener root completo.

En paralelo, Hugo Vázquez Caramés documentó públicamente un bug de tipo confused deputy
en AppArmor (ficheros .load/.replace/.remove con permisos 0666): AppArmor validaba el
proceso que hacía el write(), no el que abría el fd, permitiendo que un proceso sin
privilegios pasara un fd abierto a un proceso privilegiado para cargar política en su
nombre. Esto evidencia limitaciones reales en modelos LSM basados en políticas dinámicas.

Estos eventos motivan dos respuestas arquitectónicas diferenciadas:

- **ADR-030 (este documento):** Hardening incremental realista sobre Linux, orientado
  a producción en hardware modesto. Vagrant-compatible. Target: hospitales y municipios.
- **ADR-031:** Investigación pura sobre seL4/Genode con kernel formalmente verificado.
  No es producción, es ciencia. Ver ADR-031 para detalles.

### Axioma operativo

> En entornos de amenaza avanzada — APT, zero-days, kernel exploits de la clase
> demostrada por Mythos Preview — no puede asumirse la integridad del kernel Linux
> como garantía de seguridad base.
>
> aRGus define sus garantías como válidas dentro de su capa (detección de comportamiento
> anómalo de red). Si el kernel del host está comprometido, las garantías de detección
> se invalidan. El hardening del host es responsabilidad del operador. Esta variante
> reduce materialmente la superficie de ataque sin eliminarla por completo.

---

## Decisión

Crear la variante **aRGus-AppArmor-Hardened** con la siguiente stack:

```
┌─────────────────────────────────────────┐
│      aRGus NDR pipeline (sin cambios)   │
├─────────────────────────────────────────┤
│         Debian 13 (Trixie) minimal      │
│    kernel 6.12 LTS + hardening flags    │
│    AppArmor enforce — perfil por        │
│    componente (fase audit → enforce)    │
│    seccomp-bpf + namespaces + cgroups   │
└─────────────────────────────────────────┘
```

Arquitecturas objetivo: **ARM64** (Raspberry Pi 4/5) y **x86-64**.  
Validación inicial: Vagrant (ARM64 emulado vía QEMU bajo VirtualBox/UTM).  
Benchmarks definitivos: bare-metal Raspberry Pi.

Nota de versión: Se unifica en kernel 6.12 LTS para consistencia entre variantes.
Debian 13 (Trixie) está disponible desde agosto 2025 en versión estable (13.4 a
marzo 2026). Si en el momento de activación hubiera razón técnica para usar Debian 12
con kernel 6.6 LTS backports, se documentará como fallback y se especificará en los
resultados.

---

## Trusted Computing Base (TCB)

```
Variante estándar (baseline):
  - Kernel Linux (sin hardening)
  - aRGus runtime + dependencias

Esta variante (AppArmor-Hardened):
  - Kernel Linux 6.12 LTS con flags de hardening
  - AppArmor enforcing por componente
  - aRGus runtime + dependencias mínimas
  - TCB reducido por eliminación de servicios innecesarios
```

El TCB sigue incluyendo el kernel Linux — no hay garantías formales. La mejora
es reducción de superficie de ataque, no eliminación de riesgo. Esta distinción
es intencionada y honesta.

---

## Threat Model

**Protege contra:**
- Escalada de privilegios en userland
- Movimiento lateral entre componentes aRGus
- Abuso de syscalls no necesarias
- Persistencia vía filesystem
- Abuso de interfaces de gestión AppArmor (confused deputy)

**No protege contra:**
- Compromiso del kernel Linux (requeriría ADR-031)
- Exploits zero-day en el kernel de la clase demostrada por Mythos Preview
- Ataques físicos o DMA
- Actor estatal con capacidades Mythos-class dirigido específicamente al host

---

## Alternativas consideradas

**1. Sin hardening (baseline actual)**
- Pros: simplicidad, soporte completo, sin overhead
- Contras: superficie de ataque máxima

**2. Landlock + seccomp sin AppArmor**
- Pros: más ligero, menor overhead, sin daemon de políticas
- Contras: menos granular, sin protección de paths de fichero dinámica
- Decisión: documentar como variante alternativa si AppArmor overhead es inaceptable

**3. AppArmor hardened (esta decisión)**
- Pros: realista para producción, Vagrant-compatible, hardware modesto viable,
  mitigación directa del confused deputy vector documentado
- Contras: sin garantías formales del kernel, perfiles requieren calibración

**4. seL4/Genode (ADR-031)**
- Pros: kernel formalmente verificado
- Contras: XDP incompatible, overhead 40-60% estimado, investigación pura

---

## Alcance del hardening

### Kernel 6.12 LTS — flags de compilación

```
CONFIG_HARDENED_USERCOPY=y
CONFIG_FORTIFY_SOURCE=y
CONFIG_STACKPROTECTOR_STRONG=y
CONFIG_CFI_CLANG=y              # donde aplique en ARM64
CONFIG_INIT_ON_ALLOC_ZERO_PAGES=y
CONFIG_INIT_ON_FREE_ZERO_PAGES=y
CONFIG_RANDOMIZE_BASE=y         # KASLR
CONFIG_STRICT_KERNEL_RWX=y
CONFIG_DEBUG_WX=y
```

### AppArmor — mitigación del confused deputy

Proceso de generación de perfiles: `audit mode` → `aa-genprof` / `aa-logprof`
→ revisión manual → `enforce mode`.

Perfil base aplicado a **cada componente aRGus** para mitigar directamente
el vector del bug documentado por Hugo Vázquez Caramés:

```apparmor
# Perfil base por componente aRGus
# Mitiga confused deputy: previene que un componente comprometido
# cargue política AppArmor en nombre del sistema

deny /sys/kernel/security/apparmor/** w,
deny /etc/apparmor.d/** w,
deny /sbin/apparmor_parser rwx,
deny capability dac_override,
deny capability sys_ptrace,
deny /proc/sys/kernel/cap_last_cap w,
```

Nota: estos perfiles reducen significativamente la superficie de explotación
del vector confused deputy. No eliminan el bug en el LSM subyacente — eso
corresponde al mantenedor del kernel. La mitigación opera en la capa de
capacidades de los componentes aRGus.

### Hardening adicional

- `seccomp-bpf`: whitelist de syscalls por componente
- Namespaces: network, PID, mount por servicio
- Cgroups v2: límites de memoria y CPU por componente
- Filesystem: `/` y directorios de binarios en modo read-only
- Provisioning: ADR-025 (Ed25519 + seed.bin) sin modificación
- Imagen mínima: sin compiladores, sin herramientas de debug en producción
- Arranque verificado mediante firma de kernel (`CONFIG_MODULE_SIG`) donde
  sea técnicamente viable. En Raspberry Pi las limitaciones de secure boot
  se documentarán por plataforma.

### Flags de compilación del pipeline aRGus (ARM64)

```
-O2 -march=armv8.2-a -pipe
-fstack-protector-strong
-fPIE -pie
-D_FORTIFY_SOURCE=2
-Wl,-z,relro -Wl,-z,now
-fvisibility=hidden
```

Nota: se usa `-march=armv8.2-a` (compatible con Raspberry Pi 4/5, ambos ARMv8.2-A)
en lugar de `-march=native` para garantizar portabilidad de la imagen ARM64.
Para builds específicos de hardware puede optimizarse con `-march=native`.

---

## Baseline de referencia

Todas las métricas se comparan contra:

- aRGus ejecutando en Debian 13 estándar
- Kernel 6.12 sin hardening adicional
- Mismo hardware (misma Raspberry Pi o x86 equivalente)
- Mismo workload (pcap replay idéntico, ver §Workload)

El baseline x86-64 está disponible de mediciones anteriores en entorno Vagrant.
El baseline ARM64 bare-metal se medirá antes de las comparativas finales,
en la misma sesión de benchmarks.

---

## Workload de benchmarks

- **Dataset:** CTU-13 Neris pcap replay (Sebastian Garcia, stratosphereips.org)
- **Tráfico sintético:** 60% TCP / 30% UDP / 10% ICMP, tamaño medio 512 bytes
- **PPS objetivo:** 10k–100k (ajustado a capacidad hardware)
- **Herramienta de replay:** tcpreplay en modo timing preciso
- **Duración:** mínimo 10 minutos por run, 3 runs por métrica
- **Herramienta de red base:** iperf3 para throughput, pktgen para stress

---

## Métricas de evaluación

| Métrica | Herramienta | Umbral de viabilidad |
|---------|-------------|----------------------|
| Latencia paquete E2E (p50) | tcpreplay + timestamp | < 2x baseline |
| Latencia paquete E2E (p99) | tcpreplay + timestamp | documentar |
| Throughput XDP (p50) | pktgen | > 70% baseline |
| Latencia ZeroMQ (p50) | benchmark interno | < 2x baseline |
| Inferencia ONNX | ml-detector benchmark | < 2x baseline |
| Memoria RSS total | /proc/meminfo | documentar |
| Boot time | systemd-analyze | documentar |
| Context switches/s | perf stat | documentar |
| Packet drop rate bajo carga | tcpreplay stats | documentar |
| Syscalls permitidas (seccomp) | seccomp-tools | documentar |
| Servicios deshabilitados | systemctl list-units | documentar |

**Criterio de viabilidad para producción:**
Latencia E2E p50 ≤ 2x baseline Y throughput ≥ 70% baseline Y memoria ≤ 2x baseline.

Umbral alternativo para enlaces ≤ 500 Mbps (entorno hospitalario típico):
Latencia p50 < 1.5x Y drop rate < 0.1% → "Viable para infraestructura de baja
velocidad" aunque no supere el umbral general.

Si no se cumplen → "Experimental, no recomendado para producción en hardware
equivalente". Publicar igualmente.

---

## Consecuencias

**Positivas:**
- Hardening realista ejecutable en hardware de 150-200 USD (Raspberry Pi 4/5)
- Vagrant-compatible para validación previa a bare-metal
- Mitigación directa y auditable del confused deputy vector de AppArmor
- Baseline comparativo para ADR-031
- Sin cambios en el código del pipeline aRGus
- Imagen mínima ARM64 publicable y reproducible
- Superficie de ataque medible y documentada (syscalls, servicios, perfiles)

**Negativas / Riesgos:**
- Sin garantías formales del kernel — AppArmor es bypasseable
- Perfiles AppArmor requieren calibración por entorno (fase audit obligatoria)
- Kernel 6.12 puede requerir backport de drivers ARM64 específicos
- Pérdida de observabilidad en producción (logs, debug limitados por seccomp/AppArmor)
- Dificultad de troubleshooting en entornos muy restringidos
- Divergencia potencial de codebase si las variantes requieren configuración distinta
- Driver bcmgenet (Pi 4) no soporta XDP nativo — solo modo skb. El baseline
  ARM64 ya refleja esta limitación; los umbrales se aplican sobre el baseline
  del mismo hardware, no sobre x86.

---

## Dependencias

- ADR-025 (Plugin Integrity Verification) — DONE
- ADR-023 (Multi-Layer Plugin Architecture) — DONE
- Debian 13 (Trixie) estable — DISPONIBLE (13.4, marzo 2026)
- Hardware Raspberry Pi 4/5 — BLOCKED (pendiente adquisición)
- Baseline x86-64 sin hardening — DISPONIBLE

---

## Estado en el roadmap

```
FASE ACTUAL:    PHASE 2b (rag-ingester integration)
FASE SIGUIENTE: PHASE 3 (fleet telemetry, XGBoost)
ESTA ADR:       BACKLOG — activar post PHASE 3
```

Se activa cuando:
1. Paper arXiv publicado y estabilizado
2. Hardware Raspberry Pi disponible
3. Roadmap principal completado PHASE 3

---

## Resultados (placeholder)

*Esta sección se completará cuando se ejecuten los benchmarks.*

| Métrica | Baseline ARM64 | AppArmor-Hardened | Delta |
|---------|----------------|-------------------|-------|
| Latencia E2E p50 | — | — | — |
| Throughput XDP | — | — | — |
| Memoria RSS | — | — | — |
| Clasificación | — | — | — |

---

## Referencias

- Claude Mythos Preview: https://red.anthropic.com/2026/mythos-preview
- CTU-13 dataset: https://www.stratosphereips.org/datasets-ctu13
- seL4 Foundation: https://sel4.systems
- Genode OS Framework: https://genode.org
- AppArmor confused deputy analysis: Hugo Vázquez Caramés (LinkedIn, abril 2026)
- ADR-025: Plugin Integrity Verification
- ADR-031: aRGus-seL4-Genode Research Variant

---

## Notas

Esta ADR es la respuesta pragmática y productizable a las implicaciones de Mythos Preview.
No pretende garantías formales — pretende reducción honesta y medible de superficie de
ataque en hardware que un hospital rural puede permitirse.

Los resultados de esta variante son el baseline contra el que ADR-031 medirá el coste
real de las garantías formales.

*"La verdad por delante, siempre."*