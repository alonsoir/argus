A la atención del equipo de ingeniería de aRGus, en la sesión 138 del Consejo de Sabios.

Hemos analizado con detenimiento el informe de progreso de la rama `feature/variant-b-libpcap` y las siete cuestiones planteadas. La calidad del trabajo realizado, en particular el cierre de las deudas de arquitectura `DEBT-CAPTURE-BACKEND-ISP-001` y `DEBT-VARIANT-B-PCAP-IMPL-001`, demuestra un compromiso encomiable con la excelencia técnica. A continuación, presentamos nuestro veredicto.

---

### **[Q1] Arquitectura `PcapCallbackData`**

El enfoque de utilizar un struct plano `PcapCallbackData` como miembro de `PcapBackend` y pasarlo como argumento `user` a `pcap_dispatch` es **sólido y seguro** en el contexto descrito.

La principal garantía de seguridad proviene del modelo de ejecución síncrono de `pcap_dispatch`. Dado que la función no retorna hasta que se procesa el lote de paquetes o se alcanza una condición de parada, el ciclo de vida del struct (y del objeto `PcapBackend` que lo contiene) está inequívocamente ligado a la duración de la llamada. Este es un patrón ampliamente utilizado y documentado en la API de libpcap.

No obstante, la robustez del sistema se basa en un **invariante**: el objeto `PcapBackend` no debe ser destruido mientras `pcap_dispatch` está en ejecución. En el diseño actual, esto se cumple porque la vida de `PcapBackend` excede la del bucle de captura. Para reforzar esta garantía de por vida, se podría considerar:
*   **Documentación explícita**: Comentar en el destructor de `PcapBackend` la precondición de que `pcap_dispatch` no debe estar activo.
*   **Verificación en `close()`**: Añadir una aserción o un flag atómico que asegure que el backend no se cierra durante una captura activa.

El uso de `std::shared_ptr` o mecanismos más complejos no es necesario, ya que añadirían una sobrecarga de propiedad compartida que no se requiere en este diseño, donde la relación de contención es clara y unidireccional.

**Veredicto**: La solución actual es suficiente y correcta. Las alternativas (friend, miembros públicos) son menos deseables por las razones ya identificadas. Recomendamos documentar el invariante para prevenir futuros errores de uso.

---

### **[Q2] Wire format: `dontwait` vs bloqueante**

La política de descarte con `zmq::send_flags::dontwait` es **técnicamente aceptable para este contexto operativo**, siempre que se implemente un monitoreo riguroso.

En un sistema de detección de intrusiones (NDR), la premisa fundamental es: **es preferible perder un paquete que bloquear el bucle de captura y perder todos los paquetes subsiguientes**. Un hilo de captura bloqueado es un punto ciego total, lo cual es inaceptable en un entorno de seguridad. La naturaleza `dontwait` de ZeroMQ permite que el sniffer sea "frágil" (pierde paquetes bajo presión) en lugar de "frágil" (se bloquea y deja de funcionar).

La sobrecarga de `sleep` + `retry` en un hilo único reintroduce el riesgo de bloqueo que `dontwait` evita. El tiempo de espera podría causar que el buffer de captura de libpcap se desborde, perdiendo más paquetes de los que se descartarían por un pico en ZeroMQ.

**Recomendamos un enfoque híbrido**: Mantener `dontwait` como política por defecto, pero exponer el contador de `send_failures` a través de métricas (Prometheus, `stats()`). Si la tasa de descarte supera un umbral crítico (ej: >1%), se debe generar una alerta para que el operador investigue un posible cuello de botella en `ml-detector` o un subdimensionamiento de los sockets ZMQ. La corrección no está en el sniffer, sino en el consumidor.
Esto está en línea con el diseño de ZeroMQ, donde la contrapresión es responsabilidad del desarrollador de la aplicación.

**Veredicto**: Mantener `dontwait`. No introducir backpressure (sleep/retry) en el hilo de captura. Es prioritario monitorizar `send_failures` y generar alertas.

---

### **[Q3] `sniffer-libpcap.json`: campos a preservar vs eliminar**

La identificación de campos a eliminar es correcta: `zmq_sender_threads`, `io_thread_pools`, `zmq.socket_pools.push_sockets`, `threading.*`, `ring_buffer.*` son artefactos de la arquitectura multihilo de la Variant A y no aplican. Los campos a preservar (`capture.interface`, `output_socket.address/port`, `capture.filter.*`) constituyen la base operativa.

**Campos adicionales a considerar para eliminar o ausentes a añadir:**

*   **Eliminar**: `capture.promiscuous`. Para un NDR en producción, el modo promiscuo debe ser una decisión de despliegue, no de configuración. Hardcodear a `false` o controlarlo mediante un flag de línea de comandos sería más seguro.
*   **Eliminar**: `capture.buffer_size`. En Variant B, este valor se traduce directamente en la llamada a `pcap_set_buffer_size()`. Si no se especifica, libpcap usa un valor por defecto adecuado.
*   **Considerar añadir**: `capture.timeout_ms` (tiempo de espera de `pcap_dispatch`). Actualmente está hardcodeado en el código. Exponerlo como configuración permite ajustar la latencia sin recompilar.
*   **Considerar añadir**: `capture.endpoint_id`. Si el pipeline de `ml-detector` lo utiliza para identificación, añadir un identificador único para el sniffer podría ser útil para el diagnóstico.

**Veredicto**: La lista propuesta es completa. Recomendamos hardcodear `promiscuous = false` y `buffer_size = 0` (por defecto). Exponer `timeout_ms` y `endpoint_id` como configuración opcional.

---

### **[Q4] Test e2e: estrategia para dev VM sin tráfico real**

Ambas opciones son viables y complementarias. La elección depende del objetivo del test:

*   **`pcap_open_dead()` + `pcap_inject()`**: Ideal para **tests unitarios y de integración de la lógica de callback**. No requiere privilegios de root, es determinista y permite probar casos límite (paquetes malformados, tamaños extremos) de forma controlada. Recomendamos esta estrategia como la **base de la suite de tests**, ejecutable en cualquier entorno de desarrollo. `pcap_open_dead()` se usa típicamente para este propósito.

*   **`tcpreplay` sobre `lo` o `eth1`**: Recomendado para **tests end-to-end** que validen el pipeline completo (captura -> serialización -> compresión -> cifrado -> ZMQ). `tcpreplay` inyecta tráfico realista desde un archivo PCAP de referencia (como CIC-IDS-2017). Esto prueba el sistema en condiciones más cercanas a producción. Es menos determinista y puede requerir privilegios, pero valida la integración real.

**Veredicto**: Un enfoque de dos niveles.
1.  Usar `pcap_open_dead()` + `pcap_inject()` para la suite de tests unitarios (`ctest`), asegurando una rápida validación en el ciclo de desarrollo.
2.  Para el test end-to-end (`DEBT-VARIANT-B-CONFIG-001`), usar `tcpreplay` sobre `lo`, ya que valida el camino completo. Si la complejidad de `tcpreplay` en CI es alta, `pcap_inject()` sobre un `pcap_open_live("lo")` es una alternativa que mantiene la validez del pipeline sin depender de herramientas externas.

---

### **[Q5] `DEBT-IRP-NFTABLES-001`: atomicidad de `argus-network-isolate`**

Confirmamos que el enfoque transaccional con `nft -f` es el correcto. La operación de reemplazo atómico del ruleset es una funcionalidad nativa y garantizada de nftables.

Para gestionar el rollback si el proceso muere a mitad de la aplicación, proponemos un mecanismo de dos fases:

1.  **Snapshot Pre-Operación**: Antes de aplicar las reglas de aislamiento, el script `argus-network-isolate` debe guardar el ruleset actual en una ubicación predefinida (ej. `/var/lib/argus/irp/nftables.snapshot`) usando `nft list ruleset`.
2.  **Aplicación Atómica con Timeout de Seguridad**: El script aplica las reglas de aislamiento con `nft -f`. Inmediatamente después, programa la reversión automática usando `at` o un temporizador de systemd con `OnUnitActiveSec`. La reversión consiste en ejecutar `nft -f /var/lib/argus/irp/nftables.snapshot`.
3.  **Señal de Éxito**: Una vez finalizado el incidente, el operador (o el proceso de IRP) debe ejecutar `argus-network-isolate --clear`, lo que cancela el temporizador de reversión y opcionalmente carga una configuración de "restauración" predefinida.

Este enfoque es similar a la filosofía de herramientas como `nftguard`, que implementa versionado y rollback para nftables.

**Veredicto**: Adoptar el modelo transaccional con `nft -f`. Implementar el mecanismo de snapshot + timeout para garantizar el rollback automático incluso en caso de fallo catastrófico del proceso que aplica las reglas.

---

### **[Q6] `DEBT-COMPILER-WARNINGS-CLEANUP-001`: prioridad ODR**

**Confirmamos que la resolución de las violaciones ODR debe ser la primera sub-tarea, de forma bloqueante.** La razón es fundamental y no admite debate:

> Una violación de la Regla de Una Definición (ODR) implica que **el programa está mal formado y no hay garantías por la especificación del lenguaje**. El comportamiento no está definido, lo que puede manifestarse como corrupción silenciosa de datos, fallos de seguridad inexplicables o ejecución de código arbitrario.

En contraste, las advertencias de compilación restantes (funciones OpenSSL deprecadas, signed/unsigned, etc.) son ruidosas pero tienen un comportamiento determinista y no comprometen la integridad fundamental del programa.

En sistemas con protobuf y múltiples unidades de traducción, las ODR pueden surgir por definiciones duplicadas de clases internas (como `InternalNode` vs `TrafficNode`) si se enlazan bibliotecas estáticas y dinámicas de protobuf, o si se compilan con diferentes flags. La solución típica es asegurar que todas las unidades de traducción utilicen exactamente las mismmas definiciones de protobuf, a menudo compilando los `.proto` como parte del mismo proyecto en lugar de enlazar una biblioteca precompilada.

**Veredicto**: **ODR es la máxima prioridad, bloqueante para el resto de la limpieza**. Recomendamos una revisión exhaustiva de las dependencias de protobuf en `CMakeLists.txt` para identificar y eliminar la duplicación de definiciones.

---

### **[Q7] Threading model: ARM64 + seL4 a largo plazo**

La pregunta aborda un horizonte de investigación post-FEDER. Nuestro análisis es el siguiente:

*   **Partes reutilizables**: La interfaz `CaptureBackend`, con sus 5 métodos puros, es ideal para una arquitectura basada en capacidades. La abstracción es independiente del modelo de hilos. De igual manera, la lógica de parseo de paquetes (`ETH/IP/TCP/UDP parse`) y la construcción de `NetworkSecurityEvent` son altamente reutilizables si se aíslan en un módulo sin estado.
*   **Partes que requerirán reescritura**: Todo el stack de comunicación y procesamiento (`ZeroMQ`, `LZ4`, `CryptoTransport`, la serialización de Protobuf) deberá ser repensado. En seL4, estos componentes se implementarán como **servidores separados en distintos dominios de protección**, comunicándose mediante IPC síncrono (seL4_ReplyRecv). El uso de `std::thread` y `std::mutex` deberá ser eliminado.
*   **¿Diseñar ya para seL4?**: **Es prematuro y añadiría una complejidad innecesaria en la fase actual.** El objetivo pre-FEDER es ARM64 + AppArmor, donde el modelo multihilo de Linux es totalmente válido. Intentar abstraer el IPC de seL4 ahora llevaría a una sobre-ingeniería que ralentizaría el desarrollo sin un beneficio tangible a corto plazo. La abstracción de `CaptureBackend` ya es suficiente preparación para el futuro.

El ecosistema de seL4, a través del Microkit, ofrece soporte para C/C++ pero con limitaciones importantes, como la ausencia de una biblioteca estándar completa.

**Veredicto**: No es necesario un diseño específico para seL4 en esta fase. Mantener limpia la interfaz `CaptureBackend` (ISP) es la mejor preparación. El esfuerzo de portabilidad a seL4 será inherentemente alto y se abordará como un proyecto de investigación independiente cuando se alcance ese hito.

---

Esperamos que este veredicto guíe vuestros próximos pasos. La rama `feature/variant-b-libpcap` avanza con una solidez arquitectónica ejemplar.

*— Firmado, el Consejo de Sabios en sesión permanente.*