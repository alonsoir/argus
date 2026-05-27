## RESPUESTA DEL CONSEJO DE SABIOS — Métricas de Aceptación Hardware (ADR-029)

**Acta de deliberación científica**  
**Fecha:** 28 abril 2026  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Referencias:** ADR-029, paper arXiv:2604.04952 v18, requisitos FEDER, casos de uso hospitalario y municipal.

---

### Principios generales para las métricas de aceptación

Antes de responder pregunta por pregunta, el Consejo establece tres principios rectores:

1. **Reproducibilidad**: Cada métrica debe poder medirse con herramientas estándar (iperf3, tcpreplay, perf, /proc/meminfo, etc.) y en un entorno automatizable (Vagrant + scripts). Sin reproducibilidad, no hay método científico.

2. **Relevancia clínica/municipal**: Las métricas deben reflejar las restricciones reales de un hospital o ayuntamiento: presupuesto limitado, personal técnico escaso, necesidad de fiabilidad 24/7, y tráfico de red con picos predecibles (horarios de consulta, backups nocturnos).

3. **Defensa en profundidad**: El hardware debe proporcionar suficiente holgura (headroom) para que las defensas (AppArmor, Falco, etc.) no compitan con el pipeline por recursos. El sistema debe fallar de forma elegante (fail-closed) cuando se alcancen los límites.

---

### Respuesta a las preguntas específicas

#### Pregunta 1 — Throughput mínimo creíble para FEDER (hospital/municipio)

**Recomendación concreta:**
- **Throughput sin pérdida** (0% packet loss) sostenido durante **1 hora** ≥ **500 Mbps** para Variant A (eBPF/XDP).
- **Throughput sin pérdida** ≥ **200 Mbps** para Variant B (libpcap).
- **Ráfaga máxima** (≤ 1 segundo) tolerable hasta 1 Gbps con pérdida < 0.1% para ambas variantes.

**Justificación técnica:**
- Un hospital típico de 200 camas genera entre 100 y 300 Mbps de tráfico agregado en horas punta (imágenes médicas, EMR, VoIP, monitores). Una red municipal con 500 usuarios ronda los 200-400 Mbps. 500 Mbps proporciona un margen de seguridad del 25-50%.
- Los estudios de carga en redes de infraestructura crítica (NIST SP 800-82) recomiendan que los sistemas de detección no consuman más del 30% de la capacidad del enlace sobrante. Con enlaces de 1 Gbps, 500 Mbps dejan 500 Mbps para tráfico legítimo.
- 1 hora de sostenimiento descarta aceleración por caché y verifica estabilidad térmica en hardware pasivo (Raspberry Pi).

**Riesgo identificado:**
- Si el hospital tiene enlace de 100 Mbps (caso rural o municipal pequeño), 500 Mbps es inalcanzable. Necesitamos una **métrica escalada**: throughput ≥ 80% del enlace real. Por tanto, para la demo FEDER presentaremos **dos resultados**:
    * 500 Mbps en hardware commodity x86 (representativo de hospital mediano).
    * 100 Mbps en Raspberry Pi 5 (representativo de escuela o pequeño ayuntamiento).

**Test mínimo reproducible:**
```bash
# Desde un generador de tráfico (otra VM o máquina física) en la misma VLAN
tcpreplay -i eth1 --mbps=500 --pps=1000000 --duration=3600 captured_traffic.pcap
# Medir pérdidas desde el sniffer de aRGus:
argus-sniffer --stats --output-loss /tmp/loss.csv
# Condición de éxito: ratio_loss < 0.0001 (0.01%) durante los 3600 segundos.
```

---

#### Pregunta 2 — Delta de throughput eBPF/XDP vs libpcap: ¿métrica publicable?

**Recomendación concreta:**  
**Sí, el delta es publicable** en un paper de sistemas (OSDI, NSDI, o arXiv cs.NI). Se debe medir como **factor de mejora** y como **reducción de uso de CPU**.

**Justificación técnica:**
- XDP evita la copia de paquetes a la pila de red y el paso por netfilter, reduciendo la latencia y el consumo de CPU. En benchmarks públicos (Cilium, Facebook Katran), XDP alcanza 10-20 Mpps por núcleo frente a 1-2 Mpps de libpcap (AF_PACKET).
- Para el caso de aRGus, el sniffer no solo captura sino que también hace hash y envío a ZeroMQ. El delta será menor pero significativo (factor 3-5).
- Publicar estos números en el paper §4 (Arquitectura) o §7 (Evaluación) demostrará la ventaja de la Variant A para hospitales con alta carga.

**Métrica concreta para el paper:**
- **Throughput máximo a 0% pérdida** (Mbps) para Variant A y B en el mismo hardware.
- **CPU del sniffer** (porcentaje de un núcleo) a 500 Mbps.
- **Latencia extremo a extremo** (captura → detección → regla iptables) en microsegundos.

**Riesgo identificado:**
- Si medimos en hardware demasiado lento (ej. Raspberry Pi 4 con USB Ethernet), el delta podría ser pequeño o incluso inverso por overhead de driver. Publicaríamos ese resultado igualmente — la ciencia no exige superioridad, exige honestidad.

**Test reproducible:**
```bash
# Ejecutar ambos modos en la misma VM (cambiando flag de compilación)
make prod-build-x86 MODE=xdp   # Variant A
make prod-build-x86 MODE=pcap  # Variant B
# Mismo test de tcpreplay a 500 Mbps, medir CPU con:
pidstat -p $(pidof argus-sniffer) 1 60 > cpu.log
```

---

#### Pregunta 3 — ¿Métricas idénticas para ARM y x86? Perfil diferente

**Recomendación concreta:**  
**No idénticas**. ARM (Raspberry Pi) tiene un perfil de aceptación distinto, orientado a **entornos con menos de 100 usuarios**, **presupuesto mínimo** (≤ 150 €) y **consumo energético bajo**.

**Perfil ARM (Raspberry Pi 5, 8GB RAM):**  
| Métrica | Valor ARM | Justificación |
|---------|-----------|----------------|
| Throughput sin pérdida | ≥ 100 Mbps | Escuela, consultorio médico pequeño, centro de salud rural. |
| Latencia p50 | ≤ 50 ms | Más tolerante por menor escala. |
| CPU idle | ≥ 60% | El resto para sistema y otros servicios. |
| RAM libre tras arranque | ≥ 512 MB | Headroom para actualizaciones y logs. |
| Temperatura (sin ventilador) | ≤ 75°C | En uso continuo. |

**Perfil x86 (Celeron NUC o similar, 8GB RAM):**  
| Métrica | Valor x86 | Justificación |
|---------|------------|----------------|
| Throughput sin pérdida | ≥ 500 Mbps | Hospital mediano. |
| Latencia p50 | ≤ 15 ms | Respuesta rápida para firewalls automáticos. |
| CPU idle | ≥ 70% | Headroom para Falco + AppArmor + logs. |
| RAM libre | ≥ 1 GB | Para futuros modelos y cachés. |

**Riesgo identificado:**
- Exigir 500 Mbps a una Raspberry Pi 5 es imposible (su bus USB/Ethernet limita a ~300 Mbps reales). El test de aceptación fallaría injustamente.
- Por el contrario, aceptar 100 Mbps en x86 sería demasiado bajo y no demostraría capacidad para hospitales.

**Test reproducible para ARM:**
```bash
# Usar un generador de tráfico desde un puerto USB Ethernet dedicado (evitar USB compartido)
tcpreplay -i eth0 --mbps=100 --duration=1800 hospital_traffic_small.pcap
# Medir temperatura cada minuto
vcgencmd measure_temp
```

---

#### Pregunta 4 — Golden set de ML como test de aceptación hardware

**Recomendación concreta:**  
**Sí, absolutamente necesario**. El golden set (ADR-040) debe ejecutarse en el hardware real como parte del test de aceptación. La hipótesis es que el modelo es invariante a la arquitectura hardware (XGBoost embebido no usa instrucciones específicas más allá de SSE/NEON).

**Justificación técnica:**
- El modelo RandomForest de aRGus se basa en operaciones aritméticas de punto flotante y enteras. Diferentes implementaciones de librerías (libc, libxgboost) o diferencias en la gestión de memoria caché pueden alterar los resultados numéricos en el borde del clasificador.
- En el paper, reportamos F1=0.9985 sobre VM. Para la demo FEDER, debemos probar que ese mismo valor se mantiene en hardware real, o de lo contrario documentar la degradación.
- Es una **prueba de regresión hardware**: si falla, indica que el compilador o la biblioteca está usando instrucciones no portables.

**Test mínimo reproducible:**
```bash
# En hardware real, después de desplegar aRGus
cd /opt/argus/tests
./run_golden_set.py --input golden_traffic.pcap --output results.json
# Comparar con el baseline (guardado como golden_results_v2.json)
python3 compare_f1.py baseline.json results.json --tolerance 0.0005
# Condición de éxito: F1 >= 0.9980 (0.0005 de pérdida aceptable por ruido)
```

**Riesgo identificado:**
- Pequeñas diferencias de redondeo en ARM vs x86 pueden cambiar una clasificación marginal. Si la tolerancia es 0.0005, se debe justificar. Si es mayor, documentarlo como "el modelo es robusto a plataforma".

---

#### Pregunta 5 — Herramienta de generación de carga reproducible en Vagrant

**Recomendación concreta:**  
Combinación de **tres herramientas** según el objetivo:

| Propósito | Herramienta | Reproducibilidad | Justificación |
|-----------|-------------|------------------|----------------|
| Tráfico realista de ataque | `tcpreplay` con pcaps CTU-13, CIC-IDS-2017, o capturas hospitalarias | Alta (el mismo pcap) | Simula patrones reales de red. |
| Medición de throughput máximo | `iperf3` en modo UDP bidireccional + TCP | Alta (parámetros fijos) | Saturador simple, sin estado. |
| Latencia y micro-bursts | `hping3` con timestamps + `tcpdump` | Media | Detecta pérdidas de ráfaga corta. |

**Entorno de prueba en Vagrant:**
- VM generadora de tráfico: misma box Debian 12, con 2 NICs. Una NAT para control, otra en modo "red interna" con la VM objetivo.
- El tráfico se inyecta desde la VM generadora, nunca desde el host (evita variabilidad por CPU del host).
- Script de automatización: `test/performance/generate_load.sh` que acepta parámetros: `--mode {replay, iperf, latency}`, `--duration`, `--rate`.

**Test reproducible de throughput:**
```bash
# En VM generadora
vagrant ssh load-generator -- -t '
    iperf3 -c 192.168.50.100 -u -b 500M -t 60 -l 1400 -P 4 --bidir
' > /tmp/iperf_results.txt
# En VM objetivo, el sniffer debe reportar 0% loss.
```

**Riesgo identificado:**
- `tcpreplay` a alta velocidad puede ser limitado por la máquina generadora (si tiene CPU débil). Para 500 Mbps, basta un i5 moderno o Raspberry Pi 4 como generador. Documentar la configuración generadora.

---

#### Pregunta 6 — Criterio de éxito para FEDER: ¿funciona o mejor que comerciales?

**Recomendación concreta:**  
**Ambos, pero por separado.** El criterio principal debe ser "el sistema funciona" según las métricas anteriores. Secundariamente, si hay recursos, se puede añadir un **benchmark comparativo opcional** con alternativas open-source (Snort, Suricata, Zeek) en el mismo hardware.

**Justificación técnica:**
- El objetivo de la demo FEDER es demostrar la **viabilidad técnica** de un NDR asequible para hospitales, no necesariamente que supere a productos comerciales de 50.000 €/año. La propuesta de valor es el coste (hardware commodity + software open-source) y la facilidad de uso, no el récord de throughput.
- Sin embargo, para el paper y para los inversores, es útil mostrar cómo se compara con herramientas estándar en **igualdad de condiciones** (mismo hardware, misma pcap). Eso añade credibilidad.

**Criterio de éxito para FEDER (mínimo):**
- Cumplir todas las métricas de aceptación (throughput, latencia, F1, RAM, CPU idle) para al menos una variante (A o B) en al menos una plataforma (x86 o ARM).
- El sistema debe arrancar completamente con `systemctl start argus.target` y detenerse sin fugas de memoria en 24 horas de prueba.
- La demo debe realizarse **en directo**, sin trucos pregrabados.

**Benchmark comparativo (opcional, si hay tiempo):**
- Instalar Snort/Suricata en la misma máquina (con reglas básicas de comunidad).
- Ejecutar el mismo pcap de 1 hora de tráfico hospitalario simulado.
- Comparar: throughput alcanzable, % de detecciones F1, uso de CPU/RAM, tiempo de instalación/configuración.
- Publicar resultados en el paper como "aRGus frente a alternativas open-source".

**Riesgo identificado:**
- Si el benchmark comparativo muestra que aRGus es peor en algunos aspectos (ej. detección de ciertos ataques), no debe ocultarse. La honestidad científica exige reportarlo. El valor diferencial no es la mejor detección, sino el coste y la integración con defensa activa (firewall-acl-agent).

**Test mínimo reproducible para benchmark:**
```bash
# Instalar Suricata en la misma VM (después de desinstalar aRGus)
make suricata-install
suricata -c /etc/suricata/suricata.yaml -r hospital_traffic.pcap
# Comparar outputs (eve.json) con las alertas de aRGus mediante script python
```

---

### Tabla resumen: Métricas de aceptación mínimas para FEDER (hardware real)

| Métrica | Variant A (XDP) x86 | Variant B (libpcap) x86 | ARM (RPi5) Variant B | Medición (herramienta) |
|---------|---------------------|-------------------------|----------------------|------------------------|
| Throughput sin pérdida (1h) | **≥ 500 Mbps** | ≥ 200 Mbps | ≥ 100 Mbps | tcpreplay + argus-sniffer --stats |
| Latencia p50 (captura→alerta→iptables) | **≤ 15 ms** | ≤ 30 ms | ≤ 50 ms | hping3 + timestamp en fw logs |
| RAM libre tras arranque | **≥ 1 GB** | ≥ 1 GB | ≥ 512 MB | `free -m` |
| CPU idle durante tráfico normal (500 Mbps / 100 Mbps) | **≥ 70%** | ≥ 50% | ≥ 60% | `top -b -n 1` |
| F1 sobre golden set | ≥ 0.9985 (±0.0005) | igual | igual | golden_set.py |
| Tiempo de arranque pipeline (cold boot) | ≤ 30 s | ≤ 30 s | ≤ 45 s | systemd-analyze blame |
| Temperatura máxima (sin ventilador adicional) | N/A | N/A | ≤ 75°C | vcgencmd measure_temp |

**Nota:** Las métricas marcadas en **negrita** son las más críticas para la demostración FEDER.

---

### Próximos pasos recomendados

1. **Construir el banco de pruebas** con hardware real mínimo:
    - 1 nodo x86 (Intel NUC o Mini PC de 200 €).
    - 1 Raspberry Pi 5 (8 GB RAM) con disipador pasivo.
2. **Automatizar la suite de validación** en scripts `test/hardware_acceptance.sh` que ejecute todas las métricas y genere un informe HTML.
3. **Decidir las tolerancias concretas** (ej. pérdida máxima 0.01%) antes de comprar el hardware.
4. **Ejecutar la suite en la VM Vagrant primero** para establecer el baseline de referencia (que ya funciona). Luego ejecutar en hardware real y comparar.

El Consejo aprueba este conjunto de métricas como **suficiente para el go/no-go de la demo FEDER**, siempre que se documenten las condiciones exactas de cada test. La ciencia reproducible exige transparencia, no perfección.

*Firmado por los 8 modelos, 28 abril 2026.*  
*Via Appia Quality — “Lo que no se mide, no se mejora. Lo que no se reproduce, no es ciencia.”*