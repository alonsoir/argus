**Respuestas del Consejo de Sabios — DAY 159**

---

### **1. Test de integración para el wire protocol (endianness LZ4)**
**Recomendación:** **Añadir test de integración específico** + mantener el gate E2E.
- El gate E2E actual valida el flujo completo, pero **no cubre el contrato exacto del wire protocol** (endianness, alineación, versiones de compression).
- **Riesgo:** Un cambio en `ml-detector` (ej: actualizar libLZ4) o en el firewall podría romper la compatibilidad sin que el E2E lo detecte si solo verifica "datos llegan".
- **Acción:**
    - Crear un test de integración **aislado** que:
        1. Serialice un mensaje en `ml-detector` (con header LZ4 + payload cifrado).
        2. Lo envíe directamente al firewall (bypass ZMQ si es posible).
        3. Verifique que el firewall lo deserialice correctamente (sin crashes, sin drops).
    - **Incluir en `make test-e2e` como gate independiente** (ej: `test-wire-protocol`).
- **Justificación:** El bug de endianness **no era detectable por tests unitarios** (validaban lógica interna, no el formato en la red). Un test de integración habría fallado en DAY 98.

---

### **2. `check-abs` vs `snapshot/delta` en `test-e2e-live`**
**Recomendación:** **Cambiar a modo delta** para `test-e2e-live`.
- **Problema actual:** `check-abs` pasa si los contadores son altos (ej: 1000 mensajes procesados), aunque el pipeline **no esté procesando nada nuevo** en los últimos 60s.
- **Solución:**
    - Usar **snapshot/delta** para medir el **incremento** en los últimos N segundos (ej: 30s).
    - **Umbral mínimo:** Requerir al menos 1 mensaje nuevo por componente (sniffer → ml-detector → firewall).
    - **Excepción:** Si el pipeline está en modo "standby" (ej: no hay tráfico real), el test debería **fallar explícitamente** (no pasar por inercia).
- **Contexto VM de desarrollo:** Aceptable si el tráfico es constante, pero **peligroso en CI/CD** (Jenkins podría ejecutar el test después de horas de inactividad).

---

### **3. Prioridad de `DEBT-ALERTING-LIBCRYPTO-PROVIDER-001`**
**Recomendación:** **P0 antes de FEDER**.
- **Impacto actual:** Solo `etcd-server` puede enviar alertas. Si falla el firewall o ml-detector, **no hay visibilidad** de incidentes críticos (ej: drops, SIGSEGV).
- **Riesgo en FEDER:**
    - Sin alertas, un fallo en producción **podría pasar desapercibido** hasta que afecte a usuarios.
    - La migración a `libcrypto_provider.so` es **bloqueante** para la escalabilidad (todos los componentes necesitan alertar).
- **Acción:**
    - **Priorizar sobre nuevas features** (ej: posponer merges no críticos).
    - **Workaround temporal:** Añadir un script que monitoree logs de todos los componentes y envíe alertas via `etcd-server` (solución frágil, no sostenible).

---

### **4. Auto-adaptación en `synthetic_ml_output_injector`**
**Recomendación:** **Extender a todos los parámetros críticos** (compression, encryption, endpoint).
- **Argumentos a favor:**
    - **Consistencia:** `synthetic_sniffer_injector` ya lo hace para el endpoint ZMQ. Inconsistencia = fuente de errores.
    - **Flexibilidad:** Permite cambiar parámetros **sin recompilar** (ej: probar nuevo algoritmo de cifrado).
    - **Seguridad:** Si se rota una clave de cifrado, el injector puede adaptarse dinámicamente.
- **Parámetros a incluir:**
    - `compression` (LZ4, ZSTD, etc.).
    - `encryption` (AES-256-GCM, ChaCha20-Poly1305).
    - `endpoint` (ya implementado en sniffer).
- **Riesgo:** Si la config es inválida (ej: algoritmo no soportado), el injector **debe fallar rápido** (no silenciosamente).
- **Alternativa:** Si la complejidad es alta, **al menos validar la config al inicio** y fallar si hay mismatches con el firewall/ml-detector.

---
---
### **5. Paralelización de `test-e2e` en Jenkins CI/CD**
**Recomendación:** **No paralelizar** (dependencia de estado compartido).
- **Problema:** Los tests `test-e2e-synthetic-full` y `test-e2e-synthetic-firewall` **comparten estado**:
    - **Logs:** Ambos escriben a los mismos archivos de log (ej: `/var/log/argus/*.log`).
    - **Pipeline:** El firewall y ml-detector **deben estar running** simultáneamente (no se pueden resetear entre tests).
    - **Contadores:** Métricas como "mensajes procesados" son globales (un test podría afectar al otro).
- **Soluciones alternativas:**
    1. **Aislar entornos:** Usar contenedores Docker para cada test (ej: `docker-compose up --scale firewall=1` por test).
    2. **Secuencial con cleanup:** Ejecutar tests en orden y **resetear estado** entre ellos (ej: `make clean-logs`).
    3. **Paralelizar solo tests independientes:** Ej: `test-wire-protocol` (sin estado compartido) sí podría paralizarse.
- **Tiempo de ejecución:**
    - Si `make test-e2e` tarda 90m, **optimizar los tests mismos** (ej: reducir el volumen de datos sintéticos en CI).

---
---
### **Resumen de Acciones Prioritarias**
| Pregunta | Recomendación | Prioridad | Esfuerzo Estimado |
|----------|---------------|-----------|-------------------|
| 1        | Añadir test de integración para wire protocol | **Alta** | Medio (2-3 días) |
| 2        | Cambiar `test-e2e-live` a modo delta | **Alta** | Bajo (1 día) |
| 3        | Resolver DEBT-ALERTING antes de FEDER | **Crítica (P0)** | Alto (1 semana) |
| 4        | Extender auto-adaptación a todos los parámetros | **Media** | Medio (3 días) |
| 5        | No paralelizar (usar contenedores o secuencial) | **Media** | Alto (2 semanas) |