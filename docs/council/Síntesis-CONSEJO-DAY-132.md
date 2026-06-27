# Consejo de Sabios — DAY 132 — aRGus NDR
*26 Abril 2026 · branch: feature/adr030-variant-a · main @ 18d8e101*

---

## Contexto

DAY 132 ha sido una sesión de documentación y consolidación, no de código de producción.
El pipeline está en 6/6 RUNNING, `make test-all` ALL TESTS COMPLETE, baseline intacto.
El trabajo del día ha sido íntegramente documental y de preparación de infraestructura
para la fase de producción (ADR-030).

---

## Trabajo completado DAY 132

### P0 — Commits de documentación pendientes (arrastre DAY 131)
- **commit `5a22c068`** — `docs/adr/ADR-025.md` (D13 Emergency Patch Protocol),
  `docs/BACKLOG.md`, `docs/continuity/PROMPT_CONTINUE_CLAUDE.md`
- Estado: `main` limpio, REGLA EMECAS superada antes de cualquier acción técnica

### P1 — Paper §5 Draft v17 (arXiv:2604.04952)
- **commit `b7d38d1f`** — `docs/latex/main.tex` + `docs/latex/references.bib`
- **+315 líneas** de contenido nuevo en §5 (The Consejo de Sabios):

  | Subsección nueva | Contenido |
    |-----------------|-----------|
  | §6.5 | The RED→GREEN Gate: Merge as a Non-Negotiable Contract |
  | §6.8 | Fuzzing as the Third Testing Layer (harness libFuzzer concreto) |
  | §6.10 | CWE-78: execv() Without a Shell as a Physical Barrier |
  | §6.12 | The Build/Runtime Separation Axiom (ADR-039) |

- Nuevas referencias BibTeX: `cwe78` (MITRE) + `thompson1984` (Trusting Trust, CACM 1984)
- Acknowledgments actualizado: "132 days of continuous development"
- Attribution corregido: "The **eight** models are credited" (era "seven")
- **Compilación Overleaf verificada** — PDF 42 páginas, tabla de contenidos correcta,
  listings 6–13 numerados correctamente, referencias [16] y [23] integradas

### README — Prerequisites
- **commit `18d8e101`** — Sección `## 🔧 Prerequisites` añadida antes del Quick Start
- Instrucciones de instalación de Vagrant + VirtualBox + make para macOS y Linux
- Nota explícita: "No C++ toolchain required on the host"

### P2 — ADR-030 Variant A (inicio)
- **commit `9b3438fb`** en `feature/adr030-variant-a`
- `docs/HARDWARE-REQUIREMENTS.md` — especificaciones mínimas y recomendadas,
  tabla de plataformas commodity (~150–200 USD), compatibilidad XDP por driver NIC,
  paquetes runtime vs paquetes prohibidos en producción (BSR axiom)
  → cierra **DEBT-PROD-COMPAT-BASELINE-001**
- `vagrant/hardened-x86/Vagrantfile` — VM Debian 12/13, AppArmor enforcing,
  sin compilador, verificación BSR en provisioner, post_up_message con pasos siguientes

---

## Estado de ramas

```
main                     18d8e101  ← sagrado, REGLA EMECAS
feature/adr030-variant-a 9b3438fb  ← P2 en curso
```

---

## Plan DAY 133

### P2 (continuación) — Makefile targets para producción

Los siguientes targets deben añadirse al `Makefile` principal dentro de
`feature/adr030-variant-a`:

| Target | Descripción |
|--------|-------------|
| `build-production-x86` | Compila en dev VM con flags de producción (`-O2 -DNDEBUG`, sin símbolos debug) |
| `sign-production` | Firma todos los binarios de `dist/` con Ed25519 (reutiliza `tools/sign-model.sh`) |
| `checksums-production` | Genera `dist/SHA256SUMS` con sha256sum de cada binario |
| `verify-production` | Verifica SHA256SUMS antes de cualquier arranque en producción |
| `check-prod-no-compiler` | Falla si dpkg detecta gcc/g++/clang/cmake en la VM (ADR-039) |
| `check-prod-checksec` | Ejecuta checksec sobre binarios de `dist/` — verifica PIE, RELRO, NX |

### P3 (backlog DAY 133+) — ADR-030 Variant B ARM64
- `vagrant/hardened-arm64/Vagrantfile`
- Cross-compilation toolchain: `aarch64-linux-gnu-g++` en VM de dev
- libpcap como fallback (XDP inviable en RPi con drivers genéricos)

### Nota sobre arXiv
Draft v17 **no se sube a arXiv todavía**. Esperamos a que P2 esté más
estable y posiblemente a una revisión del Consejo sobre las 4 nuevas
secciones antes de hacerlas públicas.

---

## Preguntas al Consejo

### Q1 — Makefile targets de producción: ¿arquitectura correcta?

El plan es añadir los 6 targets de producción al `Makefile` raíz
(no a un Makefile separado). Los targets de producción solo son
invocables desde la dev VM; fallan si se ejecutan desde la hardened VM
porque no hay compilador.

**¿Es correcto mantenerlos en el Makefile raíz, o recomendáis un
`Makefile.production` separado para evitar confusión?**

### Q2 — Vagrantfile hardened-x86: ¿`debian/bookworm64` o esperar a `trixie`?

El Vagrantfile usa `debian/bookworm64` (Debian 12) porque `debian/trixie64`
(Debian 13) aún no tiene box estable en Vagrant Cloud. El paper menciona
Debian 13 como target de producción.

**¿Recomendáis mantener Debian 12 en el Vagrantfile y documentar el upgrade
path a Debian 13 para bare-metal, o buscar una box de Trixie alternativa?**

### Q3 — BSR axiom: ¿`dpkg` es suficiente o añadimos `which gcc` como segunda comprobación?

El `check-prod-no-compiler` actual usa `dpkg -l | grep -qE 'gcc|g\+\+|...'`.
Esto detecta compiladores instalados vía apt, pero no detecta binarios copiados
manualmente fuera del gestor de paquetes.

**¿Añadimos `which gcc || which clang || which cc` como segunda capa de
verificación, sabiendo que no es exhaustiva pero sí más robusta?**

### Q4 — Draft v17: revisión de las 4 nuevas secciones §5

Las secciones §6.5 (RED→GREEN gate), §6.8 (Fuzzing), §6.10 (CWE-78 execv()),
y §6.12 (BSR axiom) son contribuciones metodológicas nuevas, no documentadas
previamente en la literatura de sistemas de seguridad.

**¿Consideráis que el nivel de rigor y la evidencia empírica presentada en
cada sección es suficiente para arXiv cs.CR? ¿Qué añadiríais o reforzaríais?**

---

## Recordatorio de reglas permanentes

- **REGLA EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- **macOS:** nunca `sed -i` sin `-e ''`. Scripts con caracteres especiales → Python3 heredoc.
- **Seed ChaCha20:** nunca en CMake ni logs. Solo runtime: `mlock()` + `explicit_bzero()`.
- **dist/:** nunca en git. SHA256SUMS obligatorio. BSR axiom (ADR-039).
- **Todo fix de seguridad:** RED→GREEN + property test + integración. Sin excepciones.
- **main:** sagrado. Solo entra lo que pasa REGLA EMECAS en VM destruida y reconstruida.

---

*DAY 132 — 26 Abril 2026 · Via Appia Quality*
*"Un escudo que aprende de su propia sombra."*