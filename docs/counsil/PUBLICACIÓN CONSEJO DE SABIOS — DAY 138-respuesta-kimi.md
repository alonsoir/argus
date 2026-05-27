## Kimi — Respuesta al Consejo de Sabios — DAY 138

*Evaluación bajo criterios de lifetime safety, semántica de backpressure, atomicidad de aislamiento de red, y viabilidad de port a microkernels formales.*

---

### [Q1] — Arquitectura `PcapCallbackData` vs alternativas

**Hipótesis:** El lifetime de `PcapCallbackData` está ligado a la instancia de `PcapBackend`, pero `pcap_dispatch` puede ser reentrante en ciertos escenarios de error.

**Veredicto: La garantía es suficiente para el caso de uso actual, pero incompleta para escenarios de señalización asíncrona.**

**Análisis de lifetime:**

```cpp
// Estado actual
struct PcapCallbackData {
    PacketCallback cb;
    void* ctx;
};

class PcapBackend {
    PcapCallbackData callback_data_;  // Miembro, lifetime = instancia
    pcap_t* handle_;
    
    int poll(int timeout_ms) override {
        return pcap_dispatch(handle_, 64, pcap_packet_handler, 
                           reinterpret_cast<u_char*>(&callback_data_));
    }
};
```

**Escenarios de riesgo:**

| Escenario | ¿Riesgo? | Justificación |
|-----------|----------|---------------|
| `pcap_dispatch` síncrono normal | No | `callback_data_` vive en stack de `poll()`, no hay reentrancia |
| `pcap_dispatch` con timeout y señal `SIGALRM` | **Sí** | Si un signal handler interrumpe `pcap_dispatch` y el destructor de `PcapBackend` se ejecuta en otro hilo, `callback_data_` es destruida mientras `pcap_packet_handler` aún la referencia |
| `pcap_breakloop` desde otro hilo | **Sí** | `pcap_breakloop` no garantiza que `pcap_dispatch` retorne inmediatamente; el handler puede ejecutarse durante la ventana de cierre |

**Recomendación: Añadir weak_ptr semántico al contexto:**

```cpp
// Opción A: shared_ptr al contexto (más seguro, overhead mínimo)
struct PcapCallbackData {
    std::weak_ptr<void> ctx_weak;  // En lugar de void* crudo
    PacketCallback cb;
};

static void pcap_packet_handler(u_char* user, 
                                const struct pcap_pkthdr* hdr,
                                const u_char* data) {
    auto* cb_data = reinterpret_cast<PcapCallbackData*>(user);
    
    // Verificar que el contexto sigue vivo
    if (auto ctx_shared = cb_data->ctx_weak.lock()) {
        cb_data->cb(ctx_shared.get(), hdr, data);
    } else {
        // Contexto destruido — dropear paquete silenciosamente
        // Esto ocurre durante shutdown ordenado
    }
}
```

**Para DAY 138-139:** La versión actual con `void*` es aceptable porque:
1. `PcapBackend` no expone `pcap_dispatch` a múltiples hilos
2. El shutdown es síncrono (`close()` llama `pcap_breakloop()` antes de destruir)
3. No hay signals asíncronos en el diseño actual

**Acción:** Documentar la limitación en `pcap_backend.hpp`:

```cpp
// LIFETIME CONTRACT: PcapCallbackData is valid for the duration of 
// pcap_dispatch() call. Do not destroy PcapBackend during active 
// pcap_dispatch(). This is guaranteed by the synchronous design 
// of poll() → dispatch → return. Async signal-based interruption 
// is not supported and would require weak_ptr refactoring.
```

---

### [Q2] — Wire format: `dontwait` vs bloqueante

**Hipótesis:** En un sistema monohilo, el descarte silencioso de paquetes bajo presión es preferible al bloqueo, pero debe ser observable y limitado.

**Veredicto: `dontwait` es correcto para Variant B monohilo, pero requiere métrica de presión expuesta.**

**Análisis de backpressure:**

| Política | Pros | Contras | Adecuado para |
|----------|------|---------|---------------|
| `dontwait` (actual) | No bloquea captura, latencia predecible | Pérdida de paquetes bajo presión | Monohilo, tiempo real |
| Bloqueante (`wait`) | Zero packet loss (por ZMQ) | Bloquea `pcap_dispatch`, kernel dropa paquetes en NIC | Multihilo con buffer |
| Sleep + retry | Compromiso | Latencia impredecible, complejidad | No recomendado |

En Variant B monohilo, `dontwait` es la única opción viable porque:
- `pcap_dispatch` corre en el hilo principal
- Si bloquea, el kernel no puede entregar más paquetes desde la NIC
- El kernel dropa en la NIC ring buffer, no en userspace
- Es preferible drop controlado en ZMQ (con contador) que drop silencioso en kernel

**Recomendación: Exponer métrica de presión:**

```cpp
// En PcapBackend::stats() o en el mensaje de status ZMQ
struct PcapPressureMetrics {
    uint64_t packets_captured;
    uint64_t packets_dropped_by_zmq;  // send() con dontwait falló
    uint64_t packets_dropped_by_kernel;  // pcap_stats() ps_drop
    uint64_t packets_dropped_by_interface;  // pcap_stats() ps_ifdrop
    double drop_rate_1m;  // Rolling window
};
```

**Criterio de alerta:** Si `drop_rate_1m > 0.1%` durante 60 segundos, el sistema está saturado. El admin debe:
- Reducir la carga de análisis (ej. samplear 1 de cada N paquetes)
- Aumentar recursos (no aplicable en monohilo)
- Escalar a Variant A (XDP) si el hardware lo soporta

**Para el paper:** Documentar que la política de descarte en Variant B es **intencional y observable**, no un bug. La transparencia del descarte es una propiedad de diseño.

---

### [Q3] — `sniffer-libpcap.json`: campos a preservar vs eliminar

**Hipótesis:** La configuración de Variant B debe ser minimalista, reflejando la simplicidad del backend.

**Veredicto: Eliminar todo lo relacionado con multihilo, ring buffers, y eBPF. Preservar networking, criptografía y logging. Añadir campo de sampleo.**

**Campos a eliminar (confirmados):**

| Campo | Razón de eliminación |
|-------|---------------------|
| `zmq_sender_threads` | Variant B es monohilo |
| `io_thread_pools` | No hay thread pool |
| `ring_buffer.*` | No hay ring buffer de eBPF |
| `ebpf.*` | No hay eBPF |
| `xdp.*` | No hay XDP |

**Campos a preservar:**

| Campo | Justificación |
|-------|---------------|
| `capture.interface` | Obligatorio |
| `capture.filter.*` | BPF filter de libpcap |
| `output_socket.address/port` | ZMQ endpoint |
| `crypto.*` | HKDF + ChaCha20-Poly1305 |
| `logging.*` | Nivel de log, rotación |

**Campo a añadir (Variant B específico):**

```json
{
  "capture": {
    "interface": "eth1",
    "filter": {
      "expression": "tcp or udp",
      "optimize": true
    },
    "sampling": {
      "mode": "none",        // "none", "count_based", "time_based"
      "rate": 1.0            // 1.0 = 100%, 0.1 = 10% para alta carga
    }
  }
}
```

**Justificación del sampleo:** En un RPi4 a 100 Mbps, procesar todos los paquetes puede saturar la CPU. Un modo de sampleo permite operación degradada pero funcional bajo carga inesperada.

**Campos de Variant A que Variant B NO necesita pero que podrían parecer necesarios:**

- `capture.promiscuous`: libpcap siempre abre en promiscuo si el filtro lo requiere. No es configurable.
- `capture.snaplen`: libpcap usa `65535` por defecto. No configurable salvo necesidad específica.

---

### [Q4] — Test e2e: estrategia para dev VM sin tráfico real

**Hipótesis:** Los tests e2e deben ser reproducibles sin dependencia de infraestructura de red externa.

**Veredicto: Estrategia híbrida — `pcap_open_dead()` + `pcap_inject()` para tests unitarios de pipeline; `tcpreplay` sobre `lo` para tests de integración con tráfico real.**

**Implementación propuesta:**

```cpp
// test_pcap_backend_e2e.cpp

TEST(PcapBackendE2E, FullPipelineWithSyntheticTraffic) {
    // 1. Crear pcap handle en modo "dead" (no requiere root, no requiere interfaz)
    pcap_t* dead_handle = pcap_open_dead(DLT_EN10MB, 65535);
    ASSERT_NE(dead_handle, nullptr);
    
    // 2. Inyectar frames sintéticos
    std::vector<uint8_t> synthetic_frame = build_tcp_syn_packet(
        "10.0.0.1", 12345, "10.0.0.2", 80
    );
    
    struct pcap_pkthdr hdr;
    hdr.ts.tv_sec = time(nullptr);
    hdr.ts.tv_usec = 0;
    hdr.caplen = synthetic_frame.size();
    hdr.len = synthetic_frame.size();
    
    // 3. Usar pcap_dispatch con un callback que alimenta el backend
    // (requiere refactor menor para permitir inyección manual)
    
    // 4. Verificar que el paquete llega a ml-detector vía ZMQ
    zmq::socket_t receiver(context, zmq::socket_type::pull);
    receiver.connect("tcp://127.0.0.1:5572");  // ml-detector output
    
    // 5. Timeout de 5s para recibir
    zmq::message_t msg;
    ASSERT_TRUE(receiver.recv(msg, zmq::recv_flags::dontwait));
    
    NetworkSecurityEvent event;
    ASSERT_TRUE(event.ParseFromArray(msg.data(), msg.size()));
    EXPECT_EQ(event.src_ip(), "10.0.0.1");
}
```

**Para tests con tráfico real (requiere root):**

```bash
# test_e2e_real_traffic.sh — ejecutado manualmente, no en CI
sudo tcpreplay -i lo -t -K cic-ids-2017-sample.pcap &
./sniffer-libpcap lo &
./ml-detector &
# Verificar que ml-detector emite alertas
```

**Recomendación:** Los tests automatizados (`make test-all`) usan `pcap_open_dead`. Los tests manuales de validación usan `tcpreplay`. Esto separa reproducibilidad (CI) de realismo (validación humana).

---

### [Q5] — `DEBT-IRP-NFTABLES-001`: atomicidad de `argus-network-isolate`

**Hipótesis:** El aislamiento de red debe ser atómico para evitar estados intermedios donde el atacante tiene acceso parcial.

**Veredicto: Enfoque transaccional con `nft -f` + rollback automático via timeout. No iptables mangle (revisión anterior DAY 136 superada).**

**Justificación del cambio a nftables:**

iptables es **obsoleto** en Debian 12+ (bookworm). nftables es el backend por defecto. Usar iptables en un sistema moderno introduce:
- Dependencia de `iptables-legacy` o `iptables-nft` (wrapper)
- Inconsistencias si nftables ya tiene reglas
- Performance inferior en reglas complejas

**Arquitectura transaccional propuesta:**

```bash
# /usr/local/bin/argus-network-isolate
#!/bin/bash
set -euo pipefail

NFT_FILE="/tmp/argus-isolate-$$.nft"
ROLLBACK_FILE="/tmp/argus-isolate-rollback-$$.nft"

# 1. Generar reglas de aislamiento atómicas
cat > "$NFT_FILE" <<'EOF'
table inet argus_isolate {
    chain input {
        type filter hook input priority 0; policy drop;
        # Solo permitir loopback
        iif "lo" accept
        # Denegar todo lo demás
        drop
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
    }
    chain output {
        type filter hook output priority 0; policy drop;
        # Permitir solo tráfico al endpoint de notificación (best-effort)
        ip daddr 192.168.56.1 tcp dport 443 accept
        # Denegar todo lo demás
        drop
    }
}
EOF

# 2. Generar rollback (restaurar política accept)
cat > "$ROLLBACK_FILE" <<'EOF'
table inet argus_isolate {
    chain input { policy accept; }
    chain forward { policy accept; }
    chain output { policy accept; }
    delete table inet argus_isolate
}
EOF

# 3. Aplicar con atomicidad nftables
if nft -f "$NFT_FILE"; then
    logger -p auth.crit "ARGUS IRP: network isolated via nftables"
    # 4. Programar rollback automático en 300s si no se confirma
    (sleep 300 && nft -f "$ROLLBACK_FILE" 2>/dev/null || true) &
else
    logger -p auth.crit "ARGUS IRP: nftables isolation FAILED — system remains exposed"
    exit 1
fi
```

**Rollback automático (safety net):** Si el admin no confirma el aislamiento en 5 minutos, las reglas se revierten. Esto evita que un bug en `argus-network-isolate` deje el nodo permanentemente inaccesible.

**Rollback manual:**

```bash
argus-network-restore  # Aplica ROLLBACK_FILE inmediatamente
```

**Atomicidad garantizada:** `nft -f` aplica todo el fichero como una transacción. Si cualquier regla es inválida, ninguna se aplica.

**Riesgo:** Si el proceso muere a mitad de `nft -f`, la transacción ya está completa (es atómica) o no se ha aplicado nada. No hay estado intermedio.

---

### [Q6] — `DEBT-COMPILER-WARNINGS-CLEANUP-001`: prioridad ODR

**Hipótesis:** Las ODR violations son las únicas warnings que pueden causar comportamiento indefinido en producción.

**Veredicto: ODR es P0 bloqueante. Las demás son P1. La causa probable es inline definitions en headers compartidos entre translation units con diferentes flags de compilación.**

**Análisis de ODR en aRGus:**

Las ODR violations (`InternalNode`/`TrafficNode`) típicamente ocurren cuando:

1. **Una clase definida en header** se incluye en dos `.cpp` con diferentes flags
    - Ej: `ml-detector` compila con `-O3 -DNDEBUG`, `sniffer` con `-O2 -DDEBUG`
    - El layout de la clase puede diferir si depende de macros condicionales

2. **Una clase con métodos inline** se define en header pero el cuerpo depende de macros
    - Ej: `InternalNode::compute()` usa `#ifdef DEBUG` para logging adicional
    - Dos TUs ven diferentes cuerpos para el mismo símbolo

3. **Protobuf generado en múltiples TUs** con diferentes versiones del compilador protobuf

**Diagnóstico recomendado:**

```bash
# 1. Identificar símbolos ODR violados
nm -C dist/x86/argus-ml-detector | grep "InternalNode" | c++filt
nm -C dist/x86/argus-sniffer | grep "InternalNode" | c++filt

# 2. Verificar que los layouts coinciden
# Compilar con -fdump-lang-class y comparar
g++ -fdump-lang-class -c src/ml-detector/internal_node.cpp -o /tmp/odr_check.o
g++ -fdump-lang-class -c src/sniffer/traffic_node.cpp -o /tmp/odr_check2.o
diff /tmp/internal_node.cpp.class /tmp/traffic_node.cpp.class

# 3. Si son la misma clase, verificar flags de compilación
# Si son clases diferentes con mismo nombre, renombrar una
```

**Experiencia con ODR en sistemas protobuf:**

En sistemas con protobuf + múltiples TUs, la causa más común es:
- `protoc` genera código con `inline` en métodos de acceso
- Dos TUs incluyen el mismo `.pb.h` pero con diferentes `-DGOOGLE_PROTOBUF_NO_RTTI` o similares
- El layout de `google::protobuf::Message` difiere

**Fix recomendado:**

```cmake
# CMakeLists.txt — forzar flags idénticos para todas las TUs que comparten headers
set(COMMON_FLAGS "-O2 -DNDEBUG -fPIC")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${COMMON_FLAGS}")

# ODR-safe: nunca usar macros condicionales en headers compartidos
# Si DEBUG logging es necesario, usar runtime check:
inline void InternalNode::log_debug(const std::string& msg) {
#ifdef DEBUG
    if (debug_enabled_) {  // Runtime, no compile-time
        spdlog::debug(msg);
    }
#endif
}
```

**Acción inmediata:** Crear `fix/odr-violations-001` y:
1. Identificar todos los símbolos ODR violados (`nm + c++filt`)
2. Determinar si son la misma clase (renombrar si no) o flags diferentes (unificar si sí)
3. Añadir `-Werror=odr` al compilador si la versión lo soporta (GCC 10+, Clang 12+)

---

### [Q7] — Threading model: ARM64 + seL4 a largo plazo

**Hipótesis:** seL4 es un microkernel formalmente verificado donde el modelo de ejecución es capabilities + IPC síncrona, incompatible con pthreads y memoria compartida.

**Veredicto: Es prematuro diseñar para seL4 ahora. La arquitectura actual es lo suficientemente desacoplada para que el port sea viable sin reescribir todo.**

**Análisis de reutilizabilidad:**

| Componente actual | Reutilizable en seL4 | Esfuerzo de port |
|-------------------|---------------------|------------------|
| `CaptureBackend` (interfaz) | **Sí** — 100% | Nulo — la interfaz es agnóstica de threading |
| `PcapBackend` | **Parcial** — lógica de parseo sí, libpcap no | Medio — seL4 no tiene networking stack; necesita driver NIC en userspace |
| `CryptoTransport` | **Parcial** — algoritmos sí (libsodium/ChaCha20), threading no | Bajo — ChaCha20 es stateless, no requiere threads |
| `ZeroMQ` | **No** — ZMQ requiere sockets BSD + threads | Alto — reemplazar por IPC de seL4 (seL4CP o CAmkES) |
| `Protobuf` | **Sí** — si se compila sin threading | Bajo — `protobuf-lite` + `-DGOOGLE_PROTOBUF_NO_THREAD_SAFETY` |
| `ONNX Runtime` | **No** — requiere threads para intra-op parallelism | Muy alto — reescritura con seL4 threads o single-threaded inference |

**Recomendación: No diseñar para seL4 ahora, pero mantener la interfaz `CaptureBackend` pura.**

La interfaz `CaptureBackend` con 5 métodos puros (`open`, `poll`, `close`, `get_fd`, `get_packet_count`) es perfectamente portable a seL4 porque:
- No menciona `std::thread`
- No menciona `std::mutex`
- No menciona memoria compartida
- `poll()` puede implementarse con `seL4_Wait()` en lugar de `pcap_dispatch()`

**Lo que NO debe hacerse ahora:**
- Añadir abstracciones de "threading" a `CaptureBackend`
- Añadir `async`/`future` al pipeline
- Dependender de `std::atomic` en interfaces públicas

**Lo que SÍ debe mantenerse:**
- Monohilo como default (ya es el caso de Variant B)
- Callbacks en lugar de polling bloqueante (ya es el caso)
- Serialización explícita en lugar de memoria compartida (ya es el caso con ZMQ/Protobuf)

**Conclusión:** La arquitectura actual es **accidentalmente compatible** con seL4. No es necesario diseñar explícitamente para ello, solo **no romper** la compatibilidad añadiendo threading implícito.

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **Q1** | `PcapCallbackData` suficiente con documentación de lifetime contract | Añadir comentario explícito de contrato; considerar `weak_ptr` si se añade threading posterior |
| **Q2** | `dontwait` correcto; exponer métrica de presión | Añadir `PcapPressureMetrics` a stats; alerta si drop_rate > 0.1% |
| **Q3** | Eliminar multihilo/eBPF; preservar networking/crypto/logging; añadir `sampling` | Implementar `sniffer-libpcap.json` con campo `sampling` |
| **Q4** | Híbrido: `pcap_open_dead` para CI, `tcpreplay` para validación manual | Implementar test e2e con inyección sintética |
| **Q5** | nftables transaccional con `nft -f`; rollback automático 300s | Crear `argus-network-isolate` con nftables; rechazar iptables |
| **Q6** | ODR es P0 bloqueante; diagnosticar con `nm + c++filt`; unificar flags | Crear rama `fix/odr-violations-001`; añadir `-Werror=odr` si disponible |
| **Q7** | No diseñar para seL4 ahora; mantener monohilo y callbacks | Documentar que la arquitectura es "seL4-compatible by design" sin añadir complejidad |

**Moción:** Propongo que el DAY 139 ejecute en paralelo:
1. **Track A:** `DEBT-VARIANT-B-CONFIG-001` (JSON propio + sampling + test e2e sintético)
2. **Track B:** `fix/odr-violations-001` (diagnóstico + unificación de flags)

El Track B es bloqueante para cualquier tag posterior a v0.6.0 porque las ODR violations pueden manifestarse como corrupción silenciosa en la hardened VM. No debe posponerse.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*