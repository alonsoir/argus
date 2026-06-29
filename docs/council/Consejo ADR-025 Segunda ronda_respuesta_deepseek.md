## DeepSeek — Respuesta a la segunda ronda del ADR-025

Me parece que la discusión ha madurado mucho en esta segunda ronda. Las preguntas están bien planteadas y las posiciones de Claude y Alonso son claras. Voy a dar mi opinión punto por punto, como revisor técnico.

---

### Sobre el framing de la rotación

**Estoy de acuerdo con Claude en que el framing original (cron mensual) es incorrecto.** La rotación rutinaria no tiene sentido si el coste es recompilar y redesplegar. La rotación debería ser un evento excepcional, no una tarea automática. Por tanto, **no hay que implementar cron** en producción ni en la build machine. En todo caso, un recordatorio (notificación) para el admin, pero sin ejecución automática.

**Voto:** P1 → rotación exclusivamente manual, bajo decisión del admin. Cron como mera notificación (opcional, no parte del ADR).

---

### Sobre el coste operacional de D7 (clave pública hardcoded)

**El coste es aceptable si la rotación es excepcional.** Recompilar y redesplegar un binario de pocos megabytes no es un problema operacional grave, ni siquiera en hospitales con ventanas de mantenimiento limitadas. Además, el proceso se puede automatizar en el pipeline de CI/CD (un `make deploy` con regeneración de firmas).

**La alternativa (clave pública en fichero root-only) introduce un ataque adicional:** un atacante con capacidad de escritura (no necesariamente root) podría sustituir el fichero de clave pública por el suyo, y entonces firmar plugins maliciosos con su propia clave privada. Hardcoded evita ese vector. Por tanto, **mantener D7** (hardcoded) es más seguro y el coste operacional es asumible.

**Voto:** P2 → aceptable. Hardcoded es preferible.

---

### Sobre `provision.sh --reset`: comportamiento esperado

Propongo una secuencia clara:

1. **Advertencia y confirmación:** El script debe mostrar un mensaje claro sobre las consecuencias (todas las firmas actuales quedarán inválidas, el pipeline no arrancará hasta re-firmar todo). Exigir `--force` o confirmación interactiva.

2. **Estampación de fecha/hora:** Sí, en el nombre del fichero o en un metadato (ej. `key_20260402_120000.pub`). Útil para auditoría.

3. **Invalidación de `.sig` existentes:** **El script NO debe borrarlos automáticamente.** En su lugar, debe generar un nuevo par de claves, pero dejar los `.sig` antiguos intactos. La invalidación ocurre porque la clave pública en el binario (hardcoded) es la nueva. El pipeline fallará al verificar los `.sig` antiguos con la nueva clave pública. El admin debe re-firmar los plugins con la nueva clave privada (fuera de producción) y copiar los nuevos `.sig` antes de arrancar. Borrar los `.sig` antiguos es opcional, pero puede hacerse como limpieza.

4. **Bloqueo de arranque:** **Sí, el arranque debe fallar** si algún plugin no puede verificarse con la clave pública actual. Esto es fail-closed. El componente debe loguear un error claro y no cargar ese plugin. Si el plugin es obligatorio (crypto), el componente aborta.

**Voto:** P3 → adopto la propuesta anterior. El script debe advertir, generar nuevo par, dejar los `.sig` antiguos, y el pipeline fallará hasta que el admin re-firme y copie los nuevos `.sig`.

---

### Sobre Falco como capa de detección

**Root comprometido es un game over** para cualquier mecanismo en userspace. D7 (hardcoded) no es vulnerable a modificación de ficheros, pero sí a parcheo de memoria o a modificación del binario (si root puede escribir en el filesystem). Ahí es donde entra Falco (o IMA, o AppArmor) como capa de detección de integridad del sistema.

**El ADR-025 debe documentar este límite explícitamente** y referenciar a un futuro ADR (o a la imagen Debian hardened) para la mitigación de root comprometido. No es necesario resolverlo ahora, pero debe quedar claro que el plugin-loader no es suficiente contra un atacante con capacidades de root.

**Voto:** P4 → incluir una sección "Threat model limitations" que mencione Falco/IMA como capa complementaria, fuera del scope del ADR actual.

---

### Resumen de mi voto

| Pregunta | Mi respuesta |
|----------|-------------|
| P1 (trigger de rotación) | Rotación exclusivamente manual. Cron solo notificación (opcional, fuera del ADR). |
| P2 (coste D7) | Aceptable. Mantener clave pública hardcoded. |
| P3 (comportamiento `--reset`) | Advertir + forzar confirmación, estampar fecha, no borrar `.sig` antiguos, pipeline fail-closed. |
| P4 (Falco) | Documentar límite y referenciar trabajo futuro. |

---

### Comentario adicional

Hay un aspecto que no se ha discutido explícitamente: **¿cómo sabe el binario cuál es su clave pública hardcoded si se recompila con una nueva?** El proceso debe ser:
1. `provision.sh --reset` genera nuevo par.
2. La clave pública se inyecta en el código fuente (ej. un fichero `.h` generado) o se pasa como definición en compilación (`-DMLD_PUBKEY_HEX=...`).
3. Se recompila el plugin-loader y todos los componentes que lo enlazan.
4. Se re-firman los plugins con la nueva clave privada (en la build machine).
5. Se despliegan los nuevos binarios y los nuevos `.sig`.

Esto es perfectamente viable y no requiere cambios en el ADR, pero conviene mencionarlo en la sección de implementación.

---

Espero que esta segunda runda sirva para cerrar el ADR-025. Adelante.

— DeepSeek, miembro del Consejo de Sabios