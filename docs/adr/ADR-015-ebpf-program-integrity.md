# ADR-015: FEAT-INFRA-1 — eBPF Program Integrity Verification

**Estado:** APROBADO — implementación inmediata (P1)
**Fecha:** 2026-03-21 (DAY 93)
**Autor:** Alonso Isidoro Román + Claude (Anthropic)
**Revisado por:** Consejo de Sabios — ML Defender (aRGus EDR)
**Componentes afectados:** sniffer, crypto-transport (lib existente), plugin-loader (futuro)
**Feature ID:** FEAT-INFRA-1
**CVE relacionado:** CVE-2026-1104 (io_uring UAF, LPE en kernel ≥ 6.12)

---

## Contexto

CVE-2026-1104 describe un Use-After-Free en el subsistema `io_uring` del kernel Linux
(≥ 6.12) explotable para Local Privilege Escalation (LPE) vía heap spray en
`kmalloc-256`. Un atacante que alcance Ring 0 mediante esta vulnerabilidad tiene
capacidad de:

1. **Sustituir el programa XDP** del sniffer por uno malicioso que filtre o manipule
   tráfico antes de que llegue al pipeline
2. **Cargar programas eBPF no firmados** desde espacio de usuario comprometido
3. **Cegar el detector** — el pipeline sigue funcionando aparentemente, pero procesa
   tráfico ya manipulado

El escenario es especialmente crítico porque la sustitución del programa XDP es
**silenciosa por defecto**: el kernel no valida la procedencia de un programa eBPF
si quien lo carga tiene los privilegios necesarios.

ML Defender ya dispone de HMAC-SHA256 en la librería `crypto-transport`. La extensión
de ese mecanismo al plano del kernel es la solución natural y de menor fricción.

### Superficie de ataque actual

```
Atacante (LPE via CVE-2026-1104)
    │
    ▼
bpf_prog_load()  ←── programa XDP malicioso
    │
    ▼
sniffer captura tráfico ya manipulado
    │
    ▼
Pipeline procesa datos envenenados — sin alertar
```

---

## Decisión

Implementar verificación de integridad en **tres capas complementarias**,
reutilizando la infraestructura criptográfica existente (`crypto-transport`):

### Capa 1 — Build-time: firma del bytecode eBPF

Durante el proceso de compilación (CMake post-build), generar el HMAC-SHA256
del fichero objeto XDP compilado y almacenarlo como constante en el binario
del sniffer:

```bash
# Integrado en CMakeLists.txt como custom_command post-build
python3 scripts/sign_ebpf.py \
    --input build/sniffer_xdp.o \
    --key   infra/keys/ebpf_signing.key \
    --output build/sniffer_xdp.o.hmac
```

El HMAC resultante se embebe en `sniffer.cpp` como constante verificable en
tiempo de compilación. La clave de firma vive en `infra/keys/` — nunca en el
repositorio público.

### Capa 2 — Load-time: verificación antes de `bpf_prog_load`

En `sniffer.cpp`, antes de cargar el programa XDP en el kernel:

```cpp
// Verificación load-time — usando crypto-transport existente
bool verify_ebpf_object(const std::string& path,
                         const std::string& expected_hmac,
                         const CryptoKey&   infra_key) {
    auto bytes  = read_file_bytes(path);
    auto actual = hmac_sha256(bytes, infra_key);

    if (!constant_time_compare(actual, expected_hmac)) {
        LOG_CRITICAL("[INFRA-1] eBPF object integrity FAILED — aborting load");
        LOG_CRITICAL("[INFRA-1] path={} expected={} actual={}",
                     path, expected_hmac, actual);
        publish_security_event("EBPF_INTEGRITY_VIOLATION_LOAD_TIME", path);
        return false;
    }
    LOG_INFO("[INFRA-1] eBPF object verified OK — {}", path);
    return true;
}
```

**Contrato de fallo:** si la verificación falla, el sniffer **no arranca**.
Publica el evento de seguridad vía ZeroMQ al bus del pipeline antes de terminar.
Nunca arranca en modo comprometido silencioso.

### Capa 3 — Runtime: watchdog del programa cargado

Una vez cargado el programa XDP, el kernel asigna un `prog_id` canónico.
Un hilo watchdog independiente verifica periódicamente que el programa
adjunto al interface sigue siendo el original:

```cpp
class EbpfIntegrityWatchdog {
    int expected_prog_id_;   // capturado en el momento del attach
    int ifindex_;            // interface donde está adjunto
    std::chrono::seconds interval_{30};  // configurable en sniffer.json

public:
    void run() {
        while (running_) {
            int current_id = get_xdp_prog_id(ifindex_);

            if (current_id != expected_prog_id_) {
                LOG_CRITICAL("[INFRA-1] XDP program replaced! "
                             "expected={} current={}",
                             expected_prog_id_, current_id);
                publish_security_event("EBPF_PROGRAM_REPLACED_RUNTIME",
                    { {"expected_id", expected_prog_id_},
                      {"current_id",  current_id},
                      {"ifindex",     ifindex_} });
                // Decisión arquitectónica: alertar y pausar — no reintentar
                // El operador debe intervenir — no hay auto-reparación silenciosa
                trigger_pipeline_alert_mode();
            }
            std::this_thread::sleep_for(interval_);
        }
    }
};
```

**Intervalo configurable** en `sniffer.json` bajo la clave
`"ebpf_watchdog_interval_seconds"` — por defecto 30s. Compatible con
el principio "JSON is the law" (ADR-003).

### Capa 3b — Plugin manifest para el plugin-loader futuro

Con la llegada del plugin-loader (post-arXiv), cada plugin eBPF se describe
en un manifiesto firmado:

```json
{
  "schema_version": "1.0",
  "plugins": [
    {
      "name":   "dns_dga_detector",
      "path":   "plugins/dns_dga.o",
      "hmac":   "a3f8c2...",
      "type":   "XDP",
      "author": "ML Defender Core Team"
    },
    {
      "name":   "threat_intel_feed",
      "path":   "plugins/threat_intel.o",
      "hmac":   "b7e1d9...",
      "type":   "tracepoint",
      "author": "ML Defender Core Team"
    }
  ],
  "manifest_hmac": "f2a4c8..."
}
```

El sniffer verifica el `manifest_hmac` antes de procesar cualquier entrada
individual. Si el manifiesto está comprometido, no se carga ningún plugin.

---

## Plan de implementación (TDD — Test Driven Hardening)

### Paso 1 — Test que demuestra la vulnerabilidad (RED)

```
tests/test_ebpf_integrity.cpp

- Caso A: carga un .o modificado (1 byte alterado) → pipeline acepta sin el fix
- Caso B: watchdog con prog_id incorrecto → pipeline no detecta sin el fix
```

El test documenta el problema antes de resolverlo. Pasa en estado rojo.

### Paso 2 — Fix (GREEN)

```
src/ebpf_integrity.hpp      — clase EbpfIntegrityVerifier + EbpfIntegrityWatchdog
src/sniffer.cpp             — integración: verify() en startup, watchdog en thread
scripts/sign_ebpf.py        — firma build-time
infra/keys/                 — claves de firma (no en repo público)
```

### Paso 3 — Validación completa

```
make test  →  todos los tests existentes + test_ebpf_integrity en verde
```

### Paso 4 — Documentación

```
docs/adr/ADR-015_ebpf_program_integrity.md  (este fichero)
docs/CHANGELOG.md                            — entrada DAY 93
```

---

## Acceptance Criteria

| Criterio | Verificación |
|---|---|
| `.o` modificado en 1 byte → sniffer no arranca | `test_ebpf_integrity::load_tampered_object` |
| `.o` original → sniffer arranca correctamente | `test_ebpf_integrity::load_valid_object` |
| prog_id sustituido → evento `EBPF_PROGRAM_REPLACED_RUNTIME` publicado | `test_ebpf_integrity::watchdog_detects_replacement` |
| Evento publicado **antes** de cualquier acción de mitigación | Log timestamp ordering |
| `sniffer.json` respeta intervalo configurable del watchdog | `test_ebpf_integrity::watchdog_respects_config` |
| Todos los tests previos siguen en verde | `make test` completo |

---

## Consecuencias

**Positivas:**
- Cierra el vector de ataque post-LPE más crítico para el pipeline: sustitución
  silenciosa del programa XDP
- Reutiliza `crypto-transport` existente — sin dependencias nuevas en producción
- Establece la cadena de confianza (trust chain) que FEAT-INFRA-2 extiende
- Contribución de seguridad documentable en el preprint arXiv v2: arquitectura
  que se autoprotege en la capa de kernel
- Compatible con hot-reload seguro (ENT-4) — el manifiesto de plugins es
  su contrato de integridad

**Negativas / limitaciones:**
- La Capa 1 (build-time) requiere gestión de claves de firma — añade un paso
  al proceso de build y despliegue
- El watchdog consume un hilo adicional — costo despreciable en práctica
- Un atacante con acceso físico al sistema puede reemplazar también la clave
  de firma — fuera del modelo de amenaza de FEAT-INFRA-1 (eso es FEAT-INFRA-2)
- No protege contra ataques que ocurran **dentro** del intervalo del watchdog
  (mitigación: intervalo corto + FEAT-INFRA-2 para detección en tiempo real)

---

## Relación con otras decisiones

- **ADR-003** (JSON is the law): intervalo del watchdog configurable en `sniffer.json`
- **ADR-004** (HMAC key rotation): las claves de firma eBPF siguen el mismo
  ciclo de vida que las claves de transporte
- **ADR-007** (AND-consensus): la integridad del sniffer es prerequisito para
  que el consenso tenga sentido — un sniffer comprometido envenena ambos paths
- **ADR-016** (FEAT-INFRA-2): este ADR establece la cadena de confianza que
  FEAT-INFRA-2 extiende al plano de telemetría de kernel en tiempo real
- **ENT-4** (hot-reload): el plugin manifest de Capa 3b es el contrato de
  integridad del hot-reload

---

## Referencias

- CVE-2026-1104: io_uring Use-After-Free, LPE en kernel ≥ 6.12
- `src/crypto/crypto_transport.hpp` — HMAC-SHA256 existente
- `config/sniffer.json` — configuración del sniffer
- `docs/experiments/f1_replay_log.csv` — source of truth de métricas
- ADR-003: JSON is the law
- ADR-004: HMAC key rotation con cooldown
- ADR-007: AND-consensus scoring
- ADR-016: FEAT-INFRA-2 eBPF Runtime Kernel Telemetry (complementario)
- Conversación de diseño: DAY 93 (2026-03-21)

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus EDR)*
*DAY 93 — 21 marzo 2026*