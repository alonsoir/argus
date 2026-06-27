
**CONSEJO DE SABIOS — DAY 113 — SESIÓN DE CIERRE**

*Proyecto: aRGus NDR (ML Defender) | Rama: feature/plugin-integrity-ed25519*

---

## Resumen ejecutivo del día

DAY 113 cerró dos frentes en paralelo:

**Frente 1 — ADR-025 (Plugin Integrity Verification): IMPLEMENTADO**
El plugin-loader de aRGus NDR ahora verifica criptográficamente cada plugin `.so` antes de cargarlo. La implementación cubre los 9 decisiones del ADR (D1-D9):

- **D1**: Firma Ed25519 offline obligatoria. Clave privada nunca en host de producción.
- **D2**: `O_NOFOLLOW` + `fstat()` + size check (MIN 4KB, MAX 10MB para `.so`; MAX 512B para `.sig`).
- **D3**: Prefix check `/usr/lib/ml-defender/plugins/` con `weakly_canonical()` antes de cualquier `open()`.
- **D4**: FD discipline — el fd permanece abierto sin interrupción desde `open()` hasta después de `dlopen("/proc/self/fd/N")`.
- **D5**: Mismo patrón fd para el fichero `.sig`.
- **D6**: SHA-256 forense antes de la verificación Ed25519 (hash + size + mtime en log).
- **D7**: Clave pública hardcodeada en el binario via CMake (`MLD_PLUGIN_PUBKEY_HEX`). No en fichero, no en config — en el binario compilado.
- **D9**: Fail-closed — `std::terminate()` si `require_signature:true` (default producción). `MLD_ALLOW_DEV_MODE=1` para fail-open en desarrollo.

Infraestructura de soporte:
- `tools/provision.sh`: nueva función `provision_plugin_signing_keypair()` — bootstrapping único, skip si ya existe, muestra el hex de la pubkey para inyección en CMake.
- `tools/provision.sh sign`: firma todos los `.so` en `/usr/lib/ml-defender/plugins/`.
- `make sign-plugins`: target repetible en cada build/deploy.
- JSON configs (5 componentes): `require_signature: true` + `allowed_key_id: "ed25519:2026-04-prod"`.

**Tests (7/7 PASSED):**
- SIGN-1: Firma válida → carga exitosa
- SIGN-2: Firma inválida → `Ed25519 INVALID` + skip
- SIGN-3: `.sig` ausente → CRITICAL + skip
- SIGN-4: Symlink attack → `O_NOFOLLOW` rechaza
- SIGN-5: Path traversal en JSON config → prefix check rechaza
- SIGN-6: Clave rotada (mismatch) → rechazado
- SIGN-7: Plugin truncado → size check rechaza (< 4KB)

Suite completa: **make test: 11/11 PASSED** (4a+4b+4c+4e+SIGN-1..7).

**Frente 2 — Paper Draft v14: COMPILACIÓN LIMPIA**
Cuatro inserciones motivadas por Project Glasswing / Claude Mythos Preview (anunciado esta semana por Anthropic — modelo frontier que encontró vulnerabilidades de escalada de privilegios en el kernel Linux de forma autónoma):

- §Related Work: párrafo "AI-native security reasoning" — sitúa el paper en el contexto de abril 2026.
- §Threat Model: nueva subsección "Kernel Security Boundary (Explicit Axiom)" — axioma explícito: el kernel se asume no comprometido; esto es un límite de scope declarado, no un oversight.
- §Limitations 10.12: "Kernel Security Boundary" — fuera del enumerate de 10.11, al mismo nivel que 10.1-10.11.
- §Future Work 11.17: "Hardened Deployment Variants (ADR-030, ADR-031)" — AppArmor enforcing y seL4/Genode como respuesta arquitectónica.

arXiv Replace v13 pendiente — Scholar bloqueó verificación por rate limit. Subir cuando confirme indexación de v1 (arXiv:2604.04952).

---

## Preguntas para el Consejo

**Q1 — PR timing: ¿feature/plugin-integrity-ed25519 → main ahora o esperar?**

ADR-025 está completo con 11/11 tests. La rama `feature/plugin-integrity-ed25519` tiene tres commits limpios. Argumentos a favor del merge inmediato: PHASE 2 completa + ADR-025 completa = rama estable. Argumentos para esperar: provision.sh `--reset` (D11, rotación de claves) no está implementado todavía. ¿Es `--reset` un bloqueante para merge a main, o es deuda técnica aceptable post-merge?

**Q2 — provision.sh --reset (ADR-025 D11): ¿implementar ahora o diferir?**

D11 especifica una operación de rotación manual de claves con: confirmación interactiva escribiendo literalmente `RESET-KEYS`, timestamp en el nombre de la nueva clave, movido de `.sig` existentes a `invalidated/<timestamp>/`, mensaje explícito de que el pipeline no arrancará hasta re-firmar. No es bloqueante operacionalmente (las claves actuales son válidas), pero es una deuda de seguridad real. ¿P1 antes del merge a main, o P2 post-merge?

**Q3 — Próxima prioridad técnica: ¿PHASE 3 o ADR-026?**

El backlog tiene dos candidatos naturales:
- **PHASE 3** (pipeline hardening): systemd units con `Restart=always` + `unset LD_PRELOAD`, AppArmor profiles básicos para los 6 componentes, CI gate formal para `TEST-PROVISION-1`.
- **ADR-026** (Fleet Telemetry + XGBoost + BitTorrent distribution): aprobado en DAY 104 por el Consejo con veredictos claros (XGBoost sobre FT-Transformer unánime, HTTPS:443 como protocolo de telemetría, Precision≥0.99 gate para entornos médicos). Más ambicioso, más impacto en el paper v2.

¿Cuál tiene mayor retorno en este momento del proyecto?

**Q4 — DEBT-TOOLS-001: ¿scope correcto?**

Los tres synthetic injectors (`synthetic_sniffer_injector.cpp`, `synthetic_ml_output_injector.cpp`, `generate_synthetic_events.cpp`) usan ZeroMQ + crypto-transport pero no integran plugin-loader. Para que los stress tests sean representativos del comportamiento real de los componentes, deberían instanciar `PluginLoader` y cargar plugins firmados. Se ha registrado como DEBT-TOOLS-001 (P3). ¿Está correctamente priorizado como P3, o debería subir a P2 antes de cualquier stress test formal?

**Q5 — Paper: ¿el párrafo Glasswing/Mythos es correcto en tono y precisión?**

El párrafo en §Related Work dice:

> *"This paper was written and submitted in April 2026, a moment marked by the emergence of AI systems capable of sophisticated reasoning about kernel-level threat models — including Anthropic's Glasswing project and its Mythos Preview capability, which demonstrated that AI-assisted security analysis can reason about low-level attack surfaces with a depth previously requiring specialized human expertise."*

Project Glasswing encontró vulnerabilidades en **todos los sistemas operativos principales y todos los navegadores principales**, incluyendo escalada de privilegios en el kernel Linux. ¿El tono del párrafo es adecuado? ¿Demasiado deferente, demasiado técnico, o correcto para un paper cs.CR?

---

## Contexto para valorar las respuestas

- Proyecto: open-source, MIT, objetivo hospitales/escuelas/municipios sin presupuesto enterprise.
- Metodología: TDH (Test-Driven Hardening) + Consejo de Sabios multi-LLM.
- Estado actual: PHASE 2 completa (5/5 componentes), ADR-025 completo, paper en arXiv.
- Recursos: investigador independiente, un desarrollador, sin financiación institucional.
- Filosofía: *"la verdad por delante, siempre"* — las limitaciones se documentan explícitamente.

Gracias por vuestro tiempo y rigor.

