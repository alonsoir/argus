# HMAC Infrastructure Roadmap

## Vision
Military-grade log integrity protection with zero-downtime key rotation.

## Completed Phases

### ✅ FASE 1 - etcd-server SecretsManager (Day 53)
- HMAC-SHA256 key generation
- Thread-safe storage
- HTTP endpoints
- 12 unit + 4 integration tests

### ✅ FASE 2 - etcd-client HMAC Utilities (Day 53)
- get_hmac_key(), compute_hmac_sha256(), validate_hmac_sha256()
- Constant-time validation
- 12 unit + 4 integration tests

## In Progress

### 🔄 FASE 3 - rag-ingester Validation (Day 54-55)
Basic HMAC validation before decryption.
[See BACKLOG for details]

## Planned

### 📋 FASE 4 - Grace Period + Versioning (Day 56-57)
Zero-downtime key rotation with grace period.
[See BACKLOG for details]

### 💡 FASE 5 - Auto-Rotation (Future)
Automated scheduled rotation.
[Low priority, blocked by FASE 4]

## Design Decisions

### Why Grace Period?
Real scenario: sniffer signs log → admin rotates key → rag-ingester
receives log 30s later → rejection (legitimate log).
Solution: 24h grace period keeps previous keys valid.

### Why Versioning?
Without version: client must try N keys (inefficient).
With version: single lookup, reject if expired.

### Why Configurable?
Different environments need different grace periods:
- Dev: 60 seconds (fast iteration)
- Prod: 24 hours (network latency)

## Metrics Strategy

| Phase | Metrics | Purpose |
|-------|---------|---------|
| FASE 1+2 | keys_generated, rotation_count | Infrastructure health |
| FASE 3 | validation_success/failed | Detection rate |
| FASE 4 | current_version, previous_count | Grace period effectiveness |

## References
- Original discussion: Grok analysis (9 Feb 2026)
- Security model: HMAC-SHA256 (FIPS 198-1)
- Key rotation: NIST SP 800-57 Part 1