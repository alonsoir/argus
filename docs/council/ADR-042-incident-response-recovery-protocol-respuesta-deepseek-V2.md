## RESPUESTA DEL CONSEJO DE SABIOS — ADR-042 v2 (Segunda ronda)

**Acta de revisión adversarial definitiva**  
**Fecha:** 29 abril 2026 (DAY 135)  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Documento revisado:** ADR-042 v2 (Incident Response & Recovery Protocol)

---

### Resumen ejecutivo

El ADR-042 v2 incorpora casi todas las críticas de la primera ronda: aislamiento de red antes del poweroff (corrige la “paradoja del suicidio”), múltiples canales de alerta con cola persistente, initramfs para forensics, verificación de standby antes de promover, post‑recovery check, y cumplimiento GDPR con endpoint on‑premise. **El Consejo reconoce que el documento ha mejorado sustancialmente y está cerca de ser aprobable.**

Sin embargo, **persisten cuatro puntos débiles significativos** que deben resolverse antes de la implementación, además de algunas lagunas menores. A continuación se detallan con alternativas concretas.

---

## Puntos fuertes de v2 (lo que se ha mejorado)

1. **Aislamiento de red antes del poweroff** – Esencial. El poder fallar con `ip link down` antes de apagar elimina el vector de DoS.
2. **Múltiples canales de alerta + cola persistente** – Syslog local + webhook con cola + syslog remoto. No bloqueante.
3. **Safe mode via initramfs read‑only** – Mucho mejor que ejecutar forensics desde el sistema comprometido.
4. **Verificación de standby manual, no auto‑promoción** – Respeta el principio de que el standby podría estar también comprometido.
5. **Post‑recovery check + cuarentena** – Impide la reintegración automática.
6. **GDPR y endpoint on‑premise** – Maneja explícitamente la sensibilidad de datos clínicos.
7. **Limitaciones documentadas** – Honestidad científica sobre cadena de custodia, TPM, etc.

---

## Puntos débiles residuales (críticos)

### 1. `ip link down` puede no ser suficiente para aislar red

**Problema:**  
Un atacante con control del kernel (por ejemplo, rootkit) puede resetear la interfaz o ignorar la orden. Además, si el atacante ya tiene una sesión SSH abierta, bajar la interfaz no la cierra.

**Alternativa industrial:**
- Usar **nftables/iptables** para dropear todo el tráfico **antes** de bajar la interfaz:
  ```bash
  iptables -P INPUT DROP
  iptables -P OUTPUT DROP
  iptables -P FORWARD DROP
  ```
  Esto es más robusto frente a rootkits que intenten reestablecer la interfaz.
- Luego, eliminar reglas de conntrack: `conntrack -F`.
- Finalmente, `ip link set eth0 down`.

**Recomendación:** Añadir en `argus-network-isolate` el uso de iptables con política DROP antes de bajar interfaces. Depende de que el atacante no haya manipulado netfilter, pero es una defensa en profundidad.

### 2. La cola persistente de webhook no tiene mecanismo de reintento post‑recuperación

**Problema:**  
El ADR dice “encolar para reintento post‑recuperación”, pero no especifica quién ni cuándo procesa la cola. El nodo puede estar apagado; al reiniciar, ¿se reintenta el envío? ¿Con qué identidad?

**Solución sugerida:**
- La cola se almacena en `/var/lib/argus/irp-queue/` (persistente).
- Un servicio `argus-irp-queue-processor` (unit systemd) se ejecuta después de `network-online.target` **solo en modo operativo normal** (no en safe mode).
- Antes de reintegrar el nodo a la flota, se procesa la cola y se envía todo pendiente.
- Si falla de nuevo, se alerta al administrador por otros medios.

**Añadir esta especificación en el ADR v2 o en una deuda `DEBT-IRP-QUEUE-PROCESSOR-001`.**

### 3. Initramfs safe mode: ¿cómo se garantiza que el initramfs no ha sido manipulado?

**Problema:**  
Si el atacante tiene acceso físico o compromiso del gestor de arranque, puede modificar el initramfs almacenado en `/boot`. El safe mode podría ser falso.

**Alternativa industrial (a medio plazo):**
- **Secure Boot + UEFI** con claves personalizadas. El initramfs debe estar firmado.
- **TPM medició** del kernel e initramfs (extend PCRs).
- Para la demo FEDER se puede documentar como “requiere Secure Boot para seguridad avanzada; si no, el administrador debe verificar manualmente la integridad de `/boot`”.

**Incluir una nota en el ADR:** “En hardware sin Secure Boot, el safe mode ofrece una barrera contra ataques a nivel de sistema operativo, pero no contra manipulación del bootloader. Para entornos hospitalarios críticos, se recomienda UEFI Secure Boot y medición TPM (DEBT-IRP-SECUREBOOT-001).”

### 4. El fallback a RandomForest en Tipo B no cubre el caso de que el propio RF esté corrupto

**Problema:**  
El ADR asume que el `ml-detector` siempre puede usar el modelo RandomForest embebido. Pero si el atacante logra corromper el binario del detector, el fallback no es fiable.

**Alternativa:**
- **Doble detector** (principio de redundancia): un segundo proceso `ml-detector-fallback` que se ejecuta con privilegios mínimos, cuyos binarios se verifican por separado.
- O más simple: **canary file** con hash del modelo RF incrustado en el código. Si el binario principal falla la verificación de integridad, el sistema entra en modo “pánico final” (solo firewall con reglas estáticas).

**Recomendación:** No es bloqueante para la demo FEDER, pero debe documentarse como riesgo conocido y plan de mejora `DEBT-IRP-RF-INTEGRITY-001`.

---

## Lagunas menores (fáciles de subsanar)

### a) Falta una métrica de tiempo de restauración del SLA en producción
- El ADR menciona “rollback en <15min, nueva firma en <4h”, pero no indica cómo se mide ni quién es responsable.
- **Añadir:** Un contador en `/var/log/argus/irp-metrics.log` que registre `timestamp_trigger` y `timestamp_restored`. El sistema emite una alerta si se excede el SLA.

### b) No se especifica cómo se maneja la pérdida de alimentación durante el poweroff forense
- Si el nodo se apaga por poweroff inmediatamente después de aislar red, la recopilación de evidencia (que ocurre en safe mode) no se ha hecho aún. El ADR dice que `argus-forensic-collect` se ejecuta en safe mode, no antes del poweroff. Correcto. Pero si el hospital tira del cable, se pierde la evidencia.
- **Solución:** El servicio `argus-apt-integrity.service` debería, **antes** del poweroff, copiar volcado rápido (logs críticos) a una partición persistente que no sea el sistema principal (ej. `/var/log/forensics/`). Eso ya se hace con `journalctl --flush`. Es suficiente.

### c) El mensaje de consola en safe mode asume que el admin ve físicamente la pantalla
- En muchos hospitales el servidor está en un armario sin monitor.
- **Mejora:** Permitir redirigir la salida a un puerto serie (consola IPMI) y, opcionalmente, a un archivo en una unidad USB. Añadir `DEBT-IRP-CONSOLA-REMOTA-001`.

---

## Preguntas específicas al Consejo sobre v2 (simulando que el autor pide feedback final)

1. **¿El orden de acciones (aislar red → verificar standby → poweroff) es correcto si el atacante ya ha establecido persistencia (ej. cron job)?**  
   *Respuesta del Consejo:* Sí, sigue siendo correcto porque el poweroff interrumpe la ejecución del atacante. Pero la persistencia podría reaparecer tras el reinicio si el disco fue alterado. Ahí entra el safe mode y la reinstalación desde imagen dorada. No es un fallo del ADR.

2. **¿Debería el initramfs safe mode incluir una herramienta de restauración automática (ej. descargar imagen base desde repo)?**  
   *R:* No, eso reintroduciría dependencias de red y el riesgo de descargar software malicioso. El safe mode es forense y de verificación, no de reparación. La restauración la hace el administrador manualmente con un medio limpio.

3. **El webhook de best‑effort con cola persistente — ¿qué pasa si el endpoint on‑premise está caído y la cola crece indefinidamente?**  
   *R:* La cola debe tener un límite de tamaño (ej. 100 entradas) y rotación. Si se llena, se descartan las más antiguas y se registra un error crítico en syslog. Añadir esa política.

4. **¿Se debe implementar ahora el initramfs safe mode o puede esperar a post‑FEDER?**  
   *R:* El ADR lo clasifica como prioridad media, post‑FEDER. El Consejo está de acuerdo. Lo más urgente es `argus-network-isolate` y `argus-irp-notify`, que son implementables en horas.

5. **¿El post‑recovery check debe bloquear el arranque si falla?**  
   *R:* Sí, debe fallar y dejar el sistema en un estado de “recovery required” (consola de emergencia). Si no bloquea, el riesgo de reintegrar un nodo comprometido es real.

---

## Alternativas industriales que podrían considerarse en futuras versiones

| Área | Alternativa | Cuándo aplicaría |
|------|-------------|------------------|
| Forensics de alta garantía | **TPM 2.0 + PCR extended logs** + remote attestation | Hospitales grandes con presupuesto |
| Aislamiento más fuerte | **eBPF based isolation** (sandboxing del sistema) | Kernels 5.8+ (ya usan eBPF para XDP, se podría extender) |
| Notificación offline | **SMS/GSM módem** (específico para entornos sin red) | Hospitales rurales sin conectividad fiable |
| Recuperación automática desde partición A/B | **A/B partitioning** con verificación de firmas | Dispositivos embebidos, similar a Chromebooks |

Ninguna es bloqueante para v2.

---

## Veredicto final del Consejo

**El ADR-042 v2 se APRUEBA** con las siguientes **enmiendas obligatorias** antes de la implementación (no solo sugerencias):

1. **Reforzar el aislamiento de red:** usar `iptables -P INPUT DROP` antes de `ip link down`. Incluir en `argus-network-isolate`.
2. **Especificar el procesamiento de la cola persistente** (servicio systemd, límite de tamaño, reintento con backoff). Añadir a DEBT-IRP-A-001.
3. **Añadir una nota de advertencia sobre Secure Boot** para initramfs safe mode (sin él, el initramfs puede ser manipulado).
4. **Incluir el fallo de bloqueo del post‑recovery check** (arranque se detiene si falla).
5. **Documentar la métrica de SLA** y el log de tiempos de restauración.

Las demás sugerencias (consola remota, doble detector RF) se dejan como deudas opcionales post‑FEDER.

**Una vez incorporadas estas cinco enmiendas, el ADR-042 puede pasar a estado DISEÑO e iniciar la implementación de los componentes de alta prioridad.**

---

### Resumen para el equipo

- **Lo que está bien:** arquitectura en capas, aislamiento, cola, initramfs, GDPR, post‑recovery check.
- **Lo que debe corregirse:** el `ip link down` insuficiente (añadir iptables), la cola sin procesador, la falta de Secure Boot warning, el bloqueo del arranque post‑recovery, y la métrica SLA.
- **Prioridades inmediatas:** implementar `argus-network-isolate` y `argus-irp-notify` (con procesador de cola) – caben en DAY 136.
- **Documentación:** Actualizar BACKLOG.md con las nuevas deudas `DEBT-IRP-QUEUE-PROCESSOR-001`, `DEBT-IRP-SECUREBOOT-001`, `DEBT-IRP-RF-INTEGRITY-001`.

*Firmado por los 8 modelos, 29 abril 2026.*  
*Via Appia Quality — “Un sistema que sabe morir con dignidad sabe también renacer con evidencia.”*