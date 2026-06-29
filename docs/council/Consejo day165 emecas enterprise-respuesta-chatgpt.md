# Consejo de Sabios — Deliberación DAY 165

## Validación Enterprise: diseño de EMECAS++

El trabajo realizado entre DAY 161–165 muestra una transición clara desde “crypto estático” a un sistema enterprise con rotación coordinada y hot-reload real. Arquitectónicamente, las decisiones clave parecen correctas:

* Separación OSS / Enterprise mediante `CryptoProvider`
* Eliminación de persistencia del `vendor.key`
* Introducción de `epoch_id` explícito en wire protocol
* RCU para swap atómico de claves
* etcd como coordinador distribuido
* Validación progresiva desde unit → integration → e2e

La secuencia de fases está bien escalonada. Especialmente relevante: FASE 3 resolvió correctamente el problema fundamental de selección de clave antes de descifrado mediante `epoch_id` en cabecera. Sin eso, el sistema no podía escalar a rotación multi-epoch robusta.

---

# Pregunta 1 — Arquitectura del protocolo

## Recomendación del Consejo: **(C) Targets anidados**

### `make emecas` + `make emecas++`

Propuesta recomendada:

```bash
make emecas        # OSS baseline
make emecas++      # OSS + enterprise
```

Donde internamente:

```make
emecas:
    ...

emecas++: emecas
    ...
```

## Motivos

### 1. Preserva estabilidad histórica

El target actual no cambia comportamiento. Muy importante para:

* scripts existentes
* reproducibilidad paper/arXiv
* contributors OSS
* CI futura

### 2. Filosofía incremental correcta

Enterprise debe demostrar que:

* no rompe OSS
* añade capacidades encima del baseline

La relación conceptual correcta es:

```text
Enterprise ⊃ OSS
```

No son dos productos separados.

### 3. Menor deuda cognitiva

`emecas++` comunica inmediatamente:

* “más estricto”
* “superset”
* “full validation”

Mucho más alineado con la cultura del proyecto que `EMECAS-E`.

### 4. Jenkins futuro más limpio

Luego Jenkins puede mapear fácilmente:

```text
Stage 1 -> emecas
Stage 2 -> emecas++
```

sin duplicar lógica.

---

# Pregunta 2 — Vault dev como gate suficiente

## Recomendación del Consejo: **Sí, Vault dev es suficiente para merge gate**

Con una condición:

> Debe existir al menos un test explícito de pérdida/reconexión del provider.

No hace falta HA real aún.

---

## Motivos

### Lo que el gate debe validar ahora

El objetivo del merge gate NO es validar:

* resiliencia operativa real
* clustering Vault
* failover HA
* TLS productivo

El objetivo del gate es validar:

```text
La arquitectura crypto enterprise funciona end-to-end.
```

Y eso ya está prácticamente cubierto.

---

## Lo importante realmente

El riesgo arquitectónico hoy no es:

* Vault HA

El riesgo real es:

* desincronización de epochs
* race conditions en hot reload
* selección incorrecta de clave
* continuidad del pipeline durante rotación

Eso ya es precisamente lo que estáis atacando.

---

## Recomendación adicional

Añadir un test sencillo:

```text
Vault unavailable temporarily
→ provider retries
→ pipeline survives
```

Sin HA.
Sin cluster.
Sin TLS.

Solo reconexión básica.

Eso aporta muchísimo valor por muy poco coste.

---

# Pregunta 3 — Live epoch rotation en EMECAS

## Recomendación del Consejo: **(B) Sí debe existir live rotation real**

Esto es importante.

---

## Motivo central

`FakeEtcdServer` valida lógica.

Pero NO valida:

```text
coordinación temporal real
+
threads reales
+
network timing
+
hot reload concurrente
+
pipeline vivo
```

Y precisamente ahí es donde suelen vivir los bugs más peligrosos.

---

## La cadena crítica enterprise es:

```text
Vault
  ↓
etcd epoch update
  ↓
watch propagation
  ↓
CryptoEpochCoordinator
  ↓
CryptoProviderHandle swap
  ↓
wire header update
  ↓
firewall decrypt selection
  ↓
continuidad del pipeline
```

Ese camino completo debe ejecutarse al menos una vez en el gate.

---

## Recomendación pragmática

No hacerlo pesado.

Un único escenario basta:

```text
epoch 1
→ procesar tráfico
→ rotación
→ epoch 2
→ seguir procesando
→ zero drops
→ zero crypto_errors
```

Eso da una confianza enorme.

---

# Pregunta 4 — Test negativo (`epoch_id` inválido)

## Recomendación del Consejo: **Sí, requisito de merge**

Este test no debería diferirse.

---

## Motivo

El sistema enterprise introduce:

```text
selección dinámica de claves basada en epoch_id
```

Eso convierte el rechazo correcto en parte del contrato de seguridad.

Sin test negativo, no está validado:

* rechazo seguro
* aislamiento entre epochs
* continuidad ante mensajes corruptos
* robustez ante replay/desync

---

## Este test detecta bugs críticos

Especialmente:

* fallback accidental a clave activa
* decrypt con epoch incorrecto
* crashes por lookup inválido
* corrupción de métricas

---

## Debe validar explícitamente

```text
invalid epoch_id
→ reject
→ crypto_errors += 1
→ no crash
→ pipeline alive
```

Eso es gate-level.

---

# Pregunta 5 — Gate de Jenkins

## Recomendación del Consejo: **Merge aceptable sin Jenkins**

Condición:

```text
BACKLOG-CI-ENTERPRISE-001 = P1 bloqueante post-merge
```

---

## Motivos

Jenkins no añade validación arquitectónica nueva.

Solo automatiza ejecución.

La arquitectura enterprise ya está validándose mediante:

* tests
* Vagrant reproducible
* EMECAS++
* pipeline e2e

---

## Lo importante ahora

No bloquear innovación arquitectónica por infraestructura CI todavía incompleta.

Eso sería invertir prioridades.

---

## Pero el Consejo recomienda

Antes de release pública estable:

* Jenkins obligatorio
* `emecas++` obligatorio en CI nightly
* artifacts y logs persistentes

---

# Pregunta 6 — Naming y documentación

## Recomendación del Consejo: **(B) EMECAS++**

---

## Motivos

### 1. Coherencia cultural del proyecto

El nombre ya existe informalmente.
La comunidad probablemente ya lo entiende.

Forzar otro naming añade fricción innecesaria.

---

### 2. Refleja evolución natural

```text
EMECAS      -> baseline reproducible
EMECAS++    -> baseline + enterprise guarantees
```

Muy claro conceptualmente.

---

### 3. Bueno para paper

En arXiv queda elegante:

```text
EMECAS++
(Extended Enterprise Minimal Executable Comparable Assurance Suite)
```

Incluso podéis redefinir el acrónimo formalmente más adelante si queréis.

---

# Recomendación final consolidada del Consejo

## Estructura recomendada

```bash
make emecas
make emecas++
```

Donde `emecas++`:

* ejecuta OSS primero
* luego enterprise

---

## Gate mínimo recomendado para merge

### Obligatorio

* OSS green
* Vault dev green
* Live rotation green
* Negative epoch test green
* Pipeline continuity green
* Wire header epoch validation green

### No obligatorio aún

* Vault HA
* TLS real
* Jenkins
* multi-node infra
* failover cluster

---

# Evaluación arquitectónica general

La decisión de:

* introducir `epoch_id`
* desacoplar provider
* usar RCU
* eliminar persistencia del keypair

parece correcta y alineada con una arquitectura enterprise real.

Especialmente acertado:

* no intentar HA prematuramente
* separar funcionalidad de operatividad
* validar primero invariantes criptográficas y de continuidad

El sistema ya no parece un “modo OSS con extras”, sino una bifurcación enterprise razonablemente seria del pipeline crypto.

FASE 3 probablemente fue el verdadero punto de no retorno arquitectónico del diseño.
