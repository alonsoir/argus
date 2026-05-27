## Síntesis del Consejo de Sabios — DAY 167

---

### Q1 — KNOWN-FAIL-VM-PERF-001

**Veredicto: 8/8 → Opción C.** Unanimidad total. Dejar visible, documentar en `docs/KNOWN-FAILS.md`. La única variante es Gemini, que propone un híbrido B+C para reducir ruido visual, pero la mayoría rechaza cualquier filtro. ChatGPT añade un matiz útil: si el ruido se vuelve inaceptable en el futuro, B es aceptable *solo* para tests de performance, nunca para funcionales.

**Decisión: C. Crear `docs/KNOWN-FAILS.md` mañana como parte del cierre de DAY 167.**

---

### Q2 — `.deb` vs Suricata

**Veredicto: 8/8 → Suricata primero.** Unanimidad sin matices. El argumento es idéntico en todos: valor demostrativo FEDER incomparablemente mayor. Kimi va más lejos y propone re-etiquetar `DEBT-PACKAGE-DEB-001` como `POST-FEDER-001`.

**Decisión: Suricata → `.deb`. El roadmap original (DAY 164) queda superado por la realidad.**

---

### Q3 — NTP en EMECAS++

**Veredicto: dividido.** Aquí el Consejo no es unánime.

- **"Antes de Suricata, en Acto I" (Grok, Kimi, DeepSeek, Mistral, ChatGPT):** ADR-046 es P0, no hay negociación, esfuerzo mínimo, hacerlo ya.
- **"En provisioning primero, no en EMECAS++ aún" (Claude):** Riesgo de falsos positivos en VM antes de validar.
- **"Acto I con lógica condicional CI/PROD" (Qwen):** Gate real solo en bare metal, skip en CI VM.
- **"Sí, pero cuidado con VirtualBox clock drift" (Gemini):** Validar que no rompa el pipeline CI.

**Consenso de consensos:** Implementar `DEBT-ARGUSPP-NTP-001` en `provision.sh` primero, luego Acto I con guard condicional (como propone Qwen). No bloquear Suricata por esto — es media sesión, no un sprint.

---

### Q4 — `vendor.key` a Vault vs Suricata

**Veredicto: mayoría → paralelo, con matices.**

- **"Vault antes que Suricata" (Grok, Mistral):** Supply chain limpia primero.
- **"Paralelo — Suricata no depende de vendor.key" (Claude, DeepSeek, Kimi, Qwen):** Ortogonales, no hay dependencia técnica directa.
- **"Suricata primero, Vault después" (ChatGPT, Gemini):** No reabrir infraestructura CI recién estabilizada.

**Condición clave señalada por Qwen y Kimi:** Si Suricata usa firmas o reglas firmadas por `vendor.key`, Vault precede. Si no, son paralelos.

**Decisión: paralelo durante el sprint Suricata. Cierre antes de DAY 170.**

---

### Plan DAY 168 consolidado

```
P0 — Cerrar DAY 167:
  · Commit Jenkinsfile.dev + vagrant-shim.sh
  · docs/KNOWN-FAILS.md (KNOWN-FAIL-VM-PERF-001)
  · docs/BACKLOG.md (DEBT-PACKAGE-DEB-001, DEBT-DEPLOY-VAGRANT-001)
  · Tag v0.9.5-day167

P0 — DEBT-ARGUSPP-NTP-001:
  · chrony en provision.sh
  · health-check offset >1s con guard CI/PROD
  · (< media sesión)

P1 — BACKLOG-CRYPTO-VENDOR-KEY-001:
  · vendor.key → Vault dev
  · variable Jenkins VAULT_ADDR + token
  · paralelo al sprint Suricata

P2 — DEBT-ARGUSPP-SURICATA-001:
  · integración Vagrantfile
  · EMECAS++ gate
  · (~2 sesiones)
```

---

*8/8. Via Appia Quality. Buenas noches, Alonso.*