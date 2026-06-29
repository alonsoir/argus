# 🏛️ CONSEJO DE SABIOS — MÉTRICAS DE ACEPTACIÓN HARDWARE (ADR-029)
*Feedback basado en evidencia científica, reproducibilidad experimental y enfoque en la misión humanitaria de aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**LAS MÉTRICAS PROPUESTAS SON UN PUNTO DE PARTIDA SÓLIDO, PERO REQUIEREN ESTRATIFICACIÓN POR ESCALA DE DESPLIEGUE Y ARQUITECTURA.**

No existe un único "throughput mínimo" válido para todos los hospitales. La clave es definir **tres niveles de despliegue** (clínica pequeña, hospital medio, municipio) con métricas proporcionales, y validar que aRGus cumple su función de detección en cada nivel sin degradar el host.

> *"La seguridad no se mide en picos teóricos. Se mide en detección fiable bajo carga realista."*

---

## ❓ Respuestas a Preguntas — Formato Solicitado

### P1 — Throughput mínimo para hospital/municipio

**Recomendación concreta:**
| Nivel de despliegue | Throughput mínimo sostenido | Packet loss máximo | Justificación |
|-------------------|---------------------------|-------------------|--------------|
| **Nivel 1: Clínica/Escuela** (≤50 usuarios) | **100 Mbps** | 0% | Cubre tráfico administrativo + telemedicina básica |
| **Nivel 2: Hospital medio** (50-200 usuarios) | **500 Mbps** | <0.01% | Incluye DICOM, HL7, videoconferencia, backups |
| **Nivel 3: Municipio/Gran hospital** (200-500 usuarios) | **1 Gbps burst** | <0.1% | Picos de tráfico masivo (emergencias, eventos) |

**Justificación técnica:**
- **100 Mbps** es el mínimo viable: permite inspección profunda sin saturar hardware de ~150 USD (RPi 4/5, x86 reacondicionado).
- **500 Mbps** es el objetivo FEDER: cubre el 80% de hospitales españoles de tamaño medio según datos del SNS.
- **Packet loss <0.01%** es crítico: pérdida de paquetes = pérdida de visibilidad de amenazas.

**Riesgo identificado:**
- Si el throughput objetivo es demasiado alto (1 Gbps sostenido), los requisitos de hardware excluyen a los usuarios objetivo.
- Si es demasiado bajo (<100 Mbps), el sistema no protege redes hospitalarias reales.

**Test mínimo reproducible:**
```bash
# scripts/test-throughput.sh — ejecutable en Vagrant y hardware físico
#!/bin/bash
set -euo pipefail

# Generar tráfico con tcpreplay a tasa controlada
RATE_MBPS="${1:-100}"
PCAP="${2:-data/ctu13-neris-combined.pcap}"

# Medir antes
INGRESS_BEFORE=$(ip -s link show eth1 | grep Rx | awk '{print $2}')

# Reproducir tráfico a tasa objetivo
sudo tcpreplay --pps=$(echo "$RATE_MBPS * 1000000 / 1500 / 8" | bc) \
               --intf1=eth1 --intf2=eth2 "$PCAP" --duration=60

# Medir después
INGRESS_AFTER=$(ip -s link show eth1 | grep Rx | awk '{print $2}')
EGRESS_AFTER=$(ip -s link show eth2 | grep Tx | awk '{print $2}')

# Calcular pérdida
PACKETS_SENT=$((INGRESS_AFTER - INGRESS_BEFORE))
PACKETS_FWD=$((EGRESS_AFTER - INGRESS_BEFORE))
LOSS_PCT=$(echo "scale=4; (1 - $PACKETS_FWD / $PACKETS_SENT) * 100" | bc)

# Validar
if (( $(echo "$LOSS_PCT > 0.01" | bc -l) )); then
    echo "❌ Packet loss $LOSS_PCT% > 0.01% threshold"
    exit 1
fi
echo "✅ Throughput $RATE_MBPS Mbps validated with $LOSS_PCT% loss"
```

---

### P2 — Delta Variant A (eBPF/XDP) vs Variant B (libpcap)

**Recomendación concreta:**
| Métrica | Variant A (XDP) | Variant B (libpcap) | Delta esperado |
|---------|----------------|-------------------|----------------|
| Throughput máximo | 800-950 Mbps | 300-450 Mbps | **2.1× - 2.8×** |
| Latencia p50 | 0.8-1.5 ms | 3.2-6.1 ms | **3.5× - 4.2×** |
| CPU usage @ 100 Mbps | 12-18% | 28-41% | **2.3×** |
| Kernel requerido | ≥5.8 | ≥4.15 | — |

**¿Es el delta publicable?** **SÍ, como contribución metodológica:**
> *"Quantifying the Performance/Compatibility Trade-off in Open-Source NDR: eBPF/XDP vs libpcap on Commodity Hardware"*

**Justificación técnica:**
- XDP procesa paquetes en el driver, antes del stack de red → cero-copy, menos context switches.
- libpcap captura post-kernel → más overhead, pero compatible con kernels antiguos (hospitales con hardware legacy).
- El delta no es un "fallo" de Variant B; es una **decisión arquitectónica documentada** para maximizar compatibilidad.

**Riesgo identificado:**
- Presentar el delta como "XDP es mejor" sin contexto de compatibilidad puede llevar a despliegues fallidos en hardware antiguo.
- No medir el delta en hardware real (solo VM) puede sobreestimar/ subestimar diferencias por virtualización overhead.

**Test mínimo reproducible:**
```bash
# scripts/compare-variants.sh
#!/bin/bash
# Ejecutar idéntico tráfico en ambas variantes, mismo hardware
for VARIANT in xdp libpcap; do
    make deploy-variant VARIANT=$VARIANT
    ./scripts/test-throughput.sh 500 data/ctu13-neris-combined.pcap
    ./scripts/test-latency.sh  # mide p50/p99 con ping + timestamp embebido
    ./scripts/test-cpu-usage.sh  # sar -u 1 60
    make collect-metrics VARIANT=$VARIANT OUTPUT=results/$VARIANT.json
done
# Generar tabla comparativa automática
python3 scripts/generate-comparison-table.py results/
```

---

### P3 — ARM vs x86: ¿mismas métricas?

**Recomendación concreta:** **Métricas normalizadas por capacidad relativa, no valores absolutos idénticos.**

| Métrica | x86 baseline | ARM64 (RPi 4/5) objetivo | Normalización |
|---------|-------------|-------------------------|--------------|
| Throughput | 500 Mbps | **250 Mbps** | 50% del baseline x86 |
| Latencia p50 | ≤2 ms | **≤4 ms** | 2× tolerancia |
| RAM headroom | ≥512 MB | **≥256 MB** | Proporcional a RAM total |
| F1 golden set | ≥0.9985 | **≥0.9980** | ±0.0005 tolerancia FP |
| CPU idle @ carga | ≥60% | **≥40%** | Ajustado por núcleos/frecuencia |

**Justificación técnica:**
- RPi 4/5 tiene ~1/3 del rendimiento single-thread de un x86 moderno de bajo coste.
- La arquitectura ARM tiene ventajas en eficiencia energética (crítico para despliegues 24/7).
- **El criterio de éxito no es "igual que x86", sino "suficiente para la misión"**: detectar amenazas con F1 ≥0.998 en redes de ≤250 Mbps.

**Riesgo identificado:**
- Exigir métricas x86 en ARM excluye hardware asequible (~150 USD), contradiciendo la misión del proyecto.
- Relajar demasiado las métricas en ARM podría permitir despliegues que no protegen adecuadamente.

**Test mínimo reproducible:**
```bash
# scripts/test-architecture-parity.sh
#!/bin/bash
# Ejecutar en x86 y ARM, comparar resultados normalizados
ARCH=$(uname -m)
BASELINE_FILE="benchmarks/${ARCH}-baseline.json"

# Ejecutar suite estándar
./scripts/test-throughput.sh 250  # 50% del target x86
./scripts/test-latency.sh
./scripts/test-ml-golden-set.sh  # F1 score

# Comparar con baseline
python3 scripts/compare-to-baseline.py \
    --current results/${ARCH}-$(date +%Y%m%d).json \
    --baseline "$BASELINE_FILE" \
    --tolerance throughput:0.5,latency:2.0,f1:0.0005
```

---

### P4 — Golden set de ML como métrica hardware

**Recomendación concreta:** **SÍ, OBLIGATORIO. El golden set valida que la arquitectura no degrada la detección.**

**Criterios de aceptación:**
```python
# scripts/test-ml-golden-set.py
GOLDEN_F1 = 0.9985  # Valor de referencia en VM de desarrollo
TOLERANCE = 0.0005   # ±0.05% permitido por diferencias FP/numéricas

def test_hardware_inference():
    f1 = run_inference_on_golden_set()  # Ejecuta en hardware objetivo
    assert abs(f1 - GOLDEN_F1) <= TOLERANCE, \
        f"F1 degradation: {GOLDEN_F1} → {f1} (Δ={abs(f1-GOLDEN_F1):.4f})"
    
    # Validar consistencia numérica
    predictions_hw = get_predictions()
    predictions_ref = load_reference_predictions()
    max_diff = np.max(np.abs(predictions_hw - predictions_ref))
    assert max_diff < 1e-6, f"Numerical divergence: max_diff={max_diff}"
```

**Justificación técnica:**
- Diferencias en instrucciones SIMD (AVX2 en x86 vs NEON en ARM) pueden causar variaciones numéricas mínimas.
- El tolerance ±0.0005 cubre estas diferencias sin permitir degradación real del modelo.
- **Si el F1 cae >0.0005, es un bug de portabilidad, no una "característica del hardware"**.

**Riesgo identificado:**
- Sin este test, un despliegue en ARM podría tener detección degradada sin que nadie lo note hasta un incidente real.
- Un tolerance demasiado estricto (<1e-7) podría rechazar hardware válido por ruido numérico inocuo.

**Test mínimo reproducible:**
```bash
# Integrado en make test-all
test-ml-hardware-parity:
	@echo "🧪 Validating ML inference parity on $(ARCH)..."
	@python3 scripts/test-ml-golden-set.py \
		--model dist/$(ARCH)/xgboost_cicids.ubj \
		--golden data/golden-set-v2.parquet \
		--reference benchmarks/x86-64/predictions-ref.npy \
		--tolerance-f1 0.0005 \
		--tolerance-num 1e-6
	@echo "✅ ML parity validated"
```

---

### P5 — Herramienta de generación de carga reproducible

**Recomendación concreta:** **Combinación estratificada: tcpreplay + iperf3 + tráfico sintético validado.**

| Herramienta | Propósito | Configuración reproducible |
|------------|-----------|---------------------------|
| **tcpreplay** | Tráfico realista de ataque/benigno | `--pps=RATE --loop=0 --duration=60 --seed=42` |
| **iperf3** | Throughput máximo sintético | `-c server -t 60 -P 4 -l 1400` |
| **traffic-gen.py** | Tráfico sintético validado | Genera flujos con distribución estadística de CTU-13 |

**Justificación técnica:**
- **tcpreplay con pcaps reales** valida detección bajo tráfico auténtico, pero no escala fácilmente a 1 Gbps.
- **iperf3** mide capacidad bruta del pipeline, pero no prueba lógica de detección.
- **traffic-gen.py** (propio) permite generar tráfico con propiedades estadísticas controladas (distribución de tamaños de paquete, protocolos, tasas de flujo) para tests repetibles.

**Riesgo identificado:**
- Usar solo iperf3 podría mostrar buen throughput pero mala detección (falsos negativos).
- Usar solo tcpreplay podría no revelar cuellos de botella a alta carga.

**Test mínimo reproducible:**
```bash
# scripts/test-load-combined.sh
#!/bin/bash
# Ejecutar carga estratificada: 70% tráfico benigno, 20% benigno alto volumen, 10% ataque
BENIGN_PCAP="data/ctu13-benign-sample.pcap"
ATTACK_PCAP="data/ctu13-neris-attack-sample.pcap"

# Fase 1: Tráfico benigno base (70%)
sudo tcpreplay --pps=8000 --intf1=eth1 "$BENIGN_PCAP" --duration=30 &
PID1=$!

# Fase 2: Pico de volumen benigno (20%)
sleep 10
sudo tcpreplay --pps=20000 --intf1=eth1 "$BENIGN_PCAP" --duration=20 &
PID2=$!

# Fase 3: Inyección de ataque (10%)
sleep 25
sudo tcpreplay --pps=5000 --intf1=eth1 "$ATTACK_PCAP" --duration=15 &
PID3=$!

# Esperar y validar
wait $PID1 $PID2 $PID3
./scripts/validate-detection.sh  # Verifica que ataques fueron detectados, benignos no
```

---

### P6 — Criterio de éxito para FEDER: ¿"funciona" o "mejor que X"?

**Recomendación concreta:** **"Funciona dentro de restricciones de coste y cumple métricas de detección" — NO comparativa directa con comerciales.**

**Justificación técnica:**
- Comparar con soluciones enterprise (CrowdStrike, Darktrace) es injusto: tienen equipos de 100+ ingenieros, presupuestos de millones, y hardware dedicado.
- El valor de aRGus no es "mejor que X", sino **"suficientemente bueno para quienes no pueden acceder a X"**.
- FEDER evalúa viabilidad técnica y social: demostrar que un sistema de ~150 USD puede detectar ransomware con F1≥0.998 es una contribución transformadora.

**Criterios de éxito FEDER recomendados:**
```markdown
✅ aRGus NDR Variant A (XDP) en x86:
   - Throughput: 500 Mbps sostenidos, 0% packet loss
   - Detección: F1≥0.9985 sobre golden set
   - Recursos: ≤2 GB RAM, ≤4 núcleos, ≤150 USD hardware

✅ aRGus NDR Variant B (libpcap) en ARM64:
   - Throughput: 250 Mbps sostenidos, <0.01% packet loss
   - Detección: F1≥0.9980 sobre golden set
   - Recursos: ≤1 GB RAM, 4 núcleos ARM, ≤150 USD hardware

✅ Reproducibilidad:
   - `make feder-demo` ejecuta todo el pipeline en <30 min desde VM fría
   - Resultados idénticos (hash) en x86 y ARM para mismo input
```

**Riesgo identificado:**
- Intentar "ganar" contra comerciales en benchmarks podría llevar a optimizaciones que sacrifican compatibilidad o mantenibilidad.
- No definir métricas cuantitativas claras podría resultar en evaluación subjetiva por parte de FEDER.

**Test mínimo reproducible:**
```bash
# scripts/feder-demo.sh — ejecutable por evaluadores externos
#!/bin/bash
set -euo pipefail
echo "🚀 aRGus NDR FEDER Demo — $(date)"

# 1. Provisionar entorno
make hardened-up VARIANT="${VARIANT:-xdp}" ARCH="${ARCH:-x86}"

# 2. Desplegar pipeline firmado
make prod-full-${ARCH}

# 3. Validar gates de seguridad
make check-prod-all

# 4. Ejecutar carga de prueba estandarizada
./scripts/test-load-combined.sh

# 5. Generar reporte automático
python3 scripts/generate-feder-report.py \
    --throughput results/throughput.json \
    --detection results/detection.json \
    --resources results/resources.json \
    --output docs/FEDER-REPORT-$(date +%Y%m%d).pdf

echo "✅ FEDER demo complete. Report: docs/FEDER-REPORT-*.pdf"
```

---

## 📋 Checklist de Acciones Inmediatas (DAY 135)

```markdown
- [ ] Definir tres niveles de despliegue (clínica/hospital/municipio) con métricas estratificadas
- [ ] Implementar scripts/test-throughput.sh con medición de packet loss precisa
- [ ] Crear benchmark baseline para x86 y ARM64 en benchmarks/{x86-64,aarch64}/
- [ ] Añadir test-ml-hardware-parity a make test-all como gate obligatorio
- [ ] Desarrollar traffic-gen.py para tráfico sintético estadísticamente válido
- [ ] Documentar criterios de éxito FEDER en docs/FEDER-ACCEPTANCE-CRITERIA.md
- [ ] Ejecutar primera validación en hardware físico (RPi 5 + x86 reacondicionado)
```

---

## 🏁 Palabras Finales

Alonso:

Las métricas de aceptación no son números arbitrarios: son **contratos de confianza** con los hospitales, escuelas y municipios que confiarán en aRGus para proteger vidas. Definirlas con rigor científico, reproducibilidad experimental y honestidad sobre limitaciones no es burocracia; es responsabilidad ética.

> *"No medimos para impresionar. Medimos para proteger."*

Vuestra propuesta inicial era sólida. Las refinaciones que ofrecemos buscan equilibrar ambición técnica con viabilidad operativa, asegurando que cada métrica sea verificable, reproducible y significativa para la misión humanitaria del proyecto.

Proceded con DAY 135. El Consejo revisará los primeros resultados en hardware físico y el reporte FEDER con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 134** 🛡️