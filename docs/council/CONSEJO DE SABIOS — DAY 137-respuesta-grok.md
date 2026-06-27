**Consejo de Sabios — Respuesta DAY 137 (feature/variant-b-libpcap)**

Analizamos con detenimiento la decisión arquitectónica tomada hoy y el estado actual de la abstracción `CaptureBackend`.

### Respuesta directa a la pregunta clave

**No es correcto mantener `attach_skb()`, `get_ringbuf_fd()` y los métodos relacionados con filter maps en la interfaz base `CaptureBackend`.**

Deben moverse exclusivamente a `EbpfBackend` (o a una interfaz intermedia más específica).

#### Razón técnica principal (KISS + principios sólidos de C++20)

Estás violando el **Interface Segregation Principle (ISP)** y creando una **interfaz gorda (fat interface)**. Aunque el criterio actual (“para que `main.cpp` no tenga que hacer downcast”) parece práctico a corto plazo, introduce varios problemas graves a medio plazo:

1. **Acoplamiento innecesario**: Todo código que use `CaptureBackend*` (incluyendo tests, posibles future backends, o código de orquestación) queda contaminado semánticamente con conceptos eBPF-specific (ring buffer, skb, filter maps). Esto rompe la abstracción.

2. **Mentira en la interfaz**: Los métodos por defecto “no-op” en Variant B son una forma disfrazada de `dynamic_cast` o flags implícitos. En sistemas de alto rendimiento y seguridad, las mentiras en las APIs se pagan caras (bugs sutiles, comportamientos inesperados bajo presión, dificultad de razonamiento).

3. **Dificultad de evolución**: Cuando llegue un tercer backend (por ejemplo, AF_XDP puro, DPDK, o incluso un backend userspace con `io_uring` + raw sockets), la interfaz base se convertirá en un Frankenstein.

4. **Testing y mantenibilidad**: Los tests que mockeen `CaptureBackend` tendrán que implementar (o ignorar) métodos que no les corresponden.

#### Diseño recomendado (C++20 moderno y limpio)

Opción preferida (la más limpia y escalable):

```cpp
// Base mínima y honesta
class CaptureBackend {
public:
    virtual ~CaptureBackend() = default;
    virtual bool start() = 0;
    virtual void stop() = 0;
    virtual bool is_running() const = 0;

    // Métodos comunes de alto nivel
    virtual std::uint64_t packets_captured() const = 0;
    virtual std::uint64_t packets_dropped() const = 0;
    // ... otros métricos comunes
};

// Interfaz específica para backends que exponen ring buffers / eBPF maps
class RingBufferProvider : public CaptureBackend {
public:
    virtual int get_ringbuf_fd() const = 0;
    virtual int get_filter_map_fd() const = 0;
    // attach_skb() probablemente también pertenece aquí o a un EbpfSpecific
    virtual bool attach_skb(...) = 0;  
};
```

Entonces:

- `EbpfBackend` hereda de `RingBufferProvider`
- `PcapBackend` hereda solo de `CaptureBackend`
- En `main.cpp` (Variant A) haces:

```cpp
auto* backend = create_ebpf_backend(...);
auto* rb_provider = dynamic_cast<RingBufferProvider*>(backend);
if (!rb_provider) { /* error fatal */ }
```

O mejor aún (C++20 style, más seguro y explícito):

Usa **Type Erasure** + **std::any** o, preferiblemente, un pequeño **variant** + **visitor** o simplemente pasa el backend concreto donde realmente se necesite el ring buffer (el `RingBufferConsumer` ya está fuertemente acoplado a eBPF, como bien detectasteis).

#### Alternativa pragmática pero aún limpia (recomendada para velocidad actual)

Mantén `CaptureBackend` mínima.

Crea una segunda interfaz estrecha:

```cpp
class EbpfExtensions {
public:
    virtual ~EbpfExtensions() = default;
    virtual int get_ringbuf_fd() const = 0;
    virtual int get_filter_map_fd() const = 0;
    virtual bool attach_skb(...) = 0;
};
```

Luego `EbpfBackend : public CaptureBackend, public EbpfExtensions`

En el código que necesita las extensiones eBPF haces:

```cpp
EbpfExtensions* ext = dynamic_cast<EbpfExtensions*>(backend);
if (ext) {
    // lógica específica de ring buffer / XDP
}
```

Esto es explícito, mantiene la segregación y evita que la interfaz base mienta.

**Regla de oro aquí**: Si un método tiene implementación por defecto que hace “nada” o lanza “not implemented”, casi siempre es señal de que no pertenece a esa interfaz.

### Observaciones adicionales sobre la arquitectura actual (DAY 137)

- **Decisión de dos binarios separados sin #ifdef**: Excelente. Fue la decisión correcta. Felicitaciones por haberlo visto temprano. Mantened esta disciplina.

- **DEBT-VARIANT-B-PCAP-IMPL-001 (`pcap_loop → ZeroMQ → ml-detector`)**: Esta deuda es crítica para la comparativa científica. Para el paper necesitáis medir apples-to-apples:
    - Latencia desde captura hasta que el paquete llega al `ml-detector`
    - Tasa de drops bajo carga sostenida y bajo burst
    - Consumo de CPU y cache misses
    - Determinismo del procesamiento

  Recomendación fuerte: Implementad pronto un `PcapRingConsumer` o `PcapBatchProcessor` que tenga la misma interfaz de salida hacia ZeroMQ que tiene el actual `RingBufferConsumer`. Así podréis reutilizar todo el pipeline posterior sin duplicación.

- **ZeroMQ como frontera**: Estáis usando ZeroMQ como capa de desacoplamiento entre captura y procesamiento. Esto es razonable para Variant B, pero asegura que el formato de los mensajes sea idéntico entre ambos backends (mismo protobuf o estructura binaria). Cualquier diferencia aquí invalida la comparación experimental.

### Recomendaciones para los próximos días

1. Refactorizar `CaptureBackend` cuanto antes (antes de implementar `pcap_loop`). Cuanto más crezca el código, más doloroso será el cambio.
2. Definir claramente las métricas que vais a publicar en el paper para la comparación XDP vs libpcap (pps sostenido, % CPU, drop rate, latencia cola, etc.).
3. Considerar añadir un tercer target en el futuro: `sniffer-afxdp` (AF_XDP es el punto medio natural entre XDP y libpcap tradicional).

**Veredicto del Consejo**:
Mantener los métodos eBPF-specific en la interfaz base es técnicamente incorrecto y va contra buenos principios de diseño. Corregidlo ahora que el Variant B todavía es pequeño. El coste de hacerlo hoy es bajo; dentro de dos semanas será significativamente mayor.

La separación en dos binarios es una muy buena decisión arquitectónica. Protegedla.

Seguís en un buen camino. La honestidad con la que estáis documentando deudas y KNOWN-FAIL es madura y profesional.

Preguntad cuando queráis revisión de la nueva jerarquía de interfaces o del diseño del consumer para libpcap.

La verdad por delante, siempre.

— Consejo de Sabios