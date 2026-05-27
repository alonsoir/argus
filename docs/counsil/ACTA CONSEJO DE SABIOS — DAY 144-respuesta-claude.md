**RESPUESTAS CLAUDE — ACTA CONSEJO DAY 144**

---

**P1 — Métricas ADR-029 Variant A vs B**

Para contribución científica al paper v19, mi orden de prioridad:

**Primarias (imprescindibles):**
- **Tasa de detección bajo carga** — es la métrica que importa clínicamente. F1, Precision, Recall sobre CTU-13 Neris a diferentes velocidades de replay (10 Mbps, 50 Mbps, 100 Mbps). Si Variant B detecta peor bajo carga, no importa que consuma menos CPU.
- **Throughput máximo (pps)** antes de empezar a perder paquetes — el punto de saturación de cada variante es el dato más citeable.

**Secundarias (enriquecen el paper):**
- **Latencia p50/p95/p99** desde captura hasta decisión de firewall — relevante para el argumento de respuesta en tiempo real.
- **Consumo RAM en idle y bajo carga** — crítico para el argumento Pi 4 4GB de FEDER.

**Lo que NO mediría ahora:** overhead de kernel en detalle — es demasiado específico de la VM y no generaliza al hardware real del paper.

---

**P2 — Scope ARM64 Variant C para FEDER**

Mi posición: **suficiente con x86 eBPF + x86 libpcap para paper v19 y FEDER.**

Argumentación:

La contribución científica de ADR-029 es la comparación arquitectural entre captura en kernel space (eBPF) vs userspace (libpcap) en el contexto de detección de intrusiones. Eso está completo con las dos variantes x86.

ARM64 añade una dimensión de portabilidad que es valiosa para el argumento de despliegue en infraestructura crítica de bajo coste (Pi 4, edge computing hospitalario), pero el trabajo necesario es sustancial: cross-compilation toolchain, CMakeLists aarch64, Vagrantfile con box ARM64 real, dist/arm64/ paralelo a dist/x86/. Con deadline FEDER en septiembre y go/no-go en agosto, el riesgo de abrir esa feature ahora es alto.

Propuesta concreta: ARM64 como `feature/adr029-variant-c-arm64` con milestone post-FEDER. En el paper v19 se menciona como trabajo futuro — "portabilidad a arquitecturas ARM64 para despliegue en edge computing de infraestructura crítica". Eso es contribución sin el riesgo de no terminarlo a tiempo.

---

**P3 — Modelo probabilidad conjunta multi-señal**

Mi recomendación: **regresión logística con features explícitas**, no Naive Bayes ni modelo más sofisticado.

Razones:

Naive Bayes asume independencia entre señales — que el score ML y la frecuencia de eventos son independientes es difícilmente defendible. Los revisores del paper lo atacarán.

Modelos más sofisticados (redes neuronales, gradient boosting para la decisión de aislamiento) crean una caja negra dentro de otra caja negra — el IRP pierde auditabilidad, que es uno de los argumentos centrales del paper.

Regresión logística con features explícitas:

```
P(aislar) = sigmoid(w1·score_ml + w2·score_fast + 
             w3·frecuencia_normalizada + w4·severidad_tipo +
             w5·contexto_temporal + bias)
```

Ventajas: coeficientes interpretables y publicables, entrenamiento con datos históricos de incidentes etiquetados, auditoría trivial ("el peso del score ML es 0.7, el de frecuencia es 0.2"), y el threshold de decisión es ajustable por el operador con semántica clara.

Para producción hospitalaria: los pesos iniciales se pueden fijar manualmente por expertos de dominio y refinar después con datos reales — no necesitas datos de entrenamiento para el primer despliegue.

---

**P4 — Protocolo experimento aRGus vs Suricata vs Zeek**

El problema central de rigor científico es el **sesgo de configuración**: Suricata con reglas ET completas vs aRGus sin reglas de firma. Hay que ser explícito sobre qué se está comparando.

**Propuesta de protocolo:**

*Configuración experimental:*
- Los tres sistemas sobre el **mismo tráfico simultáneamente** via tcpreplay sobre interfaz en modo promiscuo
- Suricata: reglas ET Community (las mismas que usaría en producción real — no handicapar)
- Zeek: scripts base sin customización
- aRGus: solo detector ML, sin reglas de firma (que no tiene)

*Dos escenarios separados:*

**Escenario 1 — Tráfico conocido (CTU-13 Neris):**
Hipótesis: Suricata y Zeek tienen firmas para Neris (botnet documentada desde 2011). aRGus detecta por comportamiento. Métrica clave: ¿quién detecta antes el primer evento? ¿Quién tiene menos FP?

**Escenario 2 — Tráfico adversarial (MITRE ATT&CK sin firma):**
Usar técnicas de ATT&CK que **no tienen regla ET conocida** — movimiento lateral via protocolo legítimo, C2 sobre HTTPS, exfiltración via DNS. Aquí la hipótesis es que aRGus detecta por anomalía comportamental donde Suricata no tiene firma.

*Métricas de comparación:*
- Detecciones únicas de cada sistema (Venn diagram)
- Detecciones en solapamiento (corroboran validez)
- FP rate en tráfico benigno basal
- Time-to-detect desde inicio del ataque

*Cómo aislar el efecto de las reglas ET:*
Ejecutar Suricata en dos modos: con ET completo y con **cero reglas** (solo motor). La diferencia entre ambos modos cuantifica exactamente el valor de las firmas. Si Suricata sin reglas detecta poco y aRGus detecta mucho en Escenario 2, el argumento del detector conductual está demostrado empíricamente.

*Reproducibilidad:*
Todo el experimento en un Makefile target — `make experiment-comparative` — que descarga los pcaps, lanza los tres sistemas, recoge los logs y genera el informe. Reproducible por cualquier revisor del paper.

---

Listo. Manda esto al Consejo junto con el acta y recoge el feedback. Descansa.