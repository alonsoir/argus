## DeepSeek — Revisión de la Sesión Consolidada (ADR-023 + ADR-024)

El documento consolidado refleja fielmente la diversidad de opiniones y la síntesis alcanzada. La mayoría de mis hallazgos críticos y recomendaciones han sido recogidos en las decisiones D1–D6 y R1–R6, con un nivel de detalle y equilibrio que considero adecuado para avanzar.

A continuación, mis observaciones sobre la versión final:

---

### Fortalezas de la consolidación

- **D1 (degradación elegante)** captura correctamente el matiz de DeepSeek + Grok: ausencia del símbolo + `MLD_DEV_MODE=1` permite escape controlado, pero cualquier fallo de ejecución (result_code != 0) siempre es fail-closed. Es un compromiso razonable entre flexibilidad de desarrollo y seguridad en producción.

- **D2 y D3** documentan ahora las invariantes de seguridad (`channel_id`, `payload`, `direction`, `nonce`, `tag`). Esto cierra la principal laguna de especificación que señalé.

- **D4 (domain separation del info string)** resuelve el riesgo de reutilización de material entre derivaciones HKDF. La string propuesta es suficientemente específica.

- **D5** incorpora las open questions que faltaban (revocación, rotación, replay, perf). Son necesarias antes de la implementación real.

- **D6** especifica el mecanismo de transición atómica de claves en `CryptoTransport`, que era el mayor punto de integración pendiente.

- **R1** (reservado → sequence_number en v2) es una buena forma de aplazar el bump de API sin perder la posibilidad futura.

---

### Observaciones puntuales (no bloqueantes)

1. **D1 – definición de `MLD_DEV_MODE=1`**:  
   El ADR debería especificar que esta variable solo es reconocida si el binario fue compilado sin `NDEBUG` o con una configuración explícita de desarrollo. De lo contrario, un atacante podría forzar el modo degradado en producción estableciendo la variable. Sugiero añadir una nota: “`MLD_DEV_MODE` is only honored when the component was built with `CMAKE_BUILD_TYPE=Debug` or when a compile-time flag `MLD_ALLOW_DEV_MODE` is explicitly set.”

2. **D5 – OQ-7 (replay en primer mensaje)**:  
   El threat model de replay debería especificarse más claramente. Noise_IKpsk3 sin nonce explícito en el primer mensaje permite que un adversario con capacidad de capturar y retransmitir el mensaje `→ e, es, s, ss` pueda forzar un handshake repetido. El PSK binding mitiga porque el adversario no conoce el PSK, pero si el PSK se deriva de un seed estático comprometido, el replay sería exitoso. Debe documentarse que la seguridad asume que el seed_family y el PSK derivado no están comprometidos; si lo están, todo el sistema está comprometido. Eso es aceptable en el threat model actual, pero conviene explicitarlo.

3. **R4 (noise-c vs libsodium puro)**:  
   Se ha registrado como evaluación post-arXiv. Apoyo mantener noise-c para prototipo, pero añadiría una métrica concreta: footprint < 200 KB y latencia handshake < 50 ms en el hardware objetivo. Si no se alcanza, se pasa a libsodium puro.

4. **Nota sobre Qwen**:  
   La observación sobre Qwen autodenominándose DeepSeek es correcta y queda registrada para seguimiento. No afecta la validez técnica.

---

### Veredicto final

**ADR-023:**  
Aceptado con las condiciones D1–D3 incorporadas. El ADR está listo para ser cerrado y pasar a implementación.

**ADR-024:**  
Aprobado como diseño para implementación post-arxiv, condicionado a que se integren D4–D6 y las open questions OQ-5 a OQ-8 queden resueltas antes de codificar. El documento consolidado cumple con esos requisitos, por lo que puede considerarse la base para el trabajo futuro.

En conjunto, la sesión consolidada representa un excelente ejemplo de cómo la metodología del Consejo de Sabios permite refinar diseños complejos con contribuciones diversas y llegar a un consenso robusto. Felicito al árbitro y a los revisores por el resultado.

**— DeepSeek, miembro del Consejo de Sabios**