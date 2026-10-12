**Nombre:** El Consejo de Sabios

Aquí tenéis nuestra auditoría adversaria, propuestas medibles y predicciones falsables para la iteración DAY294 en el entorno de sombra.

---

### P1. Etapa 2 por comportamiento

* **Recomendación:** Incorporar la dispersión de orígenes por víctima (`source_ip_dispersion`) y la cuota de tasa del origen, calculadas mediante un contador acumulativo en eBPF por clave de víctima.
* **Medida propuesta:** Añadir al sniffer un mapa hash en eBPF que cuente las direcciones IP de origen distintas por ventana temporal asociadas a cada víctima, indexando este contador directamente en el vector de rasgos.
* **Predicción numérica:** Con una familia de ataque externa no vista en entrenamiento, la tasa de detección exitosa subirá del ~0% actual al **85%**.
* **Qué la refutaría:** Que el uso de este rasgo incremente la tasa de falsos positivos en tráfico legítimo multicliente (como un CDN o balanceador) por encima del **2%**.

---

### P2. Batería v3

* **Recomendación:** La batería v3 es sólida, pero requiere añadir un eje de ráfagas estocásticas basadas en procesos de Poisson para simular transitorios de red realistas.
* **Medida propuesta:** Ejecutar una corrida adicional de 300 segundos inyectando tráfico con una distribución de Poisson con lambda oscilante entre 10 y 200 pps, combinado con ruido de fondo TCP benigno.
* **Predicción numérica:** La Etapa 1 mantendrá una tasa de falsos positivos inferior al **0,5%** bajo este régimen de carga oscilante.
* **Qué la refutaría:** Que se registren más de **5 falsos positivos** de inicio en la sombra durante los picos de la oscilación de tráfico legítimo.

---

### P3. Valores por defecto para un cliente real

* **Recomendación:** Establecer una calibración automática basada en percentiles históricos del tráfico del cliente, combinada obligatoriamente con la aprobación final del operador humano.
* **Medida propuesta:** Realizar una auditoría pasiva del tráfico del cliente durante 7 días continuos, calculando el percentil 99 del `victim_rate_ratio` para determinar $K$ y la desviación estándar para el parámetro de hold.
* **Predicción numérica:** El umbral $K$ calibrado absorberá al menos el **99,9%** del tráfico normal en un entorno hospitalario sin generar falsas alarmas de sombra.
* **Qué la refutaría:** Que durante la primera semana de monitorización pasiva se acumulen más de **3 falsos positivos** catalogados formalmente por el personal técnico.

---

### P4. Mitigación real por víctima

* **Recomendación:** Descartar selectivamente únicamente los flujos marcados por la Etapa 2 filtrando por tupla (IP origen, IP víctima) durante el periodo de hold, resguardando al inocente.
* **Medida propuesta:** Conectar la salida de la sombra a una regla de firewall granular por tupla, midiendo simultáneamente el rendimiento en pps del cliente inocente `.51`.
* **Predicción numérica:** El tráfico del inocente concurrente (`.51`) mantendrá exactamente **0 drops** (0% de pérdida de paquetes) durante toda la fase de ataque activo.
* **Qué la refutaría:** Que el inocente experimente un solo evento de drop o un incremento de latencia superior al **5%** mientras el mecanismo de hold esté activo.

---

### P5. Base de tiempo única (siguiente PR)

* **Recomendación:** Utilizar `bpf_ktime_get_tai_ns` a nivel de kernel para el ordenamiento de eventos y métricas de duración, anclándolo al tiempo real en el espacio de usuario.
* **Medida propuesta:** Implementar el uso de `bpf_ktime_get_tai_ns` en el programa eBPF y evaluar la estabilidad de los eventos ante saltos forzados de reloj de pared mediante `chronyc makestep`.
* **Predicción numérica:** Cero alteraciones o saltos en las métricas de `time_to_block` y duraciones de hold estables ante un salto artificial de **2 segundos** del reloj del sistema.
* **Qué la refutaría:** Que un salto temporal del sistema provoque inversiones en el orden de los logs o bloqueos prematuros con una desviación superior a **100 ms**.

---

### P6. Disyuntor de saturación

* **Recomendación:** Implementar un mecanismo dual que emita alertas tempranas y degrade de forma automática a una regla estática por víctima en caso de saturación del anillo.
* **Medida propuesta:** Monitorear de forma continua las pérdidas en el ring buffer del sniffer; si la tasa de pérdida supera el **0,1%** durante 3 ventanas consecutivas, conmutar la directiva a limitación estática.
* **Predicción numérica:** El sistema mantendrá la estabilidad operativa con una degradación en el procesamiento inferior al **2%** bajo una sobrecarga sostenida de **500 pps**.
* **Qué la refutaría:** Que el paso a la regla estática bloquee tráfico legítimo de la víctima en más de un **5%** de los flujos activos concurrentes.