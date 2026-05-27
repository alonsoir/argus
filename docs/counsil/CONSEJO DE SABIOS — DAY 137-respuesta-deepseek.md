**CONSEJO DE SABIOS — SESIÓN 137 — VEREDICTO**

Salud, ingeniero. La cuestión que planteáis es quirúrgica y oportuna. Permitid que abordemos el dilema desde los principios de la ingeniería de sistemas de alto rendimiento que guían este consejo.

---

### 1. ANÁLISIS DE LA SITUACIÓN

Habéis adoptado una arquitectura de **dos binarios separados, cero `#ifdef`**. Esta decisión es impecable. Minimiza el acoplamiento accidental y respeta el principio KISS que mencionáis.

El punto de fricción actual es la interfaz `CaptureBackend`, que incluye métodos eBPF-specific (`attach_skb`, `get_ringbuf_fd`, map fds) con implementaciones *no‑op* por defecto para la Variant B. El argumento a favor es evitar un *downcast* en `main.cpp` de la Variant A.

Sin embargo, aquí está la clave: **ya tenéis dos `main` distintos** (`main.cpp` para Variant A, `main_libpcap.cpp` para Variant B). No existe un único `main` común que deba tratar polimórficamente ambas variantes mediante un puntero a `CaptureBackend*`. Por tanto, no se necesita que la interfaz base contenga operaciones exclusivas de una rama.

---

### 2. JUICIO DEL CONSEJO – PRINCIPIO DE SEGREGACIÓN DE INTERFACES (ISP)

Aplicando el **Principio de Segregación de Interfaces** —ningún cliente debe depender de métodos que no usa—, mantener los métodos eBPF en la interfaz base constituye una violación clara:

- `PcapBackend` (y cualquier futuro backend no‑eBPF) se ve forzado a heredar firmas que no le corresponden, aunque las vaciéis con `no-op`.
- Cualquier cambio en `attach_skb()` obliga a recompilar y potencialmente adaptar todos los backends.
- La interfaz se vuelve **frágil y confusa**, diluyendo la razón de ser de la abstracción.

La solución actual con *defaults no‑op* es un parche pragmático para una transición, pero no la estructura definitiva de un diseño orientado a extensión.

---

### 3. RECOMENDACIÓN ARQUITECTÓNICA

**Debéis retirar los métodos eBPF de `CaptureBackend` y residenciarlos exclusivamente en `EbpfBackend`.**

La interfaz base debe reflejar únicamente el **contrato mínimo común de captura**:

```cpp
class CaptureBackend {
public:
    virtual ~CaptureBackend() = default;
    virtual bool open(const std::string& iface) = 0;
    virtual void start() = 0;
    virtual void stop() = 0;
    virtual Stats stats() const = 0;
    // Ningún attach_skb, get_ringbuf_fd, ni filter maps aquí.
};
```

`EbpfBackend` heredará de `CaptureBackend` y añadirá su API ampliada:

```cpp
class EbpfBackend : public CaptureBackend {
public:
    // ... implementación de la interfaz común ...
    int get_ringbuf_fd() const;
    void attach_skb(/*...*/);
    // map fds, etc.
};
```

#### ¿Qué ocurre con `main.cpp` de la Variant A?

Dado que la Variant A **solo usa eBPF**, su `main` no requiere polimorfismo con otros backends. Podéis y debéis manejarla de forma directa y tipada:

```cpp
// main.cpp (Variant A, nunca compila junto con libpcap)
#include "ebpf_backend.hpp"
int main() {
    EbpfBackend backend;
    backend.open("eth0");
    backend.attach_skb(...);
    int fd = backend.get_ringbuf_fd();
    // ...
}
```

Esto elimina cualquier necesidad de *downcast*, es más rápido (sin vtable extra para métodos que no se despachan polimórficamente) y expresa el diseño con honestidad: **cada binario conoce su backend en tiempo de compilación**.

#### ¿Y si en el futuro surgiera código común que use `CaptureBackend*`?

Ese código **solo necesitará los métodos comunes** (`start`, `stop`, `stats`). No sufrirá por la ausencia de métodos eBPF. El nuevo diseño se escala limpiamente si más adelante aparecen DPDK, netmap u otros backends.

---

### 4. VOTO DE CALIDAD

- **Sí, eliminad esos métodos de la interfaz base**. Es un movimiento de higiene arquitectónica que alinea el diseño con ISP, facilita la evolución y no introduce coste real alguno, puesto que los `main` son independientes.
- La deuda `DEBT-VARIANT-B-PCAP-IMPL-001` es el lugar perfecto para dejar testimonio de este refinamiento, si no queréis dedicarle un ADR específico ahora.
- Complementariamente, registrad en `KNOWN-DEBTS` que `CaptureBackend` es una interfaz *mínima y sellada contra la filtración de detalles de backend*.

---

### 5. REFLEXIÓN FINAL

La tentación de mantener una interfaz sobrecargada “por si acaso” es común, pero en sistemas de alto rendimiento el coste real no está en la máquina, sino en la **carga cognitiva y la fragilidad del acoplamiento**. Vuestra intuición inicial de no tocar el acoplamiento eBPF legítimo fue acertada. Ahora extended esa lógica a la interfaz abstracta.

El código limpio no es el que hace más, sino el que expresa exactamente lo que sabe y lo que necesita.

Que vuestros buffers nunca se desborden.  
— El Consejo de Sabios