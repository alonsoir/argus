**Consejo de Sabios — Acta DAY 110 (Respuesta Oficial)**

Buen cierre de día, Alonso.  
El incidente de los ficheros vacíos es molesto pero se resolvió correctamente gracias a los `.backup`. La reconstrucción limpia de PHASE 2b y la verificación de que todo compila y pasa los tests demuestran madurez en el proceso. Los backups salvavidas y la lección aprendida fortalecen la disciplina del proyecto.

### Valoración general del Consejo

- Todas las decisiones del DAY 109 se implementaron fielmente (incluyendo las que tenían mayoría cualificada).
- El pipeline se mantiene en **6/6 RUNNING** tras la restauración → excelente señal de resiliencia.
- PHASE 2c (sniffer con payload real) ya está en código y listo para su gate `TEST-INTEG-4c`.
- El paper avanza en paralelo con argumentos sólidos en §4.

El proyecto sigue en una trayectoria limpia y productiva.

### Respuesta a la única pregunta abierta (Q1-111)

**Recomendación del Consejo: Haz PHASE 2d (ml-detector) primero, luego PHASE 2e (rag-security).**

**Argumento de una línea**: ml-detector sigue el mismo patrón sencillo que sniffer y firewall-acl-agent (invocación directa en el datapath sin handlers globales ni signal handling), por lo que cerrar primero 2d reduce riesgo, permite reutilizar el mismo código de integración y da confianza rápida antes de abordar el caso especial de `g_plugin_loader` + signal handler en rag-security.

**Razones adicionales**:
- Evita contaminar el flujo de ml-detector con cuestiones de globals o signal safety (que son más delicadas en C++).
- El patrón “set_plugin_loader() + member + invoke_all()” ya está probado en tres componentes → aplícalo directamente en ml-detector.
- Una vez 2d esté verde, el esfuerzo en 2e será más predecible y aislado.

**No identificamos riesgos no vistos** en este orden. Es la secuencia más natural y de menor riesgo.

### Observaciones menores del Consejo (no bloqueantes)

1. **D8-pre en plugin_loader.cpp**  
   El chequeo `READONLY + payload != nullptr → std::terminate()` es correcto y fuerte. Asegúrate de que el comentario en `plugin_api.h` explique claramente los dos modos y las consecuencias de violar el contrato.

2. **TEST-INTEG-4c (sniffer)**  
   Dado que ahora tienes payload real, el test debe verificar al menos:
  - Que el plugin recibe payload no-nulo y longitud correcta.
  - Que un plugin que intente modificar el payload (D8-light) active terminate.
  - Que `result_code != 0` descarte el paquete correctamente (sin llegar a ml-detector).

3. **Signal handler en rag-security (futuro 2e)**  
   Cuando llegues allí, recuerda que los signal handlers tienen restricciones severas (async-signal-safe). Si usas `g_plugin_loader`, asegúrate de que la invocación sea mínima y no llame a código no-safe (nada de spdlog, malloc, etc. dentro del handler). Posiblemente un flag volátil + procesamiento diferido en el loop principal.

### Estado actualizado PHASE 2 (según Consejo)

| PHASE | Componente       | Estado          | Gate               | Prioridad |
|-------|------------------|-----------------|--------------------|---------|
| 2a    | firewall-acl-agent | ✅ Cerrada     | TEST-INTEG-4a     | Hecho   |
| 2b    | rag-ingester     | ✅ Cerrada     | TEST-INTEG-4b     | Hecho   |
| 2c    | sniffer          | ✅ Código listo | TEST-INTEG-4c     | Día 111 |
| 2d    | ml-detector      | ⏳              | TEST-INTEG-4d     | Día 111 |
| 2e    | rag-security     | ⏳              | TEST-INTEG-4e     | Después de 2d |

**Recomendación para DAY 111**:  
Enfócate en completar e integrar PHASE 2d (ml-detector). Es el más sencillo de los pendientes y te dará momentum antes de entrar en el terreno más delicado de rag-security.

No hace falta convocar Consejo formal mañana salvo que surja un problema inesperado en el datapath de ml-detector o en el manejo de plugins con payload real.

El Consejo felicita el progreso sólido a pesar del incidente de ficheros vacíos. La capacidad de recuperación rápida es una buena señal de que el proceso de desarrollo se está endureciendo.

¿Quieres que preparemos el esqueleto de `TEST-INTEG-4d` o que revisemos el patrón de integración propuesto para ml-detector antes de que lo implementes? Estamos disponibles si lo necesitas.

¡Sigue así! DAY 111 pinta productivo.