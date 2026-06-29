**Saludos del Consejo de Sabios.**

Hemos estudiado con atención el informe del DAY 167 y las cuatro cuestiones planteadas. A continuación ofrecemos nuestras recomendaciones, fundadas en los principios de transparencia, robustez arquitectónica y valor demostrativo que rigen aRGus NDR.

---

### Q1 — KNOWN-FAIL-VM-PERF-001: ¿excluir o aceptar?

**Recomendación: Opción C — Via Appia.**  
Dejar los fallos visibles, no bloqueantes, y registrarlos formalmente en `docs/KNOWN-FAILS.md`.

**Fundamento:**
- Esconder la deuda técnica (opción A) o añadir filtros verbosos (opción B) no aporta valor real al pipeline y puede enmascarar regresiones futuras en un entorno bare-metal.
- La visibilidad de estas fallas recuerda permanentemente que los thresholds de rendimiento son propios de bare-metal y no se alcanzan en VirtualBox. Es una decisión honesta y documentada, alineada con *Via Appia Quality*.
- Mantener los tests activos pero con fallo esperado permite que, si algún día las VMs mejoran o se migra a otro hipervisor, los tests pasen sin modificar código.  
  **Acción concreta:** Registrar `KNOWN-FAIL-VM-PERF-001` en `docs/KNOWN-FAILS.md` con el detalle de los 6 tests y la justificación aquí expuesta.

---

### Q2 — `.deb` vs. Suricata: prioridad relativa

**Recomendación: Adelantar la integración Suricata (`DEBT-ARGUSPP-SURICATA-001`) y posponer el empaquetado `.deb`.**

**Fundamento:**
- La presentación FEDER tiene un valor estratégico inmediato y la detección de red con Suricata + EMECAS++ constituye un demostrador mucho más impactante que un paquete `.deb` en este momento.
- El empaquetado `.deb` es necesario para la distribución, pero su aplazamiento unas jornadas no introduce riesgo técnico; la funcionalidad ya es verificable en el entorno CI/Vagrant.
- El orden original puede reordenarse sin romper dependencias: Suricata (2 sesiones) → `.deb` (1 sesión) → Deploy Vagrant.  
  **Matiz:** No debe descuidarse el registro de `DEBT-PACKAGE-DEB-001` en el backlog; simplemente se le asigna una prioridad P1 tras Suricata.

---

### Q3 — NTP/chrony en EMECAS++ como P0 gate

**Recomendación: Incorporar `DEBT-ARGUSPP-NTP-001` al Acto I de EMECAS++ antes de iniciar Suricata.**

**Fundamento:**
- ADR-046 v3 es claro: NTP/chrony es un *boot gate P0*. Si no está en EMECAS++, el sistema no cumple el estándar de arranque seguro definido por la arquitectura.
- Un desfase horario superior a 1 s compromete la validez de certificados, la correlación de logs (Suricata, Zeek) y la integridad de las marcas de tiempo de los tests end-to-end.
- Incorporarlo como un paso de Acto I (simple health-check: `chronyc tracking | grep "System time" | awk '{print $4}'` y validar offset) es un esfuerzo mínimo (menos de 1 sesión) y refuerza la solidez del gate antes de añadir Suricata.  
  **Acción concreta:** Actualizar `EMECAS++` para incluir un *Acto I – Chrony Health Check* que falle si el offset >1 s, luego proceder con Suricata.

---

### Q4 — `vendor.key` en Vault vs. Suricata

**Recomendación: El trabajo criptográfico (`BACKLOG-CRYPTO-VENDOR-KEY-001`) puede ejecutarse en paralelo o a continuación de Suricata, sin bloquear esta última.**

**Fundamento:**
- La integración de Suricata (instalación, configuración, reglas y validación con EMECAS) no depende de la clave privada del fabricante.
- La migración de `vendor.key` a Vault es una mejora de seguridad fundamental, pero su alcance es ortogonal a la detección de red.
- Si se dispone de ancho de banda (otro desarrollador o sesiones paralelas), puede abordarse simultáneamente; en caso contrario, se pospone como la siguiente tarea criptográfica tras cerrar Suricata, evitando así bloquear el valor demostrativo inmediato.  
  **Condición:** Asegurarse de que Suricata y la futura migración no creen conflictos de configuración, y documentar en el backlog la dependencia “ninguna”.

---

### Resumen del Consejo

1. **Q1:** Opción C — visibilidad y documentación honesta.
2. **Q2:** Suricata antes que `.deb`; `.deb` se aplaza al siguiente bloque.
3. **Q3:** `NTP/chrony` debe convertirse en Acto I de EMECAS++ ya, antes de Suricata.
4. **Q4:** `vendor.key` en Vault no bloquea Suricata; puede ir en paralelo o justo después.

Con estas decisiones, el equipo avanza hacia un DAY 168 centrado en cerrar el Acto I mejorado de EMECAS++ y encarar inmediatamente la integración Suricata, manteniendo la integridad arquitectónica y maximizando el impacto de la próxima demostración.

*Firmado: El Consejo de Sabios*  
*“Via Appia, sin atajos, sin deuda escondida.”*