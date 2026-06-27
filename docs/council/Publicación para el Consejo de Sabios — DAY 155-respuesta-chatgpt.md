El Consejo considera que DAY 155 marca una transición importante: la autonomía ya no es “una idea arquitectónica”, sino un flujo operacional real con propagación de estado, enforcement y reconciliación. La decisión de pasar a cadena dedicada `argus-autonomy` fue especialmente correcta. Evita convertir autonomía en un side-effect destructivo del firewall y la convierte en una política estructurada.

También se observa una buena madurez en:

* fail-fast configuracional
* separación publisher/subscriber
* reconciliación lenta como safety net
* ZMQ tuning temprano antes de benchmarks reales

Las respuestas:

---

# Q1 — ¿Qué proceso debe poseer `CryptoAutonomyStateMachine`?

## Recomendación del Consejo: Opción A

### `etcd-server` debe ser el propietario inicial

No porque etcd “sea crypto”, sino porque:

```text id="91pc7v"
La autonomía es consecuencia del estado de coordinación/disponibilidad
```

y el proceso que primero conoce:

* pérdida de quorum
* degradación Vault
* expiración lease
* imposibilidad de refresh
* divergencia de estado

...es precisamente el componente coordinador.

---

## Por qué NO las otras opciones

### Opción C — `sniffer`

El sniffer es dataplane.

No debería decidir estados globales de autonomía criptográfica.

Acabaríais mezclando:

* captura
* observabilidad
* coordinación
* control-plane

Eso degrada aislamiento arquitectónico.

---

### Opción D — múltiples SM distribuidas

Muy peligrosa.

Terminas con:

```text id="z2zv43"
split-brain autonomy
```

Ejemplo:

* componente A → AUTONOMOUS
* componente B → NORMAL
* firewall recibe ambos

Y ahora:

* ¿último writer gana?
* ¿mayoría?
* ¿prioridades?

Habéis creado consenso distribuido accidental.

Evitar.

---

### Opción B — daemon crypto dedicado

Arquitectónicamente es probablemente el destino FINAL correcto.

Pero no para DAY 156.

Ahora mismo añadiría:

* lifecycle nuevo
* systemd nuevo
* health nuevo
* observabilidad nueva
* boot ordering nuevo
* más EMECAS surface

El Consejo cree que es premature abstraction.

---

# Recomendación concreta

## DAY 156

### Propietario:

```text id="ynogop"
etcd-server
```

### Responsabilidad:

* instanciar `CryptoAutonomyStateMachine`
* evaluar salud Vault/leases/cache
* emitir transición
* publicar eventos

---

## Evolución futura (post-FEDER)

Más adelante sí tiene sentido:

```text id="ib1p8j"
argus-crypto-daemon
```

cuando aparezcan:

* múltiples fuentes crypto
* HSM
* rotation orchestration
* policy engines
* signing services

Pero aún no.

---

# Q2 — ipc:// vs tcp://

## Recomendación fuerte del Consejo

### Mantener `ipc://`

```text id="qz3e7q"
ipc:///run/argus/autonomy.sock
```

como arquitectura oficial del firewall autonomy plane.

---

# Razón profunda

El firewall autonomy plane debe ser:

```text id="wkttj4"
local
trusted
determinista
fail-contained
```

No distribuido por red.

---

## Si el firewall depende de TCP…

Entonces:

* latencia red afecta enforcement
* particiones afectan autonomía
* TLS añade complejidad
* reconnect storms aparecen
* el autonomy plane depende de networking

Y eso derrota parte del propósito.

---

# Recomendación arquitectónica

## Regla del Consejo

### El firewall SIEMPRE local al enforcement node

Es decir:

```text id="1qutmx"
crypto owner
+
firewall reactor
+
iptables/nftables
```

deben coexistir en el mismo host.

---

# ¿Qué pasa con el servidor central?

El servidor central puede:

* observar
* monitorizar
* agregar eventos

Pero NO debe ser el que aplica autonomía firewall de edge nodes.

---

# Entonces ¿cuándo usar tcp://?

Solo para:

* telemetría
* observabilidad
* agregación
* métricas

NO para enforcement runtime crítico.

---

# Q3 — reconcile_interval_sec

## Sí: debe ser configurable

El Consejo considera correcto:

```json id="l1kz4g"
firewall.json["autonomy"]["reconcile_interval_sec"]
```

porque hospitales distintos tienen:

* tolerancias distintas
* redes distintas
* operaciones distintas

---

# Pero más importante:

## El reconciliador NO debe consultar Vault

Esto es importantísimo.

Si el reconciliador consulta Vault:

* reintroduces dependencia externa
* añades latencia
* puedes bloquear reconciliación
* mezclas control-plane y recovery-plane

---

# Qué debe hacer realmente

## Re-aplicar estado local conocido

Modelo:

```text id="vl0v3q"
Último estado válido recibido
+
verificación local de enforcement
```

NO:

* reevaluación distribuida
* reconsenso
* nueva decisión

---

# Reconciliación correcta

El reconciliador debería:

* verificar existencia cadena
* verificar reglas
* verificar ordering
* re-aplicar si drift detectado

Es decir:

```text id="dz8dku"
desired state reconciliation
```

no:

```text id="y0qntv"
distributed state recomputation
```

Eso es una diferencia enorme.

---

# Intervalo recomendado

## 90s es razonable inicialmente

Porque:

* eventos son mecanismo principal
* reconciliación es safety net
* firewall drift no ocurre constantemente

---

## Posible evolución

Más adelante:

* exponential backoff
* jitter
* drift-triggered reconciliation

Pero no ahora.

---

# Q4 — `enterprise/` vs `plugins/enterprise/`

## Recomendación fuerte:

### `plugins/enterprise/`

No `enterprise/`.

---

# Razón arquitectónica

Porque Vault NO es “core”.

Es una integración concreta de infraestructura.

La diferencia conceptual es importante:

```text id="d5zt8k"
common/ = runtime core abstractions
plugins/ = infrastructure integrations
```

---

# Estructura recomendada

```text id="y64jdb"
common/
    crypto_autonomy.*
    autonomy_publisher.*
    interfaces/
        icrypto_provider.h
        ivault_transport.h

plugins/
    enterprise/
        vault/
            vault_client.*
            vault_provider.*
            hkdf_crypto_deriver.*
```

---

# Beneficios

## 1. Build isolation

Más adelante:

```cmake id="8p7d8n"
-DBUILD_ENTERPRISE=OFF
```

será trivial.

---

## 2. Open-source clarity

El core queda claramente separado de:

* enterprise connectors
* cloud integrations
* proprietary adapters

---

## 3. Dependency hygiene

Evita contaminar `common/` con:

* Vault SDK
* etcd specifics
* enterprise transport logic

---

# CMake implication importante

El Consejo recomienda empezar YA a preparar:

```cmake id="cdj42k"
add_subdirectory(plugins)
```

aunque aún no mováis nada.

Porque después:

* install()
* include dirs
* exported targets
* pkg-config
* transitive deps

se vuelven mucho más difíciles de reorganizar.

---

# Q5 — Benchmarks sintéticos en VirtualBox

## Sí. Absolutamente sí.

Pero:

* etiquetados explícitamente como sintéticos
* jamás presentados como throughput real

---

# Por qué son valiosos igualmente

Porque permiten detectar:

## 1. Curvas relativas

Aunque los números absolutos sean falsos, las tendencias sí importan:

```text id="nrbh9q"
HWM 1000 vs 10000
1 subscriber vs 4
burst vs steady-state
```

---

## 2. Regressions

VirtualBox sirve muy bien para detectar:

```text id="2kq78f"
DAY 155 -> 40k msg/s
DAY 160 -> 12k msg/s
```

Eso es oro.

---

## 3. Pathological behavior

Detectar:

* queue explosion
* reconnect storms
* allocator pressure
* unbounded latency
* drops

sí es posible virtualizado.

---

# Lo que NO debéis hacer

No publicar:

```text id="86vnjw"
aRGus procesa X Gbps
```

basado en VirtualBox.

---

# Recomendación formal del Consejo

## Dos categorías separadas

### 1. Synthetic CI benchmarks

VirtualBox/QEMU

Objetivo:

* regresiones
* tendencias
* tuning

---

### 2. FEDER hardware benchmarks

Bare metal

Objetivo:

* cifras publicables
* paper
* capacidad real
* sizing

---

# Observación final del Consejo

La arquitectura está convergiendo hacia algo importante:

```text id="nuxbrl"
autonomous edge security runtime
```

No simplemente “un IDS/NDR”.

Y eso cambia la filosofía de diseño.

A partir de este punto:

* reconciliación
* ownership único
* deterministic enforcement
* local-first autonomy
* explicit state propagation

son más importantes que añadir detecciones nuevas.

Eso suele ser señal de que el sistema empieza a madurar de verdad.
