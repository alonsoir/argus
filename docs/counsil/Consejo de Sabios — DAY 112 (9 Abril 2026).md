# Consejo de Sabios — DAY 112 (9 Abril 2026)

**Proyecto:** ML Defender (aRGus NDR)  
**Autor:** Alonso Isidoro Román  
**Branch:** feature/plugin-crypto  
**Commits:** 10d678ed · 1691db06

---

## ✅ Completado DAY 112

### PHASE 2 Multi-Layer Plugin Architecture — COMPLETA (5/5)

Hoy se ha cerrado la última fase de integración del plugin-loader en todos
los componentes del pipeline. rag-security integrado con ADR-029 D1-D5:

| Componente | Fase | Contrato | Test | Estado |
|---|---|---|---|---|
| firewall-acl-agent | 2a | NORMAL | TEST-INTEG-4a 3/3 | ✅ |
| rag-ingester | 2b | READONLY | TEST-INTEG-4b | ✅ |
| sniffer | 2c | NORMAL + payload real | TEST-INTEG-4c 3/3 | ✅ |
| ml-detector | 2d | NORMAL post-inferencia | compilación limpia | ✅ |
| rag-security | 2e | READONLY (ADR-029) | TEST-INTEG-4e 3/3 | ✅ |

**make plugin-integ-test: 4a+4b+4c+4e PASSED** — gate completo verde.

### ADR-029 D1-D5 implementados en rag-security

- D1: `static ml_defender::PluginLoader* g_plugin_loader = nullptr` (raw pointer global)
- D2: `signalHandler` async-signal-safe — solo `write()`, `shutdown()`, `raise()`
- D3: orden obligatorio: construcción → asignación global → instalación de señales
- D4: `invoke_all` READONLY post-`processCommand`, `result_code` ignorado
- D5: `invoke_all` nunca desde signal handler
- Double-shutdown guard: `g_plugin_loader = nullptr` tras `shutdown()`

### ADR-030 y ADR-031 incorporados al repositorio

Ambos aprobados por el Consejo en sesión DAY 109 (5/5 unanimidad).
Incorporados hoy a `docs/adr/`, `BACKLOG.md` y `README.md`.

**ADR-030 (AppArmor-Hardened):** variante producción realista sobre Linux
6.12 LTS + Debian 13 + AppArmor enforcing. Vagrant-compatible. ARM64
(Raspberry Pi 4/5) + x86-64. Mitiga directamente el confused deputy
documentado por Hugo Vázquez Caramés. BACKLOG post-PHASE 3.

**ADR-031 (seL4/Genode):** investigación pura. Pregunta científica:
¿cuánto cuesta la seguridad formal en rendimiento medible sobre hardware
de 150-200 USD? XDP probablemente inviable en guest (H1). Spike técnico
2-3 semanas obligatorio antes de cualquier implementación. BACKLOG
post-ADR-030.

---

## 🔜 Planificado DAY 113

1. **Paper — implicaciones Mythos Preview** (deuda DAY 108):
    - Axioma kernel inseguro como limitación declarada del scope
    - aRGus válido contra threat model real aunque kernel comprometido
    - Detección de red como capa defensiva independiente del kernel
    - Referencia a ADR-030/031 como trabajo futuro
    - Producir Draft v14 → desbloquea arXiv Replace

2. **arXiv Replace v13** — solo si v1 ya indexada en Google Scholar

3. **Decisión PR** feature/plugin-crypto → main (PHASE 2 completa)

4. **ADR-025 implementación** (Plugin Integrity Ed25519) — desbloqueado

---

## ❓ Preguntas al Consejo DAY 113

**Q1-113 — PR timing: ¿merge feature/plugin-crypto → main ahora?**

PHASE 2 completa. Todos los tests en verde. El argumento para mergear
ahora: main está muy desactualizado (37+ commits de diferencia). El
argumento para esperar: ADR-025 (plugin signing) está desbloqueado y
podría ir en el mismo PR para no tener dos merges seguidos.

¿Vuestra recomendación: merge ahora limpio o esperar a ADR-025?

**Q2-113 — ADR-025 secuencia: ¿Ed25519 signing antes o después del merge?**

ADR-025 toca: `plugin_loader.cpp`, `plugin-loader/CMakeLists.txt`,
`tools/provision.sh` (--reset flag), JSON config schemas (6 componentes),
systemd units. Tests: TEST-INTEG-SIGN-1 a 7.

¿Implementar en feature/plugin-crypto y mergear con ADR-025 incluido?
¿O abrir nueva branch post-merge?

**Q3-113 — Paper Draft v14: ¿el axioma kernel inseguro va en §Threat Model
o en §Conclusions?**

El texto propuesto:
> *aRGus NDR defines its detection guarantees as valid within its layer
> (network behavior analysis). If the host kernel is compromised by an
> advanced adversary — as demonstrated by Mythos Preview (Anthropic, 2026)
> — detection guarantees are invalidated within the compromised host.
> Network detection remains a valid defensive layer even under kernel
> compromise, as lateral movement between hosts still traverses monitored
> network segments. Host hardening (ADR-030) and formal kernel verification
> (ADR-031) are documented as future work.*

¿§Threat Model, §Limitations, o §Future Work?

**Q4-113 — ADR-031 spike: ¿x86-64 con QEMU primero o directamente ARM64?**

ADR-031 propone Fase 1 en x86-64 (más maduro en Genode) antes de ARM64.
Dado que el hardware Pi no está disponible aún, x86-64 QEMU es la única
opción inmediata. ¿Alguna razón técnica para priorizar ARM64 desde el
inicio del spike?

---

## 📊 Estado global del proyecto

```
arXiv: 2604.04952 [cs.CR] PUBLICADO ✅ (3 Apr 2026)
Pipeline: 6/6 RUNNING ✅
Tests: 25/25 + 4a 3/3 + 4b + 4c 3/3 + 4e 3/3
PHASE 2: COMPLETA ✅
PHASE 3: ⏳ próxima (fleet telemetry, XGBoost)
ADR-025: ⏳ desbloqueado
ADR-030: BACKLOG post-PHASE 3
ADR-031: BACKLOG post-ADR-030 + spike GO
```

*La verdad por delante, siempre.*