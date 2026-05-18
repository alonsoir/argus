El Consejo de Sabios se reúne en sesión extraordinaria para evaluar la **ADR-046**. La evolución hacia **aRGus++** transforma de manera definitiva el proyecto de un excelente eBPF NDR a una plataforma de defensa híbrida y holística (NDR/EDR) con una fundamentación científica de primer nivel.

La tesis planteada sobre la **inadecuación de los datasets académicos históricos** debido a la obsolescencia de firmas (*signature aging*) y la ceguera del host sobre trazas muertas pcap es un argumento epistemológico brillante que blindará la aceptación del paper en congresos como USENIX o NDSS.

A continuación, analizamos los puntos débiles del documento y emitimos los dictámenes para las preguntas abiertas.

---

## 4. Análisis de Puntos Débiles en la Redacción de la ADR-046

1. **Sincronización horaria como Single Point of Failure (SPOF):**
   En la sección 11 (Riesgos), se menciona que el join requiere NTP. Si un atacante compromete el servidor NTP local (o realiza *NTP spoofing*), puede desalinear los relojes de los nodos *edge*, destruyendo por completo la capacidad del `correlation-engine` de unir las 5-tuplas. Esto deshabilitaría el *flywheel* y contaminaría los datasets de entrenamiento.
2. **Ambigüedad en el Join por 5-tupla tras NAT/Proxies:**
   El documento asume que la 5-tupla es idéntica en todas las fuentes. Si el agente de Wazuh reporta una conexión local hacia un proxy inverso o un balanceador en el host, y aRGus/Suricata ven el tráfico saliente post-NAT, la IP de origen o destino cambiará, rompiendo el join estricto.
3. **Monopolio de Memoria por parte de Zeek:**
   Mientras que aRGus y Suricata procesan paquetes de forma muy eficiente, Zeek mantiene tablas de estados en memoria extremadamente densas para la reconstrucción de sesiones de capa 7 (especialmente en TLS y reensamblado TCP). La hipótesis de recursos debe explicitar que el riesgo de OOM (*Out Of Memory*) en una RPi5 proviene principalmente de Zeek.

---

## 13. Respuestas y Dictámenes del Consejo

### Q1 — Ventana de correlación de ±500ms

**Dictamen:** **La ventana de 500ms es correcta para flujos interactivos, pero insuficiente para protocolos asíncronos o ráfagas de control.**

* **Punto Débil Detectado:** Un evento de Wazuh (ej. el hash de un binario que se escribe en disco tras una descarga) puede registrarse varios segundos *después* de que el flujo de red de aRGus haya cerrado la conexión TCP si el búfer de disco del agente está saturado. Un DNS *query* (Zeek) puede ocurrir segundos antes de que la conexión real (aRGus) se inicie debido al almacenamiento en caché del sistema operativo de la víctima.
* **Recomendación:** La ventana **no debe ser simétrica fija**. Debe parametrizarse dinámicamente en el JSON de configuración del `correlation-engine` mediante un modelo de ventanas relativas por origen de datos:
* `t_argus - 2000ms < t_zeek_dns < t_argus` (DNS siempre ocurre antes).
* `t_argus < t_wazuh_fim < t_argus + 5000ms` (La telemetría de host y disco suele tener retardo/delay operacional).



### Q2 — Orden de integración: ¿Suricata o Zeek primero?

**Dictamen:** **Suricata primero.**

* **Justificación:** Suricata provee dos elementos críticos de manera inmediata:
1. **Etiquetado automático de alta fidelidad:** Permite automatizar de inmediato el *ground truth* para el motor ML de aRGus.
2. **Formato unificado:** Su salida `eve.json` agrupa en un solo flujo JSON tanto la alerta (firma) como los metadatos de protocolo (DNS, TLS). Zeek requiere parsear múltiples archivos planos estructurados independientes (`conn.log`, `dns.log`), lo que incrementa la complejidad del cargador de datos en C++20 en esta etapa inicial.



### Q3 — Wazuh en el Edge: ¿P1 o P2?

**Dictamen:** **Clasificado como P2. Validación escalonada.**

* **Justificación:** El agente de Wazuh incluye el demonio de monitorización de integridad de archivos (FIM) y auditoría de llamadas al sistema (Auditd/Sysmon), cuyo impacto en la CPU/disco de sistemas embebidos de bajos recursos (como una RPi5) es severo ante ráfagas de E/S.
* **Estrategia:** Consolidad la capa de red pura primero (aRGus + Suricata + Zeek) bajo la deuda `DEBT-ARGUSPP-RESOURCE-001`. Una vez que se verifique el techo técnico y el margen de recursos remanente en la RPi5, incorporad a Wazuh para evitar caídas por falta de memoria (OOM).

### Q4 — `correlation-engine` scope mínimo v1

**Dictamen:** **v1 de Alcance Reducido: aRGus + Suricata (`eve.json`).**

* **Justificación:** El objetivo principal para el paper v24 es demostrar la viabilidad del *flywheel* y el auto-etiquetado. La unión temporal de flujos de aRGus con las alertas de Suricata utilizando `nlohmann/json` y `arrow::parquet` proporciona un Producto Mínimo Viable (MVP) científico completo. Añadir Zeek y Wazuh desde la v1 dilataría el desarrollo del motor de correlación en C++20 debido a la gestión de múltiples sockets de entrada concurrentes.

### Q5 — Arquitectura de `mitre-generator`

**Dictamen:** **Componente independiente con su propio ADR, utilizando Atomic Red Team como dependencia externa vía scripts orquestados.**

* **Justificación:** Reinventar la ejecución de tácticas atómicas de ataque es un esfuerzo innecesario que no aporta valor científico a la tesis de aRGus. El valor real radica en el **orquestador y su manifiesto JSON con marcas de tiempo precisas**.
* **Blindaje contra la deriva temporal:** El `mitre-generator` debe inyectar un ID único de ejecución (*Execution-UUID*) en el tráfico (por ejemplo, codificado en el tamaño exacto del payload de ping o en un subdominio DNS específico de prueba como `attack-<uuid>.argus.test`). Esto permitirá al `correlation-engine` verificar los joins temporales de forma determinista, independientemente de pequeñas desviaciones del reloj NTP.

### Q6 — Experimento de mezcla de datasets (Paper v24)

**Dictamen:** **Prioridad Absoluta P0 para el rigor científico del proyecto. Los datos deben ser recuperados o re-ejecutados.**

* **Justificación:** Afirmar en una publicación de revisión por pares (*peer-review*) que añadir datos académicos *degrada* el rendimiento del clasificador es una aseveración audaz que despertará el escepticismo de los revisores tradicionales si no se acompaña de evidencia empírica irrefutable.
* **Acción:** Reconstruid el experimento generando la **Curva de Degradación Comportamental** (Eje X: Ratio de mezcla de datos académicos 0-100%, Eje Y: F1-Score en entornos reales de producción). Esto constituirá el núcleo del nuevo apartado propuesto en el punto 8.4 del documento: *"On the inadequacy of academic datasets"*.

---

## Modificaciones sugeridas para el texto de la ADR antes de su firma

Para robustecer la ADR, añadid las siguientes líneas en las secciones correspondientes:

* **En la Sección 3.3 (Correlation Engine):**
> *"Para mitigar el desalineamiento temporal (NTP drift/spoofing), el `correlation-engine` no solo utilizará ventanas de tiempo dinámicas y asimétricas por protocolo, sino que validará de manera cruzada las secuencias lógicas utilizando identificadores sintéticos inyectados por el orquestador del experimento."*


* **En la Sección 11 (Deuda Técnica Generada):**
  Añadir: `DEBT-ARGUSPP-NAT-001` | *Abstracción y normalización de IPs en entornos con traducción de red (NAT) para el join de la 5-tupla host/red.* | Prioridad P1.

---

El Consejo aprueba este borrador con las enmiendas citadas. Quedamos a la espera del script de automatización para actualizar el repositorio. *¡Ad astra y Via Appia Quality!*