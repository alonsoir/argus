A continuación va la revisión del Consejo, centrada en corrección arquitectónica, mantenibilidad y consecuencias medibles en un sistema de captura de alto rendimiento.

---

# Evaluación de la decisión actual

**Situación:**
`CaptureBackend` expone métodos específicos de eBPF (`attach_skb()`, `get_ringbuf_fd()`, fds de mapas), con implementaciones *no-op* en libpcap.

**Conclusión corta:**
No es la mejor decisión. Funciona ahora, pero introduce **deuda estructural** que va a penalizar exactamente el objetivo de Variant B: comparabilidad científica y claridad de arquitectura.

---

# Problemas técnicos detectados

## 1) Violación del principio de sustitución (LSP)

Un `PcapBackend` **no puede cumplir semánticamente**:

* `attach_skb()` no tiene equivalente
* `ringbuf_fd` no existe en libpcap
* maps eBPF no existen

→ Estás forzando a que una implementación finja capacidades que no tiene.

**Efecto real:**

* API engañosa
* errores silenciosos (no-op ≠ correcto)
* dificultad para razonar sobre comportamiento en runtime

---

## 2) Acoplamiento semántico hacia eBPF

La interfaz base deja de ser “abstracción de captura” y pasa a ser:

> “abstracción de captura eBPF con compatibilidad degradada”

Esto rompe tu objetivo declarado:

> “dos binarios completamente separados, cero #ifdef”

Porque aunque eliminaste `#ifdef`, **el acoplamiento sigue existiendo en la interfaz**.

---

## 3) Coste cognitivo y de mantenimiento

Cada nuevo backend futuro (AF_PACKET, DPDK, Netmap) tendrá que:

* implementar no-ops
* documentar excepciones
* convivir con métodos irrelevantes

Esto escala mal.

---

## 4) Riesgo en benchmarking científico (muy importante)

Para el paper:

* Si la interfaz no es neutra, introduces sesgos invisibles
* El camino de datos no es comparable 1:1

Ejemplo:

* eBPF → ring buffer → userspace
* libpcap → callback → userspace

Pero tu API fuerza una forma “tipo eBPF”

→ Esto puede invalidar conclusiones si no se separa correctamente

---

# Qué hace la industria en este punto

Patrón dominante en sistemas de red de alto rendimiento:

## → Separación en **dos niveles de abstracción**

### Nivel 1 — Captura pura (común)

```cpp
class CaptureBackend {
public:
    virtual bool start() = 0;
    virtual bool stop() = 0;
    virtual int get_fd() const = 0;   // opcional (poll/select)
    virtual ~CaptureBackend() = default;
};
```

### Nivel 2 — Extensiones específicas (NO en la base)

#### eBPF específico

```cpp
class EbpfBackend : public CaptureBackend {
public:
    int get_ringbuf_fd() const;
    int get_map_fd(const std::string& name) const;
    bool attach_skb();
};
```

#### libpcap específico

```cpp
class PcapBackend : public CaptureBackend {
public:
    pcap_t* handle();
};
```

---

# Alternativas viables

## Opción A — Interfaz mínima (RECOMENDADA)

Eliminar de `CaptureBackend` todo lo específico de eBPF.

Ventajas:

* API limpia
* backends realmente intercambiables
* paper científicamente sólido

Inconveniente:

* `main.cpp` Variant A necesitará conocer `EbpfBackend`

→ Esto es correcto y esperado

---

## Opción B — Capability-based design (más avanzada)

```cpp
enum class Capability {
    RING_BUFFER,
    BPF_MAPS,
    ZERO_COPY
};

virtual bool supports(Capability c) const = 0;
```

Y luego:

```cpp
if (backend->supports(Capability::RING_BUFFER)) {
    auto* ebpf = dynamic_cast<EbpfBackend*>(backend);
}
```

Ventajas:

* extensible
* explícito

Inconvenientes:

* más complejidad
* innecesario para tu fase actual

---

## Opción C — Template/static polymorphism

No recomendable aquí:

* rompe desacoplamiento runtime
* complica build
* no aporta valor para tu caso

---

# Recomendación del Consejo

**Adoptar Opción A inmediatamente:**

1. `CaptureBackend` → solo lo común
2. Mover todo lo eBPF a `EbpfBackend`
3. `main.cpp` Variant A usa `EbpfBackend` directamente
4. `main_libpcap.cpp` usa `PcapBackend`

Esto es coherente con tu decisión previa:

> “dos binarios completamente separados”

---

# Impacto en tu pipeline (importante)

## Positivo

* Código más limpio
* Comparativa XDP vs libpcap válida científicamente
* Menor deuda técnica futura
* Facilita añadir DPDK / AF_XDP más adelante

## Negativo (menor)

* ligeros cambios en `main.cpp`
* pérdida de “intercambiabilidad artificial” (que en realidad no era real)

---

# Observación estratégica (clave para el paper)

Esta decisión afecta directamente a tu contribución:

Si lo haces bien, puedes documentar:

> “We deliberately separated capture abstractions to avoid cross-contamination between kernel-bypass (XDP) and user-space capture (libpcap), ensuring fair benchmarking.”

Eso es **material publicable**.

---

# Veredicto final

* La arquitectura general (dos binarios, sin `#ifdef`) es **excelente**
* La interfaz actual de `CaptureBackend` es **incorrecta a nivel de diseño**
* El problema no es de implementación, sino de **modelo mental de abstracción**

---

# Respuesta directa a tu pregunta

> ¿Mantener los métodos en la interfaz base o moverlos?

**Moverlos fuera de la interfaz base. Sin duda.**

Mantenerlos:

* rompe LSP
* introduce deuda
* contamina el diseño

Moverlos:

* alinea con principios sólidos
* mejora la validez científica
* escala correctamente

---

Si se quiere ir un paso más allá en el siguiente ciclo, el Consejo recomendaría revisar también:

* el contrato de entrega de paquetes (`ZeroMQ boundary`)
* la simetría de latencias entre backends
* el punto exacto de timestamping (kernel vs userland)

Ahí es donde estará la diferencia real entre Variant A y B.
