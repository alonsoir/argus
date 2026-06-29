Aquí van mis respuestas como miembro del Consejo, razonando de forma independiente:

---

## Claude — Respuestas ADR-045 CryptoEpoch Coordination

### 1. ¿`not_before` en etcd es suficiente o necesitamos ack explícito?

**`not_before` es suficiente para v1, con una condición.**

El ack explícito introduce 2PC implícito: si un componente no responde, el coordinador queda bloqueado esperando. En un sistema de infraestructura crítica eso es peor que un split-brain temporal. `not_before` con grace period largo es el patrón correcto — es exactamente lo que usan TLS certificate rotation y Kubernetes secret rotation.

La condición: cada componente debe escribir en etcd su epoch actual tras el reload (`/argus/crypto/components/<name>/epoch = N+1`). No como prerequisito del coordinador, sino como observabilidad post-hoc. El coordinador no espera — solo registra quién no rotó para el runbook del operador.

### 2. ¿30s de grace period es razonable?

**Sí para dev, no como valor fijo para prod.**

6 componentes en el mismo nodo físico: 30s es excesivo técnicamente (el reload es atómico, milisegundos). Pero 30s es correcto operacionalmente porque el cuello de botella no es el reload sino la detección humana de un fallo durante la transición.

Recomendación: `grace_period_seconds` en `/argus/crypto/epoch` junto al `not_before`. Valor por defecto 30s. Cada deployment puede ajustarlo. No por componente — la granularidad por componente introduce asimetría que es exactamente el split-brain que queremos evitar.

### 3. ¿Quién es el único escritor de `/argus/crypto/epoch`?

**etcd-server, nunca Jenkins directamente.**

Razón: Jenkins no tiene visibilidad del estado interno del pipeline. Si Jenkins escribe directamente y un componente está en `AUTONOMOUS`, la rotación ocurre sobre un sistema que ya no está en estado conocido.

El flujo correcto:
```
Vault agent detecta rotación → notifica a etcd-server via API interna
etcd-server verifica que todos los componentes están en NORMAL
etcd-server escribe /argus/crypto/epoch con not_before=now+grace
```

etcd-server es el único que tiene el estado global del pipeline. Es la autoridad natural.

### 4. ¿Cómo detectar y recuperar split-brain? ¿Necesita estado `EPOCH_TRANSITION`?

**Sí, `EPOCH_TRANSITION` es necesario. La máquina de estados actual no lo cubre.**

El split-brain de época es diferente al split-brain de Vault. Hoy `AUTONOMOUS` significa "Vault no alcanzable". Pero durante una transición de época, Vault puede estar perfectamente sano y aun así el canal ZMQ estar muerto porque un componente no rotó.

Estado nuevo propuesto:
```
NORMAL → EPOCH_TRANSITION (al recibir not_before futuro)
EPOCH_TRANSITION → NORMAL (tras reload exitoso + canal ZMQ verificado)
EPOCH_TRANSITION → EPOCH_FAILED (si grace period expira sin reload exitoso)
EPOCH_FAILED → requiere intervención manual (fail-closed)
```

`EPOCH_FAILED` es crítico: no debe caer en `AUTONOMOUS` porque las acciones de recuperación son distintas. `AUTONOMOUS` se recupera solo cuando Vault vuelve. `EPOCH_FAILED` requiere que el operador decida si forzar la época o revertir.

### 5. ¿Dual-key ZMQ implementable sin cambios en el wire protocol?

**No. Requiere añadir `epoch_id` al header binario.**

Sin `epoch_id` en el wire, el receptor no puede saber si un mensaje usa clave de época N o N+1. El único comportamiento posible es probar ambas claves por orden — O(2) descifrado, con el riesgo de falsos positivos si los seeds son similares.

El header actual (LZ4 + LE uint32_t) debe extenderse:
```
[uint32_t payload_size LE] [uint32_t epoch_id LE] [payload LZ4]
```

Esto rompe el wire protocol — es un cambio de versión. Recomiendo:
- Definir la extensión ahora en ADR-045
- Implementarla en FASE 3 con flag de compatibilidad hacia atrás
- Durante la ventana dual-key: el emisor envía con `epoch_id` nuevo, el receptor acepta N y N+1 mirando el campo

**El coste de no hacerlo es mayor**: sin `epoch_id`, la ventana dual-key es un hack que introduce ambigüedad criptográfica. Mejor el cambio limpio ahora que un workaround que persiste años.

---

**Posición de síntesis:**

ADR-045 v1 es viable con estos ajustes: `not_before` suficiente (sin ack), grace period configurable en el evento (no por componente), etcd-server como único escritor con verificación de estado previo, estado `EPOCH_TRANSITION` nuevo en la máquina de autonomía, y `epoch_id` obligatorio en el wire header desde FASE 3.

El riesgo mayor no es técnico sino operacional: el primer `EPOCH_FAILED` en producción a las 3am en un hospital. El runbook debe existir antes de que FASE 4 entre en producción.

---

¿Guardado. Quieres que ajuste el tono o la profundidad de alguna respuesta antes de que consultes al resto del Consejo?