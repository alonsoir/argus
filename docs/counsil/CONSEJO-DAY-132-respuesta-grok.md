El **Consejo de Sabios** ha revisado el backlog y el estado del proyecto en **DAY 132**, con especial atención al avance documental, la integridad de `main` y la preparación de la variante de producción (ADR-030/039). Todas las respuestas se basan en evidencia reproducible, principios de minimización de superficie de ataque, separación de concerns y prácticas establecidas en ingeniería de software de alta integridad y seguridad de sistemas críticos.

### Q1 — Makefile targets de producción: ¿arquitectura correcta?

**Recomendación: Mantener los targets de producción en el Makefile raíz, pero con namespace claro y guardrails fuertes.**

Mantener todo en un único `Makefile` (raíz) es aceptable y pragmático en esta fase del proyecto, siempre que se apliquen las siguientes medidas reproducibles:

- **Namespace explícito**: Prefijar los targets de producción, por ejemplo:
  - `production/build-x86`
  - `production/sign`
  - `production/check-no-compiler`
  - `production/verify`

  Esto evita confusión entre targets de desarrollo y producción (práctica recomendada en proyectos con múltiples configuraciones).

- **Guardrails de ejecución**: Cada target de producción debe comenzar con una comprobación explícita:
  ```make
  ifneq ($(shell which gcc 2>/dev/null),)
    $(error "Production targets must be invoked from dev VM only. Compiler detected.")
  endif
  ```
  O mejor: detectar si se está en la VM hardened mediante un archivo de marca (`/etc/argus-is-production`) o variable de entorno.

- **Documentación obligatoria** en la cabecera del Makefile y en `docs/BUILD-PRODUCTION.md`: “Los targets con prefijo `production/` solo se invocan desde la VM de desarrollo (aRGus-dev). En hardened fallan intencionadamente por ausencia de toolchain.”

Un `Makefile.production` separado añade complejidad (mantenimiento de includes, duplicación de variables comunes) sin beneficio claro en esta escala de proyecto. La evidencia de proyectos similares (Linux kernel, Debian packaging, muchos proyectos open-source de C++) muestra que un Makefile único con condicionales y namespaces es suficiente y más mantenible cuando el número de targets no excede ~50-60.

**Decisión**: Proceder con targets en el Makefile raíz usando namespace `production/`. Esto se considera correcto para la fase actual (pre-FEDER). Post-FEDER se podrá refactorizar si la complejidad crece (registrar como posible deuda técnica menor).

### Q2 — Vagrantfile hardened-x86: ¿debian/bookworm64 o esperar a trixie?

**Recomendación: Usar `debian/bookworm64` (Debian 12) en el Vagrantfile actual, documentar explícitamente el upgrade path a Debian 13 “trixie” para bare-metal y producción real.**

Razones basadas en estado actual (abril 2026):
- Debian 13 (trixie) fue liberada en agosto 2025 y ya tiene actualizaciones (hasta 13.4 en marzo 2026). Ofrece mejoras en hardening (mejores mitigaciones ROP/COP/JOP en amd64/arm64, reproducible builds mejorados, kernel 6.12 LTS).
- Sin embargo, las boxes Vagrant oficiales/community para trixie no son universalmente estables en todos los proveedores (VirtualBox). Existen repositorios que generan boxes actualizadas (ej. basadas en Packer), pero introducir una box no oficial añade riesgo de no reproducibilidad en entornos de terceros (equipo hospitalario, revisores del paper).

Debian 12 (bookworm) es extremadamente estable, tiene soporte de seguridad extendido y es ampliamente usado en entornos críticos. La diferencia en superficie de ataque es manejable si se mantiene la imagen mínima y se aplican los perfiles AppArmor + seccomp.

**Acciones requeridas**:
- En el Vagrantfile y en `docs/HARDWARE-REQUIREMENTS.md`: indicar claramente “Base: Debian 12 (bookworm) para reproducibilidad Vagrant. Target de producción final: Debian 13 trixie (bare-metal o box custom). Upgrade path documentado en sección X.”
- Incluir un target `production/upgrade-to-trixie` o instrucciones paso a paso reproducibles (apt sources, dist-upgrade controlado, verificación post-upgrade de ausencia de toolchain y AppArmor enforcing).
- En el paper (§5): mencionar que las métricas de paquetes/tamaño se miden primero en bookworm y se validan después en trixie, destacando las mejoras de hardening nativas de trixie.

Esta aproximación mantiene la **REGLA EMECAS** intacta (vagrant destroy && up reproducible hoy) y evita bloquear el progreso por inestabilidad de boxes.

### Q3 — BSR axiom: ¿dpkg es suficiente o añadimos which gcc como segunda comprobación?

**Recomendación: Implementar verificación en capas (defense-in-depth), combinando `dpkg` + chequeo de PATH + verificación de binarios críticos.**

El chequeo solo con `dpkg -l | grep` detecta paquetes instalados vía apt, pero no binarios copiados manualmente, instalados desde source o presentes en `/usr/local/bin`, etc. Esto viola parcialmente el espíritu del axioma BSR (Build-time / Runtime Separation): la restricción debe ser estructural y verificable de forma robusta.

**Implementación recomendada para `check-prod-no-compiler`** (ejecutable en el provisioner y como gate CI):
```bash
#!/bin/bash
set -e

# Capa 1: Paquetes vía dpkg (principal)
if dpkg -l | grep -qE '^(ii|hi)\s+(gcc|g\+\+|clang|cmake|make|build-essential|gdb|strace|binutils)'; then
  echo "ERROR: Compilador o herramienta de build detectada vía dpkg"
  exit 1
fi

# Capa 2: Binarios en PATH (defensa adicional)
for tool in gcc g++ cc c++ clang clang++ cmake make ninja gdb strace objdump readelf; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "ERROR: Binario de build detectado en PATH: $tool"
    exit 1
  fi
done

# Capa 3 (opcional pero fuerte): Chequeo de presencia física en directorios comunes
for dir in /usr/bin /usr/local/bin /usr/sbin; do
  if ls "$dir"/{gcc,g++,clang,cmake,make}* 2>/dev/null | grep -q .; then
    echo "ERROR: Binario de toolchain encontrado en $dir"
    exit 1
  fi
done

echo "BSR axiom verificado: ningún compilador presente."
exit 0
```

Esta verificación en múltiples capas es reproducible, auditable y alineada con prácticas de hardening (similar a checks en imágenes distroless o Docker multi-stage). `which` / `command -v` no es exhaustivo solo, pero combinado con `dpkg` y chequeo de directorios sí proporciona evidencia fuerte.

Añadir este script como `tools/check-prod-no-compiler.sh` y llamarlo desde el Makefile y desde el provisioner Vagrant.

### Q4 — Draft v17: revisión de las 4 nuevas secciones (§6.5, §6.8, §6.10, §6.12)

**Evaluación general**: El nivel de rigor es bueno para un draft interno y para una preimpresión arXiv cs.CR en esta etapa temprana del proyecto, pero requiere refuerzos empíricos y citas adicionales antes de subir a arXiv.

**Análisis por sección** (siguiendo método científico reproducible):

- **§6.5 — The RED→GREEN Gate**: Bien fundamentado como contrato no negociable. Reforzar con un diagrama simple del flujo (commit → RED → fix → GREEN → merge) y métricas históricas del proyecto (“en 132 days, X merges, 0 regresiones de seguridad gracias al gate”). Citar prácticas similares en proyectos high-assurance (seL4, Qubes OS).

- **§6.8 — Fuzzing as the Third Testing Layer (libFuzzer)**: Evidencia concreta con harness es positiva. Añadir: número de bugs encontrados/fixed gracias al fuzzer, cobertura alcanzada (líneas/branch), seeds usados y tiempo de ejecución típico. Incluir un extracto mínimo del harness en el listing. Esto eleva de “descripción” a “evidencia empírica”.

- **§6.10 — CWE-78: execv() Without a Shell as a Physical Barrier**: Excelente mención a Thompson (1984) “Trusting Trust”. Reforzar citando CWE-78 directamente y ejemplos de ataques shell injection vs. execve sin shell. Añadir medición: “En aRGus, el 100% de llamadas a ejecución externa usan execv-family sin /bin/sh”.

- **§6.12 — The Build/Runtime Separation Axiom (ADR-039)**: El axioma es defendible. Redactar con precisión: enfatizar la propiedad estructural (“el runtime no puede compilar porque carece de toolchain, independientemente de privilegios obtenidos por un atacante”). Añadir referencia a prácticas equivalentes en contenedores (distroless, multi-stage Docker) y en sistemas certificados (Common Criteria EAL alto). Incluir las métricas de paquetes/tamaño reales una vez completadas.

**Recomendaciones generales para arXiv cs.CR**:
- Añadir al menos una tabla o figura por sección nueva con datos cuantitativos (bugs encontrados, métricas de superficie, tiempos de verificación).
- Incluir sección “Threat Model” explícita si no existe (atacante con ejecución arbitraria en runtime, pero sin capacidad de modificar el build).
- Evidencia reproducible: todos los claims de “mejora de seguridad” deben ir acompañados de comandos o scripts que cualquiera pueda ejecutar (REGLA EMECAS ayuda aquí).
- El nivel actual es suficiente para preprint, pero para aceptación en venues más selectas se necesitaría más evaluación comparativa (vs. soluciones comerciales o baselines sin estas medidas).

No subir todavía a arXiv. Esperar a completar P2 (Makefile production targets + checks) y medir métricas reales en la hardened VM. Revisión del Consejo en DAY 135-137 una vez incorporados los cambios.

**Decisión global del Consejo**:
- Proceder con el plan DAY 133 según lo descrito, incorporando las recomendaciones anteriores.
- Mantener `main` sagrado y REGLA EMECAS obligatoria antes de cualquier merge.
- Todas las modificaciones deben producir artefactos verificables (logs de checks, SHA256SUMS, salida de checksec).

El proyecto avanza de forma metódica y con foco en propiedades de seguridad estructurales. Continuar documentando cada decisión con la misma seriedad.

*Via Appia Quality — La seguridad no se instala. Se diseña.*  
**Consejo de Sabios — DAY 132, 26 Abril 2026**