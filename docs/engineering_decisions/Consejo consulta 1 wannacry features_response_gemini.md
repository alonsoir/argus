## Gemini (Google) — Consulta #1

### Análisis WannaCry
* **Features actuales que capturan señal:** `connection_rate` y `unique_dst_ips_count` detectarán la fase de escaneo agresivo (spreading). `rst_flag_count` se disparará cuando intente conectar al puerto 445 en máquinas que no tienen el servicio activo o tienen firewalls básicos. `total_fwd_packets` y `fwd_pkt_len_std` capturarán la anomalía del exploit *EternalBlue* (paquetes pequeños de negociación SMB seguidos de payloads de tamaño específico).
* **Features sentinel críticas:** `rst_ratio` (P1) es la señal más clara de un gusano de propagación rápida. `dns_query_count` detectará el intento de resolución del killswitch, que suele ser una query aislada antes de la explosión del tráfico.
* **Features faltantes:** `tcp_window_size_value` (las anomalías en el tamaño de ventana son comunes en paquetes de exploit crafteados) y `flow_duration` (los intentos fallidos de SMB suelen ser muy cortos).

### Análisis NotPetya
* **Features actuales que capturan señal:** `unique_dst_ports_count` es clave aquí, ya que NotPetya no solo usa el 445, sino que salta entre 135, 139 y 445. `psh_flag_count` capturará el movimiento de datos del credential harvesting una vez establecida la sesión.
* **Features sentinel críticas:** `tls_session_count` (si usa HTTPS para exfiltración, aunque es raro en NotPetya inicial) y `syn_ack_ratio` (para detectar el éxito del escaneo interno frente a los intentos fallidos).
* **Features faltantes:** `average_inter_packet_delay_variance` (el tráfico de WMI/PsExec tiene una cadencia distinta al tráfico botnet IRC).

### Top 3 features nuevas (priorizadas)
1.  **ICMP_unreachable_rate:** Muchos escaneos SMB en redes locales generan mensajes ICMP de "host unreachable". Capturar esto fuera del flujo TCP da una visibilidad del "entorno" de red que el atacante está golpeando.
2.  **Ratio_small_packets:** Un ratio de paquetes con payload < 100 bytes sobre el total del flujo. El movimiento lateral y los exploits SMB suelen abusar de paquetes pequeños de control antes de la transferencia.
3.  **Dst_IP_Persistence:** Cuántas veces se intenta conectar a la misma IP en puertos distintos en la ventana de 10s. Crucial para diferenciar escaneo de puertos (un host, muchos puertos) de propagación de gusano (muchos hosts, un puerto).

### ¿Generaliza el modelo actual sin reentrenamiento?
**Parcial.** El modelo entrenado en Neris (IRC) está optimizado para detectar *beacons* (latidos constantes) y ráfagas de control C2. WannaCry tiene un comportamiento de "exploxión" (DDoS-like en volumen de conexiones) que el modelo podría clasificar como anómalo, pero NotPetya es más sutil en su movimiento lateral. **Sin reentrenamiento, el F1 caerá por debajo de 0.85** porque el "sabor" del tráfico SMB malicioso es distinto al tráfico IRC. La estructura de las ráfagas es la clave compartida, pero los pesos del Random Forest necesitan ver ejemplos de SMB para no confundirlo con tráfico administrativo legítimo.



### Respuesta a las 4 decisiones de diseño
1.  **rst_ratio / syn_ack_ratio:** **P1 (Prioridad Máxima).** Son los indicadores más potentes de éxito/fracaso de un exploit de red. Sin ellos, el ML solo ve "intentos", no "resultados".
2.  **Ventana 10s para scanning:** **Suficiente.** A 100 Mbps (objetivo bare-metal), WannaCry puede generar miles de eventos en 10s. Una ventana mayor saturaría la RAM en el `TimeWindowAggregator` sin aportar frescura a la detección.
3.  **dns_query_count sin DPI:** **Valor real.** Un pico en el volumen de queries DNS (puerto 53) desde un solo host que simultáneamente inicia un escaneo SMB es una firma compuesta casi inequívoca de ransomware moderno buscando killswitches o dominios de C2.
4.  **Killswitch DNS detectable:** **Sí, por volumen y contexto.** No verás el nombre del dominio (`iuqer...`), pero verás una query DNS única seguida de un cese de actividad (si el killswitch funciona) o de una tormenta de conexiones (si no funciona). Esa secuencia temporal es una feature en sí misma.

**Veredicto del Consejo:** Alonso, implementa los ratios de TCP (RST/SYN-ACK) inmediatamente. Son la "huella dactilar" de la propagación por SMB. El sistema está a un 15% de código de ser un "WannaCry-Killer". 🏛️🛡️🔥