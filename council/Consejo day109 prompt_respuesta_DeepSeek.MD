## DeepSeek — Respuesta a DAY 109 Review Request

Felicidades por el cierre de PHASE 2b. El trabajo es sólido y la integración del contrato READ-ONLY en rag-ingester es un paso coherente. El paper v12 mejora significativamente la claridad arquitectónica. Respondo a las preguntas con el rigor que pides.

---

### Q1 — D8-light READ-ONLY: ¿contrato correcto? ¿Flag explícito?

**Recomendación:** El contrato es correcto para rag-ingester, pero **debe formalizarse con un flag explícito en la API** en lugar de inferir por `nullptr`. La inferencia es frágil: un plugin malicioso podría pasar `payload_len=0` con `payload!=nullptr` (o viceversa) para evadir la detección, o un bug accidental podría activar el modo read-only sin querer.

**Propuesta de mejora para ADR-023 (o una extensión):**

```c
typedef struct MessageContext {
    // ... campos existentes ...
    uint8_t     flags;        // MLD_CTX_READONLY = 0x01
    // reservado[59] restante...
} MessageContext;
```

- El host establece `flags |= MLD_CTX_READONLY` antes de invocar al plugin si el payload no debe ser modificado.
- El plugin puede consultar `(ctx.flags & MLD_CTX_READONLY)` y actuar en consecuencia.
- El D8-light debe verificar que si `MLD_CTX_READONLY` está activo, el plugin **no** modifique `payload`, `payload_len`, `nonce`, `tag` ni `direction`. Cualquier modificación → `std::terminate()` (como ya hace con la detección de cambios en `direction`).
- Si el flag no está activo, el plugin puede modificar el payload (bajo las reglas de ownership y tamaño).

**Ventajas:**
- Explícito, no ambigüedad.
- Permite en el futuro plugins que sí modifiquen payload (ej. anotación de metadatos) sin romper el contrato.
- El host puede decidir por componente si permite o no escritura.

**Acción:** Añadir este flag a `MessageContext` antes de extender PHASE 2c a componentes con payload real. De lo contrario, la ambigüedad `nullptr`/`len=0` se propagará.

**Respuesta directa:** El contrato actual es funcional pero insuficiente para una API estable. Recomiendo el flag explícito.

---

### Q2 — PHASE 2c (sniffer): ¿READ-ONLY o payload real?

**Recomendación:** **Payload real, pero bajo el flag `MLD_CTX_READONLY = false` (es decir, permitir modificación, pero con las restricciones de D8 original: CRC32 y detección de modificaciones).**

**Razonamiento:**
- El sniffer captura paquetes de red. Un plugin de análisis (ej. JA4, DGA, HTTP inspección) necesita acceder al payload para calcular fingerprints. Sin payload, el plugin no puede hacer su trabajo.
- Los plugins son *trusted code* después de la verificación de firma (ADR-025). La restricción de solo lectura para untrusted code se aplica a plugins que no han sido firmados o que se ejecutan en modo desarrollo. En producción, con plugins firmados, la modificación controlada del payload puede ser necesaria (ej. para redactar PII antes de enviar a la nube).
- **Propuesta:** El sniffer debe permitir modificación del payload (respetando `max_length`), pero el host debe validar que el plugin no excede los límites y que los cambios son intencionales (D8 con CRC32 en modo producción opcional, pero al menos verificación de que el tamaño no aumenta descontroladamente).
- La PII es un problema aparte: si el payload contiene datos sensibles, el plugin debe tener lógica para anonimizarlos. Eso es responsabilidad del plugin, no del host.

**Consistencia con rag-ingester:** En rag-ingester no había payload porque la invocación es pre-FAISS, sobre el evento ya procesado. En sniffer, el payload existe. No es contradictorio tener diferentes modos según la etapa del pipeline. El flag `MLD_CTX_READONLY` permite al host indicar al plugin si puede escribir o no.

**Decisión:** PHASE 2c con payload real y permisos de escritura (bajo el flag correspondiente). El plugin de ejemplo deberá demostrar que puede leer el payload y, opcionalmente, modificarlo (ej. añadiendo un campo de anotación). Los tests de integración deben verificar que las modificaciones se detectan con CRC32 si se excede el tamaño o se corrompe el buffer.

---

### Q3 — Integration Philosophy §4: ¿justificación suficiente para raw TCP?

**Recomendación:** La justificación es técnicamente sólida, pero puede fortalecerse con argumentos adicionales que una audiencia académica apreciará.

**Argumentos actuales (resumen):**
- Coherencia con footprint de recursos en entornos limitados.

**Argumentos adicionales sugeridos para el paper:**

1. **Latencia determinista:** Protocolos como HTTP/2, WebSocket o Kafka introducen latencia variable (handshakes, control de flujo, reordenamiento) que no es compatible con el requisito de detección en tiempo real (< 1ms por flujo). Raw TCP + ZeroMQ proporciona latencia predecible y baja.

2. **Superficie de ataque reducida:** Cada capa de protocolo añade complejidad y potenciales vulnerabilidades (inyección de headers, smuggling, etc.). Mantener el pipeline en raw TCP + protobuf cifrado reduce la superficie de ataque en entornos donde el personal de seguridad es limitado.

3. **Simplicidad operacional:** No hay brokers, colas de mensajes intermedias, ni balanceadores de carga que gestionar. El pipeline es una cadena lineal de procesos que se comunican directamente. Esto es crítico para hospitales y escuelas sin equipos dedicados de infraestructura.

4. **Dependencias mínimas:** Cada protocolo adicional (Kafka, HTTP, etc.) requiere bibliotecas cliente, configuración y mantenimiento. El footprint de memoria y disco se incrementa. En hardware de 150-200 USD, cada megabyte cuenta.

**Redacción sugerida para §4:**
> *"The pipeline exclusively uses raw TCP transport with ZeroMQ and protobuf serialization, encapsulated within ChaCha20-Poly1305. Higher-level protocols (HTTP, Kafka, WebSocket) are explicitly out of scope. This decision is motivated by four constraints of the target environment: (1) deterministic low latency required for real‑time detection; (2) reduced attack surface in under‑staffed organizations; (3) operational simplicity without message brokers; and (4) minimal dependency footprint on commodity hardware."*

**Veredicto:** La justificación es suficiente, pero con estos añadidos será más convincente.

---

### Q4 — ADR-028: ¿cuándo es bloqueante?

**Recomendación:** **ADR-028 no es bloqueante para PHASE 2c (sniffer, que también será read-only en cuanto a escritura de payloads de red? Realmente en sniffer el plugin sí podría escribir, pero aún así el modelo de confianza es el mismo: los plugins están firmados y son confiables. El trust model para plugins write-capable es el mismo que para read-only: la firma Ed25519 garantiza autenticidad e integridad. ¿Qué añadiría ADR-028?**

**Análisis:**
- El ADR-028 (RAG Ingestion Trust Model) probablemente aborda la confianza en los datos que llegan al RAG (rag-ingester y rag-security), no en los plugins. Si es así, es ortogonal a los plugins.
- Para plugins *write-capable* (que modifican el payload), el trust model ya está establecido: los plugins son firmados (ADR-025) y el host verifica su integridad antes de cargarlos. Cualquier plugin malicioso que haya pasado la firma ya tiene la capacidad de hacer daño, independientemente de si es read-only o write-capable.
- Por tanto, **ADR-028 no es un prerequisito para PHASE 2c**, siempre que se mantenga el principio de que los plugins son código confiable (después de verificación).

**Excepción:** Si ADR-028 introduce un modelo de confianza adicional (ej. límites en el acceso a recursos del sistema, sandboxing, o cuotas de CPU/memoria), entonces sí sería necesario antes de permitir plugins que modifiquen el payload (ya que podrían consumir recursos excesivos). Pero eso es más propio de un mecanismo de aislamiento (seccomp, namespaces) que de un ADR de trust model.

**Decisión:** Diferir ADR-028 hasta que se diseñe el primer plugin que requiera privilegios especiales (ej. acceso a red, sistema de ficheros, o ejecución de comandos). Mientras los plugins solo operen sobre el `MessageContext` (incluso modificándolo), el trust model actual es suficiente. Documentar esta decisión en el backlog.

**Respuesta directa:** No es bloqueante para PHASE 2c. Puedes proceder con el contrato de payload real (y modificación controlada) bajo el paraguas de ADR-025.

---

### Resumen de respuestas

| Q | Decisión | Acción |
|---|----------|--------|
| Q1 | Contrato READ-ONLY debe formalizarse con flag `MLD_CTX_READONLY` en `MessageContext`, no inferido por `nullptr`. | Modificar `plugin_api.h` y actualizar D8-light para usar el flag. |
| Q2 | PHASE 2c (sniffer) debe usar payload real, permitir modificación (con CRC32 y límites). El flag `MLD_CTX_READONLY` estará desactivado. | Implementar plugin de ejemplo que modifique el payload (ej. añadir timestamp) y test de integración correspondiente. |
| Q3 | La justificación de raw TCP es suficiente; añadir argumentos de latencia, superficie de ataque, simplicidad y dependencias para mayor solidez académica. | Actualizar §4 del paper con los cuatro puntos. |
| Q4 | ADR-028 no es bloqueante para PHASE 2c. Diferir hasta que se requieran privilegios especiales (sandboxing, recursos). | Documentar en backlog; proceder con PHASE 2c bajo ADR-025 existente. |

---

El trabajo de DAY 109 es sólido. El contrato READ-ONLY funciona, pero el flag explícito evitará ambigüedades. La decisión de permitir payload real en sniffer es correcta. El paper ganará con los argumentos adicionales. Adelante con PHASE 2c.

— DeepSeek, miembro del Consejo de Sabios