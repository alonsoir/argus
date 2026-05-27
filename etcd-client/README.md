# etcd-client Library

Minimal but capable etcd client library for ML Defender components.

## Features
- Component registration and discovery
- Encryption: ChaCha20-Poly1305 (libsodium) with AES256 fallback
- Compression: LZ4
- Config versioning (master + active copies)
- Heartbeat mechanism
- 100% JSON-driven configuration

## Status
🚧 Work in Progress - Day 17 (Dec 16, 2025)

## Dependencies
- libsodium (ChaCha20 encryption)
- liblz4 (LZ4 compression)
- nlohmann/json (JSON parsing)
- cpp-httplib (HTTP client)

## Design Principles
- Via Appia Quality: Built to last
- KISS: Minimal but capable
- JSON is law: Zero hardcoded values
- Thread-safe by design
