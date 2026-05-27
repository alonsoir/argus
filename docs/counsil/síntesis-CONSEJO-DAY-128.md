cat > /Users/aironman/CLionProjects/test-zeromq-docker/docs/CONSEJO-DAY-128-acta.md << 'EOF'
# Acta del Consejo — DAY 128

**Fecha:** 2026-04-24  
**Modelos:** Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral  
**Veredictos vinculantes — 8/8**

---

## Decisiones vinculantes

### D1 — Invariante `0400 root:root` — MANTENER (8/8)
La invariante es correcta y no se relaja. `sudo` es el mecanismo actual
aceptable. Evolución futura (v0.6+): Linux Capabilities (`CAP_DAC_READ_SEARCH`)
o helper aislado con socket Unix. Registrado como DEBT-SEED-CAPABILITIES-001
de prioridad baja.

### D2 — `DEBT-IPTABLES-INJECTION-001` — FIX INMEDIATO (8/8)
`execve()` directo sin shell — DAY 129. `libiptc` a largo plazo.
Es el único incendio activo en el pipeline. Bloqueante de próximo tag.

### D3 — Property testing — PRIORIDADES (8/8)
Orden: (1) `compute_memory_mb`, (2) HKDF key derivation,
(3) ZeroMQ parsers, (4) protobuf round-trip, (5) nonce monotonicity ChaCha20.

### D4 — EtcdClient cleanup — ANTES de ADR-024 (5/3)
Mayoría: limpiar código legacy pre-P2P antes de implementar ADR-024.
El código muerto genera confusión y superficie de ataque.
Secuencia: `[[deprecated]]` → eliminar llamadas → stub P2P mínimo → ADR-024.
Minoría (DeepSeek/Grok/Kimi): mantener hasta ADR-024 funcional.
Decisión: mayoría prevalece. Limpiar en DAY 130-131.

### D5 — Demo FEDER scope — NDR standalone (8/8)
NDR standalone + simulación ligera de federación (2 nodos Vagrant).
No se requiere ADR-038 completo para septiembre 2026.
Milestone go/no-go: 1 agosto 2026.
Acción: clarificar con Andrés Caro Lindo si FEDER requiere federación
real o basta con NDR standalone antes de julio 2026.

---

## Nuevas deudas generadas por el Consejo

DEBT-SEED-CAPABILITIES-001    v0.6+ — Linux CAP_DAC_READ_SEARCH como
alternativa a sudo generalizado
DEBT-FEDER-SCOPE-DOC-001      docs/FEDER-SCOPE.md con scope mínimo
viable y milestone go/no-go 1 agosto

---

## Prioridades DAY 129

1. **DEBT-IPTABLES-INJECTION-001** — execve() + validación argv (BLOQUEANTE)
2. Property test `compute_memory_mb` (F17) — RED→GREEN
3. Property test HKDF key derivation
4. EtcdClient `[[deprecated]]` + plan cleanup
5. docs/FEDER-SCOPE.md

---

## Citas del Consejo

*"La seguridad no es cómoda. Es necesaria."* — Qwen  
*"No construyas encima de comportamiento incorrecto, aunque sea temporal."* — ChatGPT  
*"El sistema ya no solo implementa seguridad: empieza a comportarse como un
sistema que desconfía de sí mismo. Ese es el punto de inflexión correcto."* — ChatGPT  
*"La reproducibilidad y estabilidad de la demo son más importantes que
features incompletas."* — Grok
