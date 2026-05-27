**CONSEJO DE SABIOS — VEREDICTO DAY 143**

El Consejo ha examinado con el máximo rigor cada línea del parte. El día ha sido ejemplar en disciplina y hallazgos, y solo un necio alabaría sin señalar los puntos donde aún se puede mejorar. Vamos a ello.

---

### **P1 — Procesos zombis: `fork()+execv()` sin `wait()`**

La decisión de no bloquear al padre es correcta, pero la omisión de una **recogida periódica de hijos** es una fuga de recursos que en un sistema de seguridad no puede tolerarse. Cada aislamiento genera una entrada en la tabla de procesos que no se libera hasta que el proceso muere. En un ataque persistente de ransomware con múltiples detecciones, el número de zombis se acumularía, pudiendo agotar los PIDs y colapsar el sistema.

**Exigimos una solución inmediata, antes del merge a `main`**. Proponemos un mecanismo simple y robusto en el bucle del `BatchProcessor`:

```cpp
// En el worker thread, después de procesar un batch o cada N segundos:
while (true) {
    pid_t pid = waitpid(-1, nullptr, WNOHANG);
    if (pid <= 0) break;
    // opcional: registrar que el hijo terminó
}
```

Esto no bloquea, no necesita señales asíncronas y garantiza que ningún zombi sobreviva más de un ciclo de trabajo. La deuda quedará saldada con un commit de dos líneas.

**Veredicto**: El aislamiento debe ser impecable también en la gestión de recursos del sistema operativo. Implementad la recogida de zombis con `WNOHANG`. Es un cambio pequeño pero indispensable. Registrad la tarea como bloqueante para el merge.

---

### **P2 — Tolerancia IEEE 754: ¿eliminar la causa raíz?**

El parche con `1e-6` es *ingenierilmente correcto* pero *conceptualmente sucio*. La raíz del problema es una discrepancia de tipos que no debería existir en una ruta de decisión crítica para la seguridad.

**La solución óptima es unificar los tipos, no ajustar la comparación.**  
El `IsolateConfig` debe almacenar el umbral como `float` y la lectura del JSON debe realizarse con `std::stof`. La confianza que produce el modelo (`float`) se compara entonces con exactamente el mismo tipo. Para el valor `0.95`, la comparación directa es bit a bit idéntica si ambos se han convertido desde la misma representación.

Rechazamos tajantemente el uso de tolerancias como práctica permanente. Una tolerancia puede enmascarar futuros bugs donde el score del modelo empiece a devolver valores ligeramente por encima del umbral por defectos de cuantización, disparando aislamientos no deseados. Los sistemas distribuidos seguros **no negocian con épsilon**.

**Veredicto**: Cambiad el tipo del umbral a `float` en `IsolateConfig` y utilizad `std::stof` para la deserialización. La comparación podrá ser directa (`>=`). Si por algún motivo se desea conservar `double`, entonces la confianza debe ser también `double` en todo el pipeline. Lo inaceptable es la mezcla.

---

### **P3 — `auto_isolate: true` por defecto en hospitales**

Aquí el Consejo debe hablar con la máxima claridad y severidad.

**El valor por defecto debe ser `false`.**  
Un ventilador mecánico, un monitor de constantes o una bomba de infusión pueden depender de la conectividad de red. Un falso positivo, por muy alta que sea la confianza, desencadenaría un apagón de comunicaciones que ningún administrador hospitalario consentiría sin haber sido advertido y haber dado su consentimiento explícito.

El principio *“instalar y funcionar sin leer el manual”* es admirable para una herramienta de escritorio, pero **temerario para un dispositivo de seguridad clínica**. La seguridad en entornos médicos se rige por el principio *primum non nocere*: lo primero es no hacer daño. Un aislamiento automático no requerido puede hacer más daño que el ataque que pretende detener.

El *onboarding* de aRGus en un hospital debe incluir un paso de configuración obligatorio donde el responsable clínico habilite explícitamente el aislamiento automático, firme (digitalmente) la aceptación del riesgo y defina una lista blanca de activos críticos. El sistema, mientras tanto, debe registrar y alertar, **pero nunca aislar sin permiso**.

**Veredicto**: Cambiad `auto_isolate` a `false` por defecto, y añadid un campo `admin_acknowledged: true` que deba ser establecido manualmente para que el aislamiento automático se active. Mantened la posibilidad de arranque rápido, pero nunca a costa de la seguridad del paciente.

---

### **P4 — AppArmor profile: ¿demasiado permisivo con `/tmp`?**

El uso de `/tmp/argus-*.nft` es una puerta entreabierta que debemos cerrar. Aunque el glob reduce la superficie, `/tmp` es un directorio de escritura universal y predecible. Un atacante que comprometa el proceso podría intentar una condición de carrera o la inyección de un archivo de reglas nftables malicioso.

**Recomendamos migrar a un directorio dedicado y protegido**, por ejemplo `/var/lib/argus/irp/`, con permisos `750` y propiedad `argus:argus`. El perfil AppArmor debe reflejar exactamente esta ubicación, sin comodines que puedan ampliar el acceso.

Esto refuerza el modelo de privilegio mínimo y elimina un *smell* de seguridad que, aunque no explotable hoy, es una deuda que ningún sistema acreditado para entornos hospitalarios debería arrastrar.

**Veredicto**: Sustituid `/tmp/argus-*` por una ruta fija y privada. Actualizad el perfil AppArmor en consecuencia. Es una mejora de una hora que será apreciada en cualquier auditoría FEDER o sanitaria.

---

### **P5 — Criterio de disparo: ¿dos señales o una tercera dimensión?**

Las dos condiciones actuales son un progreso notable y **defendibles para la demostración de FEDER**. Sin embargo, para un despliegue real en un hospital, la prudencia exige una tercera condición: **la comprobación de que el interfaz a aislar no pertenece a un activo médico crítico**.

Proponemos un diseño simple y extensible:

```json
"critical_assets_cidr": ["192.168.10.0/24", "10.0.1.0/24"],
"critical_assets_mac": ["00:1A:2B:3C:4D:5E"]
```

Antes de ejecutar el aislamiento, `should_auto_isolate()` verificará que ni la IP de origen ni la de destino están en las subredes o MACs de exclusión. Esto puede implementarse en una fase posterior, pero **debe registrarse como requisito obligatorio para cualquier certificación de seguridad clínica**.

**Veredicto**: Para la demo, las dos señales bastan. Para producción sanitaria, la lista blanca de activos es irrenunciable. Registrad `DEBT-IRP-MULTI-SIGNAL-001` con alta prioridad y especificad esta tercera condición como parte de su cierre. Mientras tanto, asegurad que la documentación de usuario indique claramente esta limitación.

---

### **Sobre el plan del DAY 144**

La secuencia **Opción A (merge) → Opción B (benchmarking)** es la correcta. Antes del merge, verificad:
- La recogida de zombis (P1).
- El cambio de tipo del umbral (P2).
- La compilación con `PROFILE=production` como gate ODR.
- El cambio de `auto_isolate` a `false` por defecto (P3), aunque esto puede ser un commit separado en `main` después del merge si no retrasa.

La contribución científica del *paper* exige el benchmark comparativo. Adelante con él tras el merge.

---

El Consejo observa la madurez creciente del proyecto y no duda de que estas correcciones se incorporarán con la misma solvencia que habéis demostrado. Hoy habéis protegido pacientes virtuales; mañana, siguiendo estas directrices, protegeréis personas reales.

*Firmado, el Consejo de Sabios,  
en sesión permanente a 6 de Mayo de 2026.*