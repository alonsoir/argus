# ADR-018: eBPF Kernel Plugin Loader

**Estado:** PROPUESTO — implementación post bare-metal stress test (PHASE 2)
**Fecha:** 2026-03-22 (DAY 94)
**Autor:** Alonso Isidoro Román + Claude (Anthropic)
**Revisado por:** Consejo de Sabios — ML Defender (aRGus NDR)
**Componentes afectados:** kernel-telemetry (séptimo componente, ADR-016)
**Depende de:** ADR-016 (kernel-telemetry), ADR-017 (plugin interface hierarchy)
**Relacionado con:** ADR-013 (autenticación), ADR-015 (eBPF integrity), ADR-019 (OS hardening)

---

## Por qué ADR-018 es necesario y distinto de ADR-017

ADR-017 define la jerarquía de interfaces para plugins en espacio de usuario,
cargados vía `dlopen`/`dlsym`. El Consejo de Sabios decidió por unanimidad
(P5, DAY 94) que los programas eBPF de `kernel-telemetry` merecen un ADR
separado porque su ciclo de vida es **fundamentalmente distinto**:

| Aspecto | Plugins ADR-017 | Plugins eBPF ADR-018 |
|---|---|---|
| Mecanismo de carga | `dlopen` / `dlsym` | `libbpf` / `bpf_prog_load` |
| Espacio de ejecución | userspace | kernel space |
| Ciclo de vida | init → process → shutdown | load → attach → detach → unload |
| Persistencia | en memoria del proceso | PIN en BPF filesystem |
| Verificación | HMAC del .so | verificador del kernel + HMAC del .bpf.o |
| Gestión de mapas | N/A | BPF maps compartidos kernel↔userspace |
| Herramientas | standard C++ | libbpf + CO-RE + BTF |

Mezclarlos en ADR-017 hubiera generado un documento Frankenstein. Esta
separación permite diseñar cada mecanismo con la libertad que necesita.

---

## Contexto

ADR-016 define el séptimo componente del pipeline (`kernel-telemetry`) y los
programas eBPF que lo componen:

- `kt_bpf_prog_load.bpf.c` — kprobe en `bpf_prog_load`
- `kt_memfd.bpf.c` — tracepoint `memfd_create`
- `kt_module_load.bpf.c` — tracepoint `module_load`
- `kt_ptrace.bpf.c` — tracepoint `ptrace`

Estos programas son "plugins" en sentido conceptual — módulos cargables con
ciclo de vida gestionado y funcionalidad bien delimitada. ADR-018 define cómo
se cargan, autentican, versionan y gestionan, siguiendo los mismos principios
de ADR-017 pero con el stack técnico correcto.

---

## Principios irrenunciables — los mismos de ADR-017

### JSON is the law

Cada programa eBPF tiene su propio fichero JSON de contrato:

```json
// /etc/ml-defender/ebpf-plugins/kt_bpf_prog_load.json
{
    "name":        "kt_bpf_prog_load",
    "version":     "1.0.0",
    "description": "kprobe on bpf_prog_load — detects unsigned eBPF loading",
    "component_type": "kernel-telemetry",
    "subtype":     "kprobe",
    "object_path": "/usr/lib/ml-defender/ebpf/kt_bpf_prog_load.bpf.o",
    "attach": {
        "type":   "kprobe",
        "target": "bpf_prog_load"
    },
    "response_mode": "ACTIVE",
    "budget_ms":  5,
    "pin_path":   "/sys/fs/bpf/ml-defender/kt_bpf_prog_load"
}
```

Si falta cualquier clave requerida, el programa **falla en carga** con error
explícito y descriptivo. Sin valores por defecto silenciosos. Sin comportamiento
implícito. El componente `kernel-telemetry` loguea exactamente qué falta.

### Fallo explícito — sin degradación silenciosa

Un programa eBPF que no pasa la verificación de integridad (HMAC del .bpf.o)
no se carga. Un programa cuyo JSON tiene campos faltantes no se carga.
El componente `kernel-telemetry` continúa con los programas que sí pasaron
verificación, pero loguea con nivel CRITICAL cada programa rechazado.

### Versionado en el nombre del fichero

```
kt_bpf_prog_load_v1.bpf.o
kt_bpf_prog_load_v2.bpf.o   ← nueva versión — v1 queda como rollback
```

El JSON del componente declara qué versión cargar. El provisioning genera
keypairs distintos para cada versión. Una v1 keypair no autentica una v2.

---

## Autenticación — extensión de ADR-013 al plano eBPF

### Keypairs para programas eBPF

`provision.sh` (ADR-013, DAY 95-96) se extiende para generar keypairs para
cada programa eBPF declarado en el JSON de `kernel-telemetry`.

El proceso es idéntico al de plugins userspace (ADR-017):

```bash
# provision.sh — sección eBPF plugins
# Solo si el componente declara el programa en su JSON

if jq -e '.ebpf_plugins.enabled | contains(["kt_bpf_prog_load"])' \
    kernel_telemetry.json > /dev/null; then

    # Generar keypair para este programa eBPF
    openssl genpkey -algorithm Ed25519 \
        -out /etc/ml-defender/ebpf-plugins/kt_bpf_prog_load_private.pem
    openssl pkey -pubout \
        -in  /etc/ml-defender/ebpf-plugins/kt_bpf_prog_load_private.pem \
        -out /etc/ml-defender/ebpf-plugins/kt_bpf_prog_load_public.pem

    # HMAC del .bpf.o — firmado con la clave del componente kernel-telemetry
    python3 scripts/sign_ebpf.py \
        --input  /usr/lib/ml-defender/ebpf/kt_bpf_prog_load.bpf.o \
        --key    /etc/ml-defender/kernel-telemetry/kt_private.pem \
        --output /etc/ml-defender/ebpf-plugins/kt_bpf_prog_load.bpf.o.hmac

    chmod 0600 /etc/ml-defender/ebpf-plugins/kt_bpf_prog_load_private.pem
    chmod 0600 /etc/ml-defender/ebpf-plugins/kt_bpf_prog_load.bpf.o.hmac
fi
```

**La clave HMAC nunca viaja en el JSON.** El JSON declara el path del objeto
y los parámetros de attach. La clave se deriva del intercambio de keypairs
durante el provisioning — nunca en texto claro en ningún fichero de configuración.

### Verificación en carga — dos capas

```
Capa 1 (build-time, ADR-015):
    HMAC del .bpf.o generado en compilación
    Verificado por kt_main.cpp antes de llamar a bpf_prog_load()

Capa 2 (provision-time, ADR-018):
    HMAC firmado por la clave privada del componente kernel-telemetry
    Verificado contra la clave pública registrada en provision.sh
    Un .bpf.o modificado post-provisioning no pasa esta verificación
```

Si cualquier capa falla → programa rechazado, evento CRITICAL al RAG,
`kernel-telemetry` continúa sin ese programa.

---

## EbpfPluginLoader — interfaz del gestor

Análogo a `PluginLoader` de ADR-012/017, pero para el stack eBPF:

```cpp
// ebpf_plugin_loader.hpp
#pragma once
#include <string>
#include <vector>
#include <memory>

namespace ml_defender {

// Contrato de identidad — común con ADR-017
// Los programas eBPF también implementan este contrato, pero en C puro
// expuesto por el componente kt_main.cpp, no por el programa .bpf.o
struct EbpfPluginIdentity {
    std::string name;
    std::string version;
    std::string component_type;   // siempre "kernel-telemetry"
    std::string subtype;          // "kprobe" | "tracepoint" | "xdp"
    std::string description;
};

struct EbpfPluginStats {
    std::string name;
    uint64_t    events_emitted    = 0;
    uint64_t    verification_fails = 0;
    uint64_t    budget_overruns   = 0;
    bool        attached          = false;
};

class EbpfPluginLoader {
public:
    explicit EbpfPluginLoader(const std::string& config_json_path);
    ~EbpfPluginLoader();

    // Carga, verifica HMAC, y hace attach de todos los programas habilitados
    // Si un programa falla verificación → CRITICAL log, continúa con los demás
    void load_and_attach();

    // Detach y unload de todos los programas
    void detach_and_unload();

    // Verifica periódicamente que los prog_id siguen siendo los originales
    // (complementa al watchdog de ADR-015)
    void verify_attached_programs();

    const std::vector<EbpfPluginStats>& stats() const;
    size_t loaded_count() const;

private:
    struct LoadedEbpfPlugin;
    std::vector<std::shared_ptr<LoadedEbpfPlugin>> plugins_;
    std::vector<EbpfPluginStats>                   stats_;
    std::string                                    config_path_;
    bool                                           shutdown_called_ = false;
};

}  // namespace ml_defender
```

---

## Contrato JSON del componente kernel-telemetry

```json
// kernel_telemetry.json
{
    "component": "kernel-telemetry",
    "version":   "1.0.0",
    "logging": {
        "level": "INFO",
        "file":  "/vagrant/logs/lab/kernel-telemetry.log"
    },
    "rag_endpoint": "http://localhost:8080/kernel-events",
    "response_mode": "ALERT_ONLY",
    "ebpf_plugins": {
        "directory":  "/usr/lib/ml-defender/ebpf",
        "pin_base":   "/sys/fs/bpf/ml-defender",
        "budget_ms":  5,
        "enabled": [
            "kt_bpf_prog_load_v1",
            "kt_memfd_v1",
            "kt_module_load_v1",
            "kt_ptrace_v1"
        ]
    }
}
```

El provisioning solo genera keypairs para los programas listados en `enabled`.
Un programa no listado no recibe keypair y no puede cargarse, aunque el .bpf.o
esté físicamente en el directorio.

---

## Estructura de directorios

```
kernel-telemetry/
    src/
        kt_main.cpp              — punto de entrada + EbpfPluginLoader
        kt_ebpf_plugin_loader.cpp
        kt_event_publisher.cpp   — publica JSON+HMAC al RAG
        kt_response_engine.cpp   — kill + detach
        kt_trust_chain.cpp       — verifica firmas (reutiliza ADR-015)
    bpf/
        kt_bpf_prog_load_v1.bpf.c
        kt_memfd_v1.bpf.c
        kt_module_load_v1.bpf.c
        kt_ptrace_v1.bpf.c
    config/
        kernel_telemetry.json
        ebpf-plugins/
            kt_bpf_prog_load_v1.json
            kt_memfd_v1.json
            kt_module_load_v1.json
            kt_ptrace_v1.json
    tests/
        test_ebpf_plugin_loader.cpp
        test_kt_hmac_verification.cpp
        test_kt_response_engine.cpp
    CMakeLists.txt
```

---

## Naming convention — ficheros .bpf.o

```
kt_{funcion}_{version}.bpf.o

Ejemplos:
    kt_bpf_prog_load_v1.bpf.o
    kt_memfd_v1.bpf.o
    kt_module_load_v1.bpf.o
    kt_ptrace_v1.bpf.o
```

Coherente con la convención `lib{familia}_{nombre}_v{N}.so` de ADR-017,
adaptada al mundo eBPF donde los ficheros son .bpf.o, no .so.

---

## Restricciones invariantes

1. **Verificación HMAC obligatoria** antes de cualquier `bpf_prog_load()`.
   Sin verificación → sin carga. Sin excepciones.

2. **La clave HMAC nunca en el JSON.** El JSON declara rutas y parámetros.
   Las claves viven en paths protegidos con permisos `0600`.

3. **Provisioning controla qué se carga.** Solo los programas declarados en
   `enabled` reciben keypair. Los demás no pueden autenticarse.

4. **Versionado estricto.** v1 y v2 tienen keypairs distintos. Actualizar
   un programa requiere re-provisioning explícito — no hay actualizaciones
   silenciosas.

5. **`response_mode` configurable.** `ALERT_ONLY` en desarrollo,
   `ACTIVE` en producción. Nunca hardcodeado.

6. **Fallo explícito, no silencioso.** Si un programa falla verificación,
   evento CRITICAL al RAG antes de continuar con los demás.

---

## Consecuencias

**Positivas:**
- Mismo modelo mental que ADR-017 pero adaptado al stack eBPF correcto
- Provisioning unificado — `provision.sh` gestiona componentes, plugins
  userspace y plugins eBPF con el mismo flujo de keypairs
- Auditabilidad — cada programa eBPF tiene su JSON, su HMAC y su keypair
  registrados en el provisioning
- Rollback trivial — cambiar `enabled` en el JSON y re-provisionar

**Negativas / limitaciones:**
- Requiere `CAP_BPF` y `CAP_SYS_ADMIN` para `kernel-telemetry` — AppArmor
  (ADR-019) limita el alcance de estos privilegios al proceso específico
- En VMs Vagrant el valor es limitado — brilla en bare-metal real
- Complejidad de mantenimiento: siete componentes + loader eBPF separado

---

## Relación con otros ADRs

| ADR | Relación |
|---|---|
| ADR-013 | `provision.sh` se extiende para generar keypairs de plugins eBPF |
| ADR-015 | Capa 1 de verificación (build-time HMAC) — ADR-018 añade Capa 2 (provision-time) |
| ADR-016 | Define los programas eBPF que este ADR gestiona |
| ADR-017 | Mismos principios (JSON is the law, fallo explícito, versionado) — mecanismo distinto |
| ADR-019 | AppArmor limita los privilegios de `kernel-telemetry` — prerequisito para producción |

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus NDR)*
*DAY 94 — 22 marzo 2026*