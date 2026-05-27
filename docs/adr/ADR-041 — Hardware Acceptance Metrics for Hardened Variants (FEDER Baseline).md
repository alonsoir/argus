# ADR-041 — Hardware Acceptance Metrics for Hardened Variants (FEDER Baseline)

| Campo        | Valor                                                                 |
|--------------|-----------------------------------------------------------------------|
| **Estado**   | PROPUESTO — pendiente de aprobación                                   |
| **Fecha**    | 2026-04-28                                                            |
| **Autor**    | Alonso Isidoro Román                                                  |
| **Prioridad** | BACKLOG — validación pre-FEDER, deadline 22 sep 2026                 |
| **Referencias** | ADR-030 (AppArmor-Hardened), ADR-031 (seL4-Genode), ADR-040 (ML Plugin Retraining Contract) |
| **Consejo de Sabios** | Consultado 2026-04-28, 8/8 modelos (Claude, ChatGPT-5, DeepSeek, Gemini, Grok, Mistral, Qwen, Kimi) |

---

## Contexto

ADR-030 define la variante hardened de producción (Debian + AppArmor + eBPF/XDP como Variant A, libpcap como Variant B). ADR-031 define la variante de investigación (seL4). Antes de comprar hardware físico para la demo FEDER y antes de ejecutar cualquier prueba, es necesario establecer el baseline de métricas de aceptación con criterio de éxito claro y falsable.

Sin este baseline, cualquier prueba sobre hardware real carece de criterio de éxito objetivo. El evaluador FEDER necesita ver números, no narrativa.

El Consejo de Sabios fue consultado el 28 de abril de 2026 con seis preguntas concretas. Este ADR consolida el consenso resultante.

---

## Decisión

### Niveles de despliegue objetivo

El Consejo (propuesta Qwen, adoptada por consenso) establece tres niveles de despliegue con métricas proporcionales:

| Nivel | Entorno | Usuarios | Hardware objetivo |
|---|---|---|---|
| **Nivel 1** | Clínica / Escuela | ≤ 50 | Raspberry Pi 4/5 |
| **Nivel 2** | Hospital medio / Municipio | 50-200 | x86 commodity (NUC, mini-PC ~300€) |
| **Nivel 3** | Gran hospital / Municipio grande | 200-500 | x86 commodity potenciado |

La demo FEDER debe cubrir **al menos Nivel 1 (ARM) y Nivel 2 (x86)** simultáneamente.

---

### Tabla de métricas mínimas de aceptación

| Métrica | Variant A XDP (x86) | Variant B libpcap (x86) | ARM RPi 4/5 | Herramienta de medición |
|---|---|---|---|---|
| Throughput sin packet loss | ≥ 500 Mbps / 1h | ≥ 200 Mbps / 1h | ≥ 100 Mbps / 1h | tcpreplay + ethtool -S |
| Latencia detección p50 | ≤ 15 ms | ≤ 30 ms | ≤ 50 ms | timestamps end-to-end |
| **Latencia end-to-end (→ iptables)** | **≤ 50 ms** | **≤ 100 ms** | **≤ 150 ms** | fw log timestamps |
| RAM disponible post-arranque | ≥ 512 MB | ≥ 512 MB | ≥ 256 MB | free -m |
| F1 sobre golden set (ADR-040) | ≥ 0.9985 | ≥ 0.9985 | ≥ 0.9980 | make golden-set-eval |
| CPU idle tráfico normal | ≥ 40% | ≥ 30% | ≥ 40% | mpstat |
| Tiempo arranque pipeline (cold boot) | ≤ 30 s | ≤ 30 s | ≤ 60 s | systemd-analyze |
| Packet loss sostenido | 0% | 0% | < 0.01% | ethtool -S |
| Estabilidad (soak test) | 0 crashes / 1h | 0 crashes / 1h | 0 crashes / 1h | journalctl |
| **Temperatura máxima (sin ventilador)** | N/A | N/A | **≤ 75°C** | vcgencmd measure_temp |

**Notas:**
- La latencia end-to-end (captura → alerta → regla iptables efectiva) fue aportación de DeepSeek. Es la métrica más relevante operacionalmente: mide el tiempo real hasta que el ataque queda bloqueado, no solo detectado.
- La temperatura ARM fue aportación de DeepSeek. Crítica para despliegue pasivo 24/7 en armarios de telecomunicaciones hospitalarios.
- Todas las métricas deben cumplirse **simultáneamente**. Fallo en cualquiera → variante no aceptada para FEDER.

---

### Delta Variant A (eBPF/XDP) vs Variant B (libpcap)

El delta entre variantes es la **contribución científica central de ADR-030** y debe publicarse en el paper.

| Métrica | Valor esperado | Método |
|---|---|---|
| Throughput (A/B ratio) | 2-5× | tcpreplay a tasas crecientes, mismo hardware |
| CPU @ 100 Mbps (A vs B) | 2-3× menos en A | pidstat / mpstat |
| Latencia p50 (A vs B) | 3-4× menor en A | timestamps |

Protocolo: mismo pcap, misma carga, mismo hardware, único cambio = sniffer. Repetir 5 veces cada variante. Reportar media ± desviación estándar.

Si el delta es pequeño a las cargas del público objetivo, se publica igual. "No hay diferencia a 100 Mbps pero sí a 500 Mbps" es un resultado científicamente válido y útil para quien dimensiona.

---

### Herramientas de generación de carga

Combinación estratificada, por consenso 8/8:

| Herramienta | Propósito | Configuración |
|---|---|---|
| **tcpreplay** | Tráfico real con ataques embebidos (CTU-13) | `--mbps=TARGET --loop=3 ctu13-neris-benchmark.pcap` |
| **iperf3** | Calibración de throughput máximo previo al test | `-c host -t 10 -P 4` |
| **hping3** | Edge cases y micro-bursts (aportación ChatGPT-5) | `--flood --rand-source` |

Distribución de tráfico en test FEDER (propuesta Qwen):
- 70% tráfico benigno base
- 20% pico benigno alto volumen
- 10% ataques embebidos (CTU-13 Neris)

El pcap de benchmark estándar (`ctu13-neris-benchmark.pcap`, subconjunto versionado con hash SHA-256) debe estar en el repo junto al golden set de ADR-040 antes de ejecutar cualquier test.

---

### Criterio de éxito para la demo FEDER

**Nivel mínimo (obligatorio):** el sistema cumple todas las métricas de la tabla anterior en al menos Variant A (x86) y Variant B (ARM), en demo en directo, sin trucos pregrabados.

**Nivel recomendado (opcional si hay tiempo):** benchmark comparativo contra Snort/Suricata en el mismo hardware. No contra soluciones enterprise. El argumento no es "aRGus es más rápido que Darktrace" — esa batalla no se pelea. El argumento es:

> "aRGus alcanza F1=0.9985 sobre CTU-13 con hardware de 100-300€, sin GPU, sin servicios externos, en menos de 100 MB de RAM. Snort/Suricata en el mismo hardware: [resultados honestos]."

Métrica de narrativa FEDER (propuesta Gemini, refinada por Consejo):
> *"Protección de grado hospitalario sobre hardware de 150€ con latencia end-to-end inferior a 100 ms."*

---

### Golden set ML como parte del test de aceptación hardware

Por consenso 8/8: **obligatorio**. El golden set (ADR-040, Regla 2) se ejecuta como último paso de cualquier test de aceptación hardware.

Tolerancia por diferencias de precisión numérica (ARM vs x86, diferencias SIMD/NEON vs AVX2):

```python
GOLDEN_F1_REFERENCE = 0.9985   # validado en VM de desarrollo
TOLERANCE_X86       = 0.0000   # sin tolerancia — mismo resultado esperado
TOLERANCE_ARM       = 0.0005   # ±0.05% por diferencias FP en NEON
```

Si F1 cae más de 0.0005 en ARM, es un bug de portabilidad, no una característica del hardware. Investigar antes de continuar.

Makefile target requerido:
```bash
make golden-set-eval ARCH=$(uname -m)
# exit 0 → métricas dentro de tolerancia
# exit 1 → regresión detectada, no proceder
```

---

### Pregunta abierta — Pipeline de evaluación: interno vs CI/CD externo

El Consejo no resolvió esta pregunta explícitamente. Queda como decisión del arquitecto:

**Opción A — Interno (Makefile + Vagrant)**: `make feder-demo` ejecuta toda la suite desde VM fría en < 30 minutos. Ventaja: reproducibilidad total en cualquier entorno con Vagrant. Desventaja: acoplamiento al entorno de despliegue.

**Opción B — CI/CD externo (GitHub Actions)**: workflow separado que se dispara al subir candidato. Ventaja: histórico de decisiones en GitHub, separación de responsabilidades. Desventaja: requiere infraestructura CI con acceso a datos de entrenamiento y pcaps de benchmark.

**Recomendación provisional**: Opción A para la demo FEDER (pragmatismo). Opción B como evolución post-FEDER cuando el pipeline de reentrenamiento (ADR-040) esté activo.

---

## Protocolo de test mínimo reproducible (completo)

```bash
# Paso 0: entorno limpio
vagrant destroy -f && vagrant up

# Paso 1: desplegar variante hardened
make prod-full-x86          # o prod-full-arm

# Paso 2: warmup
sleep 30

# Paso 3: calibrar interfaz
iperf3 -c <host> -b 600M -t 10

# Paso 4: test de carga real con ataques embebidos (1 hora)
tcpreplay --mbps=500 --loop=0 --duration=3600 ctu13-neris-benchmark.pcap -i eth0

# Paso 5: durante el test, monitorizar en paralelo
mpstat 1 > /tmp/cpu.log &
free -m >> /tmp/ram.log &
# En ARM adicionalmente:
# vcgencmd measure_temp >> /tmp/temp.log &

# Paso 6: validar packet loss
ethtool -S eth0 | grep -i drop

# Paso 7: validar ML (siempre el último paso)
make golden-set-eval ARCH=$(uname -m)

# Paso 8: soak test de estabilidad (revisar logs)
journalctl -u argus-* --since "1 hour ago" | grep -i "crash\|error\|OOM"
```

---

## Consecuencias

**Positivas:**
- Cualquier compra de hardware tiene criterio de aceptación verificable antes de gastarse el dinero.
- La demo FEDER tiene un protocolo reproducible que cualquier evaluador externo puede ejecutar.
- El delta XDP/libpcap medido con rigor es publicable como contribución independiente.
- La métrica de latencia end-to-end (→ iptables) demuestra valor operacional real, no solo detección teórica.

**Negativas / trade-offs:**
- 500 Mbps en x86 requiere NIC con soporte XDP nativo. Verificar driver antes de comprar hardware.
- El pcap de benchmark y el golden set deben existir y estar versionados antes de ejecutar cualquier test — work item previo.
- El soak test de 1 hora por variante × 2 arquitecturas = mínimo 4 horas de ejecución continua.

---

## Estado de implementación

| Tarea | Estado |
|---|---|
| Definición de métricas (este ADR) | PROPUESTO |
| Subconjunto pcap CTU-13 benchmark versionado | PENDIENTE |
| Script `make golden-set-eval` | PENDIENTE (depende de ADR-040) |
| Script `make feder-demo` (suite completa) | PENDIENTE |
| Compra hardware x86 (NUC / mini-PC) | PENDIENTE — post definición métricas |
| Compra Raspberry Pi 4/5 | PENDIENTE — post definición métricas |
| Primera ejecución en hardware físico | PENDIENTE |

---

## Referencias

- ADR-030: aRGus-AppArmor-Hardened (Variant A XDP, Variant B libpcap)
- ADR-031: aRGus-seL4-Genode (investigación, fuera de scope FEDER)
- ADR-040: ML Plugin Retraining Contract (golden set, walk-forward, guardrail)
- BACKLOG-FEDER-001: Presentación Andrés Caro Lindo (UEx/INCIBE), deadline 22 sep 2026
- CTU-13 Dataset: Neris, Rbot, Murlo scenarios
- Mercadona Tech Search Engine Playbook — José Ramón Pérez Agüera (gemba.es, abril 2026)
- Consejo de Sabios — Acta 2026-04-28: Claude, ChatGPT-5, DeepSeek, Gemini, Grok, Mistral, Qwen, Kimi