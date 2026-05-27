Alonso, el **DAY 115** ha sido una jornada de consolidación estructural. Haber cerrado las 4 OQs de Noise y, simultáneamente, haber resuelto el bug de seguridad de los componentes con `active:true` para el plugin hello, justifica por sí solo el esfuerzo del domingo. El pipeline ha pasado de ser un conjunto de procesos a ser un **sistema operativo de seguridad** coherente.

Aquí tienes el veredicto del Consejo sobre el cierre de fase:

---

### 🏛️ Veredicto del Consejo de Sabios — DAY 115

#### Q1 — AppArmor: ¿complain o enforce?
**Veredicto:** **MODO COMPLAIN PRIMERO.**
**Justificación:** El uso de `CAP_BPF` y `CAP_SYS_ADMIN` en el sniffer es "territorio minado"; pequeños cambios en las syscalls de libpcap o ZeroMQ entre x86 y ARM64 pueden causar un crash silencioso en enforce. Un ciclo de 24h en complain capturando logs en `/var/log/audit/` es el estándar de oro para no romper la disponibilidad en hospitales.
**Riesgo si se ignora:** Denegación de servicio (DoS) accidental en el arranque del sniffer al migrar a Raspberry Pi debido a diferencias en los paths de sysfs.

#### Q2 — `provision.sh --reset` scope
**Veredicto:** **MANUAL EN DOS PASOS (Separación de privilegios).**
**Justificación:** `--reset` debe regenerar el material, pero la firma de plugins debe seguir siendo un acto explícito del operador para mantener la integridad de la cadena de suministro (ADR-032). En producción, `--reset` debe invalidar firmas antiguas y dejar el sistema en "fail-closed" hasta que el operador firme externamente.
**Riesgo si se ignora:** Un atacante con acceso a `provision.sh` podría blanquear un plugin malicioso mediante un `--reset` automático.

#### Q3 — Orden: AppArmor vs DEBT-ADR025-D11
**Veredicto:** **DEBT-ADR025-D11 PRIMERO (Cumplir deadline).**
**Justificación:** La rotación de claves es una deuda de seguridad fundamental; AppArmor es una capa de endurecimiento. Es preferible tener un sistema capaz de rotar claves ante una exfiltración antes que un perfil de AppArmor que, como bien sospechas, podría interferir con las operaciones de escritura de claves de `--reset`.
**Riesgo si se ignora:** Incumplimiento del contrato de recuperación ante desastres (ADR-025) y posible bloqueo de permisos (EACCES) al intentar rotar claves bajo un perfil AppArmor restrictivo.

#### Q4 — TEST-PROVISION-1: ¿Falta algún check?
**Veredicto:** **IMPLEMENTAR CHECK DE "NET-CAPABILITIES".**
**Justificación:** Ver que los binarios están ahí no basta; verifica que `getcap` devuelva las capabilities necesarias (`cap_net_raw`, `cap_net_admin`) para que el sniffer y el firewall funcionen sin ser root. Sobre el hash de binarios, es mejor delegarlo a un sistema de integridad de archivos externo (ej. Samhain o el propio AppArmor).
**Riesgo si se ignora:** El pipeline arranca, el systemd reporta "active", pero el sniffer no captura nada por falta de permisos en el socket raw, resultando en un "falso positivo" de operatividad.

---

### 🛡️ Análisis de Riesgo Residual: El hallazgo del Hello Plugin

El hecho de que 4 componentes tuvieran el plugin hello activo en producción es un recordatorio de que **el factor humano es el eslabón más débil**. El nuevo check `make validate-prod-configs` es ahora la pieza de seguridad más importante de la PHASE 3.



**Recomendación proactiva para el DAY 116:**
Antes de empezar con AppArmor, asegúrate de que el `test-provision-1` incluya la validación de que el `build-active` apunta efectivamente a `release` en el entorno de validación final.

**¿Damos por validado el hito TEST-PROVISION-1 para proceder con la rotación de claves mañana?** 🏛️🛡️🚀