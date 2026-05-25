Estimado Product Investigator (PI) y miembros del Consejo, aquí tenéis el análisis técnico independiente y las recomendaciones para el **DAY 164**.

Felicidades por cerrar la Fase 0 y la Fase 1 en el DAY 163. Conseguir un RCU header-only lock-free con 9/9 tests en verde no es moco de pavo. Al lío con el descubrimiento del stub de etcd y el diseño de la Fase 2.

---

## Q1 — HttpEtcdRegistrar: ¿etcd-cpp-apiv3 o HTTP directo?

### Recomendación del Consejo: Usar `etcd-cpp-apiv3`

Aunque la tentación de "cero dependencias nuevas en ejecución" usando `cpp-httplib` es atractiva, construir lógica de infraestructura crítica sobre HTTP/1.1 crudo para etcd v3 suele acabar en pesadilla de mantenimiento.

| Criterio | `etcd-cpp-apiv3` (Recomendado) | `cpp-httplib` directo |
| --- | --- | --- |
| **Complejidad de Código** | **Baja.** API nativa y abstracciones ya hechas. | **Alta.** Hay que implementar la máquina de estados de leases y reconnects a mano. |
| **Robustez de Conexión** | **Alta.** Gestionada por la capa gRPC subyacente. | **Media/Baja.** El long-poll en HTTP/1.1 sufre con timeouts intermitentes de red. |
| **Deuda Técnica** | **Baja.** Ya está en `provision.sh`, solo hay que usarla. | **Alta.** Mantener un cliente HTTP-etcd propio en un sistema NDR. |

> **Veredicto:** Dado que `etcd-cpp-apiv3` **ya está en el script de provisión**, no estamos añadiendo fricción al entorno de despliegue. Delegar la gestión de hilos y la serialización a una librería probada mitiga el riesgo de fugas de memoria o condiciones de carrera en la gestión de sockets.

---

## Q2 — Watch de etcd: polling vs long-poll vs gRPC watch

### Recomendación del Consejo: gRPC watch nativo

Con un grace period global fijado en **10 segundos** (ADR-045 v1), la latencia de propagación se convierte en una métrica crítica de seguridad.

* **El peligro del Polling (1s):** Si hacemos polling cada segundo, introducimos un jitter intrínseco de hasta 1000ms solo en descubrir el cambio. Esto se come automáticamente el **10% de nuestro margen de seguridad (grace period)** antes de que el componente empiece siquiera a reaccionar. Multiplicado por 6 componentes, es ruido innecesario en el log y en la red.
* **La ventaja de gRPC watch:** Al estar integrado con la recomendación de la Q1, el streaming bidireccional de gRPC reacciona en milisegundos. Notifica el cambio de epoch de forma casi instantánea, dejando los 10 segundos íntegros para la coordinación real y el vaciado de buffers de red.

> **Veredicto:** Para infraestructura crítica, el determinismo temporal manda. **gRPC watch** es la opción que garantiza que los 10 segundos de gracia se aprovechen para lo que fueron diseñados, no para esperar la siguiente iteración de un bucle de polling.

---

## Q3 — CryptoEpochCoordinator: ¿hilo dedicado o integrado en el loop existente?

### Recomendación del Consejo: Hilo dedicado / Modelo Asíncrono manejado por la librería

Integrar la lógica en el loop de health-check existente de `main.cpp` que corre cada 5 segundos es un **riesgo crítico de arquitectura**.

Si el loop corre cada 5 segundos, en el peor de los casos el componente tardará 5 segundos en enterarse de que el epoch ha cambiado. Si sumamos esto al jitter de red, **perdemos el 50% o más del grace period de 10s** antes de ejecutar `handle.reload()`. Los lectores seguirán usando el provider viejo cuando etcd ya haya avanzado, provocando descartes de paquetes o fallos de descifrado masivos al expirar el tiempo.

```
[Línea de tiempo del Grace Period de 10s si usamos el loop de 5s]

0s -------------- 5s ----------------------- 10s
|                  |                         |
Cambio en etcd     Loop detecta cambio       Fin del Grace Period
                   (¡Solo quedan 5s!)

```

### Arquitectura Propuesta

1. `etcd-cpp-apiv3` ya levanta sus propios hilos de trabajo para gestionar las llamadas gRPC asíncronas.
2. `CryptoEpochCoordinator` debe encapsular esta reactividad. Al inicializarse, lanza el `watch()` de la librería, el cual expone un callback ejecutable en el hilo de gRPC cuando cambia `/argus/crypto/epoch`.
3. Al recibir el evento, el callback ejecuta inmediatamente `VaultProvider::refresh()` y `handle.reload()`.

> **Veredicto:** **Hilo dedicado / Asíncrono.** El loop de 5 segundos de `main.cpp` debe seguir encargándose exclusivamente de la salud del proceso, manteniéndose ortogonal a la reactividad inmediata que exige la rotación criptográfica.