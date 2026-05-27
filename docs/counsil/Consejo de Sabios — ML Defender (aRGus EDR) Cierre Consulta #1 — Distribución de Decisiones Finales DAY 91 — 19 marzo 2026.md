# Consejo de Sabios — ML Defender (aRGus EDR)
## Cierre Consulta #1 — Acta Final con Respuestas Completas
### DAY 91 — 19 marzo 2026

---

Estimados miembros del Consejo,

Este documento es el **acta final** de la **Consulta #1** (iniciada DAY 90), relativa a la detección de ransomware SMB (WannaCry / NotPetya) en ML Defender. Recoge todas las respuestas recibidas, incluyendo la respuesta adicional de DeepSeek (DAY 91) y el estado pendiente de Qwen.

Este documento tiene tres propósitos:

1. **Registrar formalmente** las decisiones alcanzadas por el Consejo para que todos los miembros tengan la misma versión canónica.
2. **Documentar la respuesta adicional de DeepSeek** (DAY 91), que aportó `flow_duration_min` como nueva feature P2 no contemplada en el roadmap original.
3. **Mantener abierta la solicitud a Qwen (Alibaba/Tongyi)**, cuya respuesta genuina sigue pendiente.

---

## Contexto del sistema

**ML Defender (aRGus EDR)** es un IDS/EDR open-source en C++20 para organizaciones con recursos limitados (hospitales, colegios, ayuntamientos). Stack: eBPF/XDP, ZeroMQ, ChaCha20-Poly1305, FAISS, ONNX Runtime, protobuf.

**Baseline validado (DAY 86):**
- F1 = 0.9985, Recall = 1.0000, FPR = 6.61% — sobre CTU-13 Neris (botnet IRC)
- 31/31 tests CTest pasando
- 6/6 componentes del pipeline en ejecución

**Limitación identificada:** El modelo actual tiene recall estimado de **0.70–0.85** contra WannaCry/NotPetya sin reentrenamiento, por dos razones:
- Los features `rst_ratio` y `syn_ack_ratio` están actualmente a sentinel (`-9999.0f`) — nunca se han extraído
- La distribución de entrenamiento (CTU-13 Neris, IRC C2) no cubre tráfico SMB de escaneo masivo

---

## Preguntas de la Consulta #1

Se sometieron al Consejo las siguientes preguntas:

**Q1.** ¿Qué features son imprescindibles para detectar WannaCry/NotPetya en capa 3/4?

**Q2.** ¿Es la ventana de 10 segundos suficiente para ambos ataques?

**Q3.** ¿Debe incluirse el killswitch DNS de WannaCry como señal de detección?

**Q4.** ¿Qué recall estimado tiene el modelo actual sin reentrenamiento?

**Q5.** ¿Cuál es el roadmap de features recomendado (P1/P2/P3)?

---

## Decisiones finales del Consejo

### UNANIMIDAD — todos los modelos coincidieron

**D1 — `rst_ratio` → P1 INMEDIATO**
El ratio de paquetes RST sobre el total es el discriminador más potente para escaneo SMB masivo. WannaCry produce `rst_ratio > 0.70` (la mayoría de targets rechazan o no responden). Debe implementarse antes de cualquier dataset sintético.

**D2 — `syn_ack_ratio` → P1 INMEDIATO**
El ratio SYN/ACK mide handshakes completados. WannaCry produce `syn_ack_ratio < 0.10` (solo hosts vulnerables completan el handshake). Complementario e independiente de `rst_ratio`. Implementar en la misma iteración.

**D3 — El modelo actual NO generaliza a ransomware SMB sin reentrenamiento**
Recall estimado: **0.70–0.85** sin datos SMB + reentrenamiento.
Para alcanzar F1 > 0.90 en WannaCry/NotPetya se requieren:
- Features `rst_ratio` + `syn_ack_ratio` implementados
- Dataset sintético SMB validado
- Reentrenamiento del Random Forest

### MAYORÍA CLARA — consenso con matices menores

**D4 — Ventana 10s: suficiente para WannaCry, insuficiente para NotPetya temprano**
WannaCry a 100–200 SYN/s produce señal clara en 10s.
NotPetya a 50–150 SYN/s puede requerir acumulación en ventana de 60s para fases tempranas.
**Decisión:** Mantener 10s como ventana primaria + añadir FEAT-WINDOW-2 (60s secundaria) al backlog P2.

**D5 — Killswitch DNS de WannaCry: NO incluir como señal de detección**
Razones:
- ML Defender opera en capa 3/4 únicamente — el nombre de dominio DNS requiere DPI
- La firma compuesta DNS→SMB produce FPR inaceptable (patrón presente en tráfico Windows legítimo: WSUS, DC lookups)
- La propagación SMB ya está cubierta por `rst_ratio` sin necesitar DNS
- Es una **limitación honesta** que se documentará explícitamente en el paper (§10)

**D6 — `dns_query_count` → P3**
Valor solo en correlación con otras señales, no como feature primaria.

### Descartadas

- `ICMP_unreachable_rate` — señal secundaria, no primaria para SMB
- Firma compuesta DNS→SMB — FPR inaceptable en tráfico Windows legítimo

### Roadmap de features resultante

| Prioridad | Feature | Justificación |
|---|---|---|
| **P1** | `rst_ratio` | Discriminador primario WannaCry/NotPetya |
| **P1** | `syn_ack_ratio` | Complementario — handshakes fallidos |
| P2 | `port_diversity_ratio` | NotPetya usa SMB + WMI + RPC |
| P2 | `new_dst_ip_rate` | Velocidad de descubrimiento de nuevos targets |
| P2 | `dst_port_445_ratio` | Proporción de tráfico a puerto SMB |
| P2 | `flow_duration_min` | Flujos WannaCry < 50ms (SYN→RST); legítimos > 200ms — aporte DeepSeek DAY 91 |
| P2 | FEAT-WINDOW-2 (60s) | Cobertura NotPetya fase temprana |
| P3 | `dns_query_count` | Solo en correlación |
| P3 | `smb_connection_burst` | Señal complementaria |
| P3 | `wmi_activity_proxy` | Proxy de actividad lateral WMI |

---

## Estado de respuestas por modelo

| Modelo | Ronda 1 | Ronda 2 | Ronda 3 (DAY 91) | Estado |
|---|---|---|---|---|
| Claude (Anthropic) | ✅ | ✅ | — | Completo |
| Grok (xAI) | ✅ | ✅ | — | Completo |
| ChatGPT (OpenAI) | ✅ | ✅ | — | Completo |
| DeepSeek | ✅ | ✅ | — | Completo |
| Gemini (Google) | ✅ | ✅ | — | Completo |
| Parallel.ai | ✅ | ✅ | — | Completo |
| **Qwen (Alibaba/Tongyi)** | ⚠️ | ⚠️ | ✅ | **Completo — ver nota** |

> **Nota de atribución — Qwen DAY 91:** Las dos respuestas recibidas en DAY 91 provienen de **`chat.qwen.ai`** (plataforma oficial Alibaba/Tongyi), confirmado por el acceso directo de Alonso. En ambas respuestas el modelo se autoidentificó como "DeepSeek" — fenómeno documentado en LLMs chinos de la generación 2024-2025, donde el entrenamiento con datos cruzados entre modelos produce autoidentificaciones incorrectas. **La fuente de verdad es la plataforma, no la autodeclaración del modelo.** Ambas respuestas se atribuyen correctamente a Qwen (Alibaba/Tongyi) en el registro del Consejo.

---

## Respuestas de Qwen — DAY 91 (chat.qwen.ai)

### Ronda DAY 91 — Respuesta 1 (Consulta #1 — features WannaCry/NotPetya)

Qwen confirmó el 95% de las decisiones del Consejo y aportó `flow_duration_min` como feature P2 no contemplada en el roadmap original:

- `rst_ratio` → P1: ✅ acuerdo total
- `syn_ack_ratio` → P1: ✅ acuerdo total
- Ventana 10s (WannaCry): ✅ suficiente
- Ventana 10s (NotPetya temprano): ⚠️ marginal — recomienda 60s secundaria
- Killswitch DNS: ✅ NO incluir — acuerdo total
- Recall estimado sin reentrenamiento: desagregado como WannaCry 0.80–0.90, NotPetya 0.60–0.75 (media 0.70–0.85, coincide con el Consejo)

**Aporte nuevo Ronda 1:** `flow_duration_min` (P2) — flujos WannaCry < 50ms (SYN→RST inmediato) vs legítimos > 200ms. Derivable de timestamps eBPF/XDP sin coste adicional. Añadido al roadmap y al spec sintético.

### Ronda DAY 91 — Respuesta 2 (revisión network_security.proto)

Qwen revisó el schema protobuf completo y aportó:

**Fortalezas validadas:**
- Dual-score architecture (`fast_detector_score` + `ml_detector_score` + `DetectorSource`) — trazabilidad completa
- `DetectionProvenance` con `repeated EngineVerdict` — captura todos los votos, no solo el ganador
- Organización por modelo (`ddos_embedded`, `ransomware_embedded`, etc.) — no una bolsa desordenada de features
- `custom_features` (map<string, double>) — extensibilidad sin breaking changes

**Observación técnica — ambigüedad RansomwareFeatures:**
Identificó dos caminos para ransomware features que pueden confundir a nuevos contribuidores:
```
Camino 1 (PHASE 1): NetworkFeatures.ransomware_embedded (10 features)
Camino 2 (enterprise): NetworkSecurityEvent.ransomware (20 features)
```
Recomendación: añadir comentario explicativo en el proto documentando que PHASE 1 usa `ransomware_embedded` y PHASE 2 usará `RansomwareFeatures` (migración gradual sin breaking changes).

**Aporte concreto — campos proto para P1:**
```protobuf
// En NetworkFeatures
optional float rst_ratio = 116;     // RST/SYN ratio — escaneo SMB fallido
optional float syn_ack_ratio = 117; // SYN/ACK ratio — complementa rst_ratio
```
Opcionales → no breaking change. Tipos float → compatibles con pipeline existente.

**Checklist pre-arXiv (schema-related):**
1. Añadir comentarios `RansomwareFeatures` vs `ransomware_embedded`
2. Añadir `rst_ratio` / `syn_ack_ratio` como opcionales (P1)
3. Validar mapping CSV 127-columnas ↔ proto
4. Confirmar que `schema_version=31` refleja v3.1.0 (no v31.0)
5. Generar diagrama UML del schema para el paper (opcional)

---

---

## Respuesta adicional de Qwen — DAY 91 (Ronda 1, Consulta #1)

> *Nota: esta respuesta fue reatribuida de DeepSeek a Qwen tras confirmar que el acceso fue realizado desde `chat.qwen.ai`. Ver nota de atribución en tabla de estado.*

Qwen confirmó el 95% de las decisiones y aportó `flow_duration_min` como feature P2 nueva. Ver detalle completo en la sección de respuestas DAY 91 más arriba.

---

## Solicitud pendiente a Qwen (Alibaba / Tongyi Lab)

**Estado:** CERRADO — Qwen ha respondido en DAY 91 (dos rondas). Ver sección anterior.

La Consulta #1 está formalmente cerrada con los 7 miembros del Consejo habiendo respondido.

**Las 5 preguntas para Qwen:**

**Q1.** Dado que ML Defender opera exclusivamente en capa 3/4 (sin DPI), ¿qué features del vector de 127 columnas son más relevantes para detectar WannaCry y NotPetya? ¿Cuáles implementarías primero?

**Q2.** La ventana de agregación actual es de 10 segundos. WannaCry genera 100–200 SYN/s; NotPetya genera 50–150 SYN/s con mayor foco interno. ¿Es la ventana de 10s suficiente para ambos? ¿Qué cambiarías?

**Q3.** WannaCry tiene un mecanismo de killswitch: antes de ejecutar el payload, hace una consulta DNS a un dominio hardcoded. Si recibe respuesta, se detiene. ¿Debería ML Defender incluir esta señal DNS como feature de detección?

**Q4.** El modelo actual (Random Forest, CTU-13 Neris) tiene F1 = 0.9985 en botnet IRC. ¿Qué recall estimarías para WannaCry/NotPetya sin reentrenamiento? ¿Qué necesitaría el modelo para alcanzar F1 > 0.90 en SMB ransomware?

**Q5.** ¿Algún aspecto de la detección de ransomware SMB en capa 3/4 que el Consejo debería haber considerado y no aparece en el roadmap?

---

## Próximos pasos tras cierre del Consejo #1

Una vez registrada la respuesta de Qwen, se cierra formalmente la Consulta #1 y se procede a:

1. **DAY 91–92:** Implementar `rst_ratio` y `syn_ack_ratio` en el sniffer (próxima sesión con VM)
2. **DAY 92–95:** Generador de datos sintéticos WannaCry/NotPetya (spec en `docs/design/synthetic_data_wannacry_spec.md`)
3. **DAY 95–100:** Reentrenamiento del Random Forest + validación F1
4. **Paralelo:** Envío del preprint arXiv (esperando endorser — deadline DAY 96)

---

*Consejo de Sabios — ML Defender (aRGus EDR)*
*Consulta #1 — Cierre formal*
*DAY 91 — 19 marzo 2026*
*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*