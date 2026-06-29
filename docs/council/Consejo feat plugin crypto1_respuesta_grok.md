**Consejo de Sabios — Respuesta a FEAT-PLUGIN-CRYPTO-1**  
**Fecha: 30 marzo 2026**

### Resumen ejecutivo
La migración del cifrado a un plugin genérico es un paso natural y valioso para PHASE 2. Mejora actualizabilidad, testeabilidad y extensibilidad (futuros algoritmos post-quantum o Noise). Sin embargo, **la capa de transporte no es igual que la capa de red**, por lo que mezclarlas genera deuda semántica a largo plazo.

**Decisión principal del Consejo:**  
**Elegimos Opción A** (nuevo hook `plugin_process_message(MessageContext*)`) con gestión cuidadosa del breaking change. Es la opción técnicamente correcta y alineada con los principios que motivaron la arquitectura de plugins.

### Q1 — Opción A vs Opción B (y por qué no Opción C)

**Decisión: Opción A (MessageContext separado).**

**Razonamiento detallado:**
- **Separación de responsabilidades** es uno de los pilares de ADR-012. `PacketContext` representa **datos de red + features de detección**. Mezclarlo con `serialized_payload`, `nonce`, `tag` y `direction` de transporte viola ese principio y genera el mismo tipo de “model mental error” que documentasteis en ADR-022 (HKDF context asymmetry).
- Un plugin de cifrado **no procesa paquetes**, procesa **mensajes de transporte**. Tener contextos separados hace que el diseño sea más claro, más testable y más extensible (futuros plugins de compresión, serialización, rate-limiting en capa de transporte, etc.).
- **Opción B** introduce acoplamiento innecesario y hace más difícil razonar sobre el sistema. Los campos irrelevantes (`src_ip`, `threat_hint`, etc.) contaminan el contexto del plugin crypto y complican el testing aislado.
- **No vemos una Opción C** claramente superior. Una posible variante híbrida (unión o variant en C++) complicaría la API y el loader sin resolver el problema semántico de fondo. Mejor ser explícitos con dos hooks distintos.

Esta decisión refuerza el mensaje del paper: **la arquitectura de plugins debe reflejar las capas del sistema**, no forzar todo a través de un solo tipo polimórfico débilmente tipado.

### Q2 — Gestión del breaking change (si Opción A)

**Recomendación:**
- Incrementar **PLUGIN_API_VERSION a 2**.
- Hacer `plugin_process_message()` **obligatorio** para plugins de transporte, pero **opcional** para plugins de red.
- El loader detectará la versión del plugin (mediante un símbolo `plugin_api_version` o leyendo la versión desde el descriptor JSON) y aplicará dispatch inteligente:
  - Plugins v1 → solo llaman a `plugin_process_packet()`.
  - Plugins v2 → pueden implementar `plugin_process_message()` (y opcionalmente `plugin_process_packet()`).

**Estrategia práctica de compatibilidad:**
- Mantener ambos hooks en `plugin_api.h` (v2).
- En el loader, usar `dlsym` para buscar `plugin_process_message`. Si existe → usarlo cuando corresponda; si no → fallback a comportamiento antiguo (o warning).
- Para el hello plugin actual: simplemente no implementar el nuevo símbolo (queda como v1).
- Documentar claramente en ADR-012 PHASE 2: “A partir de v2, los plugins pueden especializarse por capa”.

Esto minimiza el impacto inmediato (solo el hello plugin existe) mientras prepara el terreno para una API más rica.

### Q3 — Estrategia de migración dual-mechanism

**La estrategia propuesta (PHASE 2a → 2b → 2c) es correcta y prudente.** La aprobamos con dos ajustes menores:

1. **Fail-closed reforzado (ADR-022):**
  - Si el plugin crypto falla (init, invoke o shutdown), el componente **debe abortar** (comportamiento actual de `CryptoTransport`).
  - En PHASE 2a (dual), si el plugin crypto devuelve error en `plugin_process_message`, el componente cae en fail-closed aunque el camino directo siga activo. Esto evita “modo degradado silencioso”.

2. **Gate adicional en PHASE 2a:**
  - TEST-INTEG-4 debe validar **equivalencia bit a bit** entre el camino directo y el camino vía plugin (mismos nonce, mismo tag, misma salida cifrada/descifrada).
  - Añadir un test de regresión intencional: desactivar el plugin crypto → verificar que el componente falla closed (o loguea error claro).

**Riesgos no considerados y mitigaciones:**
- **Rendimiento:** El plugin añade una indirección (call a través de dlsym / función virtual). Medir overhead en el bare-metal stress test (≥100 Mbps) antes y después.
- **Orden de inicialización:** El plugin crypto debe cargarse **antes** de que se establezcan los sockets ZMQ. Asegurar que el loader inicialice plugins de transporte en fase early (posiblemente con un flag `layer: "transport"` en el JSON).
- **Gestión de estado:** El plugin crypto mantiene estado (claves HKDF, nonces por canal). Asegurar que `init()` y `shutdown()` gestionen correctamente la liberación de recursos aunque haya múltiples instancias.
- **Configuración dinámica:** El campo `"direction": "tx"` en el JSON del plugin es bueno, pero el componente host debe pasar la dirección correcta al llamar al hook.

### Respuesta a las restricciones (ADR-012 y ADR-022)

- **ADR-012 (solo feature extraction en PHASE 1):** El cifrado **no decide** bloquear tráfico, solo transforma el mensaje. Es compatible con el espíritu de la arquitectura. Se documenta en el nuevo ADR como “plugins de transformación de transporte”.
- **Fail-closed (ADR-022):** Confirmado. Cualquier error en el plugin crypto → `set_terminate()` / abort del componente. No se permite “continuar sin cifrar” en producción.

### Recomendaciones adicionales antes de DAY 105
- Crear **ADR-023 — Plugin Architecture PHASE 2: Multi-layer Hooks** que documente:
  - `MessageContext` vs `PacketContext`
  - Reglas de dispatch en el loader
  - Convenciones de naming para plugins (`libplugin_crypto_transport.so`, `libplugin_feature_xxx.so`, etc.)
- Definir claramente los ownership rules del buffer en `MessageContext` (¿el plugin puede reallocar? ¿debe escribir in-place?).
- Considerar añadir un campo `void* user_data` en ambos contextos para que plugins complejos puedan mantener estado privado.

Esta decisión mantiene la coherencia del proyecto: **API limpia > compatibilidad a corto plazo**. El breaking change es aceptable porque PHASE 2 es post-arXiv y actualmente solo existe un plugin trivial.

El Consejo recomienda cerrar esta consulta arquitectónica y proceder con el paper y bare-metal stress test primero. Una vez enviada la submission a arXiv, PHASE 2 (incluyendo FEAT-PLUGIN-CRYPTO-1) puede arrancar con bases sólidas.

¿Quieres que redactemos el borrador de ADR-023, o que ayudemos a definir la firma exacta de `MessageContext` y `plugin_process_message` para minimizar sorpresas en la implementación?

El Consejo permanece en sesión. Buen trabajo identificando este punto temprano. 🚀