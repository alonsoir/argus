# ADR-016: FEAT-INFRA-2 — eBPF Runtime Kernel Telemetry

**Estado:** PROPUESTO — implementación post bare-metal stress test (P2)
**Fecha:** 2026-03-21 (DAY 93)
**Autor:** Alonso Isidoro Román + Claude (Anthropic)
**Revisado por:** Consejo de Sabios — ML Defender (aRGus EDR)
**Componentes afectados:** nuevo componente `kernel-telemetry` (séptimo componente del pipeline)
**Feature ID:** FEAT-INFRA-2
**Dependencias:** ADR-015 (FEAT-INFRA-1) — prerequisito obligatorio

---

## Contexto

FEAT-INFRA-1 (ADR-015) establece la verificación de integridad del programa eBPF
en load-time y mediante watchdog periódico. Sin embargo, un atacante sofisticado
que ya ha alcanzado Ring 0 puede operar **entre intervalos del watchdog**, o puede
comprometer el hardware antes de que el sniffer arranque.

FEAT-INFRA-2 aborda la **última línea de defensa del pipeline**: observar el
kernel en tiempo real desde dentro del kernel, detectar programas eBPF no
firmados en el momento exacto de su carga, y responder de forma autónoma
antes de que el programa malicioso capture su primer paquete.

### Diferencia arquitectónica clave respecto al pipeline principal

El pipeline principal (protobuf → ZeroMQ → ml-detector) está diseñado para
**proteger la red**. `kernel-telemetry` está diseñado para **proteger el
hardware y el pipeline mismo**. Son responsabilidades ortogonales que requieren
canales separados:

```
[Pipeline principal — protege la RED]
eBPF/XDP → protobuf → ZeroMQ → ml-detector → firewall-acl-agent

[Canal de autodefensa — protege EL HARDWARE]
eBPF Tracing → JSON+HMAC → RAG directamente (evento de primer nivel)
```

El contrato protobuf no se toca. El canal de autodefensa tiene su propio
schema, más liviano y orientado a respuesta inmediata, no a análisis ML.

### Por qué conectar directamente al RAG

- Los eventos de kernel son **evidencia forense primaria** — deben persistir
  en el índice RAG antes de cualquier acción de mitigación
- El ml-detector está en la cadena de confianza que podría estar comprometida
  — no se puede enrutar evidencia de compromiso a través del sistema comprometido
- La latencia de respuesta debe ser mínima — cada milisegundo entre detección
  y kill es una ventana de ataque

---

## Decisión

Implementar un séptimo componente del pipeline, `kernel-telemetry`, consistente
en un programa eBPF de tipo `kprobe`/`tracepoint` que:

1. **Observa** la carga de programas eBPF en tiempo real
2. **Verifica** la firma de cada programa en el momento de su carga
3. **Notifica** al RAG mediante evento directo (JSON + HMAC)
4. **Actúa** — kill del proceso propietario y detach del programa malicioso

### Flujo de respuesta ante programa eBPF no firmado

```
bpf_prog_load() detectado por kprobe
        │
        ▼
¿Está firmado? (verificar contra trust chain de ADR-015)
        │
    NO──┘
        │
        ▼
1. NOTIFY → rag-security (evento directo, JSON+HMAC)
        │           evidencia persiste ANTES de actuar
        ▼
2. KILL → kill(owning_pid, SIGKILL)
        │           proceso propietario eliminado
        ▼
3. DETACH → bpf_link_detach() + cierre del fd
                    programa malicioso eliminado del kernel
```

**Invariante de diseño:** la notificación siempre precede a la acción.
Si el kill o el detach fallan, el evento ya está en RAG con toda la evidencia.
La verdad por delante — siempre.

---

## Schema del evento directo a RAG

Los eventos de `kernel-telemetry` no usan protobuf. Usan JSON firmado con
HMAC-SHA256 (misma librería crypto-transport, instancia independiente):

```json
{
  "schema_version": "1.0",
  "event_type":     "UNSIGNED_EBPF_DETECTED",
  "timestamp_ns":   1742551234567890123,
  "severity":       "CRITICAL",
  "prog_id":        42,
  "prog_type":      "XDP",
  "attached_to":    "eth0",
  "owning_pid":     1337,
  "owning_comm":    "malicious_proc",
  "owning_uid":     0,
  "load_flags":     "BPF_F_ANY_ALIGNMENT",
  "action_taken":   "KILLED_AND_DETACHED",
  "action_result":  "SUCCESS",
  "hmac":           "a3f8c2d1e4b5..."
}
```

El campo `action_result` puede ser `SUCCESS`, `KILL_FAILED`, `DETACH_FAILED`,
o `PARTIAL` — el RAG registra el resultado real, no el esperado.

---

## Eventos de telemetría capturados

`kernel-telemetry` no se limita a programas eBPF. Captura señales de ataque
observables en el kernel que complementan la detección de red del pipeline principal:

| Evento | Kprobe / Tracepoint | Relevancia |
|---|---|---|
| Carga de programa eBPF no firmado | `kprobe/bpf_prog_load` | Vector de ataque primario |
| `memfd_create` + `fexecve` | `tracepoint/syscalls/sys_enter_memfd_create` | Ejecución en memoria sin disco |
| Acceso a `/proc/self/maps` | `tracepoint/syscalls/sys_enter_openat` | Userland unhooking |
| Carga de módulo kernel | `tracepoint/module/module_load` | Rootkit detection |
| `ptrace` sobre procesos del pipeline | `tracepoint/syscalls/sys_enter_ptrace` | Anti-debugging / evasión |
| Fork bomb / resource exhaustion | `tracepoint/sched/sched_process_fork` | DoS sobre el propio pipeline |

Cada evento genera una entrada RAG independiente con el schema descrito arriba
y su propio `event_type`.

---

## Arquitectura del séptimo componente

```
kernel-telemetry/
    src/
        kt_main.cpp              — punto de entrada, gestión del ciclo de vida
        kt_ebpf_loader.cpp       — carga y gestiona los programas BPF de tracing
        kt_event_publisher.cpp   — publica eventos JSON+HMAC al RAG
        kt_response_engine.cpp   — ejecuta kill + detach
        kt_trust_chain.cpp       — verifica firmas (reutiliza ADR-015)
    bpf/
        kt_bpf_prog_load.bpf.c   — kprobe en bpf_prog_load
        kt_memfd.bpf.c            — tracepoint memfd_create
        kt_module_load.bpf.c      — tracepoint module_load
        kt_ptrace.bpf.c           — tracepoint ptrace
    config/
        kernel_telemetry.json    — configuración (intervalo, umbrales, trust chain path)
    tests/
        test_kt_unsigned_ebpf.cpp
        test_kt_memfd_detection.cpp
        test_kt_response_engine.cpp
```

### Conexión directa al RAG

`kernel-telemetry` no pasa por ZeroMQ del pipeline principal. Escribe
directamente en el endpoint HTTP del `rag-ingester` (o en su socket UNIX
si se configura para evitar dependencia de red):

```cpp
// kt_event_publisher.cpp
void publish_to_rag(const KernelEvent& event) {
    auto json_payload = event.to_json_hmac_signed();

    // Canal directo — no pasa por ml-detector ni por el bus ZMQ principal
    rag_client_.post("/kernel-events", json_payload);

    LOG_INFO("[KT] Evento publicado al RAG: type={} pid={}",
             event.type, event.owning_pid);
}
```

---

## Acceptance Criteria

| Criterio | Verificación |
|---|---|
| Programa eBPF no firmado → evento `UNSIGNED_EBPF_DETECTED` en RAG antes del kill | Timestamp ordering en test |
| Kill del proceso propietario ejecutado tras notificación | `test_kt_response_engine::kill_after_notify` |
| Detach del programa malicioso ejecutado tras kill | `test_kt_response_engine::detach_after_kill` |
| `memfd_create` + `fexecve` detectados y reportados | `test_kt_memfd_detection` |
| Evento con `action_result: KILL_FAILED` si el proceso ya terminó | `test_kt_response_engine::graceful_on_race` |
| `kernel_telemetry.json` respeta configuración | `test_kt_config` |
| Todos los tests previos del pipeline siguen en verde | `make test` completo |

---

## Consecuencias

**Positivas:**
- Convierte ML Defender en un sistema que **se defiende a sí mismo** — no solo
  a la red que monitoriza
- Respuesta autónoma en tiempo real — detecta y neutraliza antes del primer
  paquete capturado por el programa malicioso
- Canal forense independiente — la evidencia llega al RAG aunque el pipeline
  principal esté comprometido
- Contribución académica diferenciada para USENIX Security / NDSS: arquitectura
  de autoprotección desde el kernel como séptimo componente
- Detecta técnicas de evasión de EDR modernas (`memfd_create`, userland
  unhooking) que son invisibles para los detectores de red tradicionales

**Negativas / limitaciones:**
- Requiere privilegios `CAP_BPF` y `CAP_SYS_ADMIN` — eleva la superficie de
  ataque del propio `kernel-telemetry` si se compromete
- La respuesta automática (kill + detach) puede producir falsos positivos en
  entornos de desarrollo — debe ser configurable (modo ALERT-ONLY vs ACTIVE)
- La latencia entre kprobe y respuesta introduce una ventana pequeña pero real
- En VMs Vagrant el valor es limitado — **brilla en bare-metal real**,
  que es el entorno objetivo post bare-metal stress test
- Complejidad de mantenimiento: siete componentes en lugar de seis

**Modos de operación (configurable en `kernel_telemetry.json`):**

```json
{
  "response_mode": "ACTIVE",
  "comment": "ALERT_ONLY | ACTIVE — usar ALERT_ONLY en desarrollo"
}
```

---

## Relación con otras decisiones

- **ADR-015** (FEAT-INFRA-1): prerequisito obligatorio — la trust chain de
  firmas eBPF que FEAT-INFRA-1 establece es la base de verificación que
  `kernel-telemetry` usa en tiempo real
- **ADR-003** (JSON is the law): configuración en `kernel_telemetry.json`
- **ADR-004** (HMAC key rotation): las claves de firma de eventos siguen
  el mismo ciclo de vida que las claves de transporte
- **ADR-010** (Confined LLM): los eventos de kernel son consultables por
  rag-security como cualquier otro evento indexado — el confinamiento
  del LLM aplica igualmente

---

## Referencias

- ADR-015: FEAT-INFRA-1 eBPF Program Integrity Verification (prerequisito)
- ADR-003: JSON is the law
- ADR-004: HMAC key rotation con cooldown
- ADR-010: Confined LLM skills registry
- CVE-2026-1104: io_uring Use-After-Free — motivación original
- Linux BPF documentation: `bpf_prog_load`, `bpf_link_detach`
- `libbpf` — librería de carga de programas eBPF en espacio de usuario
- Conversación de diseño: DAY 92–93 (2026-03-20/21)

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus EDR)*
*DAY 93 — 21 marzo 2026*