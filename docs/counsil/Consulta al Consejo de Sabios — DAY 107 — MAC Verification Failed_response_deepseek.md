## DeepSeek — Análisis MAC Verification Failed (DAY 107)

He revisado la evidencia. Se han descartado las causas obvias. Buen trabajo de depuración. Ahora hay que buscar lo *no obvio*.

Mis hipótesis, ordenadas de más probable a menos:

---

### H1 — Orden incorrecto de compresión y cifrado en uno de los dos lados

**Síntoma:** MAC failure → el descifrado falla porque el ciphertext no es el que se generó en el otro extremo.

**Causa posible:** `ml-detector` hace `compress(LZ4) → encrypt(ChaCha20)`, mientras que `etcd-server` hace `decrypt → decompress` (orden correcto). Pero si el servidor **no** descompone antes de verificar MAC (o viceversa), el tag no coincidirá.

**Lo que sabemos:** `etcd-client` (usado por ml-detector) tiene este orden:
```cpp
// etcd-client/src/etcd_client.cpp (debería)
auto compressed = lz4_compress(data);
auto encrypted = tx_->encrypt(compressed);
send(encrypted);
```

**Pregunta:** ¿`etcd-server` aplica exactamente el inverso? `decrypt → decompress`? Si el servidor aplica `decrypt` sobre el payload recibido y luego `decompress` sobre el resultado, está bien. Si por error intenta `decompress` antes de `decrypt` (o si el cliente no comprime pero el servidor espera compresión), el MAC fallará.

**Verificación:** Añade logs en `etcd-server` justo antes de `rx_->decrypt()` que muestren los primeros 16 bytes del payload recibido. Compáralos con los logs del cliente justo después de `tx_->encrypt()`. Deberían coincidir exactamente.

**Si no coinciden:** El problema está en el serialización/deserialización del mensaje (ver H4).

---

### H2 — Nonce desincronizado entre cliente y servidor

**Mecanismo:** ChaCha20-Poly1305 requiere que el nonce sea **único por clave**. Si el servidor espera un nonce distinto al que el cliente usó, el descifrado falla.

**Cómo ocurre:** El `etcd-server` podría estar usando un `CryptoTransport` que inicializa su nonce counter en **0** cada vez que se construye. El cliente, al hacer múltiples peticiones (ej: registro + PUT), incrementa su contador. El servidor, al recibir la primera petición cifrada, espera nonce=0 (porque acaba de arrancar), pero el cliente envía nonce=1 (porque ya usó nonce=0 en un intento previo que quizás falló y retransmitió).

**Lo que no sabemos:** ¿Hay reintentos? ¿El cliente reutiliza la misma sesión `tx_` para el PUT después de un fallo? ¿El servidor recrea `rx_` entre peticiones?

**Verificación:**
- En `etcd-server`, loguea el nonce extraído del mensaje entrante justo antes de `decrypt`.
- En `ml-detector`, loguea el nonce generado justo antes de `encrypt`.
- Deben coincidir **exactamente** (12 bytes). Si no, es el problema.

**Solución posible:** El nonce debe incluir un identificador de sesión o el contador debe ser compartido (a través del protocolo). En `etcd-client`, el nonce se serializa en el mensaje; el servidor debe leerlo y usarlo tal cual, no su propio contador.

---

### H3 — El servidor no está usando el `rx_` correcto (contexto real distinto al simulado)

**Contexto:** `etcd-server` tiene dos `CryptoTransport`:
- `tx_` con `CTX_ETCD_RX` (para cifrar respuestas)
- `rx_` con `CTX_ETCD_TX` (para descifrar peticiones) ← este falla

**Hipótesis:** El `rx_` se construye con `CTX_ETCD_TX`, pero el cliente usa `CTX_ETCD_TX` también? No, el cliente usa `CTX_ETCD_TX` para cifrar. Eso sería correcto.

**Pero:** ¿Hay otro `CryptoTransport` en el servidor que se esté usando por error? Por ejemplo, un `CryptoTransport` para el canal de registro (que no cifra) podría estar siendo reutilizado.

**Verificación:** En `etcd-server/src/component_registry.cpp`, busca dónde se llama a `rx_->decrypt()`. Asegúrate de que ese `rx_` es el que fue inicializado con `CTX_ETCD_TX` (y no otro). Añade un log que muestre el contexto real usado.

---

### H4 — La serialización del mensaje antes de cifrar no es la misma que se deserializa antes de descifrar

**Problema:** El cliente serializa un protobuf, lo comprime, lo cifra. El servidor recibe los bytes, pero antes de descifrar podría estar aplicando algún parseo (por ejemplo, leyendo una cabecera de longitud) que modifica el buffer.

**Lo que hemos visto:** El endpoint `/register` funciona sin cifrado. El endpoint `/v1/config/ml-detector` es cifrado. ¿Podría el servidor estar esperando un formato diferente en el body para los endpoints cifrados? Por ejemplo, que el cuerpo del PUT sea `{ "key": "...", "value": {...} }` pero el cliente envía solo el protobuf del valor.

**Verificación:**
- En `ml-detector`, guarda en un fichero el buffer **exacto** que se pasa a `tx_->encrypt()` (antes de cifrar).
- En `etcd-server`, guarda el buffer **exacto** que recibe `rx_->decrypt()` (antes de descifrar).
- Compáralos. Deben ser **bit a bit idénticos**. Si no lo son, el problema está en la transmisión o en el manejo de buffers en ZeroMQ (alineación, fragmentación, etc.)

---

### H5 — El servidor no está inicializando libsodium correctamente

**Síntoma:** `crypto_aead_chacha20poly1305_ietf_decrypt` puede fallar si las claves no están alineadas a 16 bytes o si libsodium no se ha inicializado con `sodium_init()`.

**Lo que sabemos:** `SeedClient` llama a `sodium_init()` en su constructor (o debería). Pero si `etcd-server` crea el `CryptoTransport` antes de que `sodium_init()` sea llamado, la derivación HKDF podría fallar silenciosamente y producir una clave inválida.

**Verificación:** En `etcd-server`, justo antes de usar `rx_->decrypt()`, comprueba que `sodium_init()` ya se ha llamado (la función es idempotente). Añade `if (sodium_init() < 0) { /* fatal */ }`.

---

### H6 — La compresión LZ4 no es determinista o añade metadatos que el otro lado no espera

**Problema:** LZ4 frame format incluye una cabecera mágica (4 bytes `0x184D2204`). Si un lado usa frame format y el otro raw block, la descompresión puede tener éxito pero los bytes descifrados no coincidirán porque el ciphertext incluye la cabecera.

**Verificación:** Comprueba que ambos lados usen **exactamente la misma API LZ4**. El proyecto usa `LZ4_compress_default` y `LZ4_decompress_safe` (raw block) o `LZ4F_*` (frame)? Si hay mezcla, MAC failure.

---

### H7 — La clave HKDF se deriva correctamente, pero el contexto `tx`/`rx` está intercambiado en el servidor

**Posible error:** En `etcd-server`, el `rx_` debería usar `CTX_ETCD_TX` (para descifrar peticiones), pero el `tx_` usa `CTX_ETCD_RX` (para cifrar respuestas). Esto es simétrico y correcto **solo si** el cliente también usa `CTX_ETCD_TX` para cifrar y `CTX_ETCD_RX` para descifrar.

**Pregunta:** ¿Estás seguro de que el cliente `ml-detector` usa `CTX_ETCD_TX` para cifrar el PUT? En `etcd-client/etcd_client.cpp`, busca la inicialización de `tx_`. Podría estar usando `CTX_ETCD_RX` por error.

**Verificación:** En `ml-detector`, loguea el contexto usado por `tx_` y `rx_`. En `etcd-server`, loguea los mismos. Deben coincidir en el par.

---

### Resumen de acciones para depurar

| # | Acción | Comando / código |
|---|--------|------------------|
| 1 | Log buffer antes de cifrar en cliente | `std::ofstream("client_before_encrypt.bin", std::ios::binary).write(data, len);` |
| 2 | Log buffer recibido antes de descifrar en servidor | `std::ofstream("server_before_decrypt.bin", std::ios::binary).write(data, len);` |
| 3 | Comparar los dos ficheros | `cmp -l client_before_encrypt.bin server_before_decrypt.bin` |
| 4 | Log nonce generado por cliente | `std::hex << std::setw(2) << ...` |
| 5 | Log nonce extraído por servidor | antes de `decrypt` |
| 6 | Verificar orden compresión/cifrado en ambos lados | Revisar código fuente |
| 7 | Comprobar inicialización libsodium | `sodium_init()` en `main()` |

---

**Mi voto:** La causa más probable es **H1** (orden de compresión) o **H2** (nonce desincronizado). Pero sin logs de los buffers reales, es imposible saberlo.

Si las verificaciones 1-3 muestran buffers idénticos, entonces el problema está en la derivación de clave (H5 o H7). Si son diferentes, el problema es de transmisión o serialización.

Sigue estos pasos y trae los resultados. Estaremos listos para la siguiente ronda.

— DeepSeek, miembro del Consejo de Sabios