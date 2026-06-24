# Revisión del Consejo — ADR-050 (DAY 193)

**Revisor:** Consejo de Sabios  
**Fecha:** 2026-06-23  
**Veredicto preliminar:** **NO ACEPTADO** — defectos críticos en §5 (correlación multi-sensor) y §13 (covariate shift no cuantificado). Veto sobre P9, P9-bis, P9-ter, P1, P2, P3.

---

## P1 · ¿Hipótesis falsable sin defecto fatal?

**VETO PARCIAL.** La hipótesis es falsable en principio, pero tiene un **defecto metodológico no fatal yet, pero grave**:

- **Falsabilidad:** sí, porque defines métricas concretas (recall, FPR, atribución correcta) sobre tráfico emulado vs. tráfico real.
- **Defecto:** no cuantificas el **gap de distribución** entre el tráfico emulado en laboratorio y el tráfico real de producción. Si el laboratorio no reproduce las condiciones de red reales (latencia, MTU, fragmentación, retransmisiones TCP, NAT, proxies), la "verdad-terreno" es válida **solo para el laboratorio**, no para producción. Esto es **covariate shift en el ground truth**, no solo en los modelos.

**Condición para levantar veto:** debes medir explícitamente el gap de distribución entre tráfico emulado y tráfico real (mínimo 1 semana de tráfico real benigno + ataque en producción, comparado con emulación). Si el gap es >15% en features clave, la hipótesis se cae.

---

## P2 · Confound de solapamiento de features

**VETO.** La pregunta está mal planteada. No basta medir "detección + atribución correcta" — debes medir **matriz de confusión completa por clase**, no solo accuracy.

- **Problema real:** las features de red (ratio de paquetes, tamaños, tiempos) son **invariantes de comportamiento**, no de intención. Un C2 beacon y un bruteforce SSH pueden tener firmas estadísticas similares (conexiones cortas, repetidas, a puertos específicos).
- **Métrica requerida:** no solo "¿disparó y atribuyó correcto?", sino **F1-score por clase** + **tasa de falsos positivos intra-clase** (cuántas veces confunde DDoS con benigno, o ransomware con bruteforce).
- **Umbral mínimo:** F1 ≥ 0.85 por clase en eval set disjunto. Si alguna clase cae <0.70, el modelo no generaliza, solo memoriza.

**Condición para levantar veto:** redefinir §10 para incluir matriz de confusión completa + F1 por clase + umbral mínimo.

---

## P3 · Factibilidad de demostrar generalización

**VETO PARCIAL.** Depende de qué signifique "generalización":

- **Generalización intra-laboratorio:** factible, pero trivial. Si entrenas y evalúas en el mismo laboratorio con las mismas herramientas, el revisor aceptará.
- **Generalización cross-entorno (lo que el paper reclama):** **no factible sin dataset externo real**. El revisor exigirá al menos **un dataset público no visto** (CTU-13, CIC-IDS2017, UNSW-NB15) con ground truth real, no emulado.

**Condición para levantar veto:** el paper debe declarar explícitamente que la generalización es **intra-laboratorio**, o incluir evaluación en ≥1 dataset público externo. Si no, el claim de "generalización" es sobrepromesa.

---

## P4 · Catálogo v1 adecuado

**ACEPTADO con observaciones.**

- **Falta:** tráfico benigno **criptográfico** (HTTPS, DNS-over-HTTPS, SSH). Sin esto, no puedes medir si el modelo distingue C2 TLS de navegación legítima TLS.
- **Sobra:** fila 9 (data poisoning) es **meta-ataque**, no ataque de red. Muévela a §14 como técnica de validación, no al catálogo de ataques.
- **Observación:** nmap agresivo (fila 6) genera features distintas a nmap sigiloso (-sS -T2). Especifica el perfil de escaneo.

**Condición:** añadir benigno TLS/DoH al catálogo, mover fila 9 a §14.

---

## P5 · Caldera vs. scriptado manual

**ACEPTADO.** Para el MVP, **scriptado manual**. Caldera añade complejidad de montaje (servidor, agentes, playbooks) que no aporta valor en fase de validación de hipótesis. Usa scripts Python/Bash directos (hping3, hydra, sqlmap, scripts propios para C2/ransomware emulado). Caldera solo si escalas a >20 técnicas.

---

## P6 · Gap de distribución DDoS

**VETO PARCIAL.** hping3/slowloris generan tráfico **sintético perfecto** (paquetes idénticos, timing regular), pero los DDoS reales tienen **variabilidad** (múltiples fuentes, tamaños de paquete distintos, timing jitter).

- **Riesgo:** el modelo DDoS-DeepSeek puede estar entrenado con tráfico sintético similar (hping3), en cuyo caso disparará bien. Pero si fue entrenado con tráfico real (CIC-IDS), habrá gap.
- **Condición:** mide la **entropía de tamaños de paquete** y **varianza de inter-arrival times** en tu emulación vs. CIC-IDS2017 DDoS. Si difieren >20%, el modelo no disparará.

---

## P7-P8 · Para DeepSeek (a ciegas)

**NO APLICA.** Estas preguntas son para DeepSeek, no para el Consejo.

---

## P9 · Invariante que sobrevive al NAT — **LA CRÍTICA**

**VETO TOTAL.** Esta es la pregunta que **invalida el ADR si no se resuelve**.

### Análisis técnico:

**NAT reescribe:**
- IP origen/destino (L3)
- Puertos origen/destino (L4)
- Checksums L3/L4

**NAT NO reescribe:**
- Payload (capa 7+)
- Opciones TCP (salvo que haya NAT con TCP rewriting, raro)
- TLS handshake (ClientHello, ServerHello) — **pero solo si el NAT no hace TLS inspection**

### Invariantes candidatos:

1. **JA3/JA4 (TLS ClientHello fingerprint):**
    - **Sobrevive al NAT:** sí, porque está en el payload TLS.
    - **Problema:** solo aplica a tráfico TLS. Tráfico no-TLS (DNS, HTTP, SMB) no tiene.
    - **Además:** si hay **TLS inspection** (proxy corporativo, common en hospitales), el fingerprint cambia.

2. **Hash de primeros bytes del payload (L7):**
    - **Sobrevive al NAT:** sí.
    - **Problema:** solo si el payload es determinista (HTTP request, SMB negotiate). Tráfico cifrado (SSH, TLS post-handshake) no tiene payload observable.

3. **Patrones seq/ack TCP:**
    - **Sobrevive al NAT:** **NO**. El NAT puede reescribir seq/ack si hace TCP normalization (raro, pero posible).
    - **Además:** seq/ack son relativos al inicio de la conexión, no son invariantes cross-sensor (aRGus ve post-NAT, Wazuh ve pre-NAT → secuencias distintas).

4. **Token coordinable (inyección en payload):**
    - **Sobrevive al NAT:** sí, si lo inyectas en el payload.
    - **Problema:** requiere modificar el tráfico (inyectar header custom), lo cual **rompe la emulación realista**. No puedes inyectar tokens en tráfico de producción.

### Veredicto:

**No existe invariante universal que sobreviva al NAT para todo tipo de tráfico.**

- Para **TLS sin inspection:** JA3/JA4 funciona.
- Para **no-TLS determinista (HTTP, SMB):** hash de payload funciona.
- Para **no-TLS no determinista o cifrado (SSH, DNS):** **no hay invariante**.

### Solución propuesta (levanta veto si se acepta):

**Correlación híbrida multi-nivel:**

1. **Nivel 1 (inequívoco, TLS):** JA3/JA4 + ventana temporal de 5s.
2. **Nivel 2 (inequívoco, no-TLS determinista):** hash de primeros 64 bytes del payload + ventana temporal de 5s.
3. **Nivel 3 (probabilístico, resto):** ventana temporal de 2s + 5-tupla (post-NAT en aRGus, pre-NAT en Wazuh → **no coincide**, así que solo ventana).

**Tasa de error esperada:**
- Nivel 1-2: <1% (ambigüedad solo si hay múltiples conexiones TLS/no-TLS determinista en 5s entre mismo par IP:puerto).
- Nivel 3: **5-15%** (ambigüedad alta si hay múltiples conexiones en 2s).

**Condición para levantar veto:**
- Implementar correlación híbrida multi-nivel.
- Medir tasa de error de join en laboratorio **con NAT en medio** (no plano).
- Si tasa de error nivel 3 >15%, **no puedes afirmar correlación inequívoca**. Debes declarar explícitamente que la correlación host↔red es **probabilística** en tráfico no-TLS/no-determinista, y acotar el blast radius (solo usar para propuesta, no para acción autónoma).

---

## P9-bis · Ventana temporal probabilística

**ACEPTADO CONDICIONAL.** Sí, es aceptable bajar de "inequívoco" a "probabilístico", **pero**:

- Debes declarar explícitamente en el ADR que la correlación es probabilística en ciertos casos.
- Debes medir la tasa de error de join (ver P9).
- Debes acotar el uso: correlación probabilística **solo para propuesta del grafo**, nunca para acción autónoma del firewall.

---

## P9-ter · Casos límite

**OBSERVACIONES:**

- **Reuso de conexión:** si una conexión TCP se reusa (keep-alive), el JA3/JA4 es el mismo, pero el hash de payload cambia. Nivel 2 (hash) distingue, nivel 1 (JA3) no.
- **Eventos de socket sin PID:** Wazuh puede no tener PID si el evento es de auditd sin contexto completo. En ese caso, no hay 5-tupla pre-NAT → **imposible correlacionar**. Debes declarar que estos eventos se descartan.
- **Tráfico no-TLS sin fingerprint útil:** ver P9 nivel 3.
- **Colocación de aRGus respecto al NAT:** si aRGus está **antes del NAT** (en la DMZ, antes del firewall), ve pre-NAT → community_id coincide con Wazuh. **Esta es la solución más simple.** ¿Por qué no colocas aRGus antes del NAT?

**Condición:** evaluar si aRGus puede colocarse pre-NAT en al menos 50% de las instalaciones. Si sí, resuelve el problema sin correlación híbrida.

---

## P10 · Proxy de laboratorio para promoción

**VETO PARCIAL.** Sin flota real, no puedes validar promoción cross-instalación. Pero puedes usar un **proxy de laboratorio**:

- **Proxy:** 3-5 máquinas virtuales en el laboratorio, cada una simulando una instalación distinta (distintas subredes, distinto NAT, distinto tráfico benigno).
- **Validación:** entrenas en VM1, promueves a VM2-VM5. Si el modelo funciona en todas, es señal de robustez.
- **Límite:** no replica la diversidad real de una flota (distintos hospitales, municipios), pero es lo mejor que puedes hacer sin financiación.

**Condición:** implementar proxy de laboratorio con ≥3 VMs heterogéneas antes de cualquier promoción.

---

## P11 · Comparación de grafos sin fusionar

**ACEPTADO.** Método: **graph motif matching** + **graph edit distance**.

- **Motif matching:** extraer subgrafos de 3-5 nodos (motifs) que representen patrones de ataque (ej: "escaneo → conexión fallida → conexión exitosa"). Comparar frecuencia de motifs entre instalaciones.
- **Graph edit distance:** medir cuántas operaciones (añadir/eliminar nodo/arista) cuestan hacer que dos grafos sean isomorfos. Distancia baja = variantes similares del mismo ataque.

**Herramienta:** NetworkX (Python) para motifs, o libgraphedit (C++) para distancia. Kuzu no tiene esto nativo, así que extraes el grafo a NetworkX/libgraphedit para comparación.

---

## P12 · Detección de envenenamiento

**VETO PARCIAL.** La contención está, la detección no. Propuesta:

**Señales de envenenamiento:**

1. **Procedencia criptográfica:** cada nodo firma sus CSV con Ed25519 (ADR-025). Si la firma no coincide con el nodo declarado → envenenamiento.
2. **Estadística de distribución:** comparar distribución de features del CSV entrante con la distribución histórica de ese nodo. Si desvía >3σ → cuarentena.
3. **Consistencia temporal:** si un nodo envía CSV con timestamps futuros o pasados (>1h de desfase) → envenenamiento.

**Condición:** implementar firma Ed25519 + validación de distribución + validación temporal antes de construir el grafo.

---

## P13 · Split disjunto en el paper

**VETO.** Con ~8 técnicas, el split disjunto es **estadísticamente insuficiente**.

- **Problema:** si train tiene 5 técnicas y eval tiene 3, el eval set es demasiado pequeño para medir generalización con confianza estadística.
- **Solución:** o amplías el catálogo a ≥20 técnicas (split 15/5), o declaras explícitamente que el split es **piloto ilustrativo** y no claim de generalización.

**Condición:** reescribir el Future Work del paper para declarar que el split es piloto, o ampliar catálogo antes de submit.

---

## Resumen de vetos

| Pregunta | Veredicto | Condición para levantar veto |
|----------|-----------|------------------------------|
| P1 | VETO PARCIAL | Medir gap de distribución emulado vs. real |
| P2 | VETO | Redefinir §10 con matriz de confusión + F1 por clase |
| P3 | VETO PARCIAL | Declarar generalización intra-laboratorio o incluir dataset externo |
| P4 | ACEPTADO | Añadir benigno TLS/DoH, mover fila 9 a §14 |
| P5 | ACEPTADO | — |
| P6 | VETO PARCIAL | Medir entropía/varianza emulación vs. CIC-IDS |
| P7-P8 | NO APLICA | Para DeepSeek |
| **P9** | **VETO TOTAL** | Implementar correlación híbrida multi-nivel + medir tasa de error con NAT |
| P9-bis | ACEPTADO CONDICIONAL | Declarar correlación probabilística + acotar uso |
| P9-ter | OBSERVACIONES | Evaluar colocación pre-NAT de aRGus |
| P10 | VETO PARCIAL | Implementar proxy de laboratorio con ≥3 VMs |
| P11 | ACEPTADO | — |
| P12 | VETO PARCIAL | Implementar firma Ed25519 + validación distribución + temporal |
| P13 | VETO | Ampliar catálogo a ≥20 técnicas o declarar piloto |

---

## Veredicto final

**NO ACEPTADO.** El ADR tiene **defectos críticos en §5 (correlación multi-sensor)** que invalidan la premisa de "correlación inequívoca". Si no se resuelve P9 con correlación híbrida multi-nivel y medición de tasa de error, el ADR no puede pasar a *Aceptado*.

**Prioridad máxima:** resolver P9 antes de cualquier implementación. El resto de vetos son levantables con ajustes metodológicos.

**Plazo para revisión:** 7 días (antes de DAY 200).

---

*Consejo de Sabios — Via Appia Quality*

FDO

QWEN