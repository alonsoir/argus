Aquí el escrito para el Consejo:

---

**CONSEJO DE SABIOS — DAY 117 · 14 Abril 2026**
**aRGus NDR (ML Defender) — Informe diario**

---

**LO QUE HEMOS HECHO HOY**

DAY 117 ha cerrado 12 de los 13 ítems bloqueantes de `feature/phase3-hardening`. El único pendiente es AppArmor enforce para el sniffer (48h complain mínimo → DAY 118).

Resumen técnico:

1. **DEBT-VAGRANTFILE-001** — `apparmor-utils` + `apparmor-profiles` añadidos al Vagrantfile. Los tres binarios (`aa-complain`, `aa-enforce`, `aa-logprof`) disponibles en `/usr/sbin/`.

2. **DEBT-SEED-PERM-001 + TEST-PERMS-SEED** — `seed_client.cpp` corregido: permisos correctos son `0640`, no `0600`. Test C++ dedicado con 3 casos (640 sin warning · 600 con warning · 644 con warning). Integrado en `ctest` como `perms_seed_tests`.

3. **REC-2 noclobber** — `set -o noclobber` añadido a `provision.sh`, `install-systemd-units.sh`, `set-build-profile.sh`. Hook pre-commit rechaza ficheros de 0 bytes en staging. Ambos verificados con tests reales.

4. **TEST-INVARIANT-SEED** — `make test-invariant-seed` verifica que los 6 `seed.bin` son byte-a-byte idénticos post-reset. Integrado en `make test-all`.

5. **TEST-PROVISION-1 8/8** — Check #8 añadido (presencia de `apparmor-utils`). `make test-all` ampliado: ahora incluye `test-provision-1` + `test-invariant-seed` + `plugin-integ-test` como CI gate completo.

6. **Backup policy `.bak.*`** — `cleanup_old_backups()` implementada: máximo 2 backups por componente, elimina el más antiguo automáticamente. Llamada en 3 puntos del script. Test: 3 resets → 14 backups (2×7 targets).

7. **ADR-021 addendum** — INVARIANTE-SEED-001 validado en producción + regresión multi-familia documentada + backup policy operacional.

8. **docs/Recovery Contract (OQ-6 ADR-024)** — Procedimiento 5 pasos de rotación de claves. Incluye lección aprendida: `--reset` rota la keypair Ed25519, la pubkey está hardcoded en tiempo de compilación → siempre `make pipeline-build` + `make sign-plugins` post-reset.

9. **DEBT-RAG-BUILD-001** — `rag/build` → `rag/build-debug` + `build-active` symlink. `set-build-profile.sh` ahora gestiona los 6 componentes uniformemente. Aviso DEBT eliminado.

10. **tools/apparmor-promote.sh** — Script complain→enforce con monitoreo 5 minutos y rollback automático si hay denials AppArmor. Detección de estado via `awk -v` (compatible con `set -u` y guiones en nombres de componentes).

11. **AppArmor enforce 5/6** — Orden Consejo Q1 DAY 116 seguida: etcd-server → rag-security → rag-ingester → ml-detector → firewall-acl-agent. 0 denials en cada uno. `make test-all` verde con 5/6 en enforce.

12. **Pubkey rotada** — Los 3 resets del test de backup policy rotaron la keypair. Nueva pubkey dev: `e51a91e91d72f74fe97e8a4eb883c9c6eb41dd2fc994feaf59d5ba2177720f3d`. Pipeline recompilado y re-firmado.

**Extra:** arXiv Draft v15 recibido de Cornell hoy. https://arxiv.org/abs/2604.04952

---

**LO QUE HAREMOS MAÑANA (DAY 118)**

1. **AppArmor enforce sniffer** — Las 48h de complain se cumplen. Verificar `journalctl` por denials acumulados, luego `sudo bash tools/apparmor-promote.sh sniffer`. Hoy ya hay 1 ALLOWED en journalctl — hay que revisar si es un false positive o indica algo que el perfil no cubre.

2. **Merge `feature/phase3-hardening` → `main`** — Si sniffer enforce pasa sin rollback. Tag `v0.4.0-phase3-hardening`.

3. **Abrir `feature/adr026-xgboost`** — Pre-requisito: enforce completo + todos los DEBTs cerrados. XGBoost Track 1 (Precision ≥ 0.99 gate médico).

---

**PREGUNTAS AL CONSEJO**

**Q1 — El sniffer tiene 1 ALLOWED en journalctl antes del enforce**

Al verificar el estado del sniffer antes del promote, encontramos:
```
vagrant ssh -c "sudo journalctl -k | grep 'apparmor.*sniffer\|ALLOWED.*sniffer' | wc -l"
→ 1
```
No tenemos el texto completo de ese ALLOWED todavía.

**Pregunta:** ¿Es normal encontrar 1 ALLOWED en un componente que lleva pocas horas en complain con el pipeline activo? ¿Deberíamos revisar el perfil antes de enforce, o proceder con enforce y dejar que el rollback automático nos proteja si hay denials?

**Q2 — noclobber en provision.sh y el operador**

Hemos añadido `set -o noclobber` a `provision.sh`. Esto protege contra truncado accidental con `>`. Sin embargo, hay un caso edge: si un operador quiere intencionalmente sobreescribir un fichero dentro del script (por ejemplo, regenerar un fichero de configuración), necesita `>|`.

Ya hemos resuelto un caso concreto (`build.env` en `set-build-profile.sh`).

**Pregunta:** ¿Recomendáis hacer un audit de todos los `>` en `provision.sh` para identificar cuáles son intencionales (deberían ser `>|`) vs accidentales (deben quedar protegidos por noclobber)? ¿O es suficiente con resolver los casos cuando fallen?

**Q3 — Merge strategy: squash vs merge commit**

`feature/phase3-hardening` tiene ~25 commits de trabajo incremental. Al mergear a main, tenemos dos opciones:
- `git merge --no-ff`: preserva historial completo, visible en `git log`
- `git merge --squash`: un commit limpio en main con todo el trabajo del DAY 115-118

**Pregunta:** ¿Cuál recomendáis para un proyecto open-source con paper académico asociado? ¿Tiene impacto en la trazabilidad científica preservar cada commit individual?

**Q4 — ADR-026 XGBoost: ¿feature flag o rama separada?**

Al abrir `feature/adr026-xgboost`, los plugins XGBoost se cargarán via `plugin-loader` con Ed25519. La pregunta es si el desarrollo debe hacerse en rama separada hasta tener F1 ≥ 0.9985 + Precision ≥ 0.99, o si conviene un feature flag en main que permita activar/desactivar los plugins XGBoost en tiempo de ejecución.

**Pregunta:** ¿Feature flag en JSON de componente (ya tenemos la infraestructura) o rama separada hasta validación completa?

---

**ESTADO DEL PIPELINE**

```
6/6 RUNNING
make test-all: ALL TESTS COMPLETE (verde)
AppArmor: 5/6 enforce · sniffer complain
arXiv: 2604.04952 Draft v15 (Cornell)
Branch: feature/phase3-hardening
Pubkey dev: e51a91e91d72f74fe97e8a4eb883c9c6eb41dd2fc994feaf59d5ba2177720f3d
```

---

*Alonso Isidoro Román · aRGus NDR · DAY 117 · Via Appia Quality 🏛️*

---

