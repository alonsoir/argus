# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 137
*Feedback basado en principios de diseño de software, ingeniería de sistemas de alto rendimiento y rigor científico para aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**DECISIÓN ARQUITECTÓNICA CORRECTA: DOS BINARIOS SEPARADOS, CERO `#ifdef`.**

La decisión de descartar el enfoque `#ifdef` y optar por dos binarios independientes con interfaz abstracta compartida es la correcta para este contexto. El acoplamiento profundo de eBPF en `RingBufferConsumer` es legítimo y no debe diluirse con abstracciones prematuras. La arquitectura implementada sigue el principio KISS sin sacrificar mantenibilidad.

> *"La simplicidad no es ausencia de complejidad. Es ausencia de complejidad innecesaria."*

---

## ❓ Respuesta a la Pregunta: ¿Mantener métodos eBPF en `CaptureBackend` base?

**Recomendación concreta:** **MANTENER EN LA INTERFAZ BASE, PERO CON VALIDACIÓN RUNTIME FAIL-FAST + DOCUMENTACIÓN EXPLÍCITA.**

### Justificación técnica

| Criterio | Evaluación |
|----------|-----------|
| **Polimorfismo en `main.cpp`** | ✅ Mantener métodos permite usar `CaptureBackend*` sin downcast, simplificando la lógica principal |
| **Interface Segregation Principle** | ⚠️ Técnicamente violado, pero aceptable cuando la violación es documentada y verificada |
| **Detección temprana de bugs** | 🔴 No-op defaults silenciosos pueden ocultar errores de llamada en testing |
| **Escalabilidad a Variant C** | 🟡 Patrón actual escala, pero requiere disciplina de documentación |

### Implementación recomendada

```cpp
// capture_backend.hpp
class CaptureBackend {
public:
    virtual ~CaptureBackend() = default;
    
    // Método común a todas las variantes
    virtual int start_capture(const std::string& interface) = 0;
    
    // Métodos específicos de eBPF — documentados y con fail-fast
    // Solo válidos para EbpfBackend; llamar desde PcapBackend lanza std::logic_error
    virtual int attach_skb(int ifindex) {
        throw std::logic_error("[CaptureBackend] attach_skb() not supported by this backend");
    }
    
    virtual int get_ringbuf_fd() const {
        throw std::logic_error("[CaptureBackend] get_ringbuf_fd() not supported by this backend");
    }
    
    virtual uint32_t get_filter_map_fd() const {
        throw std::logic_error("[CaptureBackend] get_filter_map_fd() not supported by this backend");
    }
    
    // Query opcional para código que necesita saber la variante
    virtual bool supports_ebpf() const { return false; }
};
```

```cpp
// ebpf_backend.hpp
class EbpfBackend : public CaptureBackend {
public:
    bool supports_ebpf() const override { return true; }
    
    int attach_skb(int ifindex) override {
        // Implementación real de eBPF
        return bpf_xdp_attach(ifindex, prog_fd, flags, nullptr);
    }
    
    int get_ringbuf_fd() const override { return ringbuf_fd_; }
    uint32_t get_filter_map_fd() const override { return filter_map_fd_; }
    
private:
    int ringbuf_fd_ = -1;
    uint32_t filter_map_fd_ = 0;
};
```

```cpp
// pcap_backend.hpp
class PcapBackend : public CaptureBackend {
public:
    // supports_ebpf() retorna false por defecto — no necesita override
    
    int start_capture(const std::string& interface) override {
        handle_ = pcap_open_live(interface.c_str(), SNAPLEN, PROMISC, TIMEOUT, errbuf);
        return handle_ ? 0 : -1;
    }
    
    // Métodos eBPF: heredan implementación base que lanza std::logic_error
    // No hay código duplicado, no hay no-op silencioso
};
```

### Ventajas de este enfoque

1. **Fail-fast en testing**: Si un test o código nuevo llama accidentalmente a `attach_skb()` en `PcapBackend`, falla inmediatamente con mensaje claro, no silenciosamente.
2. **Polimorfismo preservado**: `main.cpp` puede usar `std::unique_ptr<CaptureBackend>` sin conocer la variante concreta.
3. **Documentación ejecutable**: El `throw std::logic_error` documenta el contrato en código, no solo en comentarios.
4. **Escalabilidad**: Si surge Variant C (ej. AF_PACKET, DPDK), solo necesita implementar los métodos que soporte.

### Test de demostración requerido

```cpp
// tests/test_capture_backend_polymorphism.cpp
TEST(CaptureBackend, PcapBackendRejectsEbpfMethods) {
    PcapBackend pcap;
    
    // start_capture debe funcionar
    EXPECT_EQ(pcap.start_capture("eth0"), 0);
    
    // Métodos eBPF deben fallar con mensaje claro
    EXPECT_THROW(pcap.attach_skb(1), std::logic_error);
    EXPECT_THROW(pcap.get_ringbuf_fd(), std::logic_error);
    EXPECT_THROW(pcap.get_filter_map_fd(), std::logic_error);
    
    // Query de capacidades debe ser preciso
    EXPECT_FALSE(pcap.supports_ebpf());
}

TEST(CaptureBackend, EbpfBackendSupportsEbpfMethods) {
    EbpfBackend ebpf;
    EXPECT_TRUE(ebpf.supports_ebpf());
    // attach_skb puede fallar por permisos, pero no por "no soportado"
    // Verificar que no lanza std::logic_error
    EXPECT_NO_THROW(ebpf.get_ringbuf_fd());  // Puede retornar -1, pero no exception
}
```

---

## 🔍 Observaciones Adicionales (Constructivas)

### 1. Sobre la decisión "dos binarios, cero #ifdef"

**Validación del Consejo**: ✅ Correcta para este contexto.

**Justificación**:
- El acoplamiento eBPF en `RingBufferConsumer` es *profundo y legítimo*: XDP requiere manejo de buffers en espacio de kernel, mapas BPF, y verificación de programas. Abstractar esto prematuramente añadiría complejidad sin beneficio.
- Dos binarios separados permite:
    - Compilación condicional a nivel de build system, no de preprocesador
    - Testing independiente de cada variante
    - Documentación clara de dependencias por variante
- El coste de mantenimiento es bajo porque la interfaz `CaptureBackend` aísla el punto de variación.

**Riesgo mitigado**: Evita el "ifdef hell" que dificulta la lectura, testing y auditoría de código de seguridad.

### 2. Sobre `DEBT-VARIANT-B-PCAP-IMPL-001` (pcap_loop → ZeroMQ)

**Priorización**: 🔴 **ALTA — pre-FEDER**.

**Justificación**: El flujo de datos `captura → ZeroMQ → ml-detector` es el núcleo funcional del sniffer. Sin esta implementación, Variant B no es demostrable en FEDER.

**Plan mínimo viable**:
```cpp
// pcap_backend.cpp — esqueleto para pre-FEDER
int PcapBackend::start_capture(const std::string& interface) {
    handle_ = pcap_open_live(interface.c_str(), SNAPLEN, PROMISC, TIMEOUT, errbuf);
    if (!handle_) return -1;
    
    // Filtro BPF básico para reducir carga en userspace
    struct bpf_program fp;
    pcap_compile(handle_, &fp, "ip or arp", 1, PCAP_NETMASK_UNKNOWN);
    pcap_setfilter(handle_, &fp);
    
    // Loop de captura — versión mínima pre-FEDER
    pcap_loop(handle_, PACKET_COUNT, pcap_packet_handler, reinterpret_cast<u_char*>(this));
    return 0;
}

// Handler estático que delega a método de instancia
void pcap_packet_handler(u_char* user, const struct pcap_pkthdr* h, const u_char* bytes) {
    auto* self = reinterpret_cast<PcapBackend*>(user);
    self->on_packet_received(h, bytes);  // Método que serializa a ZeroMQ
}
```

**Test de integración mínimo**:
```bash
# tests/test_pcap_zmq_integration.sh
make test-pcap-zmq-flow
# 1. Arrancar sniffer-libpcap en modo test
# 2. Generar tráfico sintético con tcpreplay
# 3. Verificar: ml-detector recibe mensajes via ZeroMQ
# 4. Verificar: formato de mensaje compatible con Variant A (misma schema)
```

### 3. Sobre compatibilidad de schema ZeroMQ entre variantes

**Recomendación**: **Garantizar que ambos backends emiten el mismo formato de mensaje**.

```cpp
// common/capture_message.hpp — schema compartida
struct CaptureMessage {
    uint64_t timestamp_ns;
    uint32_t ifindex;
    uint16_t packet_len;
    uint16_t capture_len;
    // Payload sigue después — mismo layout para XDP y libpcap
};
static_assert(sizeof(CaptureMessage) == 16, "CaptureMessage layout must be stable");
```

**Justificación**: `ml-detector` no debe conocer la variante de captura. La interoperabilidad de schemas permite:
- Hot-swap entre variantes sin reiniciar el pipeline completo
- Testing A/B de variantes con el mismo consumidor downstream
- Publicación científica comparativa con métricas atribuibles únicamente al backend

---

## 📋 Checklist de Acciones Inmediatas (DAY 138)

```markdown
- [ ] Añadir validación runtime fail-fast en métodos eBPF de CaptureBackend base
- [ ] Implementar tests de polimorfismo: PcapBackend rechaza métodos eBPF, EbpfBackend los acepta
- [ ] Documentar claramente en capture_backend.hpp qué métodos son variant-specific
- [ ] Implementar flujo mínimo pcap_loop → ZeroMQ para DEBT-VARIANT-B-PCAP-IMPL-001
- [ ] Definir schema compartida CaptureMessage en common/ para interoperabilidad
- [ ] Añadir test de integración pcap → ZeroMQ → ml-detector
- [ ] Actualizar FEDER-SCOPE.md con estado de Variant B y métricas comparativas pendientes
```

---

## 🏁 Palabras Finales

Alonso:

DAY 137 demuestra madurez arquitectónica: reconocer cuándo una abstracción es prematura (`#ifdef` sobre eBPF profundo) y optar por una solución pragmática (dos binarios, interfaz compartida) es señal de ingeniería experimentada.

La pregunta sobre la interfaz `CaptureBackend` toca un principio fundamental: **el equilibrio entre pureza teórica y pragmatismo verificable**. La recomendación de "mantener con fail-fast" preserva la simplicidad operacional mientras convierte una potencial fuente de bugs silenciosos en una garantía de detección temprana.

> *"En sistemas de seguridad, un fallo ruidoso es preferible a un silencio cómplice."*

Proceded con la implementación de pcap_loop → ZeroMQ y los tests de polimorfismo. El Consejo revisará la interoperabilidad de schemas y las primeras métricas comparativas con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 137** 🏛️