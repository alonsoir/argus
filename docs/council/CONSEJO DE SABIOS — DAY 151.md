Main sincronizado. Ahora el prompt del Consejo:

---

**CONSEJO DE SABIOS — DAY 151 — aRGus NDR (arXiv:2604.04952)**

**Contexto del proyecto:**
aRGus NDR es un sistema C++20 de Network Detection & Response open-source dirigido a infraestructura crítica (hospitales, municipios, escuelas) que no puede permitirse soluciones enterprise. Arquitectura: 6 componentes C++20 (sniffer eBPF/XDP, ml-detector XGBoost, etcd-server, firewall-acl-agent, rag-ingester, rag-security), ZeroMQ + ChaCha20-Poly1305, Ed25519, FAISS/TinyLlama RAG. Modelo open-core: plugin system como mecanismo de licencias.

**Lo que hemos hecho DAY 151:**

Se ha implementado la abstracción `ICryptoProvider` completa (ADR-044):

1. **`ICryptoProvider`** — interfaz abstracta con `get_material()`, `refresh()`, `is_healthy()`, `component_name()`
2. **`SeedFileProvider`** (community) — lee `seed.bin` via `SeedClient` y deriva keypair Ed25519 con `crypto_sign_seed_keypair()` (misma derivación que VaultClient, Kimi D12)
3. **`VaultProvider`** (enterprise) — wrapper delgado sobre `VaultClient` existente
4. **`CryptoProvider::create()`** — factoría, único punto donde vive `#ifdef ARGUS_VAULT_ENABLED`
5. **`libcrypto_provider.so`** — instalada, 10 tests unitarios con fixture propio (sin root), todos verdes
6. **Integración etcd-server** — STEP 0 en arranque: `ICryptoProvider::create()` → fingerprint Ed25519 → `/run/argus/etcd-bootstrap-status.json` (0600) → eliminado tras `g_server->start()`. Verificado en log real: `fingerprint: 0079087736d9d62a...`
7. **Decisión arquitectónica Opción B (SRP)**: `SeedClient`+`CryptoTransport` (canal ZeroMQ) y `ICryptoProvider` (identidad Ed25519) son responsabilidades separadas. `CryptoTransport` no se tocó.
8. **`DEBT-VAULT-CONFIG-HARDCODED-001`** documentada (P2 post-FEDER)
9. `make test-all` verde: 55+ tests pasados, pipeline 6/6 RUNNING
10. PR mergeado a main @ `9e692a4e`

**Deudas P1 pendientes pre-FEDER:**
- `DEBT-CRYPTO-AUTONOMY-001`: máquina de estados `NORMAL → EXTENDED_AUTONOMY → RECONCILIATION → REVOKED` en `vault_client.cpp`
- `DEBT-FIREWALL-AUTONOMY-MODE-001`: `firewall-acl-agent` detecta `EXTENDED_AUTONOMY` → default-deny tráfico nuevo
- `DEBT-ALERTING-EDGE-SOS-001`: `scripts/alerts/sos_vault_unreachable.sh` webhook Discord/Telegram/email
- `DEBT-EMECAS-DUAL-COMPILATION-001`: Jenkinsfile stages paralelos `VAULT_ENABLED=ON` + `OFF`
- `DEBT-CRYPTO-RECONCILIATION-001`: handshake `key_version` con Vault tras recuperación

**Pregunta al Consejo:**

Para DAY 152, tenemos dos opciones de prioridad:

**Opción A — Máquina de estados primero** (`DEBT-CRYPTO-AUTONOMY-001`): Implementar `CryptoState { NORMAL, EXTENDED_AUTONOMY, RECONCILIATION, REVOKED }` en `vault_client.cpp`. Es el núcleo de la autonomía edge (escenario hospital sin conectividad). Bloquea `DEBT-FIREWALL-AUTONOMY-MODE-001` y `DEBT-ALERTING-EDGE-SOS-001`.

**Opción B — Dual compilation CI primero** (`DEBT-EMECAS-DUAL-COMPILATION-001`): Jenkinsfile con stages paralelos `community` (VAULT_ENABLED=OFF) y `enterprise` (ON). Cierra la deuda de calidad antes de seguir añadiendo código. Menor impacto funcional pero mayor robustez del pipeline CI.

**Preguntas concretas:**
1. ¿Opción A o B para DAY 152? ¿O hay una tercera opción mejor?
2. La máquina de estados de `vault_client.cpp` tiene un riesgo: añadir lógica compleja a una clase que ya tiene jitter, cache, keepalive, etcd. ¿Recomendáis extraerla a una clase `CryptoAutonomyStateMachine` separada, o mantenerla en `VaultClient`?
3. El TTL de `EXTENDED_AUTONOMY` es configurable (circuit breaker, default 30 días). ¿Debería exponerse vía `ICryptoProvider::get_autonomy_state()` o mantenerse encapsulado en `VaultProvider`?

---

