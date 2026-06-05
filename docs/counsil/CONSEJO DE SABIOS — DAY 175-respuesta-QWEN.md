Estimado Alonso,

El Consejo de Sabios recibe tu parte del **DAY 175** con gran satisfacción. Cablear y verificar E2E el primer eslabón de la Zona Bronce no es un detalle menor; es la materialización de la promesa de arquitectura. Tu filosofía de *"medir, no presuponer"* ha vuelto a demostrar su valor: ese falso verde del provisioning es exactamente el tipo de deuda que, si no se detecta en el día 175, se convierte en un incidente de producción en el día 300.

Felicitaciones por el cierre quirúrgico del pipeline y por mantener el `correlation-engine` limpio de dependencias de protobuf. A continuación, presentamos nuestro análisis y criterio sobre tus tres preguntas.

---

### Respuesta a Q1: Orden de batalla (Injectors vs. Consumidor)

**Criterio del Consejo:** Coincidimos plenamente con tu instinto. **(A) Injectors sintéticos primero.**

**Razonamiento:** La ingeniería de confiabilidad (SRE) dicta que no se debe construir consumo en producción sin antes tener la capacidad de generar carga de prueba determinista y barata. Depender de un replay de `smallFlows.pcap` + sniffer eBPF para validar el pipeline en CI es frágil, lento y no escala. Al corregir primero los injectores sintéticos para que pueblen `community_id`, desbloqueas:
1. Tests de integración rápidos y deterministas en CI.
2. La capacidad de hacer pruebas de estrés (load testing) contra el nuevo `correlation-engine` antes de que este procese datos reales.
3. Un ciclo de feedback más corto para el desarrollo de (B).

> `[SUGERENCIA-ARQUITECTURA-SISTEMAS: Priorizar (A) Injectors Sintéticos. Modificar los injectores para que generen un community_id mock válido (ej. "synth:test:hash") y así el filtro del hook no los descarte, permitiendo validar el ciclo de vida completo del dato en CI sin dependencias de pcap/eBPF.]`

---

### Respuesta a Q2: `authoritative_source` como `int` crudo vs. `string`

**Criterio del Consejo:** En la Zona Bronce, **prioriza la legibilidad y la estabilidad del contrato a largo plazo sobre el ahorro de bytes**. Usa el nombre simbólico (`string`).

**Razonamiento:** La Zona Bronce es el "registro de la verdad" crudo. Si dentro de seis meses el `.proto` cambia y el valor `4` pasa de ser `ML_PRIORITY` a `ANOMALY_SCORE`, cualquier dato histórico en Bronze que solo tenga un `4` se vuelve indescifrable sin consultar el código fuente de esa versión específica (acoplamiento temporal).
Además, dado que el destino final es Parquet (Plata/Oro), los motores columnares aplican *dictionary encoding* de forma nativa. El ahorro de espacio de usar un `int` en lugar de un `string` repetitivo como `"ML_PRIORITY"` es prácticamente nulo tras la compresión, pero el costo en debuggabilidad y autonomía del dato es enorme.

> `[SUGERENCIA-INGENIERIA-DE-DATOS: Escribir `authoritative_source` como `string` en el writer de Bronze. El trade-off de rendimiento es despreciable (es una operación por evento, no un bucle interno de millones de iteraciones), y la robustez del contrato de datos y la facilidad de auditoría futura lo justifican ampliamente.]`

---

### Respuesta a Q3: Modelo de confianza y escalado a N nodos (HMAC vs. Asimétrica)

**Criterio del Consejo:** Has identificado una grieta de diseño crítica. El modelo de secreto compartido (HMAC simétrico) **no escala** a una arquitectura federada (N sensores → 1 Kuzu central).

**Razonamiento:** Gestionar, rotar y distribuir claves simétricas únicas para cada componente en cada nodo periférico (hospitales, ayuntamientos) hacia un centro de correlación es una pesadilla operativa y un riesgo de seguridad (si se compromete la clave central, se comprometen todos los nodos).
La arquitectura debe evolucionar hacia un modelo de **confianza cero (Zero Trust) con firma asimétrica**. El nodo periférico (ml-detector) debe *firmar* el payload de Bronze con su clave privada (Ed25519, que ya tienes en el ecosistema de plugins). El servidor central (correlation-engine) solo necesita la clave *pública* del nodo para verificar la integridad y procedencia. Esto elimina la necesidad de compartir secretos y permite una revocación de nodos comprometidos de forma granular.

> `[SUGERENCIA-SEGURIDAD-Y-CONFIANZA: Redactar un ADR inmediato (`ADR-XXX: Modelo de Confianza Federada para Zona Bronce`). Establecer que el HMAC simétrico es válido SOLO para comunicación intra-nodo (baja latencia), pero que cualquier dato de Bronze que cruce un límite de red hacia un correlator central debe estar firmado con Ed25519. Esto debe ser un requisito no funcional antes de escribir el lado consumidor (B).]`

---

### Nota adicional sobre `DEBT-BRONZE-KEY-PROVISIONING-001`

Tu hallazgo es excelente. Para evitar que esto se repita, te sugerimos modificar el test de round-trip (`test_correlation_roundtrip`). En lugar de hardcodear `KEY_HEX`, el test debería simular el comportamiento de producción: inyectar la clave a través de una variable de entorno o un mock de etcd que ambos lados (writer y reader simulado) consulten. Así, el test valida no solo el contrato de datos, sino también el *mecanismo de obtención de la confianza*.

El bronce corre de verdad. El cimiento está puesto. Mañana, a por los injectors.

Atentamente,  
**El Consejo de Sabios**  
*aRGus NDR*

FDO
QWEN