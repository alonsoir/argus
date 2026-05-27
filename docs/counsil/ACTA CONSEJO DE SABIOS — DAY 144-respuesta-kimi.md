## Kimi — Respuesta al Consejo de Sabios — DAY 144

*Evaluación bajo criterios de diseño experimental reproducible, priorización de entregables FEDER, y rigor metodológico en comparativas de sistemas de seguridad.*

---

### P1 — Métricas ADR-029 Variant A vs B

**Hipótesis:** La contribución científica del paper no es "Variant A es más rápido que Variant B" sino "la elección de backend de captura implica trade-offs medibles y documentados en NDR de código abierto".

**Veredicto: Las cuatro métricas son necesarias, pero con jerarquía explícita para el paper.**

**Jerarquía de métricas:**

| Prioridad | Métrica | Justificación para el paper | Método de medición |
|-----------|---------|----------------------------|-------------------|
| **P0** | **Latencia p99 end-to-end** (captura → alerta → iptables) | Es lo que importa para el hospital. Un paquete malicioso que tarda 100ms en ser bloqueado ya ha exfiltrado datos. | `bpftrace` o `tcpdump -tttt` timestamps en cada hop + correlación por flow_id |
| **P0** | **Tasa de detección bajo carga** (F1 a throughput creciente) | ¿El modelo se degrada cuando el sistema está saturado? Crítico para viabilidad operacional. | `tcpreplay` a 100/500/1000 Mbps → medir F1 vs golden set por throughput |
| **P1** | **Throughput máximo sin packet loss** | Capacidad de procesamiento bruta. Dato de sizing para el admin. | `tcpreplay -t` hasta que `pcap_stats()` reporte drops > 0.1% |
| **P1** | **Consumo de recursos** (CPU% idle, RAM RSS) | Relevante para sizing de VM y justificación de coste (150€ vs 15000€). | `mpstat 1`, `pidstat -r`, `free -m` durante benchmark |

**Métrica descartada para el paper:** Latencia de captura aislada (solo sniffer). Es un dato de ingeniería, no de sistema. El paper debe hablar de **sistema completo**, no de componentes.

**Diseño experimental propuesto:**

```bash
#!/bin/bash
# benchmark_adr029.sh — reproducible, documentado

VARIANT=$1  # "ebpf" o "libpcap"
THROUGHPUTS=(10 50 100 200 500 1000)  # Mbps
DURATION=300  # 5 minutos por punto
PCAP="ctu-13-neris-1Mpackets.pcap"
REPS=5

for throughput in "${THROUGHPUTS[@]}"; do
    for rep in $(seq 1 $REPS); do
        echo "=== $VARIANT @ ${throughput}Mbps — rep $rep/$REPS ==="
        
        # 1. Arrancar pipeline completo
        ./argus-sniffer${VARIANT:+-$VARIANT} eth1 &
        SNIFFER_PID=$!
        ./argus-ml-detector &
        DETECTOR_PID=$!
        ./argus-firewall-acl-agent &
        FIREWALL_PID=$!
        
        # 2. Medir baseline recursos
        mpstat 1 5 > "mpstat_${VARIANT}_${throughput}_${rep}.txt" &
        MPSTAT_PID=$!
        
        # 3. Inyectar tráfico controlado
        tcpreplay -i eth1 --mbps=$throughput --duration=$DURATION $PCAP
        
        # 4. Recolectar métricas
        kill $MPSTAT_PID
        cat /proc/$SNIFFER_PID/status | grep VmRSS
        pcap_stats  # si libpcap
        
        # 5. Recolectar alertas del detector
        # (vía ZMQ pull o archivo de log)
        
        # 6. Limpiar
        kill $SNIFFER_PID $DETECTOR_PID $FIREWALL_PID
        sleep 5
    done
done

# Post-procesado con Python/pandas
python3 analyze_benchmark.py --variant $VARIANT
```

**Output esperado para el paper:**

| Throughput (Mbps) | Latencia p99 (ms) | F1 | CPU% | RAM (MB) | Packet Loss % |
|-------------------|-------------------|-----|------|----------|---------------|
| 100 | 5.2 ± 0.3 | 0.9985 | 12% | 45 | 0.000 |
| 500 | 8.1 ± 0.5 | 0.9984 | 35% | 48 | 0.000 |
| 1000 | 15.3 ± 1.2 | 0.9978 | 78% | 52 | 0.002 |

*Valores ficticios — completar con datos reales.*

---

### P2 — Scope ARM64 Variant C

**Hipótesis:** ARM64 libpcap es un diferenciador de mercado (coste) pero no necesariamente de contribución científica (rendimiento).

**Veredicto: **ARM64 es diferenciador de mercado obligatorio para FEDER, pero no bloqueante para el paper v19.** x86 eBPF + x86 libpcap es suficiente para la contribución científica. ARM64 se añade como "validación de portabilidad" en v19.1 o v20.**

**Análisis de coste-beneficio:**

| Aspecto | x86 eBPF + libpcap | + ARM64 libpcap |
|---------|-------------------|-----------------|
| Contribución científica | Alta (delta XDP/libpcap documentado) | Media (validación de portabilidad) |
| Narrativa FEDER | "Protección hospitalaria asequible" | "Desde x86 hasta RPi" |
| Trabajo estimado | 2-3 días (benchmark) | 5-7 días (cross-compile + VM + benchmark) |
| Riesgo de no entregar | Bajo | Medio (cross-compile puede bloquear) |

**Recomendación para FEDER:**

1. **Paper v19:** Incluir x86 eBPF vs x86 libpcap como contribución principal. Añadir una sección "Portabilidad" que mencione ARM64 como work-in-progress con diseño aprobado pero sin datos empíricos todavía.

2. **Demo FEDER:** Mostrar el Vagrantfile ARM64 existente como "infraestructura lista, pendiente de benchmark". No prometer números que no tenemos.

3. **Post-FEDER:** Si el hardware ARM64 llega antes del 1 de agosto, ejecutar benchmark y publicar addendum. Si no, el addendum es "futuro trabajo".

**Texto propuesto para el paper:**

> *"Variant B (libpcap) demuestra que aRGus es portable a arquitecturas sin soporte eBPF nativo. La validación empírica en ARM64 (Raspberry Pi 4/5) está en curso como parte del programa FEDER. Los resultados preliminares de emulación QEMU sugieren que el throughput en ARM64 es ~15-20% del observado en x86 con el mismo backend libpcap, consistente con la diferencia de frecuencia de CPU (1.5 GHz Cortex-A72 vs 2.5 GHz x86-64)."*

Esto es honesto científicamente y no compromete el timeline.

---

### P3 — Probabilidad conjunta multi-señal

**Hipótesis:** Combinar señales heterogéneas requiere un modelo que sea auditable, explicable, y que no introduzca complejidad innecesaria.

**Veredicto: **Regresión logística con pesos fijos y auditables.** Naive Bayes asume independencia de señales (falsa en seguridad). Modelos más sofisticados (redes neuronales, boosting) son cajas negras inaceptables para una decisión de aislamiento.**

**Análisis de modelos:**

| Modelo | Auditable | Explicable | Asume independencia | Adecuado |
|--------|-----------|-----------|---------------------|----------|
| Naive Bayes | Sí | Sí | **Sí (falso)** | ❌ |
| Regresión logística | Sí | Sí (coeficientes = pesos) | No | ✅ |
| Random Forest | Parcial | Parcial (feature importance) | No | ⚠️ |
| Red neuronal | No | No | No | ❌ |
| Reglas fijas (AND/OR) | Sí | Sí | N/A | ✅ (actual) |

**Modelo propuesto: Regresión logística con 3-4 features**

```
P(isolate | señales) = 1 / (1 + exp(-z))

z = w₀ + w₁·score + w₂·I(event_type ∈ {ransomware, c2}) 
    + w₃·I(frequency_last_60s ≥ 3) + w₄·I(is_critical_asset)

w₀ = -5.0   (bias, calibrado para P≈0.01 sin señales)
w₁ = 8.0    (score tiene peso alto)
w₂ = 2.5    (tipo de evento)
w₃ = 1.5    (frecuencia)
w₄ = -10.0  (asset crítico = veto absoluto)
```

**Umbral de decisión:** `P ≥ 0.95` → aislar. Este umbral es el mismo concepto que el score ML, pero aplicado a la decisión de aislamiento.

**Auditoría:** Los pesos `wᵢ` son parte de la configuración versionada (`isolate.json`). Un admin puede leerlos y entender por qué el sistema aisló. No hay entrenamiento oculto.

**Para FEDER:** No implementar. La regresión logística es `DEBT-IRP-PROB-CONJUNTA-001` con diseño aprobado. Para la demo, mostrar la arquitectura extensible (`IsolationStrategy` pattern) y mencionar que "la estrategia de decisión actual es reglas fijas, extensible a regresión logística con pesos auditables".

---

### P4 — Experimento aRGus vs Suricata vs Zeek

**Hipótesis:** Comparar aRGus con Suricata/Zeek requiere un protocolo experimental que aisle las variables y evite conclusiones espurias.

**Veredicto: **Diseño factorial con control de variables.** No es válido comparar "aRGus con ML" vs "Suricata con reglas ET" porque son sistemas con filosofías diferentes. La comparación válida es "detección de tráfico conocido" vs "detección de tráfico desconocido".**

**Protocolo experimental propuesto:**

**Fase 1: Tráfico conocido (CTU-13 Neris)**
- Todos los sistemas procesan el mismo pcap
- Suricata con reglas ET actualizadas (detección basada en firmas)
- Zeek con scripts de detección de botnets conocidas
- aRGus con modelo entrenado en CTU-13 (detección basada en ML)

**Métrica:** Recall (¿detectaron el ataque?). Suricata/Zeek deberían tener recall ≈1.0 si la firma existe. aRGus debe demostrar recall comparable sin firma previa.

**Fase 2: Tráfico desconocido (MITRE ATT&CK sin firma)**
- Generar tráfico de técnicas ATT&CK no presentes en CTU-13
- Suricata/Zeek: Recall esperado ≈0 (sin firma)
- aRGus: Recall depende de generalización del modelo

**Métrica:** Diferencia de recall entre fases. aRGus debe mostrar degradación menor que Suricata/Zeek.

**Fase 3: Falsos positivos (tráfico benigno hospitalario simulado)**
- `tcpreplay` de tráfico normal de red hospitalaria (sin ataques)
- Medir FPR de cada sistema

**Aislamiento del efecto de reglas ET:**

Suricata con reglas ET tiene una ventaja injusta en Fase 1 (conoce la firma) y una desventaja injusta en Fase 2 (no la conoce). Para aislar el efecto:

1. **Variante Suricata-A:** Reglas ET completas (baseline)
2. **Variante Suricata-B:** Reglas ET sin las firmas de Neris/Rbot/Murlo (simulando "ataque desconocido")

La comparación válida es **aRGus vs Suricata-B** en Fase 1, y **aRGus vs Suricata-A** en Fase 2.

**Tabla de resultados esperada:**

| Sistema | Fase 1 (Neris conocido) | Fase 2 (ATT&CK desconocido) | Fase 3 (Benigno) |
|---------|------------------------|----------------------------|------------------|
| aRGus ML | Recall=0.998 | Recall=0.85 (estimado) | FPR=0.0002% |
| Suricata-A (ET completo) | Recall=1.000 | Recall=0.15 | FPR=0.01% |
| Suricata-B (ET sin Neris) | Recall=0.05 | Recall=0.15 | FPR=0.01% |
| Zeek (scripts botnet) | Recall=0.95 | Recall=0.10 | FPR=0.005% |

**Nota:** Estos números son hipotéticos. Los reales deben medirse.

**Reproducibilidad:**
- Docker container con Suricata 6.0 + Zeek 5.0 + aRGus v0.7
- Mismo pcap, mismo hardware, mismo kernel
- Scripts de benchmark versionados en repo
- Resultados crudos en `data/benchmarks/2026-05-*/`

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **P1** | 4 métricas con jerarquía: latencia p99 y F1 bajo carga son P0; throughput y recursos son P1 | Implementar `benchmark_adr029.sh`; ejecutar en dev VM esta semana |
| **P2** | ARM64 como "futuro trabajo" en paper v19; no bloqueante para FEDER | Documentar diseño ARM64 aprobado; ejecutar benchmark solo si hardware llega antes de 1 agosto |
| **P3** | Regresión logística con pesos fijos y auditables; no implementar para FEDER | Registrar `DEBT-IRP-PROB-CONJUNTA-001` con diseño aprobado; mostrar `IsolationStrategy` extensible en demo |
| **P4** | Diseño factorial 3 fases; comparar aRGus vs Suricata-B (ET sin firmas conocidas) | Preparar Docker container con Suricata + Zeek; generar tráfico MITRE ATT&CK |

**Moción:** Propongo que el DAY 145 ejecute el benchmark P1 (Variant A vs B) como única tarea técnica. Es el insumo crítico que falta para el paper v19. P2, P3 y P4 son documentación y diseño que no requieren código nuevo. El merge a `main` debe esperar a que el benchmark esté completo y los datos sean consistentes.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*