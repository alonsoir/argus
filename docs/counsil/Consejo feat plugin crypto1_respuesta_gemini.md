Alonso, el **Consejo de Sabios** se reúne para una sesión de diseño preventivo. Estás planteando el "Cruce de Caminos" clásico en el desarrollo de plataformas: **Pureza Arquitectónica (Opción A)** frente a **Conveniencia de Retrocompatibilidad (Opción B)**.

Tras analizar las implicaciones en el modelo de amenazas (ADR-022) y la escalabilidad del sistema, el Consejo emite el siguiente dictamen:

---

### 🛡️ Resolución del Consejo — Consulta FEAT-PLUGIN-CRYPTO-1

#### Q1 — Elección: Opción A (API Limpia / MessageContext)
**Veredicto: El Consejo recomienda unánimemente la Opción A.**
* **Razonamiento:** ML Defender no es solo un software; es una arquitectura de referencia para redes críticas. Mezclar capas de Red (L3/L4) y Transporte (L5+) en un `PacketContext` (Opción B) crearía una deuda técnica "radioactiva" que dificultaría la implementación futura de protocolos como **Noise** o **WireGuard-in-userspace**.
* **La "Capa de Abstracción":** Un plugin de cifrado no necesita saber nada de IPs o puertos; solo necesita bytes y un nonce. Forzarle a recibir un `PacketContext` viola el principio de **Privilegio Mínimo** de datos: el plugin solo debe ver lo que necesita transformar.

#### Q2 — Gestión del Breaking Change (Opción C: El Enfoque Híbrido)
**Veredicto: Símbolos Opcionales con `PLUGIN_API_VERSION` estático.**
No es necesario un "Breaking Change" traumático si usamos la flexibilidad de `dlsym`.
* **Mecánica Sugerida:**
  1.  Mantener `PLUGIN_API_VERSION = 1`.
  2.  El `PluginLoader` intenta cargar `plugin_process_packet`. Si existe, lo registra en la cadena de análisis de red.
  3.  El `PluginLoader` intenta cargar `plugin_process_message`. Si existe, lo registra en la cadena de transporte/cifrado.
* **Resultado:** Un plugin puede implementar **uno, otro o ambos**. Esto permite que un plugin de "Detección de Anomalías" (Red) y un plugin de "Cifrado Post-Quantum" (Transporte) convivan sin que el primero tenga que implementar funciones de cifrado vacías.

#### Q3 — Estrategia de Migración y Riesgos
**Veredicto: La estrategia PHASE 2a/2b/2c es correcta, pero con un matiz de Seguridad.**
* **El Riesgo de la Dualidad:** Durante la PHASE 2a (Dual-Mechanism), existe el riesgo de "Doble Cifrado" o "Doble Latencia".
* **Recomendación:** El core de cada componente debe tener un **"Internal Crypto Fallback"**. Si no se carga ningún plugin de cifrado válido, el sistema debe usar el `CryptoTransport` interno (Fail-Closed). Solo cuando el plugin esté validado, se desactiva el interno.

---

### 🏛️ Restricciones y Fail-Closed (ADR-022)

1.  **Cifrado != Filtrado:** El plugin de cifrado **NO** decide si un mensaje pasa o no (política), solo asegura su integridad/privacidad. Por tanto, no viola la restricción de "decisión de bloqueo" de los plugins de la PHASE 1.
2.  **Fail-Closed Absoluto:** Si el plugin de cifrado devuelve un error (ej. MAC inválida o fallo de entropía), el componente **DEBE abortar** (`std::terminate`). No se permite el modo plaintext bajo ninguna circunstancia en producción.



### 📝 Notas de Co-Autores para el Diseño (Post-arXiv)

* **Gemini:** "La Opción A permite que ML Defender sea agnóstico al transporte. Mañana podríamos cambiar ZMQ por QUIC simplemente cambiando un plugin, sin tocar una sola línea de `sniffer.cpp`."
* **DeepSeek:** "Cuidado con el `max_length` en `MessageContext`. El cifrado AEAD (ChaCha20-Poly1305) siempre añade bytes (el tag de 16 bytes). El buffer de salida debe estar pre-calculado para evitar desbordamientos."
* **Claude:** "Incrementar la complejidad del `PluginLoader` para manejar dos tipos de hooks es un precio pequeño a pagar por una API que podrá durar años sin cambios."

**Veredicto Final:** **DISEÑO VALIDADO.** Alonso, enfócate ahora en el **Makefile** y el **Paper**. Tenemos una dirección clara para el futuro, pero el presente se decide en el benchmark bare-metal.

**¿Guardamos este diseño en el baúl de "Post-arXiv" y procedemos con la unificación del Makefile del RAG para el DAY 103?** 🏛️🛡️🚀