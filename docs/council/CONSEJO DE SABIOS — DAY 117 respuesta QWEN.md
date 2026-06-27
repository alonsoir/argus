# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 117
*Feedback directo, constructivo y centrado en el pipeline para ML Defender (aRGus NDR)*

---

## 🎯 Reconocimiento Inicial

**Excelente ejecución en DAY 117.** Doce de trece ítems bloqueantes cerrados, tests de invariante criptográfico implementados, política de backups automatizada, y AppArmor enforce en 5/6 componentes. El hecho de que hayáis detectado y documentado la lección del `pubkey hardcoded → requiere rebuild post-reset` demuestra madurez operativa.

> *"La seguridad no es un estado, es un hábito. Y vosotros lo estáis cultivando."*

---

## ❓ Respuestas a Preguntas — Formato Solicitado

### Q1 — Sniffer tiene 1 ALLOWED en journalctl antes de enforce

**Veredicto:** **Proceder con enforce + monitoreo activo; NO bloquear por 1 ALLOWED aislado.**

**Justificación:** Un único ALLOWED tras pocas horas en complain es esperable: puede ser una operación legítima de inicio, un acceso a `/proc` durante probing, o un evento de BPF attach. El script `apparmor-promote.sh` con rollback automático de 5 minutos es la protección adecuada. Si el ALLOWED indica un gap real, el rollback lo capturará sin downtime prolongado.

**Riesgo si se ignora:** Postergar enforce por un ALLOWED no analizado puede generar "complain drift" — perfiles que nunca se activan por miedo a falsos positivos, dejando el componente sin hardening real.

> 💡 *Proactivo:* Tras ejecutar promote, guardar el output de `journalctl -k | grep sniffer` durante los primeros 10 minutos para auditoría posterior. Si el ALLOWED se repite, entonces revisar el perfil.

---

### Q2 — noclobber en provision.sh y el operador

**Veredicto:** **Audit proactivo limitado: revisar solo redirecciones a ficheros críticos (`.sk`, `seed.bin`, `deployment.yml`, `*.sig`)**.

**Justificación:** Un audit completo de todos los `>` en `provision.sh` es overkill y añade fricción innecesaria. Pero las redirecciones a ficheros sensibles merecen revisión explícita: si alguna debe ser intencional (`>|`), debe documentarse con comentario `# noclobber: intentional overwrite`. Esto equilibra seguridad operativa con agilidad de desarrollo.

**Riesgo si se ignora:** Un operador podría intentar sobrescribir un fichero crítico sin usar `>|`, encontrando un error críptico de noclobber que ralentiza operaciones de emergencia.

> 💡 *Proactivo:* Añadir al header de `provision.sh`:
> ```bash
> # noclobber: protege contra truncado accidental.
> # Para overwrite intencional: usar >| y añadir comentario # noclobber: intentional
> ```

---

### Q3 — Merge strategy: squash vs merge commit

**Veredicto:** **`git merge --no-ff` (preservar historial) + tag anotado con changelog estructurado**.

**Justificación:** Para un proyecto open-source con paper académico, la trazabilidad es esencial: revisores, auditores o futuros colaboradores deben poder mapear commits específicos a decisiones de diseño (ADR-021, ADR-024, etc.). `--no-ff` preserva esa granularidad. El "ruido" de 25 commits se mitiga con un tag anotado `v0.4.0-phase3-hardening` que incluya changelog resumido por categoría (security, ops, tests).

**Riesgo si se ignora:** Un squash oculta el contexto de cambios individuales, dificultando debugging futuro, auditoría de seguridad o replicación científica de resultados.

> 💡 *Proactivo:* Crear `docs/CHANGELOG-v0.4.0.md` con estructura:
> ```markdown
> ## Security
> - ADR-024: Noise_IKpsk3 implementado + OQ-5..8 resueltas
> - AppArmor profiles: 6 componentes, enforce validado
> 
> ## Operations
> - provision.sh --reset con seed_family compartido
> - Backup policy: máximo 2 backups por componente
> 
> ## Tests
> - TEST-INVARIANT-SEED: verificación de derivación criptográfica
> - TEST-PROVISION-1: 8/8 checks como CI gate
> ```

---

### Q4 — ADR-026 XGBoost: ¿feature flag o rama separada?

**Veredicto:** **Rama separada `feature/adr026-xgboost` hasta validación completa**, con hook opcional para testing local vía feature flag.

**Justificación:** XGBoost Track 1 requiere métricas estrictas (Precision ≥ 0.99 para entorno médico). Desarrollar en rama separada aísla el riesgo: si el plugin introduce inestabilidad, no afecta main estable. El feature flag en JSON puede usarse *dentro de la rama* para testing A/B local, pero no debe exponerse en main hasta que los umbrales se cumplan y haya revisión del Consejo.

**Riesgo si se ignora:** Un feature flag activable en main podría habilitarse accidentalmente en producción antes de validación completa, comprometiendo métricas de detección en entornos críticos.

> 💡 *Proactivo:* En la rama `feature/adr026-xgboost`, añadir `docs/XGBOOST-VALIDATION.md` con:
> - Checklist de métricas obligatorias
> - Procedimiento de promoción a main (requiere: tests + Consejo + tag)
> - Rollback plan si métricas degradan post-merge

---

## 📋 Checklist de Acciones Inmediatas (DAY 118)

```markdown
- [ ] Ejecutar apparmor-promote.sh sniffer + monitorear 10 min post-enforce
- [ ] Audit limitado de noclobber: revisar redirecciones a ficheros críticos
- [ ] Preparar changelog estructurado para tag v0.4.0-phase3-hardening
- [ ] Merge con --no-ff + tag anotado + push a main
- [ ] Abrir feature/adr026-xgboost desde main (no desde feature branch)
- [ ] Crear docs/XGBOOST-VALIDATION.md con criterios de promoción
- [ ] Notificar al Consejo cuando XGBoost esté listo para revisión pre-merge
```

---

## 🏁 Palabras Finales

Alonso:

DAY 117 ha sido una jornada de consolidación técnica ejemplar. Habéis transformado deuda en disciplina, bugs en tests, y procedimientos en automatización. Eso no es solo progreso: es la base de un sistema que puede operar con confianza en entornos críticos.

Las cuatro preguntas que planteáis reflejan una mentalidad madura: no solo *"¿cómo lo hacemos?"*, sino *"¿cómo lo hacemos de forma que sea mantenible, auditable y seguro a largo plazo?"*.

> *"La excelencia no es un acto, es un hábito. Y vosotros lo estáis construyendo commit a commit."*

Proceded con DAY 118. El Consejo estará atento al enforce del sniffer y a la apertura de ADR-026.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 117** 🛡️