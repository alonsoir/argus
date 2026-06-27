# Consulta al Consejo de Sabios — ADR-017
## Jerarquía de interfaces del sistema de plugins
### ML Defender (aRGus NDR) — DAY 94, 22 marzo 2026

---

## Por qué esta consulta

En DAY 93 se implementó ADR-012 PHASE 1: el mecanismo de carga de plugins
(`libplugin_loader.so`) funciona, ABI validada, `libplugin_hello.so` desplegada.
El mecanismo de carga está resuelto. Lo que no está resuelto es el **contrato
de interfaces** — qué funciones expone cada familia de plugin, qué recibe, qué
devuelve, y cómo el loader verifica que un plugin es del tipo correcto para el
componente que lo carga.

Esta consulta presenta el inventario completo de plugins mencionados en los
ADR-001 a ADR-016, agrupa por componente host, e identifica las preguntas de
diseño abiertas que el Consejo debe resolver para que ADR-017 quede cerrado.

**Principio irrenunciable (no sujeto a revisión):**

> El core actual — modelos RF embebidos, Fast Detector, pipeline 6/6 — es
> **legacy estable**. No se toca. Todo crecimiento futuro entra por el sistema
> de plugins. La migración del core a plugins es decisión futura, no objetivo
> presente. Strangler Fig Pattern.

---

## Inventario completo de plugins por componente host

### COMPONENTE: sniffer

El sniffer es el componente host natural para plugins de **captura y extracción
de features**. Opera en el hot path — latencia es crítica.

| Plugin | Feature ID | ADR origen | Inputs conocidos | Output conocido | Estado |
|---|---|---|---|---|---|
| `libplugin_hello` | — | ADR-012 | PacketContext actual | PluginResult | ✅ DONE |
| `libplugin_ja4` | FEAT-TLS-1 | ADR-012 | TLS handshake bytes | JA4 fingerprint string | P1 |
| `libplugin_dns_dga` | FEAT-NET-1 | ADR-012 | DNS payload bytes | DGA score float | P1 |
| `libplugin_http_inspect` | FEAT-WAF-1 | ADR-012 | HTTP payload bytes | WAF verdict | P2 |
| `libplugin_ebpf_tls` | — | ADR-012 | eBPF uprobes OpenSSL | TLS plaintext features | P3 |
| Plugins eBPF de fuzzing | — | ADR-014 | pcap mutado | métricas de estabilidad | post-arXiv |

**Observación crítica — sniffer:**
Los plugins `ja4`, `dns_dga`, `http_inspect` necesitan **DPI** (Deep Packet
Inspection): reciben bytes de payload, no solo cabeceras TCP/IP. El
`PacketContext` actual tiene `raw_bytes` + `length` — suficiente para DPI.
Pero `libplugin_ebpf_tls` opera vía uprobes en OpenSSL, que es un modelo
completamente distinto: no recibe bytes del kernel, sino que se activa cuando
la aplicación llama a `SSL_read`/`SSL_write`. Este plugin es
**cualitativamente diferente** de los demás — requiere su propia familia de
interfaz o es un caso especial documentado.

---

### COMPONENTE: ml-detector

El ml-detector es el host natural para plugins de **inferencia y enriquecimiento
semántico**. Recibe features ya extraídas por el sniffer, no paquetes crudos.

| Plugin | Feature ID | ADR origen | Inputs conocidos | Output conocido | Estado |
|---|---|---|---|---|---|
| Modelos RF reentrenados | FEAT-RETRAIN-* | ADR-003 | FeatureVector (40 floats) | scores por clase | futuro |
| `libplugin_threat_intel` | FEAT-NET-2 | ADR-012 | src_ip, dst_ip, domain | IOC match bool + score | P2 |
| `libplugin_smb_specialist` | — | ADR-012 | SMBScanFeatures (proto) | SMB threat score | P3 enterprise |
| Modelo WannaCry/NotPetya | FEAT-RANSOM-1 | BACKLOG | FeatureVector | ransomware score | post SYN-5 |
| Modelo Ryuk/Conti | FEAT-RANSOM-4 | BACKLOG | FeatureVector extendido | ransomware score | post PHASE2 |

**Observación crítica — ml-detector:**
Los modelos RF reentrenados tienen un contrato claro y uniforme:

```c
// Todos los model-plugins exponen esto:
PluginResult plugin_predict(
    const float* features,   // vector de N floats (N conocido en tiempo de carga)
    int          n_features,
    float*       scores_out, // vector de M scores (M = número de clases)
    int          n_classes
);
```

El contrato es estable porque el dominio es estable: siempre floats in,
floats out, sobre el mismo espacio de features definido por el proto.

`libplugin_threat_intel` es **cualitativamente diferente**: no hace inferencia
sobre features de flujo, sino lookup en listas externas (IPs, dominios). Sus
inputs son strings e IPs, no el vector de features. Esto sugiere que dentro
de ml-detector hay al menos dos subfamilias de interfaz: **inference plugins**
y **enrichment plugins**.

---

### COMPONENTE: rag-security

rag-security tiene el LLM confinado (ADR-010). Sus "skills" son funcionalmente
equivalentes a plugins: código cargable que el LLM puede invocar dentro de su
espacio de acción restringido.

| Plugin/Skill | ADR origen | Inputs | Output | Estado |
|---|---|---|---|---|
| `skill_query_sqlite` | ADR-010 | SQL query string | JSON rows | existente |
| `skill_query_faiss` | ADR-010 | embedding vector | JSON hits | existente |
| `skill_exec_authorized_cmd` | ADR-010 | command name + args | JSON result | existente |
| Skills futuras | ADR-010 | variable | JSON siempre | futuro |

**Observación crítica — rag-security:**
Las skills de ADR-010 son ya un sistema de plugins, pero implementado de forma
ad-hoc, independiente de `plugin-loader`. La pregunta es: ¿deben unificarse
bajo el mismo mecanismo `plugin-loader` con su propio `RagSecurityContext`,
o es su naturaleza (invocación por LLM, siempre JSON out) suficientemente
distinta para mantenerlas separadas?

---

### COMPONENTE: kernel-telemetry (séptimo componente, ADR-016)

Los programas eBPF de `kernel-telemetry` son también plugins en sentido amplio:
módulos cargables con ciclo de vida gestionado, con interfaz bien definida.

| Plugin eBPF | ADR origen | Inputs (kernel) | Output | Estado |
|---|---|---|---|---|
| `kt_bpf_prog_load.bpf.c` | ADR-016 | kprobe bpf_prog_load | evento JSON+HMAC | propuesto P2 |
| `kt_memfd.bpf.c` | ADR-016 | tracepoint memfd_create | evento JSON+HMAC | propuesto P2 |
| `kt_module_load.bpf.c` | ADR-016 | tracepoint module_load | evento JSON+HMAC | propuesto P2 |
| `kt_ptrace.bpf.c` | ADR-016 | tracepoint ptrace | evento JSON+HMAC | propuesto P2 |

**Observación crítica — kernel-telemetry:**
Estos programas eBPF son `.bpf.c` compilados a bytecode, no `.so` en espacio
de usuario. Su mecanismo de carga es `libbpf`, no `dlopen`. Son plugins en
concepto pero **no son candidatos al mismo mecanismo `plugin-loader`**. Requieren
un `EbpfPluginLoader` separado, con interfaz análoga pero implementación distinta.
La pregunta es si ADR-017 debe contemplar esta familia o dejarla para un ADR-018
específico de kernel-telemetry.

---

### COMPONENTE: validadores de modelos ML (ADR-003)

ADR-003 define un pipeline de validación modular: `verify_A` a `verify_F`.
Estos son también plugins en concepto: módulos intercambiables con interfaz común.

| Validador | Responsabilidad | Interfaz implícita |
|---|---|---|
| `verify_A` | Overfitting detection (holdout set) | `bool validate(Model, ValidationContext)` |
| `verify_B` | Distribution shift detection | ídem |
| `verify_C` | Adversarial robustness | ídem |
| `verify_D` | Malicious model detection | ídem |
| `verify_E` | Shadow mode testing | ídem |
| `verify_F` | Performance regression | ídem |

**Observación:** estos validadores son herramientas de desarrollo/CI, no de
producción. No necesitan `dlopen` — pueden ser funciones en una librería
estática de validación. Probablemente **fuera del scope de ADR-017**.

---

## Lo que está decidido (no sujeto a revisión por el Consejo)

1. **Mecanismo de carga:** `dlopen`/`dlsym` lazy loading — IMPLEMENTADO (DAY 93)
2. **Contrato base de identidad** — todo plugin de toda familia expone:
   ```c
   const char*  plugin_name();
   const char*  plugin_version();
   int          plugin_api_version();    // debe == PLUGIN_API_VERSION
   const char*  plugin_component_type(); // "sniffer"|"ml-detector"|"rag-security"|...
   const char*  plugin_description();
   PluginResult plugin_init(const PluginConfig* config);
   void         plugin_shutdown();
   ```
3. **El loader valida `plugin_component_type()`** antes de invocar cualquier
   función específica — un plugin del tipo incorrecto hace skip silencioso, nunca crash.
4. **Plugins: SOLO feature extraction / enrichment / inference.** La decisión
   de bloqueo pertenece siempre al core. Invariante arquitectónico — no negociable.
5. **Core legacy:** modelos RF embebidos y Fast Detector son FROZEN. No se migran
   a plugins en esta fase.
6. **Versionado en el nombre del fichero:** `libmodel_neris_v1.so`,
   `libmodel_wannacry_v2.so` — auditable en filesystem sin base de datos.

---

## Preguntas abiertas que el Consejo debe resolver

### PREGUNTA 1 — Contextos tipados por componente

El `PacketContext` actual (ADR-012) es sniffer-centric. Un plugin de ml-detector
necesita un `MlDetectorContext` distinto. ¿Cuál es el diseño correcto?

**Opción A — Un contexto por familia de componente:**
```c
// plugin_api_sniffer.h
typedef struct SnifferContext {
    const uint8_t* raw_bytes;
    size_t         length;
    uint32_t       src_ip; uint32_t dst_ip;
    uint16_t       src_port; uint16_t dst_port;
    uint8_t        protocol;
    void*          features;      // FlowFeatures opaco
    int            threat_hint;   // write-only para el plugin
} SnifferContext;

// plugin_api_ml_detector.h
typedef struct MlDetectorContext {
    const float* features;        // vector de N floats
    int          n_features;      // siempre 40 en PHASE 1
    float*       scores_out;      // write-only: M scores de inferencia
    int          n_classes;
    const char*  src_ip_str;      // para threat_intel lookup
    const char*  dst_ip_str;
    const char*  domain_str;      // para DNS plugins (puede ser NULL)
} MlDetectorContext;
```

**Opción B — Contexto único extensible con void* y type tag:**
```c
typedef struct PluginContext {
    const char* component_type;  // "sniffer" | "ml-detector" | ...
    uint32_t    context_version;
    void*       data;            // cast según component_type
    size_t      data_size;
} PluginContext;
```
La Opción B es más genérica pero requiere que el plugin castee correctamente
y conozca la estructura interna — más propensa a errores. La Opción A es más
verbosa pero type-safe y documentada.

**¿Cuál recomienda el Consejo? ¿Hay una Opción C que no estamos viendo?**

---

### PREGUNTA 2 — Función de entrada por familia

La función de entrada del contrato actual es `plugin_process_packet(PacketContext*)`.
Para ml-detector es semánticamente incorrecta — no procesa paquetes, predice.

**Propuesta:**
```c
// Sniffer plugins: procesan paquetes/flujos
PluginResult plugin_process_packet(SnifferContext* ctx);

// ML-Detector inference plugins: predicen sobre features
PluginResult plugin_predict(MlDetectorContext* ctx);

// ML-Detector enrichment plugins: enriquecen con información externa
PluginResult plugin_enrich(MlDetectorContext* ctx);

// RAG-Security skill plugins: ejecutan una acción confinada
PluginResult plugin_execute(RagSecurityContext* ctx);
```

Cada familia exporta **su función de entrada específica** además de las
funciones de identidad comunes. El loader del componente sabe qué símbolo
resolver según el `plugin_component_type()`.

**¿Está de acuerdo el Consejo con esta separación? ¿Falta alguna familia?**

---

### PREGUNTA 3 — ¿Cómo gestionar plugins futuros con contratos desconocidos?

Los plugins `ja4`, `dns_dga` y `http_inspect` tienen inputs y outputs conocidos
hoy porque los hemos diseñado. Pero ¿qué pasa cuando un tercero quiere contribuir
un plugin con inputs que no anticipamos?

**Opción A — Solo plugins de familias predefinidas:**
El loader solo acepta plugins de las familias declaradas en ADR-017. Un plugin
que no encaja en ninguna familia se rechaza. Extensible añadiendo nuevas familias
en versiones futuras del API (PLUGIN_API_VERSION++).

**Opción B — Familia "generic" con schema autodescriptivo:**
Un plugin puede declararse de familia `"generic"` y exponer un JSON schema que
describe sus inputs y outputs. El loader lo acepta sin validar el contrato —
la responsabilidad recae en el operador.

**Opción C — Solo primero-partido en PHASE 2, terceros en PHASE 3:**
No resolvemos ahora el problema de terceros. En PHASE 2 solo hay plugins
desarrollados por el equipo core. La arquitectura para terceros se diseña
en PHASE 3, cuando tengamos experiencia empírica.

**¿Qué recomienda el Consejo?**

---

### PREGUNTA 4 — ¿Unificar skills de rag-security bajo plugin-loader?

Las skills de ADR-010 son funcionalmente plugins del LLM confinado. Actualmente
son funciones estáticas invocadas por el LLM. ¿Tiene sentido unificarlas bajo
`plugin-loader` con un `RagSecurityContext`, o su naturaleza (siempre JSON out,
invocadas por LLM) justifica mantenerlas como mecanismo separado?

**Argumento para unificar:** un único mecanismo de carga, autenticación (ADR-013),
y versionado para todo el sistema.

**Argumento para separar:** las skills tienen ciclo de vida distinto (no tienen
`process_packet`), son síncronas con el LLM, y su interfaz JSON ya está bien
definida en ADR-010. Añadir `dlopen` no aporta nada que el mecanismo actual
no resuelva ya.

**¿Qué recomienda el Consejo?**

---

### PREGUNTA 5 — Plugins eBPF de kernel-telemetry: ¿mismo ADR-017 o ADR-018?

Los programas eBPF de `kernel-telemetry` (ADR-016) son conceptualmente plugins
pero técnicamente distintos: se cargan con `libbpf`, no con `dlopen`, y operan
en kernel space. ¿Los contempla ADR-017 como una familia adicional con su propio
`EbpfPluginLoader`, o se separan en ADR-018?

**Argumento para incluir en ADR-017:** el contrato de identidad (name, version,
api_version, description, component_type) es común. El mecanismo de carga es
un detalle de implementación del loader específico.

**Argumento para separar en ADR-018:** el ciclo de vida de un programa eBPF es
fundamentalmente distinto (attach/detach de interfaces kernel, PIN en filesystem
BPF). Mezclarlos con `dlopen` plugins introduce confusión conceptual innecesaria.

**¿Qué recomienda el Consejo?**

---

## Propuesta preliminar de jerarquía ADR-017

Basada en el análisis anterior, esta es la jerarquía que proponemos al Consejo
para validación, corrección, o rechazo:

```
PluginBase (plugin_api_base.h)
│   plugin_name()
│   plugin_version()
│   plugin_api_version()
│   plugin_component_type()
│   plugin_description()
│   plugin_init(PluginConfig*)
│   plugin_shutdown()
│
├── SnifferPlugin (plugin_api_sniffer.h)
│   │   plugin_process_packet(SnifferContext*)
│   │
│   ├── PacketPlugin      — raw bytes, DPI (ja4, dns_dga, http_inspect)
│   └── EbpfUprobePlugin  — eBPF uprobes (ebpf_tls) — caso especial documentado
│
├── MlDetectorPlugin (plugin_api_ml_detector.h)
│   │
│   ├── InferencePlugin   — plugin_predict(MlDetectorContext*)
│   │       modelos RF reentrenados, smb_specialist
│   │
│   └── EnrichmentPlugin  — plugin_enrich(MlDetectorContext*)
│           threat_intel, IOC feeds
│
├── RagIngesterPlugin (plugin_api_rag_ingester.h) — futuro
│   │   plugin_process_event(RagIngesterContext*)
│   └── custom parsers, format adapters
│
└── [EbpfKernelPlugin — kernel-telemetry] → ¿ADR-018?
        loaded via libbpf, not dlopen
        attach/detach kernel interfaces
```

**Naming convention para ficheros .so:**

```
lib{familia}_{nombre}_v{N}.so

Ejemplos:
  libplugin_ja4_v1.so
  libplugin_dns_dga_v1.so
  libmodel_neris_v1.so
  libmodel_neris_v2.so       ← reentrenado
  libmodel_wannacry_v1.so
  libenrich_threat_intel_v1.so
```

---

## Formato de respuesta solicitado al Consejo

Para cada pregunta (1 a 5), por favor responder:

1. **Recomendación** — opción preferida o propuesta alternativa
2. **Razonamiento** — por qué en 2-3 frases
3. **Riesgos** — qué puede salir mal con esa opción
4. **Blocker** — ¿hay algo en las preguntas posteriores que cambia esta respuesta?

Para la **propuesta preliminar de jerarquía**, por favor:
- Validar o rechazar la estructura propuesta
- Identificar familias faltantes que no hemos visto
- Identificar familias que sobran o que deberían fusionarse

---

## Contexto técnico para el Consejo

**Stack actual:**
- C++20, eBPF/XDP, ZeroMQ, FAISS, ChaCha20, protobuf, ONNX Runtime
- Plugin-loader: `libplugin_loader.so.1.0.0` (53K), implementado en DAY 93
- ABI contract: `plugin_api.h` con `PLUGIN_API_VERSION=1` — estable
- Componentes: 6/6 RUNNING + kernel-telemetry propuesto (ADR-016)

**Restricción hardware:** el sistema debe funcionar en N100, RPi, hardware
de hospital de 5 años. Cada plugin que se carga tiene coste real en RAM y latencia.
El diseño debe favorecer la optionalidad — cargar solo lo que se necesita.

**Restricción de seguridad:** ADR-013 define la autenticación de plugins
(seed-client, DAY 95-96). ADR-017 diseña los contratos. Son capas ortogonales —
ADR-017 no decide cómo se autentica, solo cómo se comunica.

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus NDR)*
*DAY 94 — 22 marzo 2026*
*Destinatarios: Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Parallel.ai*

Claude:

Inventario completo — 5 familias de plugins identificadas:[Consejo adr017 consulta.md](Consejo%20adr017%20consulta.md)
La más sorprendente es que las skills de ADR-010 ya son un sistema de plugins, implementado ad-hoc antes de que existiera plugin-loader. La pregunta de si unificarlas es real y no trivial.
Los programas eBPF de kernel-telemetry (ADR-016) son conceptualmente plugins pero técnicamente incompatibles con dlopen — necesitan libbpf. Esto merece una pregunta explícita al Consejo.
Los validadores de modelos de ADR-003 (verify_A..F) son también plugins en concepto, pero son herramientas de CI/desarrollo — probablemente fuera del scope de ADR-017.
Las 5 preguntas abiertas que el Consejo tiene que resolver son genuinas — no tienen respuesta obvia. La más difícil es la PREGUNTA 3: ¿qué pasa con plugins cuyo contrato no anticipamos hoy? La postura conservadora (Opción C — solo primero-partido en PHASE 2) es la más segura y encaja con Via Appia Quality.
Mi posición como co-autor, para que el Consejo la considere: la PREGUNTA 4 (¿unificar skills de rag-security?) tiene respuesta clara — no unificar. Sus ciclos de vida son demasiado distintos y la unificación añadiría complejidad sin beneficio real en esta fase.