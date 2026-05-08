# DEBT-EMECAS-AUTOMATION-001 — Automatización Completa del Protocolo EMECAS

**Estado:** BACKLOG  
**Prioridad:** P2 — post deudas P0 activas  
**Bloqueado por:** DEBT-COMPILER-WARNINGS-CLEANUP-001 cerrada + DEBT-VARIANT-B-CONFIG-001 cerrada  
**Estimación:** 1 sesión  
**Responsable:** Alonso (PI)  
**Fecha de registro:** 2026-05-03 (DAY 140)

---

## Motivación

El protocolo EMECAS se ejecuta actualmente como secuencia manual de comandos con redirección de output. Esto funciona, pero:

- El log se genera manualmente — depende de que el operador redirija correctamente.
- No hay distinción formal entre EMECAS dev, EMECAS hardened x86 y EMECAS hardened ARM64.
- Los logs no tienen nombre estandarizado ni directorio canónico.
- La reproducibilidad no es automática — es un hábito, no un mecanismo.

Para FEDER, los logs EMECAS son artefactos de reproducibilidad demostrables ante la comisión evaluadora. Deben generarse de forma automática, con nombre fechado, y ser referenciables desde el BACKLOG como evidencia de cierre de deuda.

---

## Diseño propuesto

### Targets Makefile

```makefile
make emecas-dev           # dev VM: destroy → up → bootstrap → test-all
make emecas-prod-x86      # hardened x86: destroy → up → hardened-full → check-prod-all
make emecas-prod-arm64    # hardened arm64: destroy → up → hardened-full → check-prod-all
```

### Logs automáticos

logs/emecas-dev-YYYYMMDD-HHMMSS.log
logs/emecas-prod-x86-YYYYMMDD-HHMMSS.log
logs/emecas-prod-arm64-YYYYMMDD-HHMMSS.log

- Directorio `logs/` en raíz del repo (gitignored excepto `.gitkeep`).
- Nombre incluye timestamp ISO para ordenación cronológica.
- El log captura stdout + stderr completo del protocolo.
- Al finalizar: resumen de resultado (PASSED / FAILED) en la última línea del log.

### Estructura interna de cada log

=== EMECAS-DEV 2026-05-03T05:04:00 ===
[vagrant destroy] ...
[vagrant up] ...
[make bootstrap] ...
[make test-all] ...
=== RESULT: PASSED | FAILED ===
=== DURATION: Xm Ys ===

---

## Valor para FEDER

- Log `emecas-prod-arm64` ejecutado en hardware físico (RPi5) = demostración de reproducibilidad ante comisión evaluadora.
- Log fechado = evidencia auditoria de que el sistema funciona en la fecha declarada.
- Referenciable desde BACKLOG como cierre formal de deuda: "DEBT-X cerrada — ver logs/emecas-prod-x86-20260601-090000.log".

---

## Test de cierre

```bash
make emecas-dev
ls logs/emecas-dev-*.log  # existe y contiene "RESULT: PASSED"

make emecas-prod-x86
ls logs/emecas-prod-x86-*.log  # existe y contiene "RESULT: PASSED"
```

---

## Referencias

- REGLA EMECAS (DAY 130): `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- REGLA PERMANENTE (DAY 134): `make hardened-full` es el EMECAS sagrado de la hardened VM
- BACKLOG-FEDER-001 — demo técnica grabable como prerequisito
- DEBT-ADR041-001..006 — protocolo hardware físico (ARM64, x86 low-power)
