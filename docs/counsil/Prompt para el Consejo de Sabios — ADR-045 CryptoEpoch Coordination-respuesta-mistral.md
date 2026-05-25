**Prompt mejorado para el Consejo de Sabios — ADR-045 CryptoEpoch Coordination (v2):**

---

### **📌 Objetivo del Consejo**
**Decisión binaria por pregunta** (SÍ/NO + justificación técnica) sobre la propuesta de coordinación criptográfica para **aRGus NDR (arXiv:2604.04952)**. El PI arbitrará en caso de empate. **Tiempo límite: 48h desde recepción**.

---

---

### **🔧 Contexto Técnico (Inmutable)**
| **Ámbito**               | **Detalle**                                                                                     |
|--------------------------|-------------------------------------------------------------------------------------------------|
| **Sistema**              | aRGus NDR (C++20), infraestructura crítica, 6 componentes (*sniffer*, *firewall*, *logger*, *analyzer*, *orquestador*, *vault-agent*). |
| **Comunicaciones**       | ZeroMQ (PUB/SUB, REQ/REP) con **LZ4 + LE uint32_t (tamaño payload)**. Sin *epoch_id* en header actual. |
| **Material criptográfico** | Derivado de *seed* compartido (HKDF-SHA256, **ADR-013**). Provider: `ICryptoProvider` (interface) → `SeedFileProvider` (community) / `VaultProvider` (enterprise, HashiCorp Vault). |
| **FASE 1 (✅ Cerrada)**   | `CryptoProviderHandle`: wrapper **RCU** con `std::atomic<std::shared_ptr<ICryptoProvider>>`. Permite *swap* atómico del provider **sin downtime** (CAS + `std::memory_order_seq_cst`). |
| **Autonomy State Machine** | Estados actuales: `NOMINAL`, `DEGRADED`, `CRITICAL`. **No existe `EPOCH_TRANSITION`**. *Autonomy trigger*: si un componente detecta fallo en otro (ej: timeout ZMQ), salta a `DEGRADED` y usa *fallback* (seed anterior). |
| **Entorno**              | **Mismo nodo físico** (bare-metal, no contenedores), latencia inter-proceso <1ms. etcd-server **co-ubicado** (mismo nodo). |
| **Requisitos no funcionales** | **RTO < 5s**, **RPO = 0** (no pérdida de mensajes ZMQ durante rotación). **Disponibilidad objetivo: 99.99%**. |

---

---

### **⚠️ Problema (FASE 2)**
**Split-brain criptográfico**:
Si *sniffer* rota a *época N+1* pero *firewall* sigue en *época N* → **claves incompatibles** → canal ZMQ **muerto** (descartan mensajes por *MAC verification failure*).
**Impacto**: Pérdida de telemetría crítica (ej: logs de intrusión) hasta detección manual (TTD actual: ~2min).

---

---

### **📜 Propuesta ADR-045 v1 (Bajo Revisión)**
#### **1. Entidad Coordinadora**
- **etcd-server** (v3.5+) publica el estado de *CryptoEpoch* en:
  ```plaintext
  /argus/crypto/epoch → { "epoch_id": uint64, "seed_hash": hex(SHA256(seed)), "not_before": ISO8601, "grace_period_s": uint32 }
  ```
    - *Seed* **nunca** se almacena en etcd (solo su hash para verificación).
    - etcd **soporta watchers atómicos** (via `etcd::v3::Watch`).

#### **2. Flujo de Rotación**
1. **Vault** genera nuevo *seed* → `vault-agent` escribe en etcd:
    - `epoch_id = N+1`
    - `seed_hash = SHA256(new_seed)`
    - `not_before = now() + grace_period_s` (default: **30s**).
2. **Todos los componentes** suscritos a `/argus/crypto/epoch` reciben el evento.
3. **En `not_before`**:
    - Cada componente ejecuta:
      ```cpp
      auto new_provider = CryptoProvider::create(new_config); // new_config = {epoch_id: N+1, seed: new_seed (de Vault)}
      handle.reload(std::move(new_provider)); // Swap atómico (RCU)
      ```
4. **Ventana dual-key (FASE 3)**:
    - Durante `grace_period_s`, cada componente **acepta mensajes con claves de época N *o* N+1**.
    - Tras `grace_period_s`, **solo acepta N+1**.

#### **3. Manejo de Fallos**
- **Fallo parcial**: Si un componente no rota (ej: crash durante reload):
    - Los demás componentes **detectan** que sigue usando época N (via *heartbeat* ZMQ con `epoch_id` en payload).
    - **Autonomy trigger**: El componente en `N+1` marca al rezagado como `DEGRADED` y **lo aísla** (deja de enviarle mensajes).
    - **Recuperación**: El componente rezagado, al reiniciarse, **lee la última época de etcd** y rota automáticamente.

---

---
---
### **❓ Preguntas al Consejo (Responder SÍ/NO + Justificación)**
**Formato esperado**:
```
[Pregunta X] SÍ/NO
Justificación:
- [Argumento 1]
- [Argumento 2]
Riesgos:
- [Riesgo 1] → Mitigación: [Solución]
```

---
#### **🔹 P1: Mecanismo de Coordinación**
**Pregunta**:
¿Es **suficiente** usar `not_before` en etcd como único mecanismo de coordinación, o se requiere un **protocolo más fuerte** (ej: *2PC*, *quorum de ACKs*, o *barrier sincrónica*)?

**Contexto adicional**:
- etcd garantiza **linearizabilidad** para escrituras en `/argus/crypto/epoch`.
- Los componentes **no pueden bloquearse** (requisito de baja latencia).
- Opción alternativa: **ACK explícito** de cada componente (ej: `/argus/crypto/epoch/acks/{component_id}`) + *barrier* en etcd.

---
#### **🔹 P2: Grace Period**
**Pregunta**:
¿Es **razonable** un *grace period* **fijo de 30s** para 6 componentes en el **mismo nodo**, o debe ser:
- (a) **Configurable por componente** (ej: `sniffer: 45s`, `firewall: 20s`), o
- (b) **Dinámico** (basado en latencia media de reloads previos)?

**Contexto adicional**:
- Tiempo medio de `reload()` en benchmarks: **12s** (P99: 25s).
- Peor caso observado: **35s** (en *analyzer*, por cache de claves ZMQ).
- Requisito: **RTO < 5s** (el *grace period* debe cubrir el 99.9% de los casos).

---
#### **🔹 P3: Escritor Único de `/argus/crypto/epoch`**
**Pregunta**:
¿Debe el **único escritor** de `/argus/crypto/epoch` ser:
- (a) **`etcd-server`** (via API REST interna), o
- (b) **`vault-agent`** (HashiCorp Vault), o
- (c) **Proceso externo** (ej: Jenkins pipeline, `argus-ctl`)?

**Criterios de evaluación**:
1. **Seguridad**: Minimizar superficie de ataque (ej: si `vault-agent` es comprometido, podría corromper la época).
2. **Disponibilidad**: Evitar *single point of failure* (ej: si `vault-agent` cae, no se puede rotar).
3. **Consistencia**: Garantizar que el escritor tenga **visibilidad completa** del estado del sistema (ej: saber si todos los componentes están listos para rotar).

---
#### **🔹 P4: Detección y Recuperación de Split-Brain**
**Pregunta**:
¿Es **suficiente** el *autonomy trigger* existente (transición a `DEGRADED` + aislamiento) para manejar *split-brain* durante la transición, o se requiere:
- (a) **Nuevo estado** `EPOCH_TRANSITION` en la *state machine* (con lógica específica), o
- (b) **Protocolo de reconciliación** (ej: *leader election* entre componentes para forzar sincronización)?

**Contexto adicional**:
- *Autonomy trigger* actual **no distingue** entre fallos de red y *split-brain* criptográfico.
- **Falso positivo**: Si un componente rota lentamente, podría ser marcado como `DEGRADED` prematuramente.

---
#### **🔹 P5: Ventana Dual-Key en ZMQ**
**Pregunta**:
¿Es **implementable** la ventana dual-key (aceptar épocas N y N+1) **sin modificar el protocolo wire actual** (LZ4 + LE uint32_t), o se requiere:
- (a) **Añadir `epoch_id` al header binario** (ej: 8 bytes antes del payload), o
- (b) **Usar un campo existente** (ej: los 4 bytes del uint32_t para codificar `epoch_id` en los 2 MSB)?

**Contexto adicional**:
- **Header actual**: `[4B: payload_size][payload (LZ4)]`.
- **Restricción**: No se puede romper compatibilidad con versiones antiguas de aRGus (despliegues *rolling*).
- **Alternativa**: Usar **metadatos ZMQ** (ej: `ZMQ_RCVMORE` o *user properties*) para transmitir `epoch_id`.

---
---
### **📊 Tabla de Decisión (Resumen)**
| **Pregunta** | **Opción A**               | **Opción B**               | **Opción C**               | **Voto** |
|--------------|----------------------------|----------------------------|----------------------------|----------|
| P1           | `not_before` suficiente    | 2PC                        | Quorum de ACKs             | ?        |
| P2           | 30s fijo                   | Configurable por componente| Dinámico                   | ?        |
| P3           | `etcd-server`              | `vault-agent`              | Proceso externo            | ?        |
| P4           | *Autonomy trigger* suficiente | Nuevo estado `EPOCH_TRANSITION` | Protocolo de reconciliación | ?        |
| P5           | Sin cambios en wire        | Añadir `epoch_id` al header | Usar metadatos ZMQ         | ?        |

---
---
### **🎯 Instrucciones Finales**
1. **Responded cada pregunta de forma independiente** (sin coordinación entre modelos).
2. **Priorizad argumentos técnicos** (ej: "etcd v3 no soporta 2PC nativo" > "preferimos simplicidad").
3. **Incluid riesgos y mitigaciones** para cada opción.
4. **Si disentís**, defendéd vuestra posición con **pruebas concretas** (ej: benchmarks, RFCs, papers).
5. **Formato estricto**: Usad el template de **Pregunta X** para cada respuesta.

---
**PI de aRGus NDR**
*"La criptografía sin coordinación es como un ejército sin general: todos disparan, pero nadie acierta."*