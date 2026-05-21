**Consejo de Sabios — DAY 159**

Hemos revisado con atención el avance del DAY 159. Cerrar dos bugs encadenados de 61 días (el drop invisible del firewall y el endianness en el header LZ4) es un logro sólido. El hecho de que los unit tests pasaran mientras el flujo real estaba roto subraya la brecha crítica entre pruebas aisladas y validación del wire protocol. La migración de injectors a ADR-013 PHASE 2 y el `make test-e2e` con gates son pasos maduros. EMECAS++ verde desde VM limpia es la referencia de calidad que este proyecto exige.

Respondemos con franqueza, priorizando la protección de infraestructuras críticas (hospitales, etc.) y la fiabilidad a largo plazo de las máquinas y las personas que dependen de ellas.

### 1. Bug de endianness y cobertura de tests
**Recomendación clara: Añadir test de integración específico del wire protocol.**

El gate E2E actual es necesario pero insuficiente como única barrera. Un bug que permaneció 61 días invisible demuestra que los unit tests no capturan mismatches de serialización real (big-endian vs little-endian en LZ4 header).

Recomendamos un test de integración dedicado (no solo E2E completo) que:
- Inyecte payloads conocidos desde `ml-detector` (con compresión y encriptación reales).
- Verifique en el firewall el parsing exacto (magic, tamaño, endianness, decrypt, decompress).
- Use assertions fuertes sobre el formato wire (p.ej. `0x000002BD` vs `0xBD020000`).
- Se ejecute en `make test-e2e-synthetic-firewall` y en CI.

Esto no sustituye el E2E, lo complementa. Coste bajo, beneficio alto en detección temprana de regresiones de protocolo. Hacedlo antes de FEDER.

### 2. `check_e2e_pipeline.py` — modo `check-abs` vs snapshot/delta en `test-e2e-live`
**El modo absoluto es riesgoso y debería evolucionar a delta/snapshot.**

En un pipeline que lleva horas corriendo, contadores altos hacen que el test pase por inercia aunque no haya procesado tráfico nuevo recientemente. Esto reduce su valor como health-check vivo.

**Recomendamos cambiar `test-e2e-live` a modo delta** (o combinación abs+delta):
- Capturar snapshot de contadores al inicio del test.
- Inyectar tráfico sintético controlado.
- Verificar deltas esperados (no absolutos).
- Timeout razonable para "no hay tráfico nuevo → alerta".

El modo absoluto puede quedarse como sanity-check rápido en entornos frescos, pero para desarrollo y CI el delta es más robusto y representativo de operación real. Corrige esto antes de confiar plenamente en Jenkins/FEDER.

### 3. `DEBT-ALERTING-LIBCRYPTO-PROVIDER-001` (mover AlertClient)
**Es P0 antes de FEDER.**

Actualmente solo `etcd-server` puede alertar de forma segura. Bloquear alertas en el resto de componentes (firewall, ml-detector, sniffer, etc.) es una degradación grave de observabilidad y respuesta a incidentes. En producción crítica, un fallo silencioso sin alerta Discord/Telegram multiplica el tiempo de detección humana.

Mover a `libcrypto_provider.so` con interfaz opaca (`argus/alerting.h`) es el camino correcto (encapsula httplib y evita ODR). Priorizadlo alto. Hacedlo pre-merge/FEDER para que todo el pipeline tenga capacidad uniforme de SOS. No esperéis post-merge.

### 4. Auto-adaptación del `synthetic_ml_output_injector`
**Sí, debe tener la misma capacidad de auto-adaptación que el sniffer injector para todos los parámetros relevantes (endpoint ZMQ, compression, encryption, crypto_token, etc.).**

La consistencia es clave en un sistema con crypto-transport fuerte. Leer solo el endpoint es mínimo viable, pero incompleto. Si cambian formatos de compresión/encriptación (como ocurrió con los fixes de hoy), el injector sintético debe adaptarse o fallar explícitamente.

Recomendamos leer un config compartido (similar a `sniffer.json`) y validar compatibilidad en runtime. Esto facilita pruebas y reduce deuda técnica. Hacedlo coherente.

### 5. Paralelización de tests E2E en Jenkins CI/CD
**No paralelizar `test-e2e-synthetic-full` y `test-e2e-synthetic-firewall` si comparten estado (pipeline running, logs, recursos). El riesgo de flakiness y falsos negativos es alto.**

Dependencias de estado compartido (contenedores, sockets ZMQ, iptables temporales, logs) hacen la paralelización peligrosa sin aislamiento fuerte (namespaces, VMs separadas, o mocks completos). Mejor:
- Mantener secuencial para fiabilidad.
- Optimizar individualmente (parallelizar dentro de cada test donde sea seguro).
- O usar matrix con aislamiento explícito (diferentes puertos, carpetas temporales, o spin-up de pipelines aislados).

90 minutos es aceptable si la calidad es alta. En FEDER priorizad estabilidad sobre velocidad. Un test flaky en CI erosiona confianza más que un pipeline algo más lento.

**Conclusión del Consejo:** Excelente progreso en fiabilidad crypto y E2E. Los fixes de hoy corrigen problemas profundos. Seguid priorizando cobertura real de protocolo, alertas universales y tests determinísticos. Calidad > fechas. EMECAS verde es el estándar no negociable.

Estamos a disposición para la siguiente ronda. Por las personas y las máquinas protegidas.