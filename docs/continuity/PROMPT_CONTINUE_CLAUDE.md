DAY 158. Rama: feature/day157-autonomy-state-persistence (pendiente merge → main → v0.9.2-day157).

EMECAS DAY 157: TODO VERDE. 4 deudas P1/P2 cerradas:
✅ DEBT-AUTONOMY-STATE-PERSISTENCE-001 (autonomy_state_writer.h, 9/9 tests, etcd STEP 0c)
✅ DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 (bootstrap-status.json firmado Ed25519, atómico)
✅ DEBT-KEYPAIR-LIFECYCLE-PROD-001 (provision.sh 3 niveles, ARGUS_ENV=prod→exit 1)
✅ DEBT-CRYPTO-RECONCILIATION-001 (shared_mode + staleness guard 30s, 9/9 tests T9)

Consejo 8/8 identificó B2 pendiente antes del merge:
🔴 B2 — ExecStartPre= vs ExecStartPost=: el check de bootstrap-status.json debe
ir en ExecStartPre= de los servicios dependientes, no en ExecStartPost= del
etcd-server (fichero ya no existe en ese momento). Actualizar
DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 y docs/BACKLOG.md con la
corrección arquitectónica.

Keypair activo: b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa
Paper: arXiv:2604.04952, Draft v24 local.
Dev: macOS M2 Pro + Vagrant/VirtualBox + Debian Bookworm.
EMECAS: vagrant destroy -f && vagrant up && make bootstrap && make test-all

PENDIENTES P2 post-DAY 157 (Consejo):
- fsync(dirfd) en autonomy_state_writer.h (Kimi — garantía POSIX completa)
- staging=prod en keypair policy (ChatGPT/Kimi — P2 post-FEDER)
- Monotonic counter anti-replay en autonomy_state_writer.h (ChatGPT/Grok)
- DEBT-CRYPTO-AUTONOMY-001 (circuit breaker 30 días EXTENDED_AUTONOMY)
- ADR-046 PENDING-REVISION (3 condiciones para cierre)
- BACKLOG-ZMQ-TUNING-001 → BACKLOG-BENCHMARK-CAPACITY-001

PROTOCOLO DAY 158: PR feature/day157 → main → EMECAS en main → tag v0.9.2-day157.
Luego: B2 o DEBT-CRYPTO-AUTONOMY-001 según energía disponible.