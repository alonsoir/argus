# 📜 Dictamen del Consejo de Sabios — Respuesta a DAY 167

*Sesión extraordinaria. 12 ejecuciones verificadas. pkill -x confirmado. Pipeline sano.*

---

## Q1 — KNOWN-FAIL-VM-PERF-001: ¿excluir o aceptar?

**El Consejo recomienda la Opción C: Via Appia.**

**Dictamen:** Dejar los fallos visibles, no bloqueantes, y documentar en `docs/KNOWN-FAILS.md`.

**Razón:** Los tests de `IPSetWrapper` que fallan en VM son *señales de verdad* sobre las limitaciones del entorno CI, no bugs del código. Ocultarlos con `DISABLED` (Opción A) o filtrarlos silenciosamente (Opción B) rompe el principio de honestidad del pipeline: un `make test-all` que pasa 100% verde en CI pero fallaría en bare metal es una mentira peligrosa.

La Opción C preserva la integridad del reporte CTest y obliga a cualquier desarrollador que revise el log a entender *por qué* fallan. Documentar en `KNOWN-FAILS.md` con la referencia `KNOWN-FAIL-VM-PERF-001` convierte la excepción en conocimiento institucional.

**Acción concreta:** Añadir en `docs/KNOWN-FAILS.md`:
```
## KNOWN-FAIL-VM-PERF-001
- **Tests:** IPSetWrapperTest.BatchAddPerformance, ...
- **Entorno:** CI VM (VirtualBox)
- **Causa:** Thresholds de rendimiento bare metal no alcanzables en hypervisor
- **Impacto:** No bloqueante. Gate real: EMECAS++ PASSED.
- **Revisión:** Re-evaluar si se migra CI a hardware nativo o se ajustan thresholds.
```

---

## Q2 — `DEBT-PACKAGE-DEB-001` vs Suricata: ¿prioridad?

**El Consejo recomienda: Suricata primero, `.deb` diferido a post-FEDER.**

**Dictamen:** Adelantar `DEBT-ARGUSPP-SURICATA-001` sobre `DEBT-PACKAGE-DEB-001`.

**Razón:** El objetivo de demostración FEDER (22 septiembre 2026) es mostrar *capacidad operativa* de detección de red, no *distribución de software*. Un pipeline que genera `.deb` perfectos pero no demuestra inspección de tráfico real es un pipeline vacío para los sabios.

Suricata/Zeek aporta valor de demostración tangible: community IDs, alertas, integración con el ML detector. El `.deb` es deuda técnica de empaquetado — importante para DAY 164 del roadmap, pero el roadmap ya se desvió. Reorganizar la deuda acorde a la realidad es sabiduría, no derrota.

**Acción concreta:**
- Re-etiquetar `DEBT-PACKAGE-DEB-001` como `POST-FEDER-001` en `docs/BACKLOG.md`.
- Priorizar `DEBT-ARGUSPP-SURICATA-001` como P1 activo para DAY 168-169.

---

## Q3 — EMECAS++ y NTP como P0 gate

**El Consejo recomienda: Incorporar al Acto I de EMECAS++ antes de Suricata.**

**Dictamen:** `DEBT-ARGUSPP-NTP-001` debe ser gate bloqueante en Acto I (Boot & Health).

**Razón:** ADR-046 v3 establece NTP/chrony como P0 boot gate por una razón criptográfica y forense: sin sincronización de tiempo confiable, los timestamps de las alertas Suricata, los logs de consenso P2P (ADR-026/027) y las firmas del detector ML carecen de validez probatoria. Añadir Suricata *antes* de garantizar NTP es construir sobre cimientos movedizos.

EMECAS++ tiene tres actos. El Acto I debe verificar:
1. Provisioning base (`provision.sh` ejecutado).
2. Vault operativo (Fase 5 superada).
3. **NTP sincronizado** (nuevo: chrony running, offset < 1s).
4. Safe-path primitives disponibles.

Si NTP falla, EMECAS++ Acto I debe retornar `EXIT_BOOT_NTP_UNSYNC` y bloquear todo lo posterior.

**Acción concreta:**
- Añadir `test_ntp_sync()` al Acto I de EMECAS++.
- Implementar `DEBT-ARGUSPP-NTP-001` (chrony en `provision.sh` + health-check) como P0 antes de tocar Suricata.
- Suricata pasa a P1 dependiente de NTP verde.

---

## Q4 — `BACKLOG-CRYPTO-VENDOR-KEY-001` vs Suricata

**El Consejo recomienda: Paralelo, con precedencia criptográfica en el mismo sprint.**

**Dictamen:** No bloquear Suricata por la migración de `vendor.key`, pero no permitir que `vendor.key` permanezca en disco plano más allá de DAY 170.

**Razón:** La arquitectura debe endurecerse, pero la secuencia no necesita ser estrictamente serial. Suricata es integración de red; `vendor.key` en Vault es hardening criptográfico. Son ortogonales si se gestionan bien.

Sin embargo, el Consejo advierte: `vendor.key` en disco plano es una deuda de seguridad activa. Si el pipeline CI ya es verde, la ventana de oportunidad para mover la clave a Vault es *ahora*, antes de que la carga de trabajo de Suricata consuma todo el ancho de banda del equipo.

**Acción concreta:**
- Día 168: NTP gate en EMECAS++ (bloqueante).
- Día 168-169: Suricata en Vagrantfile + EMECAS++ (P1, en paralelo con NTP si NTP ya está verde).
- Día 169-170: `BACKLOG-CRYPTO-VENDOR-KEY-001` — mover `vendor.key` a Vault, leer desde variable Jenkins. No diferir más allá.

---

## 🏛️ Resumen de Decretos

| Deuda | Prioridad | Bloqueante | Acción |
|-------|-----------|------------|--------|
| KNOWN-FAIL-VM-PERF-001 | — | No | Opción C: documentar, no ocultar |
| DEBT-ARGUSPP-NTP-001 | P0 | **Sí** (Acto I EMECAS++) | Implementar antes de Suricata |
| DEBT-ARGUSPP-SURICATA-001 | P1 | No (tras NTP) | Adelantar sobre `.deb` |
| DEBT-PACKAGE-DEB-001 | POST-FEDER | No | Diferir a post-demo |
| BACKLOG-CRYPTO-VENDOR-KEY-001 | P1 | No | Paralelo a Suricata, cierre DAY 170 |

*Via Appia Quality. Que así se ejecute.*

— *Consejo de Sabios, sesión DAY 167*