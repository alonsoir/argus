El síntoma que describes (MAC fail con todo lo “obvio” ya verificado) apunta casi seguro a **divergencia en *inputs efectivos* de AEAD**, no en la primitiva en sí. Te dejo hipótesis **ordenadas por probabilidad real en este tipo de sistemas** y cómo validarlas rápido.

---

# 1) **Nonce divergence (la más probable)**

Aunque uses contador, hay varios fallos típicos:

### Posibles fallos

* Contador no inicializado igual en cliente/servidor
* Endianness distinto al escribir bytes 4–11
* Reutilización o salto de nonce en uno de los lados
* Uso de **instancias distintas de `CryptoTransport`** con contadores independientes

### Señal clara

* Todo parece correcto, pero MAC falla siempre

### Prueba inmediata

Loggear (en ambos lados, mismo request):

```text
nonce (hex)
session_key (hash, no la key)
ciphertext_len
```

Si el nonce no coincide → ya tienes la causa.

---

# 2) **AAD implícito inconsistente**

ChaCha20-Poly1305 permite AAD. Aunque creas que no lo usas:

### Posible problema

* Uno de los lados pasa `aad=nullptr, len=0`
* El otro pasa algo (ej: headers, metadata, length)

### Señal

MAC fail con todo lo demás correcto

### Prueba

Revisar llamada exacta a:

```c
crypto_aead_chacha20poly1305_ietf_encrypt(...)
crypto_aead_chacha20poly1305_ietf_decrypt(...)
```

Asegurarte de:

```text
aad == nullptr
aad_len == 0
```

en ambos lados.

---

# 3) **Orden compresión ↔ cifrado incorrecto (muy sospechoso en tu caso)**

Has mencionado LZ4 → esto es **candidato fuerte**.

### Orden correcto

```text
cliente: compress → encrypt
servidor: decrypt → decompress
```

### Error típico

```text
servidor: decompress → decrypt ❌
```

o:

* cliente comprime pero servidor no espera compresión

### Señal

MAC fail siempre (porque ciphertext no es el esperado)

### Prueba rápida

* Desactivar compresión en cliente → probar
* O loggear primer byte del plaintext tras decrypt

---

# 4) **Key derivation mismatch sutil (HKDF)**

Aunque context strings coincidan, hay más variables:

### Posibles divergencias

* Salt distinto (aunque no lo creas)
* Info/context con terminador `\0` en un lado y sin él en otro
* Longitud del context distinta (`strlen` vs `sizeof`)
* Uso de HKDF expand con longitud distinta

### Señal

* Keys “parecen” iguales pero no lo son realmente

### Prueba

Loggear:

```text
HKDF input key (hash)
HKDF salt (hex)
HKDF info/context (hex + length)
Derived key (hash)
```

---

# 5) **Truncamiento / framing del mensaje**

### Posible problema

El mensaje que llega al servidor no es exactamente:

```
[nonce | ciphertext | tag]
```

Ejemplos:

* pérdida de bytes en HTTP layer
* parsing incorrecto (ej: JSON vs binario)
* lectura parcial

### Señal

* `ciphertext_len` distinto entre cliente y servidor

### Prueba

Loggear:

```text
total_message_len
nonce_len
ciphertext_len
tag_len
```

---

# 6) **Confusión de buffers (muy común en C++)**

### Posible bug

* buffer reutilizado
* overwrite antes de decrypt
* lifetime incorrecto (vector resize, etc.)

### Señal

* MAC fail intermitente o constante

### Prueba

* Copiar buffer a uno nuevo antes de decrypt
* Comparar hashes antes/después

---

# 7) **Múltiples instancias de CryptoTransport**

### Problema

* Cada instancia tiene su propio contador de nonce
* Cliente usa una instancia, servidor otra no sincronizada

### Señal

* Nonce mismatch aunque código “correcto”

### Prueba

Loggear dirección de instancia (`this`) + contador

---

# 8) **Encoding / transporte HTTP**

### Posible problema

* Binary → base64 → binary mal hecho
* UTF-8 / JSON escaping
* pérdida de bytes nulos (`\0`)

### Señal

* tamaño cambia en tránsito

### Prueba

* Enviar payload en raw (no JSON)
* Comparar hash antes de enviar y después de recibir

---

# 9) **Endian bug en contador nonce (muy típico)**

### Ejemplo

```cpp
// cliente
*(uint64_t*)(nonce+4) = counter;

// servidor interpreta distinto endian
```

### Prueba

Imprimir nonce byte a byte en ambos lados

---

# 10) **Key correcta pero contexto invertido en runtime (no en código)**

Aunque el código esté bien:

* ¿Seguro que `ml-detector` está usando ese binario?
* ¿Seguro que no hay config override?

### Prueba

Loggear en runtime:

```text
CTX usado (string + length)
```

---

# Estrategia de debug (orden óptimo)

Ejecuta esto en 10 minutos:

### Paso 1 — Dump completo en ambos lados

Para un único request:

```text
seed hash
context string + len
derived key hash
nonce (hex)
ciphertext length
tag (hex)
```

---

### Paso 2 — Comparar:

| Campo          | Debe coincidir |
| -------------- | -------------- |
| seed           | ✔              |
| context        | ✔              |
| key derivada   | ✔              |
| nonce          | ✔              |
| ciphertext len | ✔              |
| tag            | ✔              |

---

### Paso 3 — Resultado

* Si **nonce difiere** → bug en contador
* Si **key difiere** → bug HKDF
* Si **len difiere** → bug transporte
* Si todo coincide → AAD / orden compresión

---

# Mi apuesta (basada en experiencia)

Orden de probabilidad:

1. 🥇 **Nonce divergence / contador**
2. 🥈 **Orden compresión ↔ cifrado**
3. 🥉 **HKDF context length / null terminator**
4. 🎯 **Framing / transporte binario**

---

# Insight clave

Cuando:

* seed OK
* contexto OK
* libsodium OK

👉 El 90% de los casos es **nonce o framing**, no criptografía.

---

Si quieres, en el siguiente paso puedo ayudarte a construir un **trace determinista mínimo (cliente ↔ servidor)** que te diga en una sola ejecución exactamente dónde diverge.
