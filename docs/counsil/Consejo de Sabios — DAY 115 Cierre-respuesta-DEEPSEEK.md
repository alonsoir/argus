## Respuesta del Consejo de Sabios – DAY 115 (12 Abril 2026)

El Consejo ha revisado el trabajo del día. Se valora muy positivamente el avance en PHASE 3, especialmente la implementación de `check-plugins` con modo producción, la eliminación del plugin hello de los JSONs (y el hallazgo del bug de `active:true`), y el CI gate TEST-PROVISION-1. A continuación, las respuestas a las cuatro preguntas, seguidas de observaciones constructivas adicionales.

---

### Q1 – AppArmor: ¿modo complain primero o enforce directamente?

**Veredicto:** **Complain primero, con un plan de promoción a enforce en 3 pasos.**

**Justificación:**
- Aunque el pipeline está bien caracterizado, los perfiles AppArmor pueden tener efectos no anticipados sobre el acceso a archivos, sockets, y capacidades. En entorno Vagrant (desarrollo) es mejor detectar denegaciones en modo `complain` antes de bloquear la ejecución.
- El flujo propuesto (complain → verificar pipeline OK → enforce) es correcto, pero añadir un paso intermedio: **ejecutar los tests de integración completos con logs de AppArmor** para asegurar que no hay violaciones no observadas.

**Riesgo si se ignora:** Ir directamente a enforce puede causar fallos no evidentes (ej. denegación de escritura en `/tmp`, o de creación de sockets de dominio Unix) que detengan el pipeline sin mensajes claros, alargando el diagnóstico.

**Nota sobre diferencias ARM64 vs x86:**
- AppArmor en Debian 13 (ARM64) es funcionalmente idéntico a x86. Las diferencias están en los paths de dispositivos (ej. `/dev/ttyAMA0` vs `/dev/ttyS0`). El Consejo recomienda **parametrizar los perfiles** con variables (ej. `@{serial_device}`) y probar en una Raspberry Pi antes de la promoción a enforce.

---

### Q2 – DEBT-ADR025-D11: `provision.sh --reset` scope y firma automática

**Veredicto:** **`--reset` debe regenerar claves, pero NO debe re‑firmar plugins automáticamente. La re‑firma debe ser manual y explícita, incluso en producción.**

**Justificación:**
- La prohibición de firma automática en producción (Consejo DAY 114) es una decisión de seguridad sólida. `--reset` es una operación de emergencia que debe ser ejecutada por un operador humano. Forzar una re‑firma automática crearía el riesgo de que, si el operador no está atento, el pipeline arranque con plugins sin firmar (o firmados con clave antigua) después del reset.
- El flujo correcto:
   1. `provision.sh --reset` → regenera seed_family, keypairs Ed25519, keypair de firma de plugins.
   2. Muestra un mensaje claro: *“Claves regeneradas. Ahora debe re‑firmar todos los plugins con: `provision.sh sign --all`”*.
   3. El operador ejecuta `provision.sh sign --all` (o `make sign-plugins`) manualmente.
- En entornos de desarrollo (donde se permite firma automática), se podría añadir `--auto-sign` como flag opcional, pero no por defecto.

**Riesgo si se ignora:** Si `--reset` re‑firma automáticamente, un atacante con acceso a la máquina podría regenerar claves y firmar plugins maliciosos en un solo paso, eliminando la oportunidad de intervención humana.

---

### Q3 – Orden AppArmor vs DEBT-ADR025-D11 (deadline 18 Apr)

**Veredicto:** **AppArmor primero, pero integrando `--reset` en las pruebas de los perfiles.**

**Justificación:**
- El deadline del 18 de abril es interno (no vinculante). AppArmor es un requisito previo para producción real, mientras que `--reset` es una operación de recuperación. Es más seguro tener AppArmor activo (en modo complain) antes de ejecutar `--reset`, porque los perfiles pueden bloquear accidentalmente el acceso a los archivos de claves o a los binarios de firmado.
- Propuesta de integración:
   1. Completar perfiles AppArmor en modo `complain` para los 6 componentes.
   2. Ejecutar `provision.sh --reset` en un entorno de pruebas con AppArmor activo, verificar qué denegaciones aparecen.
   3. Ajustar los perfiles para permitir las operaciones de `--reset` (ej. acceso a `/etc/ml-defender/keys/`, ejecución de `openssl`, `ykman` si se usa).
   4. Promover los perfiles a `enforce` después de validar que `--reset` funciona sin violaciones.

**Riesgo si se ignora:** Hacer `--reset` antes de AppArmor puede crear la falsa sensación de que todo funciona, pero al activar AppArmor después, el pipeline podría fallar inesperadamente por denegaciones no anticipadas.

---

### Q4 – TEST-PROVISION-1: ¿falta algún check?

**Veredicto:** **Sí, faltan dos checks importantes: integridad de binarios y consistencia de JSONs con plugins reales.**

**Justificación:**
- **Check 6 – Integridad de binarios:** Verificar que cada binario en `/usr/bin/ml-defender-*` no ha sido modificado desde la última firma (o desde la compilación). Propuesta: almacenar un hash SHA-256 de cada binario en un archivo firmado (ej. `/etc/ml-defender/binaries.sha256`). En cada `pipeline-start`, recalcular y comparar. Esto detecta manipulaciones post‑compilación (rootkits, modificaciones manuales).
- **Check 7 – Consistencia de JSONs:** Asegurar que cada plugin listado en los JSONs de producción existe en `/usr/lib/ml-defender/plugins/` y tiene un `.sig` válido. Actualmente solo se verifica la ausencia de `libplugin_hello`, pero no se valida que todos los plugins referenciados estén realmente presentes y firmados.
- **Check opcional – Permisos de archivos:** Verificar que los archivos de claves tienen permisos `600` y los binarios `755`. Esto podría ser parte de un check de hardening.

**Riesgo si se ignora:** Un binario modificado (por un atacante o por error del operador) podría ejecutarse sin que el sistema lo detecte, invalidando la cadena de confianza. Un JSON mal configurado (apuntando a un plugin inexistente) causaría que el componente no arrancase con un error crítico.

**Recomendación adicional:** Añadir estos checks al CI gate y también como paso previo en `pipeline-start` (además de `test-provision-1`).

---

## Observaciones constructivas adicionales (fuera de las preguntas)

1. **Hallazgo crítico sobre `active:true` en componentes:**  
   El hecho de que 4 componentes tuvieran `active:true` para `libplugin_hello` en producción es un **bug de seguridad importante**. El Consejo felicita al equipo por detectarlo y corregirlo. Recomendamos **auditar todos los JSONs** periódicamente (cada release) para evitar reintroducciones. Añadir una regla en el CI que rechace cualquier PR que añada un plugin de desarrollo a configs de producción.

2. **DEBT-RAG-BUILD-001 (rag/ no sigue convención build-debug/build-release):**  
   Este tipo de incoherencias puede causar problemas en el futuro. Sugerimos priorizarlo como P2 (no P3) porque afecta a la reproducibilidad del pipeline. Podría integrarse en `TEST-PROVISION-1` como un check adicional (simlinks correctos para todos los componentes).

3. **Documentación del flujo de rotación de claves (OQ-6):**  
   La secuencia de 5 pasos para rotación con cero downtime debería estar documentada en `docs/operations.md` o en un anexo de ADR-024. Es información valiosa para operadores hospitalarios.

4. **Próximo paso después de AppArmor:**  
   Una vez los perfiles estén en `enforce`, el Consejo recomienda **ejecutar una batería de pruebas de penetración básicas** (intentar escribir en rutas prohibidas, cargar plugins no firmados, etc.) para validar que AppArmor realmente bloquea lo que debe. Esto podría ser parte de un nuevo test (`TEST-APPARMOR-1`).

---

## Resumen de decisiones del Consejo

| Pregunta | Veredicto | Acción concreta |
|----------|-----------|------------------|
| Q1 (AppArmor) | Complain primero | Implementar perfiles en modo complain, validar con tests, luego enforce. |
| Q2 (--reset) | No auto-firma | `--reset` regenera claves; operador debe ejecutar `sign --all` manualmente. |
| Q3 (Orden) | AppArmor primero | Completar perfiles en complain, probar `--reset` con ellos, luego enforce. |
| Q4 (TEST-PROVISION-1) | Añadir checks 6 y 7 | Verificar integridad de binarios y consistencia JSONs con plugins existentes. |

*La verdad por delante, siempre – y también la mejora continua.*

El Consejo autoriza a continuar con PHASE 3 según lo planeado, incorporando las recomendaciones anteriores. Se espera el cierre de los dos ítems restantes (AppArmor profiles y `--reset`) en los próximos días.

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta del Consejo – 12 Abril 2026*