## RESPUESTA DEL CONSEJO DE SABIOS — DAY 135

**Acta de aprobación y guía para la integración**  
**Fecha:** 29 abril 2026  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Documentos revisados:** commits `531b9792..7691f867`, `check-prod-all` PASSED, arXiv v18 enviado

---

### Resumen ejecutivo

El Consejo felicita al equipo por haber cerrado **cinco deudas técnicas críticas** en un solo día, incluyendo la integridad de apt sources con `FailureAction=reboot`, la transferencia controlada de semillas, la verificación del `confidence_score`, y la implementación completa del gate `hardened-full`. El envío de arXiv v18 consolida la publicación.

**Veredicto:** No se identifican bloqueantes para el merge de `feature/adr030-variant-a` a `main`. Las decisiones adoptadas son científicamente sólidas y reproducibles. A continuación, las respuestas detalladas a las cinco preguntas.

---

### Q1 — `FailureAction=reboot` en el servicio de integridad de apt sources

**Decisión del Consejo:** ✅ **Aprobado, con matices de ajuste fino.**

**Justificación científica (fail‑closed estricto):**
- El riesgo de que un nodo con fuentes de paquetes comprometidas (cambios en `/etc/apt/sources.list`, adición de repositorios maliciosos) propague actualizaciones infectadas a toda la flota aRGus via ZeroMQ/etcd supera el coste de un reboot inesperado.
- La decisión es consistente con el **principio de fail‑closed** que ya aplicamos a la semilla (permisos `0400`) y a la firma Ed25519.

**Sobre los 30 segundos de timeout:**
- **Suficiente** para entornos de laboratorio o municipales con centralización de logs local (rsyslog, systemd journal remoto).
- En hospitales grandes con SIEM central, 30 segundos puede ser justo si la red tiene latencia. **Recomendación:** Hacer el timeout configurable mediante un fichero JSON en `/etc/argus/apt-integrity.conf`, que a su vez pueda ser distribuido via etcd (ADR-026). Por defecto 30s, pero el administrador puede aumentarlo.

**¿Debería ser configurable via JSON/etcd?**
- Sí, a medio plazo. Pero para la demo FEDER, el valor por defecto 30s es aceptable. Documentad este parámetro en `docs/OPERATIONS.md` y cread una deuda `DEBT-APT-TIMEOUT-CONFIG-001`.

**Riesgo identificado:** Un falso positivo (firma SHA-256 no coincide por una actualización legítima de sources.list) provocaría un reboot inesperado. Para mitigarlo:
- El verificador debe **fallar solo si la suma actual difiere de la capturada en el primer provisionamiento**. Si el administrador modifica los sources manualmente, debe volver a ejecutar `hardened-setup-apt-integrity` para recalcular la suma. Documentarlo.

---

### Q2 — Transferencia segura de semillas en producción real (DEBT-SEEDS-SECURE-TRANSFER-001)

**Análisis de opciones:**

| Opción | Descripción | Ventajas | Desventajas |
|--------|-------------|----------|--------------|
| (A) SSH con clave efímera | Generar keypair en provisioning de dev, transferir via `scp` con autenticación de host | Sencillo, reutiliza infraestructura SSH | La clave efímera reside en la dev VM (superficie de ataque ampliada) |
| (B) Noise Protocol IK | Handshake cifrado sin necesidad de CA | Protocolo moderno, sin dependencias externas | Complejidad de implementación; requiere código adicional en Python o C++ |
| (C) Generación local en hardened VM | Las semillas se generan en la propia hardened VM mediante `argus-seed-gen` | **Elimina la transferencia**; máxima simplicidad | ¿Violaría ADR-013? Ver análisis. |
| (D) Otra: uso de TPM/generación determinista | Derivar semillas de un secreto maestro almacenado en TPM (si el hardware lo soporta) | Seguridad hardware, sin transferencia | Requiere TPM y complejidad de gestión |

**Respuesta del Consejo:**  
✅ **Opción C (generación local) es la arquitectura preferida** para producción real, **siempre que se cumpla el ADR-013** (semillas únicas por despliegue, no derivables globalmente).

**¿Violaría ADR-013?**
- ADR-013 exige: *“Cada despliegue debe generar su propio material criptográfico (seeds ChaCha20, HMAC, llaves Ed25519) en el momento del primer arranque, sin reutilizarlas entre instalaciones.”*
- La generación local en la hardened VM **no viola** ese principio, siempre que se cumpla:
  1. La generación se haga en la hardened VM misma durante el **primer arranque**, usando una fuente de entropía local (`/dev/urandom`).
  2. Las semillas no sean derivadas de ningún secreto común (ej. un master key).
  3. El proceso de generación esté protegido (permisos `0400` y `mlock()`).
- La implementación actual en `provision.sh` (dev VM) puede portarse a un binario `argus-seed-gen` que se ejecute en la hardened VM una sola vez.

**Recomendación concreta:**
- **Para Vagrant/dev:** Mantener la transferencia via `/vagrant` (aceptable por el contexto aislado).
- **Para producción real (post-FEDER):** Implementar generación local en la hardened VM. El proceso es:
  ```bash
  # En hardened VM, como root, durante el primer arranque
  /opt/argus/bin/argus-seed-gen --output /etc/ml-defender/ --owner argus:argus --perms 0400
  ```  
- Crear la deuda `DEBT-SEEDS-LOCAL-GEN-001` para post-FEDER.

**Opción D (TPM)** es interesante pero pospuesta a futuro (ADR-042). No necesaria para la demo.

---

### Q3 — Bloqueantes para el merge de `feature/adr030-variant-a` a `main`

**Respuesta:** ✅ **No hay bloqueantes. El Consejo aprueba el merge.**

**Verificación realizada:**
- `make hardened-full` (destroy incluido) → PASSED.
- `check-prod-all` (5/5 gates) → PASSED.
- Los tres elementos pendientes (compiler warnings, transferencia segura de seeds, `prod-deploy-seeds` separado) son **no bloqueantes** porque:
  - `DEBT-COMPILER-WARNINGS-001`: son warnings pre-existentes, no afectan al comportamiento en producción.
  - `DEBT-SEEDS-SECURE-TRANSFER-001`: aplica solo a producción real; en el entorno Vagrant es aceptable.
  - `prod-deploy-seeds` explícito: es una **característica**, no un defecto. Permite control granular de cuándo se despliegan las semillas.

**Recomendación adicional:** Antes del merge, actualizar el `README.md` de la rama `main` para reflejar los nuevos comandos `make hardened-full`, `make hardened-redeploy`, etc. Asegurar que la documentación de contribución incluye la REGLA EMECAS hardened.

---

### Q4 — Flujo `hardened-redeploy` + `prod-deploy-seeds` para iteración diaria

**¿Es correcto?**  
✅ **Sí, es el flujo óptimo para desarrollo iterativo.**

- `hardened-redeploy` recompila, firma, despliega binarios y **verifica** (check-prod-all).
- `prod-deploy-seeds` es un paso **manual** (o semiautomático) porque modifica material criptográfico sensible. En desarrollo, se ejecuta una vez tras el primer despliegue.

**¿Debería existir `make hardened-full-with-seeds`?**
- No es necesario. La semilla **no debe** estar en el mismo target que `hardened-full`, porque el objetivo de `hardened-full` es validar que el sistema **sin semillas** ya es funcional (solo falta material criptográfico).
- Para un despliegue completo desde cero en un entorno real (no desarrollo), el administrador ejecutaría:
  ```bash
  make hardened-full
  make prod-deploy-seeds
  make check-prod-all   # (ya se ejecutó al final de hardened-full, pero la semilla añade warnings; se puede volver a ejecutar)
  ```  
- Si se desea un solo comando para producción, se puede crear `make hardened-prod-deploy` que encapsule ambos, pero **no** lo incluyas en el gate pre-merge.

**Mejora sugerida:** Añadir un mensaje post-ejecución de `hardened-full` que indique: *“Sistema listo. Para desplegar seeds ejecute `make prod-deploy-seeds`.”*

---

### Q5 — Próximos pasos post-merge (DAY 136)

**Análisis de opciones:**

| Opción | Descripción | Justificación | Prioridad |
|--------|-------------|----------------|-----------|
| **A** | BACKLOG-FEDER-001 (presentación para Andrés Caro Lindo, deadline 22 Sep 2026) | Necesario para asegurar financiación. Requiere ADR-026 merged y demo reproducible. | **Alta** (preparación temprana) |
| **B** | ADR-029 Variant B (libpcap en ARM64) | Contribución científica comparativa XDP vs libpcap. | **Media** (puede esperar unas semanas) |
| **C** | DEBT-COMPILER-WARNINGS-001 (limpiar warnings) | Calidad de código, no bloqueante. | **Baja** (puede hacerse en background) |

**Recomendación del Consejo (unánime):**  
✅ **Opción A (BACKLOG-FEDER-001) como foco principal de DAY 136, con una subtarea de preparación del entorno de demo reproducible.**

**Razones:**
- La demo FEDER es el **hito crítico** para la financiación del Año 1. Aunque el deadline sea septiembre, la preparación debe comenzar ahora: definir el alcance, preparar un Vagrantfile de demo, grabar un pcap representativo de hospital, y redactar la narrativa.
- La Variant B (libpcap) es importante, pero no es un prerequisito para la demo (podemos mostrar solo la Variant A eBPF/XDP).
- Los warnings de compilación no son urgentes; pueden ser abordados por un miembro del equipo en paralelo o en días sin presión.

**Plan concreto para DAY 136:**
1. **Definir el escenario de demo:**
  - Tráfico de red simulado (CTU-13 Neris + algunos flows benignos hospitalarios).
  - Duración: 10 minutos.
  - Mostrar detección en tiempo real (interfaz web simplificada o logs formateados).
  - Enfatizar la baja latencia end-to-end (captura → alerta → bloqueo).
2. **Crear un script `demo-feder.sh`** que ejecute en la VM hardened:
  - `argus-sniffer` (captura desde archivo pcap replay o desde interfaz de loopback).
  - `ml-detector`, `firewall-acl-agent`, `rag-*` en segundo plano.
  - Generar tráfico con `tcpreplay` desde otra máquina.
  - Mostrar reglas añadidas por el agente.
3. **Documentar los requisitos de hardware para la demo** (p.ej., NUC x86 con 8GB RAM suficiente).
4. **Dejar la Opción B para DAY 137 o posterior.**

**Acción:** Crear la deuda `DEBT-FEDER-DEMO-SCRIPT-001` y asignarla a DAY 136.

---

### Acuerdos finales y checklist para el merge

| Tarea | Estado | Responsable | Plazo |
|-------|--------|-------------|-------|
| Merge `feature/adr030-variant-a` a `main` | ✅ Aprobado | Alonso | Inmediato |
| Actualizar README.md con comandos hardened | Pendiente | Equipo | Antes del merge |
| Crear `DEBT-APT-TIMEOUT-CONFIG-001` | Pendiente | Documentación | DAY 136 |
| Crear `DEBT-SEEDS-LOCAL-GEN-001` (producción real) | Pendiente | Backlog | post-FEDER |
| Crear `DEBT-FEDER-DEMO-SCRIPT-001` | Pendiente | Planificación | DAY 136 |
| Añadir mensaje post-`hardened-full` sobre seeds | Sugerencia | Makefile | DAY 136 (opcional) |

---

### Reflexión científica final

El DAY 135 ha demostrado que **el proceso de endurecimiento (hardening) puede ser automatizado y verificado por completo**, desde una VM limpia hasta un entorno de producción listo para desplegar semillas. El paso de `FailureAction=reboot` es una declaración de principios: **la seguridad no se negocia, aunque duela**.

La transferencia de semillas en desarrollo via `/vagrant` es aceptable en el contexto de laboratorio, pero la arquitectura correcta para el mundo real es la generación local. El Consejo valora la honestidad de haber documentado esa deuda explícitamente.

Con el merge de esta rama, aRGus alcanza un nuevo nivel de madurez. Ahora toca preparar la demo que convenza a los financiadores.

*Firmado por los 8 modelos, 29 abril 2026.*  
*Via Appia Quality — “Un nodo que no puede probar su integridad no merece arrancar.”* 🏛️