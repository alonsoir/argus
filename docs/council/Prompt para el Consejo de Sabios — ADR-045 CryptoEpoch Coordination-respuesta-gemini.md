Aquí tenéis mi revisión técnica y detallada de la **ADR-045 v1**. Como coautor de la infraestructura, os doy mi enhorabuena por el diseño de la FASE 1; implementar el wrapper RCU con `std::atomic<shared_ptr<ICryptoProvider>>` en C++20 es la decisión correcta para garantizar un *hot-swap* libre de bloqueos (*lock-free*) y con overhead mínimo en el path de datos.

Entremos de lleno en la ingeniería de la **FASE 2 (CryptoEpoch)** para evitar el temido *split-brain* criptográfico.

---

## Revisión Técnica de la ADR-045 v1

### 1. Coordinación: ¿`not_before` o ACKs explícitos?

**Veredicto:** `not_before` combinado con la ventana dual-key (FASE 3) es **suficiente y superior** a un mecanismo de ACK explícito (como 2PC).

* **Argumentación:** Introducir ACKs o un protocolo de consenso de dos fases (2PC) añade una complejidad sistémica brutal y estados de fallo intermedios (¿qué pasa si un componente da ACK pero muere antes de aplicar el cambio?).
* **Condición Crítica:** Para que `not_before` funcione de forma segura en infraestructura crítica, dependéis de la sincronización horaria. Dado que el contexto menciona que los 6 componentes están en el **mismo nodo**, el *clock skew* entre ellos es cero (comparten el mismo reloj del OS). Por tanto, la sincronización temporal no es un problema aquí.

### 2. Dimensión del Grace Period (30s)

**Veredicto:** 30 segundos es un **abuso masivo** para componentes co-localizados en el mismo nodo. Debe ser uniforme y drásticamente menor.

* **Argumentación:** El tiempo que tarda un subscritor de `etcd` (vía gRPC watch) en recibir el evento y realizar el swap atómico RCU en C++20 se mide en **milisegundos** (normalmente < 10ms si el sistema no está en colapso de CPU).
* **Recomendación:** Reducid el *grace period* a **2 o 5 segundos**. Mantener una ventana dual-key abierta durante 30 segundos expone innecesariamente el sistema a vectores de ataque donde un atacante podría explotar claves de la época saliente durante demasiado tiempo. **No debe ser configurable por componente**; la asimetría temporal entre componentes rompería la predictibilidad del pipeline.

### 3. El Único Escritor de `/argus/crypto/epoch`

**Veredicto:** El único escritor debe ser un **proceso externo orquestador (ej. un script/agente junto a Vault)**, nunca el propio `etcd-server` (que es un mero almacén pasivo).

* **Argumentación:** El flujo ideal es: Vault genera el nuevo seed $\rightarrow$ el agente de despliegue/seguridad lee el metadata (no el seed directo) $\rightarrow$ el agente escribe en `etcd` de forma atómica. Si permitís que múltiples componentes escriban o que `etcd` "asuma" lógica de negocio, violáis el principio de única fuente de verdad y os arriesgáis a condiciones de carrera.

### 4. Detección y Recuperación de Split-Brain

**Veredicto:** La *Autonomy State Machine* existente **no es suficiente**; requiere un estado explícito de transición o degradación temporizada.

* **Argumentación:** Si un componente crítico (ej. *firewall*) falla al rotar (por ejemplo, porque se cayó su conexión al socket de `etcd`), los otros componentes empezarán a enviarle tráfico cifrado con la época $N+1$. El *firewall* rechazará los paquetes por fallo de integridad/descifrado.
* **Diseño de Recuperación:**
* Añadid el estado `EPOCH_TRANSITION`.
* Si un componente detecta un pico de fallos de descifrado/MAC procedentes de componentes hermanos justo en la ventana $T + \text{grace}$, debe asumir un fallo de sincronización de época.
* **Acción de contingencia:** Forzar un *bypass* del Watch de `etcd` realizando una lectura directa y síncrona (*Get*) de `/argus/crypto/epoch`. Si ve que está desactualizado, fuerza su propia recarga. Si aun así falla, activa el *autonomy trigger* (aislamiento del nodo).



### 5. Ventana Dual-Key en ZeroMQ (Wire Protocol)

**Veredicto:** **Requiere obligatoriamente modificar el header binario** introduciendo `epoch_id`. El descifrado a ciegas (*trial decryption*) no es una opción viable en infraestructura crítica.

* **Argumentación:** Si no enviáis el `epoch_id` en el header actual (`LZ4 + LE uint32_t`), el receptor, al recibir un paquete durante el *grace period*, no sabrá si viene cifrado con la clave $N$ o $N+1$. Tendría que intentar descifrar/verificar con la clave $N$, y si falla (lanzando excepción o código de error), intentar con la clave $N+1$.
* **El peligro:** Esto duplica el coste computacional en el peor escenario y abre la puerta a un ataque de Denegación de Servicio (DoS). Un atacante podría inundar el sistema con basura, forzando al pipeline C++20 a realizar doble verificación criptográfica por cada paquete inválido, degradando el rendimiento del NDR.
* **Propuesta de Header Modificado:**
```
+-----------------------+---------------------+-----------------------+
| Total Length (uint32) |  Epoch ID (uint32)  |  LZ4 Payload (Crypto) |
+-----------------------+---------------------+-----------------------+

```


Con esto, el componente indexa instantáneamente cuál de las dos claves activas en su `CryptoProviderHandle` debe usar, manteniendo el rendimiento determinista O(1).

---

¿Qué opináis de la estructura del nuevo header binario? Si añadimos el `Epoch ID` (4 bytes), ¿afectaría de forma crítica a la alineación de memoria en vuestro diseño actual de buffers de ZeroMQ?