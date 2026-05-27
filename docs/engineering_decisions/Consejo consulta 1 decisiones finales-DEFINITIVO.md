# Consejo de Sabios — Decisiones Finales Consulta #1
## WannaCry/NotPetya: features necesarias para detección en capa 3/4

**Fecha:** DAY 90 — 18 marzo 2026
**Rondas:** 2 deliberación + 1 validación final
**Participantes:** ChatGPT, Claude, DeepSeek, Gemini, Grok, Qwen*
**Árbitro final:** Alonso Isidoro Román
**Path:** `docs/design/consejo_consulta_1_decisiones_finales.md`
**Versión:** 1.1 — refinamientos incorporados tras validación final del Consejo

> *Nota: En la primera ronda, Qwen se identificó como DeepSeek.
> La atribución correcta está pendiente de aclaración.
> Las decisiones son válidas independientemente — el contenido técnico converge.
> Acción pendiente: lanzar Consulta #1 a Qwen individualmente para completar
> el registro con las 7 voces correctamente atribuidas.

---

## Convergencia del Consejo — Mapa de consenso

| Decisión | Ronda 1 | Ronda 2 | Validación final | Veredicto |
|---|---|---|---|---|
| rst_ratio → P1 | 6/6 | 6/6 | 6/6 | ✅ UNANIMIDAD |
| syn_ack_ratio → P1 | 5/6 | 6/6 | 6/6 | ✅ UNANIMIDAD |
| Ventana 10s suficiente WannaCry | 6/6 | 6/6 | 6/6 | ✅ UNANIMIDAD |
| Ventana 10s insuficiente NotPetya | 4/6 | 5/6 | 5/6 | ✅ MAYORÍA CLARA |
| Killswitch DNS: no detectable | 5/6 | 5/6 | 6/6 | ✅ UNANIMIDAD FINAL |
| Generaliza sin reentrenamiento: NO | 6/6 | 6/6 | 6/6 | ✅ UNANIMIDAD |
| dns_query_count → P2/P3 | 5/6 | 5/6 | 5/6 | ✅ MAYORÍA CLARA |

---

## Decisión 1 — rst_ratio y syn_ack_ratio: P1 INMEDIATO

**Veredicto: UNANIMIDAD. Decisión tomada.**

Son la firma canónica de scanning SMB con alta tasa de fallos.
WannaCry genera RST > 50–80% de SYN (hosts no vulnerables rechazan el 445).
Implementación: < 20 líneas en `FlowStatistics`. Derivable de contadores ya existentes.

**Prerequisito crítico:** implementar ANTES de generar cualquier dataset sintético
de ransomware. Si los datos sintéticos no incluyen ratios correctos, el
reentrenamiento será subóptimo.

### Implementación de referencia (C++20) — versión final

Incorpora clipping a [0,1] recomendado por Claude (ronda validación) para mitigar
artefactos de captura: SYN retransmitidos, RST de middleboxes, flows truncados.

```cpp
// FlowStatistics.hpp
float rst_ratio() const {
    const float denom = static_cast<float>(syn_flag_count);
    return denom > 0.0f
        ? std::min(
            static_cast<float>(rst_flag_count) / denom,
            1.0f)
        : 0.0f;
}

float syn_ack_ratio() const {
    const float denom = static_cast<float>(syn_flag_count);
    return denom > 0.0f
        ? std::min(
            static_cast<float>(ack_flag_count) / denom,
            1.0f)
        : 0.0f;
}
```

> "Ratios are clipped to [0,1] to mitigate retransmission and
> mid-flow capture artifacts common in NAT and load-balancer environments."

### Tests unitarios requeridos (antes de merge)

```
SYN=100, RST=80              → rst_ratio = 0.80  ✅
SYN=0                        → rst_ratio = 0.00  ✅ (no división por cero)
SYN=100, RST=0               → rst_ratio = 0.00  ✅
SYN=100, RST=150             → rst_ratio = 1.00  ✅ (clipped — middlebox artifact)
SYN=10,  ACK=10,  RST=0      → syn_ack_ratio = 1.00 ✅ (tráfico normal)
SYN=100, ACK=2,   RST=85     → syn_ack_ratio = 0.02 ✅ (scanning masivo)
SYN=50,  ACK=0               → syn_ack_ratio = 0.00 ✅ (SYN sin respuesta)
```

### Paso adicional antes de dataset sintético (recomendación Grok)

```bash
# Validar distribución de rst_ratio en tráfico benigno real ANTES de generar sintéticos
# El mayor riesgo no es no detectar WannaCry — es romper producción con FPs
# en redes con WSUS, backups, SCCM u otras herramientas administrativas Windows
```

---

## Decisión 2 — Ventana temporal WINDOW_NS

**Veredicto: MAYORÍA CLARA. Decisión tomada.**

- **WannaCry:** WINDOW_NS=10s SUFICIENTE. Escaneo explosivo (128 hilos,
  cientos de conexiones/segundo) → burst capturado completo en ventana.

- **NotPetya:** WINDOW_NS=10s INSUFICIENTE para el patrón completo.
  Lateral movement puede durar minutos a 50–200 conexiones/segundo.

**Decisión arquitectónica:**
- Mantener WINDOW_NS=10s para fast path (latencia y memoria acotadas).
- Añadir en PHASE2 agregador secundario de 60s en hilo separado (no en fast path)
  para features de "escaneo sostenido" que alimenten al ML Detector en paralelo.

**Restricción crítica del agregador 60s (DeepSeek, ronda validación):**
El agregador secundario DEBE operar sobre el mismo espacio de entidad que el
fast path (clave de agregación: `src_ip` mínimo). Si no comparte identidad
de flow/host, se pierda correlación temporal real y el modelo aprende artefactos.

```
aggregation_key = src_ip (mínimo)
opcional: src_ip + subnet / role / vlan
```

> "The 60s aggregator MUST operate on the same entity space as the 10s
> fast-path (src_ip-based), otherwise temporal features become non-comparable."

**Backlog generado:** `FEAT-WINDOW-2: agregador 60s para NotPetya/APT detection`

---

## Decisión 3 — Killswitch DNS detectable sin DPI

**Veredicto: UNANIMIDAD FINAL (6/6 en ronda validación). CERRADO.**

**El killswitch DNS de WannaCry NO es detectable con la arquitectura actual.**

### Deliberación completa

Gemini propuso firma compuesta: query DNS → burst SMB inmediato como proxy.

**Problema 1 — FPR estadístico:**
El patrón DNS→SMB ocurre constantemente en tráfico Windows legítimo (clientes
conectando a servidores de ficheros, WSUS, SCCM, herramientas de administración).
En un hospital, esa secuencia ocurre decenas de veces por hora en tráfico benigno.

**Problema 2 — La firma corregida no añade nada:**
La versión precisa sería: `DNS + rst_ratio > 0.5 + unique_dst_ips_count > umbral`.
Pero esa propagación ya es detectable sin DNS. El DNS no aporta señal adicional.

**Problema 3 — Confusión conceptual:**
La firma no detecta el killswitch. Detecta la propagación cuando el killswitch falló.
Si el killswitch funciona, WannaCry se detiene solo — no es un problema operacional.

**Argumento information-theorético (Claude, ronda validación):**

> "From an information-theoretic perspective, a single DNS query without
> payload inspection carries insufficient entropy to distinguish malicious intent."

Esto eleva el argumento de "ingeniería práctica" a "limitación fundamental".

### Texto para el paper (§10 Limitaciones)

> "The WannaCry killswitch domain is undetectable at network layers 3/4 without
> deep packet inspection. From an information-theoretic perspective, a single DNS
> query without payload inspection carries insufficient entropy to distinguish
> malicious intent. A compound heuristic (DNS query followed by SMB burst) was
> considered but rejected: the pattern occurs routinely in legitimate Windows
> administrative traffic, producing unacceptable false positive rates in production
> environments. Furthermore, the propagation phase detectable via this heuristic
> is already captured by `rst_ratio` and `connection_rate` without DNS correlation.
> This architectural constraint is deliberate — DPI is excluded to preserve privacy
> and maintain sub-microsecond latency. WannaCry detection relies on propagation
> behavior, which is fully observable at L3/4."

---

## Decisión 4 — Generalización sin reentrenamiento

**Veredicto: UNANIMIDAD. El modelo actual NO generaliza suficientemente.**

Estimaciones del Consejo (Recall sin reentrenamiento):
- WannaCry: ~0.80–0.90
- NotPetya: ~0.60–0.75

**Etiqueta requerida para el paper (Claude, ronda validación):**
Estas estimaciones son hipótesis preliminares, no métricas validadas.

```
Expected Recall (preliminary hypothesis, pending experimental validation)
```

Sin esta etiqueta los reviewers atacarán overconfidence. Con ella, el argumento
es honesto y defendible.

**Por qué no generaliza:**

| Característica | CTU-13 Neris (entrenamiento) | WannaCry/NotPetya (objetivo) |
|---|---|---|
| Patrón temporal | Beaconing periódico | Burst explosivo único |
| RST/SYN ratio | Bajo (conexiones establecidas) | Alto (scanning fallido) |
| Diversidad de puertos | Variable (IRC ports) | Concentrado en 445/135/139 |
| Conexiones exitosas | Alta proporción | Muy baja (WannaCry) / media (NotPetya) |

**Espacio compartido** (por qué detecta algo sin reentrenamiento):
`connection_rate`, `unique_dst_ips_count`, `flow_iat_mean` — anomalías de volumen
genéricas que tanto Neris como ransomware SMB generan.

**Texto para el paper (§10 Limitaciones):**
> "The model trained on CTU-13 Neris partially generalizes to SMB-propagating
> ransomware (estimated Recall 0.70–0.85 without retraining — preliminary hypothesis,
> pending experimental validation). Achieving F1 > 0.90 requires retraining with
> data modeling lateral scanning patterns and elevated RST/SYN ratios. The
> `rst_ratio` feature is critical for this generalization and is scheduled for
> implementation in PHASE2."

---

## Tabla de features — Decisiones de roadmap

### Tier 1 — P1 INMEDIATO (antes de datasets sintéticos)

| Feature | Estado actual | Acción |
|---|---|---|
| `rst_ratio` | Sentinel (-9999.0f) | **Implementar en FlowStatistics** |
| `syn_ack_ratio` | Sentinel (-9999.0f) | **Implementar en FlowStatistics** |

### Tier 2 — P2 PHASE2 (después de rst_ratio, antes de reentrenamiento)

| Feature | Tipo | Justificación |
|---|---|---|
| `port_diversity_ratio` | Derivada (unique_ports/unique_ips) | WannaCry: ratio bajo (445 dominante). Bajo coste. |
| `new_dst_ip_rate` | Multi-flow | Captura velocidad de propagación mejor que conteo absoluto. Ver nota memoria. |
| `dst_port_445_ratio` | Derivada | Especialización SMB sin DPI. Alto consenso. |
| `FEAT-WINDOW-2` (60s) | Arquitectural | Para NotPetya/APT lateral movement lento. |

> ⚠️ **Nota implementación `new_dst_ip_rate` (Claude + DeepSeek, ronda validación):**
> No usar `std::unordered_set` sin control de cardinalidad. Bajo scanning masivo,
> la explosión de RAM es O(n) y puede ser catastrófica en hardware de hospital.
> Usar estructuras aproximadas:
>
> ```
> Implementation hint: Use approximate cardinality structures
> (e.g., HyperLogLog or bounded LRU set) to avoid unbounded memory
> growth under scanning conditions.
> ```

### Tier 3 — P3 BACKLOG (post-paper, enterprise)

| Feature | Tipo | Nota |
|---|---|---|
| `dns_query_count` | Multi-flow | Valor solo en correlación. No primaria. |
| `smb_connection_burst` (1s) | Temporal | Interesante, requiere evaluación de overhead. |
| `wmi_activity_proxy` | Multi-flow | NotPetya específico. Más ingeniería. |

### Descartadas

| Feature | Razón |
|---|---|
| `ICMP_unreachable_rate` | Solo Gemini. Requiere ICMP monitoring adicional. Coste desproporcionado. |
| `lateral_movement_score` | Demasiado heurístico sin base empírica. Aplazar a enterprise. |
| `tcp_window_size_value` | Requiere inspección de payload TCP. Fuera del alcance L3/4. |
| Firma compuesta DNS→SMB | FPR inaceptable. Propagación ya cubierta por rst_ratio. Descartada. |

---

## Insight arquitectónico del Consejo

**WannaCry = combinación de dos tipos de señal:**

```
Features de "fracaso"    +    Features de "propagación"
────────────────────────────────────────────────────
rst_ratio                     unique_dst_ips_count
syn_ack_ratio                 new_dst_ip_rate
failed_connection_ratio       connection_rate
                    ↓
        scanning masivo + alta tasa de fallos
                    ↓
            firma matemática de worm SMB
```

**Formalización citable (Claude, ronda validación):**

```
Let:
  F_fail   = {rst_ratio, syn_ack_ratio, failed_connection_ratio}
  F_spread = {connection_rate, unique_dst_ips_count, new_dst_ip_rate}

Then:
  WormSignature(L3/4) = f(F_fail ∪ F_spread)
```

Esta descomposición es rara en la literatura de NIDS en capa 3/4 sin DPI.
Es citable en §7 (Formal System Model) del paper como contribución conceptual propia.

---

## Plan de implementación inmediato

```
DAY 90 (hoy):
  ✅ Decisiones del Consejo #1 documentadas y cerradas (v1.1)

DAY 91-92 (próxima sesión con VM):
  [ ] Implementar rst_ratio() en FlowStatistics.hpp (con clipping)
  [ ] Implementar syn_ack_ratio() en FlowStatistics.hpp (con clipping)
  [ ] Tests unitarios: 7 casos definidos arriba
  [ ] Validar distribución en tráfico benigno real (antes de sintéticos)
  [ ] make test — confirmar 31/31 ✅
  [ ] Actualizar CSV schema (retirar sentinels, añadir 2 features reales)
  [ ] Commit en rama feature/rst-syn-ratios-phase2

ANTES DE PHASE2 DATASET:
  [ ] port_diversity_ratio (derivada, bajo coste)
  [ ] new_dst_ip_rate (multi-flow, HyperLogLog o bounded LRU)

PHASE2:
  [ ] Dataset sintético WannaCry: rst_ratio > 0.5, connection_rate > 100/s
  [ ] Dataset sintético NotPetya: multi-port, rst_ratio ~0.2–0.4
  [ ] Tráfico benigno administrativo como control negativo (WSUS, backups, SCCM)
  [ ] Reentrenamiento RandomForest
  [ ] Validación: F1 > 0.90 en CTU-13 Neris + ransomware sintético
```

---

## Nota sobre integridad del Consejo

En la primera ronda, la respuesta etiquetada como "Qwen" era una segunda
respuesta de DeepSeek. El propio modelo lo señaló explícitamente en ronda 2.
El contenido técnico es válido y converge con el resto, pero la atribución
debe corregirse.

**Acción pendiente:** lanzar Consulta #1 a Qwen individualmente con el prompt
original. Una vez recibida, añadir como «Ronda 1 — Qwen (respuesta tardía)»
y verificar si cambia algún veredicto (improbable dado el nivel de consenso).

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic) + Consejo de Sabios*
*Consulta lanzada: DAY 90 — 18 marzo 2026*
*Decisiones v1.0 finalizadas: DAY 90 — 18 marzo 2026*
*Decisiones v1.1 refinadas: DAY 90 — 18 marzo 2026 (validación final Consejo)*
*Consejo de Sabios — ML Defender (aRGus EDR)*