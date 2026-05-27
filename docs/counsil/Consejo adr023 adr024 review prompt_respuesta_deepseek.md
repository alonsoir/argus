REVISOR: DeepSeek (external reviewer)  
FECHA: 2026-04-01

---

## VEREDICTO GLOBAL ADR-023: **ACCEPTED CON CONDICIONES**

La arquitectura multicapa es sólida y la separación de contextos es correcta.  
Condiciones:
- El diseño de `MessageContext` debe especificar claramente la vida útil del puntero `channel_id` y la propiedad de la memoria.
- La estrategia de degradación elegante debe ser revisada para PHASE 2a: si el símbolo `plugin_process_message` no existe, se debe usar el core CryptoTransport, pero **no** se debe permitir que el plugin reciba payload raw si está presente y devuelve error. El error debe ser fail-closed en ese caso.
- El orden de integración es correcto, pero añadiría un test de integración que valide el paso de datos cifrados a través de un plugin real (aunque sea `libplugin_crypto_dummy.so`) antes de mover el core a read-only.

---

## VEREDICTO GLOBAL ADR-024: **DISEÑO CON RESERVAS (no aprobado para implementación inmediata)**

El uso de Noise_IKpsk3 es técnicamente adecuado, pero el documento adolece de varias omisiones que lo convierten en un boceto, no en un diseño listo para implementar.  
Debe resolverse al menos la distribución de claves públicas estáticas y el mecanismo de inyección de las claves de sesión en `CryptoTransport` antes de pasar a implementación.

---

## HALLAZGOS CRÍTICOS (bloquean aceptación)

1. **ADR-023: Propiedad y vida útil de `channel_id`**  
   `channel_id` es un puntero `const char*` que apunta a una cadena estática o gestionada por el host. Si el plugin retiene este puntero (por ejemplo, para logueo asíncrono) después de que la función `plugin_process_message` retorne, podría acceder a memoria inválida. El contrato debe establecer que el puntero es válido solo durante la llamada; cualquier retención requiere una copia explícita. Esto no está documentado.

2. **ADR-023: Comportamiento de error cuando el plugin devuelve `result_code != 0`**  
   El ADR dice que `result_code != 0` → `std::terminate()`. Esto es correcto para PHASE 2b/2c, pero en PHASE 2a, cuando coexisten core y plugin, debería haber una política más matizada: si el plugin falla, se debe usar el core como respaldo o fallar según un flag de configuración. La actual estrategia de degradación elegante solo contempla la ausencia del símbolo, no el error de ejecución.

3. **ADR-024: Distribución de claves públicas estáticas**  
   El diseño asume que el responder tiene una clave pública estática conocida en tiempo de despliegue, pero no especifica cómo se distribuye y autentica. Si cada componente recibe un par de claves estáticas durante el provisionamiento, el sistema escala a pocos nodos, pero la gestión de claves públicas para familias dinámicas (ej. añadir un nuevo sensor) no está resuelta. Sin este mecanismo, la seguridad del handshake es nula (no hay autenticación).

4. **ADR-024: Integración con `CryptoTransport` y cambio en tiempo de ejecución**  
   `CryptoTransport` actualmente deriva claves una vez en el constructor a partir del seed estático. ADR-024 propone reemplazar esas claves con las obtenidas del handshake Noise. El diseño no explica cómo se realiza esta transición atómicamente, cómo se maneja el cifrado de mensajes en vuelo durante el handshake, ni cómo se garantiza que todos los componentes usen la misma clave de sesión. La mera afirmación de que `MessageContext` no cambia es insuficiente.

5. **ADR-024: Dependencia de noise-c**  
   El pinning de versión es adecuado, pero no se evalúa si noise-c es apropiado para un entorno embebido (tamaño binario, superficie de memoria, requisitos de tiempo real). Además, no se menciona si libsodium puede implementar directamente Noise (no puede), por lo que se introduce una nueva dependencia externa que no ha sido evaluada.

---

## HALLAZGOS RECOMENDADOS (no bloquean)

1. **ADR-023: Campo `reserved[8]`**  
   Es una buena práctica, pero quizás sea más claro tener campos explícitos `sequence_number` y `timestamp` como `uint64_t` desde el principio, dado que se prevén para usos futuros y la API no es extremadamente crítica en cuanto a estabilidad ABI en PHASE 2a. La reserva de 8 bytes podría ser demasiado pequeña si en el futuro se quieren añadir ambos. Prefiero la propuesta de Gemini de incluir campos explícitos, aunque esto suponga un bump de versión menor.

2. **ADR-023: Orden de integración**  
   `firewall-acl-agent` primero tiene sentido porque es el destino final de las alertas. Sin embargo, sugiero añadir un test de integración específico que valide el cifrado extremo a extremo desde sniffer hasta firewall usando un plugin dummy, antes de iniciar la migración del resto.

3. **ADR-024: Rango de retries**  
   La propuesta de 5 intentos × 2s es arbitraria. Debería ser configurable y basarse en el tiempo de espera de registro en etcd. También sería recomendable exponer una métrica de fallos de handshake para observabilidad.

4. **ADR-024: Rekeying**  
   La open question sobre rekeying debería priorizarse. Si la sesión se mantiene por mucho tiempo, un rekeying periódico (o por volumen de datos) es necesario para mantener la seguridad a largo plazo. Al menos debería definirse una política, aunque sea "no rekey" con justificación.

---

## RESPUESTAS A PREGUNTAS ESPECÍFICAS

**Q1 — ADR-023: superficie de ataque de `MessageContext`**  
El diseño actual expone el puntero `payload` y `max_length`. Un plugin malicioso podría desbordar el buffer si ignora `max_length`. Esto es un riesgo inherente a plugins en C, pero el ADR no especifica que el host debe usar `max_length` para validar. Debería exigirse que el plugin nunca escriba más de `max_length` bytes y que el host lo verifique tras la llamada. Además, `channel_id` es una cadena; el plugin podría leer fuera de límites si el host no garantiza terminación nula. Añadiría una nota sobre la necesidad de que todos los punteros sean seguros.

**Q2 — Mecanismo de degradación elegante**  
No es correcto. La degradación debe ser controlada: si el símbolo no existe, se usa el core. Si existe pero falla, debe ser fail-closed, porque el plugin podría haber manipulado el buffer incorrectamente. El ADR actual no distingue entre ausencia de símbolo y error de ejecución. En PHASE 2a, si el plugin existe y retorna error, debería fallar el componente, no caer al core, porque el plugin podría haber modificado parcialmente el mensaje.

**Q3 — Orden de integración**  
Correcto. Sin embargo, añadiría un pequeño test de integración temprano que utilice un plugin de cifrado dummy (que simplemente devuelva OK) para validar la infraestructura antes de introducir la lógica real. Esto reduce el riesgo de sorpresas en los componentes más críticos.

**Q4 — Minoría Gemini (bump inmediato a v2)**  
La propuesta de Gemini tiene mérito. Un bump a v2 desde el principio forzaría a todos los plugins a adoptar el nuevo hook y permitiría campos explícitos como `sequence_number` sin reservas. Dado que en PHASE 2a solo habrá unos pocos plugins (el hello y quizás el crypto), el coste de migración es bajo. El argumento de "expansión prematura" es débil porque la API de plugins es joven y la estabilidad aún no es crítica. Recomendaría adoptar v2 directamente, con los campos `sequence_number` y `timestamp` (o un único campo `uint64_t seq`), eliminando el campo reservado. Esto reduce la deuda técnica a largo plazo.

**Q5 — ADR-024: Patrón Noise más adecuado**  
`Noise_IKpsk3` es razonable porque requiere que el iniciador conozca de antemano la clave estática del responder (apropiado cuando hay una topología fija). Otra opción sería `Noise_NKpsk3`, que es similar pero requiere que el responder conozca la clave del iniciador (simétrico). `Noise_XX` sería más pesado. La elección depende de la asimetría de roles: en ML Defender, todos los componentes hablan con todos (p2p), por lo que un patrón simétrico podría ser más limpio. Sugiero reconsiderar si `Noise_NKpsk3` o incluso `Noise_KK` (con claves estáticas conocidas por ambos) encajan mejor, dado que todos los pares podrían tener claves estáticas preinstaladas.

**Q6 — Binding PSK al `seed_family`**  
Es seguro siempre que el `seed_family` se use exclusivamente para derivar el PSK y no se reutilice con otro contexto. La derivación via HKDF con info específica ("noise-ik-psk") garantiza separación de dominios. Sin embargo, si el `seed_family` se deriva a su vez de un seed estático compartido entre familias, se produce un anidamiento que podría debilitar la separación. Debe documentarse que cada familia tiene su propio `seed_family` generado independientemente.

**Q7 — noise-c vs alternativas**  
`noise-c` es una implementación ligera en C, bien auditada, y es una buena opción para sistemas embebidos. Sin embargo, el proyecto actual ya usa libsodium, y libsodium ofrece primitivas de bajo nivel (X25519, ChaCha20, etc.) que permiten implementar Noise con código propio. Añadir noise-c introduce una dependencia extra con su propio modelo de memoria. Dado que el equipo ya maneja libsodium con éxito, podría ser más sostenible implementar el handshake directamente con libsodium (siguiendo las especificaciones de Noise) sin añadir otra biblioteca. Eso reduciría la superficie de ataque y la complejidad de integración. Recomendaría evaluar esa opción.

**Q8 — Open questions bien planteadas**  
Sí, cubren los aspectos principales. Sin embargo, falta una pregunta sobre **el impacto en el modelo de despliegue**: si los componentes necesitan intercambiar claves estáticas, ¿cómo se distribuyen y actualizan en producción sin reintroducir un orquestador central? Además, ¿cómo se maneja la situación en la que un componente se reinicia y su clave estática ha cambiado (por reprovisionamiento)? Debería añadirse una open question sobre la gestión del ciclo de vida de las claves estáticas.

**Q9 — Contradicciones entre ADR-023 y ADR-024**  
La principal contradicción es que ADR-023 asume que la clave de sesión es estática y derivada de HKDF en el constructor, mientras que ADR-024 requiere una actualización dinámica de las claves de sesión. Esto implica cambios significativos en `CryptoTransport` que no están reflejados en ADR-023. Ambos ADR deberían alinearse: ya sea que `CryptoTransport` soporte un método `set_keys()` o que el plugin de cifrado inyecte las claves antes de procesar mensajes. Sin esa especificación, la integración es inviable.

**Q10 — Status de ADR-024**  
Debe cambiarse a **DISEÑO PROVISIONAL / EXPLORATORIO**. No es apropiado considerarlo "diseño" listo para implementar con las lagunas actuales. El equipo debería resolver las cuestiones abiertas, especialmente la distribución de claves públicas y la integración con `CryptoTransport`, antes de pasar a implementación. El documento actual sirve como punto de partida, pero no como base para codificación.

---

## POSICIÓN DE MINORÍA (si aplica)

- **Sobre la degradación elegante:** Considero que en PHASE 2a, la ausencia del símbolo debería ser la única causa para recurrir al core. Si el símbolo existe pero retorna error, debe fallar, independientemente de si el core está disponible. Esto evita que un plugin corrupto deje el sistema en un estado indeterminado.

- **Sobre el bump de API v2:** Soy partidario de hacerlo ahora, incluyendo los campos `sequence_number` y `timestamp` como parte de `MessageContext` desde el principio, eliminando el campo reservado. El coste es mínimo y la claridad es mayor.

- **Sobre la implementación de Noise:** Prefiero una implementación casera basada en libsodium en lugar de integrar noise-c, para mantener el control de dependencias y evitar sorpresas con la licencia y el tamaño binario. Pero acepto que ambas opciones son defendibles.

---

## CONCLUSIÓN

ADR-023 es aceptable con las condiciones señaladas; ADR-024 necesita un trabajo sustancial antes de ser considerado implementable. El camino hacia el cifrado dinámico es ambicioso y está bien orientado, pero aún requiere resolver cuestiones fundamentales de distribución de claves y de integración con la capa de transporte existente. Recomiendo proceder con ADR-023 según lo planeado, pero mantener ADR-024 en estado de diseño hasta que las lagunas se cierren.