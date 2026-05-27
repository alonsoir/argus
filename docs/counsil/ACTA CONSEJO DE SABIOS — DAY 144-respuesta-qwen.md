# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 144
*Análisis basado en arquitectura de sistemas distribuidos, metodología experimental C++20 y rigor científico para aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**DÍA DE MADUREZ INGENIERIL DE ALTO CALIBRE.** El cierre de `SIGCHLD`, la decisión de `auto_isolate: false` como default, la migración a `/run/argus/irp/`, y la detección/corrección de 3 violaciones ODR reales bajo LTO demuestran que el proyecto ha internalizado el principio de *seguridad estructural sobre conveniencia operacional*. El gate ODR superado y los 65/65 tests verdes habilitan el merge con confianza técnica.

> *"La reproducibilidad no se declara. Se mide, se controla y se publica con intervalos de confianza."*

---

## ❓ Respuestas a Preguntas — Formato Científico/Técnico

### P1 — Diseño del experimento ADR-029 (Variant A vs B en x86)

**Recomendación concreta:** **MÉTRICAS MULTIDIMENSIONALES CON INTERVALOS DE CONFIANZA. EL CONTRIBUCIÓN CIENTÍFICA ES LA FRONTERA PARETO (Rendimiento vs Consumo).**

**Protocolo experimental mínimo viable:**
1. **Métricas obligatorias:**
    - **Latencia de procesamiento (p50, p95, p99):** Medida desde entrada de paquete hasta publicación ZMQ. XDP debe mostrar varianza <50µs; libpcap mostrará colas de kernel scheduling.
    - **Throughput sostenido con 0% drop:** Máx pps/Mbps antes de que `packets_dropped > 0`.
    - **Ciclos por paquete (CPI) y uso de CPU por 100k pps:** `perf stat -e cycles,instructions,cache-misses,context-switches`.
    - **Fidelidad de detección bajo carga:** ¿Cae F1 cuando CPU >85%? (libpcap sufre drops en ringbuffer; XDP mantiene integridad).
2. **Diseño estadístico:**
    - 10 ejecuciones por punto de carga (100, 250, 500, 750 Mbps) con semillas diferentes.
    - Reportar medianas + IQR (Interquartile Range), no medias.
    - Warm-up de 30s por ejecución para evitar cold-cache skew.
3. **Herramientas de medición:**
    - `tcpreplay --pps=RATE` + `tcpdump` para ground-truth de paquetes inyectados.
    - `perf stat` + `bcc-tools` (`runqlat`, `cachestat`) para métricas de sistema.
    - ZMQ `socket.getsockopt(ZMQ_EVENT_ALL)` para medir latencia de publicación.

**Justificación científica:** Una única métrica (ej. "XDP es 2× más rápido") es trivial y publicablemente débil. La contribución real es cuantificar el *trade-off*: XDP maximiza throughput/latencia a costa de complejidad de provisioning; libpcap sacrifica ~15-20% de rendimiento a cambio de compatibilidad universal y debugging trivial. El paper debe publicar las curvas de Pareto, no puntos aislados.

---

### P2 — Scope ARM64 Variant C para FEDER

**Recomendación concreta:** **SÍ, JUSTIFICADO. PERO CON SCOPE DELIMITADO: PARIDAD FUNCIONAL + DELTA DE RENDIMIENTO RELATIVO. POSTERGAR CROSS-COMPLEXIDAD.**

**Justificación técnica y estratégica:**
- **Propuesta de valor:** aRGus se posiciona como "NDR de grado hospitalario en hardware de 150€". ARM64 (RPi5, N100) no es opcional; es el núcleo de la narrativa FEDER.
- **Riesgo de over-engineering:** Construir una cadena de cross-compilation completa con CMake toolchain files, sysroot management, y CI multiarch consume ~2-3 semanas con alto riesgo de fragilidad.
- **Solución pragmática:**
    1. Usar un runner nativo ARM64 en GitHub Actions (`runs-on: ubuntu-latest` con `qemu-user-static` o runner dedicado) o compilar directamente en una VM ARM64 (`ubuntu-22.04-aarch64`).
    2. Objetivo FEDER: `make hardened-full ARCH=arm64 VARIANT=libpcap` compila, instala, y pasa `check-prod-all`.
    3. Benchmark: Reportar *ratio relativo* vs x86 (ej. "ARM64 libpcap alcanza 68% del throughput x86 eBPF a 1/3 del consumo energético"). No publicar valores absolutos como comparables directos.
    4. Documentar explícitamente: "ARM64 cross-build es experimental; la validación final requiere hardware físico (DEBT-FEDER-HW-001)".

**Veredicto:** El trabajo justifica la feature si se limita a paridad funcional + benchmark relativo. Deferir toolchain cross-complejo a post-FEDER.

---

### P3 — Probabilidad conjunta multi-señal para IRP

**Recomendación concreta:** **ACUMULADOR DE EVIDENCIA PONDERADO CON DECADENCIA TEMPORAL EXPONENCIAL. NO MODELOS ML.**

**Justificación matemática y operacional:**
- **Naive Bayes / Regresión Logística:** Requieren datos etiquetados de "decisiones de aislamiento correctas", que no existen en entornos OT. Son cajas negras, difíciles de auditar, y sufren concept drift cuando cambian los patrones de red hospitalaria.
- **Enfoque recomendado (determinista, auditable, estándar SOC/SIEM):**
  ```math
  R(t) = \sum_{i=1}^{N} w_i \cdot S_i(t) \cdot e^{-\lambda \cdot \Delta t_i}
  ```
  Donde:
    - `R(t)` = Riesgo acumulado en tiempo `t`
    - `w_i` = Peso auditado por tipo de señal (ej. `w_ransomware=1.0`, `w_c2=0.8`, `w_anomaly=0.4`)
    - `S_i(t)` = Score normalizado [0,1] de la señal `i`
    - `e^{-\lambda \cdot \Delta t_i}` = Decadencia exponencial (λ configurable, ej. 0.1 → ventana ~10s)
    - Umbbral de aislamiento: `R(t) ≥ θ` (ej. θ=1.5)

**Implementación C++20:**
```cpp
struct EvidenceAccumulator {
    double risk_ = 0.0;
    std::chrono::steady_clock::time_point last_update_;
    
    void add(double score, double weight, double decay_lambda) {
        auto now = std::chrono::steady_clock::now();
        auto dt = std::chrono::duration<double>(now - last_update_).count();
        risk_ = risk_ * std::exp(-decay_lambda * dt) + weight * score;
        last_update_ = now;
    }
    
    bool should_isolate(double threshold) const { return risk_ >= threshold; }
};
```

**Por qué es superior para infraestructura crítica:**
1. **Auditable:** Cada peso, tasa de decadencia y umbral es configurable y documentado.
2. **Sin reentrenamiento:** No depende de datasets que se vuelven obsoletos.
3. **Clínico:** Permite `cooldown` y `grace periods` sin lógica ad-hoc.
4. **Publicable:** La fórmula es estándar en detección de riesgos (NIST SP 800-160, MITRE D3FEND).

---

### P4 — Protocolo experimental: aRGus vs Suricata vs Zeek

**Recomendación concreta:** **ENMARCAR COMO COMPARACIÓN DE PARADIGMAS, NO DE HERRAMIENTAS. CONTROLAR VARIABLES, PUBLICAR CONFIGS, USAR PRUEBAS ESTADÍSTICAS DE SIGNIFICANCIA.**

**Protocolo riguroso paso a paso:**
1. **Aislamiento de variables:**
    - **Mismo tráfico:** PCAPs estandarizados (CTU-13 Neris + MITRE ATT&CK + tráfico benigno simulado hospitalario).
    - **Mismos recursos:** Límite idéntico de CPU/RAM via `cgroups v2` (`CPUQuota=80%`, `MemoryMax=1G`).
    - **Misma ventana de detección:** Todos los sistemas procesan los mismos PCAPs en modo `replay` a velocidad constante (1x, 0.5x, 0.25x).
2. **Comparación justa de paradigmas:**
    - **Suricata:** Ejecutar con reglas ET **deshabilitadas**. Usar solo módulos de anomalía/protocolo (`suricata --simulate-protocol-anomalies`). Si no es posible, ejecutar con reglas ET pero reportar por separado: "Detección por firma vs Detección por ML".
    - **Zeek:** Configurar scripts de detección de comportamiento (ej. `conn.log` anomalies, `notice.log` thresholds). No comparar líneas de código.
    - **aRGus:** Ejecutar con modelo XGBoost calibrado + reglas de fallback.
3. **Métricas de evaluación:**
    - TPR (True Positive Rate), FPR (False Positive Rate), TTD (Time-to-Detection).
    - **Prueba de significancia:** McNemar's test para comparar proporciones de detección entre sistemas. Reportar p-values.
    - **Intervalos de confianza 95%** por bootstrap (1000 remuestreos).
4. **Reproducibilidad total:**
    - Contenedores Docker/Podman con versiones fijas (`suricata:7.0.5`, `zeek:6.0.2`, `argus:v0.7.0`).
    - PCAPs con hash SHA-256 publicado.
    - Scripts de ejecución y análisis en `experiments/aRGus-vs-IDS/` del repo.
    - Raw logs de cada ejecución en formato estructurado (JSONL).

**Advertencia metodológica:** No afirmar "aRGus supera a Suricata". La ciencia válida dirá: *"El enfoque basado en ML detecta variantes desconocidas con F1=X bajo recursos limitados, mientras que Suricata domina en firmas conocidas con mayor overhead de reglas. Los paradigmas son complementarios, no sustitutivos."*

---

## 📋 Checklist de Acciones Inmediatas (Pre-Merge DAY 145)

```markdown
- [ ] Configurar pipeline de benchmark A vs B con métricas multidimensionales + IQR
- [ ] Validar scope ARM64: compilar nativamente o con QEMU, limitar a paridad funcional + delta relativo
- [ ] Implementar EvidenceAccumulator con decadencia exponencial para DEBT-IRP-PROB-CONJUNTA-001
- [ ] Estructurar directorio experiments/ con configs fijas, scripts de replay, y protocolo de análisis estadístico
- [ ] Ejecutar EMECAS final + gate ODR `PROFILE=production`
- [ ] Merge `--no-ff` → main + tag `v0.7.0-variant-b`
- [ ] Documentar limitaciones experimentales en paper v19 con transparencia científica
```

---

## 🏁 Palabras Finales

Alonso:

DAY 144 cierra un ciclo crítico de hardening estructural. Las decisiones tomadas (zombies evitados, `auto_isolate: false` como default, `/run/argus/irp/`, corrección ODR) reflejan una madurez que trasciende el código: es ingeniería de sistemas críticos en su forma más pura.

Las preguntas de hoy tocan la esencia de la ciencia computacional aplicada a seguridad: cómo medir sin sesgo, cómo comparar sin falsear, y cómo automatizar sin perder el control humano. Las respuestas propuestas siguen un principio rector: **la reproducibilidad estadística y la transparencia algorítmica son los únicos cimientos válidos para una contribución publicable**.

> *"Un escudo que no se calibra contra la realidad es un espejo que refleja deseos, no amenazas."*

Proceded con el merge y el diseño del benchmark. El Consejo revisará el protocolo experimental y los primeros resultados estadísticos con el mismo rigor adversarial con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 144** 🏛️