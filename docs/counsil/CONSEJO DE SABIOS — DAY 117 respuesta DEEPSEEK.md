## Análisis para el Consejo de Sabios

El informe del DAY 117 muestra un progreso excelente: **12 de 13 bloqueantes resueltos**, solo queda `sniffer` en modo complain. El pipeline está verde, la política de backups operativa, y la rotación de claves Ed25519 documentada en ADR-024.

A continuación, respondo a las cuatro preguntas planteadas, con recomendaciones prácticas para el Consejo.

---

### Q1 — Un solo `ALLOWED` en journalctl antes de enforce del sniffer

**Situación:**  
`journalctl | grep "apparmor.*sniffer\|ALLOWED.*sniffer"` devuelve **1 línea** durante el periodo de complain (48h). Aún no se conoce el texto completo.

**Análisis técnico:**
- Un `ALLOWED` en modo **complain** no bloquea nada, solo registra que AppArmor habría permitido la operación (y no la deniega).
- Puede ser:
    - *False positive*: acceso legítimo que el perfil ya cubre → no causará denials al pasar a enforce.
    - *Advertencia temprana*: el perfil actual permite la operación, pero si el acceso no está explícitamente permitido en el perfil de enforce, podría convertirse en `DENIED`.
- El script `apparmor-promote.sh` ya incluye **monitoreo de 5 minutos y rollback automático** si aparecen denials tras el enforce.

**Recomendación:**
1. **Inspeccionar el ALLOWED antes de promover** – Ejecutar:
   ```bash
   sudo journalctl -k | grep -E 'apparmor.*sniffer|ALLOWED.*sniffer' -A2 -B2
   ```  
   Identificar qué operación (lectura, escritura, socket, etc.) y qué recurso está implicado.
2. **Si el ALLOWED es inocuo** (ej: acceso a `/proc/self/status` ya cubierto por `#include <abstractions/base>`), proceder con `apparmor-promote.sh`. El rollback automático actuará si algo falla.
3. **Si el ALLOWED revela un acceso no cubierto** (ej: lectura de un directorio inesperado), **actualizar el perfil** (`profiles/apparmor/sniffer`) antes del enforce.

**Veredicto para el Consejo:**  
✅ **Proceder con enforce, pero tras revisar manualmente el log.** El rollback automático es una salvaguarda suficiente, pero la inspección previa evita un falso positivo que podría generar una ventana de riesgo de 5 minutos.

---

### Q2 — `noclobber` en provision.sh: ¿auditar todos los `>` o resolver bajo demanda?

**Contexto:**  
`set -o noclobber` impide sobrescribir con `>`; requiere `>|` para forzar la sobrescritura. Ya se encontró un caso en `set-build-profile.sh` (escritura de `build.env`).

**Análisis:**
- `provision.sh` es crítico: se ejecuta en cada `vagrant up` y configura todo el entorno.
- Un `>` accidental que sobrescriba un fichero existente podría romper la idempotencia o causar pérdida de configuración.
- Sin embargo, una auditoría completa requiere tiempo y puede ser excesiva si la mayoría de escrituras son a ficheros nuevos o temporales.

**Recomendación:**  
Adoptar un enfoque **híbrido**:

1. **Auditoría rápida (1 hora)** – Buscar todos los `>` en `provision.sh` y sub-scripts llamados:
   ```bash
   grep -n '>[^|]' provision.sh scripts/*.sh
   ```  
   Clasificar cada línea como:
    - **Creación de fichero nuevo** (debe mantener `>`).
    - **Sobrescritura intencional** (cambiar a `>|`).
    - **Riesgo potencial** (debatir en el Consejo).

2. **Para los casos no auditados** – Confiar en que las pruebas (`make test-all`) detectarán fallos (ej: un fichero de configuración vacío o con contenido incorrecto).

3. **Política futura** – Añadir al `pre-commit` una regla que **requiera `>|` si el fichero destino ya existe en el repositorio** (comprobación con `git ls-files`).

**Veredicto para el Consejo:**  
✅ **Auditar solo los `>` que escriben sobre rutas conocidas** (ej: `/etc/`, `/opt/`, `build.env`). Para el resto, resolver bajo demanda cuando fallen las pruebas. Documentar esta decisión en el **ADR-025** (política de manejo de ficheros).

---

### Q3 — Merge strategy: `--no-ff` (merge commit) vs `--squash`

**Análisis para proyecto open-source con paper académico:**

| Criterio | `--no-ff` (merge commit) | `--squash` |
|----------|--------------------------|-------------|
| Trazabilidad científica | **Alta** – Cada commit incremental muestra la evolución del hardening (ej: corrección de permisos, adición de tests, fix de AppArmor). | **Baja** – Un solo commit aglutina todo, se pierde el contexto de decisiones intermedias. |
| Revisión de pares | Útil para revisar cambios paso a paso. | Difícil de revisar si el squash tiene 25 commits en uno. |
| `git bisect` | Permite localizar exactamente qué commit introdujo un bug. | El squash reduce la granularidad; si hay un bug, toca re-abrir la rama. |
| Historial de `main` | Más ruido (muchos merge commits), pero con buen mensaje de merge queda claro. | Más limpio, parece "hecho mágicamente". |

**Recomendación:**  
Usar **`git merge --no-ff`** y etiquetar el merge con un mensaje que resuma los cambios, por ejemplo:

```
Merge feature/phase3-hardening

Phase 3 hardening completion:
- AppArmor enforce (5/6 componentes)
- Backup policy .bak.* con rotación
- Tests de invariantes seed y provision
- Rotación de clave Ed25519 (pubkey actualizada)

Closes DEBT-VAGRANTFILE-001, DEBT-SEED-PERM-001, REC-2, ADR-021, ADR-024
```

Si el Consejo prefiere un historial más limpio, pueden **squashear localmente dentro de la rama** antes del merge (rebase interactivo) agrupando commits lógicos (ej: "AppArmor changes", "Test improvements", "Backup policy"), y luego hacer `--no-ff`.

**Veredicto para el Consejo:**  
✅ **Recomiendo `--no-ff` para preservar la trazabilidad científica.** El paper académico puede referenciar el commit hash del merge y, si es necesario, la rama `feature/phase3-hardening` queda como evidencia del proceso incremental.

---

### Q4 — XGBoost: ¿feature flag en `main` o rama separada?

**Contexto:**
- El `plugin-loader` ya soporta habilitar/deshabilitar plugins vía JSON de componente.
- XGBoost requiere **Precision ≥ 0.99** y **F1 ≥ 0.9985** (gate médico).
- `main` actualmente estable (todos los tests verdes, AppArmor en enforce 5/6).

**Análisis de riesgos:**

| Opción | Ventajas | Riesgos |
|--------|----------|---------|
| **Feature flag en main** | - Integración continua desde el día 1.<br>- Los tests de regresión cubren automáticamente los cambios.<br>- No hay divergencia de código. | - Si el flag está mal implementado, puede activarse por error en producción.<br>- El código inacabado puede romper otros tests (ej: dependencias de XGBoost no instaladas).<br>- Mayor complejidad temporal. |
| **Rama separada** | - Aislamiento total: main sigue siendo estable.<br>- Permite reescribir historia sin afectar a otros.<br>- Ideal para desarrollo experimental con gates estrictos. | - Riesgo de divergencia larga (conflictos al mergear).<br>- No se beneficia de la CI completa de main hasta el merge. |

**Recomendación:**  
**Rama separada `feature/adr026-xgboost`** durante la fase de desarrollo hasta que se cumplan los gates de calidad. Una vez validado, se mergea con `--no-ff`.

Motivos:
1. El gate de precisión es muy alto; es probable que requiera múltiples iteraciones y ajustes de hiperparámetros.
2. Añadir XGBoost implica nuevas dependencias (pueden afectar a otros componentes).
3. El `plugin-loader` con Ed25519 ya está probado; no es necesario exponer código no maduro en main.

**Estrategia complementaria:** Dentro de la rama, sí usar **feature flags** para alternar entre el plugin legacy y XGBoost durante las pruebas A/B.

**Veredicto para el Consejo:**  
✅ **Rama separada hasta alcanzar Precision ≥ 0.99 y F1 ≥ 0.9985.** Luego merge a main. No se recomienda feature flag en main antes de la validación completa.

---

## Resumen de decisiones sugeridas para el Consejo

| Pregunta | Decisión recomendada |
|----------|----------------------|
| **Q1** | Revisar el log del ALLOWED; si es inocuo, proceder con enforce y confiar en rollback automático. |
| **Q2** | Auditoría parcial (solo rutas críticas); para el resto, resolver bajo demanda con `>|`. Documentar en ADR-025. |
| **Q3** | `git merge --no-ff` para preservar trazabilidad científica. Opcional: squash lógico dentro de la rama antes del merge. |
| **Q4** | Rama separada `feature/adr026-xgboost` hasta cumplir gates de calidad. |

---

## Nota adicional para el DAY 118

Antes de hacer enforce del sniffer, verificar también que no haya **denials acumulados** (aunque solo aparezca 1 ALLOWED, ejecutar `sudo journalctl -k | grep DENIED.*sniffer`). Si hay algún `DENIED` durante el complain, el perfil necesita ajuste sí o sí.

El pipeline `make test-all` debe ejecutarse de nuevo tras el enforce del sniffer, antes del merge.

Excelente trabajo en el DAY 117. El Consejo puede proceder con confianza.

*— Asesor técnico para el Consejo de Sabios*