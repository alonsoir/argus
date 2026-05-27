REVISOR: Grok (cs.CR / sistemas distribuidos, enfoque en crypto y aislamiento)

FECHA: 01 de abril de 2026

VEREDICTO GLOBAL ADR-023: ACCEPTED CON CONDICIONES

VEREDICTO GLOBAL ADR-024: DISEÑO CON RESERVAS

HALLAZGOS CRÍTICOS (bloquean aceptación):
- Ninguno que bloquee ADR-023. Para ADR-024, el binding del PSK derivado del seed_family introduce un riesgo sutil de key material reuse si no se separa correctamente el contexto HKDF (ver Q6). No es fatal pero requiere mitigación explícita antes de implementación.
- En ADR-023, el uso de `std::terminate()` en `result_code != 0` es correcto para fail-closed, pero debe ir acompañado de un watchdog/reboot automático en producción (hardware embebido commodity); de lo contrario, un plugin malicioso o corrupto podría causar DoS persistente.

HALLAZGOS RECOMENDADOS (no bloquean):
- ADR-023: Añadir al `MessageContext` un campo `uint64_t sequence_number` (usando los 8 bytes reserved) ya en v1, o al menos un monotonic counter explícito para detectar replays/duplicados a nivel de plugin. El nonce de 96-bit ayuda, pero la separación de concerns lo hace más robusto.
- ADR-024: Documentar explícitamente el KCI (Key Compromise Impersonation) resistance de IKpsk3 y considerar si se necesita rekeying periódico (ej. cada 24h o por volumen de tráfico) para limitar el blast radius de una sesión comprometida.
- General: En hardware sin AES-NI (ARMv8 commodity), verificar que ChaCha20-Poly1305 de libsodium esté optimizado (neon intrinsics si disponible); de lo contrario, impacto de performance en sniffer de alto throughput.

RESPUESTAS A PREGUNTAS ESPECÍFICAS:

Q1: El diseño de `MessageContext` expone una superficie de ataque moderada pero manejable.  
Los campos `nonce[12]` y `tag[16]` son pasados al plugin: un plugin comprometido podría forzar MAC failures o manipular nonce (aunque el host es propietario del cifrado real, esto podría usarse para fingerprinting o side-channel). El `payload` pointer permite que plugins lean/escriban directamente, lo cual es necesario pero requiere que el host haga copy-on-write o validación estricta de bounds antes/después de llamar al plugin (max_length >= length + 16 es buena).  
Faltan: un `uint64_t monotonic_counter` o `sequence_number` explícito (el reserved[8] es insuficiente si no se define semántica). Sobran potencialmente: `reserved[8]` si no se usa pronto (mejor un union o campos opcionales). El `channel_id` es útil para logging/auditoría pero podría leak info si plugins lo usan maliciosamente. En general, la superficie es aceptable gracias al aislamiento criptográfico en el host.

Q2: El mecanismo de degradación elegante es **incorrecto** para un sistema de seguridad NDR (Network Detection and Response). Debería ser fail-closed también: si el símbolo `plugin_process_message` no existe, el host debe rechazar cargar el plugin o tratarlo como no confiable (ej. solo modo read-only o logging). Permitir "payload raw" abre la puerta a plugins legacy que bypassan la capa de procesamiento intencionada, violando el principio de least privilege y complicando auditoría. La degradación solo es aceptable en entornos no-security-critical.

Q3: El orden `firewall-acl-agent → rag-ingester → rag-security` es razonable y conservador (primero el enforcement más crítico). Sin embargo, una razón para reconsiderar: integrar primero `rag-security` (que presumiblemente valida/analiza) antes de `rag-ingester` permitiría early rejection de datos maliciosos antes de ingestión costosa. Si rag-ingester es pesado (embedding/RAG), priorizar security upstream reduce attack surface. Mantengo el orden actual como OK, pero recomiendo justificarlo con perfiles de threat model (ej. ataque de data poisoning vs. ACL bypass).

Q4: La minoría de Gemini **no** debería reconsiderarse por ahora. Expandir API prematuramente (v2 con sequence/timestamp) viola el principio de YAGNI en un proyecto DAY 104. El `reserved[8]` provee un migration path limpio y backward-compatible. Validar en producción (o al menos en staging con carga real) primero. Bump solo si surge necesidad concreta durante PHASE 2.

Q5: `Noise_IKpsk3` es **adecuado** pero no el óptimo ideal para todos los casos. Proporciona 1-RTT, identity hiding decente para el initiator (su static key se envía encriptado bajo la static del responder), forward secrecy por sesión y binding PSK fuerte.  
Alternativas:
- `Noise_IKpsk2` (usado en WireGuard) es muy similar y bien probado.
- `Noise_KK` si ambos lados conocen las static keys mutuamente desde deploy (más simple, mejor mutual auth).
- `Noise_XXpsk3` si se quiere transmisión explícita de static keys con más flexibilidad, pero añade overhead y peor identity hiding en algunos escenarios.  
  IKpsk3 encaja bien porque la static pública del responder es conocida en deploy time (pre-message ← s). Es correcto para nodos con recursos limitados.

Q6: El binding PSK (HKDF(seed_family, "noise-ik-psk")) es **seguro en principio** si el HKDF usa un salt/info context-specific fuerte y libsodium se llama correctamente. Sin embargo, introduce riesgo moderado de reutilización de material criptográfico si el mismo seed_family se usa en otros contextos HKDF (ej. subclaves por canal estáticas de antes). Recomiendo separar claramente: derivar un "noise_root" distinto o usar domain separation explícita en el info string (ej. "noise-ikpsk3-argus-ndr-v1"). No es catastrophic gracias a HKDF, pero documentar y auditar todos los usos de seed_family.

Q7: noise-c (vendored, commit pinned) es una elección **correcta y conservadora** para C++20 embebido. Es plain C, referencia limpia, MIT license, sin dependencias pesadas y fácil de integrar vía vendoring. Alternativas (libnoise, cacophony en Haskell, o implementaciones Rust vía FFI) añaden complejidad o runtime overhead no deseado en hardware ~150-200 USD sin AES-NI. Pinning el commit es esencial. Asegurarse de compilar con flags de hardening (-fstack-protector-strong, etc.).

Q8: Las 4 open questions están bien planteadas y cubren lo esencial.  
Riesgos adicionales que deberían convertirse en open questions:
5. Impacto de handshake failure en disponibilidad (fail-closed con std::terminate es fuerte; ¿graceful degradation con fallback a seed estático o alerta + retry prolongado?).
6. Threat model contra compromised static keypairs (distribución via provision.sh): ¿rotación de static keys? ¿certificados o pinning estricto?
7. Performance del handshake en ARMv8 commodity bajo carga (medir latencia y CPU).
8. Interacción con etcd: ¿el registro etcd expone metadata que ayude a un attacker a targetear handshakes?

Q9: No hay contradicciones graves. ADR-023 mantiene `MessageContext` y `CryptoTransport` inmutables, y ADR-024 reemplaza solo las subclaves internas post-handshake. Esto es consistente y limpio. La única tensión menor es que ambos enfatizan fail-closed (`std::terminate()`), lo cual es coherente pero amplifica el riesgo de DoS si no se maneja con watchdog.

Q10: Mantendría el status en **DISEÑO** (o "DISEÑO APROBADO CON IMPLEMENTACIÓN PENDIENTE"). No es necesario hacerlo más restrictivo aún; "post-arXiv" indica que no bloquea las PHASE 2 actuales, lo cual es correcto. Una vez implementado y probado (incluyendo TEST-INTEG), subir a "IMPLEMENTADO" o "PRODUCTION-READY" tras revisión de código y fuzzing del handshake.

POSICIÓN DE MINORÍA (si aplica):
- Recomiendo registrar como minoría: considerar `Noise_KK` en lugar de `IKpsk3` si la distribución de claves públicas estáticas es confiable y mutua desde provision.sh (mejor mutual authentication explícita y menos mensajes en handshake). IKpsk3 prioriza mejor identity hiding para initiator en escenarios donde el responder es "servidor" conocido, pero KK simplifica en despliegues cerrados de confianza (hospitales/ayuntamientos).
- Otra minoría: hacer el plugin loader fail-closed por defecto (requerir símbolo `plugin_process_message` siempre) y proveer un "compatibility shim" explícito para plugins legacy, en vez de degradación silenciosa.

El proyecto avanza de forma sólida en aislamiento criptográfico y diseño minimalista para hardware restringido. Buen trabajo en mantener el scope controlado. Recomiendo fuzzing intensivo de `MessageContext` y simulación de handshake failures antes de avanzar a PHASE 2c. ¡Sigo disponible para la siguiente sesión del Consejo!