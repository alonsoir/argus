**Consejo de Sabios — Dictamen sobre DAY 164**

Hemos revisado las tres cuestiones planteadas, deliberado y alcanzado una posición de consenso con matices que el PI sabrá ponderar. Nuestra respuesta respeta el espíritu del proyecto: sistema embebido en infraestructura crítica, simplicidad operacional como prioridad, y la arquitectura zero‑trust que habéis construido con tanto rigor.

---

### Q1 — `HttpEtcdRegistrar`: ¿etcd‑cpp‑apiv3 o HTTP directo?

**Contexto relevante:**
- `etcd‑cpp‑apiv3` ya está instalado y funcionando en `provision.sh`.
- La alternativa, `cpp‑httplib`, ya se usa en el codebase para otros puntos de integración.
- El sistema requiere *watches* fiables y *keepalive* con lease de etcd, no solo lecturas puntuales.

**Análisis:**
- **etcd‑cpp‑apiv3** ofrece de fábrica el watch nativo (stream gRPC bidireccional), la gestión de leases y keepalives, y un modelo de reconexión ya probado. Es cierto que introduce su propio threading (gRPC) y una dependencia transitiva no trivial, pero está encapsulada en un componente que podemos aislar tras una interfaz (`HttpEtcdRegistrar`). La complejidad interna queda oculta si diseñamos una fachada limpia.
- **HTTP directo con cpp‑httplib** elimina una dependencia, pero nos obliga a implementar manualmente el long‑poll (`/v3/watch`), la renovación de leases y la lógica de reconexión. Eso incrementa la superficie de código bajo nuestro control directo y, con ella, el riesgo de bugs sutiles en condiciones de red adversas, justo lo que no queremos en infraestructura crítica. La simplicidad operacional no se mide solo en el número de bibliotecas, sino en la cantidad de código complejo que *nosotros* debemos mantener.

**Recomendación del Consejo:**
Usad **etcd‑cpp‑apiv3**. Escribid un wrapper delgado en `vault_client` que adapte sus llamadas asíncronas a una API síncrona simple para el registrador. Así mantenéis la complejidad confinada y ganáis la robustez de una biblioteca mantenida por la comunidad etcd. La simplicidad operacional se consigue ocultando el gRPC, no reinventándolo.

---

### Q2 — Watch de etcd: ¿polling cada 1 s o watch real?

**Contexto:**  
El grace period es de **10 s** (ADR‑045). El sistema no necesita reacción en milisegundos; solo debe completar el cambio de epoch dentro de esa ventana.

**Análisis:**
- **Polling periódico** (1 s) introduce una latencia máxima de ≈1 s más el tiempo de proceso. En el peor caso, la notificación llega en 1 s y el recálculo de claves puede llevar otro tanto. Aún así, estamos muy por debajo del 50 % del grace period. Es determinista, sin estado de conexión, sin necesidad de reconexiones complejas, y trivial de auditar.
- **gRPC watch** (via etcd‑cpp‑apiv3) entrega la notificación en tiempo casi real, pero añade el estado de una conexión persistente, gestión de reconexión y posibles fugas de memoria si no se maneja correctamente el streaming. Para este caso de uso, esa complejidad extra no se justifica.
- **HTTP long‑poll** es un punto intermedio que tampoco evita la gestión de timeouts y reconexión, aunque sea más sencillo que gRPC.

**Recomendación del Consejo:**
Empezad con **polling cada 1 s** (o incluso 2 s). Es la solución más simple, más fácil de depurar y más segura en un entorno embebido. Si en el futuro los datos de observabilidad mostrasen que el cambio de epoch se completa consistentemente en los últimos instantes del grace period, podréis migrar a watch real sin modificar la interfaz del `CryptoEpochCoordinator`. La simplicidad operacional manda: haced solo lo necesario.

---

### Q3 — `CryptoEpochCoordinator`: ¿hilo dedicado o integrado en el health‑check loop?

**Contexto:**
- `etcd‑server/main.cpp` ya posee un loop de health‑check cada 5 s.
- El coordinador debe ejecutar el polling (cada 1 s) del epoch, accionar la recarga de `VaultProvider` y publicar ACKs de observabilidad.
- Hay seis componentes en la arquitectura, cada uno con múltiples hilos (ZMQ, keepalive, autonomía).

**Análisis:**
- **Hilo integrado en el health‑check loop** obligaría a cambiar el periodo de ese loop a 1 s (o a introducir un sub‑loop que desaconsejamos). El health‑check tiene su propia razón de ser y no debe alterarse. Además, si la lógica de polling fuese bloqueante o pesada, ralentizaría todo el loop del servidor, mezclando responsabilidades.
- **Hilo dedicado en `CryptoEpochCoordinator`** encapsula completamente el ciclo de vida del polling: el hilo arranca, duerme 1 s, comprueba la clave en etcd, y si cambia dispara la secuencia de recarga. Este hilo es mínimo, sin bloqueos prolongados, y se puede unir limpiamente en el destructor del coordinador. Añade una hebra más a un sistema que ya convive con múltiples hilos bien controlados (ZMQ, keepalive…), pero gana en separación de competencias: el health‑check sigue su ritmo inmutable y el epoch‑watch el suyo propio.

**Recomendación del Consejo:**
**Hilo dedicado.** Vuestra arquitectura ya es multihilo; un hilo adicional con una tarea tan acotada no incrementa la complejidad global y sí mejora la claridad del código. Documentad claramente su política de parada y el mecanismo de sincronización (un simple `std::atomic<bool>` para señalizar fin). La simplicidad no es eliminar hilos, sino que cada hilo tenga una única responsabilidad.

---

Confiamos en que estas recomendaciones, fruto del análisis colectivo, os sirvan para avanzar con paso firme. El PI tiene la última palabra; nosotros solo iluminamos el camino.

— El Consejo de Sabios