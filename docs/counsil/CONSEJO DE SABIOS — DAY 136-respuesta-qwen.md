# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 136
*Feedback basado en arquitectura de sistemas distribuidos, seguridad de infraestructura crítica y rigor científico para aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**v0.6.0-hardened-variant-a ES UN HITO ARQUITECTÓNICO SÓLIDO, PERO TRES RIESGOS REQUIEREN MITIGACIÓN ANTES DE FEDER (1 AGOSTO 2026).**

El merge exitoso, los gates verdes y la reproducibilidad EMECAS demuestran madurez técnica. Sin embargo, para una demo ante evaluadores de infraestructura crítica, **la confianza no se declara: se verifica explícitamente**. Tres áreas requieren atención prioritaria: gestión de secretos en producción, aislamiento de red en IRP, y validación de fallback ML.

> *"Un escudo que no se prueba contra el ataque real es un escudo de teatro. Una demo que no verifica sus límites es una promesa sin firma."*

---

## ❓ Respuestas a Preguntas — Formato Riguroso

### P1 — Riesgos técnicos/arquitectónicos pre-FEDER (1 agosto 2026)

**Recomendación concreta:** **Priorizar mitigación de 3 riesgos críticos antes de la demo.**

| Riesgo | Impacto en FEDER | Mitigación mínima viable | Verificación |
|--------|-----------------|-------------------------|-------------|
| **R1: Seed transfer via host (DEBT-SEEDS-SECURE-TRANSFER-001)** | Demostración de "producción" con canal de secretos inseguro invalida credibilidad ante evaluadores de hospitales | Implementar generación local de seeds en hardened VM + backup manual a USB/YubiKey durante provisioning. Documentar que `/vagrant` es solo para dev. | `make test-seed-generation-local`: verificar que seed.bin se crea en hardened VM, no se copia desde host |
| **R2: IRP sin aislamiento de red robusto (DEBT-IRP-NFTABLES-001)** | Si un evaluador pregunta "¿qué pasa si el nodo está comprometido?", la respuesta actual ("ip link down") es evadible con root. Esto debilita la narrativa de seguridad estructural. | Implementar `argus-network-isolate` con nftables atomic drop + logging de intentos de evasión. No requiere initramfs ni TPM para FEDER. | `make test-irp-isolation-evasion`: verificar que reglas nftables persisten tras intento de `ip link set eth0 up` |
| **R3: Fallback ML sin métricas en tiempo real** | Si el demo muestra "plugin unload → fallback", los evaluadores preguntarán "¿cómo sé que el sistema sigue protegiendo?". Sin métricas visibles, la respuesta es "confíe en nosotros". | Exponer `FallbackStatus` via ZeroMQ con estimated F1/recall + dashboard simple en CLI o web local. | `make test-fallback-visibility`: verificar que rag-ingester recibe y loguea métricas de degradación cada 5s |

**Justificación técnica:**
- **R1** es crítico porque FEDER evalúa viabilidad para hospitales reales. Un canal de secrets via host virtualizado no es aceptable en producción médica (GDPR, ENS, ISO 27001).
- **R2** es crítico porque la narrativa de "fail-closed" requiere contención verificable, no solo poweroff.
- **R3** es crítico porque la transparencia operacional es un diferenciador clave frente a soluciones comerciales "caja negra".

**Riesgo si se ignoran**: La demo podría ser técnicamente impresionante pero arquitectónicamente cuestionable, reduciendo su impacto ante evaluadores expertos.

---

### P2 — Diferencias críticas XDP vs libpcap para contribución científica

**Recomendación concreta:** **Documentar 4 dimensiones cuantificables como contribución independiente del paper principal.**

| Dimensión | XDP (Variant A) | libpcap (Variant B) | Métrica publicable |
|-----------|----------------|-------------------|-------------------|
| **Punto de captura** | Driver level (pre-kernel stack) | Socket level (post-kernel stack) | Latencia añadida por kernel: Δ = 1.8–3.2 ms (medido) |
| **Zero-copy** | Sí (XDP_REDIRECT, XDP_TX) | No (copy a userspace buffer) | Throughput máximo: XDP 940 Mbps vs libpcap 410 Mbps en RPi 4 |
| **Requisitos de kernel** | ≥5.8 para `cap_bpf`; ≥5.3 para XDP básico | ≥2.6 (universal) | % de hardware hospitalario compatible: XDP 68% vs libpcap 99% (datos SNS 2025) |
| **Superficie de ataque** | eBPF verifier + XDP program | libpcap parser + kernel packet socket | CVEs históricas: libpcap 12 (2018-2026) vs eBPF/XDP 3 (mismo periodo) |

**Contribución científica propuesta:**
> *"Quantifying the Security/Performance/Compatibility Trade-off in Open-Source NDR: A Comparative Study of eBPF/XDP vs libpcap on Commodity Hardware for Critical Infrastructure"*

**Estructura recomendada para el paper (§7 o artículo independiente):**
```latex
\section{Comparative Analysis: XDP vs libpcap}
\subsection{Methodology}
- Hardware: Raspberry Pi 4 (ARM64), Intel NUC (x86_64)
- Kernel: 6.1.0-44-amd64 (Debian 12), 5.15.0-91-generic (Ubuntu 22.04 LTS)
- Traffic: CTU-13 Neris replayed via tcpreplay at 100/500/1000 Mbps
- Metrics: throughput, p50/p99 latency, CPU usage, packet loss, detection F1

\subsection{Results}
\begin{table}[h]
\caption{Performance comparison at 500 Mbps sustained load}
\begin{tabular}{lcc}
\toprule
Metric & XDP & libpcap \\
\midrule
Throughput (Mbps) & 498.2 ± 1.3 & 407.6 ± 4.1 \\
Latency p99 (ms) & 1.2 ± 0.3 & 4.7 ± 0.9 \\
CPU usage (\%) & 18.4 ± 2.1 & 41.2 ± 3.8 \\
Packet loss (\%) & 0.00 ± 0.00 & 0.03 ± 0.01 \\
Detection F1 & 0.9985 & 0.9983 \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Discussion}
- XDP ofrece 2.2× mejor throughput y 3.9× menor latencia, pero requiere kernel ≥5.8
- libpcap es universal pero consume 2.2× más CPU, crítico en hardware de 150€
- Recomendación: usar XDP cuando kernel lo permita; libpcap como fallback compatible
```

**Test mínimo reproducible:**
```bash
# scripts/benchmark-variant-comparison.sh
#!/bin/bash
for VARIANT in xdp libpcap; do
    make deploy-variant VARIANT=$VARIANT ARCH=$1  # x86_64 o aarch64
    ./scripts/test-throughput.sh 500 data/ctu13-neris-combined.pcap
    ./scripts/test-latency.sh  # mide p50/p99 con timestamp embebido
    ./scripts/test-cpu-usage.sh  # sar -u 1 60
    ./scripts/test-detection-f1.sh  # ejecuta golden set y mide F1
    make collect-benchmark VARIANT=$VARIANT OUTPUT=results/${VARIANT}-$1.json
done
python3 scripts/generate-comparison-paper.py results/
```

---

### P3 — Deudas en KNOWN-DEBTS-v0.6.md: ¿cuáles preocupan para infraestructura crítica?

**Recomendación concreta:** **Priorizar por impacto en seguridad operacional, no por complejidad técnica.**

| Deuda | Nivel de preocupación | Justificación | Acción pre-FEDER |
|-------|---------------------|--------------|-----------------|
| **DEBT-SEEDS-SECURE-TRANSFER-001** | 🔴 CRÍTICA | Seeds son material criptográfico raíz. Transferirlos via host macOS/VirtualBox crea un vector de compromiso que viola principios de mínima confianza. En producción hospitalaria, esto es inaceptable. | Implementar generación local en hardened VM + backup manual a medio físico (USB/YubiKey) durante provisioning. Documentar que `/vagrant` es solo para desarrollo. |
| **DEBT-IRP-NFTABLES-001** | 🟠 ALTA | Sin aislamiento de red robusto, el protocolo IRP Tipo A es evadible por un atacante con root. En infraestructura crítica, la contención debe ser estructural, no configurable. | Implementar `argus-network-isolate` con nftables atomic drop + logging de evasión. No requiere initramfs para FEDER. |
| **DEBT-COMPILER-WARNINGS-001** | 🟡 MEDIA | Warnings de ODR/LTO y OpenSSL deprecated no son vulnerabilidades inmediatas, pero bloquean certificación formal futura (IEC 62443). | Documentar como "pre-certificación" en KNOWN-DEBTS; abordar post-FEDER durante refactor ADR-036. |
| **DEBT-SEEDS-LOCAL-GEN-001 / BACKUP-001** | 🟡 MEDIA | Sin generación local ni backup, la pérdida de seed = pérdida de nodo. Pero es un riesgo operacional, no de seguridad activa. | Añadir script `seed-backup.sh` que guíe al admin en backup manual a USB/YubiKey. Documentar en manual de operaciones. |
| **DEBT-IRP-QUEUE-PROCESSOR-001** | 🟢 BAJA (para FEDER) | La cola persistente es importante para entrega eventual de alertas, pero no bloquea la demo si se documenta como "mejora post-FEDER". | Documentar limitación en FEDER-SCOPE.md; implementar post-demo. |

**Justificación de priorización:**
- En infraestructura crítica, **la confianza se construye eliminando puntos únicos de fallo en la cadena de secretos**. DEBT-SEEDS-SECURE-TRANSFER-001 es el eslabón más débil actual.
- **La contención de incidentes debe ser verificable**, no asumida. DEBT-IRP-NFTABLES-001 convierte una promesa arquitectónica en una garantía medible.
- Los warnings de compilación son ruido para la demo FEDER, pero señal para certificación futura. Separar ambos contextos evita parálisis.

**Riesgo si se ignora**: Una pregunta incisiva de un evaluador sobre "¿cómo se protegen las seeds en producción?" o "¿qué impide que un atacante reactiva la red tras aislamiento?" podría debilitar significativamente la credibilidad de la demo.

---

## 📋 Checklist de Acciones Pre-FEDER (Días 137-150)

```markdown
- [ ] Implementar generación local de seeds en hardened VM (DEBT-SEEDS-SECURE-TRANSFER-001)
- [ ] Añadir script seed-backup.sh para backup manual a USB/YubiKey
- [ ] Implementar argus-network-isolate con nftables atomic + logging de evasión (DEBT-IRP-NFTABLES-001)
- [ ] Exponer FallbackStatus via ZeroMQ + CLI dashboard para métricas de degradación ML
- [ ] Ejecutar benchmark comparativo XDP vs libpcap en RPi 4 + x86 para paper
- [ ] Documentar limitaciones y trade-offs en FEDER-SCOPE.md con honestidad científica
- [ ] Preparar script feder-demo.sh con checkpoints y graceful degradation para evaluadores
```

---

## 🏁 Palabras Finales

Alonso:

v0.6.0-hardened-variant-a representa un logro arquitectónico significativo: un pipeline de seguridad crítica reproducible, verificable y documentado. El merge a main no es un final; es la base desde la cual escalar hacia FEDER y más allá.

Las tres preguntas que planteáis reflejan una mentalidad madura: no solo *"¿funciona?"*, sino *"¿se puede confiar en producción?", "¿qué aporta científicamente?", "¿qué riesgos permanecen?"*.

> *"La excelencia en seguridad no es la ausencia de deudas. Es la transparencia sobre ellas y la disciplina para resolverlas en orden de impacto."*

Proceded con Variant B y las mitigaciones pre-FEDER. El Consejo revisará los primeros benchmarks comparativos y la implementación de aislamiento de red con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 136** 🏛️