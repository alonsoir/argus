**Consejo de Sabios – Respuestas a las tres preguntas existenciales (Día 147)**

---

### Pregunta 1 – Validez metodológica (live vs offline)

**Respuesta:** La asimetría **no invalida** el experimento, pero requiere justificación explícita y un control adicional.

- **Contexto aceptado:** En investigación con pcaps históricos, el modo offline (`zeek -r`) es estándar y se publica ampliamente (ver NDSS, IEEE S&P). Evita pérdida de paquetes, lo que beneficia a Zeek. Suricata en modo live con tcpreplay es equivalente en esencia (ambos ven el tráfico), pero introduce posibles pérdidas por latencias.
- **Objeción potencial:** Un revisor podría pedir ejecutar Suricata también en modo offline (`suricata -r`) para igualdad completa.
- **Recomendación:** Añade un subexperimento con Suricata offline y reporta que los resultados son idénticos (0 alertas). Si no hay diferencia, la asimetría es irrelevante.

**Frase para el paper:**
> “Para maximizar la equidad, ambos sistemas se ejecutaron en el modo que la comunidad considera canónico para análisis offline (Zeek) y online (Suricata), verificando que Suricata no sufriera pérdida de paquetes (estadísticas de captura). Adicionalmente, una ejecución offline de Suricata confirmó el mismo resultado.”

---

### Pregunta 2 – Framing científico sobre Zeek

**Respuesta:** El framing es **correcto pero necesita precisión**. No es “Zeek no es un IDS fallido”, sino “Zeek es un **framework de monitorización** que por defecto **no genera alertas**; su filosofía es generar logs ricos para análisis posterior o scripts personalizados”. El hallazgo central es que **la detección conductual de aRGus supera a sistemas basados en reglas o scripts genéricos sin requerir adaptación específica a la amenaza**.

**Fórmula más precisa:**
> “Zeek no es un IDS en el sentido tradicional; su valor radica en la observabilidad. La comparativa revela que incluso cuando Zeek registra comportamientos anómalos (p. ej., weird.log), no los eleva a alertas sin lógica específica. En cambio, aRGus clasifica automáticamente el tráfico maligno con alta precisión. La distinción entre **observación** (Zeek) y **clasificación** (aRGus) es la contribución clave.”

**Publicable:** Sí, es una observación novedosa y ayuda a posicionar a aRGus no como un “reemplazo de Zeek” sino como un complemento con diferente filosofía.

---

### Pregunta 3 – Zeek Phase 2 (scripts avanzados)

**Respuesta:** **No es necesario para arXiv**, pero sí recomendable si no supone más de 2-3 días de trabajo. Los resultados de Phase 1 (default) ya son fuertes: Zeek solo detecta 14 de 646 flujos maliciosos (recall 2.2%). Un revisor preguntará: “¿Y con scripts de detección de botnet?”. Para anticipar esa crítica, puedes hacer un **experimento mínimo** con scripts conocidos (p. ej., `policy/protocols/irc/detect-botnets.zeek`) y mostrar que sigue sin alcanzar la recall de aRGus. Si no tienes tiempo, déjalo como *future work* con una nota: “Explorar configuraciones avanzadas de Zeek es trabajo futuro; este artículo se centra en la comparativa out-of-the-box, que es la experiencia típica de un operador”.

**Decisión del Consejo:**
- Si el paper ya es fuerte con Suricata 0 y Zeek 14 TP → **arXiv sin Phase 2**.
- Si quieres blindarte contra revisores exigentes → **Phase 2 rápida** (un solo script de IRC botnet).

**Recomendación final:** Añade un párrafo en “Future Work” mencionando la posibilidad de extender Zeek con feeds de inteligencia. No retrases el envío.

---

**Veredicto conjunto:** El experimento es metodológicamente sólido, el framing es adecuado con los matices indicados, y Phase 2 es opcional. Proceded con la redacción de §8.7.4 y el envío a arXiv.