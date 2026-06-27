## Kimi — Evaluación ADR-039 — Build/Runtime Separation

*Respuesta al Consejo de Sabios — DAY 131*

---

### Posición general

**El ADR-039 es sólido, necesario y viable.** La separación build/runtime no es opcional en un sistema que procesará tráfico de red en hospitales. Apruebo el ADR con modificaciones menores en los flags de compilación y la arquitectura de firma.

---

### P1 — ¿Opción B suficiente para FEDER o se exige Opción A?

**Veredicto: Opción B es suficiente para FEDER. No se exige Opción A para el go/no-go del 1 de agosto.**

**Razonamiento:**

El objetivo de la demo FEDER es demostrar funcionalidad y arquitectura de seguridad, no una cadena de suministro de build reproducible al nivel de distribución Linux. La Opción B garantiza la invariante crítica: **el compilador nunca está presente en la imagen de runtime**. Eso es suficiente para:

- Demostrar la separación conceptual build/runtime a evaluadores
- Cumplir el axioma de separación (el runtime no puede compilarse a sí mismo)
- Mantener el deadline del 1 de agosto

**Condición:** La Opción B debe incluir un **SBOM (Software Bill of Materials)** mínimo. Cada `.deb` o binario en `dist/` debe acompañarse de un manifest que liste:
- Hash SHA-256 del binario
- Commit del repo usado para compilar
- Versión del compilador (`gcc --version` capturado en build time)
- Lista de librerías dinámicas linkeadas (`ldd` output)

Esto mitiga el riesgo de "confianza implícita en la VM de dev" documentado en la sección 8.

**Cuándo activar Opción A:** Post-FEDER, cuando el proyecto busque certificación o despliegue en múltiples hospitales con builds reproducibles. No antes.

---

### P2 — ¿El axioma de separación es científicamente correcto y publicable?

**Veredicto: Sí, pero requiere matización para ser publicable en revisión por pares.**

**Análisis del axioma:**

> *"Un binario firmado producido en un entorno controlado de desarrollo e instalado en un entorno de runtime mínimo es más seguro que un binario compilado in-situ en producción, incluso si ambos binarios son idénticos."*

**Fortalezas científicas:**
- Es una instanciación del principio de **mínimo privilegio** aplicado a la superficie de ataque del runtime
- Es observable y verifiable (`CHECK-PROD-NO-COMPILER`)
- Tiene precedente en la literatura: "Software debloating" (Quach et al., NDSS 2018), "Attack Surface Reduction" (Manadhata & Wing, 2011)

**Matizaciones necesarias para publicación:**

1. **"Más seguro" es una orden parcial, no total.** Es más seguro *respecto a la clase de ataques que requieren un compilador en el objetivo*. No es más seguro contra todos los vectores (por ejemplo, un buffer overflow en el binario precompilado sigue siendo explotable).

2. **La firma Ed25519 (ADR-025) es parte del axioma.** Sin verificación de firma en el runtime, la separación build/runtime no garantiza integridad. El axioma debería leerse como un compuesto: separación + verificación de integridad.

3. **"Entorno controlado" necesita definición operativa.** ¿Qué significa "controlado"? ¿Air-gapped? ¿Con acceso SSH restringido? Para un paper, definidlo como: *"entorno de build con acceso de red restringido, sin secretos de producción, y con logs de auditoría de todos los comandos ejecutados"*.

**Redacción publicable propuesta:**

> **Principio de Separación Build/Runtime (BSR):** *Dado un sistema S con un conjunto de componentes C, si el subconjunto de componentes necesarios para la compilación C_build está ausente del entorno de ejecución E_runtime, entonces la superficie de ataque de E_runtime es estrictamente menor que la de E_runtime ∪ C_build, para cualquier ataque que requiera C_build. La verificación criptográfica de integridad de los binarios en E_runtime es condición necesaria para que BSR sea efectivo.*

Esto es formalizable, verificable y citable.

---

### P3 — ¿Flags de compilación adecuados para entornos hospitalarios?

**Veredicto: Aceptables con modificaciones. Faltan flags críticos para entornos de alta disponibilidad médica.**

**Flags actuales:**
```makefile
-O2 -DNDEBUG -fstack-protector-strong -fPIE -pie -D_FORTIFY_SOURCE=2 -fvisibility=hidden -Wl,-z,relro -Wl,-z,now
```

**Flags que faltan y deberían añadirse:**

| Flag | Justificación hospitalaria |
|------|---------------------------|
| `-Werror=format-security` | Previene format string bugs en logs de alertas médicas |
| `-fstack-clash-protection` | Protección contra stack clash en procesos de larga duración (sniffer, detector) |
| `-fcf-protection=full` | Control-Flow Integrity — esencial si el hospital requiere mitigaciones Spectre/Meltdown nivel empresarial |
| `-Wl,-z,noexecstack` | El stack no debe ser ejecutable nunca en un sistema de seguridad de red |
| `-Wl,-z,noexecheap` | El heap no debe ser ejecutable (si el linker lo soporta) |
| `-fomit-frame-pointer` | **Quitar de la lista de "sin"** — en producción SÍ se omite para dificultar stack traces a atacantes, pero complica debugging. Para hospitales: mantened `-fno-omit-frame-pointer` para que un crash genere core dump útil para forense. |
| `-fsanitize=cfi` (clang) | Control-flow integrity si usáis clang en lugar de gcc |

**Flags que deberían quitarse/reevaluarse:**

- `-fvisibility=hidden`: Correcto para librerías, pero para binarios ejecutables el efecto es mínimo. No daña, pero no aporta mucho.

**Flags de debug en producción hospitalaria:**

El ADR dice "Sin: `-g`". **Esto es discutible.** En un hospital, si `argus-ml-detector` crashea a las 3 AM durante un incidente de ransomware, necesitáis un core dump con símbolos para analizarlo sin recompilar. Considerad:

```makefile
# Opción: símbolos separados
PROD_CXXFLAGS += -g
PROD_LDFLAGS += -Wl,--strip-debug
# Luego: objcopy --only-keep-debug binario binario.debug
# En la VM hardened: binario sin símbolos, binario.debug en vault seguro
```

Esto da la seguridad de no exponer símbolos en el runtime pero preserva la capacidad forense.

**Veredicto final:** Añadid `-fstack-clash-protection`, `-fcf-protection=full`, `-Wl,-z,noexecstack` y considerad símbolos de debug separados. El resto es correcto.

---

### P4 — `-march=x86-64-v2` vs `-march=x86-64` (baseline)

**Veredicto: Usad `-march=x86-64` (baseline) para la imagen de producción hospitalaria.**

**Análisis de compatibilidad:**

| Nivel | Instrucciones añadidas | Compatibilidad hardware hospitalario |
|-------|------------------------|--------------------------------------|
| `x86-64` (baseline) | SSE2 | 100% — cualquier CPU x86-64 desde 2003 |
| `x86-64-v2` | SSE3, SSSE3, SSE4.1, SSE4.2, POPCNT | ~95% — requiere CPU ~2008+ |
| `x86-64-v3` | AVX, AVX2, BMI1, BMI2, FMA | ~70% — requiere CPU ~2013+ |
| `x86-64-v4` | AVX-512 | ~10% — requiere CPU ~2017+ |

**Contexto hospitalario:**

Los hospitales tienen infraestructura heterogénea y ciclos de renovación lentos (5-10 años). Es común encontrar:
- Servidores Dell/HP de 2010-2015 en salas de servidores
- VMs en hipervisores VMware ESXi con vMotion entre hosts de diferentes generaciones
- Hardware "industrial" para IoT médico con CPUs Atom o Celeron antiguos

Si compiláis con `-march=x86-64-v2` y el hospital intenta desplegar en un host que solo soporta baseline, el binario fallará con **Illegal instruction (SIGILL)** en tiempo de ejecución. Esto no es un error de linking ni de dependencia — es un crash inmediato y silencioso si no hay logging previo.

**Estrategia recomendada:**

```makefile
# Default hospitalario: máxima compatibilidad
PROD_CXXFLAGS_X86 = $(PROD_CXXFLAGS) -march=x86-64 -mtune=generic -pipe

# Variante optimizada (opt-in, no default):
PROD_CXXFLAGS_X86_V2 = $(PROD_CXXFLAGS) -march=x86-64-v2 -mtune=generic -pipe
```

**Argumento para el paper:** Podéis argumentar que aRGus es "hospital-ready" porque no asume hardware reciente. La optimización v2 se ofrece como variante, no como default. Esto es una ventaja competitiva frente a soluciones que requieren AVX2 o superior.

**Excepción:** Si el detector de ML requiere instrucciones SIMD para rendimiento real-time, ofreced dos builds: `argus-ml-detector-baseline` y `argus-ml-detector-avx2`, con detección en el provisioner. Pero el default debe ser baseline.

---

### Observaciones adicionales sobre el ADR-039

#### 1. `dist/` en `.gitignore`
El ADR menciona que `dist/` no debe commitearse. **Esto es crítico.** Añadid también:
```
dist/
*.deb
*.sig
!dist/.gitkeep
```
Y un `README.md` en `dist/` que explique que los binarios se generan en build time y no deben versionarse.

#### 2. CHECK-PROD-NO-COMPILER como gate CI
La implementación propuesta usa `which gcc clang cc c++ g++ cmake make`. **Esto no es suficiente.** Un atacante sofisticado podría instalar el compilador en un path no estándar. Usad:
```bash
dpkg -l | grep -E "gcc|clang|cmake|make|build-essential" && exit 1 || exit 0
```
Esto verifica la base de datos de paquetes, no solo el PATH.

#### 3. Verificación de firma en runtime (ADR-025)
El ADR asume que los binarios están firmados, pero no especifica **cuándo** se verifica la firma. En un hospital, la verificación debe ocurrir:
- En el provisioner (al instalar)
- En cada arranque del servicio (opcional, pero recomendado para detectar tampering post-instalación)

Considerad añadir un `argus-integrity-check` que corra antes de `argus-sniffer` en el orden de arranque systemd.

#### 4. Métricas publicables
La tabla de métricas es buena, pero añadid:
- **Tiempo de arranque del pipeline** (dev vs production) — los hospitales valoran el tiempo de recuperación ante desastre
- **Memoria residente máxima** por componente — relevante para sizing de VMs hospitalarias

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Justificación |
|----------|-----------|---------------|
| **P1** | Opción B aprobada para FEDER | Suficiente para demostrar separación; requiere SBOM mínimo |
| **P2** | Axioma publicable con matización | Formalizar como principio BSR con condición de verificación criptográfica |
| **P3** | Flags aceptables con modificaciones | Añadir `-fstack-clash-protection`, `-fcf-protection=full`, `-Wl,-z,noexecstack`; considerar símbolos de debug separados |
| **P4** | `-march=x86-64` (baseline) | Compatibilidad hospitalaria heterogénea; v2 como variante opt-in |

**Moción:** Propongo que el ADR-039 se apruebe con las enmiendas técnicas indicadas, y que se cree `DEBT-PROD-COMPAT-BASELINE-001` para documentar la decisión de baseline x86-64 como default hospitalario.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*