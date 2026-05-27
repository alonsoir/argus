# ADR-025: Plugin Integrity Verification (Ed25519 + TOCTOU-safe dlopen)

**Estado:** APROBADO — Listo para implementación  
**Fecha:** 2026-04-02  
**Rama:** `feature/bare-metal-arxiv`  
**Componentes afectados:** plugin-loader, todos los componentes con sección `plugins` en config JSON  
**ADR relacionados:** ADR-012 (Plugin Loader Architecture), ADR-013 (Seed Distribution), ADR-023 (CryptoTransport), ADR-024 (Deployment Topology SSOT)  
**Revisores (Consejo de Sabios):** Claude, ChatGPT-5, DeepSeek, Gemini, Grok, Qwen — tres rondas  
**Veredicto:** APROBADO unánime en ronda 3

---

## Contexto

El plugin-loader implementado en PHASE 1 (ADR-012) carga ficheros `.so` mediante `dlopen()` directo, verificando únicamente que el fichero existe en disco (`std::filesystem::exists`). El propio comentario de cabecera documenta esta limitación:

```
// dlopen/dlsym lazy loading. Sin crypto. Sin seed-client (PHASE 1).
```

El flujo actual es:

1. Leer JSON config
2. `std::filesystem::exists(so_path)` — solo comprueba existencia
3. `dlopen()` directo — carga ciega

No existe verificación de integridad ni autenticidad. Existe una ventana TOCTOU entre `exists()` y `dlopen()` explotable por un atacante con acceso al filesystem.

La infraestructura criptográfica necesaria ya existe en el proyecto:
- Keypairs Ed25519 generados por `tools/provision.sh`
- libsodium 1.0.19 compilada desde fuente
- Paths canónicos ya establecidos: `/usr/lib/ml-defender/plugins/`

---

## Decisión

Se introduce verificación criptográfica obligatoria en el plugin-loader antes de cualquier `dlopen()`. La implementación sigue un esquema de firma offline (clave privada nunca en host productivo) con clave pública hardcoded en el binario compilado.

---

## Decisiones detalladas

### D1 — Firma Ed25519 offline obligatoria

Cada plugin `.so` se firma con la clave privada Ed25519 en la máquina de build/CI. La firma se deposita como `<plugin_name>.so.sig` en el mismo directorio. La clave privada **nunca** reside en el host de producción. El host contiene únicamente la clave pública, hardcoded en el binario (D7).

La rotación de claves implica recompilación y redespliegue del binario. Este coste es intencional: disuade rotaciones innecesarias y fuerza evaluación humana explícita ante cualquier cambio criptográfico.

### D2 — Validación de tamaño + `O_NOFOLLOW` + `fstat()`

Antes de leer el contenido del plugin, verificar que el tamaño es razonable para evitar DoS por lectura de ficheros gigantes o malformados:

```cpp
// 1. Abrir con O_NOFOLLOW — rechaza symlinks en el último componente
int fd = open(so_path.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
if (fd < 0) { /* rechazar */ }

// 2. fstat sobre el fd — verifica tipo y tamaño antes de leer
struct stat st;
if (fstat(fd, &st) < 0 || !S_ISREG(st.st_mode)) {
    close(fd); /* rechazar — no es fichero regular */
}

constexpr size_t MIN_PLUGIN_SIZE = 4096;             // mínimo ELF válido
constexpr size_t MAX_PLUGIN_SIZE = 10 * 1024 * 1024; // 10 MB — plugins reales < 500 KB
if (st.st_size < MIN_PLUGIN_SIZE || st.st_size > MAX_PLUGIN_SIZE) {
    log_critical("Plugin size suspicious: %zu bytes", st.st_size);
    close(fd);
    std::terminate();
}
```

El mismo patrón aplica al `.sig` con `MAX_SIG_SIZE = 512` bytes.

### D3 — Prefix check estricto antes de `open()`

La validación de path ocurre **antes** de abrir cualquier fd — es política (input validation), no operación privilegiada:

```cpp
namespace fs = std::filesystem;
// weakly_canonical evita bloqueos en mount points no disponibles
// en entornos resource-constrained
auto canonical = fs::weakly_canonical(so_path);
const std::string allowed_prefix = "/usr/lib/ml-defender/plugins/";
if (canonical.string().substr(0, allowed_prefix.size()) != allowed_prefix) {
    log_critical("Plugin path outside allowed prefix: %s", so_path.c_str());
    std::terminate(); // path traversal o config poisoning
}
// Solo después del prefix check: open()
```

### D4 — Secuencia de verificación y FD discipline

La secuencia completa es estrictamente ordenada. El fd se mantiene abierto sin interrupción desde `open()` hasta después del `dlopen()`. Cerrarlo entre verificación y carga reabre la ventana TOCTOU:

```
1.  prefix_check(so_path)                               // D3 — política antes de operación
2.  fd_so  = open(so_path, O_RDONLY|O_NOFOLLOW|O_CLOEXEC)
3.  fstat(fd_so) + size check                           // D2
4.  prefix_check(sig_path)                              // D3 — también para el .sig
5.  fd_sig = open(sig_path, O_RDONLY|O_NOFOLLOW|O_CLOEXEC)
6.  fstat(fd_sig) + size check (max 512 bytes)          // D2 + D5
7.  content = read(fd_so)
8.  sig     = read(fd_sig)
9.  sha256  = crypto_hash_sha256(content)              // D6 — forense
10. verify  = crypto_sign_verify_detached(sig, content, pubkey_embedded) // D1
11. handle  = dlopen("/proc/self/fd/" + fd_so)         // nunca volver al path
12. close(fd_so); close(fd_sig)                        // solo después de dlopen exitoso
```

### D5 — Mismo patrón fd para el fichero `.sig`

El fichero de firma se abre con `O_NOFOLLOW` y se lee desde el fd. La ruta del `.sig` se infiere automáticamente añadiendo `.sig` al path del `.so`. Se puede sobreescribir con campo explícito `"signature"` en el JSON config.

### D6 — SHA-256 adicional para logging forense

Se calcula hash SHA-256 del contenido leído del fd antes de la verificación Ed25519. Su función es forense: distingue corrupción accidental de tampering deliberado y facilita correlación con Falco. El log incluye:

- Hash SHA-256 del plugin
- Tamaño en bytes (`st.st_size`)
- Timestamp de última modificación (`st.st_mtime`)
- Fingerprint de la clave pública embebida actual

Coste despreciable con libsodium (`crypto_hash_sha256`).

### D7 — Clave pública hardcoded en binario vía CMake

La clave pública Ed25519 se inyecta en tiempo de compilación como constante en el binario del plugin-loader. Elimina el vector de sustitución del fichero de clave pública:

```cmake
# tools/provision.sh exporta la pubkey como hex
# CMakeLists.txt la inyecta en compilación:
target_compile_definitions(plugin_loader PRIVATE
        MLD_PLUGIN_PUBKEY_HEX="${PLUGIN_PUBKEY_HEX}")
```

**Garantía contractual (explícita):** El plugin-loader rechaza cualquier firma generada con una clave distinta a la embebida en el binario actual, sin excepción. Esta garantía se deriva del funcionamiento de Ed25519 pero se documenta como invariante de diseño.

La clave pública no es un secreto. Hardcodearla en código fuente abierto es correcto y seguro.

### D8 — Campo `"signature"` en JSON config

```json
{
  "name": "libplugin_hello",
  "path": "/usr/lib/ml-defender/plugins/libplugin_hello.so",
  "signature": "/usr/lib/ml-defender/plugins/libplugin_hello.so.sig",
  "active": true,
  "require_signature": true,
  "allowed_key_id": "ed25519:2026-04-prod"
}
```

`"signature"` es opcional — si ausente, se infiere como `path + ".sig"`.  
`"require_signature"` por defecto es `true` en producción, `false` con `MLD_DEV_MODE=1`.  
`"allowed_key_id"` es opcional en PHASE 1, preparado para D12.

### D9 — Fail-closed explícito y diferenciado

**Plugin con `"require_signature": true` (default en producción):**
- Verificación fallida → log `CRITICAL` con: nombre del plugin, path intentado, motivo exacto (firma inválida / symlink detectado / tamaño fuera de rango / path traversal / key mismatch), fingerprint de la clave pública actual
- `std::terminate()` — el componente no arranca

**Plugin con `"require_signature": false` (solo desarrollo):**
- Verificación fallida → log `WARNING`
- Componente continúa sin ese plugin

Coherente con `std::set_terminate()` ya insertado en los 6 componentes `main()` y con D1 de ADR-023.

**Nota operacional:** Los componentes deben ejecutarse bajo systemd con `Restart=always` y `RestartSec=5s` para evitar caídas permanentes ante errores puntuales de verificación.

### D10 — Limpieza de entorno en launcher

```bash
unset LD_PRELOAD
unset LD_LIBRARY_PATH
exec /usr/bin/ml-defender-sniffer "$@"
```

Mitiga inyección vía linker dinámico (V6).

### D11 — Rotación de claves: operación exclusivamente manual

`provision.sh --reset` es una operación de alto impacto que ejecuta:

1. Muestra advertencia con fingerprint de la clave actual y consecuencias
2. Exige confirmación interactiva: escribir literalmente `RESET-KEYS`
3. Genera nuevo par Ed25519
4. Estampa fecha y hora en el nombre: `plugin_signing_key_20260402_143022.sk`
5. Muestra fingerprint de la nueva clave pública (hex corto) para que el admin lo anote
6. Registra en syslog: `KEY ROTATION: old signatures invalidated at <timestamp>`
7. Mueve (no borra) los `.sig` existentes a `/var/lib/ml-defender/invalidated/<timestamp>/` — preserva trazabilidad forense
8. No genera nuevas firmas automáticamente
9. Imprime instrucción explícita: **"La clave privada debe guardarse INMEDIATAMENTE en ubicación segura OFFLINE, fuera del filesystem de producción. El pipeline no arrancará hasta re-firmar todos los plugins con la nueva clave privada."**

**No existe cron de rotación automática.** Un cron puede emitir notificación (`NOTICE`: "La clave actual tiene N días"), nunca ejecutar la rotación.

**Estado parcial inaceptable:** No es posible tener plugins firmados con claves distintas. El arranque falla si cualquier plugin crítico presenta mismatch. Todo o nada.

**Dos escenarios de rotación:**

| Escenario | Trigger | Proceso |
|-----------|---------|---------|
| Rotación preventiva | Decisión admin (semestral o anual) | CI/CD: nueva clave → recompila binarios → re-firma plugins → redespliega |
| Rotación de emergencia | Compromiso detectado | Parada total → nueva clave → re-firma todo → descarte completo → redespliegue → clave privada a custodia offline |

### D12 — Clave pública por componente (preparación PHASE 2)

El campo `"allowed_key_id"` en el JSON config está preparado para que en futuras versiones cada componente pueda tener su propia clave de confianza. Formato: `"ed25519:YYYY-MM-<env>"` (ej: `"ed25519:2026-04-prod"`). Mitiga el vector V11 (mixed signing).

### D13 — Emergency Patch Protocol: Plugin Unload via Signed Message [POST-FEDER]

En producción sin compilador, la única forma segura de retirar un plugin
comprometido o defectuoso es mediante un plugin especial firmado con
`action="unload"`. Reutiliza íntegramente la infraestructura de confianza
existente: canal ZeroMQ, verificación Ed25519, y `dlclose()`.

**Payload del plugin de rollback:**

```json
{
  "action": "unload",
  "target_plugin": "libxgboost_v1.2.so",
  "reason": "CVE-2026-XXXX — modelo comprometido",
  "signature": "/usr/lib/ml-defender/plugins/unload_libxgboost_v1.2.sig"
}
```

**Secuencia de ejecución:**

1. Plugin-loader recibe plugin de tipo `action="unload"`
2. Verifica firma Ed25519 — misma cadena de confianza que cualquier plugin
3. Localiza handle activo de `target_plugin` en tabla interna
4. `dlclose(handle)` — descarga limpia
5. Elimina entrada de la tabla de plugins activos
6. Log `NOTICE`: nombre del plugin, motivo, timestamp, fingerprint de clave

**Garantías:**

- Un plugin de unload con firma inválida → CRITICAL + terminate() (D9)
- Un plugin de unload que referencia un plugin no cargado → WARNING, no terminate()
- La clave privada de firma nunca reside en producción (D1 — invariante)
- Zero downtime del pipeline: los demás componentes continúan operando

**Por qué es correcto:**

El sistema que sabe inyectar un anticuerpo sabe retirarlo.
Misma confianza, mismo canal, semántica extendida con un campo `action`.
No se añade superficie de ataque — se añade semántica a la superficie existente.

**Origen:** Sugerencia de founder externo vía LinkedIn (DAY 131).
Registrado como extensión post-FEDER de ADR-025, no como ADR independiente.

---

## Ficheros afectados

| Fichero | Cambio |
|---------|--------|
| `plugin-loader/src/plugin_loader.cpp` | Verificación Ed25519 + SHA-256 + O_NOFOLLOW + fstat + size check + fd discipline |
| `plugin-loader/CMakeLists.txt` | `target_link_libraries(plugin_loader PRIVATE sodium)` + inyección pubkey hex |
| `tools/provision.sh` | `--reset`: advertencias, confirmación, timestamp, fingerprint, movido de .sig a invalidated/ |
| JSON config schemas (6 componentes) | Campos `"require_signature"`, `"allowed_key_id"` en sección plugins |
| systemd units | `Restart=always`, `RestartSec=5s`, `unset LD_PRELOAD` |

---

## Tests requeridos antes de merge

| Test | Escenario | Resultado esperado |
|------|-----------|-------------------|
| TEST-INTEG-SIGN-1 | Plugin con firma válida | Carga exitosa |
| TEST-INTEG-SIGN-2 | Plugin con firma inválida | CRITICAL + terminate() |
| TEST-INTEG-SIGN-3 | .sig ausente | CRITICAL + terminate() |
| TEST-INTEG-SIGN-4 | Symlink attack (O_NOFOLLOW) | CRITICAL + terminate() |
| TEST-INTEG-SIGN-5 | Path traversal en JSON config | CRITICAL + terminate() |
| TEST-INTEG-SIGN-6 | Plugin firmado con clave rotada (mismatch) | CRITICAL + terminate() |
| TEST-INTEG-SIGN-7 | Plugin truncado (size check) | CRITICAL + terminate() |
| TEST-INTEG-SIGN-8 | Plugin unload con firma válida — target cargado | dlclose() exitoso + log NOTICE |
| TEST-INTEG-SIGN-9 | Plugin unload con firma inválida | CRITICAL + terminate() |
| TEST-INTEG-SIGN-10 | Plugin unload — target no cargado | WARNING, pipeline continúa |

---

## Threat model y vectores de ataque

| Vector | Viabilidad | Mitigación | Estado |
|--------|-----------|------------|--------|
| V1 — Compromiso clave privada | Alta si mal gestionada | Firma offline, privada nunca en host | D1 — Ahora |
| V2 — Sustitución .so + .sig (DAC débil) | Alta | AppArmor: solo root escribe en /usr/lib/ml-defender/plugins/ | Hardening Debian |
| V3 — Compromiso pipeline build | Media | Documentado como limitación PHASE 1; reproducible builds en PHASE 3 | Diferido |
| V4 — Path traversal en JSON config | Media | Prefix check estricto antes de open() | D3 — Ahora |
| V5 — Race en fd /proc/self/fd | Media | FD discipline: fd abierto sin interrupción | D4 — Ahora |
| V6 — LD_PRELOAD / entorno | Media | unset en launcher | D10 — Ahora |
| V7 — libsodium troyanizada | Baja | IMA en imagen Debian hardened | Diferido |
| V8 — Plugin legítimo con comportamiento malicioso | Alta | D8 snapshot/invariant check (ADR-023) + seccomp en PHASE 3 | Parcial |
| V9 — Symlink race | Alta | O_NOFOLLOW + fstat() en fd | D2 — Ahora |
| V10 — Truncamiento / DoS por tamaño | Media | Size check antes de lectura + log forense | D2 + D6 — Ahora |
| V11 — Mixed signing | Baja en PHASE 1 | Campo allowed_key_id preparado | D12 — PHASE 2 |

### Threat model boundaries

ADR-025 asume que el atacante no tiene privilegios root en el host de producción. Si root es comprometido, cualquier mecanismo en userspace es vulnerable a bypass. Ejemplo concreto: un atacante con root puede parchear el binario del verificador en memoria (vía `/proc/<pid>/mem`) para que acepte cualquier firma, o inyectar código en el proceso, bypassando completamente la verificación Ed25519.

**Mitigación en capas:**

- **Capa 1 (este ADR):** Firma Ed25519 offline + clave pública hardcoded → previene sustitución de plugins por usuarios no-root.
- **Capa 2 (ADR futuro — Runtime Monitoring):** Falco monitorea en tiempo real:

```yaml
- rule: ml-defender-plugin-modified
  desc: "Plugin signature or binary modified outside provision.sh"
  condition: >
    open_write and
    fd.name =~ "/usr/lib/ml-defender/plugins/.*\.(so|sig)" and
    not proc.name in ("provision.sh", "dpkg", "apt")
  output: "Plugin modification detected (user=%user.name command=%proc.cmdline)"
  priority: CRITICAL
```

- **Capa 3 (imagen Debian hardened):** AppArmor profile restringiendo escritura. IMA para integridad del binario verificador.

---

## Alternativas descartadas

**Clave pública en fichero root-only:** Introduce vector de sustitución del fichero. Descartada en favor de D7. Puede reconsiderarse si el coste de recompilación resulta prohibitivo en entornos muy distribuidos (opción B documentada).

**`memfd_create()` en lugar de `/proc/self/fd/N`:** Más portable pero mayor complejidad. Diferido a PHASE 2.

**IMA del kernel:** Diferido a imagen Debian hardened.

**Cron de rotación automática:** Antipatrón. Una rotación automática fallida puede dejar el sistema sin plugins en producción en un hospital. Descartado.

**`std::filesystem::canonical()` en D3:** Rechaza paths a mount points no disponibles — problemático en entornos resource-constrained. Se usa `weakly_canonical()` con prefix check estricto.

---

## Consecuencias

**Positivas:**
- Elimina carga ciega de `.so` arbitrarios
- Cierra ventana TOCTOU del plugin-loader
- Fail-closed explícito y auditable ante cualquier fallo de verificación
- Logging forense distingue corrupción de tampering
- Sin dependencias nuevas (libsodium ya en el proyecto)
- D13: Emergency Patch Protocol permite rollback de plugins en producción sin compilador

**Negativas / trade-offs:**
- Cada plugin nuevo requiere firma explícita en deploy
- Rotación de clave implica recompilación y redespliegue — coste operacional intencional
- `provision.sh` requiere actualización para gestionar ciclo de vida de firmas

---

## Registro del proceso de decisión

Desarrollado en tres rondas del Consejo de Sabios (Claude, ChatGPT-5, DeepSeek, Gemini, Grok, Qwen).

**Ronda 1:** Identificación de vectores de ataque y diseño base. Vectores V9 (symlink race) y V10 (TOCTOU en .sig) aportados por el Consejo — no estaban en el borrador inicial.

**Ronda 2:** Resolución de preguntas operacionales sobre rotación de claves, coste de D7, comportamiento de `provision.sh --reset` y rol de Falco. Consenso en todas las preguntas principales.

**Ronda 3:** Ajustes de precisión sin cambios bloqueantes. Incorporados: orden prefix_check antes de open(), validación de tamaño MIN/MAX para .so y .sig, systemd Restart=always, formato allowed_key_id, exclusiones dpkg/apt en regla Falco, log st_mtime en D6, garantía contractual explícita en D7, ejemplo concreto de root compromise en threat model boundaries, tabla de tests TEST-INTEG-SIGN-1 a 7.

**Extensión DAY 131:** D13 (Emergency Patch Protocol) añadido a raíz de sugerencia de founder externo vía LinkedIn. Tests SIGN-8/9/10 añadidos. Implementación diferida a post-FEDER.

**Posición de minoría registrada (Grok, ronda 1):** En componentes ultra-críticos como `firewall-acl-agent`, `std::terminate()` incluso para plugins sin `require_signature: true`. Árbitro adopta posición mayoritaria: el flag por componente con default `true` en producción es el mecanismo de control.

**Posición de minoría registrada (Gemini, ronda 2):** `provision.sh` debería guardar histórico local de rotaciones incluyendo hash del binario resultante. Diferido a implementación de `provision.sh`.

**Nota de atribución:** En las tres rondas, Qwen se autoidentificó como DeepSeek en cuatro ocasiones. Las contribuciones están registradas bajo el nombre del modelo según el archivo de respuesta recibido. El patrón queda documentado como observación de comportamiento del Consejo.