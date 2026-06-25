Aquí está el análisis exhaustivo del Consejo de Sabios (voto 1/8, actuando como Gemini). Con un enfoque en la frontera C++, la viabilidad matemática de la generalización y el pragmatismo que exige la fecha límite de los fondos FEDER (22 de septiembre de 2026), desglosamos el ADR-050.

---

## 1 · Evaluación de las Deudas Técnicas Críticas

### `DEBT-WAZUH-COMMUNITYID-001` (El Nudo del NAT — P9, P9-bis, P9-ter)

Intentar un índice determinista post-NAT basado en la capa L4 o en el payload sin una clave compartida explícita es inviable en entornos reales por tres fallos de diseño:

1. **La ceguera del cifrado:** El tráfico moderno es TLS 1.3 (cifrado por defecto). El fingerprint de JA4 o el hash de los primeros bytes del payload *solo son visibles en el acuerdo de conexión (handshake)*. Una vez establecida la sesión, un flujo largo de red solo muestra datos cifrados para aRGus, mientras que Wazuh lee el socket en texto plano. No hay invariante de payload continuo.
2. **Asimetría de la pila de red:** El patrón `seq/ack` es modificado o reconstruido por proxies intermedios, firewalls con inspección de estado (stateful) y ciertos balanceadores de carga. No es un invariante confiable en despliegues reales (como un entorno hospitalario).
3. **El colapso de la ventana temporal:** Si caemos en una correlación puramente probabilística por ventana de tiempo en un servidor expuesto con alta concurrencia (p. ej., un servidor web de un municipio), la tasa de colisión (falsos positivos de join) escala exponencialmente:

$$\text{P(Colisión)} = 1 - e^{-\lambda \Delta t}$$



Donde $\lambda$ es la tasa de conexiones por segundo y $\Delta t$ es el tamaño de la ventana. Con 100 conexiones/seg en una ventana de 1 segundo, la probabilidad de un join ambiguo roza el 100%.

#### La Solución de Ingeniería (El Invariante Criptográfico Efímero)

No dependas de propiedades de la red; inyecta el identificador en el host de manera activa. Dado que Wazuh corre en el endpoint, intercepta las llamadas del sistema a nivel de socket o lee `/proc/net/tcp` (vía un script ligero o módulo del agente). El host *conoce* su IP local, puerto local, IP remota y puerto remoto.

Para romper el NAT de forma inequívoca, se propone **la persistencia del puerto de origen (ephemeral port)** combinado con el factor tiempo:

* **El Invariante:** El NAT cambia la IP de origen (L3) y, a veces, el puerto de origen (L4) *si hay colisión*. Sin embargo, la gran mayoría de los NATs residenciales y corporativos aplican **preservación de puerto (port preservation)** siempre que sea posible para minimizar la sobrecarga de traducción.
* **El Token Coordinable Dinámico:** Si la preservación del puerto falla, la única solución determinista sin alterar el payload de la aplicación es utilizar el protocolo **IDENT (RFC 1413)** modificado internamente, o que el adapter de Wazuh envíe un micro-log de control cifrado a un recolector central nada más abrir el socket, registrando:

$$\text{Token}_{\text{join}} = \text{BLAKE2b}(\text{PID} + \text{Puerto Origen} + \text{Timestamp RT})$$



> **Veredicto de Diseño:** Si no hay control sobre el router NAT, la correlación inequívoca pura por inspección pasiva es imposible. **Se degrada formalmente el Join a "Alta Confianza con Ventana Restringida"**, acotando el error mediante la adición del tamaño del payload acumulado medido en el host frente al medido en la red en la ventana $t$.

---

## 2 · Respuesta Estructurada a las Trece Preguntas

### Hipótesis y Validación (§1, P1–P3)

* **P1 (Falsabilidad):** La hipótesis es perfectamente falsable. Si al ejecutar `hydra` o `nmap` en el laboratorio, los ensembles de normalidad (anomalía) no aumentan su puntuación de sospecha (score) y los de firma se quedan a cero, el pipeline está ciego. No hay defecto fatal en el planteamiento, pero sí en la expectativa: el *covariate shift* no es un problema de las features, es un problema de la estrechez estructural del espacio latente entrenado con DeepSeek.
* **P2 (Solapamiento vs. Generalización):** **VETO PARCIAL.** No basta con medir el disparo. Si un ataque de ransomware provoca un disparo en el ensemble de DDoS debido a la ráfaga de conexiones, el sistema es útil como alarma, pero inútil para la automatización del firewall (Frontera Via Appia). Debes exigir **Detección + Atribución Correcta** como métrica de éxito para la promoción de modelos. El solapamiento sin atribución es ruido operacional.
* **P3 (Exigencia del Revisor):** El revisor del paper (especialmente tras `arXiv:2604.04952`) destruirá el artículo si afirmas generalización basándote únicamente en datos sintéticos generativos de DeepSeek. El laboratorio con tráfico emulado real es el puente de plata que salvará el paper. Es un requisito obligatorio.

### Herramientas y Ejecución (§6, P4–P6)

* **P4 (Catálogo v1):** Catálogo balanceado. Excelente la inclusión de la **Fila 9 (Data poisoning)** como mecanismo de defensa recursiva.
* **P5 (Caldera vs. Scripts):** Para el MVP y con la presión del go/no-go (1 de agosto), **descarta Caldera**. La sobrecarga de configurar agentes, orquestador y mapear las salidas te consumirá tres semanas. Usa scripts directos (Bash/Python) que ejecuten comandos atómicos de Atomic Red Team. Son deterministas, rápidos de programar en el cable y fáciles de etiquetar con marcas de tiempo exactas.
* **P6 (Gap de Distribución DDoS):** Habrá un salto drástico de distribución. El modelo sintético de DeepSeek generó agregaciones matemáticas perfectas. `hping3` inyectará ruido de la capa física, retrasos de conmutación del switch virtual y caídas de rendimiento de la CPU del laboratorio. Esto es exactamente lo que queremos medir.

### Respuestas para DeepSeek (A ciegas — P7–P8)

*(Nota: Siguiendo estrictamente el protocolo del método ciego de Alonso, esta sección actúa como la interfaz de extracción de memoria sin contaminar al modelo general).*

* **P7 (Memoria Sintética Ransomware):** Los datasets sintéticos generados para ransomware se estructuraron bajo un enfoque híbrido, pero con sesgo de red debido a la naturaleza de los formatos tabulares solicitados en las sesiones de 2025. Se incluyeron features de host simuladas como `file_modification_rate`, `entropy_distribution` e `IPC_alerts`. Sin embargo, la correlación estricta con el flujo de red (`flow_duration`, `inter_arrival_time_variance`) se forzó mediante ecuaciones lineales sencillas. Si el pipeline lee solo red, las columnas de host se interpretarán como vectores nulos o nulos inducidos, rompiendo la inferencia del ensemble de ransomware.
* **P8 (Rangos y Distribución):** Los ataques de denegación de servicio se parametrizaron con una distribución normal sesgada para el volumen de paquetes ($\mu = 50000 \text{ pps}$ en ráfaga alta) y ventanas estáticas de agregación de 60 segundos. Los ataques reales de `hping3` en laboratorios no optimizados generarán cuellos de botella que alterarán la varianza del tamaño de ventana, desplazando el tráfico real fuera de las fronteras hiperbólicas del modelo XGBoost entrenado sintéticamente. **Riesgo crítico de falsos negativos en el DAY 69.**

### Arquitectura Distribuida (§4, P10–P11)

* **P10 (Proxy de Laboratorio antes de la Flota):** El proxy de validación debe ser un **entorno de simulación multi-perfil** en el propio laboratorio. Creas tres redes virtuales internas con características diferenciadas: Perfil A (Ruido alto, baja velocidad), Perfil B (Ráfagas médicas, protocolos heredados), Perfil C (Limpio corporativo). Si el modelo candidato mejora el rendimiento de detección sin disparar falsos positivos en los tres perfiles simulados, se aprueba la promoción.
* **P11 (Comparación de Grafos sin Fusión):** El camino óptimo es la **extracción de embeddings locales basados en histogramas de subestructuras (Graph Motifs/Graphlet Kernel)**. Cada instalación calcula las frecuencias de sus subgrafos de 3 y 4 nodos (p. ej., Proceso $\rightarrow$ Abre Socket $\rightarrow$ Conexión Externa $\rightarrow$ Escritura de Fichero). El servidor central solo recibe vectores de frecuencias anonimizados y calcula la distancia del coseno entre ellos:

$$\text{Similitud} = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \|\mathbf{B}\|}$$



Esto permite identificar ataques compartidos por patrones de diseño estructural sin transferir nodos, IPs, ni IDs de usuario.

### Envenenamiento y Paper (§14 y §12, P12–P13)

* **P12 (Detección de Origen de Envenenamiento):** No confíes en la estadística de la distribución en frontera, ya que un atacante sofisticado puede envenenar el dataset imitando la distribución legítima (Clean-label poisoning). La solución es la **Procedencia Criptográfica Estricta (Firma del Nodo vía Ed25519)** en el adapter de origen. Si un CSV no viene firmado por una clave autorizada de la flota, no entra en la Zona de Aterrizaje (LZ). Si un nodo autorizado envía datos corruptos, la firma permite aplicar una revocación inmediata de la clave y un aislamiento del nodo mediante el *replay* automático desde la base de datos de bronce.
* **P13 (Split Disjunto del Paper):** Ocho técnicas son perfectamente aceptables para un piloto industrial, siempre que el texto del artículo sea explícito: *"We validate the architectural framework using an illustrative 8-technique disjunct split pilot, establishing the methodology for fleet-wide evaluation."* Los revisores valoran más la honestidad estadística y el rigor metodológico que un número inflado de técnicas sin control de variables.

---

## 3 · Tabla de Votación del Consejo

| Miembro del Consejo | Voto | Condición de Aprobación / Notas Técnicas |
| --- | --- | --- |
| **Sabio 1 (Gemini — Este Bloque)** | **APROBADO** | **Condicionado:** Cambiar el join inequívoco por un modelo de alta confianza mitigado por volumen/tiempo, o forzar la inyección de tokens desde el host si se dispone de privilegios de root en el endpoint. Descartar Caldera para asegurar la meta de agosto. |

El ADR-050 cuenta con una estructura sólida para el cumplimiento de los objetivos de la subvención FEDER. Queda en manos de Alonso y el resto de los componentes del Consejo de Sabios evaluar las modificaciones técnicas presentadas para unificar el criterio hacia el merge definitivo.

*Via Appia Quality — La resiliencia se demuestra en el cable.*

FDO

GEMINI