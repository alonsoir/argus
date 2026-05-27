# ADR-017: Plugin Interface Hierarchy

**Estado:** ACEPTADO — implementación PHASE 2
**Fecha:** 2026-03-22 (DAY 94)
**Autor:** Alonso Isidoro Román + Claude (Anthropic)
**Revisado por:** Consejo de Sabios — unanimidad 6/6 modelos
**Componentes afectados:** plugin-loader, sniffer, ml-detector, rag-ingester
**Depende de:** ADR-012 (plugin-loader PHASE 1), ADR-013 (autenticación, DAY 95-96)
**Relacionado con:** ADR-003, ADR-008, ADR-010, ADR-014, ADR-015, ADR-016

---

## Principio rector — inamovible

> El core actual — modelos RF embebidos, Fast Detector, pipeline 6/6 — es
> **legacy estable. No se toca.** Todo crecimiento futuro entra por el sistema
> de plugins. La migración del core a plugins es decisión futura, no objetivo
> presente. **Strangler Fig Pattern.**

Este principio cierra el debate sobre si migrar los modelos RF existentes a
plugins (respuesta: no, ahora no). El sistema crece hacia adelante, no
involuciona para reorganizar lo que ya funciona.

---

## Contexto

ADR-012 (DAY 93) implementó el mecanismo de carga (`libplugin_loader.so`,
`dlopen`/`dlsym` lazy, ABI validada). Lo que no resolvió es el **contrato de
interfaces** — qué funciones expone cada familia de plugin, qué recibe, qué
devuelve, y cómo el loader verifica que un plugin es del tipo correcto.

El inventario de los ADR-001 a ADR-016 identificó cinco familias distintas de
extensión, con inputs y outputs cualitativamente diferentes. Un único
`PacketContext` sniffer-centric no sirve para todas ellas.

---

## Decisiones — unanimidad 6/6 del Consejo de Sabios

### Decisión 1 — Contextos tipados por familia (P1: Opción A)

Un contexto C por cada familia de componente host. Sin `void*` opaco.
El compilador protege contra confusiones entre familias. En el hot path del
sniffer un cast incorrecto en un plugin buggy es un SIGSEGV que tumba el NDR
del hospital. No es aceptable.

### Decisión 2 — Función de entrada semántica por familia (P2)

Cada familia exporta **su función de entrada específica**. El loader del
componente sabe qué símbolo resolver según `plugin_component_type()` +
`plugin_subtype()`. Si el símbolo no existe, el plugin se rechaza con warning.

### Decisión 3 — Solo primero-partido en PHASE 2 (P3: Opción C)

Diseñar hoy una interfaz "generic" para terceros imaginarios es YAGNI extremo
y casi siempre termina en una abstracción mediocre que hay que mantener por
retrocompatibilidad. Los plugins de PHASE 2 los desarrolla el equipo core.
La experiencia empírica con esos plugins informará el diseño de terceros en
PHASE 3 (2027+).

### Decisión 4 — Skills de rag-security NO se unifican (P4)

Las skills (ADR-010) tienen ciclo de vida síncrono con el LLM, siempre JSON
out, invocación bajo demanda. Los plugins tienen ciclo de vida asíncrono,
carga al inicio, ejecución en el datapath. Son dominios de falla distintos —
mantenerlos separados es correcto. La autenticación (ADR-013) puede compartir
el mismo `seed-client` sin que los mecanismos de carga se unifiquen.

### Decisión 5 — Plugins eBPF de kernel-telemetry en ADR-018 (P5)

`libbpf` vs `dlopen`, attach/detach de interfaces kernel, PIN en filesystem
BPF, gestión de mapas — son mundos distintos. Mezclarlos en ADR-017 generaría
un documento Frankenstein. El contrato de identidad (nombre, versión,
descripción) es común, pero el mecanismo de carga es ortogonal. ADR-018 los
diseña con la libertad que necesitan.

---

## Contrato base — toda familia de plugin

Todo plugin de toda familia exporta estos símbolos. Son la identidad del plugin
y la base para autenticación (ADR-013, DAY 95-96).

```c
// plugin_api_base.h
#pragma once
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PLUGIN_API_VERSION 1

typedef struct PluginConfig {
    const char* name;
    const char* config_json;
} PluginConfig;

typedef enum {
    PLUGIN_OK    = 0,
    PLUGIN_ERROR = 1,
    PLUGIN_SKIP  = 2
} PluginResult;

// ── Identidad — OBLIGATORIO en TODA familia ──────────────────────────────────
const char*  plugin_name();
const char*  plugin_version();
int          plugin_api_version();      // debe retornar PLUGIN_API_VERSION
const char*  plugin_component_type();  // "sniffer"|"ml-detector"|"rag-ingester"
const char*  plugin_subtype();         // ver tabla por familia
const char*  plugin_description();

// ── Ciclo de vida — OBLIGATORIO en TODA familia ──────────────────────────────
PluginResult plugin_init(const PluginConfig* config);
void         plugin_shutdown();

#ifdef __cplusplus
}
#endif
```

El loader valida `plugin_component_type()` **antes** de cualquier otro símbolo.
Un plugin con tipo incorrecto para el componente host hace skip silencioso —
nunca crash, nunca abort del proceso host.

---

## Struct base compartida — NetworkTuple

Factorización propuesta por DeepSeek para eliminar duplicación entre contextos:

```c
// plugin_api_base.h (añadir)
typedef struct NetworkTuple {
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint8_t  protocol;
} NetworkTuple;
```

Todos los contextos que lo necesiten incluyen `NetworkTuple net` como primer
campo — garantiza que el offset es predecible y permite helpers genéricos.

---

## Familia 1 — SnifferPlugin

**Componente host:** sniffer
**Subtipos:** `"packet"` (único en PHASE 2)
**Función de entrada:** `plugin_process_packet(SnifferContext*)`

```c
// plugin_api_sniffer.h
#pragma once
#include "plugin_api_base.h"

typedef struct SnifferContext {
    // ── Identidad de red ─────────────────────────────────────────────────────
    NetworkTuple   net;           // src/dst ip/port/protocol

    // ── Datos del paquete (read-only) ────────────────────────────────────────
    const uint8_t* raw_bytes;     // payload completo — para DPI
    size_t         length;

    // ── Features en construcción (write) ────────────────────────────────────
    void*          flow_features; // puntero opaco a FlowFeatures del host
                                  // el plugin puede enriquecer — nunca castear
                                  // sin conocer la versión del host

    // ── Salida del plugin (write) ────────────────────────────────────────────
    int            threat_hint;   // 0=benign, 1=suspicious, 2=malicious
                                  // el host decide si lo considera — NUNCA bloquea solo
} SnifferContext;

// Función de entrada obligatoria para subtipo "packet"
PluginResult plugin_process_packet(SnifferContext* ctx);
```

**Plugins PHASE 2 de esta familia:**
- `libplugin_ja4_v1.so` — JA4 TLS fingerprinting (FEAT-TLS-1)
- `libplugin_dns_dga_v1.so` — DNS/DGA detection (FEAT-NET-1)
- `libplugin_http_inspect_v1.so` — HTTP payload WAF (FEAT-WAF-1)

**Caso especial — EbpfUprobePlugin:**
Los plugins vía eBPF uprobes (ej: `libplugin_ebpf_tls`) operan sobre
contexto de proceso+syscall, no de paquete. Su función de entrada es distinta.
En PHASE 2 no se implementan — se documentan como excepción futura cuando
haya ≥2 plugins de este tipo que justifiquen subfamilia formal.

---

## Familia 2 — MlDetectorPlugin

**Componente host:** ml-detector
**Subtipos:** `"inference"` | `"enrichment"`
**Función de entrada:** depende del subtipo

```c
// plugin_api_ml_detector.h
#pragma once
#include "plugin_api_base.h"

typedef struct MlDetectorContext {
    // ── Identidad de red (para enrichment/lookup) ─────────────────────────
    NetworkTuple   net;

    // ── Vector de features (read para inference, read para enrichment) ─────
    const float*   features;      // vector de N floats (N=40 en PHASE 1)
    int            n_features;

    // ── Salida de inferencia (write — solo subtipo "inference") ───────────
    float*         scores_out;    // vector de M scores por clase
    int            n_classes;

    // ── Contexto textual (para enrichment/IOC lookup) ─────────────────────
    const char*    domain_str;    // puede ser NULL si no hay DNS en el flujo
} MlDetectorContext;

// Función de entrada — subtipo "inference"
// El plugin ejecuta su propio modelo y escribe en scores_out
PluginResult plugin_predict(MlDetectorContext* ctx);

// Función de entrada — subtipo "enrichment"
// El plugin enriquece el contexto con información externa (IOC, threat intel)
// NO escribe en scores_out — puede modificar threat_hint via flow_features opaco
PluginResult plugin_enrich(MlDetectorContext* ctx);
```

**Plugins PHASE 2 de esta familia:**
- `libmodel_neris_v2.so` (inference) — RF reentrenado tras SYN-5
- `libmodel_wannacry_v1.so` (inference) — tras FEAT-RANSOM-1
- `libenrich_threat_intel_v1.so` (enrichment) — FEAT-NET-2

**Invariante crítico:**
Un plugin de subtipo `"inference"` **NUNCA** toma decisiones de bloqueo.
Escribe scores. El core del ml-detector decide qué hacer con esos scores
según ADR-007 (AND-consensus). Un plugin que intente modificar directamente
`firewall_action` o equivalente viola ADR-012 y se considera malicioso.

---

## Familia 3 — RagIngesterPlugin (futuro)

**Componente host:** rag-ingester
**Subtipos:** `"parser"` (PHASE 3)
**Función de entrada:** `plugin_process_event(RagIngesterContext*)`

```c
// plugin_api_rag_ingester.h — esqueleto para PHASE 3
#pragma once
#include "plugin_api_base.h"

typedef struct RagIngesterContext {
    NetworkTuple   net;
    const char*    raw_event_json;  // evento raw sin parsear
    char*          enriched_json;   // buffer de salida — el plugin puede enriquecer
    size_t         enriched_size;
} RagIngesterContext;

PluginResult plugin_process_event(RagIngesterContext* ctx);
```

No se implementa en PHASE 2. Se define aquí para reservar el espacio
en la jerarquía y que ADR-017 sea el documento de referencia completo.

---

## Familias futuras identificadas por el Consejo

Documentadas aquí para que no se pierdan. **No implementar en PHASE 2.**

### PostProcessorPlugin (Gemini, Grok, Qwen)
Para plugins que actúan *después* de la decisión de bloqueo:
notificaciones SIEM, MITRE ATT&CK tagging, exportación a Splunk/Sentinel.
**No influyen en la decisión** — solo efectos secundarios auditables.
`plugin_subtype() = "postprocessor"`

### FlowPlugin (ChatGPT5)
Para detección temporal y correlación multi-paquete. Encaja con ADR-008
(flow graphs). Recibe `FlowContext` con ventana temporal agregada, no
paquete individual. Necesario para Ryuk/Conti (lateral movement lento).
`plugin_subtype() = "flow"`

### UprobePlugin (Qwen)
Para plugins vía eBPF uprobes en espacio de usuario (OpenSSL, glibc).
Su contexto es `ProcessContext` (PID, syscall, stack trace), no
`PacketContext`. Cuando haya ≥2 plugins reales de este tipo → subfamilia
formal. Hasta entonces: excepción documentada bajo `SnifferPlugin`.

---

## Jerarquía completa validada

```
PluginBase (plugin_api_base.h)
│   plugin_name(), plugin_version(), plugin_api_version()
│   plugin_component_type(), plugin_subtype(), plugin_description()
│   plugin_init(PluginConfig*), plugin_shutdown()
│
├── SnifferPlugin (plugin_api_sniffer.h)
│   │   plugin_process_packet(SnifferContext*)
│   │   subtype: "packet"
│   │
│   ├── PacketPlugin — DPI: ja4, dns_dga, http_inspect       [PHASE 2]
│   └── [UprobePlugin — eBPF uprobes: ebpf_tls]             [futuro ≥2 plugins]
│
├── MlDetectorPlugin (plugin_api_ml_detector.h)
│   │
│   ├── InferencePlugin — plugin_predict(MlDetectorContext*) [PHASE 2]
│   │   subtype: "inference"
│   │   modelos RF: neris_v2, wannacry_v1, ryuk_v1...
│   │
│   └── EnrichmentPlugin — plugin_enrich(MlDetectorContext*) [PHASE 2]
│       subtype: "enrichment"
│       threat_intel, IOC feeds
│
├── RagIngesterPlugin (plugin_api_rag_ingester.h)
│   │   plugin_process_event(RagIngesterContext*)
│   │   subtype: "parser"
│   └── [futuro — custom parsers, format adapters]           [PHASE 3]
│
├── [PostProcessorPlugin] — efectos post-decisión            [futuro PHASE 3]
├── [FlowPlugin] — correlación temporal multi-paquete        [futuro PHASE 3]
│
└── [EbpfKernelPlugin] → ADR-018                             [futuro]
        loaded via libbpf, not dlopen
        kprobes, tracepoints, attach/detach kernel interfaces
```

---

## Naming convention — ficheros .so

```
lib{familia}_{nombre}_v{N}.so

Familias:
  plugin_    → SnifferPlugin PacketPlugin (DPI genérico)
  model_     → MlDetectorPlugin InferencePlugin (modelos RF)
  enrich_    → MlDetectorPlugin EnrichmentPlugin (IOC, threat intel)
  ingest_    → RagIngesterPlugin (parsers)
  post_      → PostProcessorPlugin (futuro)

Ejemplos correctos:
  libplugin_ja4_v1.so
  libplugin_dns_dga_v1.so
  libmodel_neris_v1.so
  libmodel_neris_v2.so          ← reentrenado — el v1 queda en disco como historia
  libmodel_wannacry_v1.so
  libenrich_threat_intel_v1.so

Ejemplos incorrectos (evitar):
  libja4.so                     ← sin familia ni versión
  libplugin_neris_model.so      ← familia incorrecta para un modelo RF
```

El historial de modelos es auditable en el filesystem sin base de datos.
`libmodel_neris_v1.so` y `libmodel_neris_v2.so` coexisten — el operador
puede hacer rollback cambiando el `enabled` en el JSON del componente.

---

## Cómo el loader valida el tipo

```cpp
// En PluginLoader::load_plugins() — tras dlopen y resolución de símbolos base

std::string declared_type = plugin->fn_component_type();
std::string declared_sub  = plugin->fn_subtype();

if (declared_type != expected_component_type_) {
    LOG_WARN("[plugin-loader] tipo incorrecto: plugin='{}' declara '{}', "
             "host espera '{}' — skip",
             plugin->fn_name(), declared_type, expected_component_type_);
    goto skip_plugin;
}

// Resolver función de entrada según subtipo
if (declared_type == "sniffer") {
    plugin->fn_process = resolve<PluginResult(*)(SnifferContext*)>(
        handle, "plugin_process_packet");
} else if (declared_type == "ml-detector") {
    if (declared_sub == "inference") {
        plugin->fn_predict = resolve<PluginResult(*)(MlDetectorContext*)>(
            handle, "plugin_predict");
    } else if (declared_sub == "enrichment") {
        plugin->fn_enrich = resolve<PluginResult(*)(MlDetectorContext*)>(
            handle, "plugin_enrich");
    }
}
// ... etc por familia
```

---

## Restricciones invariantes — no negociables

1. **Plugins: SOLO feature extraction / inference / enrichment.**
   La decisión de bloqueo pertenece siempre al core (ADR-007 AND-consensus).

2. **Un plugin no puede forzar un bloqueo.** `threat_hint` es una sugerencia
   que el host puede ignorar. No existe canal de escritura directa a firewall
   desde un plugin.

3. **Un crash en un plugin no puede matar el proceso host.**
   PHASE 1: budget monitor detecta overruns y loguea.
   PHASE 2: proceso separado + watchdog (crash isolation).

4. **El core legacy (RF embebidos, Fast Detector) es FROZEN.**
   No se migra a plugins. No se toca para acomodar plugins.

5. **Autenticación de plugins:** PHASE 2 (ADR-013, seed-client DAY 95-96).
   Un plugin sin firma válida no se carga. El mecanismo de firma es ortogonal
   a este ADR — ADR-017 define contratos, ADR-013 define autenticación.

---


## Regla de reprovisioning — granular, no big bang

Añadir un plugin a un componente **no requiere recompilar el componente**.
El binario del componente no cambia — solo cambia su JSON de configuración
y el par de claves componente↔plugin_nuevo.
```
Evento                           → Reprovisionar
─────────────────────────────────────────────────────────────
Nuevo plugin en componente X     → solo X↔plugin_nuevo
Nueva versión plugin Y en X      → solo X↔plugin_Y_v_nueva
Nueva versión binario de X       → X↔todos sus interlocutores
Rotación periódica de seeds      → todos (mantenimiento)
```

**Por qué añadir un plugin no obliga a reprovisionar los canales ZeroMQ:**
La semilla ChaCha20 entre sniffer↔ml-detector es independiente del hecho
de que ml-detector cargue un plugin nuevo. El canal ZeroMQ usa la keypair
del componente — que no cambia cuando el componente carga un nuevo plugin.
Solo cambia la relación componente↔plugin_nuevo.

**Implementación en tools/provision:**
```
tools/
    provision/
        provision.sh              ← orquestador principal
        provision_component.sh    ← un componente individual
        provision_plugin.sh       ← un plugin userspace individual
        provision_ebpf_plugin.sh  ← un plugin eBPF individual
        verify_provision.sh       ← verifica estado del provisioning
    stress/
        tcpreplay_neris.sh
        tcpreplay_bigflows.sh
        calculate_f1_neris.py
```

`verify_provision.sh` verifica que todos los pares de claves están en su
sitio y son coherentes antes de arrancar el pipeline — falla rápido con
mensaje claro antes de que el runtime falle con un error críptico.

## Consecuencias

**Positivas:**
- Type-safety en el hot path — el compilador protege contra confusiones
  entre familias en el punto más crítico del sistema
- Semántica correcta por familia — `plugin_predict` no "procesa paquetes"
- Extensibilidad controlada — PHASE 3 para terceros, cuando haya empírica
- Historial de modelos auditable en filesystem — sin base de datos adicional
- La línea divisoria core/plugin protege la integridad científica del paper:
  el sistema detecta clases de comportamiento, no firmas de malware concreto

**Negativas / limitaciones:**
- Más headers que mantener (3 familias activas en PHASE 2)
- `PLUGIN_API_VERSION++` necesario si cambia cualquier contexto — breaking change
  gestionado con versionado semántico del .so
- Sin extensibilidad de terceros hasta PHASE 3 — contribuidores externos
  tendrán que esperar

---

## Relación con otros ADRs

| ADR | Relación |
|---|---|
| ADR-003 | Validadores de modelos (verify_A..F) están **fuera** del scope de este ADR — son herramientas CI, no plugins de producción |
| ADR-007 | AND-consensus para bloqueo — invariante que ningún plugin puede violar |
| ADR-010 | Skills de rag-security — mecanismo separado, no unificado aquí |
| ADR-012 | Plugin-loader PHASE 1 — mecanismo de carga implementado, este ADR define los contratos |
| ADR-013 | Autenticación de plugins — capa ortogonal, implementada DAY 95-96 |
| ADR-014 | Plugins de fuzzing para sniffer — familia SnifferPlugin subtipo "packet" |
| ADR-015 | Integridad eBPF — el manifiesto de plugins usa el contrato de identidad de este ADR |
| ADR-016 | Plugins eBPF de kernel-telemetry — separados en ADR-018 |

---

## Secuencia de implementación

```
DAY 94 (hoy):
  [ ] Crear plugin_api_base.h (refactor de plugin_api.h existente)
  [ ] Crear plugin_api_sniffer.h
  [ ] Crear plugin_api_ml_detector.h (esqueleto)
  [ ] Actualizar plugin_loader.hpp — añadir validación component_type + subtype
  [ ] Integrar plugin-loader en sniffer (Tarea A del DAY 94)

DAY 95-96:
  [ ] ADR-013 seed-client — autenticación de plugins
  [ ] provision.sh — keypairs y seeds

DAY 97+:
  [ ] Primer plugin real: libplugin_dns_dga_v1.so (FEAT-NET-1, P1)
  [ ] libmodel_neris_v2.so tras reentrenamiento (SYN-5)
```

---

## Acta del Consejo de Sabios — DAY 94

**Consulta:** ADR-017 Plugin Interface Hierarchy
**Modelos participantes:** Claude, ChatGPT5, DeepSeek, Gemini, Grok, Qwen (6/7)
**Resultado:** Unanimidad en las 5 preguntas

| Pregunta | Decisión | Votos |
|---|---|---|
| P1 — Contextos tipados | Opción A (tipado fuerte por familia) | 6/6 |
| P2 — Función de entrada | Separación semántica por familia + subtype | 6/6 |
| P3 — Plugins futuros | Opción C (primero-partido PHASE 2, terceros PHASE 3) | 6/6 |
| P4 — Skills rag-security | NO unificar — mecanismo separado | 6/6 |
| P5 — eBPF kernel-telemetry | ADR-018 separado | 6/6 |

**Enriquecimientos aprobados por el Consejo:**
- `plugin_subtype()` añadido al contrato base (ChatGPT5)
- `NetworkTuple` base compartida entre contextos (DeepSeek)
- `EbpfUprobePlugin` como excepción documentada, no subfamilia (consenso)
- Familias futuras documentadas: PostProcessorPlugin, FlowPlugin, UprobePlugin

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios: Claude · ChatGPT5 · DeepSeek · Gemini · Grok · Qwen · Parallel.ai*
*DAY 94 — 22 marzo 2026*
*ML Defender (aRGus NDR)*