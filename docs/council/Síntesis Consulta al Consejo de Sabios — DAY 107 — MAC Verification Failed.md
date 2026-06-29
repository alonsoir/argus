¡Felicidades a tu madre por sus 88 años! Vaya regalo de cumpleaños — un pipeline que vuelve a vivir.

Vamos por partes.

---

## 1. Síntesis para el Consejo de Sabios — DAY 107

**Asunto**: Resolución MAC verification failed — Informe post-mortem

Consejo, gracias por vuestra intervención. El diagnóstico fue correcto y el hexdump que propuso Gemini fue la clave que lo reveló todo. Aquí el post-mortem completo.

**Root cause real**: En los adaptadores `etcd_client.cpp` de ml-detector, sniffer y firewall-acl-agent, el campo `component_config_path` del `etcd_client::Config` nunca se seteaba. Sin ese path, el `SeedClient` no se inicializaba, `tx_` quedaba `nullptr`, y el guard `if (config_.encryption_enabled && tx_)` en `process_outgoing_data()` fallaba silenciosamente — enviando datos comprimidos pero **sin cifrar** con `Content-Type: application/octet-stream`. El servidor recibía LZ4 crudo, intentaba descifrarlo con ChaCha20-Poly1305, y producía MAC failure. El endpoint `/register` (texto plano, sin cifrado) funcionaba perfectamente, lo que confundía el diagnóstico.

**Lo que descartamos antes de llegar aquí** (en orden):
- Seeds distintos entre componentes → sincronizados
- Doble libsodium (so.23 + so.26) → symlink `so.23→so.26`
- CTX_ETCD_TX/RX invertidos en etcd-server → swap aplicado
- LZ4 orden incorrecto → descartado desactivando compresión (MAC persistió)
- Build cacheado / librería antigua → rebuild limpio con `rm -rf build-debug`

**Lo que reveló el hexdump de Gemini**:
```
body_size=8953
HEXDUMP first16: b2 46 00 00 f1 46 7b 0a 20 20 22 5f 68 65 61 64
```
Bytes 4-7: `7b 0a 20 20` = `{\n  ` — JSON en claro visible tras el header LZ4. El ciphertext no era ciphertext.

**Fixes aplicados**:
1. `ml-detector/src/etcd_client.cpp` → `component_config_path = "/etc/ml-defender/ml-detector/ml_detector_config.json"`
2. `firewall-acl-agent/src/core/etcd_client.cpp` → mismo patrón con `firewall.json`
3. `sniffer/src/userspace/etcd_client.cpp` → `component_config_path` + reescritura de `get_encryption_seed()` para leer seed local desde `seed.bin` (el sniffer además intentaba obtener el seed del servidor vía deprecated `get_encryption_key()`)
4. `etcd-server/src/component_registry.cpp` → swap CTX_ETCD_TX/RX (rx_ usa TX, tx_ usa RX)

**Resultado**: 6/6 RUNNING con cifrado ChaCha20-Poly1305 funcional.

**Preguntas abiertas para el Consejo**:

1. El swap CTX en etcd-server — ¿es realmente necesario dado que el fix real era `component_config_path`? Ahora tenemos dos cambios entrelazados y no hemos verificado si el swap era correcto independientemente. ¿Debería revertirse el swap y probar?

2. El sniffer lee el seed directamente desde `seed.bin` en su `get_encryption_seed()`, mientras que los otros componentes lo cargan vía `SeedClient` en el constructor de `CryptoTransport`. ¿Es arquitectónicamente correcto tener dos paths de carga del seed en el mismo sistema?

3. Los directorios `/etc/ml-defender/{component}/` tienen `chmod 755` y `seed.bin` tiene `640 root:vagrant` — SeedClient advierte que espera `0600`. ¿Debería el SeedClient aceptar `640` como permiso válido para procesos no-root, o hay que cambiar la lógica de arranque?

---

## 2. Estado actual del pipeline — Honestidad técnica

**Lo que funciona**: 6/6 RUNNING con cifrado activo. Los fixes de hoy son funcionales en la VM actual.

**Lo que está en estado intermedio** — tienes razón en preocuparte:

El pipeline arranca correctamente HOY porque aplicamos manualmente durante la sesión:
- `sudo chmod 755` en los 6 directorios de `/etc/ml-defender/`
- `sudo chmod 640 + chown root:vagrant` en los `seed.bin`
- `sudo cp etcd-server/seed.bin` → los 5 componentes restantes (seeds sincronizados)
- Symlinks JSON en `/etc/ml-defender/{component}/` → `/vagrant/{component}/config/`
- `libsodium.so.23 → libsodium.so.26` symlink
- Rebuild de `libcrypto_transport.so` (era de febrero)

**Si haces `vagrant destroy && vagrant up` mañana, el pipeline NO arrancará** porque `provision.sh` no hace ninguna de esas cosas.

**Lo que queda en `provision.sh`**: genera seeds independientes por componente (no sincronizados), deja directorios `drwx------ root`, no crea symlinks JSON, no verifica versión de libcrypto_transport.

Gracias Alonso. He leído los cinco. Síntesis ejecutiva:

---

## Veredicto del Consejo — 5/5 respondieron

### Q1 — Swap CTX: ¿revertir?
**Divided**: Gemini dice mantener. DeepSeek, Qwen y ChatGPT5 dicen revertir y probar independientemente. Grok dice probar ambos. **Decisión recomendada para DAY 108**: revertir el swap, arrancar pipeline, verificar. Si MAC falla → swap era necesario y lo restauramos con evidencia. Si funciona → era ruido.

### Q2 — Doble path seed
**Unanimidad 5/5**: unificar bajo `SeedClient`. El sniffer debe eliminiar `get_encryption_seed()` manual y usar `SeedClient` como todos. Deuda técnica clara.

### Q3 — Permisos 640 vs 600
**Consenso**: SeedClient debe aceptar 640 con warning en desarrollo, 600 obligatorio en producción. No hacer fail-hard por 640.

### Insight más valioso (ChatGPT5, confirmado por todos)
El bug fue un **fallo silencioso de configuración que degradó la seguridad sin crashear**. La solución estructural:
```cpp
if (encryption_enabled && !tx_) {
    LOG_CRITICAL("tx_ null — component_config_path no seteado");
    std::terminate();
}
```
Esto habría revelado el problema en el primer arranque. Este invariant debe añadirse a los 3 adaptadores `etcd_client.cpp`.

---

## Estado honesto del pipeline

| Qué | Estado |
|---|---|
| 6/6 RUNNING con cifrado real | ✅ |
| Fixes en código fuente | ✅ commiteables |
| `provision.sh` reproduce el estado | ❌ roto |
| `vagrant destroy && vagrant up` funciona | ❌ no garantizado |

**La distinción que pedías**: Los componentes obtienen el seed de dos formas ahora mismo — sniffer lee `seed.bin` directamente (fix de hoy), los demás vía `SeedClient` en `CryptoTransport`. Ninguno lo obtiene de etcd-server en runtime — todos leen el fichero local. Pero `provision.sh` todavía genera seeds independientes por componente, así que si se reprovisiona sin el fix manual de sincronización, los seeds diverjan de nuevo.



## LinkedIn post (English)

---

**DAY 107 — The MAC that wasn't**

Six hours chasing a `MAC verification failed` error in ChaCha20-Poly1305. Seeds identical. Contexts symmetric. One libsodium. Fresh binaries. Everything correct. Still failing.

I brought in the Consejo de Sabios — seven LLMs as adversarial peer reviewers. After ruling out every obvious cause, Gemini made a simple suggestion: dump the first 16 bytes arriving at the server before decryption.

```
body_size=8953
first16: b2 46 00 00 f1 46 7b 0a 20 20 22 5f 68 65 61 64
```

Bytes 4-7: `7b 0a 20 20` — that's `{\n  "` in ASCII. JSON. In plain sight. Inside what was supposed to be ciphertext.

The actual bug had nothing to do with cryptography.

`component_config_path` was never set in the `etcd_client::Config` struct across three components. Without it, `SeedClient` never initialized, `tx_` stayed `nullptr`, and a silent guard in `process_outgoing_data()` skipped encryption entirely — sending LZ4-compressed JSON with `Content-Type: application/octet-stream`. The server tried to decrypt it. MAC failure was guaranteed, every time.

The `/register` endpoint worked perfectly — it sends plaintext. Only the encrypted PUT failed. Classic misdirection.

The deeper lesson: **a silent security degradation is more dangerous than a crash**. The system appeared to work. Only one endpoint failed. Without the hexdump, this could have shipped.

The fix that should have been there from the start:
```cpp
if (config_.encryption_enabled && !tx_) {
    std::terminate(); // component_config_path not set
}
```

Fail loud or don't fail at all.

Pipeline: 6/6 running. ChaCha20-Poly1305 active across all channels.

Today also happens to be my mother's 88th birthday. She doesn't know what a nonce is, but she taught me never to hide what's broken. That's the same principle.

*Piano, piano.*

\#MLDefender #aRGusNDR #CyberSecurity #NDR #OpenSource #Cryptography #BuildInPublic #TDH #ConsejoDesSabios

---

Descansa, Alonso. DAY 107 cerrado. El pipeline vive.