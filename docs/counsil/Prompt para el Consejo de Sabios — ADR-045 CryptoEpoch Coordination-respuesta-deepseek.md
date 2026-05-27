**Respuesta del Consejo de Sabios — ADR-045**

Hemos analizado el problema desde las perspectivas de sistemas distribuidos, tolerancia a fallos, criptografía y protocolos de red. Nuestras deliberaciones han convergido en las siguientes recomendaciones, con alguna disensión menor que señalamos explícitamente.

---

### 1. ¿Es suficiente `not_before` o necesitamos un mecanismo más fuerte (ack explícito)?

**Consenso (7/8):**  
Para seis componentes que residen en el **mismo nodo** (confirmamos que este es el caso, según la pregunta 2), la coordinación basada en tiempo de pared con `not_before` y un *grace period* es suficiente. Los relojes en un único host son prácticamente idénticos y los *reloads* son locales, por lo que la ventana de desincronización real será de milisegundos.

Añadir confirmaciones (ack) o un protocolo de dos fases no aporta valor y sí complejidad indebida: en el mismo nodo no hay mensajes perdidos ni particiones de red que justifiquen 2PC. Además, el sistema ya contempla que un componente que no rota rompe su canal ZMQ (split-brain) y dispara el *autonomy trigger*, lo que es una forma de detección tardía pero válida.

**Disensión (1/8):**  
Un modelo sostuvo que un *ack* escrito en etcd por cada componente (ej. `/argus/crypto/epoch/ack/<componente>`) mejoraría la monitorización y facilitaría auditorías de seguridad. Sin embargo, este *ack* sería una **señal de observabilidad, no de coordinación**. El resto del Consejo acepta incorporarlo siempre que no se use para bloquear la transición, y así lo recomendamos: que cada componente notifique en etcd cuándo completó el reload, pero sin que el *etcd-server* espere esas confirmaciones para continuar.

**Recomendación final:**  
Mantener `not_before` como único mecanismo de coordinación. Opcionalmente, añadir escritura de estado *“reloaded”* por componente para monitorización.

---

### 2. ¿Grace period de 30 s configurable por componente?

**Consenso (8/8):**  
30 segundos es un valor holgado para seis procesos en el mismo sistema operativo. Un `reload` de un `CryptoProvider` basado en RCU puede completarse en menos de 100 ms por componente, incluso contando derivación HKDF y recarga de `shared_ptr` atómico.

No vemos necesidad de un *grace period* distinto por componente, porque el periodo de gracia define la ventana *dual-key* a nivel de sistema. Si un componente individual necesita más tiempo, probablemente indique un error (bloqueo, falta de acceso a Vault) que debe ser tratado como fallo, no alargando la ventana.

Sin embargo, hacer el valor **configurable globalmente** (por ejemplo, por variable de entorno o fichero de configuración) es sensato para entornos con restricciones especiales. No recomendamos granularidad por componente.

**Recomendación final:**  
*Grace period* global, configurable, con valor por defecto de 30 s.

---

### 3. ¿Quién debe ser el único escritor de `/argus/crypto/epoch`?

**Consenso (8/8):**  
El escritor único debe ser el propio **`etcd-server`**, proceso que ya forma parte del sistema (inferimos que existe un componente `etcd-server` que gestiona la publicación). La secuencia ideal es:

1. Un agente externo (Jenkins, operador, o el propio Vault tras rotar seed) invoca una API de `etcd-server` (gRPC/HTTP) con la nueva época.
2. `etcd-server` valida la coherencia de los datos (ej. que `epoch_id` sea estrictamente creciente, que `not_before` esté en el futuro, que el hash corresponda a un seed accesible en Vault).
3. `etcd-server` escribe atómicamente en etcd.

De este modo se evitan carreras si varios actores externos intentaran escribir directamente sobre etcd y se mantiene la lógica de negocio centralizada.

**Recomendación final:**  
**`etcd-server` es el único escritor.** La rotación se dispara a través de su API, no mediante escritura directa en etcd desde agentes externos.

---

### 4. ¿Cómo detectar y recuperar el *split-brain*? ¿Necesitamos un estado `EPOCH_TRANSITION`?

**Consenso (7/8):**  
La ventana *dual-key* (FASE 3) es la primera línea de defensa: mientras dure el *grace period*, los mensajes cifrados con clave antigua o nueva son aceptados, por lo que un desfase temporal no rompe la comunicación.

Una vez expirado el *grace period*, si un componente sigue con la clave antigua, su canal ZMQ con los demás fallará (autenticación AEAD). El *autonomy state machine* detecta pérdida de latido ZMQ y transita a `DEGRADED`/`FAILED`. Esto ya constituye una detección de *split-brain* criptográfico y se puede usar para disparar un reintento de recarga o una alerta.

No obstante, para evitar alarmas prematuras durante la transición, **recomendamos añadir un estado transitorio `EPOCH_TRANSITIONING`** con un temporizador igual al *grace period* + un margen. Durante ese estado, los fallos de comunicación que se resuelvan antes del timeout no escalan a `FAILED`. Esto suaviza el comportamiento y proporciona métricas claras de progreso de la rotación.

**Disensión (1/8):**  
Un modelo defendió que el estado `EPOCH_TRANSITIONING` añade complejidad innecesaria porque el *grace period* ya oculta los fallos temporales. Bastaría con que el *autonomy state machine* dispare una alarma si, tras `not_before + grace + δ`, el componente no ha reportado el nuevo `epoch_id` (usando el ack opcional de la pregunta 1). Sin embargo, el resto del Consejo considera que el estado explícito facilita el diagnóstico operacional y la integración con sistemas de monitorización.

**Recomendación final:**  
Añadir el estado `EPOCH_TRANSITIONING` a la máquina de estados de autonomía, con timeout = *grace period* + 5 s, tras el cual los fallos se tratan como fallos permanentes.

---

### 5. ¿Ventana *dual-key* requiere añadir `epoch_id` al *header* binario ZMQ?

**Consenso (8/8):**  
Sí, **es necesario incluir `epoch_id` en el *header* de cada mensaje**. Razonamiento:

El protocolo actual usa LZ4 y un `uint32_t` little‑endian (presumiblemente la longitud del *payload* comprimido). Si se utiliza cifrado autenticado (AEAD, p. ej., AES‑GCM), el receptor que desconoce la época podría intentar descifrar con ambas claves y detectar cuál es correcta mediante la verificación del *tag*. Esta solución funciona, pero tiene inconvenientes graves:
- Duplica el trabajo criptográfico en cada mensaje durante toda la ventana *dual-key*.
- Es frágil si en el futuro se adoptan algoritmos sin autenticación o con modos no detectables.
- Complica la lógica de recepción y puede introducir vulnerabilidades de *oracle* de padding/tag.

Añadir un campo `epoch_id` (p. ej., `uint64_t`) al *header* binario permite al receptor seleccionar inmediatamente la clave correcta y es una práctica estándar en protocolos que soportan rotación de claves (TLS 1.3, WireGuard, Signal). El coste es mínimo: 8 bytes adicionales en un contexto donde el *payload* comprimido probablemente supera los cientos de bytes.

**Recomendación final:**  
Extender el *header* binario con `epoch_id` (uint64_t) antes del `uint32_t` de longitud. Para compatibilidad hacia atrás durante la actualización, se puede negociar una versión de protocolo al inicio del canal ZMQ o usar un bit de *flag* en el primer byte del mensaje. Pero dado que todos los componentes se actualizan simultáneamente (mismo despliegue), la transición puede ser *flag‑day* sin negociación, siempre que se controle el orden de despliegue.

---

### Resumen de directrices para el PI

- **Coordinación:** `not_before` + *grace period* es suficiente. Añadir *acks* sólo con fines de observabilidad.
- **Grace period:** Global, configurable, 30 s por defecto.
- **Escritor único:** `etcd-server`, previa validación.
- **Estado de transición:** Añadir `EPOCH_TRANSITIONING` en la máquina de autonomía.
- **Protocolo wire:** Incluir `epoch_id` en el *header*; planificar un *flag‑day* para todos los componentes.

El Consejo considera que con estas decisiones ADR‑045 queda sólido para abordar la FASE 2. Quedamos a su disposición para revisar los detalles de implementación de la ventana *dual-key* cuando avance a FASE 3.