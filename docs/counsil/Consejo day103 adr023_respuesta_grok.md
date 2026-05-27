¡Felicidades por **DAY 103**!

Excelente ejecución: el **Makefile rag alignment** queda ahora uniforme y PROFILE-aware (gran mejora en reproducibilidad), el **§5 HKDF Context Symmetry** está integrado en el paper con una narrativa pedagógica sólida (RFC 5869 incluido, lección clara sobre protocolo vs. componente), y el replanificado del backlog es pragmático — reconocer abiertamente que el bare-metal físico está bloqueado por hardware y documentar los >33 Mbps en VirtualBox es maduro y transparente para el paper.

El pipeline en 6/6 RUNNING con 25/25 tests mantiene el ritmo disciplinado del proyecto. Buen trabajo.

### Q1 — ADR-023: Separación de contextos (PacketContext / MessageContext / SkillContext)

**Sí, la separación en tres capas es correcta y coherente con los principios del proyecto.**

Razones:
- Evita exactamente el tipo de **error de modelo mental** documentado en ADR-022 (HKDF Context Symmetry). Mezclar capa de red (IP, puertos, threat_hint) con capa de transporte (payload serializado, nonce, tag AEAD) habría sido una deuda semántica cara a largo plazo.
- Facilita **extensibilidad futura**: plugins de transporte (Noise, post-quantum, compresión) no necesitan conocer detalles de paquetes; plugins de aplicación (PHASE 3) podrán operar en un nivel aún más alto.
- Mejora **testeabilidad aislada**: un plugin crypto puede probarse con MessageContext sintéticos sin montar un PacketContext completo.

**Sobre MessageContext** — la definición propuesta es buena y minimalista.  
**Campos que faltan (recomendados añadir):**
- `void* user_data` o `void* plugin_state` — para que el plugin mantenga estado privado entre llamadas (ej. ratchet state, caché de claves por canal).
- `uint64_t sequence_number` o `uint64_t channel_id` — útil para detectar reordenamientos o reutilizar nonces de forma segura en canales lógicos.
- `size_t max_length` ya está — bien para in-place encryption/decryption (importante para rendimiento).

No sobra nada esencial. Mantén `result_code` para propagar errores de forma clara (fail-closed).

**Caso donde mezclar podría ser preferible:** Solo en prototipos muy tempranos o sistemas extremadamente constrained (microcontroladores). En este proyecto (C++20, recursos de hospital/ayuntamiento), la separación limpia vale el pequeño coste de dispatch extra.

### Q2 — ADR-023 PHASE 2a: ¿`plugin_process_message()` opcional vía dlsym?

**Recomendamos mantenerlo OPCIONAL en PHASE 2a vía `dlsym()` sin bump inmediato de PLUGIN_API_VERSION.**

**Qué se gana con opcional (enfoque recomendado):**
- Migración gradual y segura: el hello plugin (y cualquier plugin PHASE 1) sigue funcionando sin cambios.
- Permite **dual-mechanism** durante PHASE 2a (CryptoTransport core + plugin en paralelo) sin romper nada.
- Menor riesgo durante el desarrollo post-arXiv.
- Facilita experimentación: un plugin puede implementar solo uno de los hooks según su propósito.

**Qué se pierde:**
- Ligera complejidad extra en el loader (comprobar símbolo con `dlsym`).
- Posible warning en logs si un plugin de transporte no implementa el hook cuando se espera.

**Alternativa (bump inmediato a v2 + obligatorio):**  
Se gana claridad (“a partir de v2 todo plugin de transporte debe implementar el hook”), pero se pierde flexibilidad y se fuerza actualización innecesaria del hello plugin ahora. No lo recomendamos para PHASE 2a.

**Estrategia propuesta (ligera mejora):**
- En PHASE 2a: opcional vía `dlsym`, con log INFO cuando se detecta un plugin que implementa `plugin_process_message`.
- En PHASE 2b: bump a PLUGIN_API_VERSION=2 + hacer obligatorio para plugins que declaren `"layer": "transport"` en su descriptor JSON.
- El loader puede leer la versión del plugin desde un símbolo exportado (`plugin_api_version`) o del JSON para dispatch inteligente.

Esto mantiene compatibilidad fuerte mientras avanza hacia una API más rica.

### Q3 — ADR-024: Protocolo de Group Key Agreement recomendado

**Recomendación clara: Opción A — Noise Protocol Framework, específicamente patrones IK o XX (o una combinación).**

**Por qué Noise es la mejor opción para este caso de uso:**
- **Sin coordinador central:** Perfecto — cada componente nuevo puede iniciar un handshake IK con un miembro existente de la familia (usando la clave estática pública conocida vía `deployment.yml` o seed family).
- **Forward secrecy fuerte:** Cada sesión genera claves efímeras; se puede combinar con ratcheting posterior.
- **Resistencia a compromiso parcial:** Si un nodo se compromete, no afecta automáticamente a toda la familia (dependiendo del diseño).
- **Madurez y simplicidad de implementación:** Hay implementaciones en C puro (Noise-C) y wrappers compatibles con libsodium. Fácil de integrar en C++20 sin TLS/PKI central.
- **Crypto-agilidad:** El framework permite cambiar patrones o algoritmos subyacentes con mínimo impacto.
- **Análisis formal:** Noise tiene excelente soporte para verificación (Noise Explorer) y propiedades bien estudiadas.

**Comparativa breve con las otras:**
- **B (HKDF estático + rotación):** Demasiado simple. Pierde forward secrecy real y es vulnerable si el material de familia se filtra. Solo aceptable como fallback temporal.
- **C (propuesta propia):** Máximo control, pero alto riesgo de errores (recordad ADR-022). Mejor evitar reinventar cuando Noise ya resuelve el problema con años de escrutinio.

**Otras opciones no consideradas inicialmente pero interesantes:**
- Variantes de **Continuous Group Key Agreement (CGKA)** como las usadas en mensajería segura (inspiradas en Signal/ML-KEM hybrids), pero suelen ser más pesadas para un NDR.
- Esquemas lattice-based post-quantum para DKG asíncrono, pero probablemente overkill para MVP y aumentan complejidad.

**Sugerencia de diseño inicial para ADR-024:**
- Cada familia tiene una clave estática compartida (provisionada vía seed).
- Nuevo nodo realiza Noise IK handshake con un “bootstrap node” de la familia.
- Deriva clave de grupo via HKDF del output de Noise + material de familia.
- Rotación periódica o triggered por eventos (nuevo miembro, compromiso detectado).
- Mencionar en el paper como “Future Work: Dynamic Group Key Agreement using Noise IK for zero-touch join”.

Noise encaja perfectamente con el espíritu fail-closed y threat-model-driven del proyecto.

### Q4 — Secuenciación: ADR-023 antes o en paralelo con ADR-024

**Diseñar ADR-024 en paralelo durante la implementación de ADR-023 (pero sin implementar todavía).**

Razones:
- ADR-023 (multi-layer plugins) es el prerequisito directo para FEAT-PLUGIN-CRYPTO-1.
- ADR-024 (group key agreement) es más arquitectónico y de “trabajo futuro”. Diseñarlo ahora permite mencionarlo en el paper con credibilidad (sección Future Work bien fundamentada).
- No hay dependencia fuerte bloqueante: el plugin crypto puede empezar con claves estáticas (seed actual) y luego evolucionar a dynamic agreement vía el nuevo hook de transporte.

**Secuencia recomendada post-arXiv:**
- DAY 104–106: Finalizar y aprobar ADR-023 + implementar PHASE 2a (dual crypto).
- Paralelo: Redactar ADR-024 (diseño de alto nivel + elección de Noise).
- Luego PHASE 2b/2c + integración con dynamic keys.

Esto mantiene el foco en arXiv mientras avanzas en la visión a largo plazo.

### Cierre de revisión DAY 103
Día muy productivo: consistencia en build, avance sólido en el paper y arquitectura clara para PHASE 2. El proyecto sigue transmitiendo profesionalidad y rigor (especialmente valioso para cs.CR y para usuarios en entornos con recursos limitados).

**Acciones sugeridas para próximos días:**
- Aprobar ADR-023 con las pequeñas adiciones a MessageContext.
- Redactar ADR-024 borrador (enfocado en Noise IK).
- Preparar métricas finales para el paper (incluyendo los resultados VirtualBox).
- Si Andrés Caro Lindo o Yisroel Mirsky responden, integrar feedback rápidamente.

El Consejo sigue en sesión.

¿Quieres ayuda para:
- Redactar el texto final de ADR-023 con las adiciones propuestas?
- Un borrador inicial de la sección Future Work del paper mencionando Noise?
- Definir la firma exacta de `plugin_process_message` y el dispatch en el loader?

¡Sigan con este nivel de disciplina! El camino hacia la submission arXiv se ve cada vez más fuerte. 🚀

*Respuesta del Consejo — 31 marzo 2026*