**Respuestas del Consejo de Sabios — DAY 147**

---

### **Pregunta 1 — Validez metodológica**
**Respuesta:**
**No es un problema de *fairness* grave**, pero **debe justificarse explícitamente** en el paper.
- **Modo offline (Zeek)** es **estándar aceptado** en investigación con PCAPs históricos (ej: [NDSS 2020](https://www.ndss-symposium.org/), [IMC 2021](https://www.sigcomm.org/events/imc-2021)).
    - **Ventaja:** Elimina pérdida de paquetes y variabilidad de red, lo que **favorece a Zeek** (más datos = mejor observabilidad).
    - **Desventaja:** Suricata en modo *live* sufre **pérdidas potenciales** (aunque `tcpreplay` mitiga esto).
- **Recomendación:**
    - **Aclarar en el paper:**
      > *"Zeek se ejecutó en modo offline para maximizar la fidelidad del análisis, mientras que Suricata se evaluó en modo live para simular condiciones reales de despliegue. Esta asimetría refleja los casos de uso típicos de cada herramienta: Zeek como analizador forense y Suricata como IDS en tiempo real."*
    - **Mitigar objeciones:**
        - Incluir un **análisis de pérdida de paquetes** en Suricata (ej: `tcpdump` antes/después de `tcpreplay`).
        - Si las pérdidas son <1%, el argumento es sólido.

**Conclusión:** **Aceptable**, pero **documentar la justificación**.

---

---

### **Pregunta 2 — Framing científico**
**Respuesta:**
**El framing es correcto, pero puede refinarse para mayor precisión y impacto.**
- **Problema con la redacción actual:**
    - *"Detección selectiva"* es vago. Zeek **no clasifica** por defecto, pero **sí detecta anomalías** (ej: `weird.log` con IRC/beaconing).
    - La distinción clave no es *"observar vs. clasificar"*, sino:
      > **"Zeek es una plataforma de *generación de telemetría* (logs estructurados), mientras que Suricata y aRGus son sistemas de *detección de amenazas* (alertas accionables)."**

- **Framing propuesto (más preciso):**
  > *"Los resultados demuestran que Zeek, en su configuración por defecto, **no está diseñado como un IDS**, sino como un sistema de observabilidad que requiere post-procesamiento para generar alertas. Suricata, aunque basado en firmas, **tampoco detectó el tráfico histórico** debido a la ausencia de reglas relevantes. En contraste, aRGus NDR, con su enfoque basado en comportamiento, **supera las limitaciones de los sistemas tradicionales** al no depender de firmas estáticas. Este experimento subraya la necesidad de distinguir entre *herramientas de telemetría* (Zeek), *IDS basados en firmas* (Suricata), y *NDR basados en ML* (aRGus)."*

- **Términos clave para incluir:**
    - **Telemetría vs. Detección** (Zeek no es un IDS *out-of-the-box*).
    - **Dependencia de reglas** (Suricata).
    - **Robustez temporal** (aRGus detecta tráfico de 2011 sin reglas históricas).

**Conclusión:** **Refinar el framing** para evitar ambigüedades y destacar la **taxonomía de herramientas**.

---

---
### **Pregunta 3 — Zeek Phase 2 (scripts avanzados)**
**Respuesta:**
**No es necesario para el paper actual, pero sí valioso como *future work*.**
- **Argumentos a favor de omitir Phase 2:**
    - **Los resultados de Phase 1 ya son fuertes:**
        - Zeek (default) **no es un IDS**, y esto **refuerza el hallazgo central** (diferenciación entre telemetría y detección).
        - Incluir Phase 2 **complicaría la narrativa** sin añadir valor clave al mensaje principal.
    - **Riesgo de *over-engineering*:**
        - Si Zeek con scripts avanzados **sí detecta Neris**, podría **debilitar el argumento** de que Zeek no es un IDS.
        - Si **no detecta**, el resultado es redundante.

- **Argumentos a favor de incluir Phase 2 (opcional):**
    - **Para revisores escépticos:**
        - Algunos podrían argumentar: *"Zeek no detectó porque no usaste scripts de seguridad"*.
        - Una **mención breve** en *future work* o un apéndice con resultados preliminares **cierra este flanco**.
    - **Contribución adicional:**
        - Si Zeek + Intel Framework **mejora significativamente** (ej: Recall > 0.5), podría ser un **hallazgo secundario interesante**.

- **Recomendación final:**
    - **No incluir en el paper principal** (Phase 1 es suficiente).
    - **Añadir en *future work*:**
      > *"Como trabajo futuro, evaluaremos Zeek con scripts de detección avanzados (ej: Intel Framework, threat feeds) para cuantificar cómo afecta su capacidad de detección en escenarios históricos."*
    - **Si hay tiempo antes de arXiv:**
        - Ejecutar **un experimento rápido** con `policy/tuning/json-logging.zeek + frameworks/intel/seen` y reportar resultados en un **apéndice** (no en el cuerpo principal).

**Conclusión:** **Phase 1 es suficiente para el paper. Phase 2 puede esperar.**

---
---
### **📌 Resumen de Decisiones para el Paper**
| **Pregunta** | **Decisión del Consejo** | **Acción Concreta** |
|--------------|--------------------------|---------------------|
| **Validez metodológica** | Aceptable, pero justificar asimetría. | Añadir párrafo en §3 (Metodología) explicando modo offline vs. live. |
| **Framing científico** | Refinar para evitar ambigüedades. | Reescribir §8.13 con la taxonomía: *telemetría (Zeek) vs. detección (Suricata/aRGus)*. |
| **Zeek Phase 2** | No incluir en el cuerpo principal. | Mencionar en *future work* o apéndice. |

---
**Observación final:**
El experimento de tres vías **ya es una contribución sólida** para arXiv. Los resultados **refuerzan la necesidad de sistemas NDR basados en comportamiento** (como aRGus) para escenarios con tráfico histórico o amenazas sin firmas. **No sobrecarguéis el paper con Phase 2**: el mensaje central es claro y potente tal como está.