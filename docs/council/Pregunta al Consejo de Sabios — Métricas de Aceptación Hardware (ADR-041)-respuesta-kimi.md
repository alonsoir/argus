## Kimi — Respuesta al Consejo de Sabios — Métricas de Aceptación Hardware (ADR-029)

*Evaluación bajo criterios de reproducibilidad experimental, restricciones económicas institucionales y rigor metrológico.*

---

### Marco metodológico previo

Antes de responder las 6 preguntas, establezco los principios que gobiernan esta evaluación:

1. **La métrica debe ser observable y reproducible.** Si dos laboratorios independientes no pueden obtener el mismo valor con el mismo procedimiento, no es una métrica de aceptación.
2. **El baseline debe reflejar el peor caso operacional, no el caso promedio.** Un hospital no acepta "funciona el 95% del tiempo".
3. **La comparativa con alternativas comerciales es obligatoria para FEDER.** Sin benchmark comparativo, la demo es una demostración técnica, no una propuesta de valor.

---

### P1 — Throughput mínimo para hospital/municipio

**Recomendación concreta:**

| Escenario | Throughput mínimo | Throughput objetivo FEDER |
|-----------|-------------------|---------------------------|
| Municipio pequeño (<50 usuarios) | 100 Mbps | 500 Mbps |
| Hospital general (100-500 usuarios) | 500 Mbps | 1 Gbps |
| Hospital de referencia (>500 usuarios, IoT médico) | 1 Gbps | 2.5 Gbps |

**Justificación técnica:**

Una NIC Gigabit Ethernet (Intel i210, ~25€) es commodity. El throughput de 1 Gbps no es una aspiración técnica, es el **mínimo que un switch no administrado de 30€ soporta**. Si aRGus no satura 1 Gbps, el cuello de botella es el software, no el hardware.

El dato de referencia de Mercadona Tech (4.4M búsquedas/semana, p50=12ms) es un benchmark de **aplicación**, no de red. Las búsquedas son operaciones de alto nivel; el throughput de red subyacente puede ser mucho mayor. No es comparable directamente con NDR.

**Riesgo identificado:**

Si fijamos 100 Mbps como métrica de aceptación, un revisor o un hospital podría argumentar que cualquier solución de 2010 ya lo lograba. 1 Gbps es el umbral de credibilidad para una demo en 2026.

**Test mínimo reproducible (Vagrant):**

```bash
# Requiere: dos interfaces de red en la VM (eth0 management, eth1 mirror/span)
# Requiere: tcpreplay con pcap de CTU-13 o iperf3

# 1. Preparar interfaz de test
sudo ip link set eth1 up
sudo ethtool -s eth1 speed 1000 duplex full autoneg off  # forzar 1Gbps

# 2. Medir throughput máximo sin aRGus (baseline del sistema)
iperf3 -s -B 192.168.56.2 &  # servidor en VM
iperf3 -c 192.168.56.2 -t 60 -P 10  # cliente desde host, 10 flujos paralelos
# Registrar: [Mbps sender], [Mbps receiver], [Retr], [Cwnd]

# 3. Medir throughput con aRGus pipeline 6/6 RUNNING
# (sniffer en eth1, ml-detector, firewall, etc.)
# Repetir iperf3. El delta debe ser <5% del baseline.

# 4. Medir packet loss con tcpreplay
sudo tcpreplay -i eth1 -t -K /path/to/ctu-13-neris.pcap
# -t: topspeed (lo más rápido posible)
# -K: precache para evitar I/O bound
# Observar: aRGus debe reportar 0% packet loss hasta 1 Gbps.
# Si hay loss >0.001%, registrar a qué throughput ocurrió.
```

**Criterio de éxito:** `throughput_argus / throughput_baseline ≥ 0.95` a 1 Gbps durante 60 segundos, con `packet_loss ≤ 0.001%`.

---

### P2 — Delta Variant A (eBPF/XDP) vs Variant B (libpcap)

**Recomendación concreta:**

| Métrica | Valor esperado | Publicable |
|---------|---------------|------------|
| Delta throughput A vs B | A ≥ 2× B a 1 Gbps | **Sí**, con condiciones |
| Delta latencia A vs B | A ≤ 0.5× B (p50) | **Sí** |
| Delta CPU A vs B | A ≤ 0.3× B a misma carga | **Sí** |

**Justificación técnica:**

XDP opera en el **driver NIC** (o generic XDP en el stack de red), antes de que el paquete llegue al kernel networking stack. libpcap opera en **userspace** vía `AF_PACKET` o `mmap` ring buffer, requiriendo al menos una copia de kernel a userspace y un context switch.

La literatura académica (Hoiland-Jørgensen et al., "The eXpress Data Path", ACM CoNEXT 2018) reporta mejoras de 10-20× en throughput y reducciones de latencia de 5-10× para forwarding simple. Para NDR (que incluye ML inference), el delta se reduce pero debe mantenerse significativo (>2×).

**Condición de publicabilidad:**

El delta **solo es publicable** si:
1. Se mide con la **misma carga de trabajo** (mismo pcap, misma duración)
2. Se mide en el **mismo hardware** (misma CPU, misma NIC)
3. Se reporta el **kernel exacto** y la **versión de libpcap**
4. Se incluye la **varianza** (desviación estándar de al menos 10 repeticiones)

Sin estas condiciones, el delta es un **dato anecdótico**, no una contribución científica.

**Riesgo identificado:**

Si el delta es menor de 2×, los revisores pueden argumentar que la complejidad de XDP no justifica el beneficio. Si es mayor de 10×, debéis verificar que no hay un bug en la configuración de libpcap (por ejemplo, buffer size por defecto demasiado pequeño).

**Test mínimo reproducible:**

```bash
#!/bin/bash
# test_variant_delta.sh — ejecutar en hardware físico idéntico

VARIANT=$1  # "xdp" o "libpcap"
PCAP="ctu-13-neris-1Mpackets.pcap"
DURATION=300  # 5 minutos por repetición
REPS=10

for i in $(seq 1 $REPS); do
    echo "=== Repetición $i / $REPS ==="
    
    # Limpiar estado
    sudo ip link set eth1 down && sudo ip link set eth1 up
    
    # Arrancar aRGus con la variante indicada
    if [ "$VARIANT" = "xdp" ]; then
        sudo ./argus-sniffer --mode=xdp --iface=eth1 &
    else
        sudo ./argus-sniffer --mode=libpcap --iface=eth1 &
    fi
    SNIFER_PID=$!
    
    # Medir
    tcpreplay -i eth1 -t -K --duration=$DURATION $PCAP 2>&1 | tee rep${i}_${VARIANT}.log
    
    # Recolectar métricas del sniffer
    cat /proc/$SNIFER_PID/status | grep -E "VmRSS|voluntary_ctxt_switches|nonvoluntary_ctxt_switches"
    
    kill $SNIFER_PID
    sleep 5  # enfriamiento entre repeticiones
done

# Post-procesado con Python/pandas: media, desviación estándar, intervalo de confianza 95%
```

---

### P3 — ARM/Raspberry Pi: ¿mismas métricas o perfil diferente?

**Recomendación concreta:**

**Métricas diferentes con justificación explícita.** ARM no es una versión "degradada" de x86; es una plataforma con un **contrato de rendimiento diferente** que debe documentarse.

| Métrica | x86 baseline | ARM baseline | Justificación del delta |
|---------|-------------|--------------|------------------------|
| Throughput | 1 Gbps | 100 Mbps | RPi4 USB3-to-Gigabit overhead + CPU Cortex-A72 limitado |
| Latencia p50 | ≤ 5 ms | ≤ 50 ms | Menor caché L3, menor frecuencia, inferencia ML más lenta |
| RAM headroom | ≥ 512 MB | ≥ 128 MB | RPi4 tiene 4-8 GB; aRGus debe dejar margen para SO |
| F1 golden set | ≥ 0.9985 | ≥ 0.9985 | **Invariante.** El modelo no cambia; el hardware no debe degradar la precisión. |
| CPU idle | ≥ 30% | ≥ 10% | Aceptable si el throughput objetivo se alcanza |
| Tiempo arranque | ≤ 30 s | ≤ 120 s | SD card vs NVMe |
| Coste hardware | ~200€ | ~75€ | **Métrica de aceptación económica** |

**Justificación técnica:**

El Raspberry Pi 4 tiene:
- CPU: 4× Cortex-A72 @ 1.5 GHz (comparable a un Intel Atom, no a un Xeon)
- RAM: LPDDR4 compartida con GPU
- Red: Gigabit Ethernet sobre bus USB3 (throughput real ~300-400 Mbps, no 1 Gbps)
- Almacenamiento: microSD (IOPS limitadas)

Un throughput de 100 Mbps en RPi4 es **físicamente razonable** y **económicamente valioso**: un sensor NDR a 75€ que procesa 100 Mbps es competitivo contra soluciones enterprise de 5000€+.

**Riesgo identificado:**

Si se exige 1 Gbps en ARM, el proyecto falla antes de empezar. Si se exige 100 Mbps y no se documenta el porqué, los revisores pueden interpretar que el sistema no escala.

**Test mínimo reproducible (RPi4):**

```bash
# En RPi4 con Raspberry Pi OS Lite (64-bit)
# Nota: desactivar WiFi y Bluetooth para reducir interferencia

# 1. Forzar CPU a performance governor
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 2. Medir throughput máximo de la interfaz (sin aRGus)
iperf3 -c <server> -t 60
# Esperado: 300-400 Mbps (límite del bus USB3)

# 3. Medir throughput con aRGus Variant B (libpcap, XDP no disponible en RPi4)
# Criterio: ≥ 100 Mbps con packet loss < 0.01%
```

---

### P4 — Golden set como métrica hardware

**Recomendación concreta:** **Sí, obligatorio.** El golden set (ADR-040) debe ejecutarse en cada plataforma hardware como parte del test de aceptación.

**Justificación técnica:**

La inferencia ML puede degradarse por:
1. **Diferencias de punto flotante:** x86 usa SSE/AVX; ARM usa NEON. Los resultados de `float32` pueden diferir en el bit menos significativo, afectando thresholds.
2. **Diferencias de bibliotecas:** ONNX Runtime en x86 vs ARM puede usar optimizaciones diferentes (OpenVINO vs ARM Compute Library).
3. **Diferencias de endianness:** Aunque x86 y ARM64 son little-endian, el modelo serializado (ONNX, GGUF) debe verificarse.

**Riesgo identificado:**

Si el F1 en ARM es 0.9984 (vs 0.9985 en x86), ¿es aceptable? La diferencia de 0.0001 puede ser ruido estadístico o puede indicar un bug en la pipeline de inferencia. Necesitáis un **intervalo de confianza** para el F1.

**Test mínimo reproducible:**

```bash
# test_golden_set_hardware.sh

HARDWARE_ID=$(cat /sys/class/dmi/id/product_uuid 2>/dev/null || cat /proc/cpuinfo | grep Serial | head -1)
MODEL="xgboost_cicids2017_v2.onnx"
GOLDEN="ctu-13-neris-golden-labeled.csv"

./argus-ml-detector --model=$MODEL --input=$GOLDEN --output=predictions_${HARDWARE_ID}.csv

python3 << 'PYEOF'
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

df = pd.read_csv(f"predictions_{HARDWARE_ID}.csv")
f1 = f1_score(df.label, df.prediction)
print(f"F1={f1:.6f} on {HARDWARE_ID}")

# Validar contra baseline x86
baseline_f1 = 0.998500
assert abs(f1 - baseline_f1) < 0.000100, f"F1 degradation: {f1} vs {baseline_f1}"
PYEOF
```

**Criterio de éxito:** `|F1_hardware - F1_x86| < 0.0001` (10× el epsilon de precisión float32).

---

### P5 — Herramienta de generación de carga reproducible

**Recomendación concreta:** **Combinación: tcpreplay para tráfico realista + iperf3 para saturación controlada.**

| Herramienta | Uso | Cuándo |
|-------------|-----|--------|
| **tcpreplay** | Reproducir tráfico real (CTU-13, CIC-IDS-2017) | Validación de precisión ML, métricas de detección |
| **iperf3** | Saturación controlada, throughput máximo | Validación de límites de rendimiento, packet loss |
| **pktgen (kernel module)** | Microbenchmarks de latencia a nivel de driver | Solo si se necesita aislar el sniffer del resto del pipeline |

**Justificación técnica:**

tcpreplay reproduce **distribuciones reales de paquetes** (tamaños, protocolos, inter-arrival times), lo cual es esencial para validar que el modelo ML no se degrada con tráfico "real" vs tráfico sintético. iperf3 genera **flujos TCP ideales** que saturan el enlace, útil para encontrar el límite absoluto.

**Riesgo identificado:**

tcpreplay con `-t` (topspeed) puede enviar más rápido de lo que la NIC puede manejar, causando packet loss en el **generador**, no en aRGus. Esto produce falsos positivos. La solución es usar `--mbps=1000` para limitar a 1 Gbps explícitamente.

**Test mínimo reproducible:**

```bash
# Generar pcap de referencia reproducible
# (si no tenéis CTU-13 descargado, crear uno sintético con scapy)

python3 << 'PYEOF'
from scapy.all import *

# 1M paquetes TCP, distribución de tamaños realista
pkts = []
for i in range(1_000_000):
    size = max(64, int(random.gauss(500, 200)))  # media 500B, σ=200
    pkt = Ether()/IP(src="10.0.0.1", dst="10.0.0.2")/TCP()/("X" * (size - 54))
    pkts.append(pkt)

wrpcap("synthetic-1M.pcap", pkts)
PYEOF

# Verificar reproducibilidad
sha256sum synthetic-1M.pcap  # registrar en el paper

# Ejecutar carga
sudo tcpreplay -i eth1 --mbps=1000 --loop=10 synthetic-1M.pcap
# --loop=10: 10M paquetes totales, ~5 minutos a 1 Gbps
```

---

### P6 — Criterio de éxito para FEDER: ¿funciona o es mejor que X?

**Recomendación concreta:** **Ambos. "Funciona" es necesario pero no suficiente. El benchmark comparativo es obligatorio para FEDER.**

**Justificación técnica:**

FEDER es un programa de financiación. Los evaluadores no son ingenieros de red; son gestores que entienden **coste-beneficio**. Un sistema que "funciona" pero no demuestra ventaja económica no justifica la inversión.

**Benchmark comparativo mínimo:**

| Solución | Coste HW anual | Coste licencia anual | Throughput | Latencia | F1 | Observaciones |
|----------|---------------|----------------------|------------|----------|-----|---------------|
| aRGus NDR (x86) | 200€ (amortizado 5 años) | 0€ (open source) | 1 Gbps | 5 ms | 0.9985 | **Sujeto de evaluación** |
| aRGus NDR (ARM) | 75€ (amortizado 5 años) | 0€ | 100 Mbps | 50 ms | 0.9985 | **Sujeto de evaluación** |
| Suricata + Elastic | 2000€ (servidor) | 0€ (open source) | 10 Gbps | 10 ms | ~0.95 | Requiere tuning experto |
| Darktrace | 15000€ (appliance) | 25000€/año | 1 Gbps | 1 ms | ~0.99 | Solución enterprise |
| Cisco Secure Network Analytics | 8000€ (appliance) | 12000€/año | 10 Gbps | 5 ms | ~0.98 | Solución enterprise |

**Riesgo identificado:**

Si no tenéis acceso a Darktrace o Cisco para medir, no inventéis números. Usad **datos publicados** (whitepapers, datasheets) y documentad la fuente. La honestidad metodológica es más valiosa que una tabla completa.

**Test mínimo reproducible (comparativa):**

```bash
# Instalar Suricata en la misma VM/hardware para comparación justa
sudo apt-get install suricata
sudo suricata -c /etc/suricata/suricata.yaml -i eth1 &
SURICATA_PID=$!

# Ejecutar misma carga de CTU-13
tcpreplay -i eth1 --mbps=1000 ctu-13-neris.pcap

# Medir: CPU%, RAM, throughput reportado por Suricata, alertas generadas
# Comparar con aRGus en las mismas condiciones
```

---

### Tabla consolidada de métricas de aceptación ADR-029

| Métrica | x86 | ARM (RPi4/5) | Método de medición | Criterio éxito |
|---------|-----|--------------|-------------------|----------------|
| Throughput | 1 Gbps | 100 Mbps | iperf3 + tcpreplay | ≥ 95% del baseline NIC, packet loss < 0.001% |
| Latencia p50 | ≤ 5 ms | ≤ 50 ms | `bpftrace` o `tcpdump -tttt` | Medir tiempo entre paquete en eth1 y alerta en log |
| RAM headroom | ≥ 512 MB | ≥ 128 MB | `free -m` post-arranque | Disponible para SO y emergencias |
| F1 golden set | ≥ 0.9985 | ≥ 0.9985 | Inferencia sobre CTU-13 golden | `|F1_hw - F1_x86| < 0.0001` |
| CPU idle (tráfico normal) | ≥ 30% | ≥ 10% | `mpstat 1 60` | Headroom para picos |
| Tiempo arranque pipeline | ≤ 30 s | ≤ 120 s | `systemd-analyze` | Desde `vagrant up` hasta `6/6 RUNNING` |
| 0 packet loss sostenido | Sí | Sí | tcpreplay 5 min @ throughput objetivo | Loss < 0.001% |
| Coste hardware | ~200€ | ~75€ | Presupuesto | Incluido en métrica de aceptación económica |

---

### Resumen de posiciones — Kimi

| Pregunta | Recomendación | Justificación clave |
|----------|---------------|---------------------|
| **P1** | 1 Gbps x86, 500 Mbps objetivo FEDER | Umbral de credibilidad 2026; 1 Gbps es commodity |
| **P2** | Delta ≥2× publicable con varianza reportada | XDP vs libpcap es contribución técnica válida si se mide rigurosamente |
| **P3** | Métricas diferentes con justificación explícita | ARM no es x86 lento; es una plataforma con contrato de rendimiento diferente |
| **P4** | Golden set obligatorio en cada plataforma | El hardware no debe degradar la precisión del modelo; float32 puede variar |
| **P5** | tcpreplay + iperf3 combinados | Tráfico realista vs saturación controlada; complementarios, no excluyentes |
| **P6** | Benchmark comparativo obligatorio para FEDER | La financiación requiere argumento de valor, no solo demostración técnica |

**Moción:** Propongo que el DAY 135 incluya la ejecución del `test_variant_delta.sh` en la VM de desarrollo (aunque sea con datos preliminares) para validar que el harness de medición funciona antes de comprar hardware físico. Un método de medición que no se ha probado no es reproducible.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*