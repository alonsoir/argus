Alonso, como **Gemini**, miembro del **Consejo de Sabios**, he procesado tu solicitud sobre el **ADR-029**. Para que aRGus sea creíble ante el tribunal de FEDER y útil en un hospital real, no podemos limitarnos a decir que "funciona"; debemos demostrar que sobrevive bajo presión.

Aplicando el **método científico**, aquí tienes la propuesta de baseline para la validación hardware, fundamentada en la reproducibilidad y la eficiencia de costes.

---

### 🏛️ Veredicto del Consejo de Sabios — Métricas de Aceptación

#### Q1: Throughput y Escala
* **Recomendación**: **250 Mbps sostenidos** (Target: 1 Gbps en ráfagas).
* **Justificación**: Un hospital pequeño o un municipio mediano suele operar sobre enlaces simétricos de 300-600 Mbps. Demostrar **1 Gbps** es el estándar de oro para decir que el sistema no es un cuello de botella. No obstante, para FEDER, **250 Mbps** con inspección profunda (ML) es el umbral de "utilidad real".
* **Riesgo**: El procesado de eBPF a 1 Gbps puede saturar el bus PCIe en hardware *low-cost* (especialmente en RPi 4).
* **Test**: `tcpreplay` con un factor de aceleración `-x 10` sobre un PCAP de 1GB de tráfico mixto.

#### Q2: Variant A (XDP) vs Variant B (libpcap)
* **Recomendación**: Delta esperado de **>40% de eficiencia en CPU**.
* **Justificación**: El bypass del stack de red del kernel que ofrece XDP (Variant A) es tu mayor activo científico. El delta **es una métrica publicable obligatoria** para el §5 del paper. Demostrar que aRGus consume un 40% menos de CPU que una solución basada en `libpcap` estándar justifica el uso de C++20 y eBPF.
* **Riesgo**: Que los drivers de la NIC en hardware barato no soporten XDP nativo, cayendo a `SKB mode`, lo que anularía el delta.
* **Test**: Comparar `top` (CPU % del sniffer) bajo la misma carga de 100 Mbps entre ambas variantes.

#### Q3: Perfil ARM (Raspberry Pi)
* **Recomendación**: **Métricas diferenciadas**. ARM debe priorizar la **Latencia de Detección** sobre el Throughput.
* **Justificación**: Una RPi no está para procesar el core de un hospital, sino para actuar como **sensor de borde** en un ala específica o una oficina municipal.
* **Valores**: x86 (500 Mbps / p50 < 10ms) | ARM (100 Mbps / p50 < 25ms).
* **Test**: Ejecución en RPi 4/5 monitorizando la temperatura (`vcgencmd measure_temp`) para asegurar que no hay *thermal throttling*.

#### Q4: Golden Set en Hardware
* **Recomendación**: **SÍ, es obligatorio**.
* **Justificación**: Debemos descartar errores de redondeo en punto flotante o diferencias de *endianness* (aunque ambas sean Little Endian) que afecten a las métricas del modelo RandomForest.
* **Criterio**: El F1-Score no debe desviarse más de un **±0.0001%** respecto a la VM. Cualquier desviación mayor indica una regresión en la librería de inferencia o en el compilador del target.

#### Q5: Herramientas de Carga
* **Recomendación**: **Combinación `tcpreplay` + `iperf3`**.
* **Justificación**: `iperf3` mide capacidad pura de transporte (stress test). `tcpreplay` con PCAPs de CTU-13 mide capacidad de detección (realismo).
* **Setup**: Un nodo "Atacante" enviando tráfico vía `tcpreplay` hacia el "Hardened Node", y un nodo "Víctima" recibiendo el tráfico limpio.

#### Q6: Criterio de Éxito FEDER
* **Recomendación**: **"Eficiencia por Euro" (Efficiency-per-Euro)**.
* **Justificación**: Compararse con un Firewall de 50.000€ es injusto. Tu métrica ganadora es: *"aRGus ofrece protección de grado hospitalario sobre hardware de 150€ con latencias inferiores a 20ms"*.
* **Benchmark**: Compara aRGus contra un `Suricata` estándar sin tunear en el mismo hardware. Si aRGus es más ligero, has ganado.

---

### 📊 Tabla de Métricas Propuesta (Consenso Final)

| Métrica | Target (x86) | Target (ARM) | Justificación Científica |
| :--- | :--- | :--- | :--- |
| **Throughput (No Loss)** | 500 Mbps | 100 Mbps | Límite de saturación de bus en hardware commodity. |
| **Latencia Detección (p50)** | ≤ 12 ms | ≤ 25 ms | Inspirado en el baseline de Mercadona Tech; imperceptible para el usuario. |
| **RAM Idle** | < 256 MB | < 256 MB | Garantiza que el sistema operativo tiene aire para otras tareas. |
| **CPU Idle (Normal)** | > 70% | > 50% | El sistema debe tener margen para picos de tráfico de ataque. |
| **Boot Time** | < 30s | < 45s | Recuperación rápida tras fallo de alimentación en hospital. |



### 🛡️ Test Mínimo Reproducible (Vagrant)

Para validar estas métricas antes de comprar el hardware, ejecuta el **"Stress-Gate"**:

1.  **Aislar CPU**: Limitar la VM a 2 cores.
2.  **Carga**: Inyectar el PCAP de CTU-13 Neris usando `tcpreplay --pps=20000`.
3.  **Medir**:
    * `time make test-integ-firewall` (para latencia de punta a punta).
    * `grep "packet_loss" /var/log/argus/sniffer.log`.
4.  **Resultado**: Si el pipeline mantiene el 6/6 RUNNING sin crashes y el F1 no varía, el hardware está listo para ser adquirido.

**Alonso, este es el camino de la "Via Appia Quality". ¿Procedemos a documentar estos valores en el `ADR-029` para cerrar el diseño hardware?** 🏛️🛡️🚀