## Consejo de Sabios — Métricas de Aceptación Hardware (ADR-029)

Enfoque: definir **criterios falsables**, medibles y reproducibles en laboratorio y en hardware real, con trazabilidad entre VM → bare metal.

---

# 1) Métricas mínimas de aceptación (propuesta validada)

Se redefine tu tabla con valores concretos y medibles:

| Métrica                   | x86 (Variant A - XDP)               | x86 (Variant B - pcap) | ARM (RPi 4/5)      | Método                  |
| ------------------------- | ----------------------------------- | ---------------------- | ------------------ | ----------------------- |
| Throughput sin pérdida    | ≥ **1 Gbps**                        | ≥ **300 Mbps**         | ≥ **100–200 Mbps** | tcpreplay + NIC stats   |
| Packet loss               | **0% @ target throughput (10 min)** | ≤ 0.1%                 | ≤ 0.5%             | ethtool / drop counters |
| Latencia detección (p50)  | ≤ **10 ms**                         | ≤ **20 ms**            | ≤ **30 ms**        | timestamps end-to-end   |
| Latencia detección (p99)  | ≤ 50 ms                             | ≤ 100 ms               | ≤ 150 ms           | histogramas             |
| CPU idle (tráfico normal) | ≥ **40%**                           | ≥ 30%                  | ≥ 20%              | mpstat                  |
| RAM libre post-arranque   | ≥ **500 MB**                        | ≥ 400 MB               | ≥ 200 MB           | free -m                 |
| Tiempo arranque pipeline  | ≤ **30 s**                          | ≤ 30 s                 | ≤ 45 s             | systemd-analyze         |
| F1 (golden set)           | ≥ **0.9985**                        | ≥ 0.9985               | ≥ 0.9985           | test offline            |
| Estabilidad               | 0 crashes / 1h                      | idem                   | idem               | soak test               |

---

# 2) Q1 — Throughput mínimo

### Recomendación

* **Objetivo FEDER: 1 Gbps (x86, XDP)**
* **Mínimo aceptable: 300 Mbps**

### Justificación

* Redes hospitalarias modernas:

    * backbone ≥ 1 Gbps habitual
* 100 Mbps:

    * obsoleto → no defendible en 2026

### Riesgo

* Si apuntas a 1 Gbps:

    * tuning kernel necesario
    * NIC dependency (driver/XDP support)

### Test reproducible

```bash
tcpreplay --intf1=eth0 --mbps=1000 capture.pcap
watch -n1 "ethtool -S eth0 | grep drop"
```

---

# 3) Q2 — Delta XDP vs libpcap

### Recomendación

* Esperado:

    * **XDP: 3–10x más throughput**
    * **Menor latencia (~50–80%)**

### Justificación

* XDP:

    * ejecuta en kernel early path
* libpcap:

    * user-space copy + syscall overhead

### ¿Publicable?

✔ **Sí, altamente valioso**

Tabla sugerida en paper:

| Mode | Throughput | CPU | Latency |
| ---- | ---------- | --- | ------- |

### Riesgo

* Drivers sin soporte XDP → skew en resultados

### Test

* mismo PCAP
* mismo hardware
* cambiar solo sniffer

---

# 4) Q3 — ARM vs x86

### Recomendación

NO usar mismas métricas.

| Arquitectura | Perfil           |
| ------------ | ---------------- |
| x86          | rendimiento      |
| ARM          | coste/eficiencia |

### Targets ARM realistas

* 100–200 Mbps sostenidos
* latencia mayor aceptable

### Justificación

* Raspberry Pi:

    * CPU limitada
    * NIC USB (en algunos modelos)

### Riesgo

* Expectativas irreales → demo falla

### Test

* igual que x86, pero con límites ajustados

---

# 5) Q4 — Golden set en hardware

### Recomendación

✔ **OBLIGATORIO incluirlo**

### Hipótesis

El modelo debería ser:

* determinista
* independiente de hardware

### Qué puede fallar

* diferencias en:

    * compilación (flags)
    * float precision
    * ONNX runtime

### Test reproducible

```bash
make test-golden-set
```

Comparar:

* F1
* confusion matrix exacta

### Criterio

❌ cualquier desviación → INVESTIGAR

---

# 6) Q5 — Generación de carga

### Recomendación (combinación)

| Herramienta | Uso                   |
| ----------- | --------------------- |
| tcpreplay   | tráfico real (CTU-13) |
| iperf3      | saturación pura       |
| hping3      | edge cases / ataques  |

### Pipeline ideal

```bash
# 1. tráfico real
tcpreplay capture.pcap

# 2. saturación
iperf3 -c target -P 10

# 3. anomalías
hping3 --flood
```

### Justificación

* iperf3 solo → no realista
* tcpreplay → real pero no estresa máximo
* combinación → cobertura completa

---

# 7) Q6 — Criterio de éxito FEDER

### Recomendación

**Nivel mínimo:**
✔ “funciona correctamente bajo condiciones realistas”

**Nivel ideal:**
✔ “mejor ratio coste/rendimiento que alternativas”

---

### Benchmark competitivo (opcional pero potente)

Comparar contra:

* Suricata
* Zeek

Métrica clave:

```text
€ / Mbps protegido
```

---

### Justificación

* FEDER evalúa:

    * impacto real
    * viabilidad económica

---

### Riesgo

* benchmark mal diseñado → resultados cuestionables

---

### Test reproducible

* mismo hardware
* misma carga
* medir:

    * throughput
    * CPU
    * RAM

---

# 8) Métrica adicional crítica (faltante)

### 🔴 Detección → acción (end-to-end)

Nueva métrica:

| Métrica                    | Valor   |
| -------------------------- | ------- |
| Tiempo detección → bloqueo | ≤ 50 ms |

### Test

1. inyectar ataque
2. medir:

    * timestamp detección
    * timestamp iptables rule

---

# 9) Protocolo experimental mínimo (reproducible)

```bash
# 1. baseline limpio
vagrant destroy -f && vagrant up

# 2. deploy hardened
make prod-full-x86

# 3. warmup
sleep 30

# 4. carga
tcpreplay + iperf3

# 5. métricas
mpstat
free -m
ethtool -S
custom latency logger

# 6. validación ML
make test-golden-set
```

---

# 10) Conclusión del Consejo

### Lo importante no es solo que funcione:

sino que puedas demostrar:

* rendimiento suficiente
* estabilidad
* reproducibilidad
* coste razonable

---

## Veredicto final

* Tus métricas iniciales → **bien planteadas pero incompletas**
* Ajuste del Consejo → **listo para validación FEDER**

---

Si ejecutas esto correctamente, tendrás algo muy difícil de refutar:
no solo un sistema funcional, sino **medido, reproducible y defendible**.
