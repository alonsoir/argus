# CONSEJO DE SABIOS — DAY 114 — SESIÓN DE CIERRE

**Fecha:** 11 de Abril de 2026
**Proyecto:** ML Defender (aRGus NDR) — C++20 NDR open-source
**Árbitro:** Alonso Isidoro Román (independiente, Extremadura)
**Paper:** arXiv:2604.04952 [cs.CR] · DOI: https://doi.org/10.48550/arXiv.2604.04952
**Repo:** https://github.com/alonsoir/argus
**Branch activa:** feature/phase3-hardening

---

## Contexto del día

DAY 114 ha sido una sesión de cierre de deuda técnica y apertura de PHASE 3.
Los hitos del día:

1. **Pipeline rebuild post-ADR-025:** El pipeline no arrancaba porque `libplugin_hello.so`
   no estaba desplegado ni firmado tras el cambio de `libplugin_loader.so`. ADR-025
   fail-closed funcionó exactamente como debe — `std::terminate()` al detectar plugin
   sin firma. Solución: `make plugin-hello-build` + `provision.sh sign`.

2. **TEST-INTEG-4d implementado y PASSED (3/3):** Condición bloqueante 1 del merge.
   ml-detector + plugin-loader integration test. Casos: NORMAL + annotation ML score,
   D8 VIOLATION read-only, result_code=-1 no crash.

3. **DEBT-SIGNAL-001/002 resueltos:**
    - Signal handlers: `std::cout` → `write(STDERR_FILENO)` en sniffer y ml-detector
    - `shutdown_called_` `bool` → `std::atomic<bool>` en plugin_loader.hpp
    - Verificado a nivel binario (objdump): `call write@plt` con `edi=0x2` confirmado

4. **Merge feature/plugin-integrity-ed25519 → main. Tag v0.3.0-plugin-integrity.**
   12/12 tests PASSED. Commits: 65a29034.

5. **arXiv Replace v15 submitted:** submit/7467190 — párrafo Glasswing revisado
   (veredicto Q5 árbitro DAY 113 aplicado), versión bumpeada a v15.

6. **Rama feature/phase3-hardening abierta** desde main.

**Deuda nueva registrada hoy:**
- DEBT-HELLO-001: `libplugin_hello.so` no debe estar en configs de producción
- DEBT-OPS-001: `make redeploy-plugins` (build+sign+deploy unificado)
- DEBT-OPS-002: documentación operativa + Troubleshooting pipeline
- DEBT-SIGN-AUTO: firma automática de plugins en provision.sh (idempotente)

---

## Preguntas al Consejo

**Q1 — DEBT-SIGN-AUTO: diseño del mecanismo de firma automática**

El incidente de hoy revela una fragilidad operativa: cuando `libplugin_loader.so`
cambia, los plugins deben ser re-desplegados y re-firmados, pero nada lo garantiza
automáticamente. Propuesta de diseño:

```
provision.sh check-plugins:
  - Para cada plugin en /usr/lib/ml-defender/plugins/*.so:
    - Si no existe .sig → firmar
    - Si .sig existe pero es inválido para la clave actual → firmar
    - Si todo OK → skip
  - Idempotente: se puede llamar siempre sin efectos secundarios

Makefile target: check-and-sign-plugins
  - Llamado antes de pipeline-start
  - Llamado después de plugin-hello-build, plugin-loader-build

Vagrantfile provisioner:
  - Llamar check-and-sign-plugins tras cualquier rebuild
```

¿Veis riesgos en este diseño? ¿Hay casos edge no cubiertos?

**Q2 — DEBT-HELLO-001: estrategia de eliminación de libplugin_hello.so en producción**

El plugin hello-world existe para validar ADR-012 (arquitectura plugin). En producción
no tiene función y es superficie de ataque innecesaria. Opciones:

- **A)** CMake flag `BUILD_DEV_PLUGINS=OFF` por defecto en release. En dev,
  `BUILD_DEV_PLUGINS=ON` explícito.
- **B)** Eliminar referencia a `libplugin_hello.so` de todos los JSON configs de
  producción. El plugin puede existir en el repo pero no cargarse.
- **C)** Ambas: flag CMake + JSON sin referencia.

¿Cuál recomendáis? ¿Hay implicaciones para el proceso de validación ADR-012?

**Q3 — PHASE 3: priorización del backlog**

El árbitro ya estableció el orden en DAY 113: PHASE 3 antes de ADR-026.
Dentro de PHASE 3, el backlog actual es:

1. systemd units: Restart=always, RestartSec=5s, unset LD_PRELOAD
2. AppArmor profiles básicos 6 componentes (incluir: denegar write `/usr/bin/ml-defender-*` para root)
3. TEST-PROVISION-1 como gate CI formal
4. DEBT-ADR025-D11: provision.sh --reset (deadline 18 Apr)
5. DEBT-SIGN-AUTO (firma automática idempotente)
6. DEBT-HELLO-001 (eliminar hello de producción)

¿Estáis de acuerdo con este orden? ¿Alguna dependencia oculta entre ítems?

**Q4 — Troubleshooting documentation (DEBT-OPS-002)**

Hoy tardamos ~30 minutos en diagnosticar que el problema era un plugin sin firmar.
El árbol de diagnóstico debería ser:

```
Pipeline no arranca →
  ¿Algún componente falla con std::terminate()? →
    Revisar logs: [plugin-loader] CRITICAL →
      ¿"cannot open plugin (symlink?)"? → make plugin-hello-build + make sign-plugins
      ¿"Ed25519 INVALID"? → make sign-plugins
      ¿".sig not found"? → make sign-plugins
      ¿"path outside allowed prefix"? → revisar JSON config plugin path
```

¿Qué otros casos debería incluir el árbol? ¿Formato preferido: Markdown, man page, sección en CLAUDE.md?

---

## Estado del proyecto al cierre DAY 114

```
Pipeline:    6/6 RUNNING
Tests:       12/12 PASSED (plugin-integ-test)
Branch:      feature/phase3-hardening
Tag:         v0.3.0-plugin-integrity (main)
arXiv:       2604.04952v1 announced + v2 (Replace v15) submitted
Paper:       Draft v15 compilación limpia
PHASE 2:     COMPLETA (2a+2b+2c+2d+2e)
PHASE 3:     INICIADA
```

---

*Esperamos vuestro feedback. La verdad por delante, siempre.*
*— Alonso Isidoro Román, DAY 114*