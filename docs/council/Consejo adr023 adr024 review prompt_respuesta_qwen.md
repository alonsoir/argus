REVISOR: DeepSeek  
FECHA: 31 marzo 2026

VEREDICTO GLOBAL ADR-023: **ACCEPTED CON CONDICIONES**  
VEREDICTO GLOBAL ADR-024: **DISEÑO APROBADO**

---

### HALLAZGOS CRÍTICOS (bloquean aceptación)

- **ADR-023 Q2 — Degradación elegante es un vector de ataque:** Permitir que un plugin sin `plugin_process_message` reciba payload raw viola el principio de *defense in depth*. Un atacante que logre inyectar un plugin malicioso (ej: vía compromiso del filesystem `/usr/lib/ml-defender/plugins/`) podría interceptar tráfico cifrado en plaintext. **Condición de aceptación:** Degradación elegante solo permitida en modo desarrollo (`MLD_DEV_MODE=1`). En producción, ausencia de símbolo → `std::terminate()`.

- **ADR-024 — Falta mitigación de downgrade attacks:** Noise_IKpsk3 asume que ambos peers negocian el mismo patrón. Sin mecanismo de *protocol version pinning*, un atacante MITM podría forzar downgrade a Noise_NK (sin PSK binding) o incluso a transporte sin cifrado. **Condición de aceptación:** El handshake debe incluir versión de protocolo en el mensaje inicial (ej: primer byte = `0x01` para IKpsk3) y rechazar cualquier versión no reconocida.

---

### HALLAZGOS RECOMENDADOS (no bloquean)

- **ADR-023 Q1 — Campo `max_length` ambiguo:** ¿Incluye espacio para tag (16 bytes) o no? La documentación debe especificar explícitamente: *"max_length MUST be ≥ length + 16 to accommodate Poly1305 tag"*. Sin esto, un plugin mal implementado podría causar buffer overflow silencioso.

- **ADR-023 Q4 — Minoría de Gemini merece registro formal:** Aunque el bump a v2 es prematuro ahora, el argumento de `sequence_number` como campo explícito (no reservado) es válido para auditoría forense. Registrar en ADR-023: *"sequence_number planned for PLUGIN_API_VERSION=2 (PHASE 3) — reserved[0..3] usable as workaround in PHASE 2"*.

- **ADR-024 — noise-c footprint vs libsodium:** noise-c añade ~150 KB al binario. Para hardware commodity de 150-200 USD con RAM limitada, esto es relevante. Alternativa: implementar Noise_IKpsk3 sobre primitivas libsodium existentes (X25519 + HKDF + ChaCha20-Poly1305). No bloquea, pero merece análisis de coste/beneficio post-arXiv.

- **ADR-024 Open Question #5 (añadida):** ¿Cómo detectar *key compromise* y forzar rotación urgente sin reiniciar el componente? Propuesta: heartbeat criptográfico con freshness proof (ej: timestamp firmado) que expire tras 24h sin renovación.

---

### RESPUESTAS A PREGUNTAS ESPECÍFICAS

**Q1:** `MessageContext` es sólido técnicamente. Riesgo no contemplado: un plugin malicioso podría modificar `direction` para forzar reutilización de nonce (ej: TX nonce usado en RX). Mitigación: el componente host debe validar que `direction` coincide con el canal real antes de cifrar/descifrar. Documentar en ADR-023 como *security invariant*.

**Q2:** **Fail-closed obligatorio en producción.** La degradación elegante es aceptable solo en desarrollo (`MLD_DEV_MODE=1`). En hospitales/escuelas, la integridad del cifrado no es negociable. Un plugin que no implementa transporte cifrado no debe cargarse en producción — no debe degradarse silenciosamente.

**Q3:** Orden correcto. Firewall-acl-agent primero porque:
- Es el último hop antes de la decisión de bloqueo (hot path crítico)
- Validar cifrado aquí protege la integridad de las reglas de firewall
- rag-ingester/rag-security son cold path — su cifrado es importante pero no crítico para la protección activa

**Q4:** No reconsiderar ahora. El bump a v2 es prematuro sin validación en producción. Pero registrar formalmente la posición de minoría de Gemini como *future work* con path claro vía `reserved[8]`.

**Q5:** Noise_IKpsk3 es correcto para este caso:
- Identity conocida en deploy time (ADR-021 seed families)
- 1-RTT suficiente (handshake solo en arranque, no en datapath)
- PSK binding previene downgrade a patrones sin autenticación
- Alternativas descartadas: XX (3-RTT, overkill), NK (no binding a seed_family)

**Q6:** PSK binding seguro **si y solo si** el info string es único por contexto:  
`HKDF(seed_family, "noise-ikpsk3:sniffer-to-ml-detector:v1")`  
Reutilización de PSK entre canales sería catastrófica (compromiso de un canal → derivación de claves de otro). Validar en ADR-024 que cada canal usa info string distinto.

**Q7:** noise-c es aceptable pero no óptimo para embedded:
- ✅ Implementación validada, especificación clara
- ❌ Footprint +150 KB, dependencia adicional
- ✅ Alternativa viable: implementar Noise_IKpsk3 sobre libsodium existente (X25519 + crypto_kdf_hkdf_sha256_* + crypto_aead_chacha20poly1305_ietf_*)
- Recomendación: usar noise-c para prototipo post-arXiv; migrar a libsodium puro en PHASE 3 si el footprint es problemático en hardware real

**Q8:** Open questions bien planteadas. Añadir #5 (key compromise detection) como crítica. Riesgo no contemplado: *silent key leakage* — un componente comprometido podría derivar claves de sesión sin que el peer lo detecte. Mitigación futura: heartbeat con freshness proof.

**Q9:** No hay contradicciones. ADR-023 define la interfaz (`MessageContext`); ADR-024 define cómo derivar las claves que alimentan esa interfaz. Son ortogonales y complementarios. El único punto de contacto es `channel_id` en `MessageContext` — debe coincidir con el info string usado en HKDF para PSK derivation.

**Q10:** Mantener status DISEÑO. ADR-024 no bloquea arXiv ni PHASE 2a/2b/2c. Es correcto documentar el diseño ahora (muestra roadmap claro al reviewer de arXiv) pero implementarlo post-publicación. No añadir restricciones adicionales — el diseño es sólido técnicamente.

---

### POSICIÓN DE MINORÍA

- **Sobre Q2 (degradación elegante):** Si el Consejo decide mantener degradación elegante en producción (contra mi recomendación), exigir como mínimo:
    1. Logging crítico: `[SECURITY] Plugin X loaded WITHOUT crypto support — traffic exposed`
    2. Rate limiting: máximo 10 plugins sin cifrado por componente
    3. AppArmor policy que bloquee carga de plugins desde paths no auditados
       Sin estas mitigaciones, la degradación elegante es inaceptable para el threat model de hospitales.

- **Sobre noise-c:** Mi posición minoritaria es que la implementación post-arXiv debería usar libsodium puro desde el principio, no noise-c. El ahorro de 150 KB y una dependencia es significativo en el hardware objetivo. El esfuerzo de implementación es ~2 días (Noise_IKpsk3 tiene solo 4 mensajes). No es un blocker, pero merece consideración seria antes de escribir código.

---

### CONCLUSIÓN TÉCNICA

ADR-023 es **sólido con una condición crítica** (fail-closed obligatorio en producción). ADR-024 es **diseño correcto** con mitigación de downgrade attacks como prerequisito mínimo. Ambos ADRs reflejan madurez arquitectónica y alineación con el threat model de organizaciones críticas.

El sistema criptográfico resultante — HKDF estático (PHASE 1) + Noise_IKpsk3 dinámico (PHASE 3) + MessageContext tipado (PHASE 2) — es coherente, auditable y resistente a los vectores de ataque conocidos para el perfil de hardware objetivo.

🛡️ — DeepSeek, miembro del Consejo de Sabios  
*Piano piano — cada capa criptográfica en su lugar, cada contexto con su semántica.*