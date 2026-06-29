## DeepSeek — Retroalimentación DAY 103

Buen trabajo en la alineación del Makefile y en la redacción de la subsección §5 del paper. El caso de estudio HKDF Context Symmetry ha quedado muy bien explicado y será un valor añadido para los revisores. Además, aplaudo que hayáis sido honestos sobre el bloqueo del bare-metal por disponibilidad de hardware y replanificado en consecuencia.

Entro ahora en las preguntas.

---

### Q1 — ADR-023: Separación de contextos por capa

**Recomendación:** La separación en tres capas (red, transporte, aplicación) es **correcta y necesaria**. No hay caso donde mezclarlas sea preferible, porque violaría la separación de responsabilidades y reproduciría el error de modelo mental que ya documentaste en el paper.

**Sobre la definición de `MessageContext`:**

- **Campos que están bien:** `payload`, `length`, `max_length`, `direction`, `nonce`, `tag`, `result_code`. Cubren las necesidades de un plugin de cifrado simétrico.
- **Posible campo faltante:** `uint32_t message_id` (opcional). Útil para depuración y para plugins que necesiten ordenamiento o detección de repetición. No es crítico para PHASE 2a, pero podrías añadirlo como reservado para uso futuro (ej: `reserved[4]`).
- **Campo que sobra:** Ninguno. `result_code` es necesario para que el plugin comunique errores (MAC failure, buffer insuficiente, etc.) al componente host.

**Mejora sugerida:** Añadir un campo `uint8_t version` al inicio de `MessageContext` para permitir evoluciones futuras de la estructura sin romper ABI. El componente host lo llena con `sizeof(MessageContext)` o con una constante `MESSAGE_CONTEXT_VERSION = 1`. Esto es una precaución barata.

---

### Q2 — ADR-023 PHASE 2a: `plugin_process_message` opcional vs obligatorio

**Recomendación:** **Opcional vía `dlsym` + `PLUGIN_API_VERSION` sin incrementar en PHASE 2a**. Es la estrategia correcta por las siguientes razones:

| Enfoque | Ventajas | Inconvenientes |
|---------|----------|----------------|
| **Opcional (propuesto)** | Migración gradual sin romper plugins existentes; permite PHASE 2a dual-mechanism; el core CryptoTransport actúa como respaldo. | Mayor complejidad temporal (dos caminos). |
| **Obligatorio (bump a v2)** | API limpia desde el inicio; no hay dual-mechanism. | Rompe todos los plugins existentes (aunque solo sea hello plugin); obliga a migrar todo de golpe; más riesgo. |

Dado que en PHASE 2a el core CryptoTransport se mantiene como respaldo (read-only), tener el símbolo opcional es natural. El loader simplemente comprueba si existe; si no, el componente sigue usando el core. La complejidad añadida es mínima.

**Recomendación adicional:** En PHASE 2a, el componente host debe loguear en nivel INFO si el plugin implementa `plugin_process_message` o no. Esto ayuda a diagnosticar despliegues mixtos.

---

### Q3 — ADR-024: Protocolo de Group Key Agreement

**Recomendación:** **Opción A (Noise Protocol IK) con libsodium.** Es la más equilibrada entre seguridad, especificación y madurez de implementación.

**Razonamiento detallado:**

- **Noise IK** (Interactive Key agreement) asume que el nuevo componente tiene una clave pública estática conocida por la familia (pre-provisionada) y que el miembro existente tiene su propia clave estática. El handshake es de 2 mensajes (initiator → responder → responder → initiator) y produce una clave simétrica compartida con forward secrecy. Es ideal para un componente que se une a una familia conocida.
- **Compatibilidad con libsodium:** libsodium no implementa Noise directamente, pero hay implementaciones en C/C++ (ej: libnoise, or zig) que se pueden integrar. Si prefieres no añadir dependencias, puedes implementar un handshake más simple basado en X25519 + HKDF (similar a Noise pero sin el formato de mensajes). El esfuerzo es asumible.
- **Por qué no B (HKDF estático):** No ofrece forward secrecy. Si el material estático se compromete, todas las comunicaciones pasadas y futuras están comprometidas. Para un sistema que puede operar durante años en hospitales, no es aceptable.
- **Por qué no C (propuesta propia):** Riesgo de errores de diseño criptográfico. Mejor usar un protocolo estandarizado y auditado.

**Alternativa no mencionada:** **Signal Double Ratchet** es overkill para este caso (grupos pequeños, unión ocasional). Noise IK es suficiente.

**Decisión:** ADR-024 debe especificar Noise IK como protocolo base, con opción de usar una implementación ligera propia si no se quiere añadir una dependencia grande.

---

### Q4 — Secuenciación: ADR-023 vs ADR-024

**Recomendación:** **Diseñar ADR-024 en paralelo (ahora), pero implementar ADR-023 primero.**

**Razonamiento:**
- ADR-023 es la base arquitectónica (plugins multicapa). Sin ella, ADR-024 no tiene dónde apoyarse (el plugin de cifrado necesita `MessageContext`).
- ADR-024 puede diseñarse en paralelo porque es conceptualmente independiente: especifica *cómo* se distribuyen las claves, no *dónde* se inyectan. Pero su implementación debe esperar a que ADR-023 esté estable.
- Dado que ambos son post-arXiv, puedes redactar ambos ADR ahora, pero en el roadmap prioriza la implementación de ADR-023 (FEAT-PLUGIN-CRYPTO-1) en DAY 105-110, y deja ADR-024 para DAY 111+.

**Propuesta de plan:**
- **Antes de arXiv (ahora):** Redactar ADR-024 como documento de diseño, con nivel de detalle suficiente para que quede claro en el paper (sección de trabajo futuro). Incluir la elección de Noise IK.
- **Después de arXiv:** Implementar ADR-023 (MessageContext + plugin opcional). Una vez validado, implementar ADR-024 como un plugin específico que implementa Noise IK para la unión de nuevos miembros a la familia.

---

### Comentarios adicionales sobre el DAY 103

- **Makefile rag alignment:** Las 6 correcciones son sólidas. Especialmente importante que ahora `rag-build` respete `CMAKE_FLAGS` (Debug/TSan/ASan) y que `rag-attach` exista para depuración.
- **Paper §5:** La subsección sobre HKDF Context Symmetry es clara y bien argumentada. Un pequeño detalle: asegúrate de que la descripción de TEST-INTEG-3 sea autocontenida (no requiera leer el código fuente para entender el mecanismo). Menciona que el test se compila en dos versiones (contexto correcto vs erróneo) y que el fallo se manifiesta como `std::terminate()`.
- **Backlog bare-metal:** La decisión de desbloquearlo a P2 y añadir tareas de imagen Vagrant es pragmática. Documenta en el paper que los resultados de throughput se obtuvieron en VirtualBox y que bare-metal es trabajo futuro (como ya haces en §11.11).

---

### Resumen de decisiones del Consejo (DAY 103)

| Pregunta | Decisión |
|----------|----------|
| Q1 | Separación de contextos correcta. Añadir campo `version` a `MessageContext` como precaución ABI. |
| Q2 | `plugin_process_message` opcional en PHASE 2a (dlsym). PLUGIN_API_VERSION se mantiene en 1. |
| Q3 | ADR-024: Noise Protocol IK (o implementación ligera equivalente) con libsodium. |
| Q4 | Diseñar ADR-024 en paralelo, pero implementar ADR-023 primero. Ambos post-arXiv. |

El proyecto está en una excelente trayectoria. El paper v7 con la subsección de caso de estudio será un referente de transparencia y rigor. Adelante.

— DeepSeek, miembro del Consejo de Sabios