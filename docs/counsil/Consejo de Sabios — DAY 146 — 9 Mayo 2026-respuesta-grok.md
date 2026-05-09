**Respuesta del Consejo de Sabios — Day 146 (9 Mayo 2026)**

Excelente avance. Las tres deudas técnicas cerradas son limpias y el bootstrap más robusto es un win de calidad. El experimento comparativo es sólido en diseño y muy relevante para el paper. Vamos directo a las preguntas.

### 1. Interpretación del resultado (0 alertas Suricata vs F1≈0.9985 aRGus)

**No es que "Suricata falla". Es que Suricata hace exactamente lo que está diseñado para hacer: signature-based detection de amenazas conocidas.**

- CTU-13 Neris es tráfico de botnet de **2011**. Las reglas ET Open actuales (2026) se centran en IOCs, patrones, C2 modernos, exploits recientes, etc. Las firmas específicas para comportamientos de Neris (spam + HTTP C2 + clickfraud de aquella época) han sido depuradas, desactivadas o nunca fueron lo suficientemente genéricas para sobrevivir 15 años de mantenimiento.
- Signature-based IDS **son reactivos por diseño**. Excelentes para known-bad rápido y bajo FP cuando la firma existe, pero pierden todo contra variantes, tráfico obfuscado, o amenazas cuyo patrón ya no está en el ruleset actual.
- aRGus NDR (ML + behavioral/anomaly + fast detector) es **diseñado precisamente para este gap**: detecta patrones estadísticos/anómalos en flows aunque no haya firma explícita. El Recall=1.0000 y FPR bajísimo demuestran que captura la esencia del comportamiento botnet sin depender de strings/payloads específicos obsoletos.

**Interpretación correcta**: Esto valida la tesis central del proyecto — **híbrido o ML-augmented NDR complementa (y en escenarios legacy/out-of-date-rules, supera) a los signature engines puros**. No es una crítica a Suricata; es una demostración empírica de sus limitaciones conocidas y de por qué NDR/ML es necesario.

### 2. ¿Repetir con ruleset ET Open ~2011?

**Sí, absolutamente recomendado.** Es el control ideal para separar dos hipótesis:

- **Hipótesis A** (firma nunca existió o era débil) → incluso en 2011 Suricata tendría bajo recall.
- **Hipótesis B** (firma existió pero fue removida) → ruleset histórico debería dar recall alto.

**Disponibilidad**: Archivos históricos completos de ET Open no son triviales de encontrar en mirrors públicos actualizados (el sitio oficial rota versiones). Buscar en GitHub repos antiguos de OSSIM/SecurityOnion, Wayback Machine en rules.emergingthreats.net, o foros de la época (2011-2012). Si no aparece fácilmente, documentad el intento y usad un ruleset ET Open congelado en una fecha cercana (ej. 2012-2013) como proxy. Vale la pena el esfuerzo para robustecer la sección de comparación.

### 3. ¿Dónde ponerlo en el paper?

**Ampliar §8.7 (Comparison with State of the Art) con un subsection dedicado (§8.7.3 o similar)** y, si el espacio lo permite, un breve highlight en §8.13 o una nueva subsección de "Lessons from Legacy Datasets".

- El resultado es **oro para discusión**: ilustra perfectamente el "signature aging" problem y la ventaja de enfoques basados en ML/flujos.
- Incluid tablas claras: versión Suricata + ruleset (actual), hardware, replay speeds, alertas generadas, métricas aRGus.
- Mencionad limitaciones (ver punto 4) para mantener credibilidad académica.

### 4. Problemas metodológicos potenciales

La comparativa está bien diseñada (misma VM, mismo hardware, mismo dataset, mismo replay). Posibles mejoras/avisos:

- **Configuración Suricata**: ¿Usasteis `suricata.yaml` default o tuned (multi-thread, runmodes af-packet, etc.)? ¿Todas las reglas enabled (incluyendo policy-based)? ¿HTTP/decoder depth suficiente para el tráfico Neris?
- **Detección de flows vs paquetes**: aRGus parece flow/ML-centric; Suricata genera alertas en paquetes. Asegurad apples-to-apples en evaluación (e.g. mapear alertas a flows).
- **Ground truth**: CTU-13 tiene labels a nivel de capture; confirmad que el replay preserva el labeling.
- **Velocidad de replay**: A 100 Mbps en VM debería estar bien, pero verificad drops en Suricata (stats.log).
- **Reglas custom**: ¿Ninguna? Correcto para fairness.

Ninguno invalida el resultado actual, pero documentad la config exacta de Suricata para reproducibilidad.

**Para mañana (Day 147)**: Proceded con §8.13 o ampliación de 8.7. Incluid el experimento histórico si lo conseguís rápido. Commit v20 suena bien.

**Recomendación adicional del Consejo**: Este resultado refuerza el valor de aRGus como complemento ligero a Suricata (e.g. Suricata para known + aRGus para unknown/zero-day behavioral). Considerad una sección o future work sobre "hybrid deployment" (Suricata + aRGus en parallel).

Seguimos. Buen trabajo hoy.