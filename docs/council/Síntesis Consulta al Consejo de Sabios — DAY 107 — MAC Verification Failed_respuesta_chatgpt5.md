El diagnóstico es sólido y el post-mortem está bien cerrado. El patrón “datos válidos pero no cifrados → MAC fail” es clásico, y el hexdump fue la prueba definitiva. Paso a responder las tres preguntas y a señalar lo importante para no repetir este fallo.

---

# Q1 — Swap de CTX en `etcd-server`

**Respuesta:**
Sí, debes **verificarlo de forma aislada**. Ahora mismo tienes dos cambios acoplados y eso es peligroso.

### Modelo correcto esperado

Si el cliente hace:

```text
client.tx (CTX_TX) → server.rx (CTX_TX)
server.tx (CTX_RX) → client.rx (CTX_RX)
```

Entonces el servidor debe tener:

```cpp
rx_ = CTX_ETCD_TX;
tx_ = CTX_ETCD_RX;
```

Esto es lo que has dejado tras el swap, y **es correcto arquitectónicamente**.

---

### Qué hacer ahora (importante)

Haz un test controlado:

1. Mantén el fix de `component_config_path`
2. Revierte el swap de CTX
3. Prueba

**Resultado esperado:**

* Si falla → el swap era necesario
* Si funciona → había doble error (raro pero posible)

---

### Veredicto

👉 Mi hipótesis:
El swap **sí era necesario**, pero quedó oculto por el bug de cifrado desactivado.

---

# Q2 — Doble path de carga de seed (sniffer vs resto)

**Respuesta:**
No es correcto. Es una deuda técnica que debes eliminar.

---

### Problema real

Ahora tienes dos modelos:

| Componente             | Cómo obtiene seed         |
| ---------------------- | ------------------------- |
| ml-detector / firewall | `SeedClient`              |
| sniffer                | lectura manual `seed.bin` |

Esto rompe:

* consistencia
* auditabilidad
* invariantes del sistema

---

### Riesgo concreto

* drift de comportamiento
* bugs difíciles de rastrear (como el que acabas de vivir)
* bypass accidental de validaciones del `SeedClient`

---

### Decisión correcta

👉 **Unificar en `SeedClient` para TODOS los componentes**

El sniffer debe:

* usar `SeedClient`
* eliminar `get_encryption_seed()` manual

---

### Regla de arquitectura

> “El acceso al seed es un *concern centralizado*, no un detalle de implementación por componente”

---

# Q3 — Permisos `seed.bin` (0600 vs 640)

**Respuesta corta:**
Mantén **0600 root:root** y adapta el runtime. No relajes el contrato.

---

### Por qué 640 es mala idea

Con `640 root:vagrant`:

* cualquier proceso del grupo puede leer el seed
* amplías superficie de ataque lateral

En tu threat model (hospitales, etc.):

👉 **el seed es material criptográfico crítico**

---

### Opciones correctas

### Opción A (recomendada)

```text
0600 root:root
```

y ejecutar los servicios como root o con capability controlada.

---

### Opción B (más avanzada)

* mantener 0600
* usar:

    * `systemd` + `ReadOnlyPaths`
    * o `CapabilityBoundingSet`
    * o un helper con privilegios mínimos

---

### Qué NO hacer

* No permitir 640 como “válido”
* No adaptar `SeedClient` para aceptar permisos laxos

---

### Veredicto

👉 El warning de `SeedClient` es correcto.
👉 El sistema debe adaptarse al contrato, no al revés.

---

# Problema más importante (fuera de las preguntas)

## Estado de `provision.sh` — riesgo crítico

Lo que describes aquí es el verdadero problema ahora:

> “Si haces destroy/up, todo rompe”

Esto es **inaceptable en un sistema de seguridad**.

---

## Qué debe hacer `provision.sh` (obligatorio)

Debe convertirse en **fuente de verdad del entorno**.

### Mínimo necesario:

### 1. Seeds sincronizados (o modelo explícito)

Ahora mismo:

```text
❌ genera seeds distintos por componente
```

Pero tu sistema requiere:

```text
✔ mismo seed para todos los componentes (modelo actual)
```

---

### 2. Permisos correctos

```bash
chmod 700 /etc/ml-defender/<component>
chmod 600 seed.bin
chown root:root
```

---

### 3. JSON configs

* crear symlinks o copiar configs
* validar existencia

---

### 4. Verificación de librerías

* comprobar versión de `libcrypto_transport`
* comprobar libsodium correcta

---

### 5. Validación post-provision

Script debe fallar si:

* seeds no coinciden
* permisos incorrectos
* paths inválidos

---

## Recomendación fuerte

Añadir modo:

```bash
provision.sh --verify
```

Que haga:

* checksum de seeds
* permisos
* existencia de configs
* sanity check de carga

---

# Insight clave del incidente

Este bug no era criptográfico. Era:

> **Un fallo silencioso de configuración que degradó seguridad sin fallar el sistema**

Esto es más peligroso que un crash.

---

## Acción recomendada (muy importante)

Añadir invariant en runtime:

```cpp
if (encryption_enabled && !tx_) {
    LOG_CRITICAL("Encryption enabled but CryptoTransport not initialized");
    std::terminate();
}
```

Esto habría detectado el problema en segundos.

---

# Veredicto final del Consejo

* El sistema de cifrado funciona correctamente
* El bug era de inicialización/configuración
* Hay deuda en:

    * unificación de seed access
    * provisioning reproducible
    * fail-fast en invariantes críticas

---

Si corriges `provision.sh` + añades ese invariant, eliminas una clase entera de fallos silenciosos en el sistema.
