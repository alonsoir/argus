# ADR-023 — Multi-Layer Plugin Architecture

**Status:** ACCEPTED
**Date:** 2026-04-01 (DAY 104)
**Branch:** feature/plugin-crypto
**Consejo de Sabios Ronda 1:** DAY 103 — Claude, Grok, ChatGPT, DeepSeek, Gemini
**Consejo de Sabios Ronda 2:** DAY 104 — ChatGPT, DeepSeek, Gemini, Grok, Qwen — unanimidad
**Deciders:** Alonso Isidoro Roman (final arbiter)

---

## Context

ML Defender's `CryptoTransport` layer provides authenticated encryption
(ChaCha20-Poly1305 + HKDF-SHA256) across all six pipeline components. As
the plugin loader (ADR-012) is integrated into each component, plugins require
access to the same cryptographic context in order to process messages.

Three options were evaluated by the Consejo de Sabios:

1. **Plugins receive raw (decrypted) payloads only** — CryptoTransport invisible to plugins.
2. **Plugins receive a `MessageContext` struct** — structured envelope with decrypted payload
   plus metadata; plugins do not control key derivation.
3. **Plugins perform their own HKDF derivation** — plugins receive the seed directly.

Option 3 unanimously rejected: replicates the HKDF Context Asymmetry bug (ADR-022) at
the plugin boundary and undermines the single source of truth in `contexts.hpp`.

Option 2 approved unanimously.

---

## Decision

Plugins interact with the cryptographic layer exclusively through a **`MessageContext`
struct**. The host component owns key derivation and encryption/decryption. Plugins
never touch HKDF or libsodium directly.

### MessageContext definition

```c
typedef struct {
    uint8_t     version;       // MESSAGE_CONTEXT_VERSION = 1
    uint8_t     direction;     // MLD_TX = 0, MLD_RX = 1  [READ-ONLY for plugins]
    uint8_t     nonce[12];     // 96-bit monotonic counter  [READ-ONLY for plugins]
    uint8_t     tag[16];       // Poly1305 tag (16 bytes)   [READ-ONLY for plugins]
    uint8_t*    payload;       // buffer (in/out) — host-owned; pointer must not be reassigned
    size_t      length;        // current payload length (plugin updates after processing)
    size_t      max_length;    // capacity — INVARIANT: always >= length + 16
    const char* channel_id;    // "sniffer-to-ml-detector" — valid only during invocation
    int32_t     result_code;   // 0=OK, -1=MAC failure, -2=buffer overflow (plugin writes)
    uint8_t     reserved[8];   // reserved for uint64_t sequence_number in PLUGIN_API_VERSION=2
} MessageContext;
```

**Field contracts:**

- `direction` — mirrors `tx`/`rx` from `contexts.hpp` (ADR-022 fix). **Read-only for plugins.**
  Host validates post-invocation; violation → `std::terminate()`.
- `nonce[12]` — 96-bit monotonic counter (ADR-015). Host owns increment. **Read-only for plugins.**
- `tag[16]` — Poly1305 tag. Present for inspection only. **Read-only for plugins.**
- `payload` — decrypted buffer. **Host-owned at all times.** Plugin may write up to
  `max_length` bytes but must not reassign the pointer.
- `max_length` — **Security invariant:** `max_length >= length + 16` always, to accommodate
  Poly1305 tag on re-encryption. Violation is undefined behavior.
- `channel_id` — HKDF `info` selector. **Valid only during the plugin invocation call.**
  Plugin must not retain this pointer across the call boundary.
- `result_code` — plugin output. Any non-zero value → host calls `std::terminate()`.
- `reserved[8]` — reserved for `uint64_t sequence_number` in `PLUGIN_API_VERSION = 2` (PHASE 3).
  Not to be read or written in v1 implementations.

---

## Plugin Trust Model (D7)

Plugins are considered **trusted-but-potentially-buggy**, not tamper-proof.

The C ABI boundary does not enforce memory safety against a malicious plugin actor.
Security invariants (see below) are validated by the host post-invocation but are not
cryptographically enforced against an actively malicious plugin.

**Malicious plugin resistance is explicitly out of scope for ADR-023.**
Defense against malicious plugins requires OS-level isolation (AppArmor, seccomp)
outside the scope of the plugin architecture.

**TCB declaration (D9):**
Plugins operate on plaintext prior to encryption (TX path) or after decryption (RX path).
Plugins are therefore part of the **Trusted Computing Base (TCB)** of the secure channel.
A compromised plugin can read or modify all plaintext data processed by the host component.
This is an inherent consequence of the plugin architecture, documented here for transparency.

---

## Security Invariants and Post-Invocation Validation (D3 + D8)

The host snapshots read-only fields before invoking `plugin_process_message()` and
validates byte-for-byte after the plugin returns.

```c
// Pre-invocation snapshot (host)
uint8_t     snap_direction = ctx->direction;
uint8_t     snap_nonce[12]; memcpy(snap_nonce, ctx->nonce, 12);
const char* snap_channel   = ctx->channel_id;
uint8_t*    snap_payload   = ctx->payload;

// === plugin invocation ===
int rc = plugin_process_message(ctx);

// Post-invocation validation (host)
if (ctx->direction  != snap_direction)           std::terminate();
if (memcmp(ctx->nonce, snap_nonce, 12) != 0)     std::terminate();
if (ctx->channel_id != snap_channel)             std::terminate(); // pointer equality
if (ctx->payload    != snap_payload)             std::terminate(); // pointer equality
if (ctx->length     > ctx->max_length)           std::terminate();
if (rc != 0 || ctx->result_code != 0)            std::terminate();
```

Any invariant violation → `std::terminate()` (fail-closed), regardless of
`result_code` value and regardless of build type.

---

## Graceful Degradation Policy (D1 + D10)

### Case A — Symbol absent (`plugin_process_message` not found via `dlsym`)

| Build type | Behaviour |
|------------|-----------|
| **Production** (Release / Production) | `std::terminate()` — fail-closed |
| **Development** (Debug + `MLD_ALLOW_DEV_MODE` compile flag) | Plugin loads; mandatory log: `[SECURITY WARNING] Plugin <name> loaded WITHOUT plugin_process_message — plaintext may be exposed` |

`MLD_DEV_MODE=1` is **only honoured** when:
- `CMAKE_BUILD_TYPE=Debug`, AND
- compile-time flag `MLD_ALLOW_DEV_MODE` is explicitly set at build time.

In Release/Production builds, `MLD_DEV_MODE` is silently ignored. The component
always behaves fail-closed. This prevents an attacker with environment access from
forcing degraded mode in production deployments.

### Case B — Symbol present but returns non-zero `result_code`

**Always `std::terminate()`**, in all environments, with no fallback.

Rationale: a plugin that has executed may have partially modified the payload buffer.
No safe fallback state exists; the only secure response is fail-closed.

---

## Plugin API

```c
// Plugin API — PLUGIN_API_VERSION = 1
// Resolved via dlsym — see Graceful Degradation Policy
int plugin_process_message(MessageContext* ctx);
```

**Signature contract:**
- Input: `ctx->payload` contains the decrypted message; `ctx->length` is valid.
- Output: plugin writes result into `ctx->payload` (in-place, respecting `max_length`),
  sets `ctx->length` to new length, sets `ctx->result_code`.
- Return value: `0` on success, non-zero on failure (must mirror `result_code`).

---

## Integration Strategy: PHASE 2a / 2b / 2c

Approved order (Consejo de Sabios, DAY 103 + DAY 104, unanimidad):

```
firewall-acl-agent → rag-ingester → rag-security
```

**Rationale:** `firewall-acl-agent` has the simplest message structure and no ML
inference path — lowest risk for validating the `MessageContext` interface.

### PHASE 2a — firewall-acl-agent

**Gate:** `TEST-INTEG-4a` must pass before PHASE 2b begins.

Steps:
1. Add `MessageContext` to `plugin_api.h` (`PLUGIN_API_VERSION = 1`).
2. Implement `plugin_process_message()` resolution in `PluginLoader` (`dlsym`).
3. Apply Graceful Degradation Policy (D1 + D10).
4. Integrate into `firewall-acl-agent/src/main.cpp` under `#ifdef PLUGIN_LOADER_ENABLED`.
5. **Core `CryptoTransport` is read-only during PHASE 2a** (DeepSeek consensus).
6. Add `plugins` section to `firewall-acl-agent/config/firewall-acl-agent.json`.

`TEST-INTEG-4a` pass criteria:
- `plugin_process_message()` invoked on at least one real `MessageContext`.
- Post-invocation security invariants verified (D8).
- `result_code == 0` confirmed.
- `CryptoTransport` decryption path unmodified (diff check).

### PHASE 2b — rag-ingester

**Gate:** `TEST-INTEG-4b` must pass before PHASE 2c begins.

Same pattern as PHASE 2a. Plugin hook placed after deserialization, before FAISS insert.

`TEST-INTEG-4b` pass criteria:
- `plugin_process_message()` invoked on at least one ingested event.
- Post-invocation security invariants verified.
- FAISS index size increases correctly after plugin-processed event.
- `result_code == 0` confirmed.

### PHASE 2c — rag-security

**Gate:** `TEST-INTEG-4c` must pass to close PHASE 2.
**Pre-requisite:** `TEST-FUZZ-1` (MessageContext fuzzing, Backlog R3) must complete
before PHASE 2c begins.

Plugin hooks placed on the query path only; TinyLlama inference loop is not modified.

`TEST-INTEG-4c` pass criteria:
- `plugin_process_message()` invoked on at least one query context.
- Post-invocation security invariants verified.
- TinyLlama inference latency unaffected (measured via `high_resolution_clock`).
- `result_code == 0` confirmed.

---

## Forward Compatibility with ADR-024 (D11)

ADR-023 is **forward-compatible** with ADR-024 (Dynamic Group Key Agreement) but
does not require it. The `channel_id`, `direction`, and `nonce` fields are designed
to support session-derived keys without API changes. ADR-023 is fully functional
with the current static HKDF-derived keys.

When ADR-024 is implemented (post-arXiv), `CryptoTransport` will receive session keys
via `install_session_keys(tx_key, rx_key)` after the Noise handshake. From the plugin's
perspective, `MessageContext` is unchanged.

---

## Minority Positions (registered per Consejo methodology)

**Gemini — PLUGIN_API_VERSION=2 immediate bump:**
Proposed `sequence_number` and `timestamp` as explicit fields from day one. Not adopted.
`reserved[8]` provides a clean migration path.
*Condition for reopening:* if out-of-order delivery in ZeroMQ becomes observable during
PHASE 2a testing, proposal will be reconsidered before PHASE 2c.

**Grok — fail-closed even without symbol in DEV_MODE:**
Plugin loader should always require `plugin_process_message`. Partially adopted:
D10 constrains DEV_MODE to Debug builds + compile flag, closing the production vector.

**ChatGPT — eliminate DEV_MODE escape hatch entirely:**
Force fail-closed in all environments. Not adopted. DEV_MODE serves a legitimate need
for resource-constrained operators (hospitals, schools) debugging plugins without
specialised hardware.

---

## Backlog (non-blocking)

| ID | Item |
|----|------|
| R1 | `reserved[8]` → explicit `uint64_t sequence_number` in `PLUGIN_API_VERSION=2` (PHASE 3) |
| R2 | External watchdog / automatic reboot documented as production deployment requirement |
| R3 | `TEST-FUZZ-1`: MessageContext fuzzing campaign — required before PHASE 2c |

---

## Connection to ADR-022 (HKDF Context Symmetry)

The `direction` and `channel_id` fields directly encode the lessons of the HKDF
Context Asymmetry bug: context identity is explicit in the struct, not implicit
in the call site. This design avoids semantic overloading of data structures across
layers — a common source of subtle security and correctness bugs (ADR-022, §5.5).

---

## Consequences

**Positive:**
- Plugins isolated from key derivation — cannot introduce HKDF context bugs.
- Versioned interface enables safe future evolution.
- Post-invocation invariant validation catches buggy plugins before pipeline corruption.
- Phased integration with explicit gates limits blast radius of defects.
- Trust model explicitly documented — no hidden assumptions about plugin safety.

**Negative / risks:**
- Plugins form part of the TCB; a compromised plugin reads all plaintext (documented, D9).
- C ABI boundary does not enforce invariants against a malicious plugin; OS-level
  isolation required for that guarantee (documented, D7).
- `max_length` discipline required from all plugin authors.

---

## Related ADRs

| ADR | Relation |
|-----|----------|
| ADR-012 | Plugin Loader — PHASE 1b established the `dlopen`/`dlsym` pattern |
| ADR-015 | 96-bit monotonic nonce — `nonce[12]` in `MessageContext` |
| ADR-021 | deployment.yml as SSOT — `channel_id` values derived from topology |
| ADR-022 | HKDF Context Symmetry — `direction` and `channel_id` encode this lesson |
| ADR-024 | Dynamic Group Key Agreement — forward-compatible; `reserved[8]` for Noise IK |

---

*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*
*Consejo Ronda 1: Claude, Grok, ChatGPT, DeepSeek, Gemini — DAY 103*
*Consejo Ronda 2: ChatGPT, DeepSeek, Gemini, Grok, Qwen — DAY 104 — unanimidad*