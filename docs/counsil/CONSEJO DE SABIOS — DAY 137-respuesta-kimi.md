## Kimi — Respuesta al Consejo de Sabios — DAY 137

*Evaluación bajo criterios de diseño de interfaces, principio de segregación de responsabilidades, y viabilidad de la arquitectura para contribución científica publicable.*

---

### Veredicto sobre la interfaz `CaptureBackend`

**La interfaz abstracta actual es técnicamente funcional pero arquitectónicamente impura.** Mantener `attach_skb()`, `get_ringbuf_fd()` y filter map fds en la interfaz base viola el **Principio de Segregación de Interfaces (ISP)** y introduce acoplamiento semántico innecesario. Sin embargo, la razón dada (evitar downcast en `main.cpp`) es válida pero resoluble de forma más elegante.

**Recomendación: Refactorizar a dos interfaces separadas con composición, no herencia plana.**

---

### Análisis del problema

**Estado actual (impuro):**

```cpp
class CaptureBackend {
public:
    virtual ~CaptureBackend() = default;
    
    // Métodos comunes a ambas variantes
    virtual bool init(const std::string& iface) = 0;
    virtual void shutdown() = 0;
    
    // Métodos específicos de eBPF/XDP — no-op en libpcap
    virtual bool attach_skb(int fd) { return true; }  // No-op default: olor a diseño roto
    virtual int get_ringbuf_fd() const { return -1; }  // -1 como sentinel: olor a diseño roto
    virtual int get_filter_map_fd() const { return -1; }  // Igual
    
    // ... más métodos comunes
};
```

**Problemas identificados:**

| Problema | Impacto | Ejemplo concreto |
|----------|---------|------------------|
| **Semántica contaminada** | Un `PcapBackend` que "soporta" `attach_skb()` es una mentira de tipos | `backend->attach_skb(fd)` en `PcapBackend` no hace nada — el caller no lo sabe |
| **Sentinel values** | `-1` como "no soportado" obliga a checks defensivos en cada uso | `if (fd != -1) { /* usar fd */ }` — lógica condicional basada en tipo dinámico |
| **Extensibilidad bloqueada** | Si añadís un tercer backend (DPDK, AF_XDP, netmap), la interfaz se hincha | Cada backend añade sus propios métodos específicos con defaults no-op |
| **Testabilidad reducida** | No podéis testear `PcapBackend` sin saber que ignora `attach_skb()` | Un test que verifica `attach_skb` fallaría para PcapBackend |

---

### Solución propuesta: Interfaz base mínima + capability interfaces

```cpp
// capture_backend.hpp — interfaz base: solo lo que TODOS los backends hacen
class CaptureBackend {
public:
    virtual ~CaptureBackend() = default;
    
    // Ciclo de vida común
    virtual bool init(const std::string& iface) = 0;
    virtual void shutdown() = 0;
    
    // Operación fundamental: obtener el siguiente paquete
    // Variant A: desde ring buffer eBPF
    // Variant B: desde pcap_dispatch
    virtual std::optional<Packet> next_packet() = 0;
    
    // Estadísticas comunes (ambas variantes las tienen)
    virtual CaptureStats stats() const = 0;
};

// ebpf_capabilities.hpp — solo para backends que soportan eBPF
class EbpfCapable {
public:
    virtual ~EbpfCapable() = default;
    
    virtual bool attach_skb(int fd) = 0;  // Puro, no default
    virtual int get_ringbuf_fd() const = 0;  // Puro, no default
    virtual int get_filter_map_fd() const = 0;  // Puro, no default
    
    // Verificación de tipo segura sin dynamic_cast
    static bool is_ebpf_capable(CaptureBackend* backend) {
        return dynamic_cast<EbpfCapable*>(backend) != nullptr;
    }
};

// pcap_capabilities.hpp — solo para backends que soportan libpcap
class PcapCapable {
public:
    virtual ~PcapCapable() = default;
    
    virtual bool set_bpf_filter(const std::string& filter_expr) = 0;
    virtual pcap_t* raw_handle() const = 0;  // Para operaciones avanzadas de libpcap
};
```

**Implementación de variantes:**

```cpp
// ebpf_backend.hpp
class EbpfBackend : public CaptureBackend, public EbpfCapable {
public:
    bool init(const std::string& iface) override;
    void shutdown() override;
    std::optional<Packet> next_packet() override;
    CaptureStats stats() const override;
    
    // EbpfCapable
    bool attach_skb(int fd) override;
    int get_ringbuf_fd() const override;
    int get_filter_map_fd() const override;
};

// pcap_backend.hpp
class PcapBackend : public CaptureBackend, public PcapCapable {
public:
    bool init(const std::string& iface) override;
    void shutdown() override;
    std::optional<Packet> next_packet() override;
    CaptureStats stats() const override;
    
    // PcapCapable
    bool set_bpf_filter(const std::string& filter_expr) override;
    pcap_t* raw_handle() const override;
};
```

**Uso en `main.cpp` (Variant A) sin downcast inseguro:**

```cpp
// main.cpp — Variant A
std::unique_ptr<CaptureBackend> backend = std::make_unique<EbpfBackend>();

// Verificación de capacidad antes de uso
if (EbpfCapable::is_ebpf_capable(backend.get())) {
    auto* ebpf = static_cast<EbpfCapable*>(backend.get());  // Safe: verificado
    ebpf->attach_skb(skb_fd);
    poll_fds.push_back({ebpf->get_ringbuf_fd(), POLLIN, 0});
} else {
    // Esto nunca ocurre en Variant A, pero el compilador lo exige
    // y documenta la dependencia explícita
    throw std::runtime_error("Variant A requires EbpfCapable backend");
}
```

**Uso en `main_libpcap.cpp` (Variant B):**

```cpp
// main_libpcap.cpp — Variant B
std::unique_ptr<CaptureBackend> backend = std::make_unique<PcapBackend>();

// Nunca necesita EbpfCapable — el compilador lo garantiza
// Si alguien intenta usar attach_skb aquí, falla en compilación, no en runtime
```

---

### Comparativa de enfoques

| Criterio | Interfaz plana (actual) | Interfaces segregadas (propuesta) |
|----------|------------------------|-----------------------------------|
| **Seguridad de tipos** | Runtime (checks de `-1`) | Compilación (no compila si usas mal) |
| **ISP** | Violado | Cumplido |
| **Extensibilidad** | Peor: interfaz hinchada | Mejor: añadir `DPDKCapable` sin tocar existentes |
| **Testabilidad** | Tests condicionales por tipo | Tests específicos por capability |
| **Complejidad cognitiva** | Baja (una interfaz) | Media (múltiples interfaces) |
| **Overhead de virtual** | Igual | Igual |
| **Contribución científica** | Baja (diseño estándar) | **Alta** (diseño de capabilities aplicado a NDR) |

---

### Argumento para el paper

La segregación de interfaces por **capability** (no por tipo concreto) es una contribución metodológica aplicable a cualquier sistema NDR multi-backend. Documentarla en el paper §5 como:

> *"El diseño de aRGus separa la interfaz de captura en una jerarquía de capabilities: `CaptureBackend` define el contrato mínimo (inicialización, obtención de paquetes, estadísticas), mientras que `EbpfCapable` y `PcapCapable` añaden operaciones específicas sin contaminar la interfaz base. Esto permite que `main.cpp` y `main_libpcap.cpp` sean binarios separados que comparten la lógica de pipeline pero no las dependencias de backend, cumpliendo el BSR axiom (ADR-039): un nodo libpcap no requiere headers eBPF ni compilador de bytecode en su imagen de runtime."*

Esto conecta el diseño de interfaces con la separación build/runtime, fortaleciendo la narrativa del paper.

---

### Acción inmediata para DAY 137-138

1. **Refactorizar `CaptureBackend`** a interfaz mínima + `EbpfCapable` + `PcapCapable`
2. **Actualizar `EbpfBackend`** para heredar de ambas
3. **Actualizar `PcapBackend`** para heredar solo de `CaptureBackend` + `PcapCapable`
4. **Actualizar `main.cpp`** para usar `EbpfCapable::is_ebpf_capable()` + `static_cast`
5. **Añadir test de compilación:** `static_assert(!std::is_base_of_v<EbpfCapable, PcapBackend>)`

**Riesgo de no hacerlo:** Si la interfaz plana se consolida en v0.6.x, el refactor posterior (v0.7+) requerirá modificar todos los backends y todos los mains. El coste aumenta exponencialmente con cada backend añadido (DPDK, AF_XDP, netmap, etc.).

---

### Sobre `DEBT-VARIANT-B-PCAP-IMPL-001`

El stub actual (`pcap_loop → ZeroMQ → ml-detector`) es correcto como punto de partida. La implementación completa debe seguir el patrón:

```cpp
// pcap_backend.cpp — implementación completa
std::optional<Packet> PcapBackend::next_packet() {
    struct pcap_pkthdr* header;
    const u_char* data;
    
    int ret = pcap_next_ex(pcap_handle_, &header, &data);
    if (ret == 1) {
        return Packet(data, header->caplen, header->ts);
    } else if (ret == 0) {
        return std::nullopt;  // Timeout
    } else {
        throw PcapError(pcap_geterr(pcap_handle_));
    }
}
```

**Nota:** `pcap_loop` con callback bloquea el hilo y dificulta la integración con el bucle de eventos ZeroMQ. Usad `pcap_next_ex` o `pcap_dispatch` en modo no-bloqueante dentro del `poll()`/`zmq_poll()` existente.

---

### Resumen de posiciones — Kimi

| Aspecto | Veredicto | Justificación |
|---------|-----------|---------------|
| **Interfaz plana actual** | **Rechazada** para v0.6.x | Viola ISP, introduce sentinels, no escala |
| **Interfaces segregadas por capability** | **Aprobada** | Seguridad de tipos en compilación, extensible, publicable |
| **Refactor timing** | **Inmediato** — antes de que `pcap_loop` se implemente | Coste de refactor crece con cada línea de código dependiente |
| **`pcap_loop` vs `pcap_next_ex`** | **`pcap_next_ex`** | Integración con zmq_poll sin hilo adicional |
| **Contribución paper** | **Alta** si se documenta como capability-based design | Conecta con BSR axiom y separación build/runtime |

**Moción:** Propongo que el refactor de `CaptureBackend` a interfaces segregadas sea el primer commit del DAY 138, antes de implementar `pcap_loop → ZeroMQ`. La arquitectura de interfaces es la base; la implementación de libpcap es la consecuencia. Construir sobre una base impura acumula deuda técnica que el paper no puede justificar.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*