# ADR-022 — Threat Model Formal y Opción 2 Descartada (Caso Pedagógico)

**Estado:** Aprobado — deuda técnica documentada y descartada
**Fecha:** 2026-03-28 (DAY 100)
**Autores:** Alonso Isidoro Roman + Consejo de Sabios (ChatGPT/OpenAI, Grok/xAI)
**Relacionado:** ADR-013 (seed distribution), ADR-021 (topology SSOT)

---

## Contexto

Durante DAY 99 se detectó y corrigió un bug crítico: contextos HKDF asimétricos
entre emisor y receptor del mismo canal. La causa raíz fue usar el nombre del
**componente** como contexto en lugar del nombre del **canal**.

Durante el análisis de la corrección se evaluaron dos opciones para escalar
a multi-instancia en el futuro (FASE 2). Esta ADR documenta formalmente:

1. El **threat model** del sistema criptográfico actual
2. Por qué la **Opción 2 fue descartada** como deuda técnica inaceptable
3. El **caso pedagógico** del bug de asimetría para el paper arXiv

---

## Threat Model — Sistema Criptográfico Argus

### Activos protegidos

| Activo | Descripción |
|--------|-------------|
| `seed.bin` | 32 bytes aleatorios, raíz de toda la cadena de confianza |
| Claves HKDF derivadas | ChaCha20-Poly1305, 256 bits, efímeras por canal |
| Tráfico inter-componente | Eventos de red, alertas, telemetría, vectores FAISS |
| Configuración (`*.json`) | "JSON is the law" — modificación → comportamiento arbitrario |

### Modelo de amenaza

| Amenaza | Vector | Mitigación actual |
|---------|--------|-------------------|
| Escucha pasiva en ZeroMQ | Red interna comprometida | ChaCha20-Poly1305 IETF |
| Replay de mensajes | Captura y reinyección | Nonce monotónico 96-bit |
| Suplantación de componente | Proceso malicioso en host | seed.bin + HKDF → MAC falla |
| Robo de seed.bin | Acceso físico / root | chmod 0600, mlock() (P2) |
| Replay cross-instancia | Ver Opción 2 abajo | **Opción 2 descartada** |
| Modificación de config JSON | Acceso a filesystem | OS hardening (ADR-019) |
| Inyección en canal RAG | Prompt injection vía telemetría | TinyLlama confinado (ADR-010) |

### Límites del modelo

- **Fuera de scope:** ataques al kernel (eBPF integrity en ADR-015)
- **Fuera de scope:** compromisos de CA / PKI (no se usa PKI — seed-based)
- **Asumido:** el canal de distribución de seeds (`provision.sh`) es seguro
- **Asumido:** instancia única por rol en FASE 1 (ver abajo)

---

## Opción 2 — Descripción y Descarte

### Qué era la Opción 2

En el análisis de FASE 2 (multi-instancia) se propuso incorporar un `instance_id`
en el contexto HKDF para diferenciar instancias del mismo componente:

```cpp
// Opción 2 — DESCARTADA
std::string ctx = std::string("ml-defender:sniffer-to-ml-detector:v1:") + instance_id;
CryptoTransport transport(seed, ctx);
```

La motivación era: si hay `sniffer1` y `sniffer2`, cada uno derivaría
una clave distinta, evitando colisiones.

### Por qué fue descartada

**El problema:** la clave HKDF se deriva del **contexto**. Si emisor y receptor
usan contextos distintos → claves distintas → **MAC error garantizado**.

En el canal `sniffer → ml-detector`:
- `sniffer1` deriva con contexto `...:sniffer1`
- `ml-detector1` debe recibir de `sniffer1` **y** `sniffer2`
- `ml-detector1` no puede saber de antemano qué instancia envía cada mensaje
- → Imposible seleccionar el contexto correcto en el receptor sin metadatos adicionales

Esto reproduce exactamente el **bug de asimetría de DAY 99**, pero estructuralmente,
por diseño. No es un bug corregible — es una contradicción en el modelo.

**Alternativas evaluadas y descartadas:**

| Alternativa | Problema |
|-------------|----------|
| `instance_id` en nonce | El nonce es de 96 bits — reducir entropía útil es inaceptable |
| Handshake previo para negociar contexto | Complejidad de protocolo, superficie de ataque nueva |
| PKI por instancia | Rompe el modelo seed-based, añade CA |

**Decisión:** La Opción 2 es **deuda técnica inaceptable**. Se descarta formalmente.
La solución correcta para multi-instancia es el modelo de **familias de canal** (ADR-021),
donde el contexto pertenece al canal lógico, no a la instancia.

---

## Caso Pedagógico — Bug de Asimetría DAY 99

Este bug merece documentación explícita para el paper arXiv porque ilustra
un principio de diseño criptográfico no obvio.

### El bug

```cpp
// ANTES (bug) — contexto = nombre del componente
// sniffer usaba:    "ml-defender:sniffer:v1"
// ml-detector usaba: "ml-defender:ml-detector:v1"
// → claves HKDF distintas → MAC error en cada mensaje
```

```cpp
// DESPUÉS (corrección) — contexto = nombre del canal
// sniffer usaba:    "ml-defender:sniffer-to-ml-detector:v1"
// ml-detector usaba: "ml-defender:sniffer-to-ml-detector:v1"
// → misma clave HKDF → autenticación correcta
```

### La lección

**El contexto HKDF no identifica quién habla — identifica de qué hablan.**

Es un identificador semántico del canal, no del emisor. Esta distinción es
contraintuitiva: en sistemas de identidad, el contexto suele identificar
a la entidad. En HKDF para canales simétricos, identifica el canal compartido.

### Relevancia para el paper

Este caso es un ejemplo de **error de modelo mental** en sistemas criptográficos:
el desarrollador aplica correctamente la API, pero con semántica incorrecta.
El tipo-checker no puede detectarlo. Los tests de integración sí (TEST-INTEG-1/2/3).

Esto refuerza el argumento del paper sobre la importancia de **Test-Driven Hardening**
(TDH): sin TEST-INTEG-1 (ping cifrado end-to-end), el bug habría llegado a producción.

---

## Consecuencias

**De descartar Opción 2:**
- FASE 1 queda acotada a instancia única por rol — explícitamente documentado
- Multi-instancia requiere FASE 3 (families) — no hay atajos
- El paper puede citar esta decisión como ejemplo de honestidad científica

**Del threat model formal:**
- Superficie de ataque documentada públicamente → revisión externa facilitada
- `mlock()` en seed_client.cpp promovido a P2 explícito
- Falco como complemento de runtime behavioral monitoring (ya documentado)

---

## Estado

| Elemento | Estado |
|----------|--------|
| Bug de asimetría corregido | ✅ DAY 99 (contexts.hpp) |
| Opción 2 descartada | ✅ Esta ADR |
| Threat model documentado | ✅ Esta ADR |
| `mlock()` implementado | ⏳ DEBT-CRYPTO-003a (P2) |
| Caso pedagógico → paper arXiv | ⏳ Sección de diseño |

---

*DAY 100 — 2026-03-28*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*