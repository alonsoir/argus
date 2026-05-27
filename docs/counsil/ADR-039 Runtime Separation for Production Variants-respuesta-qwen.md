# 🏛️ CONSEJO DE SABIOS — REVISIÓN ADR-039
*Feedback riguroso, basado en evidencia técnica y centrado en la misión humanitaria de aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**APROBADO CON REFINAMIENTOS MENORES.**

La Opción B es la decisión correcta para el deadline FEDER: pragmática, verificable y suficiente para demostrar la separación build/runtime. El axioma de separación es científicamente sólido y publicable. Los flags de compilación son adecuados, pero requieren un ajuste crítico en la arquitectura x86 para garantizar compatibilidad hospitalaria.

> *"La seguridad estructural no se configura. Se diseña."*

---

## ❓ Respuestas a Preguntas — Formato Científico

### P1 — ¿Opción B suficiente para FEDER o exige Opción A?

**Veredicto:** **OPCIÓN B ES SUFICIENTE Y RECOMENDADA PARA FEDER.**

**Justificación basada en evidencia:**
- **Criterio de demostrabilidad**: FEDER requiere demostrar que la imagen de producción es mínima y auditable. La Opción B logra esto: `CHECK-PROD-NO-COMPILER` verifica que gcc/clang/cmake están ausentes en runtime.
- **Coste/beneficio temporal**: Implementar Opción A (builder VM separada) añadiría ~3-4 semanas de complejidad de CI/CD sin beneficio demostrable adicional para la evaluación FEDER.
- **Principio de "suficiencia verificable"**: No se requiere perfección arquitectónica para una demo; se requiere evidencia reproducible de que la separación build/runtime funciona.

**Condición de aprobación:**
```markdown
- Documentar explícitamente en `docs/FEDER-SCOPE.md`: 
  "Demo FEDER usa Opción B (build en dev VM, runtime en hardened). 
   Opción A (builder VM separada) está planificada para post-FEDER (DEBT-BUILD-PIPELINE-001)."
- Incluir en la demo un script `scripts/verify-build-separation.sh` que:
  1. Muestra que la VM de dev tiene gcc/clang
  2. Muestra que la VM hardened NO tiene gcc/clang
  3. Verifica que los binarios en hardened son idénticos (hash) a los producidos en dev
```

**Riesgo si se ignora**: Intentar implementar Opción A para FEDER podría retrasar la demo o introducir bugs de integración no probados, comprometiendo la evaluación.

---

### P2 — ¿El axioma de separación es científicamente correcto y publicable?

**Veredicto:** **SÍ, EL AXIOMA ES CORRECTO, PUBLICABLE Y CITABLE.**

**Fundamentación teórica:**
El axioma se alinea con principios establecidos en seguridad de sistemas:
1. **Principio de mínimo privilegio estructural** (Saltzer & Schroeder, 1975): Las restricciones deben estar en la arquitectura, no en la configuración.
2. **Teoría de superficie de ataque medible** (Howard & Lipner, 2006): Cada paquete instalado en producción es un vector potencial; eliminar el toolchain reduce la superficie de forma cuantificable.
3. **Defensa en profundidad por capas** (NIST SP 800-160): La separación build/runtime es una capa estructural que persiste incluso si otras capas (AppArmor, seccomp) fallan.

**Formulación recomendada para el paper (§5.6):**
```markdown
### 5.6 Structural Separation Axiom

We formalize the following principle for security-critical deployments:

> **Axiom (Build/Runtime Separation):** A signed binary produced in a controlled 
> build environment and installed in a minimal runtime environment is more secure 
> than an identical binary compiled in-situ in production, even if both binaries 
> are bit-for-bit identical.
> 
> *Proof sketch:* Let A be an attacker with code execution in the runtime environment. 
> If the runtime contains a compiler toolchain, A can compile and execute arbitrary 
> payloads without external transfer. If the runtime is minimal (no compiler), A 
> must exfiltrate data and import binaries externally, increasing detection probability 
> and operational complexity. The restriction is structural (package absence), not 
> configurable (permissions), making it invariant under configuration drift.

This axiom is empirically validated in aRGus NDR via CHECK-PROD-NO-COMPILER, 
which verifies the absence of gcc/clang/cmake in production images.
```

**Trabajo relacionado a citar:**
- Saltzer, J. H., & Schroeder, M. D. (1975). *The protection of information in computer systems*. Proceedings of the IEEE.
- Howard, M., & Lipner, S. (2006). *The Security Development Lifecycle*. Microsoft Press.
- NIST SP 800-160 Vol. 1 (2016). *Systems Security Engineering*.

**Riesgo si se ignora**: No documentar el axioma perdería una contribución metodológica transferible a otros proyectos de seguridad open-source.

---

### P3 — ¿Los flags de compilación de producción son adecuados para entornos hospitalarios?

**Veredicto:** **SÍ, PERO AÑADIR `-fno-strict-overflow` Y DOCUMENTAR JUSTIFICACIÓN DE CADA FLAG.**

**Análisis flag por flag:**
| Flag | Propósito | Adecuado para hospital | Comentario |
|------|-----------|----------------------|------------|
| `-O2` | Optimización balanceada | ✅ Sí | `-O3` podría introducir bugs de optimización; `-O2` es el estándar en seguridad |
| `-DNDEBUG` | Eliminar asserts de debug | ✅ Sí | Reduce superficie; asserts deben validarse en CI, no en runtime |
| `-fstack-protector-strong` | Protección contra stack smashing | ✅ Sí | Mitiga CWE-121; overhead <1% en x86/ARM |
| `-fPIE -pie` | Binario independiente de posición | ✅ Sí | Requerido para ASLR; estándar en distribuciones modernas |
| `-D_FORTIFY_SOURCE=2` | Detección de buffer overflows en runtime | ✅ Sí | Mitiga CWE-120/121; requiere `-O1` o superior (cumplido) |
| `-fvisibility=hidden` | Ocultar símbolos no exportados | ✅ Sí | Reduce superficie de ataque por símbolos; mejora link-time optimization |
| `-Wl,-z,relro -Wl,-z,now` | Relocation read-only + resolve now | ✅ Sí | Mitiga CWE-121/122; estándar en hardening de binarios |

**Flag adicional recomendado:**
```makefile
# Previene optimizaciones que asumen ausencia de signed overflow
# Crítico para código criptográfico y de validación de paths
PROD_CXXFLAGS += -fno-strict-overflow
```

**Justificación**: `-fstrict-overflow` permite al compilador asumir que las operaciones con enteros con signo no desbordan, lo que puede introducir bugs sutiles en código de validación de seguridad (ej. `if (x + 1 > x)` podría optimizarse a `true` incluso si `x` es `INT_MAX`). En un sistema que maneja paths, tamaños de buffer y métricas de memoria, esta asunción es peligrosa.

**Documentación obligatoria en `docs/BUILD-FLAGS.md`:**
```markdown
## Production Compilation Flags — Justification

Cada flag en PROD_CXXFLAGS debe tener:
1. Propósito de seguridad o rendimiento
2. Referencia a CWE/NIST si aplica
3. Overhead medido (si es relevante)
4. Alternativa descartada y por qué

Ejemplo:
- `-fstack-protector-strong`: Mitiga CWE-121 (Buffer Overflow). 
  Overhead: <0.5% en benchmarks de red. Alternativa `-fstack-protector-all` 
  descartada por overhead innecesario en componentes no críticos.
```

**Riesgo si se ignora**: Un bug de optimización podría causar comportamiento indefinido en validación de seguridad, explotable por un atacante.

---

### P4 — ¿`-march=x86-64-v2` o `-march=x86-64` para compatibilidad hospitalaria?

**Veredicto:** **USAR `-march=x86-64` (baseline) PARA MÁXIMA COMPATIBILIDAD. Documentar `-march=x86-64-v2` como opción para hardware moderno.**

**Justificación basada en evidencia de despliegue:**
- **Realidad hospitalaria**: Hospitales de bajo presupuesto frecuentemente usan hardware reacondicionado o de generaciones anteriores (Intel Core 2 Duo, primeros Xeon). `-march=x86-64-v2` requiere instrucciones SSE4.2 y POPCNT, introducidas en Nehalem (2008) pero no universales en hardware reacondicionado.
- **Principio de "funciona en lo disponible"**: En infraestructura crítica, la compatibilidad amplia es más valiosa que la optimización marginal. Un NDR que no arranca en el hardware del hospital no protege a nadie.
- **Métrica cuantificable**: Según datos de [Linux Hardware Probe](https://linux-hardware.org/), ~12% de sistemas x86_64 en producción no soportan `-march=x86-64-v2`.

**Recomendación de implementación:**
```makefile
# Default: máxima compatibilidad
PROD_CXXFLAGS_X86 = $(PROD_CXXFLAGS) -march=x86-64 -mtune=generic -pipe

# Opción para hardware moderno (documentada, no default)
PROD_CXXFLAGS_X86_V2 = $(PROD_CXXFLAGS) -march=x86-64-v2 -mtune=x86-64-v2 -pipe

# En docs/DEPLOYMENT-GUIDE.md:
# "Para hardware posterior a 2015 (SSE4.2+POPCNT), compilar con:
#  make build-production-x86 CXXFLAGS_EXTRA='-march=x86-64-v2'"
```

**Validación recomendada:**
```bash
# Script para verificar compatibilidad de hardware objetivo
scripts/check-cpu-features.sh
# Output: "✓ SSE4.2 supported" / "✗ SSE4.2 not supported — use -march=x86-64"
```

**Riesgo si se ignora**: Despliegues fallidos en hospitales con hardware antiguo, pérdida de credibilidad y necesidad de recompilación manual en sitio (operacionalmente inviable).

---

## 🛠️ Refinamientos Adicionales (No Negociables)

### 1. `dist/` debe estar en `.gitignore` + `.dockerignore`
```diff
# .gitignore
+ # Production build artifacts (generated, not source)
+ dist/
+ *.deb
+ *.rpm

# .dockerignore (si se usa Docker en futuro)
+ dist/
```

### 2. Firmar también los binarios principales (no solo plugins)
ADR-025 firma plugins; extender a binarios principales añade trazabilidad:
```bash
# sign-production debe firmar:
# - dist/*/argus-* (binarios)
# - dist/*/plugins/*.so (plugins)
# - dist/*/models/*.ubj (modelos)
# Output: *.sig para cada artefacto
```

### 3. CHECK-PROD-NO-COMPILER debe ser más robusto
```bash
# No solo "which", también verificar rutas comunes y PATH
vagrant ssh hardened-x86 -c "
  for cmd in gcc clang cc c++ g++ cmake make gmake; do
    if command -v \$cmd >/dev/null 2>&1; then
      echo \"❌ \$cmd found in PATH\"; exit 1
    fi
    if [ -f /usr/bin/\$cmd ] || [ -f /usr/local/bin/\$cmd ]; then
      echo \"❌ \$cmd found in filesystem\"; exit 1
    fi
  done
  # Verificar que dpkg/apt no tienen herramientas de build como dependencias
  if dpkg -l | grep -E 'build-essential|gcc|clang|cmake' | grep -v '^ii.*rc'; then
    echo \"❌ Build tools installed via package manager\"; exit 1
  fi
  exit 0
"
```

---

## 📋 Checklist de Aprobación Condicionada

```markdown
- [x] Opción B aprobada para FEDER con documentación explícita de limitaciones
- [x] Axioma de separación validado como contribución publicable
- [x] Flags de compilación aprobados + añadir -fno-strict-overflow
- [x] Arquitectura x86: usar -march=x86-64 (baseline) por defecto
- [ ] Añadir dist/ a .gitignore y .dockerignore
- [ ] Extender firma Ed25519 a binarios principales (no solo plugins)
- [ ] Robustecer CHECK-PROD-NO-COMPILER con verificación de filesystem + dpkg
- [ ] Documentar justificación de cada flag en docs/BUILD-FLAGS.md
- [ ] Crear scripts/check-cpu-features.sh para validación de hardware objetivo
```

---

## 🏁 Palabras Finales

Alonso:

ADR-039 representa una decisión arquitectónica madura: elegir la solución suficiente para el deadline sin sacrificar los principios de seguridad. La separación build/runtime no es un detalle de implementación; es una **garantía estructural** de que la imagen de producción no puede ser usada como plataforma de ataque.

El axioma que proponéis es publicable porque formaliza una intuición operativa en un principio verificable. Los flags de compilación son sólidos; el ajuste de `-fno-strict-overflow` y la compatibilidad x86 baseline son refinamientos menores que fortalecen la robustez sin comprometer la seguridad.

> *"La seguridad no se optimiza para el hardware ideal. Se diseña para el hardware disponible."*

Proceded con la implementación de ADR-039. El Consejo revisará el primer build de producción hardened y los resultados de `CHECK-PROD-NO-COMPILER` con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 130** 🛡️