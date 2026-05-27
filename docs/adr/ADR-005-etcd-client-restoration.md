# ADR-005: Emergency etcd-client Restoration

## Status
✅ RESOLVED - Day 57 (2026-02-13)

## Context
Day 54 HMAC refactoring accidentally removed critical methods from etcd-client, 
leaving only HMAC utilities. System only worked because pre-Day-54 library 
was still installed in /usr/local.

## Problem Discovered
- Header: Only HMAC methods (3031 bytes)
- Implementation: Only HMAC methods (128 lines)
- Installed library: Complete (8050 bytes header, 1MB .so)
- **Risk**: `make clean && make install` would break entire system

## Recovery
Found `etcd_client_fixed.cpp` (673 lines) in /vagrant root, added missing:
- get_encryption_key()
- get_component_config()  
- HMAC methods with proper signatures
- OpenSSL includes

## Decision
Restore complete implementation immediately before any `make install`.

## Consequences
- ✅ System safe from catastrophic rebuild
- ✅ Source code matches installed library
- ✅ HMAC + Encryption + All methods working
- 📝 Lesson: Always verify source matches installed binaries

Co-authored-by: Claude (Anthropic)
Co-authored-by: Alonso
