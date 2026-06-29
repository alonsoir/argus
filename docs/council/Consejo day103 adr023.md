# Consejo de Sabios — DAY 103
## ML Defender (aRGus NDR) — Sesión de revisión
### 31 marzo 2026

---

## Contexto

Somos un sistema de detección y respuesta de red (NDR) open-source en C++20,
diseñado para organizaciones con recursos limitados (hospitales, colegios,
ayuntamientos). Llevamos 103 días de desarrollo continuo.

Estado actual:
- Pipeline: 6/6 RUNNING
- Tests: 25/25 ✅ (récord)
- ADR-012 PHASE 1b: 5/5 componentes con plugin-loader ✅
- Paper: Draft v7, 21 páginas, LaTeX

---

## PARTE 1 — Lo realizado en DAY 103

### 1.1 Makefile rag alignment

El componente `rag-security` tenía inconsistencias con el patrón estándar del
Makefile. Se han aplicado 6 correcciones:

- `rag-build`: cmake directo con `$(CMAKE_FLAGS)` — ahora PROFILE-aware
  (Debug/Release/TSan/ASan). Antes delegaba a un Makefile interno que siempre
  compilaba en Release.
- `rag-build`: comillas simples para compatibilidad con la expansión de
  `CMAKE_FLAGS` que contiene flags con comillas dobles internas.
- `rag-logs`: log path corregido (`/vagrant/logs/lab/rag-security.log`).
  Antes apuntaba a un fichero inexistente.
- `rag-attach`: nuevo target para attachear al proceso tmux en ejecución.
- `test-components`: RAG Security añadido con ctest.
- `build-unified`: `rag-build` incluido en la secuencia de build completa.

### 1.2 Paper Draft v7 — §5 HKDF Context Symmetry

Se ha añadido una nueva subsección al paper en §5 (Consejo de Sabios):

**"HKDF Context Symmetry: A Pedagogical Case Study in Test-Driven Hardening"**

Estructura de la subsección:
- El defecto: contextos HKDF parametrizados por nombre de componente → ambos lados
  derivan subclaves idénticas → MAC tags válidas en ambas direcciones → el defecto
  es invisible.
- Por qué el type-checker no lo detecta: ambas versiones son `std::string`. El
  compilador, ASan, TSan y clang-tidy aceptan ambas sin warning.
- Cómo TEST-INTEG-3 lo detectó: regresión intencional que restaura el contexto
  erróneo en un lado y aserta que el descifrado falla con MAC error. Bajo la
  implementación correcta → `std::terminate()`. Bajo la defectuosa → éxito (test
  falla).
- Lección: correctness criptográfica es una propiedad del protocolo, no del
  componente. Tests E2E son el mínimo viable.
- RFC 5869 añadido al .bib.

### 1.3 BACKLOG replanificado — BARE-METAL

El stress test bare-metal pasa de P1 bloqueante a bloqueado por hardware físico
(sin fecha). Se añaden dos nuevas tareas P2:
- BARE-METAL-IMAGE: imagen Debian Bookworm hardened, exportable a USB.
- BARE-METAL-VAGRANT: validación de la imagen en VM antes de hardware físico.

Resultado conocido hoy: >33 Mbps sostenidos en VirtualBox, CPU/RAM con amplio
margen. El límite es la NIC emulada, no el pipeline. Documentado abiertamente.

---

## PARTE 2 — ADR-023 (propuesta para revisión)

### ADR-023 — Multi-Layer Plugin Architecture

**Estado:** PROPUESTO — pendiente revisión del Consejo

**Contexto:**

ADR-012 PHASE 1b establece un único hook de plugin:

```c
PluginResult plugin_process_packet(PacketContext* ctx);
```

`PacketContext` representa un paquete de red: IP origen/destino, puertos,
protocolo, payload raw. Es una abstracción de **capa de red**.

El siguiente objetivo (FEAT-PLUGIN-CRYPTO-1, aprobado por el Consejo en DAY 102)
requiere que un plugin pueda operar sobre mensajes cifrados ZeroMQ — payload
protobuf serializado, nonce, tag AEAD. Esto es una abstracción de
**capa de transporte**, fundamentalmente distinta.

Mezclar ambas abstracciones en `PacketContext` sería el mismo error de modelo
mental que el bug HKDF Context Symmetry (ADR-022): usar el mismo tipo para
conceptos semánticamente distintos.

**Decisión propuesta:**

Tres contextos en tres capas, con hooks independientes:

```c
// CAPA DE RED — ya existe (ADR-012 PHASE 1)
PluginResult plugin_process_packet(PacketContext* ctx);

// CAPA DE TRANSPORTE — nueva (ADR-023, PHASE 2)
PluginResult plugin_process_message(MessageContext* ctx);

// CAPA DE APLICACIÓN — futura (ADR-023, PHASE 3)
PluginResult plugin_execute_skill(SkillContext* ctx);
```

**Definición de MessageContext:**

```c
typedef struct {
    uint8_t*  payload;       // buffer del mensaje (in/out)
    size_t    length;        // longitud actual
    size_t    max_length;    // capacidad del buffer
    uint8_t   direction;     // MLD_TX = 0, MLD_RX = 1
    uint8_t   nonce[12];     // nonce 96-bit (in/out)
    uint8_t   tag[16];       // AEAD tag (in/out)
    int32_t   result_code;   // 0 = OK, <0 = error
} MessageContext;
```

**Estrategia de versioning:**

```
PHASE 2a — plugin_process_message() OPCIONAL
  dlsym() → si existe: plugin actúa como transporte
           → si no:    plugin actúa como red (PHASE 1, compatible)
  PLUGIN_API_VERSION = 1 (sin bump)
  core CryptoTransport: READ-ONLY durante toda PHASE 2a

PHASE 2b — plugin_process_message() OBLIGATORIO para plugins de transporte
  PLUGIN_API_VERSION = 2
  CryptoTransport desactivado en componentes que usen plugin crypto

PHASE 2c — CryptoTransport eliminado del core
  Solo cuando TEST-INTEG-4a/4b/4c pasen en todos los componentes
```

**Gates de validación (aprobados en DAY 102):**

| Gate | Descripción |
|------|-------------|
| TEST-INTEG-4a | Round-trip idéntico byte a byte — plugin vs core |
| TEST-INTEG-4b | Equivalencia semántica — ml-detector ve features idénticas en ambos paths |
| TEST-INTEG-4c | Fail-closed ante MAC failure → SIGABRT confirmado |

**Insight Gemini (DAY 102):** Opción A (MessageContext separado) = agnosticismo
de transporte. ZMQ → QUIC sin tocar sniffer.cpp. La capa de red no sabe nada
del cifrado.

**Regla DeepSeek (DAY 102):** core CryptoTransport read-only durante PHASE 2a.
Validación unidireccional: plugin → core. No al revés.

**Prerequisito de este ADR para implementación:**
- ADR-023 aprobado por el Consejo
- ADR-024 diseñado (Dynamic Group Key Agreement) — ver contexto en PARTE 3

---

## PARTE 3 — Contexto para ADR-024 (introducción)

Durante DAY 103 surgió una discusión sobre el mecanismo de distribución de claves
a largo plazo. El modelo actual (seeds estáticos provisionados por `provision.sh`)
es correcto para el MVP y para arXiv. Pero el diseño final requiere algo más:

**Problema:** Si un componente nuevo se une a una familia en runtime (alta
disponibilidad, sustitución en caliente), necesita inferir la misma clave de
familia sin redeploy completo.

**Lo que tenemos:**
- ADR-021: `deployment.yml` como SSOT de topología + concepto de seed families.
- ADR-013: seed-client lee seed estático desde disco.

**Lo que falta (ADR-024):**
- Dynamic Group Key Agreement: protocolo por el que un componente nuevo que
  se une a una familia puede derivar la misma clave sin que el arquitecto
  reprovisione manualmente.
- Requisitos: forward secrecy, resistencia a compromiso parcial, sin coordinador
  central (etcd no debe ser la autoridad criptográfica en producción).
- Candidatos: Noise Protocol IK handshake, Signal double ratchet adaptado a
  grupos, o un esquema propio basado en HKDF con material compartido por familia.

ADR-024 NO bloquea arXiv. Se diseña ahora para poder mencionarlo como trabajo
futuro planificado con arquitectura definida en el paper final.

---

## Preguntas al Consejo

### Q1 — ADR-023: ¿La separación PacketContext / MessageContext / SkillContext es correcta?

¿Hay algún caso donde mezclar capas en un único contexto sea preferible?
¿La definición de `MessageContext` tiene campos que faltan o sobran?

### Q2 — ADR-023 PHASE 2a: ¿`plugin_process_message()` opcional vía dlsym es la estrategia correcta?

Alternativa: bump inmediato a PLUGIN_API_VERSION=2 y hacer el símbolo obligatorio
desde el principio. ¿Qué se gana/pierde con cada enfoque?

### Q3 — ADR-024: ¿Qué protocolo de Group Key Agreement recomendáis?

Opciones conocidas:
- A: Noise Protocol IK — handshake efímero, bien especificado, implementaciones
  maduras (libsodium compatible).
- B: HKDF con material de familia compartido estático + rotación periódica —
  más simple, menos forward secrecy.
- C: Propuesta propia basada en ADR-013 + ADR-021 — máximo control, más trabajo.

¿Hay algún protocolo que no hayamos considerado y que sea mejor para el caso
de uso (componentes C++20, sin TLS, sin PKI central)?

### Q4 — Secuenciación: ¿ADR-023 implementado antes de diseñar ADR-024, o en paralelo?

El Consejo ya aprobó implementar FEAT-PLUGIN-CRYPTO-1 post-arXiv. La pregunta
es si ADR-024 debe estar diseñado (no implementado) antes de abrir
`feature/plugin-crypto`, o si puede diseñarse en paralelo durante la
implementación de ADR-023.

---

*DAY 103 — 31 marzo 2026*
*Branch: feature/bare-metal-arxiv*
*Tests: 25/25 ✅ · Paper: Draft v7*
*Preparado por: Alonso Isidoro Roman + Claude (Anthropic)*