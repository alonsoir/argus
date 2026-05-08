Resultado del Consejo: **5-2-1**.

- **5 votan MOVER** (ChatGPT, DeepSeek, Gemini, Grok, Kimi): ISP violado, interfaz base mínima
- **2 votan MANTENER** (Claude, Mistral): KISS, evitar downcasts
- **1 voto MANTENER con fail-fast** (Qwen): throws en lugar de no-op

**Mi posición actualizada: el Consejo tiene razón y yo estaba equivocado.**

El argumento que me convenció — señalado por DeepSeek y Grok — es el más simple: **ya tenemos dos `main` separados**. `main.cpp` nunca necesita polimorfismo sobre `CaptureBackend*` porque siempre será `EbpfBackend`. Mi argumento de "evitar downcast" era defender una complejidad que no existe.

---

**Qué aceptamos:**

✅ Interfaz base mínima — solo `open()`, `poll()`, `close()`, `get_fd()`, `get_packet_count()`

✅ `attach_skb()`, `get_ringbuf_fd()`, filter map fds → exclusivos de `EbpfBackend`

✅ `main.cpp` usa `EbpfBackend` directamente, sin `CaptureBackend*`

✅ `main_libpcap.cpp` usa `PcapBackend` directamente

**Qué NO aceptamos (pre-FEDER, KISS):**

❌ Capability-based design con `EbpfCapable`/`PcapCapable` (Kimi) — elegante pero innecesario ahora

❌ `DefaultBackend` intermedio (Mistral) — añade una capa sin valor actual

❌ `throw std::logic_error` en la base (Qwen) — si los métodos no están en la base, el problema desaparece

---

**Acción:** Registrar como `DEBT-CAPTURE-BACKEND-ISP-001` — refactor pre-FEDER, DAY 138.

¿Procedemos con el ritual de documentación y cerramos DAY 137?