Basado en el análisis de la lógica técnica del proyecto y las prioridades marcadas, procedo a responder las preguntas del Consejo para el DAY 159:

---

### 1. Bug de endianness: ¿Test de integración del wire protocol o suficiente con el gate E2E?

**Recomendación:** Añadir un test de integración específico para el wire protocol, complementario al gate E2E.

El gate E2E es excelente para validar que el flujo de datos funciona en conjunto, pero el bug de endianness demuestra un riesgo muy concreto: una discrepancia en la representación binaria de los mensajes entre dos componentes (ml-detector y firewall). Un test unitario/de integración centrado exclusivamente en el formato binario del header LZ4 capturaría este tipo de fallos de manera más temprana y determinista, sin necesidad de esperar a una ejecución E2E completa.

**Propuesta concreta:** Un test que serialice un header con ml-detector (o su lógica de serialización) y lo deserialice con el código del firewall, comprobando la correcta interpretación de los bytes y la coincidencia del tamaño de datos descomprimidos. Este test sería de ejecución rápida y se añadiría a la batería de tests unitarios existentes.

---

### 2. Modo `check-abs` vs `snapshot/delta` en `test-e2e-live`

**Recomendación:** Usar snapshot/delta para `test-e2e-live`, manteniendo el modo absoluto para otros contextos.

El problema descrito es real: en una VM de desarrollo que lleve horas ejecutándose, los contadores acumulados pueden enmascarar la ausencia de tráfico reciente. El test no detectaría un pipeline detenido si los valores históricos son altos.

La solución más robusta es tomar una instantánea (snapshot) de los contadores al inicio del test y verificar que los deltas (incrementos) durante la ventana de observación son coherentes con el tráfico sintético inyectado. Esto garantiza que el pipeline está procesando activamente en el momento del test, no solo que ha procesado en el pasado.

---

### 3. Prioridad de `DEBT-ALERTING-LIBCRYPTO-PROVIDER-001`

**Recomendación:** P0 antes de FEDER.

La deuda indica que actualmente solo `etcd-server` puede enviar alertas a Discord/Telegram. Para un sistema de seguridad como ARGUS, la capacidad de alerta es un habilitador crítico. Si el firewall o el ml-detector no pueden notificar eventos de seguridad en tiempo real, se pierde una capacidad fundamental de respuesta ante incidentes.

Centralizar la lógica de alerta en `libcrypto_provider.so` (que ya maneja la criptografía del sistema) es una decisión arquitectónica sólida que permitirá a todos los componentes notificar eventos de manera uniforme y segura. Esto debe estar implementado antes de FEDER para que el sistema tenga capacidades de alerta completas durante las pruebas de campo.

---

### 4. Auto-adaptación del `synthetic_ml_output_injector`

**Recomendación:** Dotar al injector de la misma capacidad de auto-adaptación para todos sus parámetros (compresión, cifrado), no solo para el endpoint.

El principio de diseño es simétrico: si el `synthetic_sniffer_injector` se adapta dinámicamente a cambios en `sniffer.json`, el `synthetic_ml_output_injector` debe hacer lo mismo con su configuración. La lógica es idéntica: el injector sintético debe reflejar el comportamiento real del componente que emula.

Si la configuración de compresión o cifrado cambia en el pipeline real, el injector sintético debe adaptarse automáticamente para generar tráfico de prueba válido. De lo contrario, los tests sintéticos dejarán de ser representativos en cuanto se modifique algún parámetro de la cadena de procesamiento, creando una nueva clase de bugs silenciosos similar al que se acaba de cerrar (61 días invisible).

---

### 5. Paralelización de `test-e2e-synthetic-full` y `test-e2e-synthetic-firewall` en Jenkins

**Recomendación:** No paralelizar estos dos tests en la misma VM o entorno compartido.

La razón principal es la dependencia de estado compartido: ambos tests inyectan tráfico sintético en el mismo pipeline, consultan los mismos logs y verifican contadores que se modifican de forma concurrente. Si se ejecutan en paralelo, los resultados de un test pueden contaminar los del otro, generando falsos positivos o falsos negativos difíciles de depurar.

**Alternativas para reducir el tiempo total (~90 min):**
- Ejecutar los tests de forma secuencial pero en VMs independientes (una VM por test) si se dispone de infraestructura.
- Paralelizar únicamente los tests que no comparten estado (por ejemplo, `test-e2e-synthetic-firewall` y `test-unit`).
- Optimizar la duración de los propios tests reduciendo ventanas de espera o volúmenes de tráfico sintético, si la cobertura lo permite.

La integridad de los resultados de CI/CD es prioritaria sobre el tiempo de ejecución, especialmente en un sistema de seguridad que se prepara para el hito FEDER.