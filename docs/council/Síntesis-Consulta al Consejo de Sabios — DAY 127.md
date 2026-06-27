Síntesis del Consejo DAY 127 — 8/8
Antes de generar los documentos, la síntesis ejecutiva:
Consenso unánime:

P1: Taxonomía suficiente. Formalizar en docs/SECURITY-PATH-PRIMITIVES.md. PathPolicy enum como semántica explícita (ChatGPT/Grok). resolve_model() como futura primitiva para modelos firmados ADR-026 (Kimi — más justificado que resolve_log()).
P2: Property → Fuzzing (libFuzzer) → Mutation. Formalizar patrón en docs/testing/PROPERTY-TESTING.md DAY 128.
P3: "La herramienta propone; el modelo de amenazas decide." Criterio: código propio → fix bloqueante; third-party → documentar con justificación.
P4: Alcanzable. Riesgo principal: Kimi plantea pregunta crítica — ¿FEDER es demo NDR standalone o requiere federación funcional? Esto hay que clarificarlo con Andrés Caro Lindo antes de julio.
P5: Sí, publicable. Framing correcto: "unit testing insuficiente para validar fixes de seguridad → capa de propiedades necesaria."

Nuevas reglas permanentes DAY 127:

Documentar taxonomía safe_path con diagrama de decisión.
Criterio de triage Snyk formalizado — código propio vs third-party.
resolve_model() en backlog para ADR-026+ (modelos firmados son superficie crítica).
Clarificar scope FEDER antes de julio.