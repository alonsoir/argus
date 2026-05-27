# Comandos del rag-security

> **Fuente canónica:** `rag/config/command_whitelist.json`
> **Componente:** `rag-security` (puerto HTTP `8080`, protocolo ZMQ cifrado)
> **Última revisión:** DAY 92 — 20 marzo 2026

---

## Índice

1. [Arquitectura de seguridad](#arquitectura-de-seguridad)
2. [Comandos permitidos](#comandos-permitidos)
3. [Patrones permitidos](#patrones-permitidos)
4. [Claves restringidas](#claves-restringidas)
5. [Límites y validación](#límites-y-validación)
6. [Referencia de comandos](#referencia-de-comandos)
7. [Ejemplos de uso](#ejemplos-de-uso)
8. [Añadir nuevos comandos](#añadir-nuevos-comandos)

---

## Arquitectura de seguridad

El rag-security implementa un **whitelist estricto** — solo se ejecutan comandos explícitamente autorizados.

```
Cliente → [ZMQ cifrado AES-256-CBC + lz4] → rag-security
                                                 │
                                                 ▼
                                     command_whitelist.json
                                                 │
                                    ┌────────────┴────────────┐
                                    │  ¿comando en whitelist?  │
                                    └────────────┬────────────┘
                                         Sí ▼       No ▼
                                       Ejecutar    REJECT (403)
```

**Parámetros de seguridad:**

| Parámetro | Valor |
|---|---|
| `security_level` | 3 (máximo) |
| `whitelist_commands` | `true` |
| `requires_encryption` | `true` |
| `max_query_length` | 1000 caracteres |

---

## Comandos permitidos

Lista completa de comandos autorizados en `allowed_commands`:

| Comando | Categoría | Descripción |
|---|---|---|
| `status` | Sistema | Estado general del componente rag-security |
| `validate` | Validación | Validar configuración o integridad del sistema |
| `encryption_test` | Seguridad | Verificar que el cifrado funciona correctamente |
| `pipeline_status` | Pipeline | Estado de todos los componentes del pipeline |
| `start_component` | Gestión | Iniciar un componente del pipeline |
| `stop_component` | Gestión | Detener un componente del pipeline |
| `get_config` | Configuración | Obtener configuración actual de un componente |
| `update_config` | Configuración | Actualizar configuración de un componente |
| `show_rag_config` | RAG | Mostrar configuración actual del sistema RAG |
| `set_rag_setting` | RAG | Modificar un parámetro del sistema RAG |
| `get_rag_capabilities` | RAG | Listar capacidades disponibles del sistema RAG |

---

## Patrones permitidos

El whitelist también acepta comandos que coincidan con estos patrones regex:

| Patrón | Comandos que acepta |
|---|---|
| `^status.*` | `status`, `status_detail`, `status_ml`, etc. |
| `^validate.*` | `validate`, `validate_config`, `validate_proto`, etc. |
| `^encryption.*` | `encryption_test`, `encryption_status`, etc. |
| `^pipeline.*` | `pipeline_status`, `pipeline_health`, `pipeline_restart`, etc. |
| `^start.*` | `start_component`, `start_sniffer`, `start_detector`, etc. |
| `^stop.*` | `stop_component`, `stop_sniffer`, etc. |
| `^config.*` | `config_reload`, `config_validate`, etc. |
| `^show.*` | `show_rag_config`, `show_logs`, `show_metrics`, etc. |
| `^set.*` | `set_rag_setting`, `set_log_level`, etc. |
| `^get.*` | `get_config`, `get_rag_capabilities`, `get_metrics`, etc. |

> **Nota:** Los patrones son evaluados **después** de la lista `allowed_commands`. Un comando es válido si aparece en la lista explícita **o** coincide con algún patrón.

---

## Claves restringidas

Las siguientes claves **nunca** deben aparecer en los parámetros de un comando. Su presencia provoca rechazo inmediato:

| Clave restringida | Razón |
|---|---|
| `password` | Credenciales de acceso |
| `secret` | Secretos de configuración |
| `private_key` | Clave privada criptográfica |
| `encryption_seed` | Seed ChaCha20 — dato crítico de seguridad |

Estas claves están protegidas independientemente del comando que se use.

---

## Límites y validación

| Parámetro | Límite | Comportamiento al exceder |
|---|---|---|
| `max_query_length` | 1000 caracteres | REJECT |
| Claves restringidas | Lista fija | REJECT inmediato |
| Cifrado | Requerido | Sin cifrado → conexión rechazada |

---

## Referencia de comandos

### `status`

Devuelve el estado operacional del rag-security.

```json
{
  "command": "status"
}
```

Respuesta esperada: estado del servidor LLM (TinyLlama), índices FAISS cargados, conexión a etcd.

---

### `pipeline_status`

Devuelve el estado de todos los componentes registrados en etcd.

```json
{
  "command": "pipeline_status"
}
```

Respuesta esperada: lista de componentes con su estado (`ACTIVE`, `ERROR`, `STARTING`, etc.) y último heartbeat.

---

### `start_component` / `stop_component`

Inicia o detiene un componente del pipeline.

```json
{
  "command": "start_component",
  "component": "sniffer"
}
```

```json
{
  "command": "stop_component",
  "component": "ml-detector"
}
```

Componentes válidos: `sniffer`, `ml-detector`, `firewall-acl-agent`, `rag-ingester`, `rag-security`, `etcd-server`.

---

### `get_config` / `update_config`

Obtiene o actualiza la configuración de un componente.

```json
{
  "command": "get_config",
  "component": "sniffer"
}
```

```json
{
  "command": "update_config",
  "component": "sniffer",
  "key": "fast_detector.enabled",
  "value": true
}
```

> **Restricción:** No se pueden modificar claves en `restricted_keys`.

---

### `validate` / `encryption_test`

```json
{
  "command": "validate",
  "target": "proto_schema"
}
```

```json
{
  "command": "encryption_test"
}
```

`encryption_test` verifica el cifrado AES-256-CBC extremo a extremo.

---

### `show_rag_config`

Devuelve la configuración activa del sistema RAG (modelo LLM, dimensiones FAISS, nivel de seguridad).

```json
{
  "command": "show_rag_config"
}
```

---

### `set_rag_setting`

Modifica un parámetro del sistema RAG en runtime.

```json
{
  "command": "set_rag_setting",
  "key": "log_level",
  "value": "debug"
}
```

---

### `get_rag_capabilities`

Lista las capacidades habilitadas en esta instancia:

```json
{
  "command": "get_rag_capabilities"
}
```

Respuesta esperada:
```json
{
  "capabilities": [
    "component_management",
    "config_validation",
    "pipeline_control",
    "embedder_system",
    "faiss_search"
  ]
}
```

---

## Ejemplos de uso

### Consulta de estado completa del pipeline

```bash
# Via ZMQ (requiere cliente con cifrado AES-256-CBC + lz4)
zmq_client --host localhost --port 8080 \
  --command '{"command": "pipeline_status"}'
```

### Verificación de cifrado tras cambio de keys

```bash
zmq_client --host localhost --port 8080 \
  --command '{"command": "encryption_test"}'
```

### Consulta RAG de seguridad (análisis de amenaza)

Las consultas de análisis de amenazas se envían como queries en lenguaje natural al modelo TinyLlama. El sistema recupera contexto relevante de los índices FAISS antes de generar la respuesta.

```json
{
  "command": "get_rag_capabilities",
  "query": "show threat analysis for suspicious SMB traffic"
}
```

---

## Añadir nuevos comandos

Para añadir un nuevo comando al whitelist:

1. Editar `rag/config/command_whitelist.json`
2. Añadir el comando exacto a `allowed_commands` **o** un patrón regex a `allowed_patterns`
3. Si el comando accede a datos sensibles, verificar que no use ninguna clave de `restricted_keys`
4. Reiniciar rag-security para que cargue la nueva configuración

```json
{
  "allowed_commands": [
    "...",
    "nuevo_comando"
  ]
}
```

> No se requiere recompilación. El whitelist se carga desde JSON en cada arranque.

---

## Mapa de capacidades vs comandos

| Capacidad | Comandos relacionados |
|---|---|
| `component_management` | `start_component`, `stop_component` |
| `config_validation` | `validate`, `get_config`, `update_config` |
| `pipeline_control` | `pipeline_status`, `start_component`, `stop_component` |
| `embedder_system` | `show_rag_config`, `set_rag_setting` |
| `faiss_search` | Consultas de análisis RAG (lenguaje natural) |

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*DAY 92 — 20 marzo 2026*