Redacto el post para el Consejo:

---

**🏛️ CONSEJO DE SABIOS — DAY 157 — aRGus NDR**
**Rama:** `feature/day157-autonomy-state-persistence`
**Tag anterior:** `v0.9.1-day156`

---

**Resumen del trabajo:**

Cuatro deudas técnicas cerradas en esta sesión:

**1. DEBT-AUTONOMY-STATE-PERSISTENCE-001 (P1)**
`common/autonomy_state_writer.h` — header-only. Escribe/lee estado `CryptoAutonomyStateMachine` firmado Ed25519 en `/var/lib/argus/crypto-autonomy-state.json`. Escritura atómica (write → fsync → rename). Lectura fail-safe: firma inválida/ausente/AUTONOMOUS expirado >24h → NORMAL. 9/9 tests RED→GREEN. Integrado en etcd-server STEP 0c: leer estado al arrancar, escribir en cada transición del health-check loop.

**2. DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 (P1)**
`etcd-server/src/main.cpp` STEP 0: `bootstrap-status.json` ahora firmado Ed25519. JSON canónico (claves ordenadas, sin `signature_hex`) → `crypto_sign_detached` → campo `signature_hex` añadido. Escritura atómica tmp→rename+fsync. Misma cadena de confianza que ADR-025 plugins. Ningún consumidor lo verifica todavía — registrado como DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 (P2).

**3. DEBT-KEYPAIR-LIFECYCLE-PROD-001 (P1)**
`tools/provision.sh` función `generate_keypair()`: política 3 niveles.
- `ARGUS_ENV=prod` + keypair ausente → `exit 1`, NUNCA genera silenciosamente
- `ARGUS_ENV=dev/staging` (default) → genera normalmente
- Keypair existente en cualquier env → skip sin cambios

**4. DEBT-CRYPTO-RECONCILIATION-001 (P2)**
`AutonomySubscriber` arquitectura final:
- `last_known_mode_` (`atomic<FirewallAutonomyMode>`) actualizado en `handle_message()` y reconciliador
- `shared_ptr<atomic<FirewallAutonomyMode>>` compartido entre subscriber y `poll_callback` — resuelve ordering sin segundo socket
- `poll_callback` en `main.cpp` retorna `shared_mode->load()` — sin segundo socket (MVP)
- Feature flag `use_dedicated_health_channel=false`
- Constructor acepta `shared_mode` opcional (`nullptr` = backward compat)
- 8/8 tests PASSED (T7: `last_known_mode()` vía ZMQ, T8: `shared_mode` vía ZMQ)

**Nueva deuda registrada:**
- DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 (P2): `check-bootstrap-status.sh` + systemd `ExecStartPost=` verificando firma antes de iniciar dependientes

**EMECAS pendiente:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`

---

**Preguntas para el Consejo (8 modelos):**

1. **DEBT-AUTONOMY-STATE-PERSISTENCE-001**: ¿Algún vector de ataque no cubierto en la lectura fail-safe? ¿La expiración de 24h para AUTONOMOUS es el umbral correcto para producción hospitalaria?

2. **DEBT-BOOTSTRAP-STATUS-SIGNATURE-001**: El fichero es efímero (se borra tras `g_server->start()`). ¿Tiene sentido que systemd lo verifique en `ExecStartPost=` dado que ya no existe en ese momento? ¿O el check debe hacerse antes del `start()`?

3. **DEBT-KEYPAIR-LIFECYCLE-PROD-001**: ¿Debería `ARGUS_ENV=staging` también requerir keypair preexistente, o la política dev/staging-igual es correcta para este proyecto?

4. **DEBT-CRYPTO-RECONCILIATION-001**: El `poll_callback` actual retorna `shared_mode->load()` — que es el último modo conocido vía ZMQ. En un escenario donde el ZMQ publisher (etcd-server) muere silenciosamente, el reconciliador seguirá devolviendo el último modo conocido indefinidamente. ¿Es suficiente para FEDER o necesitamos un timeout de staleness?

5. **Arquitectura general DAY 157**: ¿Alguna inconsistencia entre las cuatro deudas cerradas que deba resolverse antes del merge a main?

---
