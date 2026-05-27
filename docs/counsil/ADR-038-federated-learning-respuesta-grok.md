**ADR-038 — Federated Learning Distribuido para aRGus NDR**  
**Revisión del Consejo de Sabios — DAY 121**

El borrador es **ambicioso, bien estructurado y alineado** con la filosofía **Via Appia Quality**: prioriza la misión crítica (hospitales/municipios de bajo presupuesto), mantiene el foco en privacidad, reproducibilidad y fail-closed, y construye directamente sobre los cimientos ya sólidos (XGBoost ligero, firma Ed25519, ChaCha20-Poly1305, plugin architecture y scheduler conservador).

Es una evolución natural del sistema “escudo que aprende”. No es especulativo; se apoya en componentes existentes y propone un camino realista (Q4 2026 prototipo). Sin embargo, requiere refinamientos importantes en **seguridad/primeridad**, **viabilidad técnica** (especialmente con XGBoost) y **gobernanza** antes de pasar de borrador a ADR aprobado.

### Fortalezas del borrador
- Arquitectura en fases clara y modular (ingesta → anonimización → entrenamiento local → empaquetado).
- Scheduler conservador excelente: prioridad absoluta a la misión crítica (CPU <20%, no alerts, ventanas nocturnas).
- Valor de los **metadatos** aunque el modelo falle: esto es oro para detección temprana de patrones emergentes (ransomware en Pekín → alerta a Badajoz).
- Variantes de hardening (AppArmor → seL4) con sinergia explícita a ADR-029.
- Impacto en el paper bien identificado (elevación a “sistema inmune distribuido” en §6/§7).
- Enfoque asíncrono + BitTorrent: adecuado para nodos edge de bajo presupuesto.

### Debilidades y riesgos críticos a abordar

1. **Entrenamiento incremental con XGBoost en entorno federado**  
   XGBoost no se “promedia” trivialmente como redes neuronales (FedAvg funciona mal directamente sobre árboles).  
   Opciones reales de la literatura:
    - **FedXgbBagging** o enfoques de bagging/ensemble (cada nodo entrena árboles adicionales sobre bootstrap local y se agregan como ensemble).
    - **Cyclic training** o warm-start secuencial.
    - **SecureBoost** (para vertical FL, pero más complejo).
    - **Weighted Gradient Boosting** o frameworks como Federated XGBoost (con summary updates en lugar de modelos completos).

   Recomendación: En la FASE 3, define explícitamente **qué se envía al central** (no el modelo .ubj completo si es pesado; mejor updates de gradientes/estadísticas o árboles delta + metadatos). Mantén el modelo local ligero (~2MB) y permite warm-start con `xgb.train(..., xgb_model=previous)`.

2. **Anonimización y Privacidad Diferencial (P1)**  
   Eliminar IPs, normalizar puertos y agregar temporalmente es un buen inicio, pero **insuficiente** solo.  
   Para tráfico de dispositivos médicos (features de flows), existe riesgo real de re-identificación por patrones únicos (horarios de procedimientos, volúmenes de tráfico específicos de MRI/ECG, etc.).

   Usa **ε-differential privacy** con ruido calibrado (Laplace o Gaussian según sensibilidad).
    - ε bajo (ej. 1.0–5.0) para fuerte privacidad, pero evalúa trade-off utility (puede degradar F1).
    - DPIA **obligatoria** antes de cualquier piloto real.
    - Considera synthetic data generation DP (como en los datasets DeepSeek ya usados) o técnicas de tabular DP.

3. **Web-of-Trust vs PKI (P2)**  
   Web-of-Trust (PGP-style) es descentralizado pero escala mal y es frágil en práctica (usuarios deben firmar manualmente).  
   Para infraestructura crítica: **híbrido recomendado**:
    - Nodos centrales con **PKI interna jerárquica** (root CA controlada por la entidad gobernanza aRGus).
    - Nodos edge firman con keypair local y se unen vía web-of-trust ligera o certificados emitidos por centrales tras onboarding verificado (ej. attestación hardware o aprobación manual inicial).
    - Revocación rápida (CRL u OCSP ligero).

4. **Agregación federada (P3)**  
   Añade una subsección explícita con opciones:
    - Ensemble de modelos (selección o stacking de los mejores locales).
    - FedAvg ponderado por calidad local (F1, tamaño de dataset).
    - Métodos específicos para trees: bagging, SecureBoost, o agregación de updates de split.
    - Gates G1-G5 son buenos; refuerza G3 (KL-divergence) y añade detección de envenenamiento (model poisoning detection).

5. **Scheduler en entorno hospitalario (P4)**  
   Integración con HIS/RIS es ideal pero compleja (privacidad adicional, disponibilidad).  
   Alternativas prácticas:
    - Monitoreo pasivo de tráfico médico (patrones conocidos de dispositivos).
    - Señales de “baja actividad segura” vía ml-detector (no alerts + bajo throughput).
    - Override manual o por política del hospital.

6. **Incentivos y gobernanza (P5)**  
   Crítico. Propón:
    - Acceso preferente/temprano a modelos globales mejorados.
    - “Puntos de contribución” que desbloquean soporte prioritario o actualizaciones.
    - Modelo de gobernanza multi-stakeholder (hospitales, municipios, investigadores, entidad neutral).

### Recomendaciones concretas para pulir el ADR (antes de merge)

- **Añadir sección “Riesgos y Mitigaciones”** con tabla:  
  | Riesgo | Mitigación | Severidad |
  |--------|------------|-----------|
  | Degradación global por modelo envenenado | Gates G1-G5 + sandbox 24h + rollback automático | Alta |
  | Overhead en edge | Límite estricto de árboles + scheduler + entrenamiento solo en baja actividad | Media |
  | Re-identificación | DP (ε≤X) + DPIA + auditoría externa | Alta |
  | Complejidad agregación XGBoost | Prototipo con FedXgbBagging o ensemble primero | Media |

- **Reforzar secuenciación**:
    1. ADR-026 XGBoost fully merged + incremental training validado.
    2. RESEARCH-FEDERATED-001 (anonimización DP + agregación trees + web-of-trust).
    3. ADR-029 hardening.
    4. ml-trainer mínimo viable (solo metadatos + un modelo simple primero).
    5. Piloto aislado (1-2 hospitales + 1 central).

- **Impacto en paper**: Mantén en Future Work, pero añade viabilidad técnica basada en prototipos existentes (warm-start XGBoost ya probado, firma, etc.). Incluye diagrama actualizado.

- **Preguntas adicionales al autor (Alonso)**:
    - ¿Qué exactamente se enviaría en FASE 4? (modelo completo, updates, solo metadatos+stats).
    - ¿Presupuesto computacional real en nodos edge hospitalarios? (¿Raspberry-level o mejor?).
    - ¿Cómo manejar non-IID data (tráfico Extremadura vs Pekín)? FedProx o similar podría ayudar.

### Veredicto del Consejo
**Aprobar como BORRADOR con prioridad ALTA**, pero **NO implementar** hasta:
- Versión 2 incorporando las precisiones arriba (especialmente agregación XGBoost, DP concreta y web-of-trust híbrida).
- Prototipo mínimo de FASE 3 (entrenamiento local incremental + gates) en la misma VM de ADR-026.
- Validación de overhead (CPU/RAM durante entrenamiento local).

Esto mantiene la integridad científica y la seguridad militar-grade que define aRGus. El concepto de “sistema inmune distribuido” es potente y diferenciador; hagámoslo robusto desde el día 1.

*Via Appia Quality — un escudo que aprende, nunca una espada.*

¿Quieres que ayudemos a redactar secciones específicas (ej. “Agregación de Modelos XGBoost” o “Riesgos y Mitigaciones”)? ¿O que profundicemos en un gate concreto para el piloto?

¡Adelante con la iteración DAY 121+!