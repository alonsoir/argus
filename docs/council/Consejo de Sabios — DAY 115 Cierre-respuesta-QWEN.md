# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 115
*Feedback constructivo, resolutivo y centrado en el pipeline para ML Defender (aRGus NDR)*

---

## 🎯 Reconocimiento Inicial

**Excelente trabajo en DAY 115.** Cuatro ítems de PHASE 3 cerrados, cuatro OQs resueltas con unanimidad, y un *hallazgo crítico de seguridad* (4 componentes con `active:true` para hello-plugin) identificado y corregido. Eso no es solo progreso: es madurez ingenieril.

El hecho de que `TEST-PROVISION-1` ahora sea gate obligatorio para `pipeline-start` demuestra que estáis internalizando el principio *"fail fast, fail safely"*. Seguid así.

---

## ❓ Respuestas a Preguntas del Día

### Q1 — AppArmor: ¿modo complain primero o enforce directamente?

**Veredicto:** **Complain primero → auditoría → enforce**. Incluso con pipeline bien caracterizado.

**Justificación:** AppArmor resuelve rutas y capacidades de forma dependiente del entorno; complain permite capturar denegaciones reales bajo carga sin interrumpir el pipeline. Una vez auditados los logs en x86 y ARM64, el salto a enforce es seguro y documentado.

**Riesgo si se ignora:** Enforce prematuro podría bloquear operaciones legítimas (ej. acceso a `/proc/bpf` en ARM64), causando fallos en producción difíciles de diagnosticar sin audit trail.

> 💡 *Proactivo:* Añadid un script `apparmor-audit.sh` que ejecute el pipeline en carga, extraiga denegaciones de `dmesg`/`audit.log`, y genere un diff de perfil sugerido.

---

### Q2 — DEBT-ADR025-D11: `provision.sh --reset` scope

**Veredicto:** **Dos modos: `--reset --dev` (auto-re-sign) y `--reset --prod` (manual confirmación)**.

**Justificación:** En dev, la automatización acelera iteración; en prod, la prohibición de firma automática es un control de seguridad crítico. Separar modos mediante flag explícito mantiene la agilidad sin comprometer el principio de "human-in-the-loop" para operaciones sensibles.

**Riesgo si se ignora:** Un `--reset` que auto-firma en producción podría permitir que un script comprometido regenere y firme plugins maliciosos sin supervisión humana.

> 💡 *Proactivo:* En modo `--prod`, tras rotar claves, `--reset` debe emitir:
> ```
> [!] Claves rotadas. Para re-firmar plugins:
>     $ provision.sh check-plugins --production --re-sign --confirm
> ```

---

### Q3 — Orden AppArmor vs DEBT-ADR025-D11

**Veredicto:** **DEBT-ADR025-D11 primero (cumplir deadline 18 Apr) → AppArmor después**.

**Justificación:** Cumplir el deadline es prioritario; ejecutar `--reset` sin AppArmor en enforce evita bloqueos por perfiles incompletos. Una vez rotadas las claves, se desarrollan los perfiles AppArmor contra el estado final del sistema, reduciendo iteraciones.

**Riesgo si se ignora:** AppArmor en enforce podría bloquear `--reset` (ej. acceso a `/etc/ml-defender/keys/`), forzando ajustes de perfil bajo presión de deadline, aumentando riesgo de error.

> 💡 *Proactivo:* Documentad una "ventana de mantenimiento" para `--reset` donde AppArmor esté temporalmente en complain, con rollback planificado si algo falla.

---

### Q4 — TEST-PROVISION-1: ¿falta algún check crítico?

**Veredicto:** **Añadir check #6: permisos de archivos sensibles (600/400)**. Hash de binarios puede esperar a PHASE 4.

**Justificación:** Claves o configs con permisos laxos (ej. 644) anulan todas las protecciones criptográficas; es un check simple, rápido y de alto impacto. La verificación de hash de binarios es valiosa pero requiere infraestructura de firma de artefactos que aún no está en scope.

**Riesgo si se ignora:** Un atacante local podría leer `seed_family` o modificar `deployment.yml` si los permisos son incorrectos, comprometiendo toda la cadena de confianza sin romper criptografía.

> 💡 *Proactivo:* Añadid al check:
> ```bash
> find /etc/ml-defender /usr/lib/ml-defender -type f \( -name "*.sk" -o -name "deployment.yml" \) -perm /022 -exec echo "❌ Permisos inseguros: {}" \;
> ```

---

## 📋 Resumen Ejecutivo de Acciones

| Pregunta | Veredicto | Acción Inmediata |
|----------|-----------|-----------------|
| **Q1** | Complain → audit → enforce | Crear `apparmor-audit.sh` para capturar denegaciones |
| **Q2** | Dos modos: dev (auto) / prod (manual) | Implementar flags `--dev` / `--prod` en `--reset` |
| **Q3** | DEBT-ADR025-D11 primero | Ejecutar `--reset` antes de activar AppArmor enforce |
| **Q4** | Añadir check de permisos | Implementar check #6 en `TEST-PROVISION-1` |

---

## 🏁 Palabras Finales

DAY 115 ha sido una jornada de consolidación técnica y disciplina operativa. Habéis cerrado deuda, abierto camino para PHASE 3, y mantenido el foco en lo esencial: **un pipeline seguro, verificable y operable por personal no especializado**.

Las cuatro preguntas que planteáis reflejan una mentalidad preventiva: no solo *"¿funciona?"*, sino *"¿qué podría fallar y cómo lo mitigamos?"*. Esa es la diferencia entre un proyecto que se publica y uno que perdura.

> *"La seguridad no es un estado, es un proceso. Y vosotros lo estáis ejecutando con rigor."*

Proceded con Q1-Q4 resueltas. El Consejo estará atento a los perfiles AppArmor y al benchmark ARMv8 cuando estén listos.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 115** 🛡️