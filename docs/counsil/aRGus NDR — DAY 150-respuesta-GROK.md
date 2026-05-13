Se ruega a los miembros del consejo que acudan a responder a las preguntas que lanzamos para el proyecto aRGus y nos den su valioso expertise en sistemas distribuidos de alto rendimiento en c++.

Perfecto. Empezamos con la publicación para el Consejo.

---

## aRGus NDR — DAY 150 — Publicación Consejo de Sabios

### LO QUE HEMOS HECHO HOY

**EMECAS DAY 150 — verde completo**
Main @ `93b4d39c`. 4 PRs mergeados. 0 fallos.

Fix menor: `parquet-convert` y `test-parquet` ejecutaban en macOS host en lugar de la VM — patrón `vagrant ssh -c` aplicado igual que el resto del Makefile.

**Email a Dr. Andrés Caro Lindo**
Enviado con propuesta de inventario hardware (~460€: RPi5×2 + N100×2 + switch), justificación científica del delta eBPF/libpcap en bare-metal, generación de datasets con red team/pentesters bajo paraguas UEx/INCIBE, y solicitud de tiempo de cómputo en supercomputador UEx en modo VM (no bare-metal — eBPF requiere acceso kernel, incompatible con recurso compartido).

**ADR-044 implementado — tres PRs:**

*PR #70 — `provision_crypto.sh`*
Script Bash que arranca Vault en modo dev, habilita KV v1 en `argus/`, genera seeds aleatorios de 32 bytes por familia (A, B, C) y etcd (bootstrap especial) bajo paths `argus/{env}/families/family_{X}/seed` y `argus/{env}/components/etcd/seed`. Idempotente: SKIP si existe, `--force` para regenerar. Assert `seed_dev != seed_prod` en env=prod. Artifact de auditoría `crypto_audit.json` con fingerprints `sha256(seed)`. Targets Makefile: `provision-crypto` y `provision-crypto-force`.

*PR #71 — `vault_client.h/.cpp`*
Librería C++20 `libvault_client.so`. API: `VaultClient::fetch_crypto_material()`. Derivación correcta (Kimi D12): `kdf_derive(master_seed, component_index, ctx) → component_seed → sign_seed_keypair → (pk, sk)`. Fingerprint = `sha256(pk)` (Kimi D13). Jitter anti-stampede: `component_index * 500ms + rand(0..1000ms)`. Cache tmpfs TTL configurable (1h dev, 72h prod), permisos 0700. Edge autonomy: Vault KO + cache válida → `OK_FROM_CACHE` + WARN; Vault KO + cache vacía → `exit(1)`. `mlock()` opcional con WARNING si falla. `register_etcd_status()` y keepalive documentados como stub (DEBT-CRYPTO-HEARTBEAT-001). 5/5 tests PASS. Targets: `vault-client-build/clean/test`, añadido a `pipeline-build`.

*PR #72 — Jenkinsfile*
Stage `Provision Crypto — Vault (ADR-044)` insertado entre `Quick Check` y `Deploy Configs`. Condicional: main siempre, otras ramas si `PROVISION_CRYPTO=true`. `env=prod` en main, `env=dev` en ramas. Artifact `crypto_audit_${BUILD_NUMBER}.json` archivado. `error()` bloquea pipeline si Vault KO. Parámetros nuevos: `PROVISION_CRYPTO`, `FORCE_PROVISION_CRYPTO`.

**Decisión arquitectónica open-core registrada**
`seed-client` + `seed.bin` = edición community (open source, permanente).
`VaultClient` + Vault = edición enterprise (governance criptográfico avanzado).
Flag CMake: `ARGUS_VAULT_ENABLED` (OFF por defecto). Misma compilación, mismo F1=0.9985, diferente governance.

---

### LO QUE HAREMOS MAÑANA (DAY 151)

**P0 — Integración `etcd-server` con `VaultClient`**
`etcd-server` es el componente bootstrap especial — el primero en arrancar, sin barrera etcd disponible. Integración con compilación condicional `#ifdef ARGUS_VAULT_ENABLED`. Dos rutas validadas con tests:
- `ARGUS_VAULT_ENABLED=ON` → `VaultClient::fetch_crypto_material()` → deriva keypair → registra en etcd
- `ARGUS_VAULT_ENABLED=OFF` → `seed-client` legacy → comportamiento actual sin cambios

**P1 — DEBT-CRYPTO-HEARTBEAT-001**
Implementar `register_etcd_status()` real y keepalive de lease (TTL=10s, cada 5s) en `vault_client.cpp`. Stub documentado, pendiente de integración con `EtcdServiceRegistry`.

**P1 — Ansible Jinja2**
4 componentes sin template: `firewall-acl-agent`, `etcd-server`, `rag-ingester`, `rag-security`. Regla crítica: JSONs originales intocables, Ansible genera `*.dev.json` / `*.prod.json` separados.

---

### PREGUNTAS AL CONSEJO

**Q1 — Compilación condicional vs dos binarios**
La propuesta es `#ifdef ARGUS_VAULT_ENABLED` en el mismo código fuente. Alternativa: dos binarios separados `etcd-server` (community) y `etcd-server-enterprise`. ¿Cuál es más mantenible a largo plazo? ¿Hay riesgo de divergencia silenciosa con `#ifdef`?

**Q2 — Orden de migración de componentes**
Propuesta: `etcd-server` primero (bootstrap especial), luego `sniffer`, `ml-detector`, `firewall-acl-agent`, `rag-ingester`, `rag-security`. ¿Algún componente debería ir antes o después por razones de dependencia o riesgo?

**Q3 — `register_etcd_status` sin etcd disponible en bootstrap**
`etcd-server` arranca sin barrera etcd (Consejo DAY 149 Q3). Cuando implementemos `register_etcd_status()` real, `etcd-server` no puede registrarse en sí mismo antes de arrancar. ¿La solución correcta es que `etcd-server` escriba su estado crypto en un fichero local (`/run/argus/etcd-crypto-status.json`) en lugar de en etcd, y que los demás componentes lo lean de etcd normalmente?

**Q4 — Cache tmpfs y `vagrant destroy`**
El cache en `/run/argus/crypto-cache/` se pierde en cada `vagrant destroy` porque `/run` es tmpfs. En EMECAS esto es correcto — cada ciclo debe ir a Vault. Pero en producción edge (nodo que reinicia por corte de luz), el cache también se pierde y el nodo necesita Vault disponible en el arranque. ¿La solución correcta es un cache persistente en `/etc/ml-defender/{component}/crypto-cache/` con permisos 0600 para producción, manteniendo tmpfs solo para dev?

**Q5 — open-core: `ARGUS_VAULT_ENABLED` como único separador**
La decisión de hoy: `seed-client` = community, `VaultClient` = enterprise, separados por flag CMake. ¿Es suficiente este único punto de separación o hay otras funcionalidades que deberían ir detrás del flag enterprise? ¿Falco actuation, Neo4j graph, OpenCanary honeypot?

