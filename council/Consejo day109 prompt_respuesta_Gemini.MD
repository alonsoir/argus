REVISOR: Gemini (Google) / Perfil: Sistemas Distribuidos & cs.CR
FECHA: 6 de abril de 2026
ESTADO: **PHASE 2b CERRADA — MODO AUDITORÍA PHASE 2c**

Alonso, el **DAY 109** consolida la arquitectura de "Confianza Gradual". Has resuelto el problema de la rigidez del `std::terminate()` con un *escape hatch* elegante para desarrollo, y la integración en el `rag-ingester` sigue la filosofía de "mínimo privilegio necesario".

Aquí tienes el dictamen del Consejo sobre tus preguntas estratégicas:

---

### 🏛️ Resolución del Consejo — DAY 109

#### Q1 — D8-light READ-ONLY: ¿Inferencia o Flag Explícito?
**Veredicto: FLAG EXPLÍCITO (`ctx.mode`) REQUERIDO.**
* **Razonamiento:** En seguridad, la **ambigüedad es el espacio donde viven los exploits**. Inferir el modo de operación basándose en si un puntero es `nullptr` es una práctica frágil. Si en el futuro un bug en el core del sistema pone el `payload` a `nullptr` por error, el plugin entraría en modo READ-ONLY silenciosamente en lugar de disparar una violación de seguridad.
* **Acción:** Modifica `plugin_api.h` para incluir un `enum PluginMode { MODE_FULL = 0, MODE_READONLY = 1 }`. El `plugin-loader` debe validar que si `mode == MODE_READONLY`, entonces `payload` **DEBE** ser `nullptr`. Esto hace que la intención del programador sea explícita y auditable.

#### Q2 — PHASE 2c (Sniffer): ¿Payload Real o READ-ONLY?
**Veredicto: PAYLOAD REAL (READ-ONLY ACCESS).**
* **Análisis:** Un plugin en el `sniffer` que no puede ver el contenido del paquete es casi inútil para la detección de anomalías profundas (L7). Sin embargo, el contrato de **inmutabilidad** debe ser absoluto.
* **Recomendación:** El `sniffer` debe pasar el `payload` real, pero el `plugin-loader` debe aplicar el **D8-v2 (CRC32)** rigurosamente.
    * El plugin **ve** el paquete para decidir si lo descarta (`result_code != 0`), pero **no puede tocarlo**.
    * Si el plugin necesita anonimizar datos, eso no se hace en el plugin de filtrado, sino en una etapa posterior del pipeline. El plugin solo dice: "Este paquete es sospechoso, descártalo".



#### Q3 — Justificación de "Raw TCP" en el Paper (§4)
**Veredicto: SÓLIDA, pero añade "Determinismo de Latencia" y "Superficie de Ataque".**
* **Sugerencia:** Para una audiencia académica, el argumento de "recursos limitados" es bueno, pero el de **"Reducción de la Superficie de Ataque"** es mejor.
* **Argumento extra:** Al eliminar brokers (Kafka) y stacks pesados (HTTP/TLS overhead), reduces las dependencias de runtime (CVEs potenciales en librerías externas) y garantizas una latencia determinista en el procesamiento de ráfagas de red. Es una arquitectura de **"Sistemas de Tiempo Real Críticos"** aplicada a la ciberseguridad.

#### Q4 — ADR-028 (RAG Ingestion Trust Model)
**Veredicto: APROBAR ANTES DE PHASE 2c.**
* **Razonamiento:** Aunque la Fase 2c sea de lectura, el `sniffer` es la entrada principal de datos al RAG. Establecer el modelo de confianza *ahora* evita que diseñes el `sniffer` con supuestos que luego el ADR-028 contradiga.
* **Decisión:** El ADR-028 debe definir la política de **"Atribución de Origen"**: ¿Cómo sabe el RAG que el mensaje que recibe del sniffer no ha sido inyectado por un plugin malicioso? Define esto antes de abrir el grifo de datos del sniffer.

---

### 🛡️ Auditoría de Seguridad: FIX-A y FIX-B

1.  **FIX-A (Escape Hatch):** La implementación es segura porque el `getenv` es una acción consciente del operador. Sugerencia: En el log de `std::cerr`, añade el PID del proceso para facilitar la trazabilidad en entornos multi-componente.
2.  **TEST-INTEG-4b (Variant B):** Es excelente que el test intente un `const_cast`. Esto demuestra que el `plugin-loader` no confía en la buena voluntad del desarrollador del plugin, sino en la validación post-invocación.

---

### 📝 Actualización del Paper (Draft v12)

La inclusión de **§4 Integration Philosophy** es un movimiento estratégico brillante. Eleva el proyecto de ser una "herramienta útil" a ser una **"propuesta arquitectónica"**. La distinción sobre el Out-of-Scope (USB) protege al proyecto de críticas sobre seguridad física, centrando el valor en la visibilidad de red, que es donde **aRGus** es imbatible.



### 🏁 Estado del Proyecto
* **PHASE 2b:** CERRADA ✅
* **Próximo Paso:** Definir el `enum PluginMode` (Q1) y redactar el **ADR-028** antes de tocar el código del `sniffer` (PHASE 2c).

Alonso, el pipeline es cada día más una roca. Mañana nos enfocaremos en que esa roca sea capaz de mirar dentro de los paquetes sin romperse.

**¿Empezamos con el borrador del ADR-028?** 🏛️🛡️🚀