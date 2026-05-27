# Consejo de Sabios — Consulta #1
## ¿Son suficientes los features actuales para detectar WannaCry/NotPetya?

**Fecha:** DAY 90 — 18 marzo 2026
**Destinatarios:** Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Parallel.ai
**Proyecto:** ML Defender (aRGus EDR) — sistema NIDS C++20 open source
**Contexto:** arXiv preprint en preparación — respuesta influirá en PHASE2 roadmap

---

## Contexto del sistema

ML Defender es un sistema de detección de intrusiones de red en tiempo real
diseñado para organizaciones con recursos limitados (hospitales, escuelas,
pequeñas empresas). Arquitectura: eBPF/XDP → protobuf → ZeroMQ → RandomForest
embebido en C++20. Latencia sub-microsegundo en fast path.

**Baseline actual (DAY 87):**
- Dataset de entrenamiento: CTU-13 Neris (tráfico botnet/IRC C&C)
- F1 = 0.9985, Recall = 1.0000, FPR = 6.61% sobre bigFlows
- Entorno: VirtualBox VM, NIC limitada a ~33-38 Mbps (bottleneck confirmado)

---

## Feature set actual (40 features en schema, ~29 implementadas)

### Grupo 1 — Estadísticas de paquetes por flujo (single-flow, eBPF)
```
total_fwd_packets, total_bwd_packets
total_fwd_bytes, total_bwd_bytes
fwd_pkt_len_max, fwd_pkt_len_min, fwd_pkt_len_mean, fwd_pkt_len_std
bwd_pkt_len_max, bwd_pkt_len_min, bwd_pkt_len_mean, bwd_pkt_len_std
flow_bytes_per_sec, flow_packets_per_sec
fwd_packets_per_sec, bwd_packets_per_sec
avg_packet_size, avg_fwd_segment_size, avg_bwd_segment_size
dl_ul_ratio
```

### Grupo 2 — Inter-arrival times (IAT)
```
flow_iat_mean, flow_iat_std, flow_iat_max, flow_iat_min
fwd_iat_total, fwd_iat_mean, fwd_iat_std, fwd_iat_max, fwd_iat_min
```

### Grupo 3 — Flags TCP
```
fin_flag_count, syn_flag_count, rst_flag_count
psh_flag_count, ack_flag_count
```

### Grupo 4 — Multi-flow / ventana temporal (TimeWindowAggregator, WINDOW_NS=10s)
```
unique_dst_ports_count     ← número de puertos destino únicos en ventana
unique_dst_ips_count       ← número de IPs destino únicas en ventana
traffic_src_ip_entropy     ← entropía de IPs fuente en ventana
connection_rate            ← conexiones por segundo en ventana
```

### Grupo 5 — Sentinels (implementación pendiente PHASE2)
```
syn_ack_ratio              ← MISSING_FEATURE_SENTINEL = -9999.0f
rst_ratio                  ← MISSING_FEATURE_SENTINEL
dns_query_count            ← MISSING_FEATURE_SENTINEL
dns_response_count         ← MISSING_FEATURE_SENTINEL
tls_session_count          ← MISSING_FEATURE_SENTINEL
... (resto hasta 40)
```

**Nota arquitectónica:** `MISSING_FEATURE_SENTINEL = -9999.0f` es matemáticamente
inalcanzable en features de red reales. El modelo lo enruta a un path determinista
separado del scoring normal. No contamina el RandomForest.

---

## La pregunta

### Pregunta principal
**¿Son suficientes los ~29 features implementados para separar tráfico
WannaCry/NotPetya de tráfico benigno con F1 > 0.90?**

Responde considerando:

1. **Análisis por familia:**
    - **WannaCry:** propagación SMB (puerto 445), EternalBlue exploit,
      DNS killswitch lookup (`www.iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea.com`),
      alta tasa de RST (hosts no vulnerables rechazan conexión)
    - **NotPetya:** mismos vectores SMB, pero sin killswitch DNS,
      añade credential harvesting (Mimikatz) — invisible a nivel red pura,
      y propagación por WBEM/WMI (puertos 135, 445, 139)

2. **Para cada familia, indica:**
    - Qué features del set actual capturan la señal principal
    - Qué features del Grupo 5 (sentinels) son críticas para esta familia
    - Qué features NO están en el schema y deberían añadirse

3. **Priorización:** si pudieras añadir solo 3 features nuevas al schema
   para mejorar la detección de ransomware SMB-propagating, ¿cuáles serían?
   Ordénalas por impacto esperado.

### Pregunta secundaria
El modelo actual fue entrenado exclusivamente en CTU-13 Neris (botnet IRC).
**¿Esperarías que generalice a WannaCry/NotPetya sin reentrenamiento,
o es necesario datos de entrenamiento específicos de ransomware SMB?**

Justifica con referencia al espacio de features compartido vs exclusivo
entre botnet IRC y ransomware de propagación por red.

---

## Restricciones del sistema (importante para tu respuesta)

- **Latencia:** sub-microsegundo en fast path (heurísticas). El RandomForest
  se ejecuta en un thread separado — latencia tolerable hasta ~1ms.
- **Memoria:** objetivo < 512MB RAM total en producción (hospital con servidor básico)
- **Sin DPI:** el sistema opera en capa 3/4. No hay inspección de payload.
  Cualquier feature que requiera leer contenido de paquetes está fuera del alcance.
- **WINDOW_NS actual = 10 segundos.** Features multi-flow calculadas en esta ventana.
  WannaCry puede escanear miles de IPs en segundos — la ventana puede ser suficiente.
  NotPetya lateral movement puede ser más lento — ¿es suficiente?
- **Single-flow vs multi-flow:** features del Grupo 1-3 son por flujo individual.
  Features del Grupo 4 son agregadas por ventana temporal. Añadir features
  multi-flow tiene coste de implementación mayor.

---

## Lo que necesitamos decidir (output esperado del Consejo)

Con las respuestas de los 7 modelos, tomaremos estas decisiones de diseño:

1. **¿Implementar rst_ratio y syn_ack_ratio antes de generar datos sintéticos?**
   (están en Grupo 5 como sentinels — son P1 o P2?)

2. **¿unique_dst_ports_count en ventana de 10s es suficiente para capturar
   el scanning de WannaCry, o necesitamos una ventana más larga o un contador
   de scanning rate?**

3. **¿Añadir dns_query_count al schema tiene valor real sin poder inspeccionar
   el payload DNS? ¿O solo el volumen de queries al puerto 53 ya aporta señal?**

4. **¿El killswitch DNS de WannaCry (query a dominio específico) es detectable
   en capa 3/4 sin DPI, o es invisible para este sistema?**

---

## Formato de respuesta solicitado

```
## [Nombre del modelo] — Consulta #1

### Análisis WannaCry
[Features actuales que capturan señal WannaCry]
[Features sentinel críticas para WannaCry]
[Features faltantes que recomendarías añadir]

### Análisis NotPetya
[Igual estructura]

### Top 3 features nuevas (priorizadas)
1. [Feature] — [Justificación técnica]
2. [Feature] — [Justificación técnica]
3. [Feature] — [Justificación técnica]

### ¿Generaliza el modelo actual sin reentrenamiento?
[Sí/No/Parcial + justificación]

### Respuesta a las 4 decisiones de diseño
1. rst_ratio / syn_ack_ratio: [P1/P2 + por qué]
2. Ventana 10s para scanning: [Suficiente/Insuficiente + por qué]
3. dns_query_count sin DPI: [Valor/Sin valor + por qué]
4. Killswitch DNS detectable: [Sí/No/Parcial + por qué]
```

---

*ML Defender — DAY 90 — 18 marzo 2026*
*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*