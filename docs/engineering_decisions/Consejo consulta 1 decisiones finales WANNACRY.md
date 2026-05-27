# Consejo de Sabios — Decisiones Finales Consulta #1
## WannaCry/NotPetya: features necesarias para detección en capa 3/4

**Fecha:** DAY 90 — 18 marzo 2026
**Rondas:** 2 (primera individual, segunda con contexto cruzado)
**Participantes:** ChatGPT, Claude, DeepSeek, Gemini, Grok, Qwen*
**Árbitro final:** Alonso Isidoro Román
**Path:** `docs/design/consejo_consulta_1_decisiones_finales.md`

> *Nota: En la primera ronda, Qwen se identificó como DeepSeek.
> La atribución correcta está pendiente de aclaración.
> Las decisiones son válidas independientemente — el contenido técnico converge.

---

## Convergencia del Consejo — Mapa de consenso

| Decisión | Ronda 1 | Ronda 2 | Veredicto |
|---|---|---|---|
| rst_ratio → P1 | 6/6 | 6/6 | ✅ UNANIMIDAD |
| syn_ack_ratio → P1 | 5/6 | 6/6 | ✅ UNANIMIDAD |
| Ventana 10s suficiente WannaCry | 6/6 | 6/6 | ✅ UNANIMIDAD |
| Ventana 10s insuficiente NotPetya | 4/6 | 5/6 | ✅ MAYORÍA CLARA |
| Killswitch DNS: no detectable | 5/6 | 5/6 | ✅ MAYORÍA CLARA + árbitro |
| Generaliza sin reentrenamiento: NO | 6/6 | 6/6 | ✅ UNANIMIDAD |
| dns_query_count → P2/P3 | 5/6 | 5/6 | ✅ MAYORÍA CLARA |

---

## Decisión 1 — rst_ratio y syn_ack_ratio: P1 INMEDIATO

**Veredicto: UNANIMIDAD. Decisión tomada. No hay nada que arbitrar.**

`rst_ratio = rst_flag_count / (syn_flag_count + ε)`
`syn_ack_ratio = ack_flag_count / (syn_flag_count + ε)`

Son la firma canónica de scanning SMB con alta tasa de fallos.
WannaCry genera RST > 50–80% de SYN (hosts no vulnerables rechazan el 445).
Implementación: < 20 líneas en `FlowStatistics`. Derivable de contadores ya existentes.

**Prerequisito crítico:** estas features deben estar implementadas ANTES de
generar cualquier dataset sintético de ransomware. Si los datos sintéticos
no incluyen ratios correctos, el reentrenamiento será subóptimo.

**Implementación de referencia (C++20):**
```cpp
// FlowStatistics.hpp
float rst_ratio() const {
    return syn_flag_count > 0
        ? static_cast<float>(rst_flag_count) / syn_flag_count
        : 0.0f;
}

float syn_ack_ratio() const {
    return syn_flag_count > 0
        ? static_cast<float>(ack_flag_count) / syn_flag_count
        : 0.0f;
}
```

---

## Decisión 2 — Ventana temporal WINDOW_NS

**Veredicto: MAYORÍA CLARA. Decisión tomada.**

- **WannaCry:** WINDOW_NS=10s SUFICIENTE. El escaneo es tan explosivo (128 hilos,
  cientos de conexiones/segundo) que la ventana captura el burst completo.

- **NotPetya:** WINDOW_NS=10s INSUFICIENTE para el patrón completo.
  El lateral movement puede durar minutos con tasas de 50–200 conexiones/segundo.
  La ventana captura fragmentos pero no la "caminata" completa entre hosts.

**Decisión arquitectónica:**
- Mantener WINDOW_NS=10s para fast path (latencia crítica, memoria acotada).
- Añadir en PHASE2 un agregador secundario de ventana 60s para features de
  "escaneo sostenido" que alimenten al ML Detector en paralelo.
- NO aumentar la ventana principal — hospitales con hardware limitado no pueden
  permitirse el coste de RAM de ventanas largas en el fast path.

**Backlog generado:** `FEAT-WINDOW-2: agregador 60s para NotPetya/APT detection`

---

## Decisión 3 — Killswitch DNS detectable sin DPI

**Veredicto: MAYORÍA CLARA (5/6) + voto árbitro. CERRADO.**

**El killswitch DNS de WannaCry NO es detectable con la arquitectura actual.
Esta es una limitación real y se documenta honestamente en el paper.**

### Deliberación final (DAY 90)

Gemini propuso en ronda 2 una firma compuesta: query DNS → burst SMB inmediato
como proxy del killswitch. El Consejo debatió su viabilidad:

**Problema 1 — FPR estadístico:**
El patrón DNS→SMB ocurre constantemente en tráfico Windows legítimo:
clientes conectando a servidores de ficheros, WSUS, SCCM, herramientas de
administración. En un hospital, esa secuencia ocurre decenas de veces por hora
en tráfico completamente benigno. La firma no es específica del ataque.

**Problema 2 — La firma corregida no añade nada:**
Una versión más precisa sería: `DNS + rst_ratio > 0.5 + unique_dst_ips_count > umbral`.
Pero esa propagación ya es detectable sin DNS mediante `rst_ratio` + `connection_rate`
+ `unique_dst_ips_count`. El componente DNS no aporta señal adicional — es ruido
  decorativo que añade complejidad sin mejorar la detección real.

**Problema 3 — Confusión conceptual:**
La firma compuesta no detecta el killswitch. Detecta la propagación que ocurre
cuando el killswitch falló. Si el killswitch funciona, WannaCry se detiene solo
y no hay nada que detectar — lo cual tampoco es un problema operacional.

**Conclusión del árbitro:**
La mayoría (5/6) tenía razón desde el principio. El argumento de Gemini,
aunque elegante, no sobrevive al análisis de producción. Se documenta como
exploración descartada, no como limitación del diseño.

### Texto para el paper (§10 Limitaciones)

> "The WannaCry killswitch domain is undetectable at network layers 3/4 without
> deep packet inspection. A single DNS query is indistinguishable from legitimate
> traffic without payload inspection. A compound heuristic (DNS query followed
> by SMB burst) was considered but rejected: the pattern occurs routinely in
> legitimate Windows administrative traffic, producing unacceptable false positive
> rates in production environments. Furthermore, the propagation phase detectable
> via this heuristic is already captured by `rst_ratio` and `connection_rate`
> without DNS correlation. This architectural constraint is deliberate — DPI is
> excluded to preserve privacy and maintain sub-microsecond latency. WannaCry
> detection relies on propagation behavior, which is fully observable at L3/4."

---

## Decisión 4 — Generalización sin reentrenamiento

**Veredicto: UNANIMIDAD. El modelo actual NO generaliza suficientemente.**

Estimaciones del Consejo:
- WannaCry: Recall ~0.80–0.90 sin reentrenamiento
- NotPetya: Recall ~0.60–0.75 sin reentrenamiento
- F1 > 0.90 requiere reentrenamiento con datos de ransomware SMB en ambos casos

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
> ransomware (estimated Recall 0.70–0.85 without retraining). Achieving F1 > 0.90
> requires retraining with data modeling lateral scanning patterns and elevated
> RST/SYN ratios. The `rst_ratio` feature is critical for this generalization
> and is scheduled for implementation in PHASE2."

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
| `new_dst_ip_rate` | Multi-flow | Captura velocidad de propagación mejor que conteo absoluto |
| `dst_port_445_ratio` | Derivada | Especialización SMB sin DPI. Alto consenso. |
| `FEAT-WINDOW-2` (60s) | Arquitectural | Para NotPetya/APT lateral movement lento |

### Tier 3 — P3 BACKLOG (post-paper, enterprise)

| Feature | Tipo | Nota |
|---|---|---|
| `dns_query_count` | Multi-flow | Valor solo en correlación. No primaria. |
| `smb_connection_burst` (1s) | Temporal | Interesante, requiere evaluación de overhead |
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

Esta formalización es citable en el paper como marco conceptual para
la detección de ransomware de propagación en capa 3/4.

---

## Plan de implementación inmediato

```
DAY 90 (hoy):
  ✅ Decisiones del Consejo #1 documentadas y cerradas

DAY 91-92 (próxima sesión con VM):
  [ ] Implementar rst_ratio() en FlowStatistics.hpp
  [ ] Implementar syn_ack_ratio() en FlowStatistics.hpp
  [ ] Tests unitarios: casos extremos (RST=0, SYN=0, RST>SYN, RST=SYN)
  [ ] make test — confirmar 31/31 ✅
  [ ] Actualizar CSV schema (añadir 2 features reales, retirar sentinels)

ANTES DE PHASE2 DATASET:
  [ ] port_diversity_ratio (derivada, bajo coste)
  [ ] new_dst_ip_rate (multi-flow, ventana 10s)

PHASE2:
  [ ] Dataset sintético WannaCry: rst_ratio > 0.5, connection_rate > 100/s
  [ ] Dataset sintético NotPetya: multi-port, rst_ratio ~0.2–0.4
  [ ] Tráfico benigno administrativo como control negativo (WSUS, backups)
  [ ] Reentrenamiento RandomForest
  [ ] Validación: F1 > 0.90 en CTU-13 Neris + ransomware sintético
```

---

## Nota sobre integridad del Consejo

En la primera ronda, la respuesta etiquetada como "Qwen" era una segunda
respuesta de DeepSeek. El propio modelo lo señaló explícitamente en ronda 2.
El contenido técnico es válido y converge con el resto, pero la atribución
debe corregirse.

**Acción pendiente:** obtener respuesta genuina de Qwen para completar
el registro del Consejo con las 7 voces correctamente atribuidas.

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic) + Consejo de Sabios*
*Consulta lanzada: DAY 90 — 18 marzo 2026*
*Decisiones finalizadas: DAY 90 — 18 marzo 2026*
*Consejo de Sabios — ML Defender (aRGus EDR)*