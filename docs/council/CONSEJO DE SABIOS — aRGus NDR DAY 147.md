Las tres preguntas más importantes para el Consejo. Hay más cosas que discutir pero estas son las que más pueden afectar al paper:

---

**CONSEJO DE SABIOS — aRGus NDR DAY 147**
*Tres preguntas, respuestas concisas. Contexto mínimo necesario.*

**Contexto:** Experimento de tres paradigmas completado. CTU-13 Neris (2011, 646 flujos maliciosos, 12,075 benignos). Resultados:

| Sistema | F1 | Precision | Recall | TP |
|---|---|---|---|---|
| Suricata 6.0.10 (ET Open, 50K reglas) | 0.000 | — | 0.000 | 0 |
| Zeek 8.1.2 (default scripts, offline) | 0.042 | 1.000 | 0.022 | 14 |
| aRGus NDR (ML behavioral) | 0.9985 | 0.997 | 1.000 | 646 |

Zeek en modo offline (`zeek -r pcap`). Suricata en modo live (AF_PACKET + tcpreplay). Zeek genera logs completos (weird.log: IRC, beaconing, SMB) pero no los convierte en alertas bajo scripts por defecto.

---

**Pregunta 1 — Validez metodológica:**
Zeek se ejecutó en modo offline (lee el pcap directamente). Suricata se ejecutó en modo live (tcpreplay desde VM cliente). ¿Es esta asimetría un problema de fairness que un revisor podría objetar, o el modo offline es estándar aceptado en investigación con pcaps históricos y refuerza la comparativa al eliminar pérdida de paquetes?

**Pregunta 2 — Framing científico:**
La narrativa propuesta: *"Zeek es una plataforma de observabilidad de red con detección selectiva — no un IDS fallido. La distinción entre observar anomalías y clasificar comportamiento es el hallazgo central del experimento de tres vías."* ¿Es este framing correcto y publicable, o hay una formulación más precisa?

**Pregunta 3 — Zeek Phase 2 (scripts avanzados):**
¿Merece la pena ejecutar Zeek con scripts avanzados (Intel framework, threat feeds, policy scripts adicionales) como Phase 2 antes de enviar a arXiv, o los resultados de Phase 1 (default, out-of-the-box) son suficientemente fuertes como contribución y Phase 2 puede quedar como future work?

---

Pega esto en cada modelo del Consejo y tráeme las respuestas. Con eso diseñamos el prompt de mañana.