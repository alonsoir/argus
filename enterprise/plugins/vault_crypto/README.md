# Plugin Enterprise: vault_crypto

**Estado:** WIP — Day 160

## Qué hace

Provee cifrado ChaCha20-Poly1305 + compresión LZ4 con semilla obtenida
de HashiCorp Vault en lugar del archivo local `seed.bin`.

Implementa la interfaz `ICryptoProvider` (ADR-044).

## Cuándo usarlo

Cuando el entorno dispone de HashiCorp Vault y se requiere rotación
automática de claves sin intervención manual.

## Features requeridas en el token

```json
"features": ["vault_crypto"]
```

## Qué NO hace

No reemplaza `crypto-transport/` (OSS). Ambos coexisten.
El admin elige explícitamente cuál usar en `argus.conf`.

## Archivos (pendiente Day 160)

- `vault_provider.cpp` — implementación ICryptoProvider
- `vault_provider.hpp` — interfaz pública
- `CMakeLists.txt` — produce `vault_provider.so`
- `tests/` — RED→GREEN: token inválido para, token válido carga
