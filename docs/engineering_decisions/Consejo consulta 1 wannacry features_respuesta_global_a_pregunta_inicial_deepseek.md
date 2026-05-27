## DeepSeek — Consulta #1 (Respuesta como miembro del Consejo)

*Nota: Aunque en el mensaje se me atribuye como DeepSeek, asumiré que esta es mi respuesta solicitada formalmente.*

---

### Análisis WannaCry

**Features actuales que capturan señal WannaCry:**

1. **`unique_dst_ips_count` (Grupo 4):** WannaCry escanea aleatoriamente direcciones IP (tanto locales como externas) a una tasa de cientos por segundo. En ventana de 10s, esto genera valores extremadamente altos (>1000 IPs únicas), fuera de cualquier distribución benigna conocida.

2. **`connection_rate` (Grupo 4):** El worm genera conexiones masivas (~100-1000 por segundo) durante la fase de propagación. Es una de las señales más fuertes disponibles actualmente.

3. **`syn_flag_count` y `rst_flag_count` (Grupo 3):** Alta tasa de SYN salientes (intentos de conexión) y alta tasa de RST entrantes (respuestas de hosts no vulnerables). El *conteo absoluto* ya da señal, pero el *ratio* es más informativo.

4. **`flow_iat_*` (Grupo 2):** Los intervalos entre flujos son extremadamente pequeños y regulares (bursts de escaneo), diferenciables de tráfico humano o de servicios.

5. **`traffic_src_ip_entropy` (Grupo 4):** El escaneo aleatorio de IPs incrementa la entropía de destinos significativamente.

**Features sentinel críticas para WannaCry:**

- **`rst_ratio` (Grupo 5):** **CRÍTICO ABSOLUTO.** La proporción de RST respecto a SYN es la firma más limpia de escaneo de puertos con alta tasa de fallos. WannaCry: SYN masivos, RST masivos de hosts no vulnerables → ratio > 0.5. Sin este ratio, el sistema confunde tráfico de red congestionada (RST legítimos) con escaneo malicioso.

- **`syn_ack_ratio` (Grupo 5):** Muy útil para confirmar la falta de handshakes completos. WannaCry tiene ratio SYN/ACK extremadamente bajo (< 0.1) porque la mayoría de conexiones fallan antes de SYN-ACK.

- **`dns_query_count` (Grupo 5):** Secundario. WannaCry hace una única query al killswitch al inicio. En volumen, es insignificante, pero en correlación temporal con el inicio del escaneo puede aportar señal.

**Features faltantes que recomendarías añadir:**

1. **`rst_ratio` (implementar desde sentinel a feature real):** Es la prioridad máxima. Implementación trivial: `rst_flag_count / (syn_flag_count + 1e-6)`.

2. **`smb_scan_rate` (nueva):** Conexiones al puerto 445 por segundo. WannaCry genera ráfagas de 50-200 conexiones SMB en < 2 segundos. Esto es detectable incluso sin DPI porque el puerto destino es observable.

3. **`port_445_diversity` (nueva):** Número de IPs destino únicas contactadas *exclusivamente* en puerto 445. Filtra ruido de otros servicios y enfoca la señal en el vector de ataque real.

4. **`failed_connection_ratio` (nueva):** Proporción de flujos con SYN pero sin ACK posterior (incompletos). Similar a rst_ratio pero captura también conexiones que simplemente expiran sin RST.

---

### Análisis NotPetya

**Features actuales que capturan señal NotPetya:**

1. **`unique_dst_ports_count` (Grupo 4):** NotPetya usa múltiples vectores (135, 139, 445). Mayor diversidad de puertos que WannaCry. Esto es señal diferencial importante.

2. **`unique_dst_ips_count` (Grupo 4):** Escaneo más dirigido que WannaCry (menos IPs por segundo, pero más sostenido en el tiempo). Ventana de 10s captura fragmentos del patrón.

3. **`connection_rate` (Grupo 4):** Menor que WannaCry (~50-200 conexiones/segundo) pero persistente durante minutos. Detectable como anomalía sostenida.

4. **`traffic_src_ip_entropy` (Grupo 4):** Al moverse lateralmente entre hosts internos, la entropía de IPs fuente puede aumentar (múltiples hosts infectados atacando a su vez).

**Features sentinel críticas para NotPetya:**

- **`rst_ratio` (Grupo 5):** Menos crítico que en WannaCry (NotPetya es más selectivo en objetivos), pero aún útil para detectar escaneo inicial.

- **`syn_ack_ratio` (Grupo 5):** Más relevante que en WannaCry. NotPetya intenta establecer sesiones legítimas para credential harvesting y ejecución remota. Un ratio SYN/ACK anómalamente alto en ciertos puertos puede indicar éxito en establecimiento de conexiones.

- **`dns_query_count` (Grupo 5):** NotPetya consulta controladores de dominio internos (AD). Un aumento en queries DNS a servidores internos desde múltiples hosts puede indicar reconocimiento de red.

**Features faltantes que recomendarías añadir:**

1. **`wmi_activity_proxy` (nueva):** NotPetya usa WMI (puerto 135 + puertos dinámicos). Detectar flujos a 135 seguidos de ráfagas de conexiones a puertos altos desde el mismo origen en ventana corta es señal de ejecución remota.

2. **`lateral_movement_temporal` (nueva):** Patrón de "caminata" entre IPs adyacentes (ej: 192.168.1.10 → 192.168.1.11 → 192.168.1.12 en < 10s). NotPetya muestra este comportamiento; el escaneo aleatorio de WannaCry no.

3. **`internal_dns_burst` (nueva):** Volumen de queries DNS a servidores internos (dominios corporativos) desde hosts que también muestran actividad SMB anómala. Proxy para detectar reconocimiento de Active Directory.

---

### Top 3 features nuevas (priorizadas)

1. **`rst_ratio` (RST / SYN) — P1**
    - **Justificación:** Es la firma más limpia y universal para detectar escaneo de puertos con alta tasa de fallos. WannaCry: ratio > 0.5. NotPetya: ratio > 0.3 en fase inicial. Tráfico benigno: ratio < 0.1 salvo condiciones de red anómalas. Implementación trivial, impacto inmediato en F1 para cualquier escáner. **Sin este feature, el sistema tendrá FPR inaceptable en redes reales con pérdida de paquetes legítima.**

2. **`port_445_connection_burst` (conexiones a 445 por segundo) — P1**
    - **Justificación:** WannaCry genera ráfagas de 50-200 conexiones SMB por segundo durante segundos. Esto es órdenes de magnitud superior a cualquier tráfico benigno (actualizaciones Windows, backups). La ventana de 1s captura el burst mejor que la ventana de 10s agregada. Implementación: contador atómico con decay exponencial.

3. **`port_diversity_ratio` = `unique_dst_ports_count` / `unique_dst_ips_count` — P2**
    - **Justificación:** WannaCry: ratio bajo (mismo puerto a muchas IPs). NotPetya: ratio medio (varios puertos a muchas IPs). Tráfico benigno: ratio alto (cliente HTTP/HTTPS a múltiples puertos en mismo servidor, o múltiples servicios en pocos servidores). Feature de alto poder discriminatorio y bajo coste computacional (derivado de features existentes).

---

### ¿Generaliza el modelo actual sin reentrenamiento?

**Respuesta: Parcialmente — con F1 estimado < 0.85, no > 0.90.**

**Justificación técnica:**

- **Espacio de features compartido (señal detectable sin reentrenamiento):**
    - Alta tasa de conexiones (`connection_rate`)
    - Alta diversidad de IPs destino (`unique_dst_ips_count`)
    - Bajo IAT (`flow_iat_mean`)
    - Estos features permiten detectar *anomalías de volumen* que WannaCry genera. El modelo actual, entrenado en Neris, ya responde a anomalías de volumen (el C2 de Neris también genera picos, aunque de naturaleza distinta).

- **Espacio de features NO compartido (requiere reentrenamiento):**
    - **Ratio RST/SYN:** Neris tiene tráfico IRC con baja tasa de RST (conexiones establecidas). WannaCry tiene RST masivos. El modelo actual no tiene pesos calibrados para este ratio porque no existía en entrenamiento (era sentinel).
    - **Diversidad de puertos:** Neris usa puertos altos variables; WannaCry se concentra en 445; NotPetya usa 135,139,445. El modelo no ha visto esta *concentración* en puertos específicos de Windows.
    - **Patrón temporal:** Neris tiene periodicidad de beaconing; WannaCry tiene burst explosivo único. La distribución de IAT es diferente.

**Predicción cuantitativa (estimada):**
- WannaCry: Recall ~0.80-0.90 (detecta el volumen, pero puede confundir con tráfico legítimo de alta densidad si no hay rst_ratio)
- NotPetya: Recall ~0.60-0.75 (más sutil, requiere features específicos de lateral movement)
- FPR: Aumentará en entornos con herramientas administrativas legítimas (WSUS, backups, SCCM) que generan escaneo de red.

**Recomendación explícita:** No enviar a producción sin reentrenamiento con datos que incluyan:
- Escaneo SMB a diferentes tasas (10-1000 conn/sec)
- Ratios RST/SYN controlados (0.1 a 0.9)
- Múltiples puertos de lateral movement (135,139,445,3389)
- Tráfico legítimo de administración Windows como control negativo

---

### Respuesta a las 4 decisiones de diseño

1. **rst_ratio / syn_ack_ratio: P1 (implementar AHORA, antes de generar datos sintéticos)**
    - **Por qué:** Son los features más informativos para diferenciar escaneo malicioso de tráfico legítimo. Si generas datos sintéticos sin ellos, los datos serán menos realistas y el modelo suboptimizará. Además, la implementación es trivial (< 20 líneas en FlowStatistics). No hay excusa técnica para retrasarlo.

2. **Ventana 10s para scanning: Suficiente para WannaCry, INSUFICIENTE para NotPetya**
    - **WannaCry:** 10s captura el burst completo (miles de conexiones). OK.
    - **NotPetya:** El movimiento lateral puede durar minutos con tasas más bajas. Ventana de 10s captura fragmentos pero no el patrón completo de "caminata" entre hosts.
    - **Recomendación:** Mantener 10s para fast path (heurísticas de respuesta inmediata). Añadir en PHASE2 un agregador de ventana más larga (60s) para features de "escaneo sostenido" que alimenten al ML Detector. Esto permite detectar tanto bursts rápidos (WannaCry) como actividad lenta y persistente (NotPetya, APTs).

3. **dns_query_count sin DPI: Valor limitado pero NO nulo**
    - **Qué NO puede hacer:** Detectar el dominio específico del killswitch (invisible sin DPI).
    - **Qué SÍ puede hacer:** Detectar correlaciones temporales: un host que nunca hace queries DNS (o hace pocas) y de repente genera 1 query + inmediatamente después un burst SMB es una señal compuesta útil. También detectar aumentos sostenidos de queries a servidores DNS internos (reconocimiento de AD en NotPetya).
    - **Prioridad:** P2 (útil pero no crítico para detección primaria). Implementar después de rst_ratio y port_445_burst.

4. **Killswitch DNS detectable: NO (sin DPI)**
    - **Justificación técnica:** A nivel de red (capa 3/4), solo observas:
        - Un paquete UDP con destino puerto 53
        - IP origen y destino
        - Tamaño del paquete (~50-60 bytes típico)
    - El nombre del dominio (`www.iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea.com`) está en el payload DNS (capa 7). Sin inspección de payload, es completamente invisible.
    - **Proxy posible (pero débil):** Detectar que un host hace una query DNS a un dominio que no existe (respuesta NXDOMAIN) requeriría inspeccionar la respuesta DNS (también capa 7). Fuera de alcance.
    - **Conclusión:** El killswitch es indetectable en la arquitectura actual. Esto debe documentarse honestamente como limitación. No es una debilidad del diseño — es una decisión arquitectónica deliberada (no DPI por privacidad/rendimiento). La detección de WannaCry no depende del killswitch; depende del comportamiento de propagación, que SÍ es detectable.

---

### Resumen ejecutivo para roadmap PHASE2

| Feature | Prioridad | Impacto estimado | Esfuerzo |
|---------|-----------|------------------|----------|
| `rst_ratio` | **P0/P1** | Alto (WannaCry/NotPetya/escáneres) | Muy bajo |
| `port_445_connection_burst` | **P1** | Alto (WannaCry) | Bajo |
| `port_diversity_ratio` | **P2** | Medio (ambos) | Muy bajo (derivado) |
| `wmi_activity_proxy` | **P2** | Medio (NotPetya) | Medio |
| Ventana 60s adicional | **P2** | Medio (NotPetya, APTs) | Medio |
| `dns_query_count` | **P3** | Bajo (solo correlación) | Bajo |

**Acción inmediata recomendada:**
1. Implementar `rst_ratio` esta semana.
2. Generar nuevo dataset sintético que incluya:
    - Escaneo SMB a tasas 10-1000 conn/sec
    - Ratios RST/SYN 0.1-0.9
    - Tráfico de administración Windows legítimo como control
3. Reentrenar modelo y evaluar contra captures reales de WannaCry (disponibles en Malware Traffic Analysis, etc.)

---

*— DeepSeek, miembro del Consejo de Sabios*
*DAY 90 — 18 marzo 2026*

PD: La honestidad sobre los límites (killswitch indetectable, necesidad de reentrenamiento) no debilita el paper — lo fortalece. Los reviewers valorarán la madurez de reconocer lo que el sistema puede y no puede hacer. Sigue así.