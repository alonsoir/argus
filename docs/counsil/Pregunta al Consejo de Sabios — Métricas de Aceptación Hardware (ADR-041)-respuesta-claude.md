Con mucho gusto. Respondo en el formato que el propio documento del Consejo establece.

---

## Respuesta de Claude — Métricas de Aceptación Hardware (ADR-029)

---

### Pregunta 1 — Throughput mínimo para FEDER

**Recomendación**: **100 Mbps sostenidos sin packet loss durante 60 segundos** es el umbral correcto para la demo FEDER. 1 Gbps es innecesario y potencialmente contraproducente.

**Justificación**: Una red de hospital o municipio con 10-500 usuarios concurrentes genera tráfico real en el rango de 10-80 Mbps en condiciones normales. Demostrar 100 Mbps cubre ese rango con margen. Más importante: el argumento ante Andrés Caro Lindo no es "aRGus es rápido" sino "aRGus es suficiente y cabe en hardware que un hospital puede comprar". 1 Gbps requiere hardware más caro y aleja el mensaje del público objetivo.

**Riesgo**: Si el evaluador FEDER conoce soluciones enterprise que hacen 10 Gbps, 100 Mbps puede parecer modesto. Mitigación: enmarcar el número como "suficiente para el 95% de infraestructuras críticas de tamaño medio en España", con datos de referencia de INCIBE si los hay.

**Test mínimo reproducible**: `tcpreplay --mbps=100 --loop=0 captura-ctu13.pcap` durante 60 segundos sobre la interfaz monitoreada, con `ifconfig` o `ethtool` midiendo drops. El pipeline completo debe estar corriendo. Exit condition: 0 paquetes dropeados.

---

### Pregunta 2 — Delta Variant A (eBPF/XDP) vs Variant B (libpcap)

**Recomendación**: El delta es **la contribución científica central de ADR-029**, no un dato secundario. Publicarlo es obligatorio.

**Justificación**: eBPF/XDP opera en kernel space antes de que el paquete suba al stack de red, eliminando la copia al espacio de usuario. libpcap hace esa copia. A 100 Mbps la diferencia puede ser invisible; a 500 Mbps-1 Gbps debería ser medible en CPU y latencia. Ese delta — cuantificado con rigor — es exactamente el tipo de resultado que justifica un paper: misma funcionalidad, dos implementaciones, experimento controlado, resultado honesto.

**Riesgo**: Si el delta es pequeño o estadísticamente no significativo a las cargas típicas del público objetivo (100 Mbps), hay que publicarlo igual y explicar por qué. "No hay diferencia a 100 Mbps pero sí a 500 Mbps" es un resultado válido y útil para quien dimensiona.

**Test mínimo reproducible**: Mismo pcap, misma carga, mismo hardware, único cambio = Variant A vs Variant B. Medir: throughput máximo sin loss, CPU idle, latencia p50/p99 de detección. Repetir 5 veces cada variante, reportar media y desviación estándar.

---

### Pregunta 3 — ARM/Raspberry Pi: ¿mismo perfil que x86?

**Recomendación**: **Perfil diferente, explícitamente documentado**. ARM tiene umbral de throughput menor (propongo **50 Mbps** como mínimo) pero el argumento de coste lo justifica completamente.

**Justificación**: Una Raspberry Pi 5 cuesta ~80€. Un servidor x86 de gama baja, 400-800€. Para un centro de salud rural o un ayuntamiento pequeño, la diferencia es relevante. El mensaje correcto es: "Variant B en Raspberry Pi 5 protege redes de hasta 50 Mbps por 80€ de hardware. Variant A en x86 protege redes de hasta 500 Mbps por 500€." Dos perfiles, dos casos de uso, ambos legítimos.

**Riesgo**: eBPF/XDP (Variant A) puede no estar disponible o estar limitado en kernels ARM según la versión del SO. Verificar compatibilidad antes de comprar hardware.

**Test mínimo reproducible**: Mismo test que x86 pero con `--mbps=50`. Si la Pi aguanta 50 Mbps sin loss con F1 intacto, la variante ARM está validada para su caso de uso.

---

### Pregunta 4 — ¿Golden set ML como parte del test de aceptación hardware?

**Recomendación**: **Sí, obligatorio**. El golden set debe ejecutarse como último paso de cualquier test de aceptación hardware.

**Justificación**: Un cambio de arquitectura (x86 → ARM, kernel distinto, compilación con flags diferentes) puede introducir diferencias de precisión numérica en el modelo ONNX. F1=0.9985 en VM no garantiza F1=0.9985 en Raspberry Pi. Es poco probable que el delta sea grande, pero si existe y no lo detectamos, estamos desplegando un sistema con rendimiento no verificado. El golden set cuesta segundos de ejecución y elimina esa incertidumbre.

**Riesgo**: Ninguno relevante. El único coste es tener el golden set preparado antes (ADR-040, Regla 2), lo que de todas formas es necesario.

**Test mínimo reproducible**: `argus-eval --golden-set golden_set_v1.0.parquet --model plugin_rf_v1.onnx` con exit code 0 si F1 ≥ 0.9985, exit code 1 si no. Este comando debe existir como target de Makefile: `make golden-set-eval`.

---

### Pregunta 5 — Herramienta de generación de carga

**Recomendación**: **tcpreplay sobre pcaps reales de CTU-13** como herramienta principal. iperf3 como herramienta de calibración previa.

**Justificación**: tcpreplay reproduce tráfico real con los patrones exactos que el modelo fue entrenado a detectar — incluyendo los ataques. Eso es lo que queremos demostrar: no que el sistema aguanta 100 Mbps de tráfico genérico, sino que aguanta 100 Mbps de tráfico real con ataques embebidos y los detecta. iperf3 es útil para calibrar el entorno (verificar que la interfaz de red es capaz de los Mbps que queremos antes de medir aRGus), pero no tiene semántica de ataque.

**Riesgo**: tcpreplay requiere que las pcaps de CTU-13 estén disponibles en el entorno de test. Las pcaps son grandes (varios GB). Hay que definir qué subconjunto se usa como "pcap de benchmark estándar" y versionarlo junto al golden set.

**Test mínimo reproducible**:
```bash
# Paso 1: calibrar interfaz
iperf3 -c <host> -b 200M -t 10

# Paso 2: test real con ataque embebido  
tcpreplay --mbps=100 --loop=3 ctu13-neris-benchmark.pcap -i eth0
```
Durante el paso 2, aRGus debe detectar los flows de ataque con F1 ≥ 0.9985 y 0 packet loss.

---

### Pregunta 6 — Criterio de éxito para FEDER: ¿funciona o funciona mejor que X?

**Recomendación**: **Ambos, en ese orden**. Primero demostrar que funciona (criterios técnicos absolutos). Luego, un único benchmark comparativo de coste, no de rendimiento.

**Justificación**: Intentar superar en rendimiento a soluciones enterprise (Darktrace, Vectra, Claroty) es una batalla que no se gana y no hay que pelear. El argumento correcto es: "aRGus alcanza F1=0.9985 sobre CTU-13 — el mismo dataset que usan los papers académicos de referencia — con un coste de hardware de 80-500€ frente a los 20.000-100.000€/año de las alternativas enterprise." Eso es suficiente para el público objetivo de FEDER: organizaciones que hoy no tienen nada porque no pueden pagar nada.

**Riesgo**: El evaluador puede pedir datos comparativos que no tenemos (latencia vs. Snort, vs. Zeek). Mitigación: comparar contra Snort+Suricata (open source, misma liga) en vez de enterprise. Snort es un baseline razonable y públicamente documentado.

**Test mínimo reproducible**: Tabla en el paper/presentación con tres columnas: aRGus, Snort/Suricata, solución enterprise representativa. Filas: coste hardware, coste licencia/año, F1 publicado, RAM mínima, requiere GPU. Fuentes públicas para las filas de competencia.

---

## Resumen ejecutivo para el ADR-029

| Métrica | Valor propuesto (x86) | Valor propuesto (ARM) |
|---|---|---|
| Throughput sin packet loss | ≥ 100 Mbps / 60 s | ≥ 50 Mbps / 60 s |
| Latencia detección p50 | ≤ 50 ms | ≤ 100 ms |
| RAM disponible tras arranque | ≥ 256 MB | ≥ 128 MB |
| F1 sobre golden set | ≥ 0.9985 | ≥ 0.9985 |
| CPU idle tráfico normal | ≥ 30% | ≥ 20% |
| Tiempo arranque pipeline | ≤ 30 s | ≤ 60 s |
| Packet loss a carga sostenida | 0 | 0 |

Herramienta de carga: tcpreplay (ctu13-neris-benchmark.pcap, subconjunto versionado). Calibración previa con iperf3. Golden set ejecutado como último paso de cada test.

---

¿Lo guardo como fichero para que lo tengas junto al documento de la pregunta?