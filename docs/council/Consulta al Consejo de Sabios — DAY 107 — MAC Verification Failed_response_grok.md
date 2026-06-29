**Hipótesis principales (excluyendo semillas distintas, contextos asimétricos y doble libsodium/libsodium versionada)**

Estas son las causas más probables que explican **exactamente** el síntoma “MAC verification failed” en ChaCha20-Poly1305 IETF cuando todo lo demás parece idéntico:

1. **Orden o activación inconsistente de LZ4 (compresión)**  
   El pipeline más común es: `plaintext → LZ4_compress → CryptoTransport::encrypt → send`.  
   En recepción: `recv → CryptoTransport::decrypt → LZ4_decompress`.  
   Si el cliente **sí** comprime antes de encriptar y el servidor **o bien**:
    - no descomprime después del decrypt, o
    - descomprime *antes* del decrypt (orden invertido),  
      entonces los bytes que llegan a `decrypt()` **no son** lo que produjo `encrypt()`.  
      Resultado: MAC fallará siempre.  
      Esto es lo primero que recomiendo verificar (es la causa #1 que aún no descartaste).

2. **Uso inconsistente de AAD (Associated Data)**  
   La API de libsodium ChaCha20-Poly1305 IETF **sí** acepta AAD.  
   Muchos wrappers de `CryptoTransport` añaden AAD implícitamente (método HTTP + path + Content-Length + versión de protocolo, etc.) para proteger contra ataques de confusión de contexto.  
   Si en `ml-detector` (etcd-client) el `encrypt()` pasa un AAD distinto al que pasa `decrypt()` en el servidor (o uno lo pasa y el otro pasa `nullptr`/longitud 0), la Poly1305 tag **no coincidirá** aunque clave y nonce sean idénticos.

3. **Lectura corrupta del body HTTP en el servidor**  
   El body del PUT es **binario puro** (`[12-byte nonce | ciphertext | 16-byte MAC]`).  
   Causas clásicas que producen exactamente este error:
    - Lectura parcial (Content-Length mal calculado o chunked encoding mal gestionado).
    - Uso de `std::string` / `std::getline` / buffers que asumen texto (cortan en `\0` o hacen reinterpret_cast).
    - Algún middleware o handler de etcd-server que hace base64, UTF-8 sanitization, o trimming invisible.
    - Buffer overflow/underflow en el handler HTTP antes de llamar a `decrypt_data`.

   Esto explica perfectamente por qué `/register` (sin cifrado) funciona y el PUT cifrado no.

4. **Skew de librerías compartidas en ml-detector**  
   Aunque `ldconfig`, symlinks y fecha de `libcrypto_transport.so.1.0.0` estén correctos, **ml-detector** (que usa `libetcd_client.so`) puede estar cargando una versión antigua de la librería vía:
    - `LD_LIBRARY_PATH` diferente,
    - `rpath` embebido en el binario,
    - `dlopen()` con ruta absoluta antigua,
    - o incluso otra copia de `libetcd_client.so` en `/usr/local/lib` o en el directorio del componente.

   Ejecuta en ambos procesos (mientras están corriendo):
   ```bash
   cat /proc/<pid_ml-detector>/maps | grep -E 'crypto_transport|etcd_client'
   cat /proc/<pid_etcd-server>/maps | grep -E 'crypto_transport|etcd_client'
   ```
   y compara las rutas y direcciones de memoria.

5. **Diferencia sutil en la construcción del nonce o en el framing**  
   Aunque el nonce se envía en claro (bytes 0-11), cualquier off-by-one en:
    - colocación del contador de 64 bits (bytes 4-11),
    - endianness al escribir/leer el contador,
    - o si el código de `encrypt`/`decrypt` asume distinto padding/framing,
      hace que el nonce usado en Poly1305 sea diferente → MAC fail.

6. **Diferencia microscópica en HKDF (aunque improbable)**
    - Context string con/ sin null-terminator o longitud diferente.
    - Salt vacío vs salt implícito.
    - Uso de `crypto_kdf_derive_from_key` vs implementación manual de HKDF-SHA256.

### Pasos de depuración inmediatos (recomendados en este orden)

1. **En el servidor**, justo antes de llamar a `decrypt_data`:
    - Haz `hex dump` completo del body recibido (longitud exacta también).
    - Loggea `session_key` (o mejor, SHA-256 del session_key) después de HKDF en **ambos** procesos. Deben ser idénticos.

2. Confirma el orden exacto de compresión/descompresión y si AAD se está usando (mira la implementación real de `CryptoTransport::encrypt`/`decrypt` en la versión cargada).

3. Ejecuta los `maps` de las librerías compartidas en ambos PIDs.

4. Desactiva temporalmente LZ4 en el cliente (si tienes flag) y vuelve a probar. Si entonces funciona → era el orden de compresión.

5. Añade un `test_integ_end_to_end` completo (cliente real → servidor real) con logging de todo el blob cifrado.

Con cualquiera de estos tres primeros checks deberías ver la discrepancia inmediatamente.

¿Quieres que te preparemos los comandos exactos de gdb/valgrind/strace o un patch mínimo de logging para insertar en `CryptoTransport` y en el handler del PUT? Dinos y te lo damos listo para copiar-pegar. ¡Estamos para ayudar!