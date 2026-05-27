Análisis directo, sin rodeos.

---

# Q1 — AppArmor: 1 `ALLOWED` en sniffer

### Veredicto: **REVISAR ANTES DE ENFORCE (obligatorio)**

### Justificación

* En modo *complain*, AppArmor **permite todo pero registra accesos que habrían sido bloqueados** ([Documentación de Ubuntu][1])
* Un `ALLOWED` indica precisamente eso:
  → *hay comportamiento no cubierto por el perfil*
* El sniffer es el componente **más privilegiado (CAP_BPF, SYS_ADMIN)** → cualquier hueco aquí escala riesgo.

### Recomendación técnica

1. Extraer el evento completo (no solo count):

   ```bash
   journalctl -k | grep sniffer -n
   ```
2. Clasificar:

    * acceso esperado → añadir regla explícita
    * acceso inesperado → investigar (puede ser bug o exceso de permisos)
3. Solo entonces `enforce`

### Riesgo si se ignora

Bloqueo silencioso del sniffer en producción o, peor, perfil permisivo mal definido.

---

# Q2 — `noclobber` en provision.sh

### Veredicto: **AUDIT COMPLETO AHORA (no diferir)**

### Justificación

* `noclobber` cambia semántica global del script
* Fallos aquí son **sutiles y peligrosos**:

    * archivos no actualizados
    * estados inconsistentes de claves/config

### Recomendación técnica

* Buscar todos los `>`:

  ```bash
  grep -R ">" provision.sh
  ```
* Clasificar cada uno:

    * idempotente → mantener `>`
    * overwrite intencional → cambiar a `>|`
* Añadir comentario obligatorio:

  ```bash
  # INTENTIONAL OVERWRITE
  ```

### Riesgo si se ignora

Errores operacionales intermitentes extremadamente difíciles de diagnosticar.

---

# Q3 — Merge strategy

### Veredicto: **merge commit (`--no-ff`)**

### Justificación

* Proyecto con paper + seguridad → necesitas **trazabilidad completa**
* Cada commit refleja:

    * decisiones
    * fixes de seguridad
    * aprendizaje (esto es oro en auditoría)

Squash = limpio, pero destruye contexto técnico real.

### Recomendación técnica

* Mantener historial
* Opcional: limpiar mensajes antes del merge (rebase interactivo ligero)

### Riesgo si se ignora

Pérdida de trazabilidad científica y dificultad para auditar decisiones críticas.

---

# Q4 — ADR-026 XGBoost

### Veredicto: **RAMA SEPARADA + feature flag SOLO al final**

### Justificación

* Estás en dominio médico (Precision ≥ 0.99)
* XGBoost introduce:

    * nueva superficie de ataque (plugins)
    * riesgo de falsos positivos/negativos

Meterlo en `main` antes de validación = mezclar **I+D con producción**

### Recomendación técnica

Fase correcta:

1. **feature branch (aislado)**
2. Validación completa:

    * métricas
    * estabilidad
    * integración
3. THEN:

    * merge a main
    * feature flag en JSON para activar/desactivar

### Riesgo si se ignora

Regresión del pipeline base o pérdida de confianza en el sistema.

---

# Evaluación global del DAY 117

## Lo mejor (muy sólido)

* Has alcanzado nivel **operacional serio**:

    * CI gate real
    * invariantes verificadas
    * rollback automático
    * control de permisos
* AppArmor rollout impecable (orden correcto)
* Descubrimiento del bug de `seed_family` → **nivel alto de madurez**

---

## Donde debes mantener disciplina

### 1. No relajar rigor en el último paso (sniffer)

Es el componente más peligroso → trátalo como tal.

### 2. Evitar deuda silenciosa (noclobber)

Esto es el tipo de bug que aparece en producción, no en tests.

### 3. Separar claramente:

* pipeline estable
* experimentación (XGBoost)

---

# Conclusión clara

Estás en un punto crítico:

* PHASE 3 está **bien cerrada técnicamente**
* Solo queda el paso más delicado: **cerrar seguridad sin introducir regresiones**

Si haces:

* revisión del ALLOWED
* audit de noclobber
* merge con historial
* XGBoost aislado

→ tienes un pipeline listo para producción realista.

Si te saltas cualquiera de esos cuatro:

→ introduces deuda invisible que aparecerá más adelante, cuando más cueste.

---

Si quieres, en el siguiente paso puedo proponerte un **checklist de “pre-merge a main” tipo producción real** para validar que v0.4.0 está realmente listo.

[1]: https://documentation.ubuntu.com/security/docs/security-features/privilege-restriction/apparmor/?utm_source=chatgpt.com "AppArmor - Ubuntu security documentation"
