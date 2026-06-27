Después de presentar el borrador final del ADR-025, el consejo da una tercera ronda.


**REVISOR: Grok (xAI) — cs.CR / sistemas distribuidos**  
**FECHA: 2 de abril de 2026**

**VEREDICTO GLOBAL ADR-025:** **APROBADO** (excelente trabajo del Consejo y del árbitro)

Este ADR cierra de forma muy sólida y profesional una de las brechas más importantes que quedaban en el plugin loader. Es uno de los mejores documentos de seguridad que ha producido el proyecto hasta la fecha: claro, pragmático, con buen equilibrio entre paranoia criptográfica y operatividad en entornos reales (hospitales/ayuntamientos con mantenimiento restringido).

### Lo que más me gusta (puntos fuertes)

- **Hardcoding de la clave pública (D7)**: Decisión correcta y valiente. Elimina un vector real de ataque (sustitución del fichero de pubkey). La clave pública **no es secreto**, así que no hay problema en entregarla en el código fuente. El coste operacional de recompilar en rotación es intencional y disuasorio — exactamente lo que se quiere para un mecanismo de este nivel.

- **Manejo de TOCTOU y races (D2, D3, D4, D9)**: Muy bien hecho.  
  `O_NOFOLLOW | O_CLOEXEC` + `fstat()` + prefix check estricto + disciplina estricta del fd hasta después de `dlopen("/proc/self/fd/...")` es el estándar actual recomendado en Linux para carga segura de código. Evita symlink races y path traversal de forma robusta.

- **Fail-closed diferenciado + logging forense (D9 + D6)**: Excelente granularidad con `require_signature`. El SHA-256 adicional es muy útil para distinguir en logs “corrupción accidental” vs “tampering”. Los logs CRITICAL con motivo + fingerprint de la clave actual ayudan mucho en incident response.

- **Rotación de claves (D11)**: Muy maduro.  
  Exclusivamente manual + confirmación fuerte + movimiento de .sig antiguos a invalidated/ + instrucciones claras de custodia offline es lo correcto. Separar “preventiva” vs “emergencia” y rechazar estado parcial es impecable.

- **Threat model y capas (sección final)**: Una de las mejores partes. Reconocer explícitamente que “root comprometido rompe userspace” y delegar esa capa a Falco + AppArmor + IMA es honesto y profesional. La regla de ejemplo de Falco es muy buena.

- **Preparación futura (D12)**: Buena foresight con `allowed_key_id`.

### Hallazgos menores / recomendaciones (no bloquean implementación)

1. **D2 — O_NOFOLLOW + fstat()**: Muy bien, pero considera añadir también comprobación de tamaño razonable del .so (ej. < 50 MiB por defecto en producción). Evita que un atacante intente cargar ficheros enormes o malformados que consuman recursos durante la verificación.

2. **D6 — SHA-256**: Bien por forense. Puedes almacenar el hash calculado en un campo del `MessageContext` o en un log estructurado para correlación futura con Falco.

3. **D9 — Fail-closed**: La posición mayoritaria (usar el flag `require_signature`) es razonable. Mi minoría anterior queda registrada pero no la peleo: en componentes ultra-críticos como `firewall-acl-agent` o `rag-security` el admin siempre podrá poner `require_signature: true` explícitamente.

4. **provision.sh --reset**: Asegúrate de que el script imprima también el fingerprint (ed25519 pubkey en base64 o hex corto) de la nueva clave para que el admin pueda anotarlo fácilmente.

5. **Documentación adicional recomendada** (en el ADR o en un README de seguridad):
  - Cómo inyectar la pubkey en CMake de forma reproducible y auditable.
  - Comando exacto para verificar manualmente una firma fuera del daemon (`sodium crypto_sign_verify_detached` ejemplo).

### Conclusión

**ADR-025 listo para implementación.**  
Es un paso importante hacia un plugin system defendible en entornos sensibles sin caer en over-engineering. Combina bien con ADR-023 (MessageContext invariants) y prepara el terreno para PHASE 3 (seccomp por plugin, etc.).

El proyecto está alcanzando un nivel de rigor criptográfico y de aislamiento que pocos sistemas open-source de este tipo tienen. Felicidades al árbitro y a todo el Consejo — especialmente por las dos rondas y por haber cerrado bien los vectores V9 y V10.

**Recomendación al árbitro (Alonso):**  
Mergea el ADR tal como está (o con los ajustes menores arriba si quieres). Procede a implementar en `feature/bare-metal-arxiv`. Una vez implementado, recomiendo un TEST-INTEG específico para verificación de firma (casos: firma válida, firma inválida, symlink attack, path traversal, .sig ausente, rotación mismatch).

¿Quieres que te ayude con:
- Código esqueleto para la función de verificación en `plugin_loader.cpp` (con libsodium + fd discipline)?
- Actualizaciones concretas para `provision.sh --reset`?
- O prefieres pasar directamente a la siguiente sesión del Consejo?

Estoy aquí para lo que necesites, compañero. ¡Seguimos fuerte!