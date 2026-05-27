# ADR-036: Formal Verification Baseline

| Metadata | Valor |
|---|---|
| **Estado** | BORRADOR — pendiente revisión Consejo |
| **Fecha** | 14 Abril 2026 |
| **Autor** | Alonso Isidoro Román |
| **Inspiración** | Hugo Vázquez Caramés — Firewall Numantia 25A checklist |
| **Pre-requisitos** | ADR-029 (variantes hardened) + ADR-034 (topología) + ADR-035 (etcd HA) |
| **Feature destino** | feature/formal-verification (última feature del proyecto) |
| **Aplica a** | Variante A (AppArmor+eBPF/XDP) + Variante C (seL4+libpcap) |

---

## Contexto

aRGus NDR protege infraestructura crítica — hospitales, escuelas, municipios.
En ese dominio, "funciona en mis tests" no es suficiente. En algún punto del
roadmap, el software debe poder demostrar que funciona correctamente bajo
cualquier entrada válida, no solo bajo las entradas que hemos probado.

La verificación formal es el instrumento que permite hacer esa demostración.
No es el primer paso del desarrollo — es el último. Requiere que el código
esté estabilizado, que los contratos estén claros, y que la arquitectura
no cambie de forma significativa. Por eso este ADR es el punto y final
del desarrollo activo, tanto para la Variante A como para la Variante C.

Hugo Vázquez Caramés (Firewall Numantia 25A) ha documentado públicamente
un checklist de 12 pasos para establecer una baseline de verificación formal
sobre C puro. Este ADR adapta ese checklist a la realidad de aRGus NDR:
C++20 + componentes críticos en C puro (seed_client, crypto-transport) +
dos variantes de despliegue con perfiles de riesgo distintos.

---

## Decisión

Establecer una **Formal Verification Baseline** en dos fases:

- **Fase A:** componentes críticos en C puro — verificación con Frama-C/WP
- **Fase B:** componentes C++20 — verificación con clang-tidy + ASan + UBSan
  + contratos informales anotados (precondiciones/postcondiciones en código)

La Variante C (seL4) tiene un perfil de verificación más estricto que la
Variante A (AppArmor), dado que seL4 ya está formalmente verificado y los
componentes que corren sobre él deben cumplir las mismas garantías.

---

## Alcance de verificación por componente

| Componente | Lenguaje | Herramienta | Prioridad | Variante |
|---|---|---|---|---|
| seed_client.cpp | C++20/C | Frama-C (partes C) + UBSan | P0 | A + C |
| crypto-transport | C++20/C | Frama-C (partes C) + ASan | P0 | A + C |
| plugin_loader.cpp | C++20 | clang-tidy + contratos | P0 | A + C |
| etcd-server | C++20 | UBSan + contratos | P1 | A + C |
| sniffer (eBPF/XDP) | C++20 + eBPF C | Frama-C parcial + verificación eBPF | P1 | A |
| sniffer (libpcap) | C++20 | UBSan + contratos | P1 | C |
| ml-detector | C++20 | UBSan + contratos + invariantes ML | P1 | A + C |
| firewall-acl-agent | C++20 | UBSan + contratos | P2 | A + C |
| rag-ingester | C++20 | UBSan + contratos | P2 | A + C |
| rag-security | C++20 | UBSan + contratos | P2 | A + C |

---

## Checklist de baseline (adaptado de Hugo Vázquez Caramés)

### 1. Definir alcance de verificación
Por cada componente P0:
- Delimitar funciones a verificar (no todo el componente)
- Definir estados relevantes y propiedades a demostrar
- Documentar qué queda **fuera** del alcance y por qué

### 2. Fijar modelo de ejecución
Declarar explícitamente para cada componente:
- Monohilo vs multihilo (sniffer es multihilo — ShardedFlowManager)
- Presencia de interrupciones (sniffer eBPF — sí)
- Concurrencia asíncrona relevante para la lógica funcional

### 3. Restringir perfil de C/C++
Para las partes C puro (seed_client, crypto-transport):
- Evitar construcciones opacas
- Limitar aliasing de punteros
- Controlar aritmética de punteros
- Minimizar macros complejas
- Eliminar dependencias innecesarias del compilador

Para C++20:
- Evitar UB conocido (signed overflow, null deref, out-of-bounds)
- Limitar templates a instanciaciones verificables
- Controlar `reinterpret_cast` y `void*`

### 4. Normalizar el código
- Hacer explícitos tipos y conversiones
- Descomponer expresiones complejas
- Separar lectura, decisión y escritura
- Reducir efectos laterales
- Normalizar bucles y salidas

### 5. Limpiar semántica
- Inicializar todo estado persistente
- Acotar índices y longitudes (ya tenemos MAX_PLUGIN_PAYLOAD_SIZE = 64KB)
- Revisar conversiones signed/unsigned
- Controlar shifts y overflows
- Validar punteros y buffers
- Evitar depender del orden de evaluación

### 6. Modelar hipótesis del entorno
- Especificar qué comportamientos externos se asumen
- Para el sniffer: qué garantiza el kernel sobre los paquetes recibidos
- Para plugin_loader: qué garantiza el OS sobre dlopen/fstat
- Para seed_client: qué garantiza el filesystem sobre seed.bin

### 7. Aislar lógica funcional
Separar con claridad:
- Lógica interna (verificable)
- Acceso a recursos externos (no verificable formalmente)
- Gestión de buffers
- Transiciones de estado
- Tratamiento de error

### 8. Anotar con contratos formales
Para cada función crítica añadir:
```cpp
// @requires: seed_path != nullptr && strlen(seed_path) > 0
// @ensures: seed_.size() == 32 || throws(std::runtime_error)
// @invariant: seed_ permanece zeroed hasta load() completo
// @terminates: siempre (no bucles infinitos)
```

### 9. Refinar bucles
- Distinguir espera acotada de espera potencialmente infinita
- Introducir límites o timeouts verificables
- Definir condición de salida normal y de error
- Crítico para: sniffer (RingBufferConsumer), rag-ingester (FAISS queries)

### 10. Fijar entorno de compilación
Congelar para cada variante:
- Compilador y versión (GCC 12.x para Variante A, configuración seL4 para C)
- Flags: `-Wall -Wextra -Wpedantic -fstack-protector-strong`
- Arquitectura objetivo: x86-64 (Variante A) + ARM64 (Variante C)
- Tamaños de tipos explícitos (`uint32_t`, no `int`)
- Modelo de memoria documentado

### 11. Ejecutar chequeos previos automáticos
Antes de congelar la baseline:
```bash
# Warnings estrictos (ya tenemos -Wall -Wextra -Wpedantic)
make pipeline-build 2>&1 | grep -c warning

# Address Sanitizer
cmake -DCMAKE_CXX_FLAGS="-fsanitize=address" ...
make test-all

# Undefined Behavior Sanitizer
cmake -DCMAKE_CXX_FLAGS="-fsanitize=undefined" ...
make test-all

# Static analysis
clang-tidy --checks='*' src/*.cpp

# Valgrind (sin leaks en componentes críticos)
valgrind --leak-check=full ./build-debug/etcd-server
```
Gate de entrada a verificación formal: **0 warnings + 0 ASan + 0 UBSan + 0 Valgrind leaks**
en componentes P0.

### 12. Congelar línea base de verificación
Fijar exactamente:
- Commit hash de la baseline (tag `v-formal-baseline`)
- Contratos anotados en código
- Hipótesis del entorno documentadas en `docs/formal/assumptions.md`
- Configuración de compilación en `docs/formal/build-config.md`
- Propiedades a demostrar en `docs/formal/properties.md`

---

## Diferencias entre Variante A y Variante C

| Aspecto | Variante A (AppArmor+eBPF/XDP) | Variante C (seL4+libpcap) |
|---|---|---|
| Nivel de verificación requerido | Alto | Muy alto |
| Herramienta principal | Frama-C + UBSan + ASan | Frama-C + seL4 proof obligations |
| Componente más complejo | sniffer eBPF/XDP | plugin_loader sobre seL4 |
| Modelo de memoria | Linux kernel guarantees | seL4 capability model |
| Certificación objetivo | IEC 62443 (industrial) | Common Criteria EAL4+ |
| Bucles críticos | RingBufferConsumer | seL4 IPC message loops |
| Hipótesis del entorno | AppArmor + Linux kernel | seL4 microkernel (ya verificado) |

---

## Propiedades a demostrar (preliminar)

Las siguientes propiedades deben demostrarse antes de cerrar este ADR:

**P1 — Ausencia de buffer overflow en seed_client**
`∀ input: load(path) → seed_.size() == 32 ∨ throws(runtime_error)`

**P2 — Fail-closed garantizado en plugin_loader**
`∀ plugin: signature_invalid(plugin) → std::terminate() (never returns)`

**P3 — INVARIANTE-SEED-001 formal**
`∀ component ∈ COMPONENTS: seed(component) == seed_family`

**P4 — Ausencia de data race en ShardedFlowManager**
`∀ packet: process(packet) → no concurrent write to same shard`

**P5 — Terminación del pipeline bajo carga**
`∀ input_rate ≤ MAX_MBPS: pipeline terminates within bounded time`

---

## Preguntas abiertas para el Consejo

**OQ-1:** ¿Frama-C/WP es la herramienta correcta para las partes C puro, o
preferís CBMC (bounded model checking) para propiedades de seguridad específicas?

**OQ-2:** Para C++20 puro, ¿hay herramientas de verificación formal maduras
en 2026, o nos limitamos a ASan + UBSan + contratos informales anotados?

**OQ-3:** ¿Qué certificación es realista para hospitales europeos?
IEC 62443-4-2 (componentes industriales) vs Common Criteria vs ENS (España)?

**OQ-4:** ¿El delta de esfuerzo entre Variante A y Variante C justifica
mantener ambas en el roadmap de verificación formal, o Variante C es
exclusivamente investigación/paper?

---

## Consecuencias

**Positivas:**
- aRGus NDR puede aspirar a certificación formal para hospitales europeos
- La Variante C (seL4) se convierte en contribución científica publicable
  independiente del paper principal
- El checklist es reutilizable para cualquier componente nuevo

**Negativas:**
- Coste temporal muy alto — estimación: 6-12 meses de trabajo en solitario
- Requiere aprendizaje de Frama-C/WP (curva de entrada significativa)
- El código C++20 tiene soporte limitado en herramientas de verificación formal

**Neutras:**
- La baseline ASan + UBSan se puede implementar progresivamente,
  empezando por componentes P0, sin bloquear el desarrollo de otras features

---

## Estado de implementación

| Elemento | Estado |
|---|---|
| Checklist adaptado | ✅ Este documento |
| Gate ASan + UBSan en CI | ⏳ feature/formal-verification |
| Contratos anotados (seed_client) | ⏳ feature/formal-verification |
| Frama-C baseline seed_client | ⏳ feature/formal-verification |
| Propiedades P1-P5 demostradas | ⏳ feature/formal-verification |
| Certificación IEC 62443 | ⏳ post-verificación |

*Borrador — DAY 117 — 14 Abril 2026*
*Pendiente revisión Consejo de Sabios*
