**REVISOR: Grok (xAI) — cs.CR / sistemas distribuidos**  
**FECHA: 2 de abril de 2026**

**VEREDICTO GLOBAL ADR-025 (segunda ronda):** **ACEPTADO CON CONDICIONES**  
El enfoque que estás tomando es correcto y maduro. Separar claramente “rotación preventiva” de “rotación de emergencia” es la decisión correcta. Hardcodear la clave pública en el binario sigue siendo la opción más segura desde el punto de vista criptográfico y de threat model.

### Mi posición clara y directa

**P1 — Trigger de rotación:**  
**Sí, debe ser exclusivamente manual.**  
`provision.sh --reset` **nunca** debería ejecutarse automáticamente vía cron. Una rotación de clave de firma de plugins es una operación de alto impacto que implica parada + re-firma + redespliegue.  
Un cron automático sería peligroso (puede dejar el sistema sin plugins en mitad de la noche).  
**Solución aceptable:** un cron que solo envíe una notificación/recordatorio al admin (ej. “Han pasado 90 días desde la última rotación de claves de plugins. ¿Desea ejecutar provision.sh --reset?”). Pero la acción debe ser siempre manual y con confirmación explícita.

**P2 — Coste operacional de D7 (clave pública hardcoded):**  
**Es aceptable y preferible.**

Razones:
- La rotación de clave de firma **no debe ser rutinaria mensual**. Esa frecuencia es excesiva para este caso de uso. Una rotación preventiva cada 6-12 meses es más que suficiente en un entorno controlado (hospitales, ayuntamientos).
- En caso de incidente real (compromiso detectado), la recompilación + redespliegue es el precio que se paga por recuperar el control. Es comparable a rotar certificados TLS o claves SSH en un clúster.
- Hardcodear la clave pública elimina un vector de ataque (sustitución del fichero de pubkey). Es más fuerte que “fichero root-only + Falco”.
- El argumento “entregar código fuente abierto” no es problema: la clave pública **es pública por diseño**. No revela nada sensible.

**Alternativa de fichero root-only + hash embebido** es un compromiso aceptable solo si el coste operacional de recompilar es realmente prohibitivo en la práctica (muchas instalaciones distribuidas con mantenimiento muy restringido). Pero en mi opinión, **pierde más seguridad de la que gana en operatividad**.

**Recomendación final:** Mantener D7 (hardcoded) como decisión principal. Documentar la alternativa de fichero como posible mitigación futura si la experiencia en campo lo justifica.

**P3 — Comportamiento de provision.sh --reset:**

Debe hacer lo siguiente (obligatorio):

1. **Advertencia fuerte + confirmación doble**:
   ```
   ¡ATENCIÓN! Esta operación genera una nueva clave privada.
   La clave privada debe guardarse inmediatamente en un lugar seguro OFFLINE.
   Todos los plugins existentes quedarán inválidos.
   ¿Continuar? (escriba "YES" en mayúsculas)
   ```

2. Generar nuevo par Ed25519.
3. Estampar fecha y hora en el nombre del fichero privado (ej. `plugin_signing_key_20260402_1432.sk`).
4. **Invalidar activamente** los `.sig` existentes: borrarlos o renombrarlos a `.sig.old`. Mejor borrarlos para evitar confusión.
5. **NO bloquear automáticamente el arranque** si detecta mismatch de clave. Eso complicaría demasiado el loader. En su lugar:
    - Durante carga de plugins, si la firma no verifica → plugin no carga + log crítico.
    - Opcional: añadir un flag `--strict-signature-check` en modo producción que sí haga fail-closed total del componente.

**P4 — Falco como capa de detección:**  
**Sí, debe documentarse explícitamente en el ADR-025**, aunque sea como referencia a capa superior.

Texto sugerido:
> "El ADR asume un modelo de amenaza donde el daemon corre con privilegios limitados. Si el usuario root es comprometido, cualquier mecanismo userspace puede ser bypassado. La mitigación para este caso es el monitoreo en tiempo real mediante Falco (ver ADR-XXX - Runtime Monitoring), que debe alertar sobre modificaciones no autorizadas en /usr/lib/ml-defender/plugins/ y en el binario del componente."

### Resumen de mi recomendación final

- Mantener **clave pública hardcoded** en el binario (D7).
- Rotación = operación **manual** de alto impacto (nunca automática).
- Frecuencia esperada: preventiva cada 6-12 meses + emergencia cuando sea necesario.
- En rotación: todo o nada. Parar → re-firmar todo → redesplegar.
- `provision.sh --reset` debe ser muy conservador y educativo (advertencias fuertes).
- Documentar explícitamente el rol de Falco para el caso root comprometido.

Esto mantiene el principio **fail-closed** y **defense-in-depth** sin volver el sistema inmanejable operativamente.

**Posición de minoría (leve):**  
Si en pruebas reales el coste de recompilar/redesplegar resulta demasiado alto en entornos muy distribuidos (muchos ayuntamientos pequeños con personal TI limitado), entonces aceptar la alternativa de pubkey en fichero root-only + hash embebido en binario + Falco vigilando el fichero. Pero esta debería ser la opción B, no la principal.

---

¿Quieres que te prepare ahora mismo el **texto completo actualizado del ADR-025** incorporando todas estas decisiones (incluyendo la sección de rotación de claves, threat model y comportamiento de provision.sh)?

O prefieres que primero mandemos esta ronda al Consejo con mi veredicto incluido y luego redactamos el ADR final?

Dime cómo quieres proceder y lo hacemos en el siguiente paso.

Estamos dejando el mecanismo de plugins muy sólido. Buen trabajo.