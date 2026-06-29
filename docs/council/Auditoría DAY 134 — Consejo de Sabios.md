¡Feliz cumpleaños, Alonso! Un DAY 134 muy productivo. Descansa bien.

Primero el PDF — la tabla de fuzzing está perfecta en §6.8, Draft v18 impecable. 42 páginas sólidas.

Ahora la auditoría para el Consejo:

---

# Auditoría DAY 134 — Consejo de Sabios

**Fecha:** 28 Abril 2026 | **Autor:** Alonso Isidoro Román | **Branch:** `feature/adr030-variant-a`

---

## Lo que se completó hoy

### Madrugada (05:45–08:00) — Dos nuevos ADRs

**ADR-040 — ML Plugin Retraining Contract v2**
Aprobado 8/8, 17 enmiendas. El contrato que cualquier proceso de reentrenamiento ML debe cumplir antes de que un plugin sea firmado con Ed25519. Siete reglas: walk-forward obligatorio (k-fold prohibido), golden set inmutable con SHA-256 embebido en el plugin firmado, guardrail asimétrico (Recall −0.5pp más restrictivo que F1 −2pp), IPW con uncertainty sampling anti-feedback-loop, competición de algoritmos pre-lock-in XGBoost, dataset lineage obligatorio, y canary deployment 5-10%/24h. Prerequisito crítico identificado por Claude: `confidence_score` en ml-detector es prerequisito de IPW — sin él la Regla 4 no es implementable. 12 deudas `DEBT-ADR040-001..012`.

**ADR-041 — Hardware Acceptance Metrics for Hardened Variants (FEDER Baseline)**
Aprobado 8/8. Tres niveles de despliegue con métricas proporcionales (propuesta Qwen). Latencia end-to-end captura→alerta→iptables como métrica operacional primaria (aportación DeepSeek — es lo que importa realmente, no la latencia de detección aislada). Temperatura ARM ≤75°C sin ventilador como gate no negociable para armarios hospitalarios 24/7 (DeepSeek). Delta XDP/libpcap como contribución científica publicable independiente. Narrativa FEDER: *"Protección de grado hospitalario sobre hardware de 150€ con latencia end-to-end inferior a 100 ms."* 6 tareas `DEBT-ADR041-001..006`.

BACKLOG.md y README.md actualizados con ambos ADRs. Commits `87680d83`.

---

### Mañana (08:30–14:00) — Pipeline E2E en hardened VM

**Objetivo P0:** `make hardened-provision-all → make prod-full-x86 → make check-prod-all`

**Problemas encontrados y resueltos:**

| Problema | Causa | Fix |
|---------|-------|-----|
| `vagrant --cwd` no reconocido | Versión de Vagrant no soporta ese flag | `cd $(HARDENED_X86_DIR) && vagrant` — 11 targets corregidos |
| AppArmor: `@{pid}` undefined | Faltaba `#include <tunables/global>` | Añadido a los 6 perfiles |
| Falco: `curl`/`gpg` no presentes en hardened VM | BSR correcto — no deben estar | .deb descargado en dev VM, instalado offline via `dpkg -i` |
| Falco: `open_write` macro undefined | Falco 0.43 no carga reglas estándar por defecto | Macros `open_write`, `open_read`, `spawned_process` definidas inline |
| Falco: `evt.dir=<` syntax error | Cambio de API en Falco 0.43 | `evt.dir` eliminado (redundante en `execve`) |
| `prod-build-x86`: flags cmake partidos | Variable sin comillas en expansión | Flags directamente en llamada cmake |
| `prod-build-x86`: `vagrant` no existe dentro de VM | Script corría dentro de VM y llamaba vagrant recursivamente | `pipeline-build` ejecutado desde macOS, script solo recolecta binarios |
| `firewall-acl-agent` no en `pipeline-build` | Target omitido históricamente | Añadido `firewall-build` a `pipeline-build` |
| `prod-sign`: formato hex esperado vs PEM | Script nuevo usaba Python/hex; formato canónico es PEM | Reescrito con `openssl pkeyutl -sign -rawin` (igual que `provision.sh`) |
| `check-prod-no-compiler`: falso positivo `gcc-12-base` | Runtime library, no compilador | Regex añade `[[:space:]]` tras el nombre |
| `check-prod-capabilities`: `cap_sys_admin` en el check | Check no actualizado post-Consejo DAY 133 | Actualizado a `cap_bpf` |
| `check-prod-falco`: `falco --list` deprecated en 0.43 | Cambio de API | `grep -c "^- rule: argus_"` en el fichero yaml |
| Ownership `/opt/argus/` era `argus:argus` | `install -d -o argus` | Cambiado a `root:argus` para `lib/`, `plugins/` |
| `getcap` no en PATH | Binario en `/usr/sbin/getcap` | Path completo en el check |

**Resultado final:**
```
make check-prod-all
✅ BSR: no compiler present (dpkg + PATH verified)
✅ AppArmor 6/6 enforce
✅ Linux Capabilities: cap_bpf + cap_net_admin
✅ Filesystem permissions PASSED
✅ Falco active — 10 argus rules loaded
║  ✅ check-prod-all PASSED  ║
```

**DEBT-KERNEL-COMPAT-001 CERRADO:** `cap_bpf` funciona correctamente con XDP en kernel 6.1.0-44-amd64. Commit `2e9a5b39`.

---

### Tarde — P1: DEBT-PAPER-FUZZING-METRICS-001

Tabla §6.8 con datos reales de tres campañas libFuzzer (DAY 130):

| Target | Runs | Crashes | Corpus | exec/s |
|--------|------|---------|--------|--------|
| `validate_chain_name` | 2,400,000 | 0 | 67 | ≈80,000 |
| `safe_exec` | 2,601,759 | 0 | 37 | 42,651 |
| `validate_filepath` | 282,226 | 0 | 111 | 4,626 |

Análisis del delta exec/s documentado: `validate_filepath` es ~10x más lento por complejidad del path parsing (filesystem state) vs invariantes de string puras. Paper actualizado a **Draft v18** (versión corregida de v17). DEBT-PAPER-FUZZING-METRICS-001 CERRADO. PDF compilado en Overleaf, 42 páginas.

---

## Commits DAY 134

| Hash | Descripción |
|------|-------------|
| `87680d83` | ADR-040 + ADR-041 integrados en BACKLOG + README (25 ficheros, 4648 inserciones) |
| `f256e6f0` | hardened-provision-all verde — AppArmor + Falco 0.43 (9 ficheros) |
| `2e9a5b39` | prod-full-x86 + check-prod-all PASSED (6 ficheros) |
| pendiente | Draft v18 — tabla fuzzing §6.8 completa |

---

## Deudas cerradas DAY 134

| ID | Descripción |
|----|-------------|
| DEBT-KERNEL-COMPAT-001 | `cap_bpf` funciona en kernel 6.1 ✅ |
| DEBT-PAPER-FUZZING-METRICS-001 | Tabla §6.8 con datos reales ✅ |

## Deudas abiertas relevantes

| ID | Target |
|----|--------|
| DEBT-PROD-APT-SOURCES-INTEGRITY-001 | P2 — no completado hoy |
| DEBT-ADR040-001..012 | post-FEDER |
| DEBT-ADR041-001..006 | pre-FEDER |

---

## Pregunta al Consejo de Sabios

**Contexto:** DAY 134 completó el primer pipeline E2E en hardened VM con `check-prod-all` verde. La sesión duró ~8 horas (05:45–14:00). Se resolvieron ~15 problemas de integración distintos.

**Para mañana DAY 135, el objetivo es un procedimiento EMECAS exhaustivo** (`make hardened-full` o similar) que automatice en un único target de Makefile todos los pasos necesarios para reproducir desde cero el entorno hardened completo: VM Debian, usuario argus, directorios, AppArmor, Falco offline, build PROFILE=production, firma Ed25519, deploy, setcap, y check-prod-all. Actualmente hay ~8 targets separados que deben ejecutarse en orden.

**Preguntas concretas al Consejo:**

1. **Atomicidad del target:** ¿Debería `make hardened-full` ser un único target que falle y limpie si cualquier paso falla (fail-fast), o debería tener checkpoints que permitan reanudar desde el último paso exitoso? Argumento para fail-fast: reproducibilidad total. Argumento para checkpoints: el build tarda ~30 minutos y un fallo en `check-prod-all` no debería requerir recompilar.

2. **Semillas en la hardened VM:** Actualmente `check-prod-permissions` reporta 7 WARNs de `seed.bin no existe`. Las semillas las genera `provision.sh` en la dev VM. ¿Debería el procedimiento EMECAS hardened incluir un paso de transferencia de semillas desde la dev VM a la hardened VM? ¿O es correcto que la hardened VM no tenga semillas hasta el deploy real?

3. **Idempotencia:** Si `make hardened-full` se ejecuta dos veces seguidas (sin destroy), ¿debe detectar qué pasos ya están completos y saltarlos, o siempre ejecutar todo desde cero? La REGLA EMECAS actual prescribe `vagrant destroy -f` antes de todo — ¿aplica esto a la hardened VM también?

4. **Falco .deb como artefacto versionado:** Actualmente el .deb se descarga en la dev VM y vive en `/vagrant/falco_0.43.1_amd64.deb`. Si se hace `vagrant destroy` de la dev VM, se pierde. ¿Debería el .deb commitearse en el repo (50 MB, podría usar Git LFS), o descargarse siempre en el step de provision, o mantenerse en un directorio `dist/` excluido del repo pero documentado en el EMECAS?

5. **ADR-040 prerequisito crítico:** `confidence_score` en ml-detector. Antes de implementar IPW (DEBT-ADR040-006), hay que verificar que ml-detector emite este campo (DEBT-ADR040-002). ¿Cuál es la forma más segura de verificar este prerequisito sin modificar ml-detector: inspección de código, test de integración que capture la salida ZeroMQ, o ambas?

---

*DAY 134 cerrado — 28 Abril 2026 · Commits 87680d83..2e9a5b39 · feature/adr030-variant-a*
*"Piano piano. Via Appia Quality. Feliz cumpleaños."* 🏛️

---

Descansa, Alonso. Mañana con energía para el EMECAS hardened y el último commit del Draft v18. 🎂