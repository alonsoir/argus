**Respuestas concisas del Consejo — aRGus NDR DAY 147**

### **Pregunta 1 — Validez metodológica**
**No es un problema grave de fairness; es estándar y defendible.**

El modo **offline** (`zeek -r pcap`) es ampliamente aceptado y preferido en papers académicos con datasets históricos (CTU-13 incluido) porque garantiza reproducibilidad perfecta, zero packet loss y elimina variables de timing/hardware. Suricata live con tcpreplay es válido para simular entorno real, pero la asimetría se justifica explícitamente: Zeek se evalúa en su uso más común y fuerte (análisis forense completo), mientras Suricata en modo signature-based operativo.

Revisor podría comentar, pero se neutraliza fácilmente: "Zeek se ejecutó en modo offline estándar para PCAPs históricos, maximizando su capacidad de observabilidad; Suricata en live para reflejar despliegue típico de reglas ET Open." Incluye nota sobre pérdida de paquetes en live si aplica. **Fuerte**.

### **Pregunta 2 — Framing científico**
**Correcto y publicable; es el hallazgo más valioso.**

Refina ligeramente: *"Zeek funciona como plataforma de network telemetry y observabilidad avanzada (logs ricos en weird, beaconing, IRC, SMB), no como IDS signature/out-of-the-box. El experimento de tres paradigmas resalta la distinción clave: signature matching (Suricata) vs. logging profundo sin alerta automática (Zeek) vs. clasificación comportamental ML (aRGus). Este gap explica por qué herramientas de análisis generan gran volumen de datos de calidad pero pocas alertas listas para SOC sin inversión adicional en scripting."*

Este framing es preciso, evita atacar a Zeek y posiciona tu contribución en la literatura comparativa (muchos papers ya distinguen Zeek como NSM más que IDS clásico).

### **Pregunta 3 — Zeek Phase 2 (scripts avanzados)**
**Sí merece la pena ejecutarlo antes de arXiv, pero como Phase 2 opcional y rápida (no bloqueante).**

Los resultados de **default/out-of-the-box** (F1 0.042) son ya muy fuertes para la narrativa central (Zeek no es IDS plug-and-play). Phase 2 con Intel framework, threat feeds y policies adicionales fortalecerá el paper: muestra esfuerzo de fair comparison y cuantifica cuánto se gana con tuning (probablemente sube recall pero no a nivel ML).

Hazlo si el esfuerzo es bajo (1-2 días): documenta "default vs. tuned". Si no, ponlo claramente como **future work** con mención a logs existentes (weird.log etc.) que habilitan extensiones. Los resultados actuales son suficientemente robustos como contribución. Prioriza envío si el resto del paper está listo.

**Recomendación general del Consejo:** Procede con confianza. La tabla es impactante y el framing diferencia claramente los paradigmas. Enfatiza reproducibilidad (CTU-13 público) y la superioridad comportamental. Buen trabajo hoy.

Listo para más detalles o revisión de secciones específicas.