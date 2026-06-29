## SÍNTESIS DEL CONSEJO — DAY 161

**8/8 modelos respondieron.** Análisis por pregunta:

---

**Q1 — Wire Protocol Test: ¿Añadir test CryptoTransport completo?**

**5/8 dicen NO ahora** (Claude, DeepSeek, Gemini, Grok, Qwen) — test actual suficiente, separación de responsabilidades correcta.
**3/8 dicen SÍ** (ChatGPT, Kimi, Mistral) — pero todos coinciden: complementario, nunca sustitutivo, en stage Integration.

**Veredicto Alonso:** El test actual queda. Se abre `DEBT-WIRE-CRYPTO-INTEGRATION-TEST-001` como P2 para cuando haya tiempo. No bloquea DAY 162.

---

**Q2 — Jenkinsfile.dev `agent any`**

**8/8 unánimes:** correcto para la fase actual. Migrar a `agent { label 'argus-server' }` cuando Jenkins esté en el servidor FEDER.

**Veredicto:** Confirmado. Sin cambios.

---

**Q3 — Valores fijos vs runtime**

**7/8 dicen fijos** (Claude, ChatGPT, DeepSeek, Gemini, Kimi, Mistral, Qwen). Grok discrepante — propone runtime + perfiles base, pero incluso él reconoce los perfiles como fallback.

Punto de convergencia de todos: runtime solo **selecciona** el perfil, nunca **calcula** valores. Los valores son fijos, validados offline con benchmarks físicos.

**Veredicto:** Valores fijos por perfil. Diseño DEBT-CONFIG-JINJA2-PIPELINE-001 confirmado.

---

**Q4 — test-e2e-live: tráfico orgánico vs sintético**

**6/8 dicen inyectar sintético mínimo** (Claude, ChatGPT, Gemini, Grok, Kimi, Mistral). DeepSeek propone SKIP en lugar de FAIL si delta=0. Qwen propone híbrido (orgánico + sintético como fallback).

El punto de convergencia real: tráfico orgánico solo en Vagrant es **flaky por diseño** — no es aceptable en CI.

**Veredicto:** Inyectar sintético mínimo garantizado. Se implementa en DAY 162 como mini-fix antes de Suricata. `DEBT-E2E-LIVE-DELTA-001` queda parcialmente abierta — el fix del delta es correcto pero falta el inyector.

---

**Q5 — Prioridad DAY 162**

**6/8 dicen A — Suricata** (DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen). Claude y ChatGPT dicen B primero (NTP). Ambos grupos reconocen que NTP es necesario, pero difieren en cuándo.

El argumento de la mayoría: Suricata es el primer hito **visible y diferenciador** para Andrés. NTP es infraestructura invisible. Con deadline FEDER en septiembre, los hitos visibles tienen prioridad. NTP va inmediatamente después.

**Veredicto Alonso:** **A primero** — `DEBT-ARGUSPP-SURICATA-001`. NTP en DAY 163-164.

---

Ahora guardamos la síntesis y actualizamos BACKLOG y README:

```bash
python3 << 'PYEOF'
content = """# SÍNTESIS — CONSEJO DE SABIOS — DAY 161
*Fecha: 2026-05-23 · 8/8 modelos respondieron*

## Veredictos

| Q | Pregunta | Veredicto | Votos |
|---|----------|-----------|-------|
| Q1 | Test CryptoTransport adicional | NO ahora — abrir DEBT-WIRE-CRYPTO-INTEGRATION-TEST-001 P2 | 5/8 No, 3/8 Sí (complementario) |
| Q2 | Jenkinsfile.dev agent any | CORRECTO para fase actual | 8/8 unánime |
| Q3 | Valores fijos vs runtime | FIJOS por perfil, runtime solo selecciona | 7/8 fijos |
| Q4 | Tráfico sintético E2E | INYECTAR sintético mínimo garantizado | 6/8 sintético |
| Q5 | Prioridad DAY 162 | A) SURICATA primero, luego B) NTP | 6/8 Suricata |

## Decisiones tomadas
- test_wire_protocol.cpp queda como está
- Jenkinsfile.dev/prod: sin cambios
- DEBT-CONFIG-JINJA2-PIPELINE-001: valores fijos confirmados
- test-e2e-live: fix delta correcto, falta inyector sintético (DAY 162 mini-fix)
- DAY 162: DEBT-ARGUSPP-SURICATA-001 (ADR-048 F2)

## Nueva deuda abierta
- DEBT-WIRE-CRYPTO-INTEGRATION-TEST-001: P2, post-Suricata
"""
with open('docs/council/síntesis - CONSEJO DE SABIOS — DAY 161.md', 'w') as f:
    f.write(content)
print("OK")
PYEOF
```

¿Guardamos las respuestas individuales y la síntesis, y luego actualizamos BACKLOG y README?