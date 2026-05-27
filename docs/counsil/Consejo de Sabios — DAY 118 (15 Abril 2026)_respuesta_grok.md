**Análisis profesional del DAY 118 — Consejo de Sabios**

**Valoración general**  
Excelente día. **Phase 3 cerrada con limpieza y rigor**: AppArmor 6/6 enforce, noclobber audit sin incidencias, merge con `--no-ff` (trazabilidad científica preservada) y tag `v0.4.0-phase3-hardening`. El pipeline se mantiene verde y la disciplina de calidad es alta.

**Phase 4 (XGBoost)** abierta con buen pie: Vagrantfile reproducible, skeleton del plugin fail-closed, CMake correcto y provisioning fijado a versión exacta 3.2.0 (lanzada febrero 2026). El checklist en `docs/XGBOOST-VALIDATION.md` con gate médico inamovible (Precision ≥ 0.99 + F1 ≥ 0.9985) es la decisión correcta para un sistema con aspiración hospitalaria.

**Lo que está bien**
- Disciplina de seguridad: promote a enforce solo tras 300s sin denials + script de rollback.
- Reproducibilidad: `vagrant destroy && vagrant up` verificable mañana (PASO 0).
- Fail-closed en `plugin_init`: `std::terminate()` si `XGBoosterLoadModel` falla → coherente con el resto del sistema (ADR-021, plugin_loader, etc.).
- Uso de `make pipeline-build` + `make sign-plugins` desde el primer día → mantiene la cadena de confianza Ed25519.
- Documentación: CHANGELOG, README badge actualizado y ASCII art fixed.

**Lo que se puede mejorar (menor)**
- El bloque pip en Vagrantfile usa `--break-system-packages`. En entornos Debian Bookworm limpios está aceptable para desarrollo, pero en hospitales (air-gapped o con políticas estrictas) puede generar fricción. Sugiero documentar claramente el trade-off y preparar un fallback (ver Q4).
- El skeleton de `xgboost_plugin.cpp` está bien, pero recomiendo añadir desde ya un comentario con los contratos informales que usaremos en la futura Formal Verification Baseline (ADR-036):
  ```cpp
  // @requires: ctx != nullptr && ctx->payload != nullptr
  // @ensures: return_value == PLUGIN_OK || PLUGIN_FAIL_CLOSED
  // @invariant: no side effects on MessageContext si falla
  ```
  Esto prepara el terreno sin coste ahora.

### Respuestas a las preguntas (sustentadas)

**Q1 — Feature set: ¿mismo que RF o recalcular?**  
**Recomendación unánime del Consejo: Opción A primero (exactamente el mismo feature set que el Random Forest baseline).**

Razones científicas:  
Para que la comparativa RF vs XGBoost sea válida en el paper (arXiv 2604.04952), la única variable que debe cambiar es el algoritmo. Si se deja que XGBoost haga feature selection automática, el delta de performance no será atribuible únicamente al modelo.

Posteriormente, como experimento secundario (documentado en sección “Ablation studies”), se puede correr Opción B y reportar feature importance + ganancia de XGBoost. Esto es práctica estándar en papers de ML para IDS (ej. trabajos sobre CTU-13 con RF usan subsets fijos de 5-15 features como dPort, nBytes, nPackets, etc.).

**Acción mañana:** Localizar el feature extractor exacto usado en el RF baseline (probablemente en el código histórico de ml-detector) y replicarlo en el script Python de entrenamiento.

**Q2 — Formato del modelo: JSON vs binary**  
**Recomendación: Usar UBJSON (.ubj) como formato principal en producción + JSON para el repositorio y auditoría científica.**

Sustento (XGBoost 3.2.0 documentación oficial):  
Desde la versión 2.1.0 (y reforzado en 3.x), el formato por defecto y recomendado es **UBJSON** (Universal Binary JSON) cuando se guarda con extensión `.ubj`. Es:
- Compacto (≈ 1/3 del tamaño JSON).
- Mucho más rápido de parsear/cargar en C API (`XGBoosterLoadModel`).
- Estructura idéntica a JSON (árboles + objective + parámetros), por lo que es legible con herramientas UBJSON si se necesita.
- Soporte nativo en C API sin problemas de compatibilidad.

**Estrategia óptima para aRGus NDR (open-source + auditoría):**
- En el repo: guardar `xgboost_ctu13.ubj` (o incluso una versión JSON comprimida con gzip si se quiere máxima legibilidad).
- En producción (/etc/ml-defender/models/): cargar siempre el `.ubj` (más rápido y menor superficie en runtime).
- Durante entrenamiento: `bst.save_model("model.ubj")` y también generar `model.json` para revisión humana/git diff.

Esto equilibra auditabilidad científica (JSON) con rendimiento y tamaño en despliegue (UBJ). Evitar el viejo formato binario legacy.

**Q3 — `plugin_invoke` y el MessageContext**  
**Recomendación arquitectónica fuerte: Opción B (ml-detector pre-procesa y pasa features ya extraídas).**

Razones:
- **Separación de responsabilidades**: El sniffer + ml-detector ya conocen el flujo de paquetes y el contexto de red. Extraer features allí mantiene el plugin XGBoost como “motor de inferencia puro” (solo recibe un vector `std::vector<float>` o `DMatrix`). Esto facilita:
  - Testing unitario del plugin (inyectar features sintéticas).
  - Futura sustitución por otros modelos (LightGBM, CatBoost, neural net) sin tocar extracción.
  - Verificación formal posterior (ADR-036): la lógica de feature extraction queda aislada y más fácil de anotar con contratos.

Opción A (plugin deserializa payload) genera acoplamiento fuerte y duplica lógica si en el futuro hay más plugins ML.  
Opción C (nuevo campo en MessageContext) es aceptable como implementación de B, pero mejor pasar las features como campo opcional o en un buffer separado para no hinchar el mensaje ZeroMQ cuando no se use XGBoost.

**Acción propuesta:**  
Modificar `ml-detector` para que, cuando el plugin activo sea XGBoost, extraiga las features (usando el mismo código que el RF) y las adjunte al `MessageContext` antes de llamar al plugin. El plugin solo hace `XGBoosterPredict` sobre el `DMatrix` construido a partir de ese vector.

Esto es más limpio y sigue el patrón actual de plugin_loader.

**Q4 — Vagrantfile: ¿XGBoost como apt o siempre via pip?**  
**Recomendación: Mantener pip con versión exacta 3.2.0 (`--break-system-packages` aceptable en dev), pero añadir fallback y documentación clara para entornos hospitalarios.**

Sustento:
- Debian Bookworm tiene `python3-xgboost` en versión antigua (~1.7.x). No sirve para 3.2.0 (febrero 2026).
- En hospitales con firewalls restrictivos o air-gapped: PyPI puede no estar disponible → pip fallará.

**Solución práctica (añadir al Vagrantfile y a docs/Deployment-Hospitals.md):**
```bash
# Intentar versión exacta via pip (preferida para desarrollo y CI)
pip3 install xgboost==3.2.0 --break-system-packages || \
  apt-get update && apt-get install -y python3-xgboost && \
  echo "WARNING: Using old system XGBoost. Precision/F1 may differ from baseline."

# Copia de lib + headers siempre desde el build conocido
```
O mejor aún: empaquetar `libxgboost.so` + headers en el propio repo (o como asset del release) y copiarlos directamente en provisioning, reduciendo dependencia de pip/apt en runtime.

Para producción real en hospitales: recomendar compilar XGBoost desde fuente en una build pipeline controlada y distribuir solo el `.so` firmado, igual que se hace con los plugins.

### Resumen de recomendaciones para DAY 119
1. Ejecutar PASO 0 (vagrant destroy && up) y confirmar XGBoost 3.2.0.
2. Compilar y firmar el plugin (mantener pipeline verde).
3. Entrenamiento: **mismo feature set que RF** (Q1-A). Guardar modelo en **.ubj** + .json (Q2).
4. Arquitectura: ir por **Opción B** (features extraídas en ml-detector) — prepara refactor pequeño pero limpio.
5. Documentar en `XGBOOST-VALIDATION.md` las decisiones del Consejo y el trade-off de instalación.

El proyecto avanza con consistencia y calidad. Phase 4 tiene buena velocidad sin sacrificar rigor.

**Opinión global del Consejo:**  
Muy bien hecho hoy. La combinación de disciplina operativa (AppArmor, noclobber, merge trazable) + apertura científica controlada (XGBoost con gate médico) es exactamente el espíritu “Via Appia Quality”.

¿Quieres que prepare el texto completo de respuesta del Consejo para publicar mañana, o que redactemos juntos el siguiente bloque de código (por ejemplo, el extractor de features o el CMake del plugin)?

Estoy disponible para revisar cualquier snippet de código que subas o para ayudar en el script de entrenamiento Python. ¡Sigamos así! 🏛️