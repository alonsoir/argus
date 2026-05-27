## DeepSeek — Recomendación FEAT-PLUGIN-CRYPTO-1

Excelente análisis. Has planteado con claridad el conflicto entre pureza arquitectónica (Opción A) y pragmatismo de migración (Opción B). Mi voto es claro, pero con matices.

---

### Q1 — Opción A vs Opción B vs Opción C

**Recomendación: Opción A con un puente de compatibilidad (no-breaking) para PHASE 2a.**

**Razonamiento:**
- **Opción B** (ampliar `PacketContext`) introduce acoplamiento que contradice la razón de ser del plugin-loader: separación de responsabilidades. Mezclar capa de red con capa de transporte en un mismo contexto hará que el plugin crypto tenga dependencias absurdas (src_ip, dst_port) que no usa, y dificultará el testing aislado. Además, sentaría un precedente peligroso para futuros plugins.
- **Opción A** es arquitectónicamente correcta: cada capa tiene su contexto, los plugins de red y de transporte son conceptualmente diferentes. El breaking change es explícito y se puede gestionar con una migración gradual.

**Opción C — Híbrido:** Mantener `CryptoTransport` en el core (no plugin) para PHASE 2, pero diseñar la API de plugins de transporte desde ahora para que cuando se decida migrar, el core ya tenga el soporte. Esto retrasaría la migración pero evitaría el breaking change. No lo recomiendo porque ya tienes el mecanismo de plugins funcionando; extenderlo ahora es natural.

---

### Q2 — Gestión del breaking change

**Recomendación: Símbolo opcional con `PLUGIN_API_VERSION` sin incrementar (PHASE 2a), luego bump a 2 en PHASE 2b.**

**Estrategia concreta:**

1. **PHASE 2a (dual-mechanism):**
  - Añadir `plugin_process_message` como **símbolo opcional** en la API. El loader, al cargar un plugin, comprueba con `dlsym` si existe. Si existe, lo usa para mensajes (y si no existe, el componente host sigue usando `CryptoTransport` interno).
  - `PLUGIN_API_VERSION` se mantiene en 1. Los plugins existentes (`hello`) no implementan `plugin_process_message` y siguen funcionando (como plugins de red).
  - En esta fase, el plugin crypto se implementa con el nuevo símbolo, pero el core sigue teniendo el `CryptoTransport` como respaldo (el dual-mechanism de tu propuesta). El gate TEST-INTEG-4 valida que ambos producen el mismo resultado.

2. **PHASE 2b (cambio a solo plugin):**
  - Una vez validado, se desactiva `CryptoTransport` interno. El loader se convierte en el único responsable de cifrar/descifrar. Se incrementa `PLUGIN_API_VERSION` a 2 para reflejar que ahora todos los componentes *requieren* que el plugin crypto esté presente y exponga `plugin_process_message`.
  - Los plugins existentes (que no tienen ese símbolo) seguirán funcionando en sus componentes respectivos (sniffer, ml-detector, etc.) porque se cargan con el mismo loader, pero los componentes que necesiten cifrado (todos) fallarán si el plugin crypto no está cargado.

3. **PHASE 2c:**
  - Eliminar código de `CryptoTransport` del core.

Este enfoque evita un big-bang, mantiene la compatibilidad durante la transición, y al final la API queda limpia y tipada.

---

### Q3 — Estrategia de migración dual-mechanism

**Recomendación: La estrategia es correcta, pero con dos advertencias:**

1. **TEST-INTEG-4 debe ser exhaustivo:** no solo probar equivalencia de resultado, sino también que el comportamiento en errores (MAC failure, nonce overflow, etc.) sea idéntico. Incluir casos de corrupción de datos.

2. **Riesgo de divergencia mantenida:** Durante PHASE 2a, el core y el plugin coexisten. Hay riesgo de que se acumulen cambios en `CryptoTransport` que no se reflejen en el plugin, o viceversa. Para mitigarlo, en PHASE 2a el core debe ser read-only; solo se hacen cambios en el plugin, y el core se mantiene congelado. Así la validación es unidireccional: plugin → core.

3. **Fall-closed:** El componente debe abortar si el plugin crypto no está cargado o falla en PHASE 2b. En PHASE 2a, mientras el core actúa como respaldo, puede tolerar la ausencia del plugin (pero debe loguear una advertencia). Documentar claramente en ADR-022 que el modo degradado solo es temporal.

---

### Consideración adicional sobre ADR-012

La restricción de ADR-012 (plugins solo feature extraction, nunca bloqueo) **no aplica** al plugin de cifrado. El cifrado no decide bloquear; transforma el mensaje. Además, el plugin crypto es un componente de infraestructura que opera en la capa de transporte, no en la de detección. Por tanto, puede tener un tratamiento especial y ser obligatorio en producción. Documentarlo en ADR-022 como excepción justificada.

---

### Resumen de decisiones

| Pregunta | Decisión |
|----------|----------|
| Q1 | Opción A (MessageContext), con migración gradual. |
| Q2 | Símbolo opcional en PHASE 2a, luego bump a API v2 en PHASE 2b. |
| Q3 | Estrategia dual-mechanism correcta; añadir gate de congelación del core durante la fase dual. |

Con estas directrices, el diseño de FEAT-PLUGIN-CRYPTO-1 puede avanzar después de arXiv sin romper la estabilidad actual.

— DeepSeek, miembro del Consejo de Sabios