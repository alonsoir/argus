REVISOR: Gemini (Google) / Perfil: Sistemas Distribuidos & cs.CR
FECHA: 1 de abril de 2026

VEREDICTO GLOBAL ADR-023: **ACCEPTED CON CONDICIONES**
VEREDICTO GLOBAL ADR-024: **DISEÑO CON RESERVAS**

---

### HALLAZGOS CRÍTICOS (bloquean aceptación):

1.  **Ambigüedad en el Ownership del Buffer (ADR-023):** El struct `MessageContext` contiene `uint8_t* payload`. No queda claro quién libera esa memoria si un plugin decide reasignarla (por ejemplo, si el cifrado aumenta el tamaño más allá de `max_length`). Si el plugin hace `malloc`, el host no sabrá cómo liberarlo (ABI mismatch).
    * *Corrección:* Definir que el buffer es **siempre propiedad del host** y el plugin solo puede escribir hasta `max_length`. Si necesita más, debe devolver un error específico.
2.  **Ataques de Replay en Handshake (ADR-024):** El patrón `Noise_IK` es vulnerable a replay del primer mensaje (el mensaje `e, es, s, ss` no tiene frescura garantizada si el responder no tiene estado previo).
    * *Corrección:* Es imperativo que el `psk3` (derivado del `seed_family`) se combine con un timestamp o un nonce persistente para evitar que un atacante reinicie una sesión antigua capturada.

### HALLAZGOS RECOMENDADOS (no bloquean):

1.  **Padding en MessageContext:** El campo `reserved[8]` debería estar alineado a 64 bits para evitar problemas de padding de compilador entre diferentes arquitecturas (ARM vs x86).
2.  **Alineación con libsodium:** En lugar de usar `noise-c`, se recomienda evaluar **Drygascon** o directamente las primitivas de `libsodium` para construir el handshake, reduciendo el conteo de dependencias externas.

---

### RESPUESTAS A PREGUNTAS ESPECÍFICAS:

**Sobre ADR-023:**

* **Q1 (Superficie de ataque):** Falta un campo `associated_data` (AD) explícito. Aunque el `channel_id` puede actuar como tal, para un uso estricto de AEAD, el encabezado del mensaje (nonce + metadatos) debería estar vinculado criptográficamente.
* **Q2 (Degradación elegante):** **Es un riesgo.** Si el plugin de cifrado falla en cargar su símbolo, el sistema procesará datos en claro. **Debe ser fail-closed.** Si un componente está configurado para usar un plugin de transporte, su ausencia debe invocar `std::terminate()`.
* **Q3 (Orden de integración):** Correcto. El `firewall-acl-agent` es el que más se beneficia de la agilidad de los plugins de transporte para interoperar con diferentes firewalls.
* **Q4 (Minoría de Gemini):** Mantengo mi posición. Usar `reserved[8]` es una "solución de compromiso". Un bump a v2 ahora evita tener que parsear campos reservados en el futuro, lo cual suele ser fuente de bugs de alineación.

**Sobre ADR-024:**

* **Q5 (Patrón Noise):** `IKpsk3` es excelente para 0-RTT/1-RTT cuando las claves estáticas son conocidas. Sin embargo, para máxima seguridad ante compromiso de claves estáticas, **Noise_XX** es el estándar de oro (aunque requiere 1.5-RTT). Para el MVP, `IKpsk3` es aceptable.
* **Q6 (Binding PSK):** Es seguro siempre que el `info` string de HKDF sea único: `"ml-defender:noise-psk:v1"`. Esto garantiza la separación de dominios criptográficos.
* **Q7 (noise-c):** Es funcional, pero **noise-c** está algo estancado. Recomiendo **monocypher** o simplemente usar las funciones `crypto_kx` de **libsodium** que ya están en el stack. Menos código = menos bugs.
* **Q8 (Open questions):** Falta una: **¿Cómo se revocan las claves públicas estáticas si un nodo es robado del hospital?** Sin un mecanismo de revocación o CRL, el sistema es vulnerable a nodos maliciosos persistentes.

**General:**

* **Q9 (Contradicciones):** Hay una tensión en el manejo del Nonce. ADR-023 dice que el host lo gestiona, pero ADR-024 (Noise) genera sus propios nonces de sesión. Debe quedar claro que el nonce de `MessageContext` es el que finalmente viaja por el cable, independientemente de la lógica interna del protocolo Noise.
* **Q10 (Status de ADR-024):** Mantener como **DISEÑO**. Implementar esto antes de arXiv añadiría un riesgo de inestabilidad innecesario. La criptografía estática actual (DAY 99) es suficiente para la publicación.

---

### POSICIÓN DE MINORÍA:

Insisto en que el `MessageContext` debe incluir un **Sequence Number** explícito de 64 bits fuera del campo `reserved`. En redes industriales/médicas, detectar la pérdida o el desorden de mensajes (Packet Loss) es tan importante como la integridad. Delegar esto a un campo "reservado" es tratar la telemetría como un ciudadano de segunda clase.