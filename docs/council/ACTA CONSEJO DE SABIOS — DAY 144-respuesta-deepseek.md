**CONSEJO DE SABIOS — VEREDICTO DAY 144**

Honorable Alonso, el Consejo se reúne hoy con la satisfacción de ver cerradas cuatro deudas de alto riesgo, un gate ODR impecable y una disciplina de pruebas que ya es emblema del proyecto. Vuestro trabajo sobre `SA_NOCLDWAIT`, la eliminación de la copia stale de protobuf (40k líneas fuera) y la reducción a una única fuente de verdad para `auto_isolate` son decisiones que elevan la calidad del sistema a la altura de su responsabilidad clínica. Dicho esto, vayamos a las preguntas difíciles.

---

### P1 — Diseño experimental ADR-029 Variant A vs B

Para una contribución científica sólida al paper arXiv v19, **es imprescindible medir throughput, latencia y consumo de recursos de forma simultánea, no secuencial**. La comparación debe ir más allá de "A es más rápido que B" y caracterizar el perfil de cada variante.

**Métricas imprescindibles:**
1.  **Throughput máximo (pps / Mbps)**: Curva de saturación. ¿A qué tasa de paquetes empieza a perder el backend? Esto es crítico para NDR, donde un drop es una alerta perdida. Debéis medir tanto la tasa máxima sin pérdidas como la pérdida en función de la carga.
2.  **Latencia de procesamiento (p50, p95, p99)**: No solo la media. En Variant B, el paso extra por userspace (libpcap) introduce una latencia de cola que la media puede ocultar. En seguridad, el p99 es más relevante que el promedio, porque un ataque se detecta en el peor caso, no en el caso medio.
3.  **Consumo de CPU y memoria**: La Variant A descarga trabajo al kernel (eBPF/XDP), mientras que la Variant B consume CPU de usuario por cada paquete. Esto determina la capacidad de coexistencia con otros servicios en un dispositivo médico (que aRGus debe proteger, no saturar).
4.  **Tasa de detección bajo carga**: La métrica de negocio. Medid F1-score de detección para cada variante en condiciones de carga creciente. Un backend que pierde paquetes degradará su F1.

**Protocolo experimental sugerido:**
Replicad el tráfico de CTU-13 (Neris) con `tcpreplay` a velocidad controlada, incrementando la tasa desde 10 Mbps hasta la saturación. Para cada tasa, medid las 4 métricas anteriores. Esto produce gráficos bidimensionales (métrica vs carga) que son visualmente potentes en un paper y científicamente rigurosos.

**Veredicto**: Medid throughput, latencia p99, CPU/RAM y F1-score, todos en función de la carga ofrecida. Esto constituye la contribución central de ADR-029.

---

### P2 — Scope ARM64 Variant C

**Para la fecha límite de FEDER (22 de septiembre), el esfuerzo de una feature completa ARM64 Variant C no es justificable y pone en riesgo el entregable principal.** La contribución científica sustantiva es la comparación empírica de arquitecturas de captura (eBPF vs libpcap) sobre x86, que es un entorno controlado y reproducible por cualquier revisor.

La Variant C (ARM64 + libpcap) es una mejora de portabilidad con interés de ingeniería, pero su valor diferencial para un paper es bajo: demostraría que libpcap funciona en ARM, cosa que ya se sabe. No aporta una hipótesis novedosa. El riesgo, en cambio, es alto: la cadena de compilación cruzada, la emulación o el aprovisionamiento de hardware real pueden consumir semanas que el proyecto no tiene.

**Propuesta estratégica:**
Centrad FEDER en **x86 eBPF + x86 libpcap**. Para la defensa de que aRGus puede correr en dispositivos médicos de bajo consumo (que suelen ser ARM), realizad una **simulación de viabilidad**: una sola medición de Variant B compilada y ejecutada en una Raspberry Pi 5 con un pcap pequeño, solo para demostrar que el binario arranca, procesa y no se colapsa. Esto cabe en un párrafo de "Trabajo Futuro" y no requiere una feature completa.

**Veredicto**: Variant C no es necesaria para el paper v19. Priorizad el experimento en x86. Reservad ARM64 para una demostración de viabilidad, no para un benchmark completo.

---

### P3 — Probabilidad conjunta multi-señal

La transición de un umbral simple a una decisión basada en múltiples señales heterogéneas es un salto cualitativo. El Consejo recomienda un enfoque **híbrido, auditable y publicable**:

**Primera etapa: Modelo de Naive Bayes con priors configurables**
Naive Bayes es la opción inicial correcta porque:
- Combina naturalmente señales de distinta naturaleza (probabilidad de score, frecuencia de eventos, tipo de detección) asumiendo independencia condicional, lo cual es razonable para un prototipo.
- Sus pesos son probabilidades condicionales que un administrador clínico puede entender y auditar con un poco de formación: "Si es ransomware, la probabilidad de aislamiento necesario es 0.98; si es C2 beacon, 0.90".
- Es publicable: los revisores de FEDER apreciarán un modelo estadístico bien documentado y con priors basados en datos de entrenamiento (CTU-13, MITRE ATT&CK) que se pueden listar en un apéndice del paper.

**Segunda etapa: Regresión logística calibrada**
Si los datos lo permiten, una regresión logística ofrece una salida de probabilidad calibrada, permite interacciones entre variables y sigue siendo un modelo de caja blanca. Sería una evolución natural post-FEDER.

**Lo que debe evitarse:**
Cualquier modelo de caja negra (redes neuronales, gradientes boosting) para la decisión de aislamiento. La responsabilidad clínica exige que la razón del aislamiento sea explicable con un rastro determinista: "Se aisló porque el score fue 0.97, el tipo ransomware, y hubo 3 eventos en 60 segundos".

**Veredicto**: Implementad un Naive Bayes con priors documentados como cierre de `DEBT-IRP-MULTI-SIGNAL-001`. Es el equilibrio perfecto entre rigor y auditabilidad.

---

### P4 — Protocolo experimental: aRGus vs Suricata vs Zeek

Para una comparación científicamente válida y reproducible, debéis eliminar variables de confusión y medir la capacidad intrínseca de detección, no la calidad de las reglas estáticas.

**Diseño experimental con dos vectores de ataque:**
1.  **Detección basada en firmas (baseline)**:
    *   Usad el tráfico de **CTU-13 Neris** (malware conocido, con firmas).
    *   **Suricata con reglas ET Open actualizadas**: Comparad F1 de Suricata (detección por firma) contra F1 de aRGus (detección ML). Esto mide si aRGus puede, sin firmas, alcanzar un rendimiento comparable a un IDS tradicional.
    *   **Zeek**: Medid su capacidad de generar logs de anomalías para el mismo tráfico, no su F1 (Zeek no es un IDS de alertas por defecto), sino la riqueza de sus metadatos.

2.  **Detección de amenazas adversariales sin firma**:
    *   Usad tráfico de **MITRE ATT&CK** que no esté cubierto por las reglas estándar. Por ejemplo, comandos C2 sobre protocolos permitidos o exfiltración lenta de datos que no active umbrales de Suricata.
    *   Aquí la métrica es la **tasa de detección pura**: aRGus debería detectar anomalías por comportamiento, mientras que Suricata (solo reglas) fallará. Esto valida la hipótesis central del ML para NDR.

**Aislamiento del efecto reglas vs ML:**
Para el experimento con CTU-13, ejecutad Suricata en dos modos: con reglas ET completas y con un conjunto mínimo de reglas (solo protocolo). Esto separa lo que detecta por heurísticas de protocolo de lo que detecta por firma. No es posible apagar el ML de aRGus para "empatar", pero podéis medir la contribución de las reglas de Suricata.

**Reproducibilidad obligatoria:**
Todos los pcaps, configuraciones y scripts de medición deben ser públicos y versionados en el repositorio. El paper debe incluir un apéndice con el hash de los pcaps, las versiones exactas de Suricata/Zeek y las reglas utilizadas. Solo así la comunidad científica podrá replicar (y criticar) vuestros resultados.

**Veredicto**: Dos vectores (Neris con firmas, ATT&CK sin firma). Aislad el efecto reglas en Suricata con dos ejecuciones. Documentadlo todo para reproducibilidad exacta. Esto es competitivo para cualquier conferencia de seguridad o sistemas.

---

### Sobre el plan del DAY 145

La secuencia es impecable: EMECAS, experimentos Variant A/B, y merge a `main`. Añadid un paso previo a las mediciones: una **limpieza del estado del sistema** (reinicio de servicios, borrado de logs previos) y una **medición de baseline** (sistema en reposo) para descontar el ruido de la VM en las métricas de CPU/RAM.

El Consejo aguarda los resultados del experimento comparativo con gran expectación. Consolidar la rama en `main` será un digno cierre de 144 días de ingeniería excepcional.

*Firmado, el Consejo de Sabios, en sesión permanente,  
a 7 de Mayo de 2026.*