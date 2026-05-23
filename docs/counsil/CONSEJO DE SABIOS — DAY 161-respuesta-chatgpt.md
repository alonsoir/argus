## Consejo de Sabios — DAY 161

El salto de calidad de DAY 161 es importante por una razón concreta: empezáis a cerrar deuda estructural que evita “falsos verdes”. El pipeline ya no solo ejecuta cosas; empieza a demostrar propiedades del sistema. Eso cambia mucho la madurez del proyecto [aRGus repository](https://github.com/alonsoir/argus?utm_source=chatgpt.com)

---

# Q1 — Wire Protocol Test

## Recomendación del Consejo

Sí: debería existir un segundo test E2E que pase por `CryptoTransport` completo.

Pero el diseño correcto es:

### Nivel 1 — Test de protocolo binario puro

Ya lo tenéis:

* framing
* endianess
* longitud
* compresión LZ4
* serialización exacta

Ese test es crítico y debe permanecer aislado.

Porque si mezcláis cifrado:

* perdéis capacidad de aislar errores
* aumentan falsos negativos
* debugging empeora

El DAY 98 era precisamente un bug de framing/protocolo.

---

### Nivel 2 — Test integrado `CryptoTransport`

Debe validar:

* compress → encrypt → transmit → decrypt → decompress
* roundtrip exacto
* payloads vacíos
* payloads grandes
* payloads truncados
* corruption handling
* invalid key rejection

Pero ese test NO debe reemplazar el wire protocol test puro.

---

## Arquitectura recomendada

### Correcto

```text
[Payload]
   ↓
[Serialize]
   ↓
[LZ4]
   ↓
[Wire Protocol]
   ↓
[Encryption]
   ↓
[Socket]
```

Con tests separados:

| Layer           | Test              |
| --------------- | ----------------- |
| Wire protocol   | framing puro      |
| CryptoTransport | pipeline completo |
| E2E             | nodos reales      |

---

## Veredicto

* El test actual es correcto y necesario
* NO es suficiente por sí solo
* Añadid un integration test de `CryptoTransport`
* No mezcléis ambos conceptos

---

# Q2 — Jenkinsfile.dev vs Jenkinsfile.prod

## El diseño actual es correcto

Para la fase actual:

* Mac local
* Vagrant
* Jenkins experimental
* fundador único
* sin runners distribuidos

`agent any` es exactamente lo correcto.

Mover ahora a labels rígidos os complicaría:

* bootstrap
* portabilidad
* debugging
* onboarding futuro

---

## Cuándo cambiar a `argus-server`

El momento correcto es cuando aparezca al menos UNA de estas condiciones:

### 1. Hardware persistente dedicado

Ejemplo:

* servidor UEx
* mini rack
* N100 CI host
* runner permanente

---

### 2. Necesidad de reproducibilidad fuerte

Cuando:

* mismas librerías
* mismas toolchains
* mismo kernel
* mismo Vault
* mismos artefactos

empiecen a ser críticos.

---

### 3. CI distribuido real

Cuando:

* ARM runners
* x86 runners
* build matrices
* hardware-specific tests

formen parte del pipeline.

---

## Consejo importante

Mantendría:

```groovy
Jenkinsfile.dev  -> agent any
Jenkinsfile.prod -> label argus-server
```

Mucho tiempo.

Porque:

* dev = elasticidad
* prod = reproducibilidad

Separarlos fue una muy buena decisión arquitectónica.

---

# Q3 — Jinja2 pipeline y perfiles hardware

## Recomendación fuerte del Consejo

NO calcular parámetros “óptimos” automáticamente en runtime.

Eso parece elegante… hasta que rompe producción.

---

## Problema del autotuning runtime

El hardware no describe:

* calidad NIC
* jitter
* IRQ contention
* temperatura
* throttling
* tipo de tráfico
* latencia disco
* contenedores vecinos

Dos RPi5 iguales pueden comportarse distinto.

---

## Diseño recomendado

### Perfiles fijos y auditables

```text
naive
edge-low
edge-medium
edge-high
feder-server
```

Con:

* valores explícitos
* versionados
* reproducibles
* comparables

---

## Lo correcto

### Runtime detection SOLO selecciona perfil

Ejemplo:

```text
Detectado:
- 16 GB RAM
- 4 cores
- NVMe

→ perfil: edge-high
```

Pero:

* NO recalcula buffers
* NO recalcula threads
* NO recalcula thresholds

---

## Excepción válida

Puede existir:

```text
profile + bounded adaptive layer
```

Ejemplo:

* ring buffer dinámico ±15%
* workers limitados
* backpressure controlado

Pero siempre:

* con límites
* deterministic
* observable

Nunca “IA mágica” de autotuning.

---

## Veredicto

### Correcto

* templates sagrados
* generated ignorados
* perfiles fijos
* runtime → selección de perfil

### Incorrecto

* recomputar configs enteras dinámicamente

---

# Q4 — test-e2e-live y tráfico sintético

## El Consejo considera que:

El test debe inyectar tráfico sintético mínimo.

Porque el objetivo del test NO es:

> “ver si internet existe”

El objetivo es:

> validar el pipeline E2E.

---

## Problema del tráfico orgánico

Dependéis de:

* NAT
* Vagrant
* MacOS bridges
* timing
* DNS cache
* ARP cache
* estado de red

Eso convierte el test en:

* flaky
* no determinista
* no reproducible

Muy peligroso para CI.

---

## Diseño correcto

### test-e2e-live

Debe:

1. snapshot
2. generar tráfico mínimo
3. esperar
4. validar delta

---

## Tráfico recomendado

Muy simple:

```bash
ping -c 1 1.1.1.1
```

o:

```bash
curl http://example.com
```

o incluso:

```bash
nc
```

No necesitáis tráfico “realista”.
Necesitáis:

* determinismo
* observabilidad
* repetibilidad

---

## Recomendación importante

Separad conceptos:

| Test          | Objetivo              |
| ------------- | --------------------- |
| synthetic-e2e | validar pipeline      |
| passive-live  | observar entorno real |

No mezclarlos.

---

# Q5 — Prioridad DAY 162

## Prioridad recomendada:

# B) DEBT-ARGUSPP-NTP-001

---

## Razón estratégica

Ahora mismo tenéis:

* múltiples motores
* enriquecimiento
* correlación futura
* pipelines distribuidos
* replay potencial
* evidencia temporal

Sin sincronización temporal sólida:
todo eso se degrada.

---

## Por qué NTP antes que Suricata

Suricata puede dar:

* primeras señales externas
* valor visible inmediato

Pero sin tiempo coherente:

* correlación multi-engine
* causalidad
* reconstrucción
* forensic graphs
* attack chains

se vuelven ambiguos.

---

## El problema es muy serio

Un drift de:

```text
300-500 ms
```

ya puede romper:

* correlación lateral
* secuencias
* replay
* joins temporales

---

## NTP es infraestructura fundacional

No es “feature visible”.
Es:

* consistencia causal
* orden temporal
* confianza forense

---

## Orden recomendado

### DAY 162

B) NTP

### DAY 163-164

A) Suricata

### Después

D) libcrypto_provider extraction

### Más adelante

C) EXTENDED_AUTONOMY

---

## Sobre EXTENDED_AUTONOMY

Todavía es pronto.

Autonomía sin:

* correlación madura
* señales externas
* timing sólido
* observabilidad completa

puede crear:

* decisiones incorrectas
* loops
* autoaislamiento
* falsas expulsiones

Primero:

* percepción
* coherencia temporal
* señales
* correlación

Luego:

* autonomía extendida

---

# Evaluación global DAY 161

DAY 161 parece menos “espectacular” que otros días, pero técnicamente es uno de los más importantes.

Porque:

* endurece CI
* reduce flakiness
* separa entornos
* protege invariantes
* prepara reproducibilidad

Eso suele ser lo que diferencia:

* proyectos interesantes
  de
* sistemas operables a largo plazo.
