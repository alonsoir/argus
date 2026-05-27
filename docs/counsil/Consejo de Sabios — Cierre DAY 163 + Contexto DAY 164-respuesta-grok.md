**Recomendaciones del Consejo para DAY 164 (respuesta independiente).**

He analizado las preguntas en el contexto del proyecto: sistema crítico (infraestructura, crypto hot-reload con grace period de 10s, zero-trust, RCU para providers, componentes embebidos con múltiples hilos ya existentes). Prioridades: **fiabilidad operacional**, **simplicidad de despliegue/mantenimiento**, **baja latencia predecible** y **mínima superficie de ataque/complejidad**. El ADR-045 ya define grace period global de 10s y coordinación ligera (sin 2PC fuerte).

### Q1 — HttpEtcdRegistrar: ¿etcd-cpp-apiv3 o HTTP directo?

**Recomendación fuerte: etcd-cpp-apiv3 (la que ya está instalada en provision.sh).**

Razones:
- Ya está provisionada → **cero costo operacional nuevo**. No introduces nueva dependencia de build/runtime.
- API idiomática C++ con soporte nativo para leases/keepalive y watch. Reduce boilerplate y errores comunes (reintentos, reconexiones, lease management).
- gRPC subyacente es el estándar de etcd v3 y está optimizado para esto (mejor que reinventar long-poll fiable).
- En sistemas críticos, código mantenido por terceros (con historia en Nokia y comunidad) suele ser más robusto que un wrapper HTTP ad-hoc que tendréis que mantener vosotros para edge cases (reconnects, timeouts, watch resumption por revision).

**Contra cpp-httplib**: Ahorra una dep en teoría, pero pagas en código propio para watch fiable (long-poll no es trivial en producción: manejo de reconexiones, headers de watch, resumir desde revision, etc.). En embedded/crítico, “menos deps” es bueno solo si no aumenta complejidad/código propio. Aquí aumenta.

**Decisión PI sugerida**: Adelante con etcd-cpp-apiv3. Aseguraos de compilar con la opción síncrona si queréis minimizar threads background (o controlad el thread pool). Testead lease TTL y reconexión agresiva en red flaky.

### Q2 — Watch de etcd: polling vs long-poll vs gRPC watch

**Recomendación: gRPC watch nativo vía etcd-cpp-apiv3 (o equivalente long-poll bien implementado si usáis HTTP). Polling periódico NO.**

Razones para grace period de 10s:
- **Polling cada 1s** es “aceptable” en latencia (peor caso ~1s + procesamiento), pero genera ruido innecesario en etcd (miles de requests/segundo en cluster grande), consume CPU/banda en componentes embebidos y complica “exactly-once” semantics (necesitáis trackear revisiones de todas formas).
- etcd está diseñado para **watches eficientes** (gRPC streams bidireccionales o HTTP long-poll). Es más eficiente en servidor y cliente, garantiza entrega ordenada y sin pérdida (MVCC + revisiones).
- Para 10s de grace, even una latencia de watch de ~100-500ms es excelente y permite reaccionar con holgura (refresh Vault + reload RCU atómico).

**gRPC watch** es preferible si usáis la lib (gestión automática de streams, reconexiones). Si caéis en HTTP, long-poll es aceptable pero requiere más cuidado en reconexión y re-establecimiento desde última revision conocida.

**Decisión PI sugerida**: Watch real (gRPC preferido). Polling solo como fallback degradado con backoff exponencial. Documentad en ADR la revisión de recuperación (para no perder eventos durante reconexiones).

### Q3 — CryptoEpochCoordinator: ¿hilo dedicado o integrado en health-check loop?

**Recomendación: Integrado en el health-check loop existente (llamar a coordinator.poll() cada iteración).** Evitad hilo dedicado salvo que el poll sea blocking largo.

Razones:
- Ya tenéis múltiples hilos por componente (ZMQ, keepalive, autonomy). Añadir uno más por componente (×6) aumenta complejidad de debugging, scheduling jitter y riesgo de thread explosion/leaks.
- El health-check loop cada 5s es ritmo natural y suficiente para grace 10s. `poll()` puede ser no-blocking (check si hay eventos en watch sin bloquear) o con timeout corto.
- **Encapsulación**: El coordinador puede exponer `poll()` + callbacks/events internos. El main loop sigue siendo el dueño del threading → más predecible y fácil de razonar (un solo loop de control principal por proceso).
- RCU/hot-reload ya es lock-free y seguro para readers. No necesitáis hilo extra para la mayoría de casos; el refresh se dispara asincrónicamente vía callback.

**Cuándo hilo dedicado**: Solo si implementáis un watch blocking (stream gRPC que bloquea) y queréis aislarlo completamente. En ese caso, encapsulad bien el threading dentro del Coordinator (start/stop, exception safety, join en shutdown).

**Decisión PI sugerida**: Integrado + `poll()`. Mantiene el sistema más “embedded-friendly” y reduce hilos totales. Si más adelante el watch necesita ser fully event-driven, migrad a dedicated thread con clara ownership.

### Observaciones generales / DEBT-ETCD-REGISTRAR-REAL-001
- Priorizad **TDH RED→GREEN** con tests de reconexión, lease expiry, network partition y recuperación de epoch.
- Añadid métricas (número de watches activos, revision lag, reloads exitosos/fallidos) para observabilidad post-hoc (como en P1 del ADR).
- Documentad en ADR-045 v2 las decisiones de threading y cliente elegido, con trade-offs explícitos.
- El stub → real es buen momento para unificar register_status + keepalive + watch bajo una sola conexión/cliente donde posible.

Estas recomendaciones priorizan robustez operacional y minimizar moving parts en un sistema ya complejo con crypto hot-path. El PI tiene la última palabra; estoy disponible para contra-argumentos o más detalles técnicos.

¡Éxito en DAY 164!