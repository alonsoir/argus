Mis respuestas como miembro del Consejo:

---

**1. Test de integración wire protocol LE/BE**

El gate E2E es necesario pero no suficiente para este tipo de bug. El problema es que `test-e2e` detecta "fluye o no fluye" pero no "fluye con el formato correcto". Recomiendo añadir un test unitario específico en `crypto-transport` que serialice un payload con LZ4, lo deserialice en el contexto del firewall, y verifique byte a byte que el header es little-endian. Coste: 20 líneas. Beneficio: detecta regresiones de formato sin necesidad de levantar el pipeline. El gate E2E complementa pero no sustituye este test.

---

**2. Modo absoluto vs delta en test-e2e-live**

El modo absoluto tiene el problema que describes — pasa aunque no haya tráfico nuevo. Sin embargo, cambiar a snapshot/delta en `test-e2e-live` introduce otro problema: el snapshot debe tomarse *antes* de que haya tráfico, lo cual requiere saber cuándo empieza el periodo de observación. Mi recomendación: mantener modo absoluto pero añadir una verificación de timestamp — el último stat de ml-detector debe tener timestamp dentro de los últimos 120 segundos. Así garantizamos que hay actividad reciente sin la complejidad del snapshot en un pipeline que lleva horas corriendo.

---

**3. DEBT-ALERTING-LIBCRYPTO-PROVIDER-001 — prioridad FEDER**

P2, no P0. El argumento es que para FEDER lo crítico es demostrar detección y respuesta, no notificación. etcd-server ya alerta correctamente — si se detecta un AUTONOMOUS event, la alerta llega. Que el firewall o ml-detector no puedan alertar directamente es una limitación operacional, no una limitación de seguridad. Post-FEDER tiene sentido resolverlo porque en producción real querrás alertas granulares por componente. Pero bloquear el merge o el roadmap FEDER por esto sería desproporcionado.

---

**4. Auto-adaptación completa del ml_output_injector**

No recomiendo leer compression y encryption desde JSON en el injector. La razón: esos parámetros están acoplados al CryptoTransport que ya inicializa el injector desde el JSON oficial. Si compression está en true en el JSON pero el injector no lo lee, falla — pero eso ya está resuelto porque el injector usa exactamente el mismo código de serialización que ml-detector (LZ4 LE + CryptoTransport). El único parámetro que realmente cambia entre despliegues es el endpoint ZMQ, que ya leemos. Leer más parámetros añade complejidad sin beneficio real porque el código de crypto/compresión ya es el canónico.

---

**5. Paralelización de test-e2e en Jenkins**

No paralelizar. La dependencia de estado compartido es real y peligrosa: `test-e2e-synthetic-full` para el sniffer, `test-e2e-synthetic-firewall` para sniffer+ml-detector, y si corren en paralelo los estados se interfieren. El riesgo de falsos negativos es alto. La solución correcta para Jenkins es dividir en dos jobs secuenciales: `test-all` (paralelizable por componente) y `test-e2e` (secuencial, siempre). 90 minutos es aceptable para un gate de merge — no es un test de desarrollo diario sino un gate de calidad. Si en el futuro se necesita acortar, la opción correcta es reducir los `sleep` usando polling activo de logs en vez de tiempos fijos.

---

Cuando tengas el feedback del Consejo, los docs y el README, continuamos.