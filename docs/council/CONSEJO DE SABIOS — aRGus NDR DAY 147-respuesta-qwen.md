**CONSEJO DE SABIOS — RESPUESTAS TÉCNICAS — DAY 147**
*Respuestas concisas, fundamentadas en metodología de investigación en ciberseguridad.*

---

### **Respuesta 1 — Validez metodológica: offline vs. live**

**Veredicto**: ✅ **No es un problema de fairness**; es una decisión metodológica defendible y, de hecho, *conservadora* para Zeek.

**Argumentación técnica**:
| Aspecto | Justificación |
|---------|--------------|
| **Estándar en investigación** | El modo `zeek -r pcap` es la práctica establecida en literatura con datasets históricos (CTU-13, CIC-IDS, etc.) para garantizar reproducibilidad exacta [[18]][[30]]. |
| **Eliminación de confounders** | El modo offline elimina pérdida de paquetes, jitter de tcpreplay y variabilidad de AF_PACKET como variables de ruido. Si Zeek tuviera ventaja, sería por *menos* ruido, no por más capacidad de detección. |
| **Transparencia proactiva** | Añadir una frase en §8: *"Zeek was executed in offline mode to ensure bit-exact reproducibility; this removes packet loss as a confounding variable and represents a best-case scenario for signature/logging-based approaches."* |

**Si un revisor objeta**: La réplica es que Suricata *también* se puede ejecutar en offline (`suricata -r pcap`) y los resultados son idénticos (0 alertas), confirmando que la diferencia no es artefacto del modo de ejecución.

---

### **Respuesta 2 — Framing científico: Zeek como plataforma de observabilidad**

**Veredicto**: ✅ **El framing es correcto, preciso y publicable**. Refinamiento sugerido:

> *"Zeek is a network observability framework that logs protocol semantics and anomalies (e.g., weird.log entries for IRC/beaconing) but delegates classification policy to the analyst. aRGus NDR, by contrast, embeds behavioral classification in its inference pipeline. The experiment isolates this paradigmatic distinction: observation ≠ automatic adjudication."*

**Por qué funciona**:
- **Fiel a la filosofía de Zeek**: Los creadores de Zeek siempre han enfatizado que es un "lenguaje para describir tráfico", no un IDS turnkey [[51]][[53]].
- **Evita la falacia del "falso negativo"**: Zeek no "falló" al no alertar; registró los indicadores (weird.log) pero no los mapeó a "malicioso" por defecto. Eso es diseño, no bug.
- **Contribución conceptual**: Clarifica una confusión frecuente en literatura donde se compara "Zeek IDS" vs "ML NDR" sin distinguir entre *logging* y *clasificación automática*.

**Cita para el paper**:
```latex
% En §8.13 o Discusión:
\emph{The zero-alert outcome for Suricata and the low-recall for Zeek default scripts do not indicate malfunction; they reflect the design philosophy of each tool: signature matching requires prior knowledge, and observability frameworks require explicit policy. Behavioral ML approaches like aRGus learn implicit policy from traffic patterns.}
```

---

### **Respuesta 3 — Zeek Phase 2: ¿scripts avanzados antes de arXiv?**

**Veredicto**: 🎯 **Enviar con Phase 1 (default) como resultado principal; Phase 2 como Appendix o Future Work**.

**Razones estratégicas**:
| Opción | Pros | Contras | Recomendación |
|--------|------|---------|---------------|
| **Phase 1 only** | Mensaje limpio: paradigma observability vs. classification. Submit más rápido. | Revisor podría preguntar "¿y con reglas personalizadas?" | ✅ **Principal** |
| **Phase 2 incluido** | Preempta crítica de "Zeek no estaba bien configurado". Muestra exhaustividad. | Riesgo de diluir el hallazgo central; añade complejidad metodológica (¿qué feeds? ¿qué políticas?). | 📎 **Appendix B** |
| **Phase 2 como Future Work** | Mantiene foco; reconoce limitación sin sobrecargar el paper. | Algunos revisores podrían verlo como "trabajo incompleto". | ✅ **Mención explícita en §9** |

**Compromiso óptimo**:
1. Mantener Phase 1 como resultado principal en §8.13.
2. Añadir un **Appendix B: "Zeek with Enhanced Configuration (Exploratory)"** con:
    - 2-3 scripts representativos (ej: `intel.framework` con un feed público de 2011, `policy/tuning/local.zeek` para alertar en weird.log).
    - Resultado esperado: Recall mejora modestamente (ej: 0.15-0.30), pero requiere mantenimiento manual de feeds — lo que *refuerza* la tesis central sobre deuda técnica de firmas.
3. En §9 (Future Work): *"Extending Zeek with historical threat intelligence could improve recall on legacy threats; however, this reintroduces the signature maintenance burden that behavioral approaches aim to reduce."*

---

### **RESUMEN EJECUTIVO PARA EL PAPER**

```latex
% En §8.13 Conclusiones:
\begin{itemize}
  \item \textbf{Metodología}: Offline execution for Zeek ensures reproducibility and removes packet loss as confounder; results are conservative for logging-based approaches.
  \item \textbf{Framing}: Zeek's default behavior reflects its design as an observability framework, not a turnkey IDS; the gap between logging and classification is the key insight.
  \item \textbf{Scope}: Phase 1 (default configs) isolates paradigm differences; Phase 2 (enhanced Zeek) is documented in Appendix B as exploratory, reinforcing the maintenance trade-off of signature-dependent systems.
\end{itemize}
```

---

**Frase de cierre para el Consejo**:
> *"No estamos comparando herramientas, estamos comparando filosofías: registrar el mundo vs. juzgarlo automáticamente. El silencio de Suricata y la observación pasiva de Zeek no son errores; son coordenadas en el espectro de la detección de amenazas."*

¿Necesitáis que redacte el Appendix B en LaTeX o prepare el snippet para la frase de transparencia metodológica en §8? 🛡️🧠