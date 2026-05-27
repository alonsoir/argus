# ADR-012: Plugin Loader Architecture

**Estado:** PROPOSED  
**Fecha:** 2026-03-19 (DAY 88) — actualizado DAY 91  
**Autor:** Alonso + Consejo de Sabios  
**Componente:** `libs/plugin-loader` (nueva shared library interna)

---

## Contexto

ML Defender tiene un pipeline de 6 componentes con rendimiento validado en entornos
resource-constrained (hospitales, escuelas, pymes). El roadmap contempla nuevas
capacidades: JA4 fingerprinting (FEAT-TLS-1), DNS/DGA detection (FEAT-NET-1),
HTTP payload inspection (FEAT-WAF-1), y otras futuras.

Añadir estas features directamente al core de cada componente comprometería:

- **Rendimiento base** — organizaciones con hardware limitado no deben pagar el coste
  de features que no necesitan
- **Mantenibilidad** — el core se volvería monolítico e impredecible
- **Extensibilidad** — terceros no pueden contribuir features sin tocar el core

El patrón ya establecido en el proyecto con `crypto-transport` como shared library
interna demuestra que la extracción de responsabilidades funciona bien en esta base
de código.

---

## Línea divisoria: core open source vs plugin

Esta distinción es **arquitectónicamente crítica** y debe respetarse en cualquier
decisión de implementación presente o futura.

### Core open source — estadísticas universales de flujo TCP/IP

Pertenecen al core **todas las features que son estadísticas observables universalmente
en cualquier flujo de red**, independientemente de la familia de amenaza:

| Feature | Razón |
|---|---|
| `rst_ratio` | Ratio TCP RST/SYN — observable en cualquier flujo |
| `syn_ack_ratio` | Ratio handshakes completados — ídem |
| `flow_duration_min` | Duración mínima de flujos — ídem |
| `dst_port_445_ratio` | Proporción de tráfico a un puerto — ídem |
| `port_diversity_ratio` | Diversidad de puertos destino — ídem |
| `connection_rate` | Tasa de conexiones por segundo — ídem |
| `unique_dst_ips_count` | Cardinalidad de IPs destino — ídem |

> **Principio:** El Random Forest embebido no detecta "WannaCry". Detecta
> **escaneo TCP masivo con handshakes fallidos** — una clase de comportamiento.
> Que WannaCry, NotPetya, u otro worm produzcan ese comportamiento es una
> consecuencia, no el objeto de detección. Esto hace el sistema más robusto
> (generaliza a variantes desconocidas) y más honesto científicamente.
>
> Meterlas en un plugin sería añadir complejidad sin ningún beneficio —
> equivale a tratar `packet_rate` como un plugin porque los DDoS son rápidos.

### Plugin — conocimiento específico de amenaza

Son candidatos a plugin **la lógica que depende de conocimiento específico de una
familia o campaña concreta y que puede quedar obsoleta**:

| Candidato a plugin | Razón |
|---|---|
| Modelos especializados por familia (SMB-RF, DNS-RF...) | Entrenados con datos propietarios; se actualizan sin recompilar |
| Threat intelligence feeds con IOCs (FEAT-NET-2) | Listas de IPs/dominios maliciosos que cambian continuamente |
| Reglas de correlación multi-evento | Firmas compuestas específicas de campaña |
| JA4 TLS fingerprinting (FEAT-TLS-1) | Requiere DPI — fuera del hot path genérico |
| HTTP payload inspection (FEAT-WAF-1) | Ídem |
| DNS/DGA detection (FEAT-NET-1) | Requiere análisis de nombres de dominio — DPI |

> **Regla práctica:** Si una feature puede quedar obsoleta cuando el atacante
> cambia su TTPs, es un plugin. Si seguirá siendo válida en 10 años para cualquier
> ataque de escaneo masivo, es core.

---

## Decisión

Implementar un mecanismo unificado de plugins como **shared library interna**
`libs/plugin-loader`, siguiendo el mismo patrón que `libs/crypto-transport`.

Cualquier componente que quiera soporte de plugins añade una línea en su
`CMakeLists.txt` y una sección `plugins` en su JSON de configuración. El
mecanismo de carga, ciclo de vida, y control de rendimiento son responsabilidad
exclusiva del loader — el componente host no reimplementa nada.

---

## Estructura del proyecto

```
libs/
    crypto-transport/          ← existente
    plugin-loader/             ← nuevo
        include/
            plugin_api.h       ← contrato C puro (ABI estable)
            plugin_loader.hpp  ← interfaz C++ del loader
        src/
            plugin_loader.cpp
        CMakeLists.txt
```

---

## Contrato del plugin — `plugin_api.h`

API C pura para evitar ABI hell entre compilaciones de C++:

```c
#pragma once
#ifdef __cplusplus
extern "C" {
#endif

#define PLUGIN_API_VERSION 1

typedef struct PluginConfig {
    const char* name;
    const char* config_json;  // sección JSON del plugin, ya parseada como string
} PluginConfig;

typedef struct PacketContext {
    /* Read-only: datos del paquete */
    const uint8_t* raw_bytes;
    size_t         length;
    uint32_t       src_ip;
    uint32_t       dst_ip;
    uint16_t       src_port;
    uint16_t       dst_port;
    uint8_t        protocol;

    /* Write: el plugin puede enriquecer features y emitir alertas */
    void*          features;     /* puntero opaco a FlowFeatures del componente host */
    void*          alert_queue;  /* puntero opaco a AlertQueue del componente host */
    int            threat_hint;  /* 0=benign, 1=suspicious, 2=malicious */
} PacketContext;

typedef enum {
    PLUGIN_OK    = 0,
    PLUGIN_ERROR = 1,
    PLUGIN_SKIP  = 2   /* plugin decide no procesar este paquete */
} PluginResult;

/* Símbolos que todo plugin DEBE exportar */
const char*  plugin_name();
const char*  plugin_version();
int          plugin_api_version();   /* debe retornar PLUGIN_API_VERSION */
PluginResult plugin_init(const PluginConfig* config);
PluginResult plugin_process_packet(PacketContext* ctx);
void         plugin_shutdown();

#ifdef __cplusplus
}
#endif
```

---

## Interfaz del loader — `plugin_loader.hpp`

```cpp
#pragma once
#include <string>
#include <vector>
#include <memory>
#include "plugin_api.h"

struct PluginStats {
    std::string name;
    uint64_t    invocations   = 0;
    uint64_t    budget_overruns = 0;
    uint64_t    errors        = 0;
};

class PluginLoader {
public:
    explicit PluginLoader(const std::string& config_json_path);

    /* Carga todos los plugins habilitados en el JSON.
       Llama a plugin_init() en cada uno. */
    void load_plugins();

    /* Invoca plugin_process_packet() en todos los plugins cargados.
       Mide latencia. Si supera budget_us, incrementa overrun counter. */
    void invoke_all(PacketContext& ctx);

    /* Llama a plugin_shutdown() y hace dlclose en todos. */
    void shutdown();

    const std::vector<PluginStats>& stats() const;

private:
    struct LoadedPlugin;
    std::vector<std::shared_ptr<LoadedPlugin>> plugins_;
    std::vector<PluginStats> stats_;
    std::string config_path_;
    uint32_t budget_us_ = 100; /* default: 100 microsegundos por plugin */
};
```

---

## Configuración JSON (sección estándar)

Cada componente que use el loader añade esta sección a su JSON:

```json
{
  "plugins": {
    "directory": "/usr/lib/ml-defender/plugins",
    "budget_us": 100,
    "enabled": ["hello", "ja4"],
    "hello": {},
    "ja4": {
      "blacklist_path": "/etc/ml-defender/ja4_blacklist.txt",
      "slow_path_features": true
    }
  }
}
```

- Si `plugins.enabled` está vacío o ausente, no se carga ningún plugin.
- Si un `.so` listado en `enabled` no existe en `directory`, se loguea warning y se continúa — **nunca se aborta el arranque del componente**.
- Si `plugin_api_version()` del `.so` no coincide con `PLUGIN_API_VERSION`, se rechaza con warning.

---

## Integración en un componente existente (ejemplo: sniffer)

**CMakeLists.txt:**
```cmake
target_link_libraries(sniffer PRIVATE plugin-loader crypto-transport)
```

**Código del sniffer (mínimo cambio):**
```cpp
#include "plugin_loader.hpp"

// En inicialización:
PluginLoader plugin_loader_("config/sniffer.json");
plugin_loader_.load_plugins();

// En el packet handler, después del fast path:
PacketContext ctx{};
ctx.raw_bytes  = packet_data;
ctx.length     = packet_len;
ctx.src_ip     = flow.src_ip;
// ...
plugin_loader_.invoke_all(ctx);

// En shutdown:
plugin_loader_.shutdown();
```

---

## Plugin Hello World — validación del mecanismo

El primer plugin a implementar es `libplugin_hello.so`. No tiene lógica de seguridad.
Su único propósito es validar el contrato end-to-end:

```cpp
// plugins/hello/hello_plugin.cpp
#include "plugin_api.h"
#include <spdlog/spdlog.h>

extern "C" {

const char* plugin_name()        { return "hello"; }
const char* plugin_version()     { return "0.1.0"; }
int         plugin_api_version() { return PLUGIN_API_VERSION; }

PluginResult plugin_init(const PluginConfig* config) {
    spdlog::info("[plugin:hello] init OK — config: {}", config->config_json);
    return PLUGIN_OK;
}

PluginResult plugin_process_packet(PacketContext* ctx) {
    spdlog::debug("[plugin:hello] paquete recibido src={}:{} dst={}:{}",
        ctx->src_ip, ctx->src_port, ctx->dst_ip, ctx->dst_port);
    return PLUGIN_OK;
}

void plugin_shutdown() {
    spdlog::info("[plugin:hello] shutdown OK");
}

} // extern "C"
```

**Criterios de éxito del hello world:**
- [ ] `dlopen` / `dlsym` funcionan correctamente
- [ ] `plugin_init()` recibe la config JSON parseada
- [ ] `plugin_process_packet()` se invoca en cada paquete
- [ ] `plugin_shutdown()` se llama limpiamente al cerrar el sniffer
- [ ] Si se elimina el `.so`, el sniffer arranca sin errores
- [ ] Si `budget_us` se excede, aparece warning en el log

---

## Control de rendimiento

```cpp
// Dentro de PluginLoader::invoke_all()
auto t0 = std::chrono::steady_clock::now();
plugin->process_packet(ctx);
auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(
    std::chrono::steady_clock::now() - t0).count();

stats_[i].invocations++;
if (elapsed_us > budget_us_) {
    stats_[i].budget_overruns++;
    spdlog::warn("[plugin-loader] plugin '{}' overrun: {}us > {}us budget",
        plugin->name(), elapsed_us, budget_us_);
}
```

Los stats son accesibles para el componente host, que puede exponerlos
vía HTTP health endpoint o loguearlos periódicamente.

---

## Plugins que usarán este mecanismo (roadmap)

> **Nota:** `rst_ratio`, `syn_ack_ratio`, `flow_duration_min` y otras estadísticas
> de flujo TCP/IP **no son plugins** — pertenecen al core open source. Ver sección
> "Línea divisoria" más arriba.

| Plugin | Feature | Componente host | Prioridad |
|--------|---------|----------------|-----------|
| `libplugin_hello` | Validación mecanismo | sniffer | P0 — primero |
| `libplugin_ja4` | JA4 TLS fingerprinting | sniffer | P1 |
| `libplugin_dns_dga` | DNS/DGA detection | sniffer | P1 |
| `libplugin_http_inspect` | HTTP payload WAF | sniffer | P2 |
| `libplugin_threat_intel` | Threat intelligence feeds (FEAT-NET-2) | ml-detector | P2 |
| `libplugin_smb_specialist` | Modelo RF especializado SMB (enterprise) | ml-detector | P3 |
| `libplugin_ebpf_tls` | eBPF uprobes OpenSSL | sniffer | P3 |

---

## Consecuencias

**Positivas:**
- El core de cada componente no crece con cada nueva feature
- Organizaciones resource-constrained solo cargan lo que necesitan
- Terceros pueden contribuir plugins sin tocar el core
- Rendimiento base siempre predecible y medible
- Extensible a cualquier componente del pipeline con mínimo esfuerzo
- La línea divisoria core/plugin protege la integridad científica del paper:
  el sistema detecta clases de comportamiento, no firmas de malware concreto

**Negativas / riesgos:**
- Un plugin mal escrito puede causar crash del proceso host (mitigado parcialmente
  con el budget monitor; mitigación completa requeriría sandbox de proceso separado,
  fuera de alcance por ahora)
- El `PacketContext` con punteros opacos requiere disciplina — el plugin no debe
  castear `features` sin conocer la versión del host

---

## Alternativas consideradas

- **Feature flags en el core**: descartado — el core crece indefinidamente y el
  rendimiento base se vuelve impredecible
- **Procesos separados con IPC**: descartado — latencia inaceptable en el hot path
- **eBPF programs dinámicos**: interesante a largo plazo pero complejidad muy alta;
  reservado para FEAT-EDR-1
- **Detección por familia como plugin** (e.g., `libplugin_wannacry`): descartado —
  `rst_ratio` y `syn_ack_ratio` son estadísticas universales de flujo TCP, no
  firmas de WannaCry. Ver sección "Línea divisoria".

---

## Referencias

- `libs/crypto-transport` — patrón de shared library interna ya establecido
- FEAT-TLS-1: JA4 TLS Fingerprinting (primer plugin real, post-ADR-012)
- FEAT-NET-1: DNS/DGA Detection
- FEAT-NET-2: Threat Intelligence Feeds
- FEAT-WAF-1: HTTP Payload Inspection
- `docs/design/synthetic_data_wannacry_spec.md` — spec de datos sintéticos SMB
- Conversación de diseño: sesión DAY 87-88 (2026-03-18/19), actualizado DAY 91