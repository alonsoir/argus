# Consejo de Sabios — DAY 106 Report
## ML Defender (aRGus NDR) — feature/plugin-crypto
### 3 April 2026

---

## Context

DAY 106 had two parallel workstreams: closing the 4 mandatory conditions from the Consejo
DAY 105 review (PHASE 2a gate), and preparing + submitting the arXiv preprint (Draft v11).

Both workstreams completed successfully.

---

## Work Completed

### PHASE 2a — All 4 Consejo conditions closed

**1c — nonce/tag NULL contract in `plugin_api.h`**
Added explicit production guarantee documentation before the `nonce` and `tag` fields
in `MessageContext`:
- Production: `nonce != NULL && tag != NULL`
- Test/config mode (`--test-config`, `MLD_DEV_MODE`): MAY be NULL
- Plugins MUST check for NULL before dereferencing

**1d — Makefile dependency propagation**
Added `plugin-loader-build` as explicit dependency to 4 remaining build targets:
`sniffer`, `ml-detector`, `rag-ingester`, `rag-build`.
`firewall-acl-agent` already had this dependency from DAY 105. All 5 components now
correctly declare their plugin-loader dependency.

**1a — CRC32 payload integrity (D8-v2)**
Implemented `crc32_fast()` as a static function in `plugin_loader.cpp` (debug builds only,
guarded by `#ifdef MLD_ALLOW_DEV_MODE`). The function uses the standard CRC-32/ISO-HDLC
polynomial (0xEDB88320). Snapshot taken before plugin invocation; comparison after.
Mismatch produces a `SECURITY D8-v2` log entry and increments `stats_.errors`.
This closes the gap in the existing D8 check, which only validated pointer identity,
not payload content integrity.

**1b — TEST-INTEG-4a-PLUGIN**
Created `plugins/test-message/` with:
- `plugin_test_message.cpp`: 3 variants selectable via `MLD_TEST_VARIANT`
- `CMakeLists.txt`: builds `libplugin_test_message.so`
- `test_variants.cpp`: standalone test runner
- `test_config.json`: isolated test config (does not touch production firewall.json)

Test results:
```
=== TEST VARIANT A === → PASS (errors=0, result_code=0)
=== TEST VARIANT B === → PASS (D8 VIOLATION detected, errors=1)
=== TEST VARIANT C === → PASS (PLUGIN_ERROR registered, errors=1, no crash)
=== TEST-INTEG-4a-PLUGIN: PASSED (0 failures) ===
```

### arXiv submission

Draft v11 prepared and submitted:
- Removed UEx affiliation (pending legal resolution)
- Added 3 TikZ architecture figures:
    - Fig 1: End-to-end pipeline overview
    - Fig 2: HA hospital deployment (dual-NIC, primary/standby, per-segment firewall-acl-agent topology)
    - Fig 3: Federated distributed intelligence (future work, explicitly marked as not yet implemented)
- Fixed development environment spec: Intel Core i9 2.5 GHz, 32 GB DDR4 (was incorrectly M2 Pro 16 GB)
- Added TDH GitHub repo link: https://github.com/alonsoir/test-driven-hardening
- Submission ID: 7438768 — STATUS: submitted

---

## Questions for the Consejo

**Q1 — PHASE 2b sequencing**
The standard pattern for integrating `plugin_process_message()` into a component is now
established (firewall-acl-agent DAY 105). Should PHASE 2b (rag-ingester) follow the
identical three-file pattern, or are there rag-ingester-specific considerations
(e.g., the FAISS ingestion path) that warrant a different approach?

**Q2 — CRC32 scope**
The current D8-v2 CRC32 check is restricted to `MLD_ALLOW_DEV_MODE` (debug builds).
Should a lightweight integrity check (e.g., pointer + length validation only, no CRC)
be retained in Release builds as well, given that plugins are treated as untrusted code?

**Q3 — test_config.json ownership**
The test plugin uses a dedicated `test_config.json` isolated from production configs.
Should this pattern be formalized as a testing convention for all future plugin tests,
or should we build a test fixture factory instead?

---

## Status

- Tests: 25/25 ✅ + TEST-INTEG-4a-PLUGIN 3/3 ✅
- PHASE 2a: COMPLETE
- PHASE 2b (rag-ingester): UNBLOCKED
- arXiv: submitted, pending moderation