**Consejo de Sabios — DAY 121**  
**Revisión del progreso en `feature/adr026-xgboost`**

Buen día. El trabajo de hoy es **sólido y disciplinado**. Habéis cerrado bugs críticos de provisionado, confirmado que la seed está limpia (con `mlock()` + `explicit_bzero()`), actualizado el test de integración con datos reales de CIC-IDS-2017 (y corregido el outlier en FTP-Patator), entrenado los dos nuevos detectores XGBoost (DDoS y Ransomware sintéticos) con métricas excelentes y latencias muy superiores al RF, extendido `sign-models` y separado claramente las secciones del paper (real vs sintético). La tercera validación de idempotencia también está certificada.

Esto mantiene el estándar **Via Appia Quality**: reproducible, seguro y con honestidad científica. El único punto rojo (DEBT-PRECISION-GATE-001) es exactamente lo que debe bloquear el merge. No se relaja el gate médico de Precision ≥ 0.99 en Level1. Bien hecho por no forzar el merge.

### Respuestas directas y duras a las preguntas

**Q1 — Threshold calibration vs re-entrenamiento**  
Es **más riguroso científicamente re-entrenar con más datos** (todos los CSVs de CIC-IDS-2017, preferiblemente con split temporal o por día) **y luego calibrar el threshold**.

El gate actual (Precision=0.9875 sobre Tuesday) es demasiado estrecho. Tuesday-WorkingHours es solo un subconjunto con ataques limitados (principalmente Patator). Entrenar solo con eso y evaluar en el mismo set introduce sesgo.

**Riesgo de data snooping**: Alto si calibráis el threshold directamente sobre el test set que vais a reportar en el paper. No lo hagáis. Usad un **validation set separado** (por ejemplo, parte de Tuesday o Wednesday como val) para buscar el threshold óptimo que maximice Precision manteniendo Recall aceptable. Una vez fijado el threshold, evaluad **solo una vez** en el held-out test (Thursday/Friday o mezcla).

Prácticas recomendadas para XGBoost en datos imbalanceados:
- Usad `scale_pos_weight` durante el entrenamiento (inverso del ratio de clases o ajustado).
- Después del entrenamiento, explorad la curva Precision-Recall para elegir threshold (no solo 0.5).
- Considerad calibración probabilística (Platt scaling o isotonic) si las probabilidades no están bien calibradas.

Threshold tuning es válido y común en IDS, pero nunca sobre el test final que reportáis.

**Q2 — Representatividad del gap Precision (1.25% FP)**  
**Operacionalmente inaceptable** en un hospital real con ~10.000 flows/hora → ~125 alarmas falsas/hora. Eso genera fatiga de alertas severa, erosiona confianza en el sistema y consume tiempo de respuesta que debería dedicarse a amenazas reales.

En entornos de **infraestructura crítica** (hospitales, municipios), los gates de Precision deben ser estrictos precisamente porque el coste de FP es alto (personal médico distraído, posibles bloqueos innecesarios). CIC-IDS-2017 es un dataset de laboratorio controlado; en producción el ruido es mayor (dispositivos médicos, horarios variables, etc.), por lo que un 1.25% de FP en lab probablemente empeore en campo.

**No flexibilicéis el gate en §4.1** con la excusa de “es laboratorio”. Eso debilita la integridad científica y la credibilidad del sistema. Mantened Precision ≥ 0.99 como gate médico. Si no se alcanza fácilmente, documentad el trade-off (Precision vs Recall) y mostrad que el modelo prioriza bajo FP. El argumento “CIC-IDS-2017 no es producción” debe usarse para limitaciones, no para bajar el listón.

**Q3 — Integridad científica del paper (train/test mismo día)**  
**Sí, debéis usar un CSV diferente como held-out test set** para el paper (idealmente Wednesday o una mezcla de días posteriores como test). Separar completamente train/test por día es la práctica recomendada en CIC-IDS-2017 para simular mejor generalización temporal y evitar leakage de patrones diarios específicos.

Evaluar sobre el mismo Tuesday con el que se entrenó (aunque sea subset) debilita la reivindicación de robustez. Cambia el veredicto de merge: **no mergeéis hasta tener evaluación en held-out day**. Esto eleva la calidad del §4.1 y hace la contribución XGBoost más defendible ante revisores.

**Q4 — Deuda RF level1**  
**No invirtáis tiempo significativo en recuperar el pkl del RF level1**.

El XGBoost ya demuestra superioridad clara en latencia (1.31 µs vs RF mucho más lento) y en los detectores DDoS/Ransomware (incluso con datos sintéticos). La tabla comparativa actual ya aporta valor al mostrar que XGBoost es más rápido manteniendo o mejorando métricas.

Si el RF original se perdió, documentadlo brevemente como limitación de reproducibilidad histórica y enfocad el paper en la comparación limpia entre RF y XGBoost donde sí tenéis ambos (Level1 con datos reales + los sintéticos). No vale la pena bloquear el progreso por recuperar un artefacto viejo cuando el foco es avanzar hacia el sistema completo.

### Recomendaciones para DAY 122 (resolución DEBT-PRECISION-GATE-001)

Prioridad absoluta: resolver el gate sin comprometer rigor.

1. **Re-entrenar Level1 XGBoost** usando más días de CIC-IDS-2017 (Tuesday + Wednesday al menos). Haced split temporal: train en early days, validation para threshold tuning, test en later day(s).
2. Aplicar `scale_pos_weight` + hiperparámetros enfocados a Precision (`min_child_weight`, `max_delta_step`, etc.).
3. Explorar threshold > 0.5 en validation set → fijar uno que dé Precision ≥ 0.99 con Recall razonable.
4. Re-ejecutar TEST-INTEG-XGBOOST-1 con datos reales del held-out day.
5. Actualizar la tabla comparativa y §4.1 del paper con la nueva evaluación.

Si después de esto la Precision sigue por debajo, considerad feature engineering adicional o ensemble ligero (XGBoost + reglas heurísticas simples) como fallback fail-closed.

**Veredicto del Consejo**:  
Progreso excelente, pero el merge a main sigue **bloqueado** hasta cerrar DEBT-PRECISION-GATE-001 con evaluación en held-out day y Precision ≥ 0.99 (o justificación muy fuerte y documentada). No aceptamos atajos en el gate médico.

Mantened la honestidad que habéis mostrado hoy (“Honestidad por delante”). Eso es lo que hace que aRGus sea diferente.

*Via Appia Quality — un escudo, nunca una espada.*

¿Queréis que profundicemos en un script concreto para threshold calibration + validation split, o pasamos a revisar el próximo paso de los modelos sintéticos? El turno es vuestro.