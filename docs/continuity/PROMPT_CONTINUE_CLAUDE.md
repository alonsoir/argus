# Prompt de continuidad — DAY 154
# aRGus NDR (arXiv:2604.04952)
# 2026-05-15

## Estado — main @ DAY 153

**Rama:** main (DAY 152 + DAY 153 mergeados)
**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv

## Completado DAY 152
- CryptoAutonomyStateMachine (crypto_autonomy.h) — 4 estados, ManualClock, thread-safe
- ICryptoProvider::get_operational_mode() — default NORMAL
- VaultProvider hookea transiciones en refresh()/get_material()
- 11 tests verdes — DEBT-AUTONOMY-CLOCK-INJECTION-001 cerrada

## Completado DAY 153
- vault_types.h — tipos compartidos (rompe include circular)
- IVaultTransport: HttpVaultTransport + NullVaultTransport + StubVaultTransport
- ICacheManager: FilesystemCacheManager + NullCacheManager + InMemoryCacheManager
- VaultClient por composición — inyección de dependencias, backward-compatible
- 13 tests verdes (7 transport + 6 cache)

## Pendiente DAY 154 (P0)
- ICryptoDeriver — extraer derive_material() de VaultClient
- IEtcdRegistrar — extraer register_etcd_status() + keepalive
- DEBT-FIREWALL-AUTONOMY-MODE-001 — firewall reacciona a AUTONOMOUS

# Documentar el backlog de resiliencia
# en docs/BACKLOG.md y docs/adr/ADR-046-crypto-rotation-protocol.md

## Deudas activas
- DEBT-AUTONOMY-STATE-PERSISTENCE-001 (P1)
- DEBT-AUTONOMY-ZMQ-EVENTS-001 (P1)
- DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 (P1)
- BACKLOG-ZMQ-TUNING-001
- BACKLOG-BENCHMARK-CAPACITY-001

## Protocolo de arranque DAY 154 — OBLIGATORIO
1. EMECAS completo en main:
   vagrant destroy -f && vagrant up && make bootstrap && make test-all
   make hardened-full && make check-prod-all
2. Solo si EMECAS verde → nueva rama:
   git checkout -b feature/adr045-vaultclient-decomposition-day154
3. Arrancar con ICryptoDeriver

## Reglas permanentes
1. Makefile es única fuente de verdad
2. macOS: nunca sed -i sin -e ''. Usar Python3 inline
3. EMECAS antes de cualquier merge
4. Push directo a main BLOQUEADO
5. #ifdef ARGUS_VAULT_ENABLED solo en crypto_provider.cpp
6. Migración por canal: sniffer+ml-detector simultáneamente
7. Qwen se identifica como DeepSeek — registrar siempre como Qwen
8. Calidad sobre fechas

## Keypair activo
Post-destroy DAY 133: b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa