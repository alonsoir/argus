# Security Path Primitives — safe_path Taxonomy

> **Consejo 8/8 DAY 127 — PERMANENTE**  
> Toda nueva superficie de ficheros se clasifica con PathPolicy antes de implementar.
> Documentar en este fichero.

---

## Tabla de primitivas

| Primitiva | Caso de uso | Técnica central | Permisos | Estado |
|-----------|-------------|-----------------|----------|--------|
| `resolve()` | Validación general | `weakly_canonical()` post-resolución | cualquiera | ✅ Activa |
| `resolve_seed()` | Material criptográfico | `lstat()` pre-resolución, sin symlinks | exactamente `0400` | ✅ Activa |
| `resolve_config()` | Configs con symlinks legítimos | `lexically_normal()` pre-resolución | cualquiera | ✅ Activa |
| `resolve_model()` | Modelos firmados Ed25519 | TBD — ADR-038 | TBD | ⏳ Backlog |

---

## Diagrama de decisión
¿Material criptográfico (seed, clave privada)?
└─ SÍ → resolve_seed()
• lstat() sobre path ORIGINAL (nunca sobre resolved)
• Rechaza symlinks incondicionalmente
• Enforza permisos exactos 0400 — std::terminate() si viola
• Componentes que lo usan deben arrancar con sudo
¿Config con symlinks legítimos (dev/prod parity)?
└─ SÍ → resolve_config()
• lexically_normal() verifica prefix ANTES de seguir symlinks
• Acepta symlinks que apunten dentro del prefix
• Rechaza symlinks que escapen el prefix
¿Modelo ML firmado?
└─ SÍ → resolve_model()  [BACKLOG — ADR-038]
• Ed25519 signature verification
• No implementado — usar resolve() + verificación manual hasta ADR-038
¿Ninguno de los anteriores?
└─ resolve()
• weakly_canonical() post-resolución
• Verificación de prefix estándar
---

## PathPolicy enum conceptual

```cpp
// Documentación — no implementado como enum en producción (DAY 127)
// La selección de primitiva se hace en el punto de llamada.
enum class PathPolicy {
    GENERAL,        // resolve()        — ficheros generales
    CRYPTO_SEED,    // resolve_seed()   — material criptográfico
    CONFIG,         // resolve_config() — configs con symlinks legítimos
    SIGNED_MODEL,   // resolve_model()  — modelos firmados [BACKLOG ADR-038]
};
```

---

## Ejemplos de uso correcto

```cpp
// ✅ seed criptográfico
auto seed_path = safe_path::resolve_seed(
    "/etc/ml-defender/etcd-server/seed.bin",
    "/etc/ml-defender/etcd-server"
);

// ✅ config con symlink legítimo /etc/ml-defender/ → /vagrant/
auto cfg_path = safe_path::resolve_config(
    "/etc/ml-defender/sniffer/sniffer.json",
    "/etc/ml-defender/sniffer"
);

// ✅ fichero general
auto log_path = safe_path::resolve(
    "/vagrant/logs/lab/sniffer.log",
    "/vagrant/logs"
);
```

## Ejemplos de uso incorrecto

```cpp
// ❌ seed con resolve() — no enforza 0400 ni bloquea symlinks
auto seed_path = safe_path::resolve(
    "/etc/ml-defender/etcd-server/seed.bin",
    "/etc/ml-defender/etcd-server"
);

// ❌ config con resolve_seed() — rechazaría el symlink legítimo
auto cfg_path = safe_path::resolve_seed(
    "/etc/ml-defender/sniffer/sniffer.json",
    "/etc/ml-defender/sniffer"
);

// ❌ modelo con resolve() — no verifica firma Ed25519
auto model_path = safe_path::resolve(
    "/vagrant/ml-detector/models/production/level1/xgboost_cicids2017_v2.ubj",
    "/vagrant/ml-detector/models"
);
```

---

## Hallazgos que motivaron esta taxonomía

**DAY 126 — `fs::is_symlink(resolved)` es inútil post-`weakly_canonical()`**  
`weakly_canonical()` ya resuelve el symlink antes de que podamos inspeccionarlo.
El único `lstat()` defensivo es sobre el path original, antes de cualquier resolución.

**DAY 127 — `lexically_normal()` vs `weakly_canonical()`**  
Dos herramientas para dos casos de seguridad distintos:
- `lexically_normal()` normaliza el path **sin tocar el filesystem** → verifica prefix antes de seguir symlinks
- `weakly_canonical()` **resuelve contra el filesystem** → confirma destino final post-resolución

**DAY 125 — Property test encontró overflow en fix F17**  
Validación empírica de la necesidad de property testing en toda superficie aritmética.
Ver `docs/testing/PROPERTY-TESTING.md`.

**DAY 128 — resolve_seed() enforza 0400 con std::terminate()**  
Los componentes que leen seeds vía `resolve_seed()` requieren `sudo` en el Makefile.
`0440` viola la invariante — la solución correcta es `sudo`, no relajar permisos.

---

## Referencias

- ADR-025: Ed25519 plugin integrity, TOCTOU-safe dlopen
- ADR-026: XGBoost Track 1
- ADR-038: resolve_model() — BACKLOG
- CWE-22: Path Traversal
- CWE-23: Relative Path Traversal
- OWASP Path Traversal
- TOCTOU literature
 
---

## Estado de Verificación (DAY 129)

| Primitivo | Implementado | Tests | Estado |
|---|---|---|---|
| `resolve_seed()` | ✅ | TEST-INVARIANT-SEED | ✅ VERIFICADO |
| `resolve_config()` | ✅ | ConfigLoaderTraversal 3/3 | ✅ VERIFICADO DAY 129 |
| `resolve_model()` | ⏳ | — | BACKLOG ADR-038 |
| `resolve()` | ✅ | — | ✅ ACTIVO |

`DEBT-FIREWALL-CONFIG-PATH-001`: CERRADA DAY 129.
- `resolve_config()` en `config_loader.cpp` usa `argus::safe_path::resolve_config()`
- prefix siempre fijo (`/etc/ml-defender/`) — nunca derivado del input
- 3/3 tests GREEN: dot-dot rejection + out-of-prefix rejection + valid path acceptance
