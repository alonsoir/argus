**CONSEJO DE SABIOS — VEREDICTO DAY 142**

Salud, Alonso. El trabajo de hoy es de una solidez que enorgullece a este Consejo. Un protocolo de aislamiento transaccional, un buffer de captura que ahora es real en ARM64, y la exclusión mutua documentada. Quedan pocos pasos para la integración completa y la demo de FEDER. Atendemos vuestras preguntas con la precisión que merece un sistema que puede aislar una red hospitalaria.

---

### P1 — Criterio de disparo: ¿umbral único o matriz de decisión?

Coincidimos con vuestra postura: **umbral único configurable (`threat_score >= 0.95`) para el MVP FEDER**, con la matriz de decisión pospuesta como mejora post‑FEDER. La justificación es tripartita y va más allá de la simple auditabilidad:

1. **Determinismo clínico**: Un administrador de hospital debe poder predecir exactamente cuándo se activará el aislamiento. Una matriz con ventanas temporales y conteos de eventos introduce una complejidad que puede dar lugar a falsos positivos inesperados o, peor aún, a falsos negativos por una configuración malentendida.

2. **Supervisión humana**: La respuesta a incidentes en entornos sanitarios nunca debe ser completamente automática sin intervención. El umbral alto (0.95) actúa como un disparador de “alta confianza” que inicia el aislamiento, pero debe ir acompañado de un mecanismo de anulación manual (ya previsto con `argus-network-isolate --clear`). Si el administrador quiere una matriz, puede implementarla externamente (por ejemplo, un pequeño daemon que consuma eventos y decida cuándo invocar `argus-network-isolate`). Esto mantiene el núcleo del IRP simple y componible.

3. **Registro completo para auditoría**: Incluso con umbral único, cada evento que supere 0.95 debe registrarse junto con todos los metadatos (tipo de evento, score exacto, timestamp). Así se construye una traza forense que permitiría, en el futuro, entrenar o calibrar una matriz de decisión si se demuestra necesario.

**Veredicto**: Mantened el umbral simple. Abrid `IDEA-IRP-DECISION-MATRIX-001` como habéis propuesto. Para la demo, la contundencia de un solo número transmite confianza.

---

### P2 — `execv()` vs `fork()+execv()` en `firewall-acl-agent`

Vuestra intuición es la correcta: **`fork() + execv()` es la única opción viable para un sistema de seguridad**. El Consejo es unánime.

**Razonamiento definitivo:**
- El `firewall-acl-agent` es un **observador persistente**. Debe seguir recolectando eventos, escribiendo logs forenses y, potencialmente, orquestando otros mecanismos de contención incluso durante el aislamiento.
- Un `execv()` que reemplace al agente lo convierte en un proceso de un solo uso. Si el aislamiento falla o es revertido, no hay agente para registrarlo. Es un punto ciego inaceptable.
- Con `fork()+execv()`, el hijo ejecuta `argus-network-isolate` y termina; el padre puede hacer `waitpid()` para recoger el estado de salida y actuar en consecuencia (por ejemplo, registrar un fallo de aislamiento). Esto mantiene al agente informado y operativo.

**Consideración técnica C++20**: Podéis encapsular la llamada en una pequeña función con `std::system` o `boost::process::child`, pero la gestión manual de `fork()` es más ligera y evita dependencias extra. Recordad bloquear todas las señales en el padre antes del fork y restaurarlas después, y cerrar los descriptores de archivo no necesarios en el hijo antes del exec para cumplir con AppArmor.

**Veredicto**: `fork()+execv()`. El agente debe sobrevivir. Es un invariante arquitectónico.

---

### P3 — AppArmor profile para `argus-network-isolate`

**`enforce` desde el primer despliegue, sin excepciones.** La postura del Consejo es absoluta en este punto.

Un perfil en modo `complain` no es más que un *log* de violaciones. En producción, una violación de AppArmor con el perfil en `enforce` se traduce en una operación bloqueada y, por tanto, en un aislamiento fallido **que es ruidoso y detectable**. Con `complain`, el fallo pasa inadvertido hasta que un atacante explota la falta de restricción.

El axioma BSR (Build Secure by Default) exige que el sistema se despliegue en el estado más restrictivo posible. Si el perfil bloquea una operación legítima, el fallo se verá en desarrollo con el EMECAS y los tests sobre la VM *hardened*. Es mejor arreglar una regla de AppArmor en el laboratorio que explicar por qué un aislamiento no se ejecutó en un hospital.

**Veredicto**: `enforce` desde el día 1. Coherente con la filosofía del proyecto y la seguridad del paciente.

---

### P4 — Rollback con backup persistente del ruleset

La aproximación actual —eliminar únicamente la tabla `argus_isolate` en el rollback, dejando intactas las tablas ajenas— es **correcta y suficiente para el MVP y la demo FEDER**. El Consejo no encuentra riesgo inmediato en este diseño.

**Por qué funciona:**
- El script solo añade una tabla nueva (`argus_isolate`) con reglas de bloqueo/allowlist. No modifica tablas preexistentes del sistema ni las que gestione `iptables` (que pueden ser ignoradas en el snapshot con la expresión `xt match`).
- El rollback simplemente borra su propia tabla con `nft delete table argus_isolate`. Es una operación atómica desde el punto de vista de nftables: la tabla y todas sus reglas desaparecen instantáneamente. Cualquier regla del cliente que estuviera antes sigue en su lugar porque nunca fue tocada.

**Limitación a futuro**: Si una versión posterior de `argus-network-isolate` necesitase modificar la política de enrutamiento o tablas existentes, sería indispensable guardar una copia persistente del estado previo. Para ese escenario, registrad `DEBT-IRP-LAST-KNOWN-GOOD-001` como habéis planeado.

**Veredicto**: El diseño actual es robusto para el alcance declarado. La deuda post‑FEDER es sensata. No complejizéis el MVP.

---

El Consejo observa con satisfacción cómo el protocolo de aislamiento cobra vida y cómo cada decisión se alinea con los principios de seguridad, simplicidad y auditabilidad. Mañana, con la integración del `firewall-acl-agent`, cerraréis el círculo. Continuad con la misma firmeza.

*Firmado, el Consejo de Sabios, en sesión permanente,  
a 5 de Mayo de 2026.*