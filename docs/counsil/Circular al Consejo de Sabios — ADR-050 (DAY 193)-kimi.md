# Respuesta del Consejo de Sabios — ADR-050 (DAY 193)

He leído el ADR completo. Respondo **pregunta a pregunta**, marcando vetos explícitos donde aplique. El tono es el que pediste: morder a saco.

---

## P1 · ¿Es la hipótesis de §1 falsable y sin defecto fatal?

**Sí, es falsable.** La hipótesis es: *"los modelos no ven clases de ataque para las que no fueron entrenados, salvo lo que capten por anomalía los modelos de normalidad"*. Se falsifica si una sonda no vista (hydra, nmap) dispara el ensemble correcto con atribución correcta.

**Defecto fatal candidato: confound por solapamiento de features (P2).** Si nmap genera muchas conexiones fallidas, y el modelo de ransomware entrenado en C2 beacon también ve conexiones fallidas, ¿dispara ransomware o normalidad? Si dispara ransomware, es **misclasificación**, no generalización. La hipótesis sobrevive solo si medís **detección + atribución correcta**, no solo "¿disparó algo?".

**VETO parcial sobre métrica.** Si el experimento solo mide "¿alertó algún modelo?", el ADR no prueba la hipótesis. La métrica mínima debe ser: **precision/recall por clase, con matriz de confusión cross-sensor**. Sin eso, el experimento mide ruido, no generalización.

---

## P2 · ¿Disparo sobre sonda no vista = generalización o misclasificación por solapamiento?

**Es el confound central.** Las features de red se solapan masivamente:
- Conexiones fallidas: bruteforce, C2 beacon, escaneo.
- Ratio paquetes/seg: DDoS, pero también C2 burst.
- Tamaños de paquete: todo.

**VETO sobre "detección basta".** No basta. Debéis medir:
1. **Atribución correcta:** ¿el modelo que disparó es el de la clase emulada?
2. **Cross-sensor concordancia:** ¿el grafo reconstruye la misma etiqueta que el ensemble?
3. **Feature importance shift:** ¿qué features activó el modelo en la sonda vs. en entrenamiento? (SHAP/LIME sobre el evento emulado).

Si el ensemble DDoS dispara ante nmap porque ambos generan "muchas conexiones por segundo", es **falso positivo de clase**, no generalización. El ADR lo intuye en §10 pero no lo formaliza como gate de aceptación.

**Recomendación:** Añadid un **"índice de solapamiento"** por par de clases (Jaccard sobre top-10 features) antes de emular. Si >0.6, la sonda no prueba generalización — prueba robustez al ruido.

---

## P3 · ¿Es factible demostrar generalización con detectores entrenados en sintético generativo?

**Factible, pero el revisor exigirá un dataset externo real.** No hay escapatoria.

El paper ya reconoce covariate shift en CIC-IDS. Si los ensembles se entrenaron en DeepSeek-sintético y testeáis en emulación controlada (que también es "sintético" en el sentido de orquestado, aunque capture real en el cable), el revisor dirá: *"ambos son laboratorio; demostradlo en tráfico real de producción"*.

**VETO sobre el claim del paper si no hay validación externa.** El ADR es piloto ilustrativo (§12 lo admite). Mi consejo: **no claims de generalización en el paper**, solo "demostramos metodología y medimos gap". El claim de generalización requiere:
- Holdout de tráfico real de producción (no emulado), etiquetado manualmente.
- O: participación en benchmark público con ground truth (CIC-IDS nuevo, pero ya sabéis que shifta).

**Alternativa honesta:** Frame the paper as *"methodology for measuring generalization gap"*, not *"we generalize"*. Eso sí pasa revisión.

---

## P4 · ¿Catálogo v1 adecuado?

**Adecuado para piloto, insuficiente para paper.**

| # | Técnica | ¿Problema? |
|---|---|---|
| 1-2 | DDoS | OK, pero ¿probaréis volumétrico + protocolo + aplicación? Solo SYN/UDP + slowloris es narrow. |
| 3-4 | Ransomware fase-red | OK, pero la fase-host (fila 5) es la que diferencia ransomware de C2 genérico. Sin ella, el ensemble ransomware no se estresa. |
| 5 | Ransomware fase-host | **Obligatoria** si el modelo mezcla host+red (§13). Sin Wazuh alimentando esto, el test es incomplete. |
| 6-8 | Sondas | OK, pero faltan: DNS tunneling (C2 encubierto), ICMP tunneling, exfiltración HTTP/HTTPS (técnica real, no ataque). |
| 9 | Data poisoning | Metodológicamente brillante. **Prioridad alta.** |

**VETO sobre fila 5 si no hay Wazuh en el testbed.** Si no cableáis Wazuh → features de host para el ensemble ransomware, el test de ransomware es **vacío de contenido** (§13, implicación 1). El ADR lo sabe; el Consejo lo eleva a bloqueante.

**Añadir al catálogo:** DNS tunneling (T1071.004), ICMP tunneling (T1095), exfiltración HTTP POST grande (T1041). Son técnicas reales que vuestros clientes (hospitales) ven y que generan features de red distintivas.

---

## P5 · ¿Vale Caldera su coste de montaje en el MVP?

**No. Veto explícito sobre Caldera para MVP.**

Caldera es ~527 procedimientos, pero:
- Es endpoint-céntrico (Wazuh). Vuestro gap crítico es red (aRGus/Suricata/Zeek).
- El coste de montaje (infraestructura Caldera + agentes + adaptadores) es 2-3 semanas. Tenéis 6 semanas al go/no-go.
- Los procedimientos ATT&CK que necesitáis (filas 1-4, 6-8) son **más fáciles de ejecutar con scripts directos** que con Caldera.

**Recomendación:** Scriptado a mano para MVP. Caldera para fase 2 (post-FEDER) cuando el pipeline Wazuh esté maduro y queráis escalar cobertura ATT&CK.

---

## P6 · ¿hping3/slowloris generan features que coincidan con DDoS-DeepSeek?

**Probablemente no, y eso es bueno.**

DeepSeek generó "snapshots 1-5 min, agregación paquetes/seg, fuentes únicas" (§13). hping3 genera SYN flood crudo; slowloris genera conexiones HTTP lentas. Son **modalidades distintas** de DDoS.

**Esto no es bug, es feature.** Si el modelo entrenado en DeepSeek-sintético dispara ante hping3, es **generalización real** (distribución diferente, misma clase). Si no dispara, medís el gap.

**Veto sobre ajustar hping3 para "encajar" en DeepSeek.** No. Emulad lo realista para el cliente (hospital): volumétrico desde múltiples IPs (hping3 distribuido), slowloris desde una IP, reflexión DNS si podéis. Medid el gap, no lo cerréis artificialmente.

---

## P7-P8 · Para DeepSeek (a ciegas)

No aplican a mí (soy Kimi, no DeepSeek). Pero dejo nota metodológica:

**El protocolo ciego es correcto.** Confrontar la respuesta de DeepSeek contra §13 es buena práctica. Mi predicción (para confrontar después): DeepSeek dirá que las features eran "mixtas host+red" sin detallar la proporción, y que las distribuciones fueron "basadas en patrones conocidos de ransomware". Si no menciona explícitamente entropía de I/O ni `file_operations`, §13 gana — y el gap host-red se confirma.

---

## P9-P9-ter · `DEBT-WAZUH-COMMUNITYID-001` — LA PRIORITARIA

**Esta es la pregunta más dura del ADR. La muerdo a fondo.**

### ¿Qué invariante sobrevive al NAT?

**Ninguno de los obvios sobrevive intacto:**

| Candidato | ¿Sobrevive NAT? | ¿Ambos lados lo ven? | Veredicto |
|---|---|---|---|
| `community_id` (5-tupla) | **NO** — NAT reescribe IPs/puertos | Sí, pero valores distintos | **Descartado** |
| JA3/JA4 TLS fingerprint | Sí (payload intacto) | aRGus sí (TLS handshake en claro); Wazuh **solo si intercepta TLS** (no por defecto) | **Parcial** |
| Hash primeros N bytes payload | Sí | aRGus sí; Wazuh **solo si tiene acceso al buffer de red** (no, es host-level) | **No** |
| Seq/ack TCP | Sí | aRGus sí; Wazuh no expone seq/ack en eventos de socket estándar | **No** |
| Payload application-level | Sí | aRGus sí; Wazuh **no**, salvo que el agente Wazuh haga deep packet inspection (no lo hace) | **No** |

**Conclusión dura:** No hay invariante de payload que **ambos sensores computen nativamente** sin modificación del agente Wazuh.

### ¿Qué sí podría funcionar?

**Opción A: Modificar Wazuh para emitir `community_id` pre-NAT + post-NAT.**

Wazuh ve la 5-tupla pre-NAT en el socket del proceso. Si aRGus ve post-NAT, necesitáis que Wazuh emita **ambos** (o que el adapter Wazuh compute `community_id` con ambas vistas y envíe ambos). Pero esto requiere:
- Que Wazuh sepa la IP pública/NATed (¿la sabe? En algunos casos sí, vía STUN/UPnP; en hospitales, no necesariamente).
- O: que el adapter Wazuh haga **passive NAT detection** (comparar IP local vs. IP en cabeceras HTTP/S, si las hay).

**Complejidad: alta. Viabilidad: media-baja para MVP.**

**Opción B: Token coordinable (impronta en adapters).**

Ambos adapters (aRGus y Wazuh) inyectan un **token efímero** en el payload o en un header custom. Ejemplo: el adapter Wazuh añade un header HTTP `X-ARGUS-CORR: <token>` en peticiones salientes; aRGus lo ve en el cable. Para no-TLS, funciona. Para TLS, el header está encriptado — aRGus no lo ve.

**Limitación:** Solo funciona para tráfico donde Wazuh puede modificar (HTTP no-TLS, o si hacemos TLS termination). No es universal.

**Opción C: Ventana temporal probabilística + acotación de error.**

**VETO sobre "inequívoco" si caéis aquí.** No es inequívoco. Es probabilístico. Pero **puede ser suficiente** si acotáis la tasa de error.

**Cálculo de tasa de error del join por ventana temporal:**

Suponed:
- Ventana temporal: ±Δt (ej. ±1 segundo).
- Tasa de conexiones nuevas en el host: λ (ej. λ=10 conexiones/seg en un servidor web).
- Eventos Wazuh en la ventana: 1 (el que queremos unir).
- Flujos aRGus en la ventana: ~λ × 2Δt = 20.

**Probabilidad de join ambiguo:** Si hay 20 flujos y 1 evento Wazuh, y no hay otra señal discriminante, el join es **1/20 = 5% de acierto por azar** si hay 20 candidatos. Pero si el evento Wazuh es "proceso X conectó a IP:puerto Y", y aRGus vio 20 flujos a distintos destinos, el filtro por IP:puerto remoto reduce a ~1-2 candidatos.

**Acotación práctica:**
- Usad **ventana temporal corta** (±100ms, no ±1s).
- Añadid **filtro por IP:puerto remoto** (Wazuh lo sabe, aRGus lo ve post-NAT pero el destino NO cambia con NAT saliente — el NAT reescribe origen, no destino).

**¡Esto es clave!** En NAT saliente (el caso hospital):
- **IP/puerto origen:** cambia (192.168.x → pública).
- **IP/puerto destino:** **NO cambia** (el servidor remoto es el mismo).

Por tanto, si Wazuh emite "conexión a `dest_ip:dest_port`" y aRGus filtra flujos a ese `dest_ip:dest_port`, el join es **mucho más estrecho**. El `community_id` falla porque incluye origen; pero si hacéis join por **(dest_ip, dest_port, protocolo, ventana_temporal)**, el NAT no rompe nada.

**Propuesta del Consejo (híbrida):**

```
join_key = hash(dest_ip, dest_port, protocol, floor(event_time / window_size))
```

Donde `window_size` = 100ms o 1s. El NAT no afecta `dest_ip:dest_port`. La ambigüedad depende de cuántas conexiones distintas del mismo host van al mismo destino en la misma ventana — en la práctica, baja.

**¿Es aceptable bajar de "inequívoco" a "probabilístico"?**

**Sí, pero con condiciones:**
1. **Documentar la tasa de error teórica** (como arriba) y medirla empíricamente en el testbed.
2. **No usar este join para decisiones de firewall autónomas** (§3 ya lo prohíbe; el grafo propone, no actúa).
3. **Validar con ground truth inyectado:** en el laboratorio, sabéis qué evento Wazuh corresponde a qué flujo aRGus. Medid la tasa de falsos joins. Si es <5%, es usable para enriquecimiento del grafo. Si es >20%, no lo es.

**VETO sobre usar join probabilístico para acción autónoma.** El ADR ya lo prohíbe (§3), pero lo reafirmo: si el join tiene 5% de error, y el grafo propone basado en ese join, y un humano revisa, OK. Si el join alimenta directamente el ensemble que dispara el firewall, **NO**.

**P9-ter: Casos límite.**

- **Reuso de conexión:** Wazuh evento "socket connect" vs. aRGus flujo completo. Si Wazuh emite eventos por paquete/operación, hay múltiples eventos por flujo. El join debe ser **1 flujo → N eventos**, no 1:1.
- **Eventos socket sin PID:** Wazuh a veces ve conexiones sin asociar a proceso (kernel-level). En ese caso, el enriquecimiento es menor — documentadlo como limitación.
- **Tráfico no-TLS sin fingerprint:** El join por destino+ventana es la única opción. Aceptad la ambigüedad.
- **Colocación de aRGus:** Si aRGus está **antes** del NAT (LAN side), ve pre-NAT. Si está **después** (WAN side), ve post-NAT. En hospitales, aRGus probablemente está en el router/firewall (post-NAT saliente, pre-NAT entrante). **Esto es asimétrico:** saliente = post-NAT, entrante = pre-NAT. El join por destino funciona para saliente; para entrante, origen = destino remoto (no cambia). Así que **destino siempre es invariante** en ambas direcciones.

---

## P10 · ¿Qué proxy de laboratorio valida promoción antes de flota?

**No hay proxy perfecto. El honesto es "diversidad sintética + holdout real".**

Opciones:
1. **Holdout de emulaciones no vistas:** El laboratorio emula técnicas que el modelo no vio en entrenamiento. Si generaliza en laboratorio, es proxy débil pero mejor que nada.
2. **Datos históricos de una instalación piloto:** Si tenéis una instalación piloto (¿la vuestra propia?) con tráfico real etiquetado manualmente, eso es holdout.
3. **Benchmark público externo:** CIC-IDS-2024, pero covariate shift conocido.

**VETO sobre promover a "todos los nodos" sin proxy.** No lo hagáis. La promoción debe ser **por nodo**, con opt-in, y con métricas de FPR/TPR reportadas por el nodo. El modelo "mejoró en laboratorio" no implica "mejoró en el hospital X".

**Recomendación:** Diseñad el sistema de plugins (ADR-025) para **versionado por nodo**, no global. Cada nodo puede quedarse en la versión que validó. El "todos los nodos" es aspiracional post-FEDER.

---

## P11 · Comparar grafos sin fusionarlos: ¿qué método?

**Similitud de grafos / motif matching es el camino correcto.**

Opciones concretas:
1. **Graph kernels** (Weisfeiler-Lehman): comparar grafos enteros por coloración de vecindarios. Rápido, probado.
2. **Motif counting:** Contar subgrafos frecuentes (triángulos, cadenas de 4 nodos) y comparar distribuciones. Si dos instalaciones tienen el mismo motif "C2 beacon → lateral SMB → cifrado", es la misma variante.
3. **Embedding de nodos (Node2Vec/GraphSAGE) + distancia coseno:** Cada grafo se resume en un vector; la distancia entre vectores = similitud de patrones de ataque.

**VETO sobre reconstruir supergrafo por el backdoor.** Si comparáis embeddings y luego entrenáis un modelo global sobre ellos, habéis fusionado de facto. Mantened la frontera: **comparación solo para alerta/insight, no para entrenamiento conjunto.**

**Recomendación:** Empezad con **motif counting** (más interpretable que embeddings). Un "motif" = secuencia técnica ATT&CK (T1071 → T1021.002 → T1486). Si dos instalaciones reportan el mismo motif en ventanas similares, alerta de variante propagada.

---

## P12 · `DEBT-NODE-PROVENANCE-001`: ¿cómo detectar origen envenenado?

**Señales candidatas:**

| Señal | ¿Funciona? | Complejidad |
|---|---|---|
| **Estadística de distribución en frontera** | Sí. Un CSV envenenado tendrá features fuera de la distribución histórica de ese nodo (z-score >3). | Media. Requiere baseline por nodo. |
| **Procedencia criptográfica (firma del nodo)** | Sí, pero **no detecta el envenenamiento**, solo autentica el origen. Un nodo legítimo puede enviar datos envenenados (comprometido). | Baja. Obligatoria para autenticidad, insuficiente para detección. |
| **Inconsistencia temporal** | Sí. Si un nodo envía eventos con timestamps futuros o en ráfagas imposibles, es señal. | Baja. |
| **Divergencia grafo-local** | Sí. Si el grafo de un nodo tiene estructuras que no aparecen en ningún otro nodo de la flota (outlier en espacio de motifs), es señal. | Alta. Requiere comparación cross-nodo. |

**VETO sobre confiar solo en firma criptográfica.** Firma = autenticidad, no integridad semántica. Un nodo comprometido firma datos maliciosos válidamente.

**Recomendación (capas):**
1. **Firma Ed25519** (ADR-025): autenticidad del nodo.
2. **Z-score por feature por nodo** (estadística): outlier detection.
3. **Motif outlier cross-nodo** (§11): si un nodo reporta un motif que nadie más ve, cuarentena.
4. **Human-in-the-loop** para liberación de cuarentena.

La detección no será perfecta. La contención (§14) es sólida; la detección es **mejora continua**.

---

## P13 · Split disjunto con ~8 técnicas como piloto ilustrativo

**Aceptable para metodología, no para claim de generalización.**

El ADR lo dice honestamente en §12: *"el split es ilustrativo / piloto; se declara así en el paper"*. **Mantened esa honestidad.** No reescribáis el Future Work para sobreprometer.

**VETO sobre cambiar el framing a "demostramos generalización" con 8 técnicas.** Con 8 técnicas, el split disjunto puede dejar 4 en train y 4 en eval. Si eval es trivial (ej. solo SYN flood vs. solo slowloris), no prueba nada. Fijad el criterio de partición para que eval sea **no trivial** (al menos 2 técnicas por clase, distribuidas).

**Recomendación para el paper:**
- Frame: *"We propose a methodology for adversarial multi-sensor ground truth generation and evaluate its feasibility on a pilot set of 8 techniques."*
- Future Work: *"Scaling to full ATT&CK coverage and validation on real-world production traffic."*

Eso pasa revisión. Un claim de generalización con 8 técnicas y sintético no.

---

## Resumen de vetos explícitos

| # | Veto | Sección | Razón |
|---|---|---|---|
| 1 | Métrica "¿disparó?" insuficiente | P1/P2 | Debe ser detección + atribución correcta + matriz de confusión |
| 2 | Claim de generalización sin validación externa | P3 | El revisor lo matará; frame como metodología |
| 3 | Fila 5 (ransomware host) sin Wazuh cableado | P4 | El test de ransomware es vacío sin host features |
| 4 | Caldera en MVP | P5 | Coste 2-3 semanas; scriptado a mano primero |
| 5 | Join probabilístico para acción autónoma | P9 | El grafo propone, no actúa; ya en §3, reafirmado |
| 6 | Promoción global sin proxy por nodo | P10 | "Mejoró en lab" ≠ "mejoró en hospital X" |
| 7 | Supergrafo por el backdoor | P11 | Comparar sí, fusionar no |
| 8 | Confianza solo en firma criptográfica para poisoning | P12 | Firma ≠ integridad semántica |
| 9 | Claim de generalización con 8 técnicas | P13 | Frame honesto como piloto metodológico |

**Votos: 9/9 vetos parciales, 0 vetos totales.** El ADR es sólido en arquitectura y seguridad. Los vetos son sobre **formulación de claims, métricas, y priorización de MVP**. La hipótesis no tiene defecto fatal, pero necesita métricas más duras.

---

## La respuesta a `DEBT-WAZUH-COMMUNITYID-001` (síntesis)

**No hay invariante de payload que ambos sensores computen nativamente sin modificar Wazuh.** La dirección práctica es:

1. **Join por (dest_ip, dest_port, protocolo, ventana_temporal).** El NAT no reescribe destino. Esto reduce la ambigüedad drásticamente.
2. **Medir tasa de error empíricamente** en el testbed con NAT desde el día 1.
3. **Aceptar probabilístico para enriquecimiento del grafo**, nunca para acción autónoma.
4. **Investigar** (post-FEDER) modificar Wazuh para emitir `community_id` pre-NAT o inyectar token coordinable.

**El NAT no mata el proyecto. Mata la ilusión de "inequívoco".** La rebaja a probabilístico es aceptable si se documenta y se acota.

---

*Via Appia Quality — construido para durar décadas.*

FDO 

KIMI