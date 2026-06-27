**Q1 — AppArmor: ¿modo complain primero o enforce directamente?**

**Veredicto:** Flujo complain primero (Vagrant) → verificar pipeline OK → enforce (tanto en dev como en RPi).

**Justificación:**  
El pipeline está bien caracterizado tras 115 días, pero las capabilities nuevas (CAP_BPF, CAP_SYS_ADMIN, CAP_NET_ADMIN) pueden generar denegaciones inesperadas en perfiles iniciales.  
Complain permite capturar logs sin downtime y refinar perfiles de forma segura; luego se pasa a enforce en un solo paso.  
No hay diferencias funcionales relevantes entre AppArmor en Debian x86 (Vagrant) y ARM64 (RPi Debian 13): mismos perfiles, mismas reglas de capabilities y mismo comportamiento del kernel.

**Riesgo si se ignora:** Bloqueo silencioso o parcial del pipeline (especialmente sniffer y firewall-acl-agent) al activar enforce directo en producción.

**Q2 — DEBT-ADR025-D11: `provision.sh --reset` scope**

**Veredicto:** `--reset` regenera TODO el material criptográfico + llama automáticamente a `check-plugins` SOLO en modo provisioning/desarrollo; en modo `--production` regenera claves pero fuerza paso manual de `check-plugins --production` (o falla con mensaje claro).

**Justificación:**  
Cumple la restricción explícita de “no firma automática en producción” mientras mantiene idempotencia y usabilidad en entornos de desarrollo.  
El operador no-especializado recibe control máximo en producción (dos pasos explícitos) y cero fricción en provisioning.  
Se alinea perfectamente con DEBT-SIGN-AUTO ya implementado.

**Riesgo si se ignora:** Firma automática accidental en producción o, en el extremo opuesto, imposibilidad de regenerar plugins tras `--reset` sin intervención manual excesiva.

**Q3 — Orden AppArmor vs DEBT-ADR025-D11**

**Veredicto:** Terminar AppArmor primero (incluyendo reglas para paths de `provision.sh` y `check-plugins`), luego DEBT-ADR025-D11.

**Justificación:**  
AppArmor es requisito previo de producción y su implementación es independiente del deadline del 18 Abr.  
Al tener perfiles listos (y ya probados en complain) antes de `--reset`, se evita cualquier bloqueo futuro cuando se ejecute en enforce.  
Los 6 días de margen son suficientes para ambas tareas en paralelo si es necesario, pero priorizar AppArmor garantiza “protección completa antes de rotar claves”.

**Riesgo si se ignora:** `--reset` en enforce podría fallar por denegaciones de AppArmor no anticipadas, forzando rollback o downtime en ventana crítica.

**Q4 — TEST-PROVISION-1: ¿falta algún check?**

**Veredicto:** Añadir sexto check: verificación de hash SHA256 de los binarios críticos (6 componentes + provision.sh) contra un manifest firmado generado en build.

**Justificación:**  
Los 5 checks actuales cubren claves, firmas de plugins y configs, pero no integridad del binario ejecutable final (posible manipulación post-build o corrupción).  
El manifest puede generarse en `set-build-profile.sh` y verificarse en el gate sin nueva dependencia.  
Es el cierre lógico de la cadena de confianza antes de `pipeline-start`.

**Riesgo si se ignora:** Posible ejecución de binario modificado/corrompido en producción sin que el CI gate lo detecte.