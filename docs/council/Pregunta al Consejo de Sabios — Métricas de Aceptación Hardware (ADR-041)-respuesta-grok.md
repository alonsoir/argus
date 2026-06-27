**Respuesta del Consejo de Sabios — Métricas de Aceptación Hardware (ADR-029)**

El Consejo valida el conjunto propuesto de métricas como base científica sólida, alineada con el método científico: cada una debe ser **cuantificable**, **reproducible** y **falsable** mediante experimentos controlados en Vagrant (desarrollo) y hardware físico (validación FEDER). Se completa y ajusta el cuadro con valores concretos derivados de benchmarks publicados (eBPF/XDP vs. libpcap, IDS en Raspberry Pi, requisitos FCC para sanidad, datasets CTU-13 y pruebas de NDR en hardware commodity). Todos los valores priorizan entornos de infraestructura crítica (hospital/municipio 10-500 usuarios) con hardware asequible (Raspberry Pi 4/5 o x86 mini-PC <300 €), sin GPU ni servicios externos, y con headroom para no comprometer el host.

### Métricas mínimas de aceptación validadas y completadas

| Métrica | Valor mínimo aceptado | Justificación técnica (basada en evidencia reproducible) |
|---------|-----------------------|---------------------------------------------------------|
| Throughput sin packet loss | ≥ 1000 Mbps (x86) / ≥ 500 Mbps (ARM/RPi) | FCC recomienda ≥1000 Mbps para hospitales; R-Snort (NIDS optimizado) alcanza 1 Gbps en RPi 5 con 0 % pérdida. |
| Latencia de detección (p50) | ≤ 50 ms | Inferencia ML en pipeline <2 μs/paquete; latencia total IDS/NDR típica <1 ms en bajo carga y <12 ms en referencia Mercadona. Asegura respuesta útil del firewall-acl-agent antes de que el ataque progrese. |
| RAM disponible tras arranque | ≥ 1024 MB | Debian minimal + AppArmor + pipeline usa ~300-500 MB; headroom ≥1 GB evita swapping en host (requisito Debian no-desktop). |
| F1 sobre golden set (ADR-040) | ≥ 0.9985 | Igual que en VM; arquitectura no debe degradar modelo (validado en x86_64 vs. ARM64). |
| CPU idle durante tráfico normal | ≥ 60 % | Garantiza que aRGus no satura host en tráfico típico (10-500 usuarios); benchmarks XDP en commodity muestran <40 % CPU a carga sostenida. |
| Tiempo de arranque del pipeline | ≤ 60 s | Reinicio de emergencia en <1 minuto (boot Debian + eBPF load + ML init). |
| 0 packet loss a carga sostenida | Sí (durante ≥300 s) | A throughput aceptado; CTU-13 + iperf3 confirman zero-drop en pruebas reproducibles. |

**Criterio general de éxito**: Todas las métricas deben cumplirse simultáneamente en hardware físico (x86 y ARM). Fallo en cualquiera → no aceptado para FEDER.

A continuación respondemos a las 6 preguntas específicas siguiendo el formato exigido.

### 1. Sobre Throughput
- **Recomendación concreta**: 1000 Mbps (x86) y 500 Mbps (ARM/RPi) como mínimo creíble a demostrar en FEDER.
- **Justificación técnica**: Redes hospitalarias/municipales típicas requieren 100-1000 Mbps (FCC: ≥1000 Mbps para hospitales; 100-500 Mbps para 10-50 usuarios). R-Snort en RPi 5 alcanza 1 Gbps con 0 % pérdida; XDP permite escalar a wire-speed en commodity. 100 Mbps es insuficiente para “crítico”; 1 Gbps es demostrable y competitivo sin hardware enterprise.
- **Riesgo identificado**: Sobreestimar → rechazo FEDER si hardware real no alcanza (ej. RPi saturado por ML). Subestimar → pérdida de credibilidad vs. soluciones comerciales.
- **Test mínimo reproducible (Vagrant)**: `iperf3 -c <target> -t 300 -P 8` + `tcpreplay --pps=rate --loop=10 ctu13.pcap` a 1000/500 Mbps; monitorizar `cat /proc/net/dev` y `ebpf-tool` para zero-drop durante 300 s. Script automatizado en Vagrantfile con `--rate-limit`.

### 2. Sobre Variant A (eBPF/XDP) vs Variant B (libpcap)
- **Recomendación concreta**: Delta esperado ≥3× throughput (A vs. B); sí, métrica publicable en paper.
- **Justificación técnica**: XDP procesa en driver (antes de sk_buff), alcanzando 10-26 Mpps/core vs. libpcap (userspace, ~1.4 Gbps max en benchmarks tcpdump). Estudios XDP muestran 2-10× ganancia en forwarding/drop. El delta es reproducible y destaca la ventaja hardened de Variant A (kernel-bypass).
- **Riesgo identificado**: Si delta <2× en hardware real (ej. generic XDP en RPi), pierde impacto publicable; o si libpcap se optimiza inesperadamente.
- **Test mínimo reproducible (Vagrant)**: Ejecutar idéntico pipeline A/B con `tcpreplay` a tasas crecientes (100-1000 Mbps) durante 60 s; medir Mbps con `bpftool prog` + `iftop`. Repetir 5× y reportar media ± stddev.

### 3. Sobre ARM/Raspberry Pi
- **Recomendación concreta**: Métricas de throughput escaladas (500 Mbps ARM vs. 1000 Mbps x86); resto idénticas (latencia, RAM, F1, CPU, boot). ARM tiene perfil diferente pero justificado por coste.
- **Justificación técnica**: RPi 5 alcanza 1 Gbps en NIDS optimizados pero CPU ARM64 limita vs. x86 (menor clock/cache). Galette y R-Snort confirman viabilidad XDP en SBC. Coste <50 € vs. >200 € x86 justifica menor throughput para despliegue edge (hospitales pequeños).
- **Riesgo identificado**: Si se exigen métricas idénticas, RPi falla y se descarta hardware asequible; o se sobrecompra x86 innecesariamente.
- **Test mínimo reproducible (Vagrant)**: Usar box ARM64 (ej. `generic/arm64`) en Vagrant; repetir tests de throughput/latencia vs. x86 box. Comparar con `lscpu` y `cat /proc/cpuinfo`.

### 4. Sobre el golden set como métrica hardware
- **Recomendación concreta**: Sí, ejecutar golden set (ADR-040) como parte obligatoria del test de aceptación hardware.
- **Justificación técnica**: Cambios de arquitectura (x86_64 → aarch64) pueden afectar precisión numérica (float, SIMD) o inferencia. F1 ≥0.9985 verifica reproducibilidad científica del modelo ML independientemente del hardware. Pruebas en VM ya lo validan; hardware debe confirmar no degradación.
- **Riesgo identificado**: Falso positivo en VM pero degradación sutil en hardware real (ej. endianness o cache effects) → modelo no fiable en producción.
- **Test mínimo reproducible (Vagrant)**: `python3 ml-detector/test_golden.py --hardware-mode --arch $(uname -m)` tras boot pipeline; comparar F1 vs. baseline VM con script CI (assert |ΔF1| < 0.0001).

### 5. Sobre la herramienta de generación de carga
- **Recomendación concreta**: Combinación **tcpreplay sobre PCAPs reales CTU-13 + iperf3**.
- **Justificación técnica**: tcpreplay + CTU-13 reproduce tráfico botnet real (malware + background) para validar detección ML y zero-loss. iperf3 estresa throughput sostenido (UDP/TCP) para medir límites. Combinación es estándar en literatura NDR/IDS y 100 % reproducible (mismos PCAPs, mismos rates).
- **Riesgo identificado**: Solo iperf3 (sintético) ignora patrones reales → F1 falso alto; solo tcpreplay puede no saturar hardware.
- **Test mínimo reproducible (Vagrant)**: Script: `tcpreplay --mbps=rate --loop=5 ctu13-scenario1.pcap & iperf3 -u -b 1G -t 300`; monitorizar con `bpftrace` y `tcpdump -c`. Guardar logs en `/vagrant/results/` para reproducibilidad.

### 6. Sobre el criterio de éxito para FEDER
- **Recomendación concreta**: Baseline = “el sistema funciona” (todas métricas ≥ umbrales en hardware físico). Opcional pero recomendado: benchmark comparativo ligero vs. alternativa comercial (ej. costo/año).
- **Justificación técnica**: FEDER prioriza viabilidad técnica y reproducibilidad (método científico). Métricas cuantitativas + golden set + zero-loss son suficientes y falsables. Comparativo (ej. vs. solución enterprise a 5000-10000 €/año) añade impacto pero no es obligatorio si hardware es asequible y supera requisitos FCC.
- **Riesgo identificado**: Solo “funciona” → débil ante evaluadores; benchmark comparativo falla si no se dispone de licencia comercial (coste/time).
- **Test mínimo reproducible (Vagrant)**: Ejecutar suite completa (throughput + golden + latencia) en script `acceptance-test.sh`; generar PDF con tablas + gráficos (matplotlib). Para comparativo: medir vs. baseline iperf3 sin aRGus o citar benchmarks públicos de Suricata/Snort en misma hardware.

Estas recomendaciones son derivadas directamente de evidencia empírica publicada y son verificables en cualquier laboratorio con Vagrant + hardware objetivo. El Consejo recomienda automatizar toda la suite en GitHub Actions + Vagrant para reproducibilidad total antes de comprar hardware (deadline FEDER 22 sep 2026). Cualquier ajuste posterior debe ir acompañado de nuevo experimento controlado.

El Consejo de Sabios está a disposición para revisar resultados de los tests iniciales.