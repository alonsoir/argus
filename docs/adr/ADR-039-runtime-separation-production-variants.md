# ADR-039: Build/Runtime Separation for Production Variants

**Estado:** APROBADO — Consejo de Sabios 8/8, DAY 130
**Fecha:** DAY 130 — 25 Abril 2026
**Autor:** Alonso Isidoro Román
**Relacionado con:**
- ADR-030 (aRGus-AppArmor-Hardened — variante de producción)
- ADR-031 (aRGus-seL4-Genode — investigación)
- ADR-025 (Plugin Integrity Verification via Ed25519)
- BACKLOG-FEDER-001 (demo FEDER, deadline 22 septiembre 2026)

---

## 1. Contexto y Motivación

ADR-030 especifica que la imagen de producción debe ser mínima: sin compiladores,
sin herramientas de debug, sin dependencias de desarrollo. Sin embargo, ADR-030
no especifica *cómo* se producen los binarios que se instalan en esa imagen.

Existen dos enfoques posibles:

**Opción A — Build en imagen separada (builder VM):**
Una VM de build dedicada compila, genera `.deb` firmados y los deposita en `dist/`.
La imagen hardened solo ejecuta `dpkg -i`.

**Opción B — Build en VM de desarrollo, runtime en imagen hardened:**
La VM de desarrollo (aRGus-dev, ya existente) compila con flags de producción
mediante targets Makefile dedicados (`make build-production-x86`,
`make build-production-arm64`). Los binarios resultantes se depositan en `dist/`
y se instalan en la imagen hardened via provisioner Vagrant.

Este ADR documenta la elección entre ambas opciones y sus consecuencias.

---

## 2. Decisión

**Se adopta la Opción B — Build en VM de desarrollo, runtime en imagen hardened.**

La Opción A (builder VM separada) es arquitectónicamente más correcta a largo plazo
pero introduce complejidad innecesaria para el deadline FEDER (1 agosto 2026 go/no-go).
La Opción B reutiliza infraestructura existente y es suficiente para demostrar la
separación build/runtime en la demo FEDER.

La Opción A se documenta como evolución post-FEDER (DEBT-BUILD-PIPELINE-001).

**Aprobado por Consejo de Sabios 8/8, DAY 130.**
Ver acta: `docs/consejo/CONSEJO-ADR039-DAY130.md`

---

## 3. Justificación de seguridad

### Por qué el compilador NO debe estar en producción

Un compilador en la imagen de producción amplía la superficie de ataque de forma
significativa:

1. **Compilación de payloads en tiempo de ejecución (Living off the Land):**
   Si un atacante consigue ejecución de código arbitrario, encuentra gcc/clang/cmake
   listos para compilar y ejecutar código malicioso adicional sin necesidad de
   transferencia de binarios externos — aumentando drásticamente su probabilidad
   de detección por aRGus.

2. **CVEs en el toolchain:** gcc, clang, make, cmake, binutils acumulan CVEs
   regularmente. Cada paquete de desarrollo instalado en producción es superficie
   de ataque adicional cuantificable.

3. **Tamaño de imagen y superficie de ataque medible:** La reducción de paquetes
   instalados es una métrica publicable en el paper (§5 Draft v17).

### Axioma de Separación Build/Runtime (BSR)

> **Dado un sistema S con un conjunto de componentes C, si el subconjunto de
> componentes necesarios para la compilación C_build está ausente del entorno
> de ejecución E_runtime, entonces la superficie de ataque de E_runtime es
> estrictamente menor que la de E_runtime ∪ C_build, para cualquier ataque
> que requiera C_build. La verificación criptográfica de integridad de los
> binarios en E_runtime es condición necesaria para que BSR sea efectivo.**
>
> *Corolario operativo:* La restricción es estructural (ausencia de paquetes),
> no configurable (permisos). Un atacante con ejecución arbitraria en E_runtime
> debe exfiltrar datos e importar binarios externamente, aumentando su probabilidad
> de detección. Esta propiedad es invariante bajo configuration drift.

**Supuesto de confianza explícito (supply chain):** La seguridad del binario de
producción es tan buena como la seguridad del entorno de build. Si la VM de
desarrollo está comprometida, el binario firmado también lo está. Este supuesto
("trusted build environment assumption") debe declararse explícitamente en el
paper §5 y en la documentación de despliegue.

**Referencias:**
- Saltzer, J. H., & Schroeder, M. D. (1975). *The protection of information in
  computer systems.* Proceedings of the IEEE. (Principio de mínimo privilegio)
- Howard, M., & Lipner, S. (2006). *The Security Development Lifecycle.*
  Microsoft Press. (Attack Surface Reduction)
- NIST SP 800-160 Vol. 1 (2016). *Systems Security Engineering.*
- Manadhata, P. K., & Wing, J. M. (2011). *An attack surface metric.*
  IEEE Transactions on Software Engineering.

---

## 4. Implementación

### 4.1 Flags de compilación de producción

Los targets `make build-production-*` compilan con los siguientes flags,
aprobados por el Consejo 8/8 con enmiendas DAY 130:

```makefile
# Flags base de producción — aprobados Consejo 8/8 DAY 130
PROD_CXXFLAGS = -O2 -DNDEBUG \
                -fstack-protector-strong \
                -fPIE -pie \
                -D_FORTIFY_SOURCE=2 \
                -fvisibility=hidden \
                -fstack-clash-protection \
                -fno-strict-overflow \
                -Werror=format-security \
                -fasynchronous-unwind-tables \
                -Wl,-z,relro -Wl,-z,now \
                -Wl,-z,noexecstack

# x86-64 — baseline para máxima compatibilidad hospitalaria (Consejo 5/8)
# Hardware objetivo: Intel Core 2 Duo+ (2006), Xeon cualquier generación
# x86-64-v2 disponible como opt-in: make build-production-x86-v2
PROD_CXXFLAGS_X86 = $(PROD_CXXFLAGS) -march=x86-64 -mtune=generic -pipe

# x86-64-v2 — opt-in para hardware moderno (post-2009, SSE4.2+POPCNT)
# Documentado en docs/HARDWARE-REQUIREMENTS.md
PROD_CXXFLAGS_X86_V2 = $(PROD_CXXFLAGS) -march=x86-64-v2 -mtune=generic -pipe

# ARM64 — Raspberry Pi 4/5 (ARMv8.2-A)
PROD_CXXFLAGS_ARM64 = $(PROD_CXXFLAGS) -march=armv8.2-a -pipe

# Solo x86-64, donde el hardware lo soporta:
# -fcf-protection=full  (Control-Flow Integrity — evaluar por componente)
```

**Justificación de cada flag:**

| Flag | Propósito | CWE mitigado |
|------|-----------|-------------|
| `-O2 -DNDEBUG` | Optimización estable, sin asserts de debug | — |
| `-fstack-protector-strong` | Protección contra stack smashing | CWE-121 |
| `-fPIE -pie` | ASLR completo del ejecutable | CWE-119 |
| `-D_FORTIFY_SOURCE=2` | Verificación de límites en funciones de string | CWE-120/121 |
| `-fvisibility=hidden` | Reduce exportación de símbolos | — |
| `-fstack-clash-protection` | Protección contra stack clash en procesos largos | CWE-121 |
| `-fno-strict-overflow` | Previene optimizaciones peligrosas en validación | CWE-190 |
| `-Werror=format-security` | Previene format string bugs | CWE-134 |
| `-fasynchronous-unwind-tables` | Genera core dumps útiles para forense | — |
| `-Wl,-z,relro -Wl,-z,now` | RELRO full + resolución inmediata (anti GOT overwrite) | CWE-122 |
| `-Wl,-z,noexecstack` | Stack no ejecutable | CWE-119 |

**Sin:** `-g` (symbols), `-fsanitize=*`, `-fno-omit-frame-pointer`, `-DDEBUG`.

**Nota sobre símbolos de debug (Kimi DAY 130):** Para capacidad forense en
producción hospitalaria, se pueden generar símbolos separados:
```bash
objcopy --only-keep-debug dist/x86/argus-ml-detector dist/x86/argus-ml-detector.debug
strip --strip-debug dist/x86/argus-ml-detector
# binario.debug se guarda en vault seguro, no en imagen hardened
```
Documentado como DEBT-PROD-DEBUG-SYMBOLS-001 (backlog v1.1).

### 4.2 Estructura de directorios

```
dist/
  x86/
    argus-sniffer
    argus-ml-detector
    argus-rag-ingester
    argus-rag-security
    argus-firewall-acl-agent
    argus-etcd-server
    plugins/
      xgboost_plugin.so
      xgboost_plugin.so.sig       <- firma Ed25519 (ADR-025)
    models/
      xgboost_cicids2017_v2.ubj
      xgboost_cicids2017_v2.ubj.sig
    configs/
      *.json
    SHA256SUMS                    <- checksums obligatorios (ChatGPT DAY 130)
  arm64/
    (misma estructura)
  README.md                       <- "Artefactos generados. No editar manualmente."
```

**CRÍTICO:** `dist/` está en `.gitignore`. Los artefactos binarios no se versionan.

### 4.3 Targets Makefile

```makefile
build-production-x86:
    # Compila con flags de producción x86 (baseline) en la VM de desarrollo
    # Output: dist/x86/

build-production-x86-v2:
    # Opt-in: flags x86-64-v2 para hardware moderno (SSE4.2+POPCNT)
    # Output: dist/x86-v2/

build-production-arm64:
    # Compila con flags de producción arm64 en la VM de desarrollo
    # Output: dist/arm64/

sign-production:
    # Firma Ed25519 (ADR-025): binarios + plugins + modelos
    # Requiere: make build-production-* previo
    # Output: *.sig para cada artefacto

checksums-production:
    # Genera SHA256SUMS para cada artefacto en dist/
    # Verificado por provisioner de hardened VM antes de instalación

dist-clean:
    # Limpia dist/ completamente
```

### 4.4 Vagrantfile hardened-x86

```
vagrant/hardened-x86/Vagrantfile
```

Características:
- Imagen base: `debian/trixie64` (Debian 13 mínima)
- Sin instalación de: gcc, clang, cmake, make, build-essential, gdb, strace
- Instala desde `dist/x86/` via provisioner con verificación de checksums
- Verifica firmas Ed25519 antes de instalar cada artefacto
- AppArmor en enforce mode desde el arranque
- systemd units instaladas desde `etcd-server/config/`
- Ed25519 keypair generado en runtime (ADR-025)

### 4.5 Gates CI obligatorios

```bash
# CHECK-PROD-NO-COMPILER — más robusto que 'which' (Kimi + Qwen DAY 130)
make check-prod-no-compiler

# Implementación:
# vagrant ssh hardened-x86 -c "
#   for cmd in gcc clang cc c++ g++ cmake make gmake; do
#     command -v \$cmd >/dev/null 2>&1 && echo FAIL && exit 1
#   done
#   dpkg -l | grep -E 'build-essential|gcc|clang|cmake' | grep '^ii' && exit 1
#   exit 0
# "

# CHECK-PROD-CHECKSEC — verifica hardening de binarios (ChatGPT DAY 130)
make check-prod-checksec
# checksec --file=dist/x86/argus-* → PIE, RELRO full, NX enabled

# CHECK-PROD-PIPELINE-6/6 — pipeline arranca en hardened VM
# CHECK-PROD-APPARMOR — AppArmor 6/6 enforce, 0 denials
# CHECK-PROD-SIGN — TEST-INTEG-SIGN 7/7 en hardened VM
# CHECK-PROD-SHA256 — verificación de checksums en dist/
```

---

## 5. Métricas publicables (contribución al paper §5)

| Métrica | aRGus-dev | aRGus-production | Delta |
|---------|-----------|-----------------|-------|
| Paquetes instalados | ~450 | < 80 (estimado) | −82% |
| Tamaño imagen disco | ~8 GB | < 2 GB (estimado) | −75% |
| gcc/clang presentes | Sí | No | — |
| CVEs toolchain expuestos | N | 0 | −100% |
| Syscalls permitidas (seccomp) | no restringidas | whitelist por componente | documentar |
| Tiempo arranque pipeline | documentar | documentar | documentar |
| Memoria RSS por componente | documentar | documentar | documentar |

*Valores exactos se completarán tras implementación (DEBT-PROD-METRICS-001).*

---

## 6. Alternativas descartadas

### Opción A — Builder VM separada (descartada para v1, DEBT-BUILD-PIPELINE-001)
Una tercera VM (`vagrant/builder/`) compila, firma y deposita en `dist/`.
La hardened no tiene acceso a la dev VM. Arquitectura ideal a largo plazo.

**Por qué se pospone:**
- Requiere un tercer Vagrantfile y pipeline de CI adicional
- Complejidad innecesaria para demo FEDER (deadline 1 agosto 2026)
- La separación build/runtime ya se garantiza con Opción B en la práctica

**Cuándo activar:** Post-FEDER, cuando haya equipo. DEBT-BUILD-PIPELINE-001.

### Opción C — Compilar en la imagen hardened en tiempo de provisioning y luego eliminar el compilador
**Descartado definitivamente.** El compilador estuvo presente en el sistema
en algún momento. Logs, caché de paquetes y artefactos intermedios pueden
persistir. La restricción debe ser estructural, no temporal.

---

## 7. Deuda técnica generada

| ID | Descripción | Target |
|----|-------------|--------|
| DEBT-BUILD-PIPELINE-001 | Builder VM separada (Opción A) | post-FEDER |
| DEBT-PROD-METRICS-001 | Completar tabla de métricas §5 | DAY 131-135 |
| DEBT-PROD-COMPAT-BASELINE-001 | Documentar decisión x86-64 baseline en HARDWARE-REQUIREMENTS.md | DAY 131 |
| DEBT-PROD-DEBUG-SYMBOLS-001 | Símbolos de debug separados para forense hospitalario | v1.1 |

---

## 8. Consecuencias

**Positivas:**
- Imagen de producción sin compilador — restricción estructural, no configurable
- Reutilización de infraestructura existente (VM de dev)
- Métricas publicables: reducción de superficie de ataque cuantificada
- Viable para deadline FEDER (1 agosto 2026 go/no-go)
- Sin cambios en el código del pipeline aRGus
- CHECK-PROD-NO-COMPILER + CHECK-PROD-CHECKSEC como gates CI verificables

**Negativas / Riesgos:**
- La VM de dev es confianza implícita en el build ("trusted build environment
  assumption") — documentado explícitamente, no ocultado
- Cross-compilation para ARM64 desde x86 puede requerir `aarch64-linux-gnu-g++`
  en la VM de dev
- `dist/` no debe commitearse — `.gitignore` obligatorio

---

## 9. Tests requeridos

| Test | Descripción | Gate |
|------|-------------|------|
| CHECK-PROD-NO-COMPILER | gcc/clang/cmake ausentes + dpkg verify | BLOQUEANTE |
| CHECK-PROD-CHECKSEC | PIE + RELRO full + NX en todos los binarios | BLOQUEANTE |
| CHECK-PROD-SHA256 | Checksums verificados antes de instalación | BLOQUEANTE |
| CHECK-PROD-PIPELINE-6/6 | Pipeline 6/6 RUNNING en imagen hardened | BLOQUEANTE |
| CHECK-PROD-APPARMOR | AppArmor 6/6 enforce, 0 denials | BLOQUEANTE |
| CHECK-PROD-SIGN | TEST-INTEG-SIGN 7/7 en hardened VM | BLOQUEANTE |

---

## 10. Decisiones del Consejo de Sabios — DAY 130 (8/8)

| Pregunta | Decisión | Votos |
|---------|----------|-------|
| P1: Opción B para FEDER | APROBADA | 8/8 |
| P2: Axioma BSR publicable | APROBADO con matización supply chain | 8/8 |
| P3: Flags de compilación | APROBADOS con enmiendas (ver sección 4.1) | 8/8 |
| P4: `-march=x86-64` baseline | APROBADO como default | 5/8 |
| P4: `-march=x86-64-v2` opt-in | APROBADO como target adicional | 8/8 |

Ver acta completa: `docs/consejo/CONSEJO-ADR039-DAY130.md`

---

*Via Appia Quality — La seguridad no se instala. Se diseña.*
*DAY 130 — 25 Abril 2026 — Aprobado Consejo de Sabios 8/8*