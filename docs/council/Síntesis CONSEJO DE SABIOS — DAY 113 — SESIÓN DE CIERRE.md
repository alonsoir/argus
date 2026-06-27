## ACTAS CONSEJO DE SABIOS — DAY 113 — SESIÓN DE CIERRE

**Fecha:** 10 Abril 2026 | **Rama:** feature/plugin-integrity-ed25519
**Miembros respondientes:** ChatGPT-5, DeepSeek, Gemini, Grok, Qwen
**Nota de atribución:** Qwen se auto-identificó como DeepSeek en esta sesión — patrón consolidado (6ª vez). Contribuciones registradas bajo Qwen según el archivo de respuesta recibido.

---

### VEREDICTOS POR PREGUNTA

---

**Q1 — PR timing: ¿merge ahora o esperar?**

| Miembro | Veredicto |
|---------|-----------|
| ChatGPT-5 | MERGE YA |
| DeepSeek | NO hasta TEST-INTEG-4d + signal safety |
| Gemini | MERGE AHORA |
| Grok | NO hasta D11 implementado |
| Qwen | MERGE AHORA |

**Resultado: 3-2 a favor del merge inmediato. BLOQUEADO por condición crítica.**

DeepSeek eleva una cuestión de **peso bloqueante** que el árbitro acepta: PHASE 2d (ml-detector) aparece marcada como ✅ en las actas pero **sin TEST-INTEG-4d** documentado como fichero de test existente. Si el test no existe, la validación es incompleta. Grok añade que D11 (--reset) es deuda operativa real pero el árbitro no lo considera bloqueante para el merge.

**Veredicto árbitro:** MERGE CONDICIONADO. Dos condiciones antes del merge:
1. Verificar existencia de TEST-INTEG-4d o implementarlo (DeepSeek — bloqueante aceptado)
2. Revisar async-signal-safety de `shutdown()` en plugin_loader.cpp (DeepSeek — bloqueante aceptado)

---

**Q2 — provision.sh --reset (D11): ¿ahora o diferir?**

| Miembro | Veredicto |
|---------|-----------|
| ChatGPT-5 | P1 post-merge inmediato |
| DeepSeek | P1 antes del merge |
| Gemini | P2 diferir |
| Grok | P1 ANTES del merge |
| Qwen | P2 post-merge |

**Resultado: mayoría P1, split pre/post merge.**

**Veredicto árbitro:** P1 post-merge, con plazo de 7 días tras el merge. No bloqueante para el PR pero no es backlog indefinido. Se registra en BACKLOG.md con deadline explícito.

---

**Q3 — Próxima prioridad: ¿PHASE 3 o ADR-026?**

**UNANIMIDAD (5/5): PHASE 3 primero.**

Argumento convergente: el paper habla de hardening y kernels inseguros. Sin systemd `Restart=always`, sin perfiles AppArmor básicos, sin CI gate para provision, el discurso y el código no son coherentes. ADR-026 (Fleet/XGBoost/BitTorrent) es material para paper v2, no para la base actual.

**Veredicto árbitro: PHASE 3. Sin discusión.**

---

**Q4 — DEBT-TOOLS-001: ¿P3 correcto?**

| Miembro | Veredicto |
|---------|-----------|
| ChatGPT-5 | P2 |
| DeepSeek | P3 con matices |
| Gemini | P3 mantener |
| Grok | P2 |
| Qwen | P3 correcto |

**Resultado: 3 P3, 2 P2.**

**Veredicto árbitro:** P3 con condición: si se usan los injectors para benchmarks formales o publicación de métricas de rendimiento, subir a P2 antes de ejecutarlos. En el estado actual (sin benchmarks formales planificados), P3 es correcto.

---

**Q5 — Párrafo Glasswing/Mythos: ¿tono correcto?**

| Miembro | Veredicto |
|---------|-----------|
| ChatGPT-5 | Demasiado suave — añadir "autonomous" + "chaining" |
| DeepSeek | Adecuado pero mover de Related Work a Introducción |
| Gemini | Correcto, añadir contrapunto defensivo explícito |
| Grok | Demasiado deferente — reescribir factual y defensivo |
| Qwen | Adecuado (respuesta truncada) |

**Resultado: mayoría exige revisión de tono hacia más preciso y factual.**

**Veredicto árbitro:** el párrafo actual dice lo correcto pero en tono demasiado admirativo. Se adoptan tres recomendaciones convergentes:

1. **(Grok/ChatGPT-5):** Mencionar capacidades ofensivas demostradas: chaining autónomo de vulnerabilidades de kernel, escalada a root en Linux.
2. **(Gemini):** Añadir contrapunto defensivo explícito — que aRGus responde arquitectónicamente a esta realidad.
3. **(DeepSeek):** Considerar mover el párrafo a §Introduction o como nota en §Threat Model — Related Work es para trabajos previos, no anuncios contextuales. No bloqueante para arXiv Replace pero deseable.

**Texto revisado propuesto (para Draft v14 → sustituir el párrafo actual):**

```latex
\paragraph{AI-native security reasoning and the evolving threat landscape.}
This paper was written and submitted in April 2026, concurrent with the
announcement of Anthropic's Project Glasswing~\cite{anthropic2026glasswing},
which demonstrated that AI models can autonomously identify and chain
kernel-level vulnerabilities --- including local privilege escalation to
root in Linux --- at a scale and speed previously requiring specialized
human expertise. These results represent a shift in the threat landscape:
AI-augmented offensive capabilities are no longer theoretical.
This directly motivates the explicit kernel security boundary axiom in
\S\ref{sec:threatmodel:kernel}: aRGus NDR assumes the kernel as a
potentially compromised boundary and shifts its trust anchor to
verifiable network behavioral patterns. The network remains an observable
chokepoint even when the host is not. The hardened deployment variants
ADR-030 (AppArmor) and ADR-031 (seL4) documented in
\S\ref{sec:future:hardened} are a direct architectural response to this
trajectory.
```

---

**OBSERVACIÓN ADICIONAL — ChatGPT-5 (posición de minoría registrada)**

`std::terminate()` como política de fail-closed puede ser un vector de DoS triggerable en producción: un plugin mal firmado tumba el proceso completo. ChatGPT-5 sugiere considerar fail-isolated (skip plugin sin matar proceso) para plugins con `require_signature:false`. El árbitro toma nota pero no cambia la implementación actual — ADR-025 D9 es explícito en que `require_signature:true` usa `terminate()` y `false` usa skip. La distinción ya está implementada correctamente. Se registra como observación para ADR futuro sobre estrategias de degradación controlada.

**OBSERVACIÓN ADICIONAL — Gemini (importante para PHASE 3)**

El perfil AppArmor de PHASE 3 debe denegar acceso de escritura a los binarios de `/usr/bin/ml-defender-*` incluso para procesos con privilegios elevados, protegiendo la clave pública hardcodeada contra hex-edit. Se añade a la especificación de PHASE 3.

---

### RESUMEN EJECUTIVO

| Pregunta | Veredicto | Condición |
|----------|-----------|-----------|
| Q1 Merge | CONDICIONADO | TEST-INTEG-4d + signal safety primero |
| Q2 --reset | P1 post-merge | Plazo 7 días tras merge |
| Q3 Siguiente | PHASE 3 unánime | — |
| Q4 DEBT-TOOLS | P3 | Sube a P2 si hay benchmarks formales |
| Q5 Párrafo | Revisar tono | Texto revisado propuesto arriba |

---

### ACCIONES DAY 114 (derivadas del Consejo)

1. Verificar TEST-INTEG-4d — ¿existe o hay que implementarlo?
2. Revisar async-signal-safety de `shutdown()` en plugin_loader.cpp
3. Aplicar texto revisado del párrafo Glasswing en Overleaf → compilar → Draft v14 final
4. Merge feature/plugin-integrity-ed25519 → main (si 1 y 2 resueltos)
5. Abrir rama feature/phase3-hardening
6. Registrar D11 (--reset) en BACKLOG con deadline explícito

---

*"La verdad por delante, siempre."*
*Via Appia Quality · Un escudo, nunca una espada.*
*Actas redactadas: DAY 113 — 10 Abril 2026*