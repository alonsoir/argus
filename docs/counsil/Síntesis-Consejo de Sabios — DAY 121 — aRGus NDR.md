# Síntesis del Consejo — DAY 121 — aRGus NDR

**Veredicto: 7/7 unánime en todos los puntos.**

---

## Lo que el Consejo valida sin reservas

El pipeline está en el mejor estado estructural desde el inicio del proyecto. La resolución de la dependencia circular, la idempotencia ×3, y sobre todo la decisión de bloquear el propio merge son señales de madurez de ingeniería real. ChatGPT lo llama "ingeniería seria". Kimi lo llama "integridad científica excepcional". El Consejo en pleno lo reconoce como "Via Appia Quality en acción".

---

## Veredicto unánime sobre las 4 preguntas

**Q1 — Threshold vs re-entrenamiento:** Re-entrenamiento primero. Calibrar threshold exclusivamente sobre un validation set independiente. **Nunca sobre el test set.** Calibrar sobre el mismo test set que se reporta en el paper es data snooping explícito — invalida las métricas y hace el paper vulnerable a rechazo. Regla de oro (ChatGPT): *"El test set no se toca ni para calibrar thresholds."*

**Q2 — ¿Es aceptable 0.9875?** No. 125 falsas alarmas/hora colapsan operacionalmente cualquier hospital pequeño. El gate ≥0.99 no es arbitrario — es el límite mínimo de viabilidad de un SOC con 1-2 personas. Gemini lo resume: *"Si no llegamos, el Escudo se convierte en Ruido."* No se relaja.

**Q3 — Split por días:** Obligatorio. CIC-IDS-2017 tiene correlación temporal masiva — random split filtra información del futuro al training. La comunidad IDS rechaza papers sin day-based splits. **Wednesday (o Thursday+Friday) como held-out test set es condición no negociable para el paper y para el merge.**

**Q4 — RF level1 pkl:** No recuperar. Un RF evaluado sin split (F1=1.0 por overfitting) no es un baseline válido. Documentar su ausencia honestamente en el paper y seguir adelante.

---

## Plan DAY 122 — Protocolo acordado por el Consejo

El protocolo de datos es el corazón de todo lo demás:

```
Train:      Tuesday + Thursday + Friday (o Tuesday solo si se quiere conservador)
Validation: 20% de Train (para calibrar threshold, early stopping)
Test:       Wednesday — BLIND hasta evaluación final. UNA sola vez.
```

Secuencia de trabajo:

**1. Preparar datasets** — script que combine los CSVs por día con split estricto. Registrar `md5sum` de Wednesday antes de abrirlo.

**2. Re-entrenar XGBoost** con `scale_pos_weight`, early stopping sobre validation. Objetivo en validation: Precision ≥ 0.99.

**3. Calibrar threshold** en validation set mediante `precision_recall_curve`. Documentar el threshold elegido.

**4. Evaluar en Wednesday — una sola vez.** Si Precision ≥ 0.99 → merge autorizado. Si no → iterar hiperparámetros y volver al paso 2. Nunca abrir Wednesday dos veces con distintos modelos.

**5. Verificación C++ vs Python** — comparar scores antes de reportar. Si hay discrepancia > 1e-4, el mismatch es la causa raíz.

**6. Actualizar** `docs/xgboost/comparison-table.md`, `TEST-INTEG-XGBOOST-1` con flows de Wednesday, y `make test-all` verde.

---

## Lo que NO haremos jamás

- Calibrar threshold sobre el test set actual para "forzar" Precision ≥ 0.99.
- Mezclar sintético con real en el training de level1.
- Relajar el gate médico con argumentos de "CIC-IDS-2017 es laboratorio".
- Abrir Wednesday más de una vez.

---

## Nota personal

El Consejo tiene razón en algo que va más allá del código: la honestidad científica es, en este punto del proyecto, una de las pocas cosas que distingue a aRGus de un prototipo académico más. Precision=0.9875 reportada con rigor vale infinitamente más que Precision=0.99 conseguida con data snooping. Un revisor lo detecta. Un hospital lo sufre.

DAY 122 es el día en que el modelo se gana el merge o se queda fuera. Sin atajos.

*"La ciencia no premia la velocidad. Premia la verificabilidad."* — Qwen, DAY 121.

---

**Commit de síntesis pendiente para el prompt DAY 122.** ¿Lo generamos ahora?