Evaluación directa del DAY 109. El sistema está entrando en una fase de **endurecimiento real**; los cambios van en la dirección correcta. Respuestas y ajustes recomendados:

---

# Q1 — D8-light READ-ONLY

**El contrato es válido, pero no es suficientemente explícito.**

Inferir READ-ONLY con:

```cpp
payload == nullptr && payload_len == 0
```

funciona, pero es **frágil a futuro**:

* ambigüedad semántica (¿payload vacío vs modo especial?)
* fácil de romper al extender el API
* obliga a lógica implícita en múltiples sitios

**Recomendación (obligatoria antes de escalar plugins):**

Introducir flag explícito en el API:

```cpp
typedef enum {
    PLUGIN_MODE_NORMAL = 0,
    PLUGIN_MODE_READONLY = 1
} PluginMode;

typedef struct MessageContext {
    ...
    uint8_t mode;  // nuevo campo
    ...
} MessageContext;
```

Y en loader:

```cpp
const bool is_readonly = (ctx.mode == PLUGIN_MODE_READONLY);
```

**Ventaja clave:**

> conviertes un contrato implícito en contrato verificable

---

## Riesgo detectado (importante)

Aunque el payload sea `nullptr`, el plugin aún puede:

* modificar `result_code` arbitrariamente
* intentar mutar otros campos (ya detectado por D8)

Esto es aceptable, pero implica:

👉 el plugin sigue siendo **punto de decisión crítico**

No es solo “observador”.

---

# Q2 — PHASE 2c (sniffer)

**Recomendación clara: payload REAL, pero READ-ONLY estricto.**

No usar `nullptr` aquí. Sería perder información clave.

---

## Contrato correcto para sniffer

```text
payload: presente (bytes del paquete)
mode: PLUGIN_MODE_NORMAL
mutabilidad: prohibida
```

---

## Reglas necesarias

1. **Payload inmutable**

    * ya cubierto parcialmente por D8
    * mantener CRC / snapshot

2. **Límite de tamaño**

```cpp
if (ctx.payload_len > MAX_PLUGIN_PAYLOAD_SIZE) {
    // truncar o rechazar
}
```

3. **No exponer PII directamente (si aplica)**

    * opcional: masking parcial (futuro)

---

## Decisión final

| Componente   | Payload | Mode                        |
| ------------ | ------- | --------------------------- |
| rag-ingester | ❌ no    | READONLY                    |
| sniffer      | ✅ sí    | NORMAL (read-only enforced) |

---

# Q3 — §4 Integration Philosophy (raw TCP)

**La decisión es correcta, pero la justificación actual es insuficiente para paper académico.**

Ahora mismo:

> “resource footprint”

No basta
