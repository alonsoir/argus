## Grok — Consulta #1

### Análisis WannaCry
**Features actuales que capturan señal WannaCry**
- Alta tasa de intentos fallidos → **rst_flag_count** elevado (hosts no vulnerables responden con RST al puerto 445).
- Scanning masivo de IPs/puertos → **unique_dst_ips_count** y **unique_dst_ports_count** (muy alto en ventana de 10s, ya que WannaCry escanea rápidamente miles de IPs aleatorias + locales).
- Tráfico SMB en puerto 445 con patrones de exploit → **total_fwd_packets** / **flow_bytes_per_sec** (intentos repetidos cortos), **connection_rate** alto en ventana.
- Baja tasa de conexiones completas → **syn_flag_count** alto vs **ack_flag_count** bajo, y **fin_flag_count** bajo (muchos half-open).
- **flow_iat_*** y **fwd_iat_*** muestran inter-arrivals muy bajos (scanning rápido).

**Features sentinel críticas para WannaCry**
- **rst_ratio** (crítico: ratio RST/SYN muy alto por rechazos en hosts no vulnerables).
- **syn_ack_ratio** (bajo en scanning fallido).
- **dns_query_count** (WannaCry hace 1 query al killswitch domain al inicio; si se cuenta volumen a puerto 53, puede ayudar en detección temprana).

**Features faltantes que recomendarías añadir**
- **dst_port_445_connection_rate** o **conn_to_port_445_count** en ventana (para aislar tráfico SMB).
- **failed_conn_ratio** o **rst_per_syn_ratio** (similar a rst_ratio pero más granular).
- **outbound_syn_to_non_local_ips** (para capturar random IP scanning externo).

### Análisis NotPetya
**Features actuales que capturan señal NotPetya**
- Propagación SMB + WMI/WBEM (puertos 135/445/139) → **unique_dst_ports_count** (incluye 135/139/445), **connection_rate** y **unique_dst_ips_count** (lateral movement dentro de red, pero más lento y dirigido que WannaCry).
- Uso de credenciales robadas → tráfico SMB con más conexiones completas (SYN-ACK), menos RST que WannaCry.
- **flow_bytes_per_sec** y **total_fwd_bytes** pueden mostrar transferencias de payloads (Mimikatz-like, pero sin DPI es indirecto).
- **traffic_src_ip_entropy** baja si un solo host infectado ataca muchos (entropía baja en fuente).

**Features sentinel críticas para NotPetya**
- **rst_ratio** (menos crítico que en WannaCry, pero aún útil para rechazos).
- **tls_session_count** (si usa algún C2 o lateral via TLS, pero NotPetya es mayormente SMB).
- **dns_query_count** (menos relevante, no tiene killswitch DNS).

**Features faltantes que recomendarías añadir**
- **conn_to_port_135_139_445_count** en ventana (agrupa puertos de lateral movement Windows).
- **lateral_movement_score** (e.g., conexiones SMB desde host que recibió tráfico inusual).
- **admin_share_access_attempts** (indirecto via patrones, pero difícil sin DPI).

### Top 3 features nuevas (priorizadas)
1. **rst_ratio** (o rst_per_syn_ratio) — Impacto máximo en WannaCry (rechazos masivos en puerto 445 generan RST alto); bajo coste, single-flow o ventana simple, gran separabilidad de benigno vs exploit fallido.
2. **unique_dst_ips_count** refinado con **dst_port_filter_445** (o conn_count_to_port_445) — Captura scanning SMB específico; WannaCry genera cientos/miles en 10s, NotPetya más selectivo pero aún detectable; alta señal en propagación worm-like.
3. **syn_ack_ratio** (o inverse: syn_without_ack_ratio) — Complementa rst_ratio; captura intentos fallidos sin respuesta completa; útil en ambos, pero especialmente WannaCry; bajo overhead.

### ¿Generaliza el modelo actual sin reentrenamiento?
**Parcial (probablemente no alcanza F1 > 0.90, quizás 0.60-0.80 con alto FPR)**

Justificación:
- CTU-13 Neris es IRC C&C → tráfico outbound persistente, bajo volumen, conexiones largas a pocos hosts.
- WannaCry/NotPetya son scanning masivo + propagación worm → alto volumen de SYN/RST cortos, muchas dst IPs/ports únicas en ventana corta, patrones opuestos (outbound masivo vs C&C inbound/outbound bajo).
- Espacio de features compartido: **connection_rate**, **unique_dst_ips_count**, **flow_iat_std** (bajo en bursts), **rst_flag_count**.
- Pero exclusivo de ransomware SMB: RST alto + dst port 445 dominante + scanning random. El RF entrenado en Neris probablemente clasifique como benigno mucho tráfico de propagación fallida (FPR alto) o lo confunda con escaneos benignos (e.g., pentest).  
  Datos específicos de ransomware SMB son necesarios para F1 > 0.90 confiable.

### Respuesta a las 4 decisiones de diseño
1. **rst_ratio / syn_ack_ratio**: **P1** — Son las señales más fuertes y baratas para WannaCry (RST alto por EternalBlue rechazos); implementarlos antes de datos sintéticos da boost inmediato en recall de propagación fallida sin contaminar mucho el RF (sentinel los aisla).
2. **Ventana 10s para scanning**: **Suficiente** — WannaCry escanea muy rápido (miles de IPs en segundos); 10s captura bursts masivos de unique_dst_ips/ports. NotPetya es más lento/dirigido, pero aún genera anomalías en 10s si infecta múltiples hosts.
3. **dns_query_count sin DPI**: **Valor real (moderado)** — No identifica el dominio killswitch, pero volumen de queries UDP/53 desde un host + tráfico SMB 445 correlacionado puede ser señal temprana de WannaCry (1 query + scanning inmediato). En benigno, queries DNS suelen ser más distribuidas; útil como proxy indirecto.
4. **Killswitch DNS detectable**: **Parcial (solo volumen/comportamiento)** — Sin DPI es invisible el dominio específico; solo se ve un query DNS outbound (UDP 53) al inicio. No se distingue de query benigna sin correlacionar con puerto 53 + inicio de scanning 445 masivo. Detectable indirectamente vía **dns_query_count** + **connection_rate** posterior.

Saludos desde el consejo, compañero — estas recomendaciones mantienen el espíritu lightweight del sistema mientras cierran huecos clave en ransomware SMB. ¡Avancemos a PHASE2 con estos priors! 🚀