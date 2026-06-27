**Respuesta del Consejo de Sabios — ADR-040: ML Plugin Retraining Contract**

El Consejo de Sabios aprueba el ADR-040 en su esencia como un contrato científico robusto para el reentrenamiento de plugins ML en aRGus NDR. Las reglas propuestas alinean con evidencia empírica en **continual learning** para sistemas de detección de intrusiones (NIDS/NDR): catastrophic forgetting es un problema documentado en IDS basados en ML, donde modelos secuenciales pierden capacidad en ataques clásicos al incorporar nuevos datos. La validación **walk-forward** es el estándar oro para datos temporales como flujos de red (CTU-13 muestra fuerte correlación temporal en sesiones botnet), evitando el leakage de información futura que infla métricas en k-fold random (hasta 5-10 pp de F1 artificial). El golden set inmutable actúa como ancla de reproducibilidad, similar a holdout sets en benchmarks de ciberseguridad. Los guardrails de regresión protegen contra degradaciones silenciosas en Recall (crítico en seguridad: falsos negativos = ataques no mitigados). IPW + exploración forzada mitiga feedback loops y distributional shift, técnicas validadas en causal inference y bias mitigation. La competición de algoritmos evita sesgo de confirmación; en datos tabulares de flujos de red (features como duración, paquetes, bytes), CatBoost destaca en manejo de categóricas y latencia de inferencia, LightGBM en velocidad, XGBoost como baseline sólido — la elección debe ser empírica.

El ADR refuerza ADR-025 (firma Ed25519 fail-closed) con semántica de calidad ML, y prepara el terreno para ADR-026 (arquitectura federada P2P). Referencia al playbook de Mercadona Tech (búsquedas a escala sin GPU, latencia p50 ~12 ms, bajo consumo RAM) es adecuada: prioriza baja latencia y reproducibilidad sobre precisión marginal.

**Recomendación general**: Adoptar las 5 reglas con ajustes menores para mayor rigor científico y operatividad. Crear un sub-ADR o sección dedicada al golden set (definición, cobertura mínima de escenarios CTU-13: Neris, Rbot, Murlo + tráfico benigno representativo, hash SHA-256, verificación CI). Añadir replay selectivo (memory replay) como mecanismo complementario a IPW para combatir catastrophic forgetting en escenarios de continual learning.

A continuación, respuesta a la **pregunta abierta** siguiendo el formato solicitado:

### Pregunta: ¿El pipeline de evaluación es un componente aRGus (interno) o CI/CD externo?

- **Recomendación concreta**: **Opción A — Componente interno** (ejecutado dentro del entorno Vagrant/dev, integrado en `make test-all` y ml-detector), con triggers opcionales hacia CI/CD externo (GitHub Actions) para la fase de firma/promoción final. No puramente externo (Opción B).

- **Justificación técnica**:
    - Reproducibilidad científica exige que la evaluación use **exactamente los mismos binarios, entorno y datos** que el pipeline de producción (eBPF/XDP o libpcap → ml-detector). Un pipeline interno garantiza zero skew entre eval y runtime (mismo Python/Rust env, mismas dependencias, mismo hardware emulation en Vagrant). Walk-forward, golden set verification y guardrails son tests unitarios/integración que deben correr en dev antes de cualquier commit/PR.
    - En literatura MLOps para seguridad, las evaluaciones críticas (drift, regression guards) viven cerca del código para fail-fast y auditoría. CI/CD externo es excelente para orquestación (histórico, artefactos, triggers en push de candidato), pero no debe ser la fuente única de verdad — riesgo de divergencia (diferentes runners, versiones de libs). Combinación híbrida es práctica estándar: core eval en repo (reproducible localmente), CI para gating de firma Ed25519.
    - Alineado con referencia Mercadona: procesos de calidad (quality guard) integrados en el flujo de desarrollo, no solo en CI remoto.

- **Riesgo identificado**:
    - Si puramente interno (sin CI): falta de trazabilidad histórica y posible bypass manual en entornos distribuidos (Año 1 post-FEDER). Si puramente externo: acoplamiento débil con datos sensibles/entrenamiento (problemas de acceso seguro a golden set o PCAPs), y dificultad para reproducir fallos localmente en Vagrant.
    - Riesgo adicional: sin replay/memory mechanisms explícitos, catastrophic forgetting puede pasar los guardrails del -2% en ciclos tempranos.

- **Test mínimo reproducible (en Vagrant)**:
    - Crear script `ml-evaluation-pipeline.py` en ml-detector/ que acepte `--split-date`, `--golden-hash`, `--current-plugin-path`, `--candidate-path`. Ejecuta walk-forward sobre dataset temporal, evalúa F1/Recall/FPR vs golden (assert |Δ| ≤ umbrales), genera informe JSON + diversidad (pre/post IPW). Integrar en Makefile: `make test-ml-eval`. En CI (GitHub Actions): workflow separado que clona, corre el script interno con artefactos, y solo si exit 0 procede a `ed25519_sign()`. Verificar con `sha256sum golden_set/ && python test_golden.py --arch $(uname -m)`. Repetir con datos sintéticos CTU-13 subsets para zero-regresión.

**Consecuencias actualizadas**:
- Positivas: Contrato auditable + reproducibilidad científica (publicable post-FEDER). Golden set + walk-forward como baseline para papers en continual NDR.
- Negativas/Trade-offs: Requiere disciplina para crear golden set **antes** de cualquier reentrenamiento (proactivo, como en el ADR). El 5% exploración manual necesita proceso ligero (e.g., oráculo semi-automático vía RAG-security o revisión por equipo). Competición añade ~horas-días iniciales, pero amortizada por mejor elección (posible CatBoost/LightGBM ganando en latencia para edge ARM/RPi).

**Estado de implementación recomendado**:
- Definición contrato + golden set: Iniciar inmediatamente (pre-FEDER si posible, mínimo cobertura CTU-13 canónica).
- Walk-forward script + guardrail en firma: Post-FEDER, integrar en plugin-system.
- IPW + 5% exploración + memory replay: Año 1, con informe de diversidad obligatorio.
- Competición algoritmos: Ejecutar sobre CTU-13 + datos internos antes de lock-in XGBoost; documentar ganador con métricas (F1, Recall@low FPR, inferencia ms/paquete en x86/ARM).

El Consejo recomienda complementar con:
- Monitoreo de drift en producción (estadístico + performance) para trigger retraining.
- Versionado completo (modelo + datos + código + config) para rollback.
- Tests de robustness (adversarial examples en flujos) en el pipeline de eval.

Este contrato eleva aRGus de “funciona en VM” a sistema ML confiable y científico para infraestructura crítica (hospitales/municipios). Cumple método científico: hipótesis falsables (guardrails), reproducibilidad (golden + walk-forward + hashes), y experimentación controlada (competición).

El Consejo queda disponible para revisar el golden set draft, resultados de la competición o implementación inicial del pipeline interno. ¡Adelante con la disciplina proactiva!