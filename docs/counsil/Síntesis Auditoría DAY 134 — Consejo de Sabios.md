# Síntesis del Consejo de Sabios — DAY 134 (8/8)

---

## Q1 — Atomicidad de `make hardened-full`

**Consenso: 8/8** — Fail-fast obligatorio para el target principal. Divergencia en checkpoints.

| Modelo | Posición |
|--------|----------|
| Claude | Checkpoints con ficheros sentinel `.build-complete` |
| ChatGPT | Fail-fast + separación `prod-build-x86` (cacheable) / `prod-deploy-x86` (siempre) |
| DeepSeek | Fail-fast en `hardened-full` + target separado `hardened-continue` con marcadores manuales |
| Gemini | Fail-fast + fichero sentinel para skip de compilación |
| Grok | Fail-fast + stamps `.stamp` + flag `CONTINUE=1` opcional |
| Kimi | Dos targets: `hardened-full` (fail-fast, EMECAS sagrado) + `hardened-resume` (checkpoints, dev) |
| Mistral | Fail-fast + `hardened-clean` + checkpoints documentados en `docs/EMECAS.md` |
| Qwen | Pasos idempotentes con tracking en `.hardened-state/` + gates de seguridad siempre completos |

**Decisión arquitecto:** Dos targets. `make hardened-full` (fail-fast, destroy incluido — EMECAS sagrado para demo FEDER y validación). `make hardened-redeploy` (sin destroy, para iteración durante desarrollo). Los gates `check-prod-all` se ejecutan **siempre** en ambos.

---

## Q2 — Semillas en la hardened VM

**Consenso: 7/8** — NO transferir semillas en el EMECAS. Los 7 WARNs son correctos por diseño.

Única divergencia: **Gemini** propone transferencia "out-of-band" durante el deploy para que `check-prod-permissions` pase de WARN a PASS. Los demás 7 rechazan esto.

**Razonamiento consolidado:** Las semillas son material criptográfico de operación, no de build. Una hardened VM sin semillas en el EMECAS es el estado correcto — simula la imagen estéril que llega al hospital antes del primer arranque real. El WARN debe convertirse en INFO documentado. Se crea target separado `prod-deploy-seeds` para el momento del deploy real, con transferencia vía `scp -F vagrant-ssh-config` (REGLA PERMANENTE DAY 129).

**Decisión arquitecto:** Gemini queda en minoría. Los WARNs se convierten en INFO. `prod-deploy-seeds` como target explícito post-EMECAS.

---

## Q3 — Idempotencia

**Divergencia genuina 5/3:**

- **Fail-fast + no idempotente (5/8):** Claude, ChatGPT, DeepSeek, Kimi, Mistral — `hardened-full` siempre destruye. La REGLA EMECAS aplica a la hardened VM.
- **Idempotente por defecto (3/8):** Grok, Qwen, Gemini — idempotencia estándar en IaC; destrucción solo para releases y demos FEDER.

**Punto de convergencia:** Todos acuerdan que debe existir un modo de iteración rápida sin destroy para el desarrollo de perfiles AppArmor y reglas Falco.

**Decisión arquitecto:** La separación de los dos targets resuelve la divergencia. `hardened-full` no idempotente (REGLA EMECAS). `hardened-redeploy` idempotente (iteración). Documentado explícitamente en `docs/EMECAS-hardened.md`.

---

## Q4 — Falco .deb como artefacto versionado

**Consenso: 8/8** — No commitear en el repo. Nunca Git LFS. Verificación SHA-256 obligatoria.

Convergencia en la solución: directorio `dist/debs/` o `vendor/` excluido de git, con hash SHA-256 pinneado en el Makefile o en un manifiesto `dist/falco-manifest.json`. El hash sí se committea. El .deb no.

**Aportación destacada de Qwen:** manifiesto JSON explícito:
```json
{
  "version": "0.43.1",
  "url": "https://download.falco.org/...",
  "sha256": "<hash>",
  "verified_by": "make check-falco-manifest"
}
```

**Decisión arquitecto:** Directorio `dist/vendor/` gitignored. `dist/vendor/CHECKSUMS` con SHA-256 committeado. Target `make vendor-download` que descarga y verifica. Si hash no coincide → abort. El .deb actual (`falco_0.43.1_amd64.deb`) ya está en `/vagrant` — lo movemos a `dist/vendor/` y documentamos.

---

## Q5 — `confidence_score` prerequisito ADR-040

**Consenso: 8/8** — Ambos métodos obligatorios. Inspección de código primero, test de integración segundo.

**Orden de ejecución acordado:**
1. Inspección estática — verificar que el campo existe en el `.proto` y se asigna en el código fuente. Barato, rápido, definitivo sobre existencia.
2. Test de integración ZeroMQ — capturar mensaje real con flujo conocido, verificar `confidence_score ∈ [0,1]` y que **no es constante** entre predicciones.
3. Solo cuando ambos pasen → DEBT-ADR040-002 CERRADO → desbloquear DEBT-ADR040-006 (IPW).

**Aportación crítica de Kimi y Qwen:** el campo puede existir en el código pero ser siempre `0.5` o `1.0` (valor constante). El test debe verificar variabilidad — si el score no varía entre un flow benigno y uno malicioso, IPW no tiene nada que ponderar.

**Decisión arquitecto:** Crear `scripts/check-confidence-score.sh` (inspección estática) + `tests/integration/test_confidence_score.py` (integración ZeroMQ con golden pcap determinista). Ambos en el repo. Ejecutar antes de cualquier trabajo en DEBT-ADR040-006.

---

## Observaciones adicionales del Consejo (no solicitadas)

Tres modelos destacaron algo no preguntado que merece atención:

**DeepSeek:** *"La reproducibilidad no es un lujo; es la única manera de que un hospital pueda confiar en tu software."* — La demo FEDER con `make feder-demo` debe ejecutarse desde VM fría sin trucos pregrabados. El evaluador externo debe poder reproducirla.

**Kimi:** Propone que el primer acto de DAY 135 sea ejecutar `make hardened-full` en modo EMECAS sagrado (destrucción total) para validar reproducibilidad desde cero. Cualquier fallo es bloqueante para el merge de `feature/adr030-variant-a` a `main`.

**Mistral:** Recuerda que DEBT-PROD-APT-SOURCES-INTEGRITY-001 (P2 de hoy, no completado) debe cerrarse antes de más avances en hardening. SHA-256 de `sources.list` es el único vector de ataque de supply-chain que queda abierto en la hardened VM.

---

## Acta de decisiones vinculantes DAY 135

| # | Decisión | Origen |
|---|----------|--------|
| D1 | `hardened-full` = fail-fast + destroy. `hardened-redeploy` = sin destroy, iteración | Consejo 7/8 |
| D2 | Seeds NO en EMECAS. WARNs → INFO. Target `prod-deploy-seeds` explícito | Consejo 7/8 |
| D3 | `.hardened-state/` o stamps para skip de build, gates siempre completos | Consejo 8/8 |
| D4 | `dist/vendor/CHECKSUMS` committeado, .deb gitignored, `make vendor-download` + SHA-256 | Consejo 8/8 |
| D5 | `confidence_score`: inspección estática + test ZeroMQ con golden pcap + variabilidad | Consejo 8/8 |
| D6 | DAY 135 arranca con `make hardened-full` desde VM destruida — gate pre-merge | Kimi, adoptado |
| D7 | DEBT-PROD-APT-SOURCES-INTEGRITY-001 en agenda DAY 135 antes de nuevos avances | Mistral, adoptado |

---

*Acta Consejo de Sabios — DAY 134 — 28 Abril 2026*
*8/8 modelos consultados. Decisiones del arquitecto marcadas.*
*"Piano piano. Via Appia Quality."* 🏛️