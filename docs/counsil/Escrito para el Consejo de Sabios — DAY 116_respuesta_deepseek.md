## Respuesta del Consejo de Sabios – DAY 116 (13 Abril 2026)

El Consejo ha examinado el trabajo del día. Se valora muy positivamente la finalización de PHASE 3, la detección y corrección del bug arquitectural de `seed_family`, y la implementación de `provision.sh --reset` con tests. A continuación, las respuestas a las preguntas, seguidas de observaciones críticas para mejorar la robustez del sistema.

---

### Q1 – AppArmor enforce strategy: orden de activación

**Veredicto:** **En orden de menor a mayor privilegio (etcd-server → rag-* → firewall → sniffer).**  
**Justificación:**
- Los componentes sin capacidades especiales (etcd-server, rag-ingester, rag-security, ml-detector) tienen menor probabilidad de causar bloqueos imprevistos. Activarlos primero permite validar los perfiles base.
- El firewall-acl-agent necesita `CAP_NET_ADMIN`, y el sniffer necesita `CAP_BPF`, `CAP_SYS_ADMIN`. Deben ser los últimos, y se recomienda mantenerlos en `complain` al menos 48 horas adicionales mientras se monitorizan logs.
- **Ningún componente debe permanecer indefinidamente en complain** – pero el sniffer puede requerir más tiempo por su interacción directa con XDP/eBPF.

**Riesgo si se ignora:** Activar sniffer o firewall antes de tiempo podría causar fallos en el pipeline que interrumpan la detección de red, dejando el sistema ciego durante el troubleshooting.

---

### Q2 – DEBT-SEED-PERM-001: mensaje engañoso de `chmod 600`

**Veredicto:** **Opción (a) – corregir el mensaje a `640` y documentar por qué.**  
**Justificación:**
- `600` sería incorrecto porque los procesos no corren como root (deben correr con un usuario dedicado, ej. `ml-defender`). `640` con grupo `vagrant` (o `ml-defender`) permite lectura por el grupo, no por otros.
- Cambiar a `600` y hacer que los procesos corran como root **aumenta la superficie de ataque** (cualquier vulnerabilidad en el pipeline da root). Es una mala práctica.
- Documentar como *“requisito: el grupo del usuario que ejecuta los componentes debe tener acceso de lectura al seed”* en la guía de operaciones.

**Acción concreta:**
- Modificar el mensaje de `SeedClient` para sugerir `chmod 640` y `chown root:ml-defender`.
- Añadir un check en `TEST-PROVISION-1` que verifique los permisos correctos (ya lo hicieron con check #6, pero ajustar el mensaje de error).

**Riesgo si se ignora:** Un operador novato podría aplicar `chmod 600` y luego preguntarse por qué los componentes no arrancan (permiso denegado al leer el seed). Pérdida de tiempo y confianza.

---

### Q3 – Próxima fase: ¿ADR-026 o consolidar AppArmor + deudas?

**Veredicto:** **Dedicar DAY 117 íntegramente a AppArmor enforce + deudas pendientes, NO abrir ADR-026 todavía.**  
**Justificación:**
- PHASE 3 está técnicamente completa, pero AppArmor en `complain` no es suficiente para producción. Un día más para refinar perfiles, ejecutar `aa-logprof`, y activar `enforce` en los componentes de menor riesgo es una inversión que previene regresiones.
- Las deudas técnicas identificadas (`DEBT-VAGRANTFILE-001`, `DEBT-SEED-PERM-001`, `DEBT-RAG-BUILD-001`) son pequeñas pero molestas. Limpiarlas ahora mejora la experiencia del desarrollador.
- ADR-026 (XGBoost) es una funcionalidad nueva que requerirá diseño, entrenamiento y tests. Abrirla antes de tener una base completamente endurecida puede multiplicar los frentes abiertos.

**Recomendación:**
1. Día 117: Promover AppArmor a `enforce` para etcd-server, rag-*, y ml-detector. Verificar pipeline y tests.
2. Día 117: Resolver las tres deudas menores.
3. Día 118: Si todo estable, abrir ADR-026.

**Riesgo si se ignora:** Comenzar ADR-026 con AppArmor aún en `complain` podría ocultar violaciones de seguridad que solo se manifestarían más tarde, cuando sea más costoso depurarlas.

---

### Q4 – `seed_family` como ADR propio o addendum

**Veredicto:** **Crear un ADR-033 específico para documentar el invariante `seed_family` compartido.**  
**Justificación:**
- El hecho de que el reset fallara por asumir seeds independientes demuestra que el diseño no estaba suficientemente explicitado. Un ADR dedicado obliga a pensar en todas las implicaciones (rotación, backup, recuperación ante desastre).
- El ADR-021 (CryptoTransport) habla de derivación de claves pero no establece que todos los componentes deban compartir el mismo seed. Es mejor separar: ADR-021 para el protocolo de transporte, ADR-033 para la gestión del material criptográfico raíz.
- Contenido mínimo del ADR-033:
    - Invariante: un único `seed_family` en `/etc/ml-defender/keys/seed.bin` para toda la instalación.
    - Derivación: HKDF con salt específico por componente.
    - Procedimiento de regeneración (`provision.sh --reset`) que preserva el invariante.
    - Permisos y propiedad del archivo seed (640, root:ml-defender).
    - Implicaciones para la recuperación ante desastre (backup del seed).

**Riesgo si no se hace:** El próximo desarrollador que toque el sistema de claves podría volver a romper el invariante, causando el mismo bug. Un ADR explícito evita que la historia se repita.

---

## Observaciones adicionales (críticas constructivas)

1. **Felicitación por la detección del bug de `seed_family`.** Es un ejemplo excelente de por qué los tests de integración (TEST-RESET-2) son valiosos. Sin ellos, el bug habría llegado a producción.

2. **DEBT-VAGRANTFILE-001 (apparmor-utils faltante)** – Este tipo de omisiones en el aprovisionamiento inicial deberían detectarse con un test de humo en CI. Sugerimos añadir un check en `TEST-PROVISION-1` que verifique que los paquetes necesarios para AppArmor están instalados.

3. **AppArmor perfiles para `provision.sh --reset`** – Han incluido paths de `--reset` en los perfiles. Verificar que también permiten la ejecución de comandos como `cp`, `mv`, `openssl` (si se usa) y `chmod`. Un perfil demasiado restrictivo podría bloquear el propio reset.

4. **Documentación de la secuencia de rotación de claves con cero downtime** (OQ-6 del ADR-024) – Aún no la vemos en `docs/`. Es crítica para operadores. Por favor, incluirla antes de cerrar PHASE 3.

5. **Pruebas de rendimiento de AppArmor** – Aunque en `complain` no hay overhead medible, en `enforce` puede haber una ligera penalización en syscalls. Ejecutar los benchmarks de latencia (pcap replay) con AppArmor en `enforce` para asegurar que no se superan los umbrales (<2x baseline). Si hay degradación, ajustar perfiles (ej. usar `complain` para sniffer).

---

## Veredicto final sobre DAY 116

**PHASE 3 está completa en funcionalidad, pero la transición a `enforce` de AppArmor y la limpieza de deudas menores deben completarse antes de declarar la fase como “lista para producción”.** El Consejo autoriza a proceder según lo recomendado (AppArmor enforce + deudas en DAY 117, luego ADR-026).

*“La verdad por delante, siempre” – y también la excelencia operativa.*

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta del Consejo – 13 Abril 2026*