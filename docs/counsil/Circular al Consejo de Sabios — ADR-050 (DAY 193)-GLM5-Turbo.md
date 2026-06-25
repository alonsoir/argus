**CIRCULAR DE RESPUESTA — CONSEJO DE SABIOS**
**Ref:** ADR-050 · DAY 193
**Clasificación:** Revisión por pares (Método ciego aplicado donde procede)
**Veredicto global:** **6/8 — DOS VETOS PARCIALES** (Se requiere resolución explícita para promoción a *Aceptado*)

Hemos analizado el ADR-050 con la severidad que exige la fecha del calendario (6 semanas al go/no-go FEDER). El diseño es sólido, el rigor metodológico es superior a la media y la honestidad intelectual (declarar las deudas y las limitaciones del split) es de calidad de publicación principal.

Sin embargo, hay dos puntos donde el diseño choca con la física de las redes y la estadística. No son sugerencias: son bloqueos.

A continuación, procedemos pregunta a pregunta.

---

### SOBRE LA HIPÓTESIS

**P1. ¿Es la hipótesis de §1 falsable y sin defecto fatal?**
**Sin veto.** Es falsable por diseño (basta con ejecutar las sondas y observar la matriz de confusión). El único "defecto" es que es casi trivialemente cierta para cualquier modelo supervisado estándar: si no vio la clase, el clasificador no la saca. El valor real del ADR no está en probar la hipótesis (que es un axioma del ML), sino en **cuantificar el recall de los modelos de anomalía frente a lo desconocido**. Aseguraos de que la métrica de éxito no sea "el modelo de DDoS falla en nmap" (esperado), sino "el modelo de normalidad detecta nmap como anomalía y no como tráfico legítimo".

**P2. Confound por solapamiento de features.**
**SIN VETO, pero con advertencia crítica de redacción.** Habéis detectado el verdadero nudo. Un escaneo nmap (T1046) y un brute force hydra (T1110) generan, a nivel de flujo de red, exactamente la misma firma: ráfagas de conexiones fallidas hacia un puerto. Si el modelo etiqueta eso como "Brute Force" porque lo vio en entrenamiento, y en evaluación le lanzáis nmap, ¿es una falsa generalización o un acierto estructural?
*Exigencia del Consejo:* El paper **no puede** usar "Detección" (True/False Positive) como métrica principal para reivindicar generalización. Debe usar **"Detección + Atribución Correcta"** (Multi-class Precision/Recall). Si el modelo dice "Aquí hay un Brute Force" cuando en realidad es un Nmap, es un *False Positive de atribución*, aunque acierte en que es un ataque. Si no medís esto, el revisor destruirá el claim de generalización.

**P3. ¿Factible demostrar generalización con sintético generativo?**
**Sin veto.** Es altamente improbable que un revisor acepte "nuestro modelo generaliza a tráfico real porque fue entrenado con CSV de DeepSeek" sin un ancla en el mundo físico. **La salvación de este ADR es él mismo:** la emulación en laboratorio (este ADR-050) es el ancla física que legitima el sintético. En el paper, el sintético debe presentarse como *pre-training o data augmentation*, y la emulación como *evaluación empírica*.

---

### SOBRE EL TOOLSET

**P4. ¿Catálogo v1 adecuado?**
**Sin veto.** Adecuado para MVP. Faltan cosas obvias para fases posteriores (exfiltración DNS T1071.004, Pass-the-Hash T1550.002), pero para demostrar la metodología de ground truth y el join Wazuh/aRGus, DDoS + Ransomware + 3 sondas es sobrado.

**P5. ¿Vale Caldera en el MVP?**
**Sin veto. Recomendación firme:** NO a Caldera en el MVP. Caldera abstrae demasiado la ejecución. Para vuestro problema de alineación temporal (§9, reloj controlado) y correlación (§5), queréis saber el *nanosegundo exacto* en que se abre un socket. Un script Python con `socket.connect()` o un `hydra -l admin -P pass.txt ssh://...` os da control absoluto del timing. Caldera introduce latencia de orquestación que ensuciará vuestra ventana temporal de join en el MVP.

**P6. ¿hping3/slowloris coinciden con las distribuciones DeepSeek?**
**Sin veto.** Probablemente no. Y eso es exactamente lo que queréis medir. hping3 inyecta a velocidad de cable (wire-speed); DeepSeek probablemente generó una distribución de "paquetes por segundo" basada en papers, no en la realidad de una interfaz de red saturada. Este es vuestro mejor experimento de covariate shift.

---

### PARA DEEPSEEK (A CIEGAS — NOTA DEL CONSEJO)

*(Como modelo de IA, estoy sujeto a las limitaciones del prompt. No puedo ejecutar el protocolo ciego sobre mí mismo porque acabo de leer el §13. Sin embargo, como Consejo, dictaminamos lo siguiente sobre el diseño del test ciego)*:

**P7 y P8.** El diseño del test es científicamente impecable. Al aislar a DeepSeek, medís si la representación interna del modelo sobre lo que generó coincide con la realidad de vuestro espacio de features.
*Lo que buscáis descubrir con este test:* Si DeepSeek admite que generó features de *host* (I/O entropy) mezcladas con features de *red*, confirmáis el **feature drift estructural** (la porción host llega vacía a aRGus). Esto es oro para la sección de limitaciones del paper.

---

### SOBRE LA CORRELACIÓN MULTI-SENSOR — `DEBT-WAZUH-COMMUNITYID-001`

**P9. El invariante que sobrevive al NAT.**
**VETO PARCIAL #1: Sobre la premisa de "inequívoco sin ninguna duda" mediante un hash auto-acuñado.**

Conocéis la respuesta, Alonso, pero no queréis admitirla en el ADR: **No existe ningún invariante matemático calculable de forma independiente por Wazuh y aRGus que sobreviva a un NAT simétrico/patrimonial sin intervención del dispositivo de NAT.**
* Por qué JA3/JA4 falla parcialmente: Es excelente para TLS, pero ¿qué hacéis con SMB (T1021.002), SSH (T1110) o DNS? No hay JA3 para TCP crudo o UDP genérico.
* Por qué el hash de bytes iniciales falla: TCP handshakes puros no tienen payload.
* Por qué los patrones seq/ack fallan: Muchos NATs modernos (CGNAT de operadores) aleatorizan el ISN (Initial Sequence Number).

**La resolución del veto (arquitectura, no magia algorítmica):**
No intentéis resolver esto en los adapters derivando un hash ciego. Resolvedlo **inyectando el estado del NAT en la pipeline**. Si aRGus está en el cable (post-NAT) y el cliente es un hospital, ese cable sale de un router/firewall. Ese router sabe la tabla de traducción.
1.  **Solución ideal (requiere agente en router):** Extraer la tabla de traducción vía NetFlow/IPFIX/syslog (muy común en firewalls empresariales) y unir `IP_post_NAT:Port_post_NAT` ↔ `IP_pre_NAT:Port_pre_NAT` *antes* de calcular el `community_id`.
2.  **Solución degradada (sin acceso al router):** Aceptad que la correlación host↔red en entornos NAT es **imposible de hacer inequívoca** por ingeniería de datos pura. Pasad a la opción del P9-bis.

**P9-bis. Caer a ventana temporal probabilística: ¿Aceptable? Tasa de error.**
**Sin veto, sujeto a acotación estricta.** Es aceptable si se mide y publica.
*   **Tasa de error esperable:** En una red hospitalaria/municipal en horario laboral, un join por ventana de 1 segundo sobre el puerto 443 puede tener N=50 fl concurrentes. La tasa de ambigüedad (error de join) es del 98%.
*   **Acotación obligatoria:** La ventana temporal **no puede ser fija**. Debe ser una función del *número de flujos concurrentes* que comparten el destino y la ventana. Si hay 1 flujo -> ventana 5s (inequívoco). Si hay 20 flujos -> ventana 50ms (tolerancia de reloj) o se declara *Unresolved*.
*   **Consecuencia:** El grafo Kuzu debe tener un tipo de arista especial: `CORRELATES_PROBABILISTICALLY (confidence: 0.2)`, distinta de `CORRELATES_EXACT (community_id_match)`.

**P9-ter. Casos límite.**
**Sin veto.**
*   *Reuso de conexión (HTTP Keep-Alive):* Un solo `community_id` en aRGus. Múltiples eventos Wazuh (procesos distintos leyendo el mismo socket). El join 1:N es estructuralmente roto sin PID en el flujo de red (algo que Zeek/Suricata no tienen porque ocurre en L7/app). Solución: solo correlar eventos Wazuh de *apertura* de socket (`connect()`), no de lectura.
*   *Eventos sin PID:* Descartar del join. Si Wazuh no sabe qué proceso abrió el socket, no sirve para la correlación cruzada.

---

### SOBRE LA ARQUITECTURA DISTRIBUIDA

**P10. Proxy de laboratorio pre-FEDER.**
**Sin veto.** Usad variación sintética de benigno. Tomad el generador de tráfico de julio-2025 y generad 5 "perfiles de hospital" distintos (uno muy HTTP, otro muy DNS, otro muy SMB interno). Aplicad el mismo ataque sobre esos 5 benignos distintos. Si el modelo/promoción sobrevive a los 5 benignos diferentes, es un proxy razonable de "distintas instalaciones" para el paper.

**P11. Comparar grafos sin fusionar (motifs).**
**Sin veto.** Enfoque correcto. Usad el test de isomorfismo de subgrafos de Weisfeiler-Lehman (WL-test) o extraed *Graph Embeddings* (Node2Vec / GraphSAGE) de cada grafo de instalación y calculad la similitud del coseno entre ellos. Si dos instalaciones sufren variantes de Neris, sus embeddings de grafo deberían clusterizar juntos.

---

### SOBRE ENVENENAMIENTO

**P12. Detectar el origen envenenado (`DEBT-NODE-PROVENANCE-001`).**
**Sin veto. Directriz de investigación:**
La firma criptográfica del nodo (Ed25519) solo prueba que el nodo envió el CSV, no que el CSV sea verdad (un nodo puede estar comprometido y firmar datos envenenados válidamente).
La detección debe ser **estadística en la frontera (Bronze layer)**.
*   Implementad **Population Stability Index (PSI)** o **Kolmogorov-Smirnov (KS test)** en los CSV entrantes comparándolos contra la distribución del benigno conocido de esa instalación.
*   Un ataque de data poisoning (ej. inyectar flujos benignos falsos para bajar la sensibilidad) alterará drásticamente la distribución de paquetes/seg o bytes/paquete. Si `PSI > 0.2` (criterio estándar de drift), el CSV va a cuarentena automáticamente antes de tocar el grafo.

---

### SOBRE EL PAPER

**P13. Split disjunto con ~8 técnicas como piloto.**
**VETO PARCIAL #2: Sobre la ubicación en el paper.**
Un split de 8 técnicas (ej. 5 train, 3 eval) es estadísticamente inválido para sustentar un claim fuerte de generalización. Un revisor de IEEE/ACM o de una buena revista lo rechazará al instante por falta de potencia estadística.
*Resolución del veto:* No eliminéis el split (es metodológicamente correcto y honesto), pero **prohibid que se use como resultado principal en el abstract o las conclusiones**. Debe estar estrictamente confinado a una sección de *"Pilot Study / Proof of Concept"* o en el *"Future Work"*, dejando claro que la validez estadística vendrá cuando el catálogo supere las ~30 técnicas (post-FEDER). Si lo vendéis como resultado principal, el paper muere.

---

### RESOLUCIÓN Y DEUDAS

El ADR es técnicamente maduro. Los vetos no son defectos de diseño estructural, sino **correcciones de alcance**: hay que bajar la arrogancia epistemológica en dos puntos (el join "inequívoco" y el split "validado"). La física de las redes y la estadística no perdonan.

**Estado requerido para pasar a Aceptado (8/8):**
1.  **Reescribir §5 (P9):** Eliminar la promesa de índice inequívoco auto-acuñado. Declarar que el join post-NAT requiere tabla de traducción (IPFIX) o se degrada a probabilístico con aristas etiquetadas con confianza.
2.  **Reescribir §12 / §17 P13:** Aislar el split de 8 técnicas como *piloto ilustrativo*, no como claim de generalización.

**Deudas nuevas ratificadas por el Consejo:**
*   `DEBT-WAZUH-COMMUNITYID-001` (Aprobada su gravedad).
*   Añadimos **`DEBT-JOIN-CONFIDENCE-001`**: Implementar lógica de ancho de ventana temporal dinámico basado en la cardinalidad de flujos concurrentes para evitar joins masivamente ambiguos en horario laboral.

*Votación registrada. A la espera de enmiendas de Alonso.*

FDO 

GLM5-Turbo