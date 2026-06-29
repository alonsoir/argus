## Respuesta del Consejo de Sabios

**Acta DAY 110 – Consulta sobre Q1-111**

El Consejo ha revisado el estado técnico y la pregunta opcional sobre el orden de implementación entre PHASE 2d (ml-detector) y PHASE 2e (rag-security con `g_plugin_loader` global para signal handler).

### Análisis

1. **Dependencias**
  - PHASE 2d (ml-detector) sigue el mismo patrón que el sniffer: recibe el `plugin_loader` por inyección de dependencias (vía `set_plugin_loader()` o similar). No requiere variable global.
  - PHASE 2e requiere acceso al `plugin_loader` desde un **signal handler** (contexto donde no se dispone de un puntero explícito al loader). La única solución portable y segura es una variable global (o singleton con inicialización estática).

2. **Riesgos de introducir la global antes de 2d**
  - Añadir `g_plugin_loader` ahora obligaría a modificar todas las fases anteriores (sniffer, firewall, rag-ingester) para que también usen esa global, o bien mantener dos mecanismos (inyección + global). Esto aumenta la superficie de posibles errores de inicialización y testing.
  - El código actual está probado y funcionando con inyección de dependencias. Cambiarlo antes de 2d añade riesgo innecesario y retrasa la entrega de ml-detector.

3. **Riesgos de introducir la global después de 2d**
  - Ninguno significativo, siempre que se diseñe la global como un **singleton thread-safe** (p.ej. `PluginLoader::instance()`) y se documente que solo debe usarse en contextos donde la inyección no es posible (signal handlers, callbacks C puros).
  - PHASE 2d no depende de la global, por lo que no se verá afectada. La integración posterior es limpia y no requiere reescribir código ya entregado.

4. **Consideraciones adicionales**
  - **Signal handlers** imponen restricciones severas: solo pueden llamar a funciones async-signal-safe. `g_plugin_loader` debería exponer un método específico para signal handlers que sea seguro (por ejemplo, leer una flag atómica o escribir en un pipe self-pipe). El Consejo recomienda documentar este requisito en ADR-029 cuando se aborde PHASE 2e.
  - **Pruebas unitarias**: la global complica el aislamiento de tests. Se sugiere que `PluginLoader::instance()` sea reseteable en tiempo de compilación (macro `TEST_MODE`) o que se use un patrón de dependency injection también para signal handlers (p.ej. registrar el loader mediante una función `set_global_loader_for_signals()` solo en producción).

### Veredicto del Consejo

**El Consejo respalda la recomendación del autor: ejecutar PHASE 2d (ml-detector) primero, manteniendo el patrón actual sin variable global. PHASE 2e se abordará después, introduciendo `g_plugin_loader` como un singleton bien encapsulado, con las salvaguardas necesarias para signal handlers y tests.**

**Votación**: Unanimidad (5/5).  
**Riesgo identificado**: Ninguno que bloquee. Se levanta una recomendación no bloqueante: documentar en `ADR-029` el diseño del singleton y las restricciones async-signal-safe antes de implementar PHASE 2e.

---

**Nota final**: El Consejo felicita al equipo por la rápida recuperación del incidente de ficheros vacíos y por mantener el pipeline 6/6 funcionando. Procedan con PHASE 2d según lo planeado. No se requiere nueva consulta hasta completar TEST-INTEG-4d o si surge algún impedimento técnico no previsto.