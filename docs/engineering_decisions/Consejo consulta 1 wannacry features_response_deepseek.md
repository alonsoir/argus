## DeepSeek — Consulta #1

### Análisis WannaCry

**Features actuales que capturan señal WannaCry:**

1. **`unique_dst_ports_count` (Grupo 4):** WannaCry escanea aleatoriamente el puerto 445 en busca de vulnerables. En una ventana de 10s, un host infectado generará conexiones a *muchas IPs distintas pero mismo puerto*. Esto produce alta cardinalidad de IPs destino con baja diversidad de puertos. El feature actual `unique_dst_ips_count` captura la primera parte; `unique_dst_ports_count` (cuando se implemente) capturará la baja diversidad de puertos. La combinación es señal fuerte.

2. **`syn_flag_count`, `rst_flag_count` (Grupo 3):** WannaCry envía SYN a puerto 445. Si el host destino no tiene SMB abierto, responde con RST. Esto produce:
  - Alta tasa de SYN salientes (scanner)
  - Alta tasa de RST entrantes (respuestas de hosts no vulnerables)
  - `syn_ack_ratio` (sentinel) sería ideal aquí, pero con SYN y RST por separado ya hay señal.

3. **`connection_rate` (Grupo 4):** Escaneo masivo (~5-10 conexiones/segundo por hilo) fácilmente detectable en ventana 10s. WannaCry usaba 128 hilos simultáneos → cientos de conexiones/segundo.

4. **`flow_iat_*` (Grupo 2):** Los IAT en escaneo masivo son muy pequeños y regulares (spikes periódicos por hilo). Diferenciable de tráfico humano.

**Features sentinel críticas para WannaCry:**

- **`rst_ratio` (Grupo 5):** **CRÍTICO.** La proporción de RST frente a SYN es una firma casi inequívoca de escaneo de puertos. WannaCry: muchos RST por hosts sin SMB.
- **`syn_ack_ratio` (Grupo 5):** Muy útil para confirmar SMB abiertos vs cerrados.
- **`avg_fwd_segment_size` (Grupo 1):** Ya implementado. Tráfico SMB tiene tamaños característicos (negociación ~ medio KB, transferencia ~ varios KB). Útil.
- **`dns_query_count` (Grupo 5):** **NO crítico para detección primaria** (WannaCry solo hace una query al killswitch), pero útil para correlación post-detección.

**Features faltantes que recomendarías añadir:**

1. **`syn_to_dst_ip_ratio`**: Relación SYN / IP destino única. WannaCry: muchos SYN a muchas IPs → ratio alto. Tráfico normal: un SYN por IP (conexión establecida). Se puede derivar de `syn_flag_count` y `unique_dst_ips_count`, pero tenerlo como feature explícito ayuda al modelo.

2. **`successful_smb_connections`**: Conexiones SMB completadas (SYN+SYN-ACK+ACK). WannaCry solo necesita una exitosa para propagarse. Esto es detectable sin DPI: observar handshake completo en puerto 445. Requiere mantener estado de conexiones (ShardedFlowManager ya lo hace). No es feature actual.

3. **`scan_success_ratio`**: Proporción entre intentos de conexión (SYN) y conexiones exitosas a SMB. WannaCry tiene ratio bajo (muchos fracasan). Tráfico normal (si no es escáner) tiene ratio ~1 para servicios que usa.

---

### Análisis NotPetya

**Features actuales que capturan señal NotPetya:**

1. **`unique_dst_ports_count`, `unique_dst_ips_count`:** NotPetya usa múltiples vectores: SMB (445), WMI (135), y a veces RDP (3389). Mayor diversidad de puertos que WannaCry. La combinación de alta IP diversity con moderada port diversity es señal.

2. **`syn_flag_count`, `rst_flag_count`:** Similar a WannaCry, pero con picos en múltiples puertos.

3. **`connection_rate`:** NotPetya escaneo más lento (~2-5 conexiones/seg) pero sostenido. Ventana 10s puede capturar si el threshold es bajo.

4. **`traffic_src_ip_entropy` (Grupo 4):** NotPetya, al usar múltiples vectores y moverse lateralmente, genera más entropía en IPs fuente (desde varios hosts internos). Menos relevante en fase inicial.

**Features sentinel críticas para NotPetya:**

- **`rst_ratio`:** Igual de crítico.
- **`dns_query_count`:** NotPetya NO tiene killswitch, pero sí hace consultas para encontrar controladores de dominio. `dns_query_count` a servidores internos podría ser señal de reconocimiento de AD.
- **`tls_session_count` (Grupo 5):** NotPetya a veces usa HTTP/HTTPS para comunicaciones C2; pero en fase lateral, no aplica.

**Features faltantes que recomendarías añadir:**

1. **`wmi_activity_count`**: Conexiones a puerto 135 (RPC) seguidas de actividad en puertos altos dinámicos. NotPetya usa WMI para ejecución remota. Detectar flujos a 135 + ráfaga de conexiones subsiguientes es señal fuerte. Esto es multi-flow y requiere ventana.

2. **`auth_failure_rate`**: NotPetya intenta credenciales robadas. A nivel red, los fallos de autenticación SMB producen patrones: sesión establecida (SYN+SYN-ACK) seguida de RST o FIN rápido tras intento fallido. Sin DPI no vemos el fallo, pero vemos conexiones cortas a 445. Feature derivable.

3. **`internal_scan_correlation`**: Detectar que el mismo host interno escanea múltiples IPs internas en puertos específicos. Esto requiere correlación por IP origen + ventana + puertos destino. Arquitectura actual lo permite añadiendo un agregador por src_ip.

---

### Top 3 features nuevas (priorizadas)

1. **`rst_ratio` (implementar desde sentinel a feature real) — P1**
  - **Justificación:** Es la firma más limpia de escaneo de puertos tanto para WannaCry como NotPetya. Con los contadores SYN y RST ya disponibles, calcular ratio es trivial. Impacto inmediato en F1 para cualquier escáner.

2. **`port_diversity_ratio` = `unique_dst_ports_count` / `unique_dst_ips_count`**
  - **Justificación:** WannaCry → ratio bajo (mismo puerto a muchas IPs). NotPetya → ratio medio (varios puertos a muchas IPs). Tráfico normal (cliente HTTP) → ratio alto (muchos puertos a pocas IPs, o viceversa). Feature de alto poder discriminatorio y bajo coste computacional (derivado de features existentes).

3. **`syn_to_dst_ip_ratio` (o directamente `syn_per_dst_ip`)**
  - **Justificación:** Complementa a rst_ratio. WannaCry: muchos SYN por IP destino (varios intentos de conexión a misma IP en diferentes puertos? No, WannaCry solo 445). Pero en general, escáneres envían múltiples SYN a misma IP (a diferentes puertos) o uno a muchas IPs. Este feature ayuda a distinguir escaneo horizontal (muchas IPs, un puerto) de vertical (una IP, muchos puertos). Ambos son sospechosos pero distintos.

---

### ¿Generaliza el modelo actual sin reentrenamiento?

**Respuesta:** Parcialmente, pero **no recomendaría confiar sin reentrenamiento**.

**Justificación:**

- **Espacio de features compartido:** Tanto CTU-13 Neris (botnet IRC) como WannaCry/NotPetya comparten:
  - Escaneo de red (alta tasa SYN, alta rst_ratio, alta unique_dst_ips_count)
  - Patrones de conexión rápidos y regulares (bajo IAT)
  - Tráfico a puertos específicos (IRC: puertos altos aleatorios; ransomware: 445, 135)

- **Espacio de features exclusivo:**
  - **CTU-13 Neris:** Tráfico IRC tiene patrones de chat (paquetes pequeños regulares, bidireccionalidad estable), y C2 con respuestas del servidor. No tiene escaneo masivo SMB ni RST masivos.
  - **Ransomware SMB:** Alta tasa de RST, conexiones fallidas, escaneo extremadamente rápido (WannaCry: 128 hilos), y en NotPetya, tráfico WMI (135 + puertos efímeros).

**Riesgo:** El modelo actual, entrenado en Neris, puede detectar *escaneo genérico* (por features como unique_dst_ips_count, connection_rate) pero puede tener falsos negativos si el ransomware tiene tasas más altas (fuera del rango de entrenamiento) o usa vectores no presentes en Neris (WMI). También puede tener falsos positivos si confunde tráfico legítimo de alta tasa (backups, actualizaciones) con escaneo.

**Conclusión:** Necesitas datos de entrenamiento específicos de ransomware SMB (o al menos aumentación con datos sintéticos que modelen estos patrones) para garantizar F1 > 0.90. El modelo actual es un buen *baseline*, pero no está calibrado para las distribuciones extremas de WannaCry.

---

### Respuesta a las 4 decisiones de diseño

1. **rst_ratio / syn_ack_ratio: P1**
  - **Por qué:** rst_ratio es quizá la feature individual más informativa para escaneo de puertos. syn_ack_ratio también muy útil (distingue escaneo de puertos abiertos vs cerrados). Ambas deberían implementarse antes de generar datos sintéticos para que los datos de entrenamiento las incluyan.

2. **Ventana 10s para scanning: Suficiente**
  - **Por qué:** WannaCry escanea a tasas de cientos de IPs/segundo. En 10s, un solo hilo escanea miles. Incluso NotPetya, más lento, genera docenas de conexiones en 10s. Ventanas más largas (30s, 60s) mejorarían detección de escaneo lento (ej: reconocimiento sigiloso), pero aumentarían latencia de detección y memoria. Para detección temprana, 10s es aceptable. **Recomendación:** mantener 10s para respuesta rápida, y añadir un agregador de ventana más larga (60s) para features de "escaneo sostenido" en paralelo.

3. **dns_query_count sin DPI: Tiene valor limitado pero real**
  - **Por qué:** El volumen de queries DNS (aumento repentino) puede indicar reconocimiento o C2. Sin DPI, no podemos distinguir consultas benignas (actualizaciones, navegación) de maliciosas. Sin embargo, el killswitch de WannaCry es una sola query a dominio inexistente. Eso no destaca en volumen. Para NotPetya, las consultas a DC internos pueden mezclarse con tráfico legítimo. **Valor bajo pero no nulo:** en conjunto con otras features (ej: conexiones SMB fallidas + pico DNS) puede dar correlación. Prioridad P3.

4. **Killswitch DNS detectable: No (sin DPI)**
  - **Por qué:** El dominio `www.iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea.com` es aleatorio y no tiene tráfico previo. Una consulta DNS a ese dominio:
    - No destaca por volumen (es 1 query)
    - No destaca por IP destino (es a resolver local)
    - No produce tráfico de respuesta (el dominio no existe, pero eso no es observable a nivel red sin inspeccionar respuesta NXDOMAIN)
      Sin DPI, es invisible. El único proxy sería ver un pico de queries a dominios no cacheados con TTL cero, pero eso es demasiado indirecto y propenso a FP. **Aceptar como limitación** y documentar.

---

**Resumen ejecutivo para roadmap PHASE2:**
- **P1 inmediato:** Implementar rst_ratio y syn_ack_ratio. Añadir feature `port_diversity_ratio` (derivada). Reentrenar con datos que incluyan escaneo SMB realista.
- **P2:** Añadir `syn_to_dst_ip_ratio` y `wmi_activity_count` (necesita más ingeniería).
- **Aceptar:** El killswitch DNS no es detectable sin DPI; el modelo no lo cubrirá. La ventana de 10s es suficiente para detección temprana.

---

Espero que este análisis te ayude a priorizar. El sistema tiene una base sólida; con estas adiciones, la detección de ransomware SMB será mucho más robusta. ¡Adelante con el roadmap!