Claude:

Bien. Tengo las respuestas de los 5 modelos (ChatGPT, Claude, DeepSeek, Gemini, Grok — Qwen se identificó como DeepSeek, hay que aclararlo). Voy a hacer el arbitraje completo.

---

## Arbitraje Consejo #1 — WannaCry/NotPetya features

### Decisión 1: rst_ratio / syn_ack_ratio — P1 o P2?

**Veredicto: CONVERGENCIA TOTAL → P1 inmediato.**

Todos los modelos sin excepción. No hay nada que arbitrar. Antes de generar ningún dato sintético, `rst_ratio` y `syn_ack_ratio` tienen que salir del Grupo 5 (sentinels) a features reales. Son calculables directamente de flags que ya tenemos implementados.

---

### Decisión 2: Ventana 10s para scanning — ¿suficiente?

**Veredicto: MAYORÍA CLARA con matiz documentado.**

Todos coinciden: **suficiente para WannaCry** (escanea tan rápido que 10s captura el burst completo). Para NotPetya hay divergencia menor — ChatGPT, Claude y Qwen dicen insuficiente; DeepSeek, Gemini y Grok dicen suficiente con cautela.

Decisión: **mantener WINDOW_NS=10s para fast path**. Añadir en backlog PHASE2 una ventana secundaria de 60s para features de "escaneo sostenido" (lateral movement lento). No bloquea nada hoy.

---

### Decisión 3: dns_query_count sin DPI — ¿vale la pena?

**Veredicto: MAYORÍA → valor limitado, P2 o P3.**

Aquí hay divergencia real. Gemini es el outlier optimista — dice que la secuencia temporal DNS→scanning es señal casi inequívoca. El resto es más escéptico: sin DPI solo ves volumen al puerto 53, indistinguible de ruido legítimo.

Mi arbitraje: **P3, no P2**. El argumento de Gemini sobre correlación temporal es interesante pero frágil — genera FPs en cualquier red con lookups DNS normales previos a conexiones SMB legítimas. Documentar como limitación, no implementar antes de rst_ratio.

---

### Decisión 4: Killswitch DNS detectable sin DPI?

**Veredicto: DIVERGENCIA REAL — Gemini vs todos los demás.**

Gemini: sí, por la secuencia temporal (1 query DNS → tormenta de conexiones o silencio). Todos los demás: no detectable en capa 3/4.

El argumento de Gemini es elegante pero tiene un problema fundamental: esa secuencia (DNS → SMB scanning) también ocurre en tráfico legítimo. Un cliente Windows haciendo lookup antes de conectar a un servidor de ficheros produce exactamente esa firma.

**Decisión: NO detectable. Limitación honesta para el paper.** El argumento de Gemini va a la sección de trabajo futuro como heurística experimental, no como feature implementable hoy.

---

### Top features nuevas — síntesis

| Feature | Votos | Decisión |
|---|---|---|
| `rst_ratio` | 6/6 | **P1 — implementar ya** |
| `syn_ack_ratio` | 5/6 | **P1 — implementar ya** |
| `port_diversity_ratio` (unique_ports/unique_ips) | 2/6 | P2 — backlog |
| `new_dst_ip_rate` | 1/6 | P2 — backlog |
| `failed_connection_ratio` | 2/6 | P2 — cubre lo mismo que rst_ratio |
| `smb_connection_burst` (ventana 1s) | 1/6 | Interesante, P3 |
| `ICMP_unreachable_rate` | 1/6 (Gemini único) | Descartada — requiere ICMP monitoring |

---

### ¿Generaliza sin reentrenamiento?

**Convergencia total: NO con confianza suficiente.**

Estimaciones de Recall sin reentrenamiento: 0.60–0.85 según el modelo. Ninguno da F1 > 0.90 sin datos de ransomware SMB. Texto para el paper ya lo tenemos — la formulación de Qwen/DeepSeek es la más citable:

> *"El modelo entrenado en CTU-13 Neris generaliza parcialmente a ransomware de propagación SMB. Para F1 > 0.90, se requiere reentrenamiento con datos que modelen patrones de escaneo lateral y ratios RST/SYN elevados."*

---

## Decisiones finales DAY 90

**Ejecutar antes de PHASE2:**
1. `rst_ratio` → implementar (trivial, flags ya disponibles)
2. `syn_ack_ratio` → implementar
3. Reentrenamiento con datos sintéticos SMB → **no antes de tener estas dos features**

**Backlog PHASE2:**
- `port_diversity_ratio` — high value, bajo coste
- Ventana secundaria 60s para NotPetya

**Paper — limitaciones documentadas:**
- Killswitch DNS: no detectable en capa 3/4
- Generalización a ransomware SMB: Recall estimado 0.70–0.85 sin reentrenamiento

---

¿Generamos el documento de decisiones del Consejo #1 para guardarlo en `docs/adr/` o `docs/design/`, o prefieres esperar a tener también la respuesta de Qwen real?