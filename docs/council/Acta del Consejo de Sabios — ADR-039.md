# Acta del Consejo de Sabios — ADR-039
*DAY 130 — 25 Abril 2026*

**Documento revisado:** ADR-039 (Build/Runtime Separation for Production Variants)
**Quórum:** 8/8 — Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral
**Resultado:** APROBADO con enmiendas

---

## Veredicto global

**ADR-039 APROBADO — 8/8.**
Opción B aprobada para demo FEDER. Enmiendas técnicas incorporadas al documento.
Listo para implementación en DAY 131.

---

## Respuestas por pregunta

### P1 — ¿Opción B suficiente para FEDER o se exige Opción A?

**Decisión: 8/8 Opción B aprobada. Opción A → DEBT-BUILD-PIPELINE-001 post-FEDER.**

Argumentos convergentes del Consejo:

- La demo FEDER requiere demostrar separación build/runtime funcional, no un pipeline
  de CI industrial. La Opción B logra la invariante crítica: el compilador nunca
  está presente en la imagen de runtime.
- La Opción A añadiría ~3-4 semanas de complejidad (tercer Vagrantfile, orquestación
  de dist/, gestión de claves entre VMs) sin beneficio demostrable para la evaluación.
- La VM de desarrollo ya es confiable por la REGLA EMECAS: se reconstruye desde cero
  en cada sesión.

**Condición impuesta (ChatGPT + Qwen):** Los artefactos en `dist/` deben acompañarse
de SHA256SUMS obligatorio. El provisioner de la hardened VM verifica checksums antes
de instalar. Fallo en mismatch = provisioning abortado.

**Condición adicional (Kimi):** SBOM mínimo por artefacto: hash SHA-256, commit del
repo, versión del compilador, lista de librerías dinámicas (`ldd` output).
Documentado como DEBT-PROD-METRICS-001.

---

### P2 — ¿El axioma de separación es científicamente correcto y publicable?

**Decisión: 8/8 CORRECTO y PUBLICABLE con matización obligatoria.**

El axioma captura una propiedad de seguridad estructural real alineada con:
- Principio de mínimo privilegio (Saltzer & Schroeder, 1975)
- Attack Surface Reduction (Howard & Lipner, 2006)
- Defensa en profundidad por capas (NIST SP 800-160)
- "Living off the Land" como vector bloqueado estructuralmente (Gemini)

**Matización obligatoria para publicación (Claude + DeepSeek + Kimi):**
El axioma asume que el entorno de build no está comprometido. Si lo está, el binario
firmado también lo está — supply chain attack clásico. El paper §5 debe declarar
explícitamente el "trusted build environment assumption". No es un defecto del diseño;
es honestidad científica necesaria.

**Formulación publicable aprobada (síntesis Kimi + Qwen):**

> "Dado un sistema S con un conjunto de componentes C, si el subconjunto de
> componentes necesarios para la compilación C_build está ausente del entorno
> de ejecución E_runtime, entonces la superficie de ataque de E_runtime es
> estrictamente menor que la de E_runtime ∪ C_build, para cualquier ataque
> que requiera C_build. La verificación criptográfica de integridad de los
> binarios en E_runtime es condición necesaria para que el principio BSR sea
> efectivo."

**Referencias a citar en §5:**
- Saltzer & Schroeder (1975) — Principio de mínimo privilegio
- Howard & Lipner (2006) — Security Development Lifecycle
- NIST SP 800-160 Vol. 1 (2016) — Systems Security Engineering
- Manadhata & Wing (2011) — An attack surface metric (IEEE TSE)

---

### P3 — ¿Los flags de compilación son adecuados para entornos hospitalarios?

**Decisión: 8/8 APROBADOS con enmiendas. Flags adicionales obligatorios.**

Flags base aprobados como correctos y alineados con Debian hardening defaults,
CIS Benchmarks, y OpenSSF recommendations.

**Enmiendas obligatorias (consenso 6+/8):**

| Flag añadido | Propuesto por | Justificación |
|---|---|---|
| `-fstack-clash-protection` | ChatGPT, Gemini, Kimi | Protege procesos de larga duración (sniffer, detector) |
| `-fno-strict-overflow` | Qwen | Crítico para código de validación de paths y buffers |
| `-Werror=format-security` | Kimi, Mistral | Previene format string bugs en logs de alertas |
| `-fasynchronous-unwind-tables` | Mistral | Genera core dumps útiles para forense |
| `-Wl,-z,noexecstack` | Kimi | Stack nunca ejecutable en sistema de seguridad |

**Flag condicional (evaluación por componente):**
- `-fcf-protection=full` (solo x86-64 moderno, clang) — ChatGPT, Gemini, Kimi.
  Documentado como evaluación post-implementación.

**Flag propuesto pero no obligatorio para v1:**
- `-ftrivial-auto-var-init=zero` (DeepSeek) — inicializa stack a cero. Útil pero
  requiere gcc ≥12. Documentado como mejora futura.
- `-D_GLIBCXX_ASSERTIONS` (DeepSeek) — aserciones de libstdc++ sin overhead debug.
  Evaluar en CI.

**CHECK-PROD-CHECKSEC (ChatGPT):** Target Makefile que verifica via `checksec`:
PIE enabled, RELRO full, NX enabled en todos los binarios de `dist/`. Gate BLOQUEANTE.

---

### P4 — `-march=x86-64-v2` vs `-march=x86-64` (baseline)

**Decisión: 5/8 `-march=x86-64` como DEFAULT. 8/8 `-march=x86-64-v2` como OPT-IN.**

Posiciones:
- **x86-64 baseline (Claude, Kimi, Qwen, Mistral, ChatGPT):** Hospitales tienen
  infraestructura heterogénea con ciclos de renovación de 5-10 años. Hardware 2008-2012
  es común. Un SIGILL en despliegue es un bloqueante operativo inaceptable.
  Kimi cita Linux Hardware Probe: ~12% de sistemas x86_64 en producción no soportan v2.
- **x86-64-v2 (DeepSeek, Gemini, Grok):** CPUs pre-Nehalem (2008) son <1% en data
  centers hospitalarios europeos en 2026. El beneficio de SSE4.2+POPCNT en
  operaciones de red y hashing es ~10-20%.

**Resolución:** El principio "funciona en lo disponible" prevalece para la imagen
default. Un hospital rural que no puede desplegar aRGus por incompatibilidad de
instrucciones es un hospital sin protección.

**Target adicional aprobado 8/8:** `make build-production-x86-v2` como opt-in
documentado en `docs/HARDWARE-REQUIREMENTS.md`.

**Frase de cierre sobre P4 — Kimi:**
> "La seguridad no se optimiza para el hardware ideal. Se diseña para el hardware
> disponible."

---

## Observaciones adicionales del Consejo

### Robustez de CHECK-PROD-NO-COMPILER (Kimi + Qwen)
`which` no es suficiente. La verificación debe incluir:
1. `command -v` para cada compilador conocido
2. `dpkg -l | grep -E 'build-essential|gcc|clang|cmake'` para verificar base de datos
3. Verificación de paths no estándar (`/usr/local/bin`, `/opt/`)

### `dist/` — control crítico (todos)
- `.gitignore` obligatorio
- `README.md` dentro de `dist/`: "Artefactos generados automáticamente. No editar."
- SHA256SUMS obligatorio, verificado por provisioner antes de instalación

### Firma Ed25519 (DeepSeek + Qwen)
ADR-025 firma plugins. Extender a binarios principales y modelos XGBoost.
`sign-production` debe firmar: binarios + plugins + modelos + configs críticos.

### Símbolos de debug separados para forense (Kimi)
En producción hospitalaria, un crash a las 3 AM durante un incidente de ransomware
requiere capacidad forense sin recompilar. Técnica: `objcopy --only-keep-debug`
genera `binario.debug` que se guarda en vault seguro, no en imagen hardened.
Documentado como DEBT-PROD-DEBUG-SYMBOLS-001.

### Métricas adicionales para el paper (Gemini + Kimi)
Añadir a la tabla §5:
- Número de syscalls permitidas por componente (comparativa seccomp)
- Tiempo de arranque del pipeline (dev vs production)
- Memoria RSS máxima por componente

---

## Decisiones vinculantes

| ID | Decisión | Votos |
|----|----------|-------|
| D1 | Opción B aprobada para FEDER | 8/8 |
| D2 | Axioma BSR publicable con "trusted build environment assumption" | 8/8 |
| D3 | Flags base + enmiendas obligatorias (sección 4.1 ADR-039) | 8/8 |
| D4 | `-march=x86-64` baseline como default | 5/8 |
| D5 | `-march=x86-64-v2` como target opt-in | 8/8 |
| D6 | SHA256SUMS obligatorio en dist/ | 8/8 |
| D7 | CHECK-PROD-CHECKSEC gate BLOQUEANTE | 8/8 |
| D8 | CHECK-PROD-NO-COMPILER via dpkg (no solo which) | 8/8 |

---

## Deuda técnica generada por el Consejo

| ID | Origen | Target |
|----|--------|--------|
| DEBT-BUILD-PIPELINE-001 | Opción A builder VM separada | post-FEDER |
| DEBT-PROD-METRICS-001 | Completar tabla métricas §5 | DAY 131-135 |
| DEBT-PROD-COMPAT-BASELINE-001 | HARDWARE-REQUIREMENTS.md con requisitos CPU | DAY 131 |
| DEBT-PROD-DEBUG-SYMBOLS-001 | Símbolos separados para forense | v1.1 |

---

## Frases del Consejo DAY 130

> "La separación build/runtime no es un detalle de implementación. Es una garantía
> estructural de que la imagen de producción no puede ser usada como plataforma
> de ataque." — Qwen

> "La seguridad no se optimiza para el hardware ideal. Se diseña para el hardware
> disponible." — Kimi

> "Has eliminado otro vector de ataque que requería presencia del compilador.
> Eso es defensa en profundidad real, no prometida." — ChatGPT

> "El axioma BSR es publicable porque formaliza una intuición operativa en un
> principio verificable con tests de CI reproducibles." — DeepSeek

> "Via Appia Quality — Lo que no está presente no puede ser atacado." — Gemini

---

*Consejo de Sabios (8/8) — DAY 130 — 25 Abril 2026*
*ADR-039 APROBADO — Implementación autorizada para DAY 131*