Recibo la v3.1 del ADR-052. La auto-revisión ha sido quirúrgica: las cuatro correcciones (C1–C4) eliminan las pequeñas imprecisiones que v3 arrastraba sin alterar el consenso ni las decisiones de árbitro. Analizo cada cambio y confirmo la fidelidad pedida.

### Correcciones v3.1

**C1 – Eliminación de `deployment_epoch` del `node_id`**  
Era un acierto. La v3 había eliminado la clave efímera pero añadía un entero mutable; eso introducía un footgun análogo, aunque menor. Al dejar `node_id` como string declarado puro (legible, firmado en el inventario) se gana simplicidad y se respeta la continuidad de rol que pide §0. La nota de que un cambio deliberado de identidad requiere una operación de inventario revisada es sensata.  
**No rompe ningún consenso**; la separación identidad de corpus / identidad de autenticación ya estaba ratificada 8/8.

**C2 – Señal TLS acotada a destinos gestionados con cert‑expectation store**  
La v3 presentaba el mismatch TLS como una señal ligera, cuando realmente requiere infraestructura previa (el *esperado*). El Consejo temía exactamente ese rabbit‑hole. v3.1 lo reconoce, acota la señal a destinos internos/gestionados con expectativa declarada y difiere el resto a una deuda (`DEBT-CERT-EXPECTATION-STORE-001`).  
Esto **no revierte el arbitraje** (las señales TCP/TLS siguen dentro de ADR-052), pero añade la honestidad que faltaba. La anulación de árbitro queda, por tanto, mejor delimitada y justificada.

**C3 – Separación de confianza‑por‑corroboración y peso‑de‑de‑duplicación**  
La v3 llamaba “score IPW” a una cantidad que sube con testigos, cuando el verdadero peso IPW (de‑duplicación) baja con testigos. v3.1 lo distingue con claridad:
- `corroboration_confidence` (feature, va al pipeline ML).
- peso de de‑duplicación (para el sampler, se deriva de `witness_count` pero con signo opuesto).  
  Ambas se dejan como derivadas, mientras que el modelo de propensión real es propiedad de ADR-040. Esto corrige un error de categoría y refuerza la separación de responsabilidades.  
  **Totalmente alineado con la resolución Q4** y con la filosofía de “primitivas crudas” del Consejo.

**C4 – Estructura explícita de la hash‑chain del WAL**  
La v3 mencionaba hash‑chain sin detalle. v3.1 especifica `prev_hash = H(entrada_{i-1})` y verificación periódica de la cadena. Esto cierra el hueco sobre cómo se detecta manipulación del WAL (independientemente de la divergencia con Neo4j).  
**Aporta concreción sin cambiar la decisión.** La interfaz WAL y el soporte etcd/ADR-048 ya estaban decididos.

### Fidelidad al consenso de la 2ª pasada

Las votaciones 8/8 (Q1, Q5) y las resoluciones del resto de preguntas (Q2, Q3, Q4, Q6) permanecen intactas. Los apartados modificados no alteran los puntos que recibieron consenso; al contrario, los refuerzan.

**Las dos anulaciones del árbitro están explícitas y claras:**
- §3.1.1 (función de hash = la de libsodium congelada, idéntica en todo el pipeline).
- §3.11 (señales TCP/TLS dentro de ADR-052, contra la mayoría del Consejo).  
  La v3.1 añade el matiz de honestidad sobre el cert‑expectation store, pero **mantiene la incorporación de las señales TCP/TLS** bajo el mismo epígrafe, con alcance delimitado. El texto es transparente: “ANULACIÓN DE ÁRBITRO” y “Decisión explícita de Alonso”.

Por tanto, respondo directamente a la pregunta de confirmación de fidelidad:

> **v3.1 refleja fielmente el consenso de la 2ª pasada y deja claras las dos anulaciones de árbitro.** La función de hash está anclada a libsodium y la sección de anomalías TCP/TLS lleva la marca de arbitraje sin ambigüedad.

No surge ninguna necesidad de tercera deliberación. La auto-revisión ha sido precisamente el tipo de pulido que cabía esperar antes de la ratificación final.

### Ratificación final

**Ratifico ADR-052 v3.1.**  
El diseño de identidad de flujo es robusto, estable ante rebuilds de EMECAS++ y reproducible offline. La defensa contra el data‑plane hostil cubre desde L2 hasta L7, con limitaciones documentadas con honestidad. Las primitivas de confianza y el etiquetado con no‑repudio (WAL con hash‑chain) garantizan la integridad del corpus. La v3.1 desbloquea DEBT‑NEO4J‑FLOW‑KEY‑001 sin deudas ocultas. Puede procederse a la implementación.

— Alonso (vía DeepSeek), Consejo de Sabios.

FDO

DEEPSEEK