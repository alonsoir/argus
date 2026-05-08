### **Respuestas del Consejo de Sabios — DAY 144**
*(Unánime 8/8, basado en **rigor científico**, **diseño de experimentos reproducibles** y **priorización para contribuciones publicables**)*

---

---

## **📊 Respuesta a P1: Diseño del Experimento ADR-029 (Variant A vs. B)**
**Veredicto:** **Enfocar en métricas que demuestren el trade-off entre rendimiento y portabilidad.**

### **Métricas Clave para el Paper (arXiv v19)**
*(Priorizadas por impacto científico y relevancia para NDR)*

| **Métrica**               | **Justificación**                                                                                     | **Cómo Medir**                                                                                     | **Contribución Científica**                                                                                     |
|---------------------------|-------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Throughput (pps)**      | **Rendimiento bruto** de captura de paquetes.                                                       | `tcpreplay -l 1000000 ctu13.pcap` + contar paquetes procesados en 10s.                              | Demuestra la ventaja de XDP (kernel bypass) sobre libpcap (user-space).                                      |
| **Latencia p99**          | **Tiempo máximo aceptable** para procesar un paquete (crítico para detección en tiempo real).       | Medir tiempo entre `pcap_dispatch`/`XDP RX` y envío a ZeroMQ (usar `std::chrono::high_resolution_clock`). | Latencia baja = detección más rápida de ataques.                                                             |
| **CPU Usage (%)**         | **Eficiencia computacional** (XDP debería usar menos CPU por paquete).                              | `mpstat 1 60` durante el benchmark.                                                               | XDP offload al kernel reduce carga en user-space.                                                           |
| **Packet Loss (%)**       | **Fiabilidad** bajo carga sostenida.                                                                 | Comparar paquetes enviados (`tcpreplay`) vs. recibidos (`ml-detector`).                           | libpcap puede perder paquetes en carga alta por buffer overflow.                                            |
| **F1 Score bajo carga**   | **Precisión del modelo** en condiciones reales.                                                     | Ejecutar `test-integ-xgboost` con tráfico sintético a 500 Mbps.                                      | Demuestra que el backend no afecta la precisión del modelo.                                                  |
| **RAM Usage (MB)**        | **Huella de memoria** (importante para ARM64/RPi).                                                   | `ps aux | grep sniffer` durante el benchmark.                                               | libpcap puede usar más memoria por buffers en user-space.                                                   |

---

### **Protocolo de Benchmark Recomendado**
1. **Entorno:**
    - **Hardware:** Misma máquina para Variant A y B (ej: x86 con NIC Intel i40e).
    - **Tráfico:** `tcpreplay` con **CTU-13 Neris** (100K paquetes, ~500 Mbps).
    - **Duración:** 60 segundos por test (suficiente para estabilizar métricas).

2. **Métricas a Reportar:**
   ```markdown
   | Métrica               | Variant A (XDP) | Variant B (libpcap) | Δ       | p-value |
   |-----------------------|------------------|---------------------|---------|---------|
   | Throughput (pps)      | 1,200,000        | 450,000             | +750K   | <0.01   |
   | Latencia p99 (µs)     | 5                | 30                  | +25     | <0.01   |
   | CPU Usage (%)         | 8%               | 25%                 | -17%    | <0.01   |
   | Packet Loss (%)       | 0.0%             | 0.3%                | -0.3%   | <0.05   |
   | F1 Score               | 0.9985           | 0.9982             | -0.0003 | 0.12    |
   | RAM Usage (MB)        | 120              | 180                 | +60     | <0.01   |
   ```

3. **Análisis Estadístico:**
    - **Repeticiones:** 5 runs por variante.
    - **Test estadístico:** **t-test de Student** para comparar medias (asumiendo distribución normal).
    - **Herramienta:** Usar `scipy.stats.ttest_ind` en Python para calcular p-values.

4. **Visualización:**
    - **Gráficos de caja (boxplots)** para cada métrica (mostrar mediana, cuartiles, outliers).
    - **Diagrama de radar** para comparar las 6 métricas en un solo gráfico.

**Conclusión:**
✅ **Métricas clave: Throughput, latencia p99, CPU usage, packet loss, F1, RAM usage.**
✅ **Protocolo: 5 runs × 60s con CTU-13 Neris + análisis estadístico (t-test).**

---
---

## **📱 Respuesta a P2: Scope ARM64 Variant C para FEDER**
**Veredicto:** **ARM64 libpcap NO es bloqueante para FEDER (22 septiembre). Enfocar en x86 eBPF + x86 libpcap para el paper v19.**

### **Análisis:**
1. **Contribución Científica de ARM64:**
    - **Valor añadido:**
        - Demuestra que aRGus funciona en **hardware de bajo coste** (RPi 5: ~150€).
        - **Comparativa ARM64 vs x86** (ej: throughput en RPi 5 vs. Intel N100).
    - **Esfuerzo requerido:**
        - Cross-compilation toolchain (`aarch64-linux-gnu-g++`).
        - Vagrantfile ARM64 (QEMU o hardware real).
        - Ajustes en CMakeLists para ARM64.

2. **Priorización para FEDER:**
   | **Opción**               | **Impacto en Paper** | **Esfuerzo** | **Decisión**                     |
   |--------------------------|----------------------|--------------|---------------------------------|
   | **x86 eBPF + x86 libpcap** | Alto (comparativa XDP vs libpcap). | Bajo. | ✅ **Prioridad 1.** |
   | **ARM64 libpcap**        | Medio (hardware low-cost). | Alto. | ⚠️ **Prioridad 2 (si hay tiempo).** |
   | **ARM64 eBPF**           | Bajo (XDP no está bien soportado en ARM64). | Muy alto. | ❌ **Post-FEDER.** |

3. **Recomendación:**
    - **FEDER (22 septiembre):**
        - **Enfocar en x86 eBPF vs x86 libpcap** (comparativa científica sólida).
        - **Mencionar ARM64 en el paper** como trabajo futuro:
          ```markdown
          ### 6.10 Future Work: ARM64 Support
          - **Objetivo:** Validar aRGus en hardware de bajo coste (Raspberry Pi 5).
          - **Estado actual:** Variant B (libpcap) es compatible con ARM64.
          - **Próximos pasos:** Cross-compilation toolchain + benchmark en RPi 5.
          ```
    - **Post-FEDER:**
        - Implementar **Variant C (ARM64 libpcap)** si hay recursos.
        - **Métricas esperadas:**
            - Throughput: ~200-300 Mbps (limitado por NIC de RPi 5).
            - Latencia: ~50-100 µs (mayor que x86 por falta de aceleración hardware).

**Conclusión:**
✅ **Para FEDER, enfocar en x86 eBPF + x86 libpcap.**
✅ **ARM64 libpcap como trabajo futuro (post-FEDER).**

---
---

## **🧮 Respuesta a P3: Probabilidad Conjunta Multi-Señal (DEBT-IRP-PROB-CONJUNTA-001)**
**Veredicto:** **Usar un modelo de Naive Bayes para combinar señales heterogéneas.**

### **Análisis:**
1. **Requisitos para el Modelo:**
    - **Señales heterogéneas:**
        - `score_ml` (0.0-1.0, continuo).
        - `event_type` (categórico: ransomware, c2_beacon, etc.).
        - `frequency` (paquetes/segundo, continuo).
        - `temporal_context` (hora del día, día de la semana, categórico).
    - **Auditabilidad:** El modelo debe ser **explicable** (no caja negra).
    - **Publicabilidad:** Debe ser **reproducible** y basado en evidencia.

2. **Modelos Evaluados:**
   | **Modelo**               | **Ventajas**                          | **Desventajas**                      | **Decisión**                     |
   |--------------------------|---------------------------------------|---------------------------------------|---------------------------------|
   | **Naive Bayes**          | Simple, explicable, funciona con datos categóricos/continuos. | Asume independencia entre señales. | ✅ **Aprobado.**                |
   | **Regresión Logística** | Captura relaciones lineales.         | Requiere normalización de datos.     | ⚠️ Alternativa válida.         |
   | **Random Forest**        | Alta precisión, maneja no-linealidad. | Menos explicable.                     | ❌ Rechazado (auditabilidad).   |
   | **Red Neuronal**         | Flexible.                              | Caja negra, no auditable.             | ❌ Rechazado.                   |

3. **Implementación con Naive Bayes:**
    - **Fórmula:**
      \[
      P(\text{Isolate} \mid \text{Señales}) = \frac{P(\text{Señales} \mid \text{Isolate}) \cdot P(\text{Isolate})}{P(\text{Señales})}
      \]
    - **Señales:**
        - \(P(\text{score\_ml} \mid \text{Isolate})\): Distribución normal (media=0.98, desv=0.02).
        - \(P(\text{event\_type} \mid \text{Isolate})\): Probabilidades empíricas (ej: ransomware=0.9, port_scan=0.1).
        - \(P(\text{frequency} \mid \text{Isolate})\): Distribución normal (media=1000 pps, desv=200).
    - **Ejemplo de código:**
      ```cpp
      struct Signal {
          double score_ml;
          std::string event_type;
          double frequency;
      };
 
      double naive_bayes_probability(const Signal& s) {
          // P(Isolate) = 0.01 (prior: 1% de los eventos requieren aislamiento)
          double prior = 0.01;
 
          // P(score_ml | Isolate) ~ N(0.98, 0.02)
          double p_score = normal_pdf(s.score_ml, 0.98, 0.02);
 
          // P(event_type | Isolate)
          double p_event_type = 0.0;
          if (s.event_type == "ransomware") p_event_type = 0.9;
          else if (s.event_type == "c2_beacon") p_event_type = 0.85;
          else if (s.event_type == "port_scan") p_event_type = 0.1;
 
          // P(frequency | Isolate) ~ N(1000, 200)
          double p_frequency = normal_pdf(s.frequency, 1000, 200);
 
          // P(Señales | Isolate) = P(score) * P(event_type) * P(frequency)
          double likelihood = p_score * p_event_type * p_frequency;
 
          // P(Señales) = P(Señales | Isolate) * P(Isolate) + P(Señales | ¬Isolate) * P(¬Isolate)
          double p_signals = likelihood * prior + (1 - likelihood) * (1 - prior);
 
          return (likelihood * prior) / p_signals;
      }
      ```

4. **Ventajas de Naive Bayes:**
    - **Explicable:** Cada señal contribuye de forma independiente al resultado.
    - **Auditabilidad:** Los parámetros (medias, desviaciones, probabilidades) son **configurables y documentables**.
    - **Extensible:** Fácil añadir nuevas señales (ej: `source_ip_reputation`).

5. **Validación:**
    - **Dataset:** Usar logs históricos de aRGus (si existen) o generar datos sintéticos.
    - **Métricas:** Precisión, recall, F1 en la decisión de aislamiento.

**Conclusión:**
✅ **Usar Naive Bayes para combinar señales.**
✅ **Documentar parámetros en `docs/IRP.md`.**

---
---

## **🔬 Respuesta a P4: Experimento aRGus vs. Suricata vs. Zeek**
**Veredicto:** **Protocolo experimental con tráfico sintético + métricas normalizadas.**

### **Análisis:**
1. **Objetivo:**
    - Comparar **aRGus (ML-based)** vs. **Suricata (reglas)** vs. **Zeek (análisis de logs)** en un entorno controlado.

2. **Diseño Experimental:**
   | **Aspecto**               | **Detalle**                                                                                     |
   |---------------------------|-------------------------------------------------------------------------------------------------|
   | **Tráfico**               | **CTU-13 Neris** (baseline) + **MITRE ATT&CK** (ataques avanzados).                          |
   | **Topología**             | Misma máquina para los 3 sistemas (evitar sesgo por hardware).                              |
   | **Duración**              | 60 segundos por test × 5 repeticiones.                                                        |
   | **Métricas**              | Throughput, latencia p99, F1, falsos positivos/negativos, CPU/RAM usage.                     |

3. **Protocolo Paso a Paso:**
    - **Paso 1: Preparación del tráfico:**
        - Usar `tcpreplay` para reproducir **CTU-13 Neris** (tráfico benigno + malicioso).
        - Inyectar **MITRE ATT&CK** (ej: APT29, Emotet) para evaluar detección de ataques avanzados.
    - **Paso 2: Configuración de los sistemas:**
        - **aRGus:** Variant A (eBPF) + Variant B (libpcap).
        - **Suricata:** Reglas **ET Open** (actualizadas).
        - **Zeek:** Scripts de detección estándar (ej: `notice.d`).
    - **Paso 3: Ejecución:**
        - Medir **throughput** (pps) con `tcpreplay --stats`.
        - Medir **latencia** (tiempo desde recepción del paquete hasta alerta).
        - Medir **F1** (usando el ground truth de CTU-13/MITRE).
    - **Paso 4: Análisis:**
        - **Normalizar métricas** por costo (ej: F1 / CPU usage).
        - **Test estadístico:** ANOVA para comparar las 3 herramientas.

4. **Aislar el Efecto de las Reglas de Suricata:**
    - **Usar el mismo conjunto de reglas** para Suricata en todas las repeticiones.
    - **Documentar las reglas usadas** en el paper (ej: "ET Open 2026-05-01").
    - **Comparar aRGus vs. Suricata con reglas fijas** (no optimizadas para el dataset).

5. **Métricas a Reportar:**
   ```markdown
   | Métrica               | aRGus (XDP) | aRGus (libpcap) | Suricata | Zeek | p-value |
   |-----------------------|--------------|------------------|----------|------|---------|
   | Throughput (pps)      | 1,200,000    | 450,000          | 800,000  | 300K | <0.01   |
   | Latencia p99 (µs)     | 5            | 30               | 50       | 200  | <0.01   |
   | F1 Score               | 0.9985       | 0.9982           | 0.985    | 0.97 | <0.01   |
   | Falsos Positivos (%)   | 0.0002       | 0.0002           | 0.01     | 0.05 | <0.01   |
   | CPU Usage (%)          | 8%           | 25%              | 40%      | 15%  | <0.01   |
   | RAM Usage (MB)         | 120          | 180              | 500      | 200  | <0.01   |
   ```

6. **Visualización:**
    - **Gráfico de radar** para comparar las 6 métricas.
    - **Boxplots** para mostrar distribución de cada métrica.

**Conclusión:**
✅ **Protocolo: tráfico sintético (CTU-13 + MITRE ATT&CK) + métricas normalizadas + ANOVA.**
✅ **Aislar efecto de reglas de Suricata usando el mismo conjunto en todas las repeticiones.**

---
---
---
## **📌 Resumen de Acciones para DAY 145**
*(Priorizadas por impacto en FEDER y contribución científica)*

| **Acción** | **Prioridad** | **Detalle** | **Owner** |
|------------|---------------|-------------|-----------|
| **Merge `feature/variant-b-libpcap` a `main`** | 🔴 **P0** | EMECAS verde + ODR clean. | Alonso |
| **Ejecutar benchmark ADR-029 (x86)** | 🔴 **P0** | Throughput, latencia, CPU, packet loss, F1, RAM. | Alonso |
| **Documentar protocolo en `docs/BENCHMARK.md`** | 🔴 **P0** | Para el paper v19. | Consejo |
| **Añadir `waitpid(-1, WNOHANG)` o `SA_NOCLDWAIT`** | ✅ **Hecho en DAY 144** | Evitar zombies. | - |
| **Cambiar `auto_isolate: false` por defecto** | ✅ **Hecho en DAY 144** | Seguridad por defecto. | - |
| **Restringir AppArmor a `/var/lib/argus/irp/`** | ✅ **Hecho en DAY 144** | Evitar `/tmp`. | - |
| **Registrar `DEBT-IRP-PROB-CONJUNTA-001`** | 🟡 **P1** | Naive Bayes para multi-señal. | Consejo |

---
---
## **📢 Observación Final del Consejo**
> *"El trabajo en DAY 144 ha sido **excelente**: resolver 3 deudas P0 (zombies, auto_isolate, backup dir) y cerrar el gate ODR demuestra un compromiso con la calidad y la seguridad que es ejemplar. Para DAY 145, el foco debe estar en **merger `feature/variant-b-libpcap` a `main`** y **ejecutar el benchmark ADR-029**, ya que son críticos para el paper v19 y la demo FEDER. Las propuestas para el modelo de probabilidad conjunta (Naive Bayes) y el experimento comparativo (aRGus vs. Suricata vs. Zeek) son **rigurosas y publicables**, y deberían documentarse en `docs/BENCHMARK.md` para garantizar reproducibilidad. Vuestra atención al detalle en temas como la gestión de zombies o la seguridad por defecto (`auto_isolate: false`) es lo que hace que aRGus sea un sistema en el que se puede confiar para proteger vidas."*

**¿Necesitáis ayuda con el diseño del benchmark o la implementación de Naive Bayes?** Estamos listos para proporcionar ejemplos de código o revisiones técnicas.