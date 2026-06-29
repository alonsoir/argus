## DeepSeek — Retroalimentación DAY 101

Excelente trabajo. La corrección del parser del PluginLoader es un ejemplo perfecto de por qué los tests de integración con JSON real son necesarios. El patrón canónico `extract_enabled_objects` vs `extract_enabled_list` queda ahora documentado en el código y evita futuros errores similares. El hecho de que el smoke test de sniffer pasara de warnings a un inicio limpio valida la corrección.

Voy a las preguntas.

---

### Q1 — Orden de integración plugin-loader

**Recomendación:** Confirmo el orden propuesto: **sniffer ✅ → ml-detector ✅ → firewall-acl-agent → rag-ingester**.

**Razonamiento:**  
El firewall es el componente que ejecuta la respuesta activa. Integrarlo antes que rag-ingester permite validar el bucle completo: detección en ml-detector (con plugins) → decisión → bloqueo real. rag-ingester es importante para logging y observabilidad, pero no bloquea la cadena de valor de seguridad. Tener el bucle completo funcionando con plugins (incluyendo el hello plugin) antes de expandir a rag-ingester reduce el riesgo de sorpresas en la integración final.

**Posible mejora:** Al integrar en firewall-acl-agent, considera si el plugin loader debe estar activo por defecto o no. El patrón `#ifdef` con `active:false` en JSON es adecuado para mantener la opcionalidad.

---

### Q2 — PAPER-ADR022: ubicación del caso pedagógico

**Recomendación:** **§5.5 (Cryptographic Transport) con una referencia cruzada desde §6 (Consejo de Sabios / TDH).**

**Razonamiento:**
- El error es intrínsecamente técnico (diseño de contextos HKDF). Documentarlo en la sección de criptografía (5.5) es natural, porque ahí se describe el mecanismo y se explica por qué se eligió `contexts.hpp`.
- Sin embargo, el proceso de descubrimiento (TDH) y la validación mediante TEST-INTEG-1 son un ejemplo del método del Consejo. Por tanto, una nota al pie o un pequeño recuadro en §6 que refiera a §5.5 conecta ambas contribuciones sin duplicar contenido.

**Estructura sugerida:**
- En §5.5: añadir un párrafo final: “*A subtle design error discovered during integration testing (asymmetric HKDF contexts) is documented in the reproducibility artifacts; see also the discussion of Test-Driven Hardening in §6.*”
- En §6: una breve mención de que TDH permitió capturar este error a través de un test de integración específico (TEST-INTEG-1).

De esta forma, el caso pedagógico refuerza ambas secciones sin alargar excesivamente.

---

### Q3 — Plugin invocations=0: ¿test unitario sintético?

**Recomendación:** Sí, conviene añadir un test unitario específico que invoque `invoke_all()` con un `PacketContext` sintético.

**Razonamiento:**
- El smoke test actual solo verifica carga, inicialización y cierre del plugin, pero no que el pipeline de invocación funcione correctamente.
- Un test unitario en `test_plugin_loader.cpp` que cree un `PacketContext` mínimo (con datos dummy) y llame a `invoke_all()` validaría que el plugin no crash, que devuelve `PluginResult` coherente, y que el contador de invocaciones se incrementa.
- Esto es especialmente importante para plugins que modifiquen datos de contexto (ej. añadiendo features). Aunque el hello plugin no lo haga, el test sienta las bases para futuros plugins.

**Implementación sugerida:**
- Usar un `PacketContext` estático con valores predecibles.
- Verificar que `invoke_all()` devuelve `PLUGIN_CONTINUE` (o el valor esperado).
- Comprobar que los contadores (invocations) se incrementan correctamente.

No sustituye al smoke test E2E (que verifica carga desde JSON y el flujo real), pero lo complementa cubriendo la lógica interna de invocación.

---

### Comentario adicional sobre el endorser

El contacto con el profesor Caro Lindo es una muy buena opción por la relación previa y la vinculación institucional. Si acepta, el proceso de arXiv será más rápido. Mientras tanto, el estado actual del preprint (v6) ya es sólido para publicación. No demores la sumisión esperando a todos los endorsers; uno solo es suficiente.

---

### Cierre

DAY 101 ha consolidado el patrón de plugin loader en dos componentes críticos, corregido un bug sutil del parser, y avanzado en la estrategia de publicación. Con los tests de integración verdes y el roadmap claro, el proyecto está en excelente posición para los siguientes pasos (firewall, rag-ingester, bare-metal).

Enhorabuena por mantener el ritmo en los 101 días.

— DeepSeek, miembro del Consejo de Sabios