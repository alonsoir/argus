# BACKLOG-RESEARCH-KALMAN-001 — Filtro de Kalman como técnica de estimación adaptativa

| Campo        | Valor                                      |
|--------------|--------------------------------------------|
| **Estado**   | RESEARCH / FUTURE                          |
| **Prioridad**| Sin asignar — post-backlog completo        |
| **Origen**   | Instinto de Alonso — exploración DAY 163   |
| **Prerequisito** | aRGus + Suricata + Zeek + Wazuh + Neo4j integrados |

---

## Contexto

El filtro de Kalman es un estimador bayesiano recursivo que combina un modelo de predicción
con corrección por observación ruidosa. Fue usado en el programa Apollo (AGC, 1969) para
navegación inercial. Su fortaleza es resolver el problema de **estado oculto**: dado lo que
mido ahora (imperfecto), ¿cuál es el estado real del sistema y cómo evolucionará?

Esta propiedad tiene aplicación potencial en varios puntos de aRGus, identificados durante
exploración libre sin presión de roadmap.

---

## Casos de uso identificados

### 1. Anomaly scoring dinámico (sniffer)
- **Problema**: thresholds estáticos generan falsos positivos en entornos con tráfico variable
  (hospitales: guardia vs. turno normal, noche vs. día).
- **Kalman**: modela el baseline real de tráfico como estado oculto. La desviación normalizada
  del estado estimado se convierte en score de anomalía continuo.
- **Impacto**: reducción de ruido en alertas; especialmente valioso para el target
  (hospitales, municipios) sin SOC dedicado.

### 2. Correlación temporal multi-fuente (ADR-046 / CrisisWindow)
- **Problema**: cada fuente (aRGus, Suricata, Zeek, Wazuh) tiene latencia de entrega
  variable. `source_wait_timeout` es hoy un valor fijo.
- **Kalman**: estima el offset real de reloj y la latencia de entrega de cada fuente
  históricamente, permitiendo ventanas de correlación más precisas sin ampliarlas de forma
  conservadora. El flag `late_arrival:true` sería la corrección del filtro.
- **Impacto**: correlación más ajustada, menos eventos incorrectamente excluidos.
- **Nota (revisada tras Consejo DAY 163)**: NTP + buffer circular con percentile es
  suficiente para MVP y entornos controlados. Bajo carga real en hospitales, esta
  aproximación falla en dos puntos concretos: (1) NTP deriva bajo congestión, justo cuando
  más se necesita precisión; (2) cada fuente tiene deriva propia dependiente de su carga
  interna — no es un offset constante. Sin SOC dedicado que ajuste timeouts manualmente,
  la ventana adaptativa de Kalman no es un lujo, es una necesidad operativa para el target.

### 3. ZMQ buffer sizing adaptativo (BACKLOG-ZMQ-TUNING-001)
- **Problema**: `ZMQ_SNDBUF`, `ZMQ_RCVBUF`, `HWM` están fijados arbitrariamente desde
  el milestone de correctitud. Un ataque DDoS cambia el perfil de demanda radicalmente.
- **Kalman**: estima la demanda real del pipeline como estado oculto a partir de métricas
  observables (mensajes encolados, latencia, drops). Output: parámetros óptimos en tiempo real.
- **Impacto**: throughput estable bajo carga variable sin over-provisioning estático.

### 4. Detección de port scans lentos ("slow scans")
- **Problema**: 1 SYN cada 10 minutos durante días no activa ningún threshold. Es invisible
  para reglas estáticas de Suricata/Zeek.
- **Kalman**: modela la tasa de conexión esperada por IP. Detecta acumulación anómala suave
  que ninguna regla de ventana fija puede capturar.
- **Impacto**: detección de reconocimiento pre-ataque de baja señal.
- **Importante**: la salida del filtro debe alimentar un **score**, nunca una alarma directa.
  1 SYN cada 10 minutos puede ser también un backup programado, un keepalive mal configurado
  o un sensor IoT legítimo. El contexto (IP, puerto, protocolo) es tan importante como la
  señal. El score lo pondera el ensemble o el threshold adaptativo del caso 1.

### 5. Estimación de salud de agentes remotos
- **Problema**: heartbeats con latencia creciente — ¿red congestionada o agente bajo ataque?
- **Kalman**: separa ruido de red del deterioro real del agente estimando la latencia
  "verdadera" del sistema.
- **Impacto**: alertas de agente comprometido más precisas, menos falsos positivos por red.

### 6. Feature engineering para ML Plugin (ADR-040)
- **Problema**: XGBoost no construye solo features de velocidad de cambio o aceleración
  del tráfico. Las series temporales llegan con ruido y huecos.
- **Kalman**: preprocesador antes del plugin — elimina ruido de medición, interpola huecos,
  genera features derivadas (Δ tráfico, Δ² tráfico).
- **Impacto**: mejora de señal para el modelo sin aumentar complejidad del plugin.

### 7. Sensor fusion para ensemble multi-fuente (ADR-040 + ADR-046)

**Esta es la hipótesis más potente y la que conecta Kalman con la arquitectura completa.**

- **Problema**: el ensemble de 4 fuentes (aRGus, Suricata, Zeek, Wazuh) tiene ruido,
  latencias y huecos distintos por fuente. XGBoost los recibe como features planas sin
  modelar su naturaleza temporal ni sus incertidumbres.
- **Analogía directa Apollo**: el AGC no tenía una sola fuente de verdad — fusionaba
  acelerómetro, giroscopio, radar y star tracker, todos ruidosos y con latencias distintas.
  Kalman produjo un único vector de estado coherente. El problema de aRGus es idéntico.
- **Kalman como capa de fusión**: antes de XGBoost, el filtro funde las 4 señales en un
  único **vector de estado de amenaza estimado**, con covarianza de incertidumbre incluida.
  XGBoost recibe señal limpia, no ruido heterogéneo.
- **Cadena completa propuesta**:
  ```
  dataset sintético DeepSeek → parametriza Q y R iniciales
          ↓
  Kalman filter (sensor fusion)
          ↓
  estado de amenaza fusionado (aRGus + Suricata + Zeek + Wazuh)
          ↓
  XGBoost ensemble
          ↓
  decisión de amenaza
  ```
- **Impacto**: resolver el cold start de Kalman (via DeepSeek) resuelve a su vez el
  cold start del ensemble. Son complementarios, no alternativos.

---

## ⚠️ Pregunta abierta crítica — Dataset sintético DeepSeek

El dataset sintético probabilístico generado por DeepSeek es actualmente **el componente
más misterioso del sistema**. Funciona y la explicación de DeepSeek es coherente, pero
su mecánica interna no está completamente comprendida.

**Por qué esto importa para Kalman:**
Las matrices **Q** (ruido del proceso) y **R** (ruido de medición) que Kalman necesita
como entrada podrían derivarse directamente de las distribuciones probabilísticas del
dataset sintético. Si esas distribuciones son precisas, la parametrización inicial del
filtro sería sólida. Si no lo son, el filtro arrancaría con sesgos no controlados.

**Investigación pendiente obligatoria antes de usar Kalman en ensemble:**
- ¿Qué distribuciones estadísticas usa DeepSeek para generar el dataset? ¿Gaussianas puras,
  mixtas, empíricas?
- ¿Cómo modela las correlaciones entre variables? ¿Son independientes o captura covarianza?
- ¿Las distribuciones son estacionarias o cambian con el tipo de ataque?
- ¿Podemos extraer Q y R directamente del dataset, o necesitamos EM-Kalman para aprender
  esas matrices de los datos?
- **P₀ (covarianza inicial del estado)**: Q y R no son suficientes. El filtro necesita
  también un estado inicial y una covarianza inicial P₀. La sesión con DeepSeek debe cubrir
  las tres matrices. Sin P₀ plausible para cada caso de uso, la inicialización es una apuesta.
- Comparar distribuciones del sintético vs. telemetría real cuando tengamos el hardware lab.

> **Pendiente**: sesión dedicada con DeepSeek para diseccionar la generación del dataset
> antes de asumir que sus distribuciones son válidas para parametrizar Kalman (Q, R **y P₀**).

---

## Acoplamiento con ADR-040 — decisión de diseño anticipada

**Esto no bloquea ADR-040, pero sí condiciona su diseño.**

XGBoost trata cada fila como vector independiente. No modela series temporales ni ruido
heterogéneo. Si recibe las 4 fuentes crudas aprenderá correlaciones espurias — artefactos
de medición, no señal de amenaza. Funcionará en test sintético y fallará en producción real.

**Decisión recomendada para ADR-040**: diseñar desde el inicio que su entrada es un
**vector de estado fusionado**, independientemente de quién lo produce. Esto permite:
- Arrancar con fusión naive (media ponderada con timestamp) sin Kalman
- Reemplazar esa capa por Kalman cuando esté listo, sin tocar el contrato del plugin
- Evitar reentrenar el modelo y rediseñar features cuando Kalman llegue

La capa de fusión de sensores es un prerequisito natural del clasificador cuando las
fuentes son heterogéneas y temporales. No es opcional — es parte de la arquitectura.

---

## Fuera de scope (explícito)

- ❌ Capa crypto / autenticación — determinista, no hay estado oculto que estimar
- ❌ ZMQ transport layer — lógica de correctitud, no de estimación
- ❌ Cualquier uso pre-FEDER o que interfiera con el backlog activo

---

## Variantes relevantes

| Variante | Uso | Coste computacional |
|----------|-----|---------------------|
| Kalman lineal (KF) | Casos 1, 3, 5, 6 | O(n) — válido en RPi5 |
| Extended Kalman (EKF) | Caso 1 con no-linealidades | Moderado |
| Unscented Kalman (UKF) | Ataques de rampa rápida | Mayor |

---

## Referencias

- R. E. Kalman, "A New Approach to Linear Filtering and Prediction Problems", 1960
- MIT AGC source: https://github.com/chrislgarry/Apollo-11
- Relación directa: ADR-046, ADR-040, BACKLOG-ZMQ-TUNING-001

---

## Nota de seguimiento

> Este item no bloquea nada y no tiene fecha. Volverá cuando aRGus, Suricata, Zeek,
> Wazuh y Neo4j estén integrados — ese es el momento natural en que la señal compuesta
> existe y la investigación tiene suelo real bajo los pies.
> Alonso es el árbitro de si y cuándo entra en roadmap formal.

*Revisado DAY 163 con aportaciones del Consejo (Claude + DeepSeek).*
