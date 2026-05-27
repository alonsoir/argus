# Consejo de Sabios — FEAT-PLUGIN-CRYPTO-1
## Consulta arquitectónica — 30 marzo 2026

---

## Contexto

DAY 102. ADR-012 PHASE 1b completada: el plugin-loader está activo en los
5 componentes del pipeline. El hello plugin valida el hot path. Tests: 25/25 ✅.

Durante el cierre del día surgió una pregunta sobre el camino natural de
PHASE 2: ¿cómo migrar el cifrado ChaCha20-Poly1305/HKDF del core de cada
componente a un plugin genérico `libplugin_crypto_transport.so`?

Esta consulta documenta el problema arquitectónico identificado y solicita
decisión del Consejo antes de iniciar el diseño formal (DAY 105+, post-arXiv).

---

## Estado actual del cifrado (PHASE 1)

El cifrado está **integrado directamente** en el core de cada componente:

```
main.cpp → CryptoTransport(config_path) → SeedClient → HKDF → ChaCha20-Poly1305
```

- `CryptoTransport` lee `component_id` del JSON → selecciona contexto HKDF
- Contextos canónicos en `contexts.hpp` (DAY 99):
  ```cpp
  CTX_SNIFFER_TO_ML  = "ml-defender:sniffer-to-ml-detector:v1"
  CTX_ML_TO_FIREWALL = "ml-defender:ml-detector-to-firewall:v1"
  // ... 6 canales, todos simétricos
  ```
- Opera en **capa de transporte ZMQ**: payload = protobuf + LZ4, antes del socket

---

## Objetivo de FEAT-PLUGIN-CRYPTO-1

Convertir `CryptoTransport` en un **plugin genérico configurable**:

```json
{
  "plugins": {
    "enabled": [
      {
        "name": "crypto_transport",
        "path": "/usr/lib/ml-defender/plugins/libplugin_crypto_transport.so",
        "active": true,
        "config": {
          "component_id": "sniffer",
          "direction": "tx"
        }
      }
    ]
  }
}
```

El plugin lee su identidad → selecciona contexto HKDF correcto →
gestiona cifrado/descifrado del mensaje de transporte.

**Ventajas:**
- Cifrado actualizable sin recompilar el componente host
- Testable de forma aislada
- Extensible a otros algoritmos (post-quantum, Noise) sin tocar el pipeline

---

## El problema arquitectónico central

### Hook actual — capa de red

```c
// plugin_api.h PHASE 1
PluginResult plugin_process_packet(PacketContext* ctx);
```

`PacketContext` contiene datos de **capa de red**:
```c
typedef struct PacketContext {
    const uint8_t* raw_bytes;  // bytes del paquete
    uint32_t       src_ip;
    uint32_t       dst_ip;
    uint16_t       src_port;
    uint16_t       dst_port;
    uint8_t        protocol;
    void*          features;       // opaco — FlowFeatures
    void*          alert_queue;    // opaco — cola de alertas
    int            threat_hint;
} PacketContext;
```

### Necesidad — capa de transporte

El cifrado opera sobre el **mensaje ZMQ serializado**:

```
[protobuf serializado] → [LZ4] → [ChaCha20-Poly1305] → [socket ZMQ]
```

No tiene src_ip, dst_port ni threat_hint. Necesita:
- Payload binario (bytes + longitud)
- Dirección (tx/rx)
- Posiblemente: nonce, tag de autenticación

---

## Las dos opciones en conflicto

### Opción A — Nuevo hook `plugin_process_message()` (API limpia)

```c
// MessageContext — nueva estructura para capa de transporte
typedef struct MessageContext {
    uint8_t*    payload;        // buffer in/out (cifrar o descifrar)
    size_t      length;         // longitud del payload
    size_t      max_length;     // capacidad máxima del buffer
    uint8_t     direction;      // 0=tx (cifrar), 1=rx (descifrar)
    uint8_t     nonce[12];      // nonce 96-bit (tx: generado; rx: leído del frame)
    uint8_t     tag[16];        // MAC tag Poly1305
    int         result_code;    // código de resultado del plugin
} MessageContext;

// Nuevo símbolo obligatorio en plugin_api.h PHASE 2
PluginResult plugin_process_message(MessageContext* ctx);
```

**Ventajas:**
- Semánticamente correcto — cada capa tiene su contexto
- API clara para futuros plugins de transporte (Noise, post-quantum)
- Separación limpia: plugins de red vs plugins de transporte

**Inconvenientes:**
- `PLUGIN_API_VERSION` debe incrementarse (breaking change)
- Todos los plugins existentes necesitan implementar el nuevo símbolo
  (o el loader lo marca como opcional con warning)
- Mayor complejidad en el loader (dispatch por tipo de hook)

---

### Opción B — Ampliar `PacketContext` con `serialized_payload` (no breaking)

```c
typedef struct PacketContext {
    // ... campos existentes sin cambio ...

    // NUEVO — PHASE 2: capa de transporte (nullable)
    uint8_t*    serialized_payload;  // NULL si no aplica
    size_t      serialized_length;
    uint8_t     msg_direction;       // 0=tx, 1=rx
} PacketContext;
```

El plugin crypto inspecciona `serialized_payload != NULL` para saber
si debe actuar como plugin de transporte.

**Ventajas:**
- No rompe `PLUGIN_API_VERSION` — los plugins existentes ignoran los nuevos campos
- El loader no necesita cambios
- Migración gradual sin gate de breaking change

**Inconvenientes:**
- Semánticamente impuro: `PacketContext` mezcla capa de red y de transporte
- `src_ip`, `dst_port`, `threat_hint` son irrelevantes para un plugin de cifrado
- Aumenta el acoplamiento entre capas — viola el principio de separación que
  motivó la arquitectura de plugins en primer lugar
- Dificulta el testing aislado del plugin de cifrado

---

## Preguntas al Consejo

### Q1 — Opción A vs Opción B

¿Cuál es la decisión correcta?

- **Opción A** (`MessageContext` nuevo): API limpia, breaking change explícito,
  mayor esfuerzo de migración
- **Opción B** (ampliar `PacketContext`): no breaking, migración gradual,
  pero semánticamente impuro

¿O existe una **Opción C** que no hemos considerado?

### Q2 — Gestión del breaking change (si Opción A)

Si se elige Opción A, ¿cómo gestionar la compatibilidad?

- ¿El nuevo símbolo `plugin_process_message` es **obligatorio** o **opcional**?
- Si opcional: el loader busca el símbolo con `dlsym` y lo ignora si no existe
  (sin incrementar `PLUGIN_API_VERSION`)
- Si obligatorio: `PLUGIN_API_VERSION = 2`, todos los plugins deben implementarlo

### Q3 — Estrategia de migración dual-mechanism

La propuesta es:

```
PHASE 2a: CryptoTransport directo (actual) + CryptoPlugin en paralelo
          Gate: TEST-INTEG-4 valida equivalencia cifrado/descifrado

PHASE 2b: CryptoTransport directo desactivado
          Gate: 72h sin regresiones en bare-metal

PHASE 2c: CryptoTransport eliminado del main.cpp
          Código limpio
```

¿Es correcta esta estrategia? ¿Hay riesgos no considerados en la
transición dual-mechanism?

---

## Restricciones del diseño (ADR-012, ADR-022)

- **ADR-012:** Plugins PHASE 1 = solo feature extraction. Decisión de bloqueo:
  NUNCA en un plugin. ¿Aplica esta restricción al plugin de cifrado?
  (El cifrado no decide bloquear — transforma el mensaje. Parece compatible.)
- **ADR-022:** Fail-closed. Si el plugin de cifrado falla, ¿el componente
  aborta (actual comportamiento de CryptoTransport) o continúa sin cifrar?
  Respuesta esperada: abortar — pero el Consejo debe confirmarlo.
- **PLUGIN_API_VERSION = 1** actualmente. Un bump a 2 requiere actualizar
  los 5 plugins existentes (actualmente solo `libplugin_hello.so`).

---

## Esta consulta es pre-diseño

No se solicita implementación todavía. Solo decisión arquitectónica para
que DAY 105+ arranque con el diseño validado por el Consejo.

La implementación es post-arXiv. El paper primero.

---

*Proyecto: ML Defender (aRGus NDR)*
*Rama: feature/bare-metal-arxiv*
*Tests: 25/25 ✅ · ADR-012 PHASE 1b: 5/5 COMPLETA*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*