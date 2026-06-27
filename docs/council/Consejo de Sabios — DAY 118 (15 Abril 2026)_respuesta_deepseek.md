## Dictamen del Consejo de Sabios — DAY 118 (15 Abril 2026)

*Miembros del Consejo: hemos revisado el informe de Alonso Isidoro Román. En general, el cierre de PHASE 3 y la apertura ordenada de PHASE 4 son excelentes. A continuación, nuestras observaciones y respuestas a las preguntas abiertas, con referencias verificables.*

---

### ✅ Lo que está bien (y debe mantenerse)

1. **Enforce 6/6 con monitorización activa**
  - El uso de `apparmor-promote.sh` con ventana de 5 minutos y rollback automático es una práctica industrial sólida.
  - Verificación recomendada (ya la hicieron):
    ```bash
    sudo aa-status | grep -E "enforce|complain" | grep -E "sniffer|etcd|rag|ml|firewall"
    ```  
    Salida esperada: 6 líneas con `enforce`.

2. **Merge `--no-ff` y tag semántico**
  - Correcto por la trazabilidad científica. El tag `v0.4.0-phase3-hardening` permite reproducir el estado exacto de la baseline.
  - Sugerencia futura: incluir el hash del commit en `CHANGELOG-v0.4.0.md` para facilitar el `git checkout` por parte de terceros.

3. **Noclobber audit**
  - Buen enfoque práctico (auditoría solo sobre rutas críticas). El Consejo valida que no se requirieron cambios.
  - Para mantener la calidad, añadir en `.pre-commit-config.yaml` una regla que detecte `>` sin `|` en rutas conocidas (por ejemplo, usando `grep -n '>[^|]' provision.sh`). No bloqueante.

4. **XGBoost instalado manualmente + Vagrantfile**
  - Separar la instalación manual (para desarrollo) de la automática (para CI) es correcto.
  - El uso de `--break-system-packages` es necesario en Debian 12+; documentar esta decisión en `docs/ENVIRONMENT.md`.

---

### ⚠️ Lo que se puede mejorar (con código o comandos)

#### 1. Falta test de integración para XGBoost en `make test-all`
- Actualmente el pipeline solo compila el plugin, pero no valida que la inferencia produzca resultados coherentes.
- **Propuesta concreta:** Añadir un test unitario en `tests/xgboost_integration_test.cpp` que:
  - Cargue un modelo de juguete (entrenado offline con unos pocos puntos).
  - Llame a `plugin_invoke` con un `MessageContext` sintético.
  - Verifique que la salida esté en [0,1] y no sea NaN.
- Ejemplo mínimo:
  ```cpp
  // tests/xgboost_integration_test.cpp
  #include "plugin_loader.h"
  TEST(XGBoostPlugin, InvokeReturnsProb) {
      Plugin p = load_plugin("libplugin_xgboost.so");
      MessageContext ctx;
      ctx.payload = create_dummy_features(); // 10 floats
      float result = p.invoke(&ctx);
      ASSERT_GE(result, 0.0f);
      ASSERT_LE(result, 1.0f);
  }
  ```

#### 2. El `MessageContext` actual no está preparado para features numéricas
- La **Opción C** (nuevo campo `features[]`) es la más limpia arquitectónicamente, pero implica modificar `ml-detector` y recompilar todo.
- **Alternativa intermedia (híbrida):** El plugin interpreta el payload como un array de `float` serializado con msgpack o flatbuffers, y `ml-detector` ya lo produce así. Esto evita cambiar la API central y mantiene la separación.
- Ejemplo de serialización en ml-detector:
  ```cpp
  std::vector<float> features = extract_features(packet);
  std::string serialized(reinterpret_cast<char*>(features.data()), features.size()*sizeof(float));
  context.payload = serialized;
  ```  
  Y en el plugin:
  ```cpp
  const float* feats = reinterpret_cast<const float*>(ctx.payload.data());
  size_t n = ctx.payload.size() / sizeof(float);
  ```  
- **Decisión del Consejo:** Recomendamos esta solución **Opción B+** (preprocesado en ml-detector + payload binario). Es la que menos acoplamiento introduce y no requiere cambiar la interfaz de `MessageContext`.

#### 3. El Vagrantfile no maneja fallback offline para hospitales
- Es cierto que muchos entornos restringidos no tienen acceso a PyPI.
- **Mejora sugerida:** Añadir un bloque condicional en `provision.sh` que intente primero `apt-get install -y python3-xgboost` (versión 1.7, suficiente para pruebas) y solo si falla, recurra a pip con `--index-url` opcional.
- Código:
  ```bash
  if ! dpkg -l | grep -q python3-xgboost; then
      echo "Trying apt version (offline-friendly)..."
      sudo apt-get install -y python3-xgboost || {
          echo "apt failed, falling back to pip..."
          pip3 install xgboost==3.2.0 --break-system-packages
      }
  fi
  ```  
- Además, documentar en `docs/OFFLINE-DEPLOYMENT.md` cómo precargar el `.whl` de XGBoost.

---

## Respuestas a las preguntas del Consejo

### Q1 — Feature set: ¿mismo que RF o recalcular?

**Opción A (mismo feature set)** es la única científicamente válida para la comparativa directa.

- **Razón:** Si se cambia el feature set, cualquier diferencia en rendimiento puede atribuirse a los features, no al clasificador.
- **Procedimiento recomendado:**
  1. Extraer el feature set exacto del RF baseline (consultar `ml-detector/features.h`).
  2. Entrenar XGBoost con exactamente esos mismos features (mismo preprocesado, mismo escalado).
  3. Publicar en `XGBOOST-VALIDATION.md` una tabla comparativa:

| Modelo | Precision | Recall | F1 | FPR |
|--------|-----------|--------|----|-----|
| RF (baseline) | 0.992 | 0.988 | 0.990 | 0.001 |
| XGBoost (mismos features) | ? | ? | ? | ? |

- **Opción B** (XGBoost con selección automática) se hará después, como experimento adicional, documentado en un anexo.

**Veredicto del Consejo:** ✅ **Opción A primero, Opción B secundaria.**

---

### Q2 — Formato del modelo: JSON vs binary

**Recomendación dual:**
- **En el repositorio (git):** JSON → legible, diff-friendly, auditable.
- **En producción (sobre la VM):** binary (UBJ) → menor footprint, carga más rápida.

**Implementación:**  
El `plugin_init` debe intentar cargar primero el binario, y si no existe, el JSON.
```cpp
const char* model_path = getenv("MLD_XGBOOST_MODEL_PATH");
if (access((std::string(model_path) + ".ubj").c_str(), F_OK) == 0)
    XGBoosterLoadModel(booster, (std::string(model_path) + ".ubj").c_str());
else
    XGBoosterLoadModel(booster, (std::string(model_path) + ".json").c_str());
```  
Además, añadir un script `scripts/convert_xgboost_model.sh` que convierta JSON→UBJ para despliegue.

**Veredicto del Consejo:** ✅ **JSON en repo, binary en producción.**

---

### Q3 — `plugin_invoke` y el MessageContext

Tras analizar las opciones, el Consejo elige **Opción B modificada** (preprocesado en ml-detector + payload binario de floats).

**Razones:**
- No modifica la API estable de `MessageContext` (evita recompilar todo el ecosistema por un cambio en un plugin).
- Mantiene la responsabilidad de extracción de features en el componente que ya conoce el protocolo de red (ml-detector).
- El plugin XGBoost se mantiene agnóstico al formato del mensaje original, solo recibe un array de floats.

**Ejemplo de implementación en ml-detector (cambio localizado):**
```cpp
// ml-detector/src/feature_extractor.cpp
std::vector<float> features = compute_features(packet);
context.payload.assign(reinterpret_cast<const char*>(features.data()),
                       features.size() * sizeof(float));
context.payload_size = context.payload.size();
```  
En el plugin:
```cpp
// plugins/xgboost/xgboost_plugin.cpp
extern "C" float plugin_invoke(MessageContext* ctx) {
    if (ctx->payload_size % sizeof(float) != 0) return -1.0f;
    const float* features = reinterpret_cast<const float*>(ctx->payload.data());
    size_t n_features = ctx->payload_size / sizeof(float);
    // crear DMatrix y llamar a XGBoosterPredict
}
```  

**Veredicto del Consejo:** ✅ **Opción B+ (payload binario).** Se debe actualizar la documentación de `MessageContext` para indicar que el payload puede ser de cualquier tipo (antes solo texto cifrado).

---

### Q4 — Vagrantfile: ¿pip o apt para XGBoost?

**Estrategia híbrida con fallback offline** (como se detalló en la mejora 3).

Además, **para hospitales con firewalls muy restrictivos** se puede ofrecer un script que descargue el `.whl` de XGBoost desde un mirror interno.

**Acción inmediata:** Modificar `provision.sh` con el bloque condicional propuesto.

**Veredicto del Consejo:** ✅ **Fallback apt → pip, documentar mirror alternativo.**

---

## Resumen de decisiones del Consejo (acta)

| Asunto | Decisión | Responsable | Plazo |
|--------|----------|-------------|-------|
| Feature set | Opción A (mismo que RF) | Alonso | DAY 119 |
| Formato modelo | JSON (repo) + binary (prod) | Alonso | DAY 119 |
| `plugin_invoke` | Payload binario de floats (Opción B+) | Alonso (ml-detector + plugin) | DAY 120 |
| Vagrantfile XGBoost | Fallback apt→pip + documentación | Alonso | DAY 119 |
| Test integración XGBoost | Añadir test unitario en `make test-all` | Alonso | DAY 120 |

---

## Observación final

El avance es sólido y metódico. El Consejo felicita al equipo por cerrar PHASE 3 y por la instalación reproducible de XGBoost. Se espera que mañana (DAY 119) se complete el paso 0 (prueba de Vagrantfile desde cero) y se inicie el entrenamiento offline con CTU-13.

Recordad: el gate médico (Precision ≥ 0.99, F1 ≥ 0.9985) es inamovible. Si XGBoost no lo alcanza con el mismo feature set, se descarta y se vuelve al RF. No hay presión por forzar un modelo inferior.

*Via Appia Quality — siempre con evidencias reproducibles.*

— **Secretario del Consejo de Sabios**