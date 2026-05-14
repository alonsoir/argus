# Prompt de continuidad — DAY 152
# aRGus NDR (arXiv:2604.04952)
# 2026-05-14

## Estado del proyecto

**Proyecto:** aRGus NDR — C++20 NDR open-source para infraestructura crítica
**Rama:** main @ `9e692a4e` (DAY 151 mergeado)
**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv
**Principio rector:** calidad sobre fechas — no hay deadline duro para FEDER

---

## Lo que acabamos de completar (DAY 151)

### ICryptoProvider — Abstracción completa (ADR-044)

**Decisión Opción B (SRP):** `SeedClient`+`CryptoTransport` (canal ZeroMQ) y `ICryptoProvider` (identidad Ed25519) son responsabilidades separadas. `CryptoTransport` no se tocó.

**Ficheros creados en `common/`:**
- `crypto_provider.h/.cpp` — interfaz `ICryptoProvider` + `CryptoProviderConfig` + factoría `CryptoProvider::create()`
- `seed_file_provider.h/.cpp` — community: `SeedClient` → `crypto_sign_seed_keypair()` → `CryptoMaterial`
- `vault_provider.h/.cpp` — enterprise: wrapper delgado sobre `VaultClient`
- `tests/test_crypto_provider.cpp` — 10 tests con fixture propio (`mkdtemp` + seed.bin 0400, sin root)
- `CMakeLists.txt` — target `crypto_provider`, option `ARGUS_VAULT_ENABLED`

**`make vault-client-test`:** 2/2 PASSED. `make test-all`: 55+ tests verdes, pipeline 6/6 RUNNING.

**etcd-server STEP 0:** `CryptoProvider::create()` → `get_material()` → fingerprint hex → `/run/argus/etcd-bootstrap-status.json` (0600) → eliminado tras `g_server->start()`. Verificado en log: `✅ ICryptoProvider OK — fingerprint: 0079087736d9d62a...`

**ADR-045 aprobado (Consejo 8/8):** VaultClient por composición — `IVaultTransport`, `ICacheManager`, `IEtcdRegistrar`, `ICryptoDeriver`, `IJitterStrategy`. Cada responsabilidad inyectable y testeable en aislamiento.

**Nuevas deudas documentadas:**
- `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` (P1 pre-FEDER): bootstrap status sin firma Ed25519
- `DEBT-AUTONOMY-STATE-PERSISTENCE-001` (P1): estado autonomía sin persistencia firmada
- `DEBT-AUTONOMY-CLOCK-INJECTION-001` (P1): Clock no inyectable en `CryptoAutonomyStateMachine`
- `DEBT-AUTONOMY-ZMQ-EVENTS-001` (P1): transiciones no emiten evento ZeroMQ

---

## Decisiones arquitectónicas activas

- **`#ifdef ARGUS_VAULT_ENABLED`:** confinado ÚNICAMENTE en `crypto_provider.cpp`. Ningún otro fichero lo ve.
- **Migración por canal:** sniffer+ml-detector simultáneamente (ZeroMQ es bilateral).
- **TTL = ventana de renovación preferente, nunca fecha de muerte.**
- **Firewall default-deny en `AUTONOMOUS`.**
- **Reconciliación obligatoria al recuperar Vault.**
- **VaultClient por composición (ADR-045):** hoy Vault, mañana cualquier backend, pasado el nuestro propio.
- **`OperationalMode`:** `NORMAL`, `AUTONOMOUS`, `RECONCILING`, `DEGRADED` — mismo contrato en community y enterprise.

---

## Plan DAY 152 (P0 — consenso Consejo 8/8)

### P0 — `CryptoAutonomyStateMachine`

**Ficheros a crear:**
- `common/crypto_autonomy.h`
- `common/crypto_autonomy.cpp`

**Requisitos:**
```cpp
enum class OperationalMode { NORMAL, AUTONOMOUS, RECONCILING, DEGRADED };

class CryptoAutonomyStateMachine {
public:
    // Tabla de transiciones explícita — no enums sueltos
    void on_vault_unreachable();   // NORMAL → AUTONOMOUS
    void on_vault_restored();      // AUTONOMOUS → RECONCILING
    void on_reconciliation_ok();   // RECONCILING → NORMAL
    void on_revocation();          // cualquier → DEGRADED
    void on_tamper_detected();     // cualquier → DEGRADED

    OperationalMode current_mode() const noexcept;  // std::atomic, sin lock
    bool can_operate() const noexcept;              // NORMAL || AUTONOMOUS || RECONCILING
};
```

**Concurrencia (¡atención!):**
- `std::mutex` para transiciones (escritura)
- `std::atomic<OperationalMode>` para lectura en hot path (consulta desde firewall sin bloquear)
- Thread-safe desde el primer día — keepalive, timer, firewall llaman desde hilos distintos

**Clock inyectable (DEBT-AUTONOMY-CLOCK-INJECTION-001):**
```cpp
template<typename Clock = std::chrono::steady_clock>
class CryptoAutonomyStateMachine { ... };
```

**Tests en aislamiento:** sin Vault, sin red, sin etcd. Solo eventos sintéticos y `ManualClock`.

### P0 — `ICryptoProvider` ampliada

Añadir `get_operational_mode()` con default `NORMAL`:
```cpp
virtual OperationalMode get_operational_mode() const noexcept {
    return OperationalMode::NORMAL;
}
```

- `SeedFileProvider::get_operational_mode()` → siempre `NORMAL` (sin lógica adicional)
- `VaultProvider::get_operational_mode()` → delega a `CryptoAutonomyStateMachine`

### P1 — ADR-045 documentado antes de tocar código

`docs/adr/ADR-045-vaultclient-decomposition.md` — YA CREADO en DAY 151.

---

## Plan DAY 153

- Descomposición `VaultClient`: `IVaultTransport` + `ICacheManager` primero
- `DEBT-EMECAS-DUAL-COMPILATION-001` — Jenkinsfile dual stage community/enterprise

## Plan DAY 154

- `IEtcdRegistrar` + `ICryptoDeriver`
- `DEBT-FIREWALL-AUTONOMY-MODE-001` — firewall reacciona a `AUTONOMOUS`

---

## Reglas permanentes (no negociables)

1. **Makefile** es única fuente de verdad. Nunca cmake/make directamente.
2. **macOS:** nunca `sed -i` sin `-e ''`. Usar Python3 inline.
3. **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all` antes de cualquier merge.
4. **GitHub:** push directo a main BLOQUEADO. Feature branch → PR → merge.
5. **`#ifdef ARGUS_VAULT_ENABLED`:** solo en `crypto_provider.cpp`. Sin excepciones.
6. **Migración por canal:** sniffer+ml-detector simultáneamente.
7. **TTL ≠ fecha de muerte.**
8. **Qwen se identifica como DeepSeek** en el Consejo — siempre registrar como Qwen.
9. **Calidad sobre fechas** — no hay deadline duro para FEDER.

---

## Keypair activo

Post-destroy DAY 133: `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`

## Consejo de Sabios

Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral (8 modelos)