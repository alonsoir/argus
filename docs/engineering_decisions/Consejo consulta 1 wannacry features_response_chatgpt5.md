## ChatGPT — Consulta #1

### Análisis WannaCry

**Señal capturada con features actuales:**

* **Scanning SMB masivo (puerto 445):**

  * `unique_dst_ips_count` → crecimiento explosivo en ventana
  * `connection_rate` → alto número de conexiones/segundo
  * `flow_packets_per_sec` → flujos muy cortos pero intensos
* **Patrón de conexiones fallidas (hosts no vulnerables):**

  * `rst_flag_count` → elevado en respuestas
  * `syn_flag_count` → alto volumen de intentos
* **Asimetría de tráfico:**

  * `dl_ul_ratio` + `total_fwd_packets` ≫ `total_bwd_packets`
* **Temporalidad agresiva:**

  * `flow_iat_mean` bajo + `flow_iat_std` bajo (ráfagas rápidas)

**Features sentinel críticas:**

* `rst_ratio` → clave para distinguir scanning agresivo vs tráfico legítimo
* `syn_ack_ratio` → identifica falta de handshakes completos
* `dns_query_count` → útil para detectar comportamiento anómalo agregado (aunque limitado)

**Features faltantes recomendadas:**

* **`failed_connection_ratio` (RST / SYN o SYN sin ACK)**
  Más robusta que métricas individuales
* **`dst_port_445_ratio` (proporción de tráfico hacia 445)**
  Focaliza comportamiento SMB sin DPI
* **`new_dst_ip_rate` (IPs nuevas por segundo)**
  Mejora señal de propagación

---

### Análisis NotPetya

**Señal capturada con features actuales:**

* **Movimiento lateral SMB/WMI:**

  * `unique_dst_ips_count` → incremento moderado pero sostenido
  * `connection_rate` → menor que WannaCry pero persistente
* **Uso de múltiples puertos (135, 139, 445):**

  * `unique_dst_ports_count` → señal relevante
* **Distribución temporal menos agresiva:**

  * `flow_iat_mean` mayor que WannaCry
* **Asimetría de tráfico:**

  * similar a WannaCry pero menos extrema

**Limitaciones importantes:**

* Credential harvesting (tipo Mimikatz) → completamente invisible en red L3/L4
* Propagación más “legítima-looking” → difícil separar de administración real

**Features sentinel críticas:**

* `syn_ack_ratio` → distingue conexiones legítimas vs barridos
* `rst_ratio` → menos dominante pero útil
* `tls_session_count` → puede aportar señal si hay actividad lateral cifrada

**Features faltantes recomendadas:**

* **`lateral_movement_pattern_score` (heurística multi-flow)**
  Basado en secuencias repetitivas de conexión interna
* **`internal_dst_ip_ratio` (intra-subred vs externo)**
  Clave para detectar movimiento lateral
* **`port_sequence_entropy`**
  Detecta patrones automatizados en uso de puertos

---

### Top 3 features nuevas (priorizadas)

1. **`failed_connection_ratio` (SYN sin ACK / total SYN)**

  * Máxima señal para scanning tipo WannaCry
  * Generaliza bien a múltiples worms/exploits
  * Bajo coste (derivable de flags existentes)

2. **`new_dst_ip_rate` (IPs únicas nuevas por segundo)**

  * Captura directamente propagación tipo worm
  * Mucho más discriminativo que `unique_dst_ips_count` en ventana fija
  * Reduce dependencia del tamaño de ventana

3. **`dst_port_445_ratio` (proporción tráfico a SMB)**

  * Permite especializar detección sin DPI
  * Muy relevante para ransomware tipo WannaCry/NotPetya
  * Bajo coste computacional

---

### ¿Generaliza el modelo actual sin reentrenamiento?

**Respuesta: No (solo parcialmente, con alto riesgo de fallo).**

**Justificación:**

* **CTU-13 Neris (IRC botnet):**

  * Tráfico persistente, C&C, patrones relativamente estables
  * Baja explosividad en scanning lateral
* **WannaCry/NotPetya:**

  * Worms auto-propagantes → comportamiento altamente explosivo
  * Dominado por scanning + explotación, no por C&C

**Conclusión técnica:**

* El espacio de features **no es isomorfo**:

  * Botnet IRC → patrones de comunicación
  * Worm SMB → patrones de propagación
* El modelo puede detectar “anomalía extrema” (WannaCry),
  pero fallará en:

  * NotPetya (más sigiloso)
  * Falsos positivos en tráfico legítimo intensivo (backup, IT tools)

**Recomendación:**

* Reentrenamiento obligatorio con:

  * Dataset sintético controlado de scanning SMB
  * Mezcla de tráfico lateral legítimo (administración real)

---

### Respuesta a las 4 decisiones de diseño

1. **rst_ratio / syn_ack_ratio: P1**

  * Son features estructurales para distinguir:

    * scanning vs tráfico legítimo
  * Bajo coste, alto impacto inmediato
  * Especialmente críticas para WannaCry

---

2. **Ventana 10s para scanning: Parcialmente suficiente**

  * WannaCry:

    * Sí, suficiente (alta velocidad)
  * NotPetya:

    * No siempre (movimiento lateral más lento)

   **Recomendación:**

  * Mantener 10s + añadir `new_dst_ip_rate`
  * Evitar aumentar ventana (impacto en memoria/latencia)

---

3. **dns_query_count sin DPI: Valor limitado pero útil**

  * No detecta dominio específico (killswitch)
  * Pero sí:

    * ráfagas anómalas de DNS
    * comportamiento previo a conexión

   **Conclusión:**

  * Valor **secundario (P2)**, no crítico para ransomware SMB

---

4. **Killswitch DNS detectable: No (sin DPI)**

  * El dominio es necesario para la señal real
  * A nivel L3/L4 solo ves:

    * tráfico a puerto 53
    * no el FQDN

   **Posible excepción (débil):**

  * correlación temporal:

    * DNS → inmediatamente sin scanning → comportamiento raro
  * pero esto es heurístico, no fiable

---

## Conclusión ejecutiva

* **WannaCry:** detectable con features actuales + 2–3 mejoras clave
* **NotPetya:** detección parcial, requiere features adicionales multi-flow
* **Gap principal:** falta de métricas de *intento fallido* y *propagación explícita*
* **Acción inmediata recomendada:**
  → Implementar `failed_connection_ratio` + `syn_ack_ratio` + `new_dst_ip_rate` antes de generar datasets PHASE2
