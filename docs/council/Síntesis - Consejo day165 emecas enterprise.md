## Análisis de discrepancias entre los 8 modelos

Las preguntas 1, 5 y 6 tienen **unanimidad total**: todos votan (C) targets anidados, merge sin Jenkins (P1 post-merge), y (B) EMECAS++. No hay nada que deliberar ahí.

Las discrepancias reales son tres, y todas en las preguntas 2, 3 y 4.

---

### Discrepancia D1 — Pregunta 2: ¿Test de reconexión de Vault pre-merge?

| Posición | Modelos |
|----------|---------|
| No bloquea, post-merge | Claude, DeepSeek, Grok, Mistral |
| Sí bloquea, obligatorio pre-merge | Kimi, Qwen |
| Sugieren añadirlo pero no lo declaran bloqueante | ChatGPT, Gemini |

**Lo que divides:** si el test básico de "Vault cae, pipeline sobrevive con caché RCU, Vault vuelve, epoch se recupera" es parte del gate de merge o es deuda P1.

**Argumento del bando que bloquea (Kimi/Qwen):** el RCU handle fue diseñado exactamente para ese escenario. Si no lo testamos en el gate, no hemos validado su razón de existir. Son ~2 minutos de test.

**Argumento del bando que no bloquea (Claude/DeepSeek):** Vault HA es un problema de infraestructura. El test funcional ya pasa. El riesgo de añadir un `pkill vault` en EMECAS es introducir flakiness por timing.

**El quid:** ¿tiene `VaultProvider` ya implementado el retry/caché para que ese test pueda pasar en verde, o habría que implementarlo también?

---

### Discrepancia D2 — Pregunta 3: ¿Live epoch rotation en el gate?

| Posición | Modelos |
|----------|---------|
| Solo FakeEtcdServer (A) | Claude (1/8) |
| Live rotation obligatoria (B) | ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen (7/8) |

Esta es la discrepancia más clara en número. 7 contra 1.

**El argumento de la mayoría:** FakeEtcdServer valida la lógica del coordinador pero no la cadena real Vault→etcd→CryptoEpochCoordinator→CryptoProviderHandle RCU→wire header→firewall. Los bugs de race condition en hot-reload con threads reales y sockets reales no se detectan con un mock. Coste: ~3-5 min. Valor: eliminar la categoría más peligrosa de bugs de integración.

**El argumento de Claude:** riesgo de flakiness por timing de etcd watch en entorno Vagrant (VM con recursos limitados). Un EMECAS que falla por timing entrena a ignorar los fallos.

**El quid:** ¿ha demostrado ya `test-e2e-vault` estabilidad en el entorno Vagrant, o produce resultados variables? Si ese test ya es estable, el argumento del flakiness se debilita.

---

### Discrepancia D3 — Pregunta 4: ¿Test negativo epoch_id incorrecto, bloqueante?

| Posición | Modelos |
|----------|---------|
| P2, no bloquea merge | Claude, DeepSeek |
| Bloqueante, obligatorio pre-merge | ChatGPT, Gemini, Grok, Kimi, Mistral, Qwen (6/8) |

**El argumento de la mayoría:** en un sistema NDR de seguridad, el rechazo correcto de mensajes inválidos no es una feature opcional, es parte del contrato de seguridad. Un firewall que procesa mensajes con `epoch_id` desconocido podría, en el peor caso, intentar descifrar con clave incorrecta y o bien corromper el estado o bien generar un oracle de padding. Kimi lo dice explícitamente: "no es un bug funcional, es una vulnerabilidad". El test son ~20 líneas.

**El argumento de Claude/DeepSeek:** el test positivo (crypto_errors == 0 con epoch válido) ya valida el camino seguro. El negativo es barato pero no es arquitectónico.

---

## Las tres preguntas para ti, Alonso

**D1:** ¿Tiene `VaultProvider` implementado ya el retry + caché post-caída, o es código que habría que escribir? Si ya existe: el test de reconexión debería pasar sin implementación nueva y entra en el gate. Si no existe: es feature nueva, post-merge.

**D2:** ¿Ha sido `test-e2e-vault` estable en las ejecuciones anteriores, o has visto flakiness por timing? Si es estable: la mayoría de 7/8 gana. Si hay historial de flakiness: el argumento de Claude cobra peso.

**D3:** Esta me parece la más clara. 6/8 votan que el rechazo de `epoch_id` inválido es contrato de seguridad, no deuda técnica. Son ~20 líneas que ya tienes infraestructura para escribir. ¿Tienes algún motivo para diferirlo más allá de tiempo?