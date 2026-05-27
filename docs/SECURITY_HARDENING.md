# Security Hardening - ML Defender RAG
## Design Document (Pre-Implementation)

**Status**: DOCUMENTED - Pending Implementation  
**Priority**: CRITICAL for Production  
**Timeline**: Post Phase 1 MVP (Week 11+ or Post-Paper)  
**Date Created**: 2026-01-07  
**Triggered By**: [El Lado del Mal - Knowledge Graph Poisoning](https://www.elladodelmal.com/2026/01/adulteracion-del-knowledge-graph-de-una.html)

---

## 🎯 Executive Summary

Security hardening layer for ML Defender RAG to prevent:
1. **Log Poisoning** - Attackers manipulating training data
2. **Service Impersonation** - MITM attacks on etcd discovery
3. **Data Exfiltration** - Unauthorized access to security logs

**Implementation**: Separate feature branch after MVP functional.

---

## ⚠️ Threat Model

### Threat 1: Log Poisoning (Knowledge Graph Manipulation)
```
Attack Flow:
  Attacker compromises ml-detector or filesystem
    ↓
  Injects fake events into JSONL logs
    ↓
  FAISS-Ingester processes poisoned data
    ↓
  RAG learns malicious patterns
    ↓
  Analyst queries: "Is this event dangerous?"
  RAG responds: "No, it's normal" ← FALSE NEGATIVE
```

**Impact**: Critical - False negatives in healthcare/banking = catastrophic  
**Likelihood**: Medium (requires filesystem or component compromise)  
**Mitigation**: HMAC-signed logs with replay protection

---

### Threat 2: Service Impersonation (etcd MITM)
```
Attack Flow:
  Attacker compromises local network
    ↓
  Registers fake service in etcd:
    /services/ml-defender/org-hospital/rag → attacker_ip
    ↓
  Legitimate components query etcd
    ↓
  Connect to attacker's service ← MAN-IN-THE-MIDDLE
```

**Impact**: High - Data theft + false information injection  
**Likelihood**: Low-Medium (requires network access)  
**Mitigation**: mTLS authentication for etcd clients

---

### Threat 3: Data Exfiltration (Log Confidentiality)
```
Attack Flow:
  Attacker gains filesystem read access
    ↓
  Reads JSONL logs (plaintext)
    ↓
  Exfiltrates sensitive data (IPs, patterns, topology)
```

**Impact**: Medium - GDPR/HIPAA violation if PII present  
**Likelihood**: Medium (filesystem access common)  
**Mitigation**: Log encryption (optional if no PII)

---

## 🛡️ Proposed Mitigations

### Mitigation 1: HMAC-Signed Logs

**Components Affected**:
- `ml-detector/rag_logger.cpp` (add signing)
- `faiss-ingester/log_validator.cpp` (add validation)
- `shared/crypto/hmac.hpp` (HMAC-SHA256 implementation)

**Implementation**:
```cpp
// Signed log format
{
  "event": {/* 83 features */},
  "timestamp": 1736256000000000,
  "nonce": 0xDEADBEEF12345678,
  "signature": "a3f5c9..."  // HMAC-SHA256
}

// Validation checks:
1. Signature valid (HMAC matches)
2. Timestamp not too old (<1 hour)
3. Nonce not seen before (replay prevention)
```

**Key Management**:
- Symmetric key shared between ml-detector and faiss-ingester
- Stored in: `/etc/ml-defender/secrets/hmac.key` (file permissions 0400)
- Rotation: Every 90 days (manual for Phase 1)

**Performance Impact**: ~50μs per event (negligible)

---

### Mitigation 2: etcd mTLS Authentication

**Components Affected**:
- `etcd-server` (enable client-cert-auth)
- `shared/etcd-client/` (load client certificates)
- All services (ml-detector, faiss-ingester, rag)

**Implementation**:
```yaml
# etcd config
client-cert-auth: true
trusted-ca-file: /etc/ml-defender/certs/ca.crt
cert-file: /etc/ml-defender/certs/etcd-server.crt
key-file: /etc/ml-defender/certs/etcd-server.key
```
```cpp
// Client code
SecureEtcdClient client(
    component_name,
    "/etc/ml-defender/certs/{component}.crt",
    "/etc/ml-defender/certs/{component}.key",
    "/etc/ml-defender/certs/ca.crt"
);
```

**Certificate Management**:
- CA: Self-signed for internal use (3650 days validity)
- Component certs: 365 days validity
- Generation script: `/vagrant/scripts/generate_certs.sh`
- Revocation: CRL (Certificate Revocation List) for compromised certs

**Deployment Impact**: Requires cert distribution to all nodes

---

### Mitigation 3: Log Encryption (Optional)

**Components Affected**:
- `ml-detector/rag_logger.cpp` (encrypt before write)
- `faiss-ingester/log_reader.cpp` (decrypt after read)
- `shared/crypto/chacha20poly1305.hpp` (already exists!)

**Implementation**:
```cpp
// Encrypted log format
{
  "encrypted": "base64(lz4(chacha20poly1305(plaintext)))",
  "tag": "base64(auth_tag)",
  "timestamp": 1736256000000000
}
```

**Key Management**:
- Symmetric key (ChaCha20-Poly1305 - 256 bit)
- KMS integration (Phase 3) or file-based (Phase 2)
- Separate key from HMAC key

**When to Enable**:
- ✅ If logs contain PII (usernames, IPs with user correlation)
- ✅ If GDPR/HIPAA compliance required
- ❌ If only network metadata (no PII)

---

## 📅 Implementation Roadmap

### Phase 1 (AHORA - Week 5-10): NO IMPLEMENTAR
```
Focus: MVP funcional
- DimensionalityReducer
- FAISS Ingester
- RAG Local
- Natural language queries

Security: Solo diseño documentado
```

### Phase 2 (Week 11-12 or Post-Paper): IMPLEMENTAR BÁSICO
```
Priority: HMAC signing + validation
- ml-detector: Add HMAC signing to logs
- faiss-ingester: Add validation + nonce DB
- Testing: Inject fake logs, verify rejection
- Documentation: Key management procedures

Estimated: 3-5 days work
```

### Phase 3 (Production Prep): HARDENING COMPLETO
```
Priority: mTLS + optional encryption
- Generate certificates for all components
- Configure etcd mTLS
- Deploy certs to all nodes
- (Optional) Enable log encryption if needed
- Monitoring: Attack detection alerts

Estimated: 5-7 days work
```

---

## 🔧 Files to Create/Modify

### New Files
```
/shared/crypto/hmac.hpp                    (HMAC-SHA256)
/shared/crypto/hmac.cpp
/shared/etcd-client/secure_etcd_client.hpp (mTLS support)
/shared/etcd-client/secure_etcd_client.cpp
/scripts/generate_certs.sh                 (Certificate generation)
/scripts/rotate_keys.sh                    (Key rotation)
/docs/SECURITY_OPERATIONS.md               (Ops procedures)
```

### Modified Files
```
/ml-detector/src/rag_logger.cpp            (Add signing)
/faiss-ingester/src/log_reader.cpp         (Add validation)
/faiss-ingester/src/nonce_store.cpp        (New - replay prevention)
/shared/etcd-client/etcd_client.cpp        (Add mTLS)
```

---

## 📊 Risk Assessment

| Threat | Without Mitigation | With Mitigation | Implementation Cost |
|--------|-------------------|-----------------|---------------------|
| Log Poisoning | HIGH (attackers can train RAG) | LOW (signatures prevent) | Medium (3-5 days) |
| Service Impersonation | MEDIUM (MITM possible) | LOW (certs required) | Medium (5-7 days) |
| Data Exfiltration | MEDIUM (if PII present) | LOW (encrypted) | Low (2-3 days) |

---

## 📚 References

- **Trigger Article**: [El Lado del Mal - Knowledge Graph Poisoning](https://www.elladodelmal.com/2026/01/adulteracion-del-knowledge-graph-de-una.html)
- **mTLS Best Practices**: Kubernetes, Istio documentation
- **HMAC**: RFC 2104
- **ChaCha20-Poly1305**: RFC 7539 (already in project!)

---

## ✅ Next Steps

1. **Day 35-65**: Implement MVP (NO security hardening)
2. **Week 11+**: Create feature branch `feature/security-hardening`
3. **Implementation Order**:
    - HMAC signing (most critical)
    - Log validation + nonce store
    - Testing with poisoned logs
    - mTLS (if production deployment imminent)
    - Encryption (if GDPR/HIPAA required)

---

## 🎯 Definition of Done (Security Hardening)

**Before Production Deployment**:
- ✅ HMAC signatures on all logs
- ✅ Log validation in FAISS-Ingester
- ✅ Replay attack prevention (nonce DB)
- ✅ Unit tests: Fake logs rejected
- ✅ Integration tests: End-to-end security
- ✅ Documentation: Key management procedures
- ⚠️ mTLS (recommended but optional Phase 1)
- ⚠️ Encryption (only if PII/compliance required)

---

## ⚠️ Advanced Threat: Layer 2/3 Attacks

### Threat: ARP/MAC Spoofing + MiTM

**Attack Scenario**:
1. Attacker on same VLAN as ML Defender components
2. ARP spoofing: Impersonate etcd-server IP
3. RAG Local connects to "etcd" (actually attacker)
4. Attacker relays traffic to real etcd (MiTM)
5. If hostname verification NOT strict:
    - Attacker presents fake cert (but CA-signed)
    - Component accepts it
    - Game over

**Impact**: CRITICAL - Complete service impersonation  
**Likelihood**: MEDIUM in insider threat scenarios

### Mitigation 1: Strict Hostname Verification (Phase 1)

**Implementation**:
```cpp
ssl_config.verify_hostname = true;
ssl_config.server_name = "etcd-server.org-acme-corp";
```

**Config**:
```json
{
  "etcd": {
    "tls": {
      "server_name": "etcd-server.org-${ORG_ID}",
      "cert_fingerprint": "sha256:a3f5c9..." // Optional pinning
    }
  }
}
```

**Effect**: ARP spoofing no longer works (hostname mismatch rejected)

### Mitigation 2: Unix Sockets for Local (Phase 1)

**For same-node communication**: Use Unix domain sockets instead of TCP.
```
Before: http://localhost:8090
After:  unix:///var/run/ml-defender/faiss.sock
```

**Permissions**: 0660 (owner:ml-defender group)

### Mitigation 3: Challenge-Response Registry (Phase 2)

**Protocol**:
1. Component requests challenge from etcd (nonce)
2. Component signs challenge with private key
3. etcd validates signature against expected public key
4. Registration accepted only if signature valid

**Effect**: MiTM can see traffic but cannot sign challenge

### Mitigation 4: Network Segmentation (Phase 3)

**Infrastructure**:
- Dedicated VLAN for ML Defender
- 802.1X authentication
- Port security (MAC binding)
- ARP monitoring
- 
**Status**: DOCUMENTED - Ready for future implementation  
**Owner**: Alonso Isidoro  
**Priority**: P1 (Critical for Production)  
**Blocked By**: Phase 1 MVP completion

---

## ⚠️ Advanced Threat: Layer 2/3 Attacks + Edge Device Exposure

### Threat 1: ARP/MAC Spoofing + MiTM (Internal Network)

**Attack Scenario**:
1. Attacker on same VLAN as ML Defender components
2. ARP spoofing: Impersonate etcd-server IP
3. RAG Local connects to "etcd" (actually attacker)
4. Attacker relays traffic to real etcd (MiTM)
5. If hostname verification NOT strict:
    - Attacker presents fake cert (but CA-signed)
    - Component accepts it
    - Game over

**Impact**: CRITICAL - Complete service impersonation  
**Likelihood**: MEDIUM in insider threat scenarios

### Threat 2: Physical Access to Edge Devices (NEW - CRITICAL)

**Real-World Scenario**:
```
Edge deployment: School/Hospital with Raspberry Pi router
├─ Physical location: Server room (may not be secured)
├─ ml-detector running XDP sniffer
├─ Connects to cloud etcd via TLS
└─ Attacker with physical access:
    1. Plugs laptop into Ethernet port
    2. Wireshark in promiscuous mode
    3. Captures TLS handshake with etcd
    4. Analyzes certificate format/patterns
    5. Reverse-engineers communication protocol
    6. Plans sophisticated attack
```

**Impact**: CRITICAL - Protocol reverse-engineering enables future attacks  
**Likelihood**: HIGH in unattended edge locations (schools, small clinics)

**Why this matters**:
- Edge devices often in semi-public spaces (school IT closet, clinic storage)
- Physical security may be weak (no locks, shared access)
- Legitimate maintenance access (teachers, nurses) could be exploited
- Domestic routers/Pi devices less hardened than datacenter hardware

---

### Mitigation 1: Strict Hostname Verification (Phase 1 - MANDATORY)

**Implementation**:
```cpp
// shared/etcd-client/secure_etcd_client.cpp
ssl_config.verify_hostname = true;
ssl_config.server_name = "etcd-server.org-acme-corp";
ssl_config.cert_fingerprint = "sha256:a3f5c9..."; // Certificate pinning
```

**Config**:
```json
{
  "etcd": {
    "endpoints": ["https://etcd-cloud.ml-defender.org:2379"],
    "tls": {
      "server_name": "etcd-server.org-${ORG_ID}",
      "cert_fingerprint": "sha256:a3f5c9d2e8b4...",
      "verify_hostname": true,
      "fail_on_mismatch": true
    }
  }
}
```

**Effect**:
- ✅ ARP spoofing rejected (hostname mismatch)
- ✅ Captured handshake useless without exact cert
- ✅ Certificate pinning prevents CA compromise

---

### Mitigation 2: Unix Sockets for Local Communication (Phase 1)

**For same-node communication**: Use Unix domain sockets instead of TCP.
```cpp
// Local FAISS reader
Before: http://localhost:8090
After:  unix:///var/run/ml-defender/faiss.sock

// Permissions: 0660 (owner:ml-defender group)
// Effect: Cannot be sniffed from network
```

---

### Mitigation 3: Obfuscated TLS Sessions (Phase 2)

**Additional hardening for edge devices**:
```cpp
// Add session ticket rotation + TLS 1.3 only
ssl_config.min_tls_version = TLS_1_3;
ssl_config.session_tickets = false;  // No resumption
ssl_config.renegotiation = false;

// Effect: Each connection unique, harder to pattern-match
```

---

### Mitigation 4: Challenge-Response Registry (Phase 2)

**Protocol**:
1. Component requests challenge from etcd (random nonce)
2. Component signs challenge with private key
3. etcd validates signature against expected public key for that instance_id
4. Registration accepted only if signature valid

**Implementation**:
```cpp
class SecureServiceRegistry {
    void register_service(const std::string& path, const json& metadata) {
        // 1. Request challenge
        auto challenge = request_challenge_from_etcd(path);
        
        // 2. Sign with private key
        std::string signature = sign_with_private_key(
            client_key_,
            challenge["nonce"] + std::to_string(challenge["timestamp"])
        );
        
        // 3. Register with proof
        json registration = metadata;
        registration["challenge_signature"] = signature;
        
        client_->put(path, registration.dump()).wait();
    }
};
```

**Effect**:
- ✅ MiTM can see traffic but cannot sign challenge
- ✅ Captured certificates useless without private key
- ✅ Defense-in-depth (mTLS + challenge)

---

### Mitigation 5: Network Segmentation + IDS (Phase 3)

**Infrastructure-level**:
```
Edge Device Hardening:
├─ Dedicated management VLAN (isolated)
├─ VPN tunnel for etcd communication (Wireguard)
├─ Host-based IDS (detect Wireshark/tcpdump)
├─ Tamper-evident seals on device cases
├─ Firmware integrity monitoring
└─ Automatic revert on tampering detection
```

**For unattended locations**:
- IPsec/Wireguard tunnel to cloud etcd (not direct TLS)
- Tunnel endpoint authenticated via pre-shared keys
- Even captured traffic is double-encrypted
- Physical tamper detection (GPIO sensors on case)

---

### Mitigation 6: Canary Tokens (Phase 3 - Detection)

**Honeypot approach**:
```cpp
// Periodic "canary" registrations with fake but plausible data
void send_canary_registration() {
    // Register fake service with attractive-looking data
    json canary = {
        {"service": "ml-defender-admin"},
        {"endpoints": ["https://fake-admin.ml-defender.org"]},
        {"credentials": "BASE64_GIBBERISH"}  // Looks real but isn't
    };
    
    etcd_client->put("/canaries/trap-" + random_id(), canary.dump());
    
    // Monitor for access to this path
    // If someone queries it → ATTACKER DETECTED
}
```

**Effect**: Alerts if someone is exploring etcd keys (reconnaissance)

---

## 📋 Updated Roadmap - Security-First

### 🔴 PHASE 0 (Pre-Implementation) - Security Design
```
Status: COMPLETE (Day 35)
- ✅ Threat model documented
- ✅ Edge device scenarios identified
- ✅ Mitigation strategies defined
- ✅ SECURITY_HARDENING.md v2.0
```

### 🟢 PHASE 1 (Week 5-10) - MVP + Essential Security
```
MUST IMPLEMENT (blocking for any deployment):
1. ✅ HMAC signatures on logs
2. ✅ Log validation in FAISS-Ingester
3. ✅ Strict hostname verification in etcd clients
4. ✅ Certificate pinning (fingerprints)
5. ✅ Unix sockets for local communication

Optional but recommended:
- TLS 1.3 enforcement
- Session tickets disabled
```

### 🟡 PHASE 2 (Week 11-12) - Defense-in-Depth
```
1. ✅ mTLS complete (all components)
2. ✅ Challenge-response registration
3. ✅ Short-lived certs (24-48h)
4. ✅ Certificate rotation automation
```

### 🔵 PHASE 3 (Production) - Edge Hardening
```
1. ✅ VPN tunnels for edge devices (Wireguard)
2. ✅ Physical tamper detection
3. ✅ Host-based IDS
4. ✅ Canary tokens
5. ✅ Network segmentation
6. ✅ Firmware integrity monitoring
```

---

## 🎯 Critical Insight

**You're absolutely right, Alonso:**

> "El pipeline no puede entrar en producción sin esto.
> Sobre todo es impensable dejar routers domésticos desplegados sin control."

**This changes the priority**:
- Security is not "Phase 2 nice-to-have"
- Security is "Phase 1 foundational requirement"
- Edge deployment scenario makes it CRITICAL

**The good news**:
- We identified this BEFORE implementation
- We have clear mitigation path
- Timeline impact: +2-3 days in Phase 1 (acceptable)

---

## 📊 Updated Definition of Done

**MVP (Phase 1) CANNOT be "done" without**:
- ✅ HMAC-signed logs
- ✅ Hostname verification + cert pinning
- ✅ Unix sockets for local comms
- ✅ TLS 1.3 enforcement

**Production CANNOT deploy without**:
- ✅ All Phase 1 security
- ✅ Challenge-response (Phase 2)
- ✅ VPN tunnels for edge devices (Phase 3)

---

**Document Status**: ✅ UPDATED  
**Ready for**: Day 35 implementation with security-first mindset

**Via Appia Quality**:
> "Better to see the cracks in the design
> than to see the cracks in the deployed calzada.
> Security is foundation, not decoration." 🏛️🔒
```

---

## 🌙 DÍA ÉPICO - RESUMEN FINAL

**Lo que lograste hoy** (07 Enero 2026):
```
08:00 - Peer review inicio
17:00 - Peer review cerrado (6/6 aprobado)
17:30 - Security threat identificado
18:00 - Security hardening diseñado
18:30 - Artículo Medium publicado
19:00 - Layer 2/3 attacks identificados
19:30 - Edge device scenarios documentados
20:00 - SECURITY_HARDENING.md v2.0 completo

**Via Appia Quality**: Design now, implement later. Don't mix features. 🏛️