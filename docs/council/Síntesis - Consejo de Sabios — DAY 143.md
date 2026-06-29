Hay consenso muy claro. Déjame sintetizarlo:

---

**P1 — Zombies: UNÁNIME**
8/8 coinciden: hay que recoger hijos. La diferencia es el mecanismo:
- Claude, Mistral, Grok, ChatGPT, DeepSeek → `waitpid(-1, WNOHANG)` periódico o `SIGCHLD` handler
- Qwen → `sigaction(SIGCHLD, SA_NOCLDWAIT)` — la más limpia, delega al kernel directamente
- ChatGPT, Gemini → van más lejos: `systemd-run` como arquitectura superior

**Decisión sugerida:** `SA_NOCLDWAIT` de Qwen + registrar `DEBT-IRP-SIGCHLD-001` P0 pre-merge.

---

**P2 — float vs double: DIVIDIDO (interesante)**
- Claude, Gemini, Grok, DeepSeek → cambiar a `float` para consistencia
- Mistral, Qwen → mantener `double` + tolerancia `1e-6`, es matemáticamente más correcto
- ChatGPT → enteros escalados (`uint32_t`) para sistemas críticos — posición más radical

**Consenso real:** No hay acuerdo. La tolerancia actual funciona. Registrar como deuda de limpieza, no bloqueante para merge.

---

**P3 — auto_isolate default: UNÁNIME**
8/8 coinciden: **`false` por defecto en producción hospitalaria.** Ningún modelo defiende `true`. El debate es solo en el mecanismo de onboarding:
- Algunos: wizard interactivo
- Otros: `admin_acknowledged: true` explícito
- Qwen: `grace_period_h: 24` — 24h en shadow mode antes de activar

**Decisión sugerida:** Cambiar a `false` + warning prominente al arrancar con IRP desactivado. P0 pre-merge.

---

**P4 — /tmp en AppArmor: UNÁNIME**
8/8: migrar a `/var/lib/argus/irp/` o `/run/argus/irp/`. Qwen hace la distinción correcta:
- `/run/argus/irp/` (tmpfs) para archivos transaccionales volátiles
- `/var/lib/argus/irp/` para estado persistente

**Decisión sugerida:** `/run/argus/irp/` para backup/ruleset temporal. P0 pre-merge.

---

**P5 — Señales: UNÁNIME en el diagnóstico, dividido en la solución**
8/8: dos señales no son suficientes para hospital real. Para FEDER, sí. Las propuestas:
- Claude, Grok, ChatGPT → whitelist de activos críticos como tercera señal
- Qwen → `CorrelationWindow` con N eventos en T segundos (más sofisticado)
- Gemini → inventario topológico por segmento (quirófano vs administración)
- Mistral → `require_second_sensor: true` con Falco/Suricata

**Consenso:** `DEBT-IRP-MULTI-SIGNAL-001` post-FEDER. La whitelist de activos es la señal mínima viable.

---

**Orden para DAY 144 — UNÁNIME:**
**A (merge) → B (benchmark)**. Nadie defiende C primero. Pero antes del merge: P1 + P3 + P4 como blockers, P2 como deuda.

---

¿Abrimos las cuatro deudas formalmente y las añadimos al backlog antes de cerrar el día?