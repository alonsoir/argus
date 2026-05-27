# CHANGELOG — v0.4.0-phase3-hardening

**Fecha de release:** 2026-04-15  
**Rama origen:** `feature/phase3-hardening`  
**Merge:** `git merge --no-ff` → `main`  
**Tag:** `v0.4.0-phase3-hardening`  
**Paper:** arXiv:2604.04952 (Draft v15)

---

## Security

### AppArmor enforce 6/6 componentes (0 denials)
- Perfiles MAC activados en modo enforce para todos los componentes del pipeline:
  `etcd-server`, `rag-security`, `rag-ingester`, `ml-detector`, `firewall-acl-agent`, `sniffer`
- ADR-021 addendum: política de AppArmor documentada como invariante de producción
- Herramienta `tools/apparmor-promote.sh`: promote complain→enforce con monitorización
  300s y rollback automático ante cualquier denial
- Referencias: ADR-021, DEBT-APPARMOR-ENFORCE, DAY 116–118

### ADR-025 — Plugin Integrity Verification: Ed25519 + TOCTOU-safe dlopen (COMPLETADO)
- Firma offline Ed25519 de plugins con `make sign-plugins`
- Carga TOCTOU-safe: `O_NOFOLLOW` + `fstat()` + `dlopen(/proc/self/fd/N)`
- SHA-256 forensic logging en cada carga de plugin
- Pubkey hardcoded en CMakeLists.txt vía CMake variable
- Fail-closed `std::terminate()` cuando `require_signature: true`
- Keypair dev rotada tras reset DAY 117:
  `e51a91e91d72f74fe97e8a4eb883c9c6eb41dd2fc994feaf59d5ba2177720f3d`
- Lección operacional documentada: `provision.sh --reset` rota keypair;
  secuencia obligatoria post-reset: `make pipeline-build` → `make sign-plugins` → `make test-all`
- Referencias: ADR-025, DEBT-ADR025-D11, DAY 113–117

### INVARIANTE-SEED-001
- Todos los `seed.bin` de los 6 componentes deben ser idénticos (SHA-256 igual)
- Seed family post-reset DAY 117:
  `75deaca96768b5d973a4339faf2325c058969bf93c00c0d21eef703a2ab91360`
- Test automatizado `TEST-INVARIANT-SEED` integrado en `make test-all`
- Referencias: DEBT-SEED-PERM-001, DAY 117

### noclobber audit — ficheros críticos
- Auditoría de redirects `>` en `tools/provision.sh` sobre rutas sensibles:
  `/etc/`, `.sk`, `seed.bin`, `.sig`, `.pem`, `.pk`, `.env`
- Resultado: cero riesgos de clobber no intencional — audit limpio
- Referencias: REC-2, Consejo DAY 117 Q2, DAY 118

---

## Operations

### systemd units — 6 componentes
- Units instaladas y habilitadas para todos los componentes del pipeline
- Integradas en `make pipeline-start` / `make pipeline-stop`
- Referencias: DEBT-SIGN-AUTO, DAY 115

### tools/apparmor-promote.sh
- Script de promoción complain→enforce con ventana de observación configurable (300s)
- Rollback automático si se detectan denials durante la ventana
- Log estructurado con timestamps
- Referencias: DAY 117

### Backup policy — `.bak.*`
- Política de backups automáticos para ficheros sensibles modificados por provision.sh
- Formato: `<fichero>.bak.<timestamp>`
- Referencias: DAY 117

### Recovery Contract (OQ-6 ADR-024)
- Documento `docs/recovery-contract.md` formaliza el procedimiento de recuperación
  ante reset de keypair o corrupción de seed
- Paso a paso verificable y testeable
- Referencias: ADR-024, DAY 117

### set-build-profile.sh
- Script centralizado para activar perfiles de build (debug/release/profile)
  en los 6 componentes simultáneamente
- References: DAY 115–116

---

## Tests

### TEST-PROVISION-1 — CI Gate PHASE 3 (8/8 checks)
1. Claves criptográficas — integridad 6/6 componentes
2. Firmas de plugins (producción) — ADR-025 D1
3. Configs de producción sin dev plugins
4. build-active symlinks
5. systemd units instalados
6. Permisos ficheros sensibles
7. Consistencia JSONs con plugins reales
8. apparmor-utils instalado

### TEST-INVARIANT-SEED
- Verifica que todos los `seed.bin` son idénticos (SHA-256)
- Integrado en `make test-all`

### TEST-APPARMOR-ENFORCE
- Verifica 6/6 perfiles en modo enforce via `aa-status`
- Sin denials tras ventana de observación 300s por componente

### TEST-INTEG-4a/4b/4c/4d/4e + TEST-INTEG-SIGN (6/6 PASSED)
- Suite de integración de plugins ADR-025
- Cobertura: carga, firma, verificación, fail-closed, TOCTOU

### make test-all — resultado final DAY 118
```
🎉 ALL TESTS PASSED
TEST-PROVISION-1     8/8  ✅
TEST-INVARIANT-SEED       ✅
TEST-INTEG-4a             ✅
TEST-INTEG-4b             ✅
TEST-INTEG-4c             ✅
TEST-INTEG-4d             ✅
TEST-INTEG-4e             ✅
TEST-INTEG-SIGN           ✅
AppArmor enforce    6/6   ✅
```

---

## Bug Fixes

### DEBT-VAGRANTFILE-001
- Vagrantfile corregido: dependencias de provisioning en orden correcto
- Referencias: DAY 117

### DEBT-SEED-PERM-001
- Permisos de `seed.bin` corregidos: `600` (solo lectura por owner)
- Verificado en Check 6/8 de TEST-PROVISION-1
- Referencias: DAY 117

### DEBT-RAG-BUILD-001
- Pipeline de build de rag-ingester corregido
- Symlink `build-active` apuntando correctamente tras reset
- Referencias: DAY 117

### DEBT-HELLO-001
- Plugin `libplugin_hello.so` excluido de configs de producción
- Verificado en Check 3/8 de TEST-PROVISION-1
- Referencias: DAY 115

### REC-2 — noclobber
- Redirects peligrosos en provision.sh auditados y documentados
- Referencias: DAY 117–118

---

## DEBTs no bloqueantes — trasladados a features futuras

| DEBT | Feature destino |
|------|----------------|
| DEBT-CRYPTO-003a | feature/crypto-hardening |
| DEBT-OPS-001/002 | feature/ops-tooling |
| DEBT-TOOLS-001 | feature/adr026-xgboost |
| DEBT-SNIFFER-SEED | feature/crypto-hardening |
| DEBT-FD-001 | feature/adr026-xgboost |
| DEBT-INFRA-001 | feature/bare-metal |
| DEBT-CLI-001 | feature/adr032-hsm |
| docs/CRYPTO-INVARIANTS.md | feature/crypto-hardening |
| ADR-033 TPM | post-PHASE 4 |

---

## Roadmap siguiente — PHASE 4

- **feature/adr026-xgboost:** XGBoost/RF como plugins especializados (Track 1, Year 1)
  Gate de entrada: Precision ≥ 0.99 + F1 ≥ 0.9985 + revisión Consejo
- **feature/crypto-hardening:** DEBT-CRYPTO-003a + DEBT-SNIFFER-SEED + CRYPTO-INVARIANTS
- **ADR-029:** Variantes hardened — Variant A (Debian+AppArmor+eBPF/XDP),
  Variant B (Debian+AppArmor+libpcap), Variant C (seL4+libpcap, research)
- **ADR-024 Noise_IKpsk3:** Group Key Agreement — implementación post-arXiv

---

*aRGus NDR — "un escudo, nunca una espada"*  
*Via Appia Quality · piano piano · pasito a pasito*