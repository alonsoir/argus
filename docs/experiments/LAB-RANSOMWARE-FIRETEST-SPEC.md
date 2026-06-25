# LAB-RANSOMWARE-FIRETEST — Especificación de laboratorio para la validación de detección de ransomware en red

| Campo | Valor |
|---|---|
| **Documento** | Especificación de diseño experimental |
| **Estado** | Diseño cerrado · ejecución pendiente de hardware |
| **Origen** | DAY 195 — primer acto cerrado (desync dirimido), segundo acto especificado |
| **Autor** | Alonso Isidoro Román |
| **Revisión** | Consejo de Sabios |
| **Deudas relacionadas** | `DEBT-RANSOMWARE-FEATURE-SEMANTICS-001`, `DEBT-RANSOMWARE-ML-HEAD-INERT-001` |
| **Método invariante** | "Medir, no votar." Tirar hacia atrás desde el binario. Toda afirmación contra fichero, nunca contra memoria. |

---

## 0. Propósito y alcance

Esta especificación define la infraestructura de laboratorio necesaria para someter el detector de ransomware de aRGus a su **prueba de fuego**: detonar ransomware real en un entorno controlado y aislado, capturar con el propio sniffer de aRGus la secuencia completa de tráfico que genera, y medir qué detecta el pipeline en producción — distinguiendo con instrumentación lo que detecta el **fast path** heurístico de lo que detecta la **cabeza ML** (RandomForest embebido).

Este experimento es el **paso de captura del ACRL** (Adversarial Capture-Retrain Loop) aplicado al dominio que hasta ahora faltaba: ransomware observado *en red*, en el mismo espacio de features que el sensor ve en producción. No es un experimento más; es el que cierra —o refuta— la hipótesis de la cabeza ML inerte abierta en DAY 195.

**Lo que esta prueba decide.** Si la detección de ransomware en aRGus es real y de qué componente proviene. El resultado determina si los modelos fundacionales necesitan reentrenamiento contra ground truth de red (no contra el espacio host de `files/processes_guaranteed.csv`) antes de cualquier despliegue en producción.

**Lo que esta prueba NO es.** No es un experimento de reentrenamiento. Para reentrenar hace falta un corpus grande; para *diagnosticar* basta un puñado de detonaciones bien capturadas. Diagnóstico antes que cura.

---

## 1. Hipótesis registrada (falsable, fechada)

> Se registra **antes** de ejecutar el experimento, deliberadamente. Una predicción firmada con fecha es ciencia; la misma frase dicha tras ver los resultados es sesgo de confirmación. La diferencia entre ambas es la fecha del commit.

**H1 (Alonso, DAY 195):** En la detonación de ransomware real, el **fast path heurístico del sniffer detectará más que la cabeza ML del ml-detector**. El sistema no disparará en todas las acciones del ransomware, pero sí en las suficientes para indicar que algo anómalo está ocurriendo.

**Criterio de confirmación de H1:** en los eventos del canal de ransomware durante la detonación, la nota `final` proviene mayoritariamente del `fast` (`source=DETECTOR_SOURCE_DIVERGENCE`, `final=fast`), con la cabeza ML (`ml`) deprimida y poco discriminante.

**Criterio de refutación de H1:** la cabeza ML (`ml`) produce scores altos y discriminantes de forma consistente y es la que sostiene la nota `final` (`source=ML_PRIORITY`). En ese caso, la hipótesis de la cabeza inerte caería y habría que revisar `SEMANTICS-001`.

**Predicción secundaria a contrastar:** indicio previo (relays NERIS, diciembre 2025) mostró `ml≈0.1454` clavado bajo frente a `fast=0.7000`. Es indicio sostenido por memoria del operador, **no** prueba; este experimento lo eleva a dato capturado o lo refuta.

---

## 2. Separación de dos experimentos ortogonales

El error a evitar desde la lista de la compra: **mezclar dos experimentos que tienen víctimas, objetivos y hardware distintos.**

### E1 — Detección de ransomware (¿detecta el modelo?)
Mide si aRGus, sobre tráfico de ransomware real, detecta, y desde qué componente. Las víctimas que ejecutan el malware son **x86_64**, porque las familias reales con huella de red documentada son binarios x86. Una Raspberry Pi ARM **no ejecuta** ese binario y por tanto **no sirve como cobaya de infección**.

### E2 — Port ARM64 / sensor en hardware modesto (¿corre aRGus en bajo consumo?)
Mide si aRGus compila y corre sobre ARM64 (Raspberry Pi) como sniffer pasivo. Es un caso de uso real y **vendible**: un NDR open source que corre en hardware barato de bajo consumo es exactamente lo que un hospital pequeño o un ayuntamiento puede permitirse desplegar. Es argumento de paper, no solo de laboratorio.

**Por qué no se mezclan:** E1 mide *si el modelo detecta*; E2 mide *si aRGus corre en hardware modesto*. Confundirlos lleva a pedir el hardware equivocado y a no poder atribuir un fallo a su causa. La Raspberry Pi pertenece a E2 (sensor), nunca a E1 (víctima).

> **Consecuencia operativa:** E2 (port ARM64 sobre tráfico **benigno**) no necesita malware y se puede ejecutar **ya**, sin esperar al hardware de laboratorio. Ver §9.

---

## 3. Arquitectura de laboratorio — tres capas

```
   ┌─────────────────────────────────────────────────────────┐
   │            RED DE LABORATORIO AISLADA (air-gapped)        │
   │                                                          │
   │   ┌──────────────┐   ┌──────────────┐                    │
   │   │  VÍCTIMA x86 │   │  VÍCTIMA x86 │   (sacrificables,   │
   │   │  (detona)    │   │  (lateral)   │    snapshot+restore)│
   │   └──────┬───────┘   └──────┬───────┘                    │
   │          │                  │                            │
   │       ┌──┴──────────────────┴──┐                         │
   │       │  SWITCH GESTIONADO      │  ← port mirroring / TAP │
   │       │  (puerto espejo)        │                         │
   │       └───────────┬─────────────┘                         │
   │                   │ (copia pasiva del tráfico)            │
   │            ┌──────┴───────┐                               │
   │            │   SENSOR     │  aRGus (x86 o Pi ARM64)       │
   │            │   aRGus      │  NO se infecta. Solo escucha. │
   │            └──────────────┘                               │
   │                                                          │
   │   SIN gateway al exterior · SIN carpetas compartidas      │
   │   con el anfitrión · anfitrión fuera del segmento         │
   └─────────────────────────────────────────────────────────┘
```

### 3.1 Capa víctima — x86_64
Donde detona el malware, donde cifra ficheros, desde donde intenta moverse lateral. Son **sacrificables** y se restauran de snapshot tras cada ejecución. Mínimo dos nodos para que el movimiento lateral tenga destino y genere tráfico inter-host observable (que es justo la huella de red que interesa). Es la capa que concentra el aislamiento serio (§4).

### 3.2 Capa sensor — aRGus
Donde corre aRGus escuchando. **No se infecta:** ve tráfico, no ejecuta payload. Puede ser:
- una **Raspberry Pi (ARM64)** → valida E2 de paso, o
- otra **x86 pequeña** → más simple, sin port, si E2 se desacopla.

El sensor recibe una copia pasiva del tráfico de las víctimas; nunca está en la ruta de datos.

### 3.3 Capa de captura — tap / mirror
Cómo el sensor ve el tráfico de las víctimas sin estar en la ruta. Un **switch gestionado barato con port mirroring** o un **TAP de red**. Es la pieza que se olvida pedir y que, sin ella, bloquea todo el montaje. Sin captura no hay experimento.

---

## 4. Aislamiento y contención de malware activo

Estos requisitos **no son negociables**. No es la VM aislada genérica de un laboratorio de pruebas; es contención de malware vivo que cifra de verdad y busca propagarse.

- **Sin ruta al exterior.** Red virtual/física sin gateway a Internet ni a la red doméstica. El C&C no debe poder alcanzar a su operador real, y el ransomware no debe poder alcanzar nada que importe.
- **Anfitrión fuera del segmento.** El portátil de trabajo (y cualquier máquina personal) **no** forma parte de la red de laboratorio. Ninguna interfaz compartida.
- **Sin carpetas compartidas** (`vboxsf`, montajes, unidades de red) entre víctimas y anfitrión. El ransomware cifra lo que alcanza; no debe alcanzar nada tuyo.
- **Snapshots antes de cada detonación** y restauración completa después. Estado limpio garantizado entre ejecuciones.
- **Tensión explícita y asumida:** cuanto más se deja al malware comportarse (cifrar, moverse lateral) para capturar tráfico realista, más estricto debe ser el sellado. Las dos cosas a la vez.

> **Nota de alcance.** El objetivo del experimento es *observar* el comportamiento de red natural del malware dentro de la contención, no potenciarlo. La disciplina aquí es la misma que aplica el proyecto a la procedencia de datos, ahora aplicada a binarios peligrosos.

---

## 5. Procedencia y cadena de custodia de las muestras

Para un proyecto con financiación FEDER y destino hospitalario, la cadena de custodia de las muestras **no es burocracia: es lo que separa "experimento reproducible" de "el investigador manejó malware sin registro".**

Por cada muestra detonada se registra:

| Campo | Detalle |
|---|---|
| **Hash** | SHA-256 del binario exacto detonado |
| **Fuente** | Repositorio académico/forense de procedencia |
| **Fecha** | De obtención y de detonación |
| **Familia** | Identificación de la familia, si se conoce |
| **Entorno** | Snapshot, topología, versión de aRGus usada |
| **Resultado** | Captura asociada (PCAP) y log DUAL-SCORE asociado |

Las muestras se obtienen exclusivamente de **repositorios de muestras con procedencia documentada**, en el marco de investigación de seguridad defensiva. El manejo se ajusta a las normas éticas y legales aplicables a la investigación con malware.

---

## 6. Protocolo de ejecución (cuando haya hardware)

1. **Snapshot** de todas las víctimas en estado limpio.
2. **aRGus en marcha** en el sensor, capturando, con instrumentación DUAL-SCORE activa (§7).
3. **Detonar** una muestra en una víctima. Registrar hash, hora de inicio.
4. **Dejar comportarse** dentro de la contención: cifrado, intento de movimiento lateral hacia la segunda víctima.
5. **Capturar** todo el tráfico (PCAP crudo) en paralelo al log de aRGus.
6. **Registrar** la corrida DUAL-SCORE completa del canal de ransomware.
7. **Etiquetar** la captura con la metadata de §5.
8. **Restaurar** snapshots. Estado limpio para la siguiente.
9. **Repetir** con varias familias/muestras para no concluir sobre una sola.

---

## 7. Métricas e instrumentación

La instrumentación clave ya existe en el pipeline: los logs `DUAL-SCORE`. Por cada evento del canal de ransomware se registra `fast`, `ml`, `final`, `source` y `divergencia`. La medición que dirime H1 sale de ahí, sin reentrenar nada:

- **¿De qué componente viene `final`?** `source=DETECTOR_SOURCE_DIVERGENCE` con `final=fast` (heurístico) vs `source=ML_PRIORITY` (cabeza ML).
- **¿Dónde se distribuye `ml`?** Clavado bajo (~0.14, hipótesis inerte) vs alto y discriminante.
- **¿En qué acciones dispara y en cuáles no?** Cifrado local vs movimiento lateral vs C&C.
- **Tasa de divergencia** sobre el total de eventos del canal.

Salida del experimento: "N eventos, X% `source=DIVERGENCE`, distribución de `ml`", que reemplaza el actual "lo recuerdo bien" por dato capturado.

---

## 8. Lista de hardware — separada por función

> La topología real no es "Raspberry Pi y x86 pequeños" como bloque. Es esto:

| Función | Hardware | Cantidad mínima | Se infecta | Notas |
|---|---|---|---|---|
| **Víctima** | x86_64 pequeño (mini-PC / NUC-like) | 2 | **Sí** (sacrificable) | Detonación + destino de lateral. Snapshot+restore. |
| **Sensor** | Raspberry Pi (ARM64) **o** x86 pequeña | 1 | **No** | Pi valida E2 de paso; x86 más simple. |
| **Captura** | Switch gestionado con port mirroring **o** TAP de red | 1 | No | Pieza crítica. Sin esto no hay experimento. |
| **(E2 aparte)** | Raspberry Pi para port ARM64 | 1 | No | Puede solaparse con el sensor. Trabajo ejecutable ya (§9). |

---

## 9. Trabajo ejecutable AHORA (sin hardware peligroso)

Mientras llega el equipo de laboratorio, avanza lo que **no depende del malware**:

- **Port ARM64 sobre tráfico benigno (E2).** Compilar aRGus limpio a ARM64, hacerlo correr en una Raspberry Pi, validar que el pipeline `sniffer → detector` funciona sobre tráfico benigno en ARM. Es un hito completo, desacoplado de E1, que cuando llegue el resto del laboratorio deja el sensor ya probado y solo pendiente de detonar.
- **Pipeline faltante (circuito completo).** Adapters, Landing Zones, grafo, herramienta MITRE — el trabajo decidido como prioridad en DAY 195. El microscopio antes que la muestra.
- **Documentación.** Esta spec en repo y en la sección de metodología experimental del paper.

Esto respeta la decisión de DAY 195: terminar el circuito asumiendo la inferencia ML rota/incompleta, y reentrenar los fundacionales **después**, contra ground truth de circuito completo —no contra eval host— y con ransomware **real en red**, no más sintético host (si no, el segundo experimento MITRE choca con la misma pared que el primero).

---

## 10. Dependencias, calendario y marco honesto

- **Hitos:** go/no-go 1 de agosto 2026 · final 22 de septiembre 2026.
- **Apoyo de hardware:** posible vía Dr. Andrés Caro Lindo. Se asume **no disponible en verano** (vacaciones). El plan no depende de que esté.
- **Ritmo realista:** proyecto de una sola persona con responsabilidades personales en paralelo. El hardware llega "cuando llega". Eso es el ritmo de un proyecto individual con vida alrededor, **no un retraso imputable al plan ni al investigador**.
- **Marco para el paper:** si en septiembre la prueba de fuego no se ha ejecutado por falta de hardware, el paper sostiene perfectamente *"diseño de laboratorio especificado, ejecución pendiente de hardware"*. Es honesto y es lo que hay. Un límite material no se convierte en deuda personal.

---

## 11. Resultado esperado para el paper

Pase lo que pase con la ejecución, esta spec produce un activo publicable:

- Si se ejecuta y confirma H1 → caso concreto y trazado de **domain mismatch host↔red** en modelos fundacionales, capturado tirando hacia atrás desde el binario. Es la misma tesis del *synthetic-data discovery*, instanciada y medida.
- Si se ejecuta y refuta H1 → la cabeza ML funciona mejor de lo previsto; resultado igualmente valioso y honesto.
- Si no llega el hardware → diseño experimental cerrado y reproducible como contribución metodológica, ejecución señalada como trabajo futuro.

La fortaleza del trabajo no está en no tener componentes flojos. Está en nombrarlos con precisión y diseñar el experimento que los mide. Eso es lo que vuelve defendible —y no fanfarrón— el objetivo de fondo: un conjunto de sensores en tiempo real open source, documentado con una honestidad que las siguientes generaciones puedan auditar.