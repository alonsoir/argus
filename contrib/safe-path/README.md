# safe_path — ADR-037

Header-only C++20 library for path traversal prevention in aRGus NDR.

## Usage

```cpp
#include <safe_path/safe_path.hpp>

// General config files
const auto safe = argus::safe_path::resolve(config_path, "/etc/ml-defender/");

// Writable output paths
const auto out = argus::safe_path::resolve_writable(output_path, "/etc/ml-defender/");

// Cryptographic seed material (O_NOFOLLOW + 0400 check)
const int fd = argus::safe_path::resolve_seed(seed_path);
// ... use fd ...
close(fd);
```

## Security guarantees

- Rejects `../` traversal via `weakly_canonical()`
- Normalises trailing slash to prevent prefix bypass
- `resolve_seed()`: symlink check + permissions check (0400) + `O_NOFOLLOW | O_CLOEXEC`
- TOCTOU window documented — mitigated by AppArmor in production (see ADR-037)

## Tests

9 acceptance tests (RED→GREEN). Each documents a real attack vector.
