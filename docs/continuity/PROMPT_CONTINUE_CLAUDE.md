DAY 164 — aRGus NDR (arXiv:2604.04952)

Estado: main @ v1.0.0-day166. EMECAS++ 3 actos verdes. Rama enterprise mergeada.

PRIORIDAD DAY 164:
BACKLOG-CI-ENTERPRISE-001 — Jenkins gate `make emecas++` (post-merge, hardware FEDER pendiente).
ADR-048 F2 — DEBT-ARGUSPP-NTP-001 (NTP+chrony P0) + DEBT-ARGUSPP-COMMUNITY-ID-001 (P0).
DEBT-ARGUSPP-SURICATA-001 — Integrar Suricata en Vagrantfile + EMECAS.

CERRADO DAY 163:
- Bug CMake: test_ntp_health_check triplicado en common/CMakeLists.txt. Fix: sed elimina líneas 291-302 y 387-398. EMECAS++ verde en 1h 3m 26s.
- BACKLOG-CRYPTO-VENDOR-KEY-001 ✅ (Modelo B efímero).
- BACKLOG-CRYPTO-HOT-RELOAD-001 ✅ (CryptoProviderHandle RCU 9/9 tests).
- ADR-045 v2 aprobado (Consejo 8/8).
- DEBT-CMAKE-GRAPH-INVARIANTS-001 abierta (lint CI, propuesta ADR-028).

CONSEJO DAY 163 (8/8):
- P1 CMake: `if(NOT TARGET)` invariante obligatorio. Bloques condicionales no crean targets.
- P2 Fase 1: AppRole + vendor.key + test aislamiento = los tres o no cierra (posición dura Claude/ChatGPT/Grok/Kimi/DeepSeek). Gemini/Qwen aceptan ENV VAR sola como Fase 1.
- P3 Acto I: suficiente con compilación + UTs hasta cerrar BACKLOG-CRYPTO-VENDOR-KEY-001.
- Pendiente responder a Gemini: ciclo de vida credencial temporal Jenkins→Vault.
- Typo "DAY 167" en commit: regresión fue sesión anterior sin número asignado.

REGLAS NUEVAS:
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
- EMECAS++ = 3 actos (I arranque Vault, II rotación live, III Vault fault inject zero downtime).
- VaultProvider caché RCU implementación del Acto III.

ENTORNO: macOS M2 Pro, Vagrant/VirtualBox Debian Bookworm, vagrant/dev/.
STACK: ZeroMQ + ChaCha20-Poly1305 + Ed25519 + libsodium 1.0.19, eBPF/XDP, etcd-server, Vault dev.
KEYPAIR ACTIVO: c76e5e10e2a5a5ebcbf249a2d36a2a18d88b05aa75552bb7042353221484cf90 (efímero, regenera en EMECAS).
REGLA: Python3 heredoc en macOS. vagrant ssh -c siempre con -c. -Werror permanente. Nunca direct merge a main. EMECAS++ antes de cualquier merge enterprise.