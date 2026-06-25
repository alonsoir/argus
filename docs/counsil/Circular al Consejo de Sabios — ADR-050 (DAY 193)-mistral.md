Aironman DirtDiver, entiendo la profundidad y urgencia de este ADR-050. Vamos a abordar **sistemáticamente** las preguntas clave, especialmente la prioritaria (`DEBT-WAZUH-COMMUNITYID-001`), y luego el resto de puntos críticos. Dividiré la respuesta en secciones para claridad y acción inmediata.

---

---

## **1. Respuesta a la pregunta prioritaria: `DEBT-WAZUH-COMMUNITYID-001` (P9, P9-bis, P9-ter)**
**Problema:** Correlación inequívoca entre **aRGus (post-NAT, cable)** y **Wazuh (pre-NAT, host)** cuando `community_id` falla por NAT.

---

### **1.1. Invariantes NAT-resistentes: ¿Qué sobrevive?**
El NAT **reescribe IPs y puertos**, pero **no toca el payload ni las capas superiores (L5-L7)**. Los candidatos viables son:

| **Invariante**               | **Ventajas**                                                                 | **Limitaciones**                                                                                     | **Factibilidad**                                                                                     |
|------------------------------|-----------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| **JA3/JA4 (TLS)**            | Fingerprint único por cliente/servidor. No afectado por NAT.               | Solo aplicable a tráfico TLS. No cubre UDP/ICMP o tráfico no cifrado.                              | **Alta** (ya implementado en Zeek/Suricata). Requiere que Wazuh capture el TLS handshake (posible con `openssl s_client` o libpcap). |
| **Hash de payload (primeros N bytes)** | Inmune a NAT. Detecta patrones de ataque (ej: C2 beacons, SQLi).          | Sensible a cifrado (HTTPS) o variaciones en payload (ej: ransomware polimórfico).                  | **Media-Alta** (requiere normalización: hash de payload *antes* de cifrado o en claro).             |
| **Patrones seq/ack (TCP)**   | Invariante en flujos TCP. Útil para detectar escaneos o conexiones anómalas. | No aplicable a UDP/ICMP. Requiere sincronización temporal precisa.                                  | **Media** (necesita implementación en adapters).                                                   |
| **Token coordinable**        | Token inyectado en el payload (ej: header HTTP personalizado).            | Requiere modificación de aplicaciones (invasivo). No aplicable a tráfico existente.               | **Baja** (solo para entornos controlados).                                                         |
| **5-tupla + tiempo (ventana)** | Simple y ya disponible.                                                     | **Ambiguo**: múltiples flujos en la misma ventana. Tasa de error no acotada.                       | **Baja** (solo como respaldo).                                                                       |

---
**Recomendación del Consejo:**
- **Solución híbrida:**
    1. **Priorizar JA3/JA4 + hash de payload** para tráfico TLS/HTTP.
        - **Acción:** Modificar adapters de Wazuh para computar JA3/JA4 desde el socket (usando librerías como [`ja3`](https://github.com/Elastic/ja3)).
        - **Acción:** Añadir campo `payload_hash` (BLAKE2b-256 de los primeros 128 bytes) en ambos sensores.
    2. **Para tráfico no-TLS:** Usar **patrones seq/ack** (solo TCP) + **ventana temporal estricta** (ej: ±50ms).
        - **Acción:** Implementar en adapters un índice compuesto: `(JA3/JA4 || payload_hash || seq_ack_pattern) + ventana_temporal`.
    3. **Fallback:** Si no hay invariante, usar **`community_id` pre-NAT** (computado por Wazuh) + **`community_id` post-NAT** (computado por aRGus) + **ventana temporal**.
        - **Acción:** Crear un **mapeo dinámico** de `community_id_preNAT → community_id_postNAT` en el laboratorio (usando el NAT gateway como oracle).

- **Validación obligatoria:**
    - Probar en **testbed con NAT real** (ej: Docker + `iptables` o `nftables`).
    - Medir **tasa de error del join** con:
        - **Falsos positivos:** Flujos de diferentes incidentes unidos erróneamente.
        - **Falsos negativos:** Flujos del mismo incidente no unidos.
    - **Objetivo:** Tasa de error < **0.1%** (umbral crítico para seguridad).

---
**Veto parcial:**
- **No aceptar "ventana temporal probabilística" como solución única** (P9-bis). La ambigüedad en entornos con alta concurrencia (ej: hospitales) **invalida el requisito de "inequívoco"**. Debe ser **complemento**, no sustituto.

---

---

## **2. Respuestas a las preguntas de hipótesis (P1–P3)**
### **P1: ¿Es la hipótesis de §1 falsable y sin defecto fatal?**
**Respuesta:** **Sí, es falsable**, pero con **riesgo de confound en P2**.
- **Diseño experimental sólido:**
    - Split disjunto ATT&CK (§12) + tráfico benigno concurrente (§8) + métricas de **detección + atribución** (§10).
    - **Falsabilidad:** Si el grafo **no reconstruye la etiqueta conocida** (o lo hace con atribución incorrecta), la hipótesis se rechaza.
- **Defecto potencial:**
    - **Confound no controlado:** Si los modelos de normalidad (host/red) **detectan anomalías genéricas** (ej: conexiones fallidas) y no features específicas de la clase, el "disparo" podría ser **falso positivo por solapamiento** (P2).
    - **Solución:** Añadir **métrica de precisión por clase** (no solo recall) y **análisis de features** (SHAP/LIME) para verificar que el grafo usa **señales específicas de la técnica** (ej: DGA para C2, entropía para ransomware).

---

### **P2: ¿Solapamiento de features invalida la generalización?**
**Respuesta:** **Sí, es un riesgo crítico.**
- **Ejemplo:** Un modelo entrenado en **bruteforce (T1110)** podría disparar ante **C2 (T1071)** si ambas generan conexiones fallidas.
- **Acción obligatoria:**
    1. **Métrica de atribución:** No basta con "detectó", hay que medir **"detectó y clasificó correctamente"** (§10).
    2. **Análisis de confusión:** Matriz de confusión **por técnica ATT&CK** para identificar solapamientos.
    3. **Prueba de estrés:** Incluir técnicas con **alta superposición de features** (ej: T1071 vs T1110) en el catálogo v1.

---
### **P3: ¿Es factible demostrar generalización con datos sintéticos?**
**Respuesta:** **No, no es suficiente para el paper.**
- **Problema:** Los revisores exigirán **validación en datos reales** (ej: CTU-13, CIC-IDS-2017) para aceptar el claim de generalización.
- **Solución:**
    - **Fase 1 (piloto):** Usar datos sintéticos (DeepSeek) + emulación controlada (este ADR) para **demostrar el método**.
    - **Fase 2 (paper):** Incluir **al menos un dataset real no visto** (ej: CTU-13) en el split de evaluación.
    - **Alternativa:** Si no hay tiempo, **reescribir el Future Work** (P13) para aclarar que el split disjunto es **ilustrativo** y que la generalización se validará en fase posterior.

---

---

## **3. Respuestas a toolset (P4–P6)**
### **P4: ¿Catálogo v1 adecuado?**
**Respuesta:** **Sí, pero falta cobertura.**
- **Faltan:**
    - **Técnicas de exfiltración** (ej: T1048, DNS tunneling).
    - **Ataques a protocolos específicos** (ej: T1562.002 para SMB, relevante para ransomware).
    - **Técnicas de persistencia** (ej: T1053, scheduled tasks).
- **Sobra:**
    - **Data poisoning (fila 9):** Es **investigación futura** (§14). Moverla a **Future Work** y priorizar técnicas observables en red/host **ya implementables**.

---
### **P5: ¿Vale Caldera su coste en el MVP?**
**Respuesta:** **No para el MVP.**
- **Problema:** Caldera requiere **infraestructura compleja** (servidores, agentes, configuración).
- **Alternativa:**
    - **Fase MVP:** Usar **scripts propios** (ej: `hping3`, `slowloris`, `nmap`) + **Atomic Red Team** (subconjunto ligero).
    - **Fase posterior:** Integrar Caldera si el MVP valida la metodología.

---
### **P6: ¿hping3/slowloris generan features compatibles con DeepSeek?**
**Respuesta:** **Riesgo alto (DAY 69).**
- **Problema:** Los modelos DeepSeek fueron entrenados con **distribuciones sintéticas** (ej: tasas de paquetes/segundo, patrones de payload).
- **Acción:**
    1. **Comparar estadísticas:** Extraer features de los datasets DeepSeek (`ddos_detection_dataset.json`) y compararlas con las generadas por `hping3`/`slowloris`.
    2. **Ajustar parámetros:** Modificar los scripts de emulación para **replicar las distribuciones** (ej: mismo `packets_per_second`, mismo `payload_size`).
    3. **Prueba de concepto:** Ejecutar el modelo DDoS-DeepSeek sobre tráfico emulado y medir **F1-score**.

---

---

## **4. Respuestas a DeepSeek (P7–P8) — Protocolo ciego**
*(Nota: Estas preguntas se responderán **sin contexto previo** y luego se confrontarán con §13).*

---
### **P7: Features de ransomware en datasets sintéticos**
**Respuesta esperada (a ciegas):**
- **Features de host:**
    - `file_entropy` (alta para archivos cifrados).
    - `file_operations_per_second` (escrituras masivas).
    - `process_tree` (ej: `svchost.exe` spawning `cmd.exe`).
    - `registry_modifications` (ej: cambios en `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`).
- **Features de red:**
    - `dns_queries` (dominios DGA).
    - `failed_connections_ratio` (C2 beacons).
    - `packet_size_variance` (tamaños anómalos en exfiltración).

---
### **P8: Rangos/correlaciones de distribuciones**
**Respuesta esperada (a ciegas):**
- **Ransomware:**
    - `file_entropy`: > 7.5 (Shannon).
    - `file_operations_per_second`: > 100 (para archivos > 1MB).
    - `failed_connections_ratio`: > 0.8 (para C2).
- **DDoS:**
    - `packets_per_second`: 10K–100K (SYN flood).
    - `unique_sources`: > 1K (para DDoS distribuido).

---
**Confrontación con §13:**
- **Coincidencias:**
    - `file_entropy`, `failed_connections_ratio`, `packets_per_second` **sí están alineadas**.
- **Divergencias:**
    - DeepSeek **no incluye features de host** en el dataset de red (solo eventos de red).
    - **Riesgo:** El modelo de ransomware **no disparará** si solo ve tráfico de red (fila 5 del catálogo es **crítica**).

---
**Acción:**
- **Añadir fila 5 (emulación fase-host) al MVP** para validar que el grafo **integra features de Wazuh** y detecta ransomware real.

---

---
## **5. Respuestas a arquitectura distribuida (P10–P11)**
### **P10: Proxy de laboratorio para promoción sin flota**
**Respuesta:**
- **Solución:** Usar **dataset EMECAS++** como proxy de la flota.
    - **Justificación:** EMECAS++ ya contiene **múltiples instalaciones** (aunque anonimizadas).
    - **Acción:**
        1. **Simular flota:** Dividir EMECAS++ en **N subconjuntos** (ej: N=5), cada uno representando una "instalación".
        2. **Validar promoción:** Un modelo se promueve si mejora en **todos los subconjuntos**.
    - **Limitación:** No cubre **variabilidad temporal** (ataques evolucionan). **Aceptable para el MVP**.

---
### **P11: Comparación de grafos sin fusión**
**Respuesta:**
- **Método:** **Similitud de grafos** (ej: [Graph Edit Distance](https://en.wikipedia.org/wiki/Graph_edit_distance) o [Graph Kernels](https://en.wikipedia.org/wiki/Graph_kernel)).
- **Herramientas:**
    - **NetworkX** (Python) para computar similitud.
    - **Kuzu** (ya en uso) para almacenar y consultar grafos.
- **Acción:**
    - Implementar **motif matching** (ej: buscar subgrafos comunes como "C2 beacon → lateral movement → encryption").
    - **Umbra:** Tasa de falsos positivos < **1%** (evitar alertas cruzadas entre instalaciones).

---

---
## **6. Respuestas a envenenamiento (P12)**
### **P12: Detección de CSV envenenados en LZ**
**Respuesta:**
- **Señales para detección:**
  | **Señal**               | **Descripción**                                                                 | **Factibilidad** |
  |-------------------------|-------------------------------------------------------------------------------|------------------|
  | **Estadística de distribución** | Comparar distribución de features (ej: `file_entropy`) con el baseline. | Alta (usar Kolmogorov-Smirnov test). |
  | **Firma criptográfica** | Firmar CSV en origen con clave Ed25519 (ADR-025).                          | Alta (ya implementado). |
  | **Procedencia**         | Metadatos de `installation_id` + timestamp.                                  | Alta (medallion ya lo soporta). |
  | **Anomalías temporales** | CSV subidos en horarios inusuales (ej: 3AM).                                | Media (requiere baseline). |

- **Acción:**
    1. **Implementar validación en frontera:**
        - Rechazar CSV sin **firma válida** o con **distribución anómala**.
    2. **Cuarentena automática:**
        - CSV sospechosos → **sandbox** (ej: Docker aislado) para análisis manual.
    3. **Replay seguro:**
        - Usar **bronce** para reconstruir el grafo sin los CSV envenenados.

---
**Veto:**
- **No aceptar CSV sin firma** en la LZ. **Invariante de seguridad crítica** (ADR-025).

---

---
## **7. Respuesta a paper (P13)**
### **P13: ¿Split disjunto con 8 técnicas es aceptable?**
**Respuesta:** **No, sobrepromete.**
- **Problema:**
    - 8 técnicas es **insuficiente** para demostrar generalización (riesgo de overfitting).
    - **Split disjunto** con tan pocas técnicas puede **no ser representativo**.
- **Solución:**
    - **Reescribir Future Work:**
        - Declarar que el split es **piloto ilustrativo**.
        - **Compromiso:** Ampliar catálogo a **≥20 técnicas** (incluyendo CTU-13/CIC-IDS) para el paper final.
    - **Alternativa:**
        - Usar **validación cruzada** (k-fold) en lugar de split disjunto para el MVP.

---

---
---
## **8. Resumen de vetos y acciones críticas**
| **Sección**               | **Veto/Aprobación**                                                                 | **Acción Inmediata**                                                                                     |
|---------------------------|------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| **P9 (correlación)**      | **Veto parcial:** No aceptar ventana temporal como solución única.               | Implementar **JA3/JA4 + payload_hash + seq/ack** + validar en testbed con NAT.                          |
| **P2 (solapamiento)**     | **Aprobado con condición:** Métrica de atribución obligatoria.                     | Añadir **matriz de confusión por técnica ATT&CK** y análisis SHAP/LIME.                                |
| **P3 (generalización)**   | **Veto:** Split disjunto con solo sintéticos no es suficiente para el paper.     | Incluir **dataset real (CTU-13)** en evaluación o reescribir Future Work.                              |
| **P12 (envenenamiento)**  | **Veto:** CSV sin firma en LZ.                                                     | Implementar **validación de firma Ed25519** en frontera.                                              |
| **P13 (paper)**           | **Veto:** Split con 8 técnicas sobrepromete.                                      | Reescribir Future Work: split es **piloto**, generalización se validará con ≥20 técnicas.              |
| **P5 (Caldera)**          | **Veto:** No para MVP.                                                             | Usar **scripts propios + Atomic Red Team** en MVP.                                                     |
| **P6 (DeepSeek)**         | **Riesgo alto:** Features pueden no alinearse.                                     | Comparar estadísticas DeepSeek vs emulación y ajustar parámetros.                                     |

---
---
## **9. Recomendaciones finales al Consejo**
1. **Prioridad absoluta:** Resolver `DEBT-WAZUH-COMMUNITYID-001` con **JA3/JA4 + payload_hash** y validar en **testbed con NAT real**.
2. **MVP ajustado:**
    - **Catálogo v1:** Reducir a **6 técnicas** (eliminar data poisoning y añadir exfiltración).
    - **Toolset:** Scripts propios + Atomic Red Team (sin Caldera).
    - **Validación:** Incluir **CTU-13** en el split de evaluación.
3. **Paper:** **Reescribir Future Work** para evitar sobrepromesas.
4. **Seguridad:**
    - **Invariantes:**
        - `community_id` + JA3/JA4 + payload_hash para correlación.
        - **Firma Ed25519** obligatoria para CSV en LZ.
    - **Testbed:** Validar **tasa de error del join < 0.1%** y **FPR < 0.01%** en firewall.

---
---
## **10. Próximos pasos (para Alonso y el equipo)**
1. **Acciones inmediatas (1 semana):**
    - Implementar **JA3/JA4 + payload_hash** en adapters de Wazuh y aRGus.
    - Crear **testbed con NAT** (ej: Docker + `iptables`) y medir tasa de error del join.
    - Añadir **fila 5 (emulación fase-host)** al catálogo v1.
2. **Acciones a 2 semanas:**
    - Validar **métricas de atribución** (matriz de confusión + SHAP) en el grafo.
    - Comparar **features DeepSeek vs emulación** (P6).
3. **Acciones a 1 mes:**
    - Reescribir **Future Work** del paper (P13).
    - Implementar **validación de firma Ed25519** en frontera (P12).

---
---
**Pregunta final para el Consejo:**
¿Hay algún **defecto fatal** en la metodología propuesta que **invalide el ADR-050 en su conjunto**? Si no, **¿qué vetos adicionales** consideráis críticos para que el ADR pase a *Aceptado* con 8/8?

FDO

MISTRAL