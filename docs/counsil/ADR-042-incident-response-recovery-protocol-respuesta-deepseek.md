## RESPUESTA DEL CONSEJO DE SABIOS — ADR-042

**Acta de revisión adversarial**  
**Fecha:** 29 abril 2026 (DAY 135)  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Documento revisado:** ADR-042 (Incident Response & Recovery Protocol)

---

### Valoración general

El ADR-042 aborda un tema **crítico y hasta ahora ausente** en aRGus: cómo responder ante incidentes de integridad sin caer en la falsa dicotomía “seguridad vs disponibilidad”. Los principios P1–P5 son sólidos y alineados con buenas prácticas de *incident response* en sistemas críticos (NIST SP 800-61, ISO/IEC 27035). La separación en tres capas por incidente es clara y extensible.

**Sin embargo, el Consejo identifica varios puntos débiles y omisiones** que, de no corregirse, podrían llevar a una implementación frágil o incluso contraproducente. A continuación, se presentan con honestidad intelectual y se proponen alternativas basadas en la industria.

---

## Puntos fuertes (lo bonito y bien pensado)

1. **P1 – “El sistema nunca muere en silencio”**  
   Es un principio fundamental. La inclusión de webhook best‑effort y logging local es correcta. Muchos sistemas fallan en este punto.

2. **P2 – Acción proporcional**  
   Diferenciar entre OS comprometido (poweroff), plugin defectuoso (unload+rollback) y pipeline degradado (modo seguro) es acertado.

3. **P3 – Herramientas, no un sistema negro**  
   El *safe mode* con recogida de evidencia, firma y confirmación al admin es una característica que pocos NDR tienen. Bien.

4. **P5 – Forensics primero**  
   Impedir la limpieza antes de recopilar evidencia es crucial. Muchos equipos destruyen la escena del crimen.

5. **Incidente Tipo B – Emergency Plugin Unload + fallback a RandomForest**  
   La capacidad de `dlclose()` inmediato y caer a un modelo embebido es elegante. El hot‑swap firmado evita downtime.

6. **Deudas identificadas**  
   El ADR es honesto al marcar `DEBT-IRP-C-001` (pipeline degradado) como post‑FEDER y priorizar `argus-irp-notify` como primer paso.

---

## Puntos débiles y omisiones (lo que debe mejorar)

### 1. Webhook best‑effort: “grito” puede ser insuficiente
- **Problema:** Un webhook que falla silenciosamente (por red caída, endpoint fuera de servicio) deja al hospital sin alerta. El nodo se apaga y nadie sabe por qué.
- **Alternativa industrial:** Usar **múltiples canales** con fallback:
    - Syslog remoto (con `*.* @loghost:514` y `discard` after failure).
    - SNMP trap (tradicional en entornos hospitalarios).
    - Escribir una alerta en un **archivo persistente** que un watchdog externo (ej. monitoreo Nagios) pueda leer.
- **Recomendación:** El webhook debe ser **uno de varios destinos**, no el único. Implementar `argus-irp-notify` que itere sobre una lista de URLs y métodos, registrando éxito/fracaso en `/var/log/argus/irp.log`. El fallo de todos los destinos no debe bloquear el poweroff.

### 2. ¿Forensics desde sistema comprometido o desde entorno externo?
- **Problema (OQ‑2):** El ADR propone ejecutar `argus-forensic-collect` en *safe mode* (boot externo). No detalla cómo se arranca ese modo. En hardware físico sin consola remota, pedir al admin que inserte un USB es poco práctico.
- **Alternativa industrial:**
    - **Opción A (iniciar desde initramfs):** Configurar una entrada GRUB “aRGus Safe Mode” que arranque un initramfs mínimo con el recopilador estático. El sistema comprometido nunca monta los discos en modo lectura–escritura.
    - **Opción B (firma de ejecutable y ejecución en vivo):** Si se confía en que el kernel aún no está comprometido, se puede ejecutar un binario estático, **read‑only** y verificado con firma Ed25519, que realice las lecturas directamente desde el disco en modo solo‑lectura. Luego se apaga.
- **Recomendación:** Implementar ambas: un script que intente ejecutarse desde el sistema vivo, pero si detecta signos de compromiso (p. ej. `LD_PRELOAD` no esperado), que aborte y pida entrar en el modo GRUB. Documentar el procedimiento.

### 3. Endpoint receptor: SaaS externo vs on‑premise (GDPR)
- **Problema (OQ‑3):** Si el endpoint es `irp.argus-ndr.org` gestionado por el equipo aRGus, cualquier log que contenga IPs de pacientes, fechas de acceso a historiales clínicos, o datos identificables viola GDPR. El hospital no puede enviar esa información a un tercero sin consentimiento explícito.
- **Alternativa industrial:**
    - **Modelo híbrido:** El recopilador empaqueta la evidencia, la cifra con una clave pública del hospital (proporcionada en el despliegue), y la envía a un **colector on‑premise** (ej. un servidor local con una API simple). El equipo aRGus solo proporciona el receptor de referencia para pruebas, no para producción.
    - **Para la demo FEDER:** Se puede usar un endpoint de prueba que anonimice los datos (eliminando IPs, timestamps exactos, etc.) y obtener consentimiento de la organización colaboradora.
- **Recomendación:** Añadir `DEBT-IRP-GDPR-001` para implementar cifrado local + colector on‑premise. En el ADR, indicar que el endpoint SaaS es solo para diagnóstico y debe ser reemplazado en producción.

### 4. Fallback RandomForest: ¿realmente disponible y suficiente?
- **Problema (OQ‑4):** El ADR asume que el modelo RandomForest embebido en `ml-detector` funciona igual que el plugin XGBoost. Sin embargo, el plugin podría tener mejor recall para ciertos ataques. Un hospital puede aceptar una degradación temporal, pero necesita un SLA de restauración.
- **Alternativa:**
    - Definir un **SLA interno**: el plugin anterior (última versión firmada conocida) debe poder restaurarse en menos de 15 minutos (ya está en `dist/`).
    - Para plugins completamente nuevos (no hay versión anterior), el fallback es RF; el SLA para firmar una versión corregida es <4h (equipo aRGus).
- **Recomendación:** Añadir una métrica en `check-prod-all` que verifique que el RF está presente y funcional (inferencia de prueba). Documentar el SLA en `docs/IRP-SLA.md`.

### 5. Promoción automática de standby: riesgo de compromiso en cadena
- **Problema (OQ‑5):** Si el nodo primario se apaga por fuentes de APT comprometidas, el atacante pudo haber manipulado también el nodo standby (por ejemplo, a través de la misma red). Promoverlo automáticamente puede propagar el problema.
- **Alternativa industrial:**
    - **Quorum con testigo externo:** No promover a menos que un tercer nodo (o un servicio de salud externo) verifique la integridad del standby.
    - **Modo manual por defecto:** El standby se convierte en primario solo tras confirmación humana (vía API o webhook). La alta disponibilidad en hospitales suele permitir una ventana de <1 min para intervención manual si el personal está entrenado.
- **Recomendación:** Para el primer despliegue, deshabilitar la promoción automática. Incluir un script que el admin pueda ejecutar para promover tras verificar la integridad. Añadir `DEBT-IRP-HA-002` para implementar quorum simple más adelante.

### 6. Falta de detección de comportamiento anómalo del plugin (no solo métricas)
- **Problema:** La detección de Tipo B se basa en `confidence_score` fuera de rango o falsos positivos observados por el operador. Un plugin malicioso podría comportarse bien durante días y luego activarse.
- **Alternativa:**
    - **Canary deployment** (ADR-040 ya lo sugiere): desplegar el plugin en un 5-10% del tráfico durante 24h antes de promocionar al 100%. Monitorear desviaciones en la distribución de `confidence_score` y tasas de alerta.
    - **Fuzzing del plugin** en entorno de staging (libFuzzer sobre su API) antes de firmar.
- **Recomendación:** Integrar la regla de canary en el proceso de despliegue de plugins (ya en ADR-040). No es necesario modificar el ADR-042, pero debe mencionarse como prevención.

### 7. Incidente Tipo C (pipeline degradado) es demasiado vago
- **Problema:** Se etiqueta como “post‑FEDER” pero es muy probable en un hospital (por ejemplo, que falle etcd, o ml-detector). La respuesta actual es silenciosa.
- **Recomendación:** Definir un **esqueleto** para Tipo C ahora, aunque sea básico:
    - Si etcd falla, el sniffer sigue capturando pero no puede consultar reglas distribuidas; continuar con reglas locales cacheadas.
    - Si ml-detector falla, el firewall no recibe nuevas alertas; solo las reglas existentes persisten.
    - El admin recibe una alerta “pipeline degradado” con un código de diagnóstico.
    - No es necesario implementar toda la lógica, pero sí definir el comportamiento esperado.

---

## Respuestas a las preguntas abiertas (OQ‑1 a OQ‑5)

| ID | Pregunta | Respuesta del Consejo |
|----|----------|------------------------|
| **OQ‑1** | ¿Webhook best-effort o síncrono con timeout? | **Best‑effort con timeout de 2 segundos, sin bloqueo.** Si falla, se registra en `/var/log/argus/irp-failure.log` y se continúa con el poweroff. Preferimos un `curl --max-time 2 --retry 0` para no retrasar la acción defensiva. El timeout de 5s es aceptable solo si se demuestra que la red hospitalaria responde en <100ms; 2s es más seguro. Además, añadir envío syslog remoto como alternativa asíncrona. |
| **OQ‑2** | ¿Ejecutar forensics desde boot externo o sistema comprometido? | **Desde boot externo (initramfs) por defecto**, pero proporcionar también un binario estático verificado para ejecución en vivo si el administrador confirma que el kernel no está comprometido (modo experto). La implementación inicial puede ser el binario estático; la deuda `DEBT-IRP-FORENSICS-001` cubrirá el initramfs. |
| **OQ‑3** | ¿Endpoint SaaS o on‑premise? | **On‑premise obligatorio para hospitales.** El equipo aRGus proporciona una implementación de referencia (servidor Python simple) que el hospital puede desplegar en su propia red. Para la demo FEDER se puede usar un endpoint de prueba con anonimización y consentimiento. Añadir `DEBT-IRP-GDPR-001`. |
| **OQ‑4** | ¿RandomForest como fallback suficiente? | **Sí, pero con SLA de restauración del plugin.** El hospital debe conocer que la F1 puede bajar a 0.98 (estimado) hasta que se restaure el plugin. SLA sugerido: rollback a versión anterior en <15 minutos (scripts ya existen). Para plugins sin versión anterior, <4h para obtener nuevo plugin firmado por el equipo. Añadir `DEBT-IRP-SLA-001`. |
| **OQ‑5** | ¿Auto‑promote de standby siempre deseable? | **No, deshabilitado por defecto en el primer despliegue.** El administrador debe promover manualmente tras verificar la integridad del nodo standby (ejecutando `argus-apt-integrity-check` y `argus-forensic-collect` de forma preventiva). Para futuros despliegues, se puede implementar promoción automática con quorum simple (testigo externo) como `DEBT-IRP-HA-002`. |

---

## Alternativas industriales no mencionadas (pero relevantes)

1. **AIDE / Tripwire con central logging:** En lugar de un script casero, usar herramientas estándar para monitorizar la integridad del sistema. aRGus podría integrar AIDE con un perfil predefinido y alertar via syslog. Sin embargo, el diseño actual es más ligero y está bien.
2. **Network quarantine en lugar de poweroff:** Algunos entornos hospitalarios prefieren aislar el nodo mediante una regla de firewall (ej. `iptables -P INPUT DROP`) en lugar de apagarlo, para poder acceder en remoto y hacer forensics. El ADR opta por poweroff por simplicidad, pero podría ofrecer una alternativa configurable (ej. `ARGUS_IRP_ACTION=quarantine`). **Recomendación:** Añadir como deuda `DEBT-IRP-QUARANTINE-001` para entornos que requieran acceso remoto.
3. **Recuperación automática desde imagen dorada:** Algunos sistemas (ej. Chromebooks) utilizan una partición de recuperación que restaura el sistema a un estado limpio. Podría ser aplicable a aRGus si el hardware tiene particiones A/B. No urgente.

---

## Conclusión y voto del Consejo

El ADR-042 es **necesario y bien intencionado**, pero actualmente es **PRE‑DISEÑO** con varias lagunas que deben subsanarse antes de la implementación.

**Veredicto:**
- **Aceptado en principio**, condicionado a la incorporación de las siguientes enmiendas:
    1. Múltiples canales de alerta (syslog, SNMP, webhook).
    2. Especificación clara del entorno de forensics (initramfs o binario estático).
    3. Endpoint on‑premise para producción, con cifrado.
    4. SLA de restauración de plugins documentado.
    5. Deshabilitar auto‑promote por defecto.
    6. Añadir esqueleto para Incidente Tipo C.

- Se deben crear las deudas identificadas (`DEBT-IRP-FORENSICS-001`, `DEBT-IRP-GDPR-001`, `DEBT-IRP-SLA-001`, `DEBT-IRP-HA-002`, `DEBT-IRP-QUARANTINE-001`) y priorizarlas junto a las ya existentes.

- El equipo puede proceder a implementar `argus-irp-notify` (webhook) inmediatamente, ya que es de bajo riesgo y mejora la situación actual (silenciosa).

*Firmado por los 8 modelos, 29 abril 2026.*  
*Vía Appia Quality — “Un sistema que no sabe morir con dignidad no merece vivir en un hospital.”*