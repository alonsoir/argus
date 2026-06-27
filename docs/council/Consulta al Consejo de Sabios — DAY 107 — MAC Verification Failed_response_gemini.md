REVISOR: Gemini (Google) / Perfil: Sistemas Distribuidos & Criptografía Aplicada
FECHA: 4 de abril de 2026
ESTADO: **AUDITORÍA DE EMERGENCIA — DAY 107**

Alonso, el Consejo ha recibido el reporte. Si los **seeds**, los **contextos** y la **versión de libsodium** son idénticos, estamos ante un error de **estado de memoria** o de **secuenciación de bytes**. El error `MAC verification failed` en ChaCha20-Poly1305 es binario: o la clave es distinta, o el mensaje ha mutado, o el **Nonce** no es el que el receptor espera.

Descartadas las causas obvias, el Consejo propone las siguientes **4 Hipótesis de "Nivel Profundo"** para investigar de inmediato:

---

### Hipótesis 1: El Fantasma del Nonce Monotónico (Desincronización de Estado)
`CryptoTransport` usa un contador de 64 bits para el Nonce. Si el `ml-detector` se reinicia pero el `etcd-server` no (o viceversa), ocurre lo siguiente:
* **Escenario:** El cliente reinicia su contador a `0`. El servidor espera el Nonce `N+1` de la sesión anterior.
* **Resultado:** El servidor intenta descifrar con `Nonce=0` cuando su estado interno espera `N+1`. ChaCha20-Poly1305 fallará el MAC instantáneamente aunque la clave sea la misma.
* **Prueba:** Reinicia **ambos** procesos simultáneamente. Si el primer PUT funciona y el segundo falla, tienes un problema de persistencia/sincronización de Nonces.



### Hipótesis 2: El Orden de Operaciones LZ4 vs. Crypto (Double-Wrapping)
Has mencionado la compresión LZ4 en los puntos no verificados. Este es un error clásico de "capa".
* **El Error:** Si el cliente hace `encrypt(compress(data))` y el servidor intenta `decompress(decrypt(data))`, el MAC fallará porque el servidor está intentando descifrar algo que no fue cifrado en ese orden, o peor, intenta descifrar el stream comprimido con parámetros incorrectos.
* **Verificación:** Revisa `etcd_client.cpp` y `component_registry.cpp`. Asegúrate de que el orden sea **espejo exacto**:
    * Cliente: `Payload -> Compress -> Encrypt -> Wire`.
    * Servidor: `Wire -> Decrypt -> Decompress -> Payload`.
* **Sospecha:** Si el `decrypt` falla *antes* de que LZ4 actúe, es probable que la longitud del buffer que se pasa a `decrypt` incluya bytes extra de la cabecera de compresión que no deberían estar ahí.

### Hipótesis 3: Corrupción de Punteros en el `MessageContext` (Memoria)
Dado que estamos en C++20 y usamos `const uint8_t*`, existe la posibilidad de que el buffer que `ml-detector` pasa a libsodium sea volátil.
* **Escenario:** Si el `plaintext` se destruye o se sobrescribe (por ejemplo, un `std::string` temporal que sale de scope) *antes* de que `crypto_aead_chacha20poly1305_ietf_encrypt` termine su trabajo, el ciphertext resultante será basura.
* **Verificación:** Asegúrate de que el buffer de salida (`ciphertext`) no solape con el de entrada en memoria, a menos que uses la API *in-place* de libsodium explícitamente.



### Hipótesis 4: Endianness o Alineación en el Nonce de 96 bits
ChaCha20-Poly1305 IETF espera un nonce de 12 bytes (96 bits). Tu implementación usa:
`[ 4 bytes fijos | 8 bytes contador ]`.
* **El Riesgo:** Si el servidor y el cliente están interpretando los 8 bytes del contador con diferente **Endianness** (poco probable en x86_64, pero posible si hay casting de punteros `uint64_t*` a `uint8_t*`), el MAC fallará.
* **Verificación:** Loguea el Nonce en hexadecimal en ambos extremos justo antes de la llamada a libsodium. Deben ser idénticos byte a byte.

---

### Plan de Acción Inmediato (The "Deep-Dive" Trace)

Para resolver esto en los próximos 60 minutos, aplica esta instrumentación:

1.  **Log de Clave Derivada (DEBUG ONLY):** En el constructor de `CryptoTransport`, imprime los primeros 4 bytes de la `session_key` generada por HKDF para el contexto `TX`. Si los 4 bytes no coinciden en el `tx_` del cliente y el `rx_` del servidor, el problema es **HKDF** (posiblemente un carácter invisible en el string del contexto o un seed mal leído a pesar de los checks).
2.  **Hexdump del Ciphertext:** Imprime el hexdump de lo que sale del cliente y lo que entra en el servidor.
    * Si el primer byte cambia -> Problema de transporte/ZMQ.
    * Si los últimos 16 bytes (MAC) cambian -> Corrupción en el cable.
3.  **Check de Longitud:** Verifica que `ciphertext_len` sea exactamente `plaintext_len + 12 (nonce) + 16 (tag)`. Si hay un byte de diferencia, libsodium rechazará el bloque.

**Pregunta del Consejo:** ¿El `etcd-server` está usando `std::string` o `std::vector<uint8_t>` para recibir el body del PUT? Si hay un `\0` en el ciphertext y usas `std::string`, el buffer se truncará y el MAC fallará por datos incompletos.

**Alonso, revisa el truncamiento por `\0` en el transporte del PUT. Es el sospechoso número uno cuando el registro (texto plano) funciona pero el cifrado (binario) falla.** 🏛️🛡️🚀