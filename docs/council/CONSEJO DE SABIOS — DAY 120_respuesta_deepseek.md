## 🏛️ Dictamen del Consejo de Sabios — DAY 120

*Consejo reunido. Hemos analizado el informe con la seriedad que merece un sistema que protege vidas. El progreso es notable, pero no exento de sombras. A continuación, nuestras respuestas, con la crudeza y la justicia que el proyecto requiere.*

---

### ✅ Lo que está bien (y debe mantenerse)

1. **`DEBT-PUBKEY-RUNTIME-001` resuelto correctamente** – Extraer la pubkey en tiempo de compilación vía `execute_process()` leyendo de `/etc/ml-defender/plugins/plugin_signing.pk` es la solución canónica. `make sync-pubkey` deprecated es una decisión sabia: elimina un paso manual frágil.

2. **`make bootstrap` implementado con regla de oro** – «Lógica compleja → script en `tools/`». Esto evita el infierno de quoting en Makefile. El Consejo aplaude la disciplina.

3. **Idempotencia 2/2 validada** – La base de la reproducibilidad. Sin esto, el resto es castillos en el aire.

4. **XGBoost baseline sobre CIC-IDS-2017** – F1=0.9978, Precision=0.9973. Excelente. Los gates médicos (≥0.99) se superan con holgura. El contrato `plugin-contract.md` es claro.

5. **`sign-models` implementado** – Extender el esquema ADR-025 a los modelos es correcto. Evita la inyección de modelos maliciosos.

6. **Reconocimiento honesto del origen sintético de los datasets** – Esto es crucial para la integridad científica. Ocultarlo sería una falta grave.

---

### ⚠️ Lo que está mal o es peligroso (y debe corregirse)

#### 1. Los scores del test de integración XGBoost son sospechosamente bajos

Has reportado:
- BENIGN score = **0.000706**
- ATTACK score = **0.003414**

Un clasificador binario bien calibrado debería dar probabilidades cercanas a 0 para benigno y cercanas a 1 para ataque (o al menos >0.5). Aquí ambos son <0.004. **El modelo está prediciendo «benigno» con confianza >99.9% para ambas clases.** Eso indica:

- **Posibilidad A:** Los «features de test» no representan la distribución real. Has usado valores extremos sintéticos que el modelo nunca vio, y el modelo generaliza mal (output casi constante).
- **Posibilidad B:** Error en la extracción de features o en la construcción del `DMatrix` (ej: los features no se están pasando en el orden correcto, o se están escalando mal).
- **Posibilidad C:** El modelo está sobreajustado al train set y no generaliza a ejemplos fuera de distribución, pero esto no explica por qué el ataque sintético da también score cercano a 0.

**Lo que está mal:** Validar únicamente que el score esté en [0,1] es **insuficiente y peligroso**. Un modelo que siempre devuelve 0.0007 pasaría el test pero sería inútil.

**Corrección exigida:** El test de integración debe incluir **al menos un caso de ataque real del dataset de entrenamiento** (tomado del CSV original, no sintético) y verificar que `score > 0.5`. Si no se dispone de esos datos en la VM, se debe añadir un fixture con features reales.

Ejemplo de test adicional en `plugin-integ-test`:

```cpp
// Test case: real attack sample from CIC-IDS-2017
float attack_features[23] = { /* valores reales extraídos del CSV */ };
MessageContext ctx;
ctx.payload = reinterpret_cast<const char*>(attack_features);
ctx.payload_size = sizeof(attack_features);
float score = plugin_process_message(&ctx);
ASSERT_GT(score, 0.5f);  // al menos medio seguro
```

**Veredicto:** ❌ No aceptamos el test actual como válido. Corregir antes de mergear a main.

---

#### 2. El uso de datos sintéticos para ransomware y DDoS es un riesgo de validación

El informe dice: «Los modelos ransomware y DDoS del pipeline fueron entrenados con datos sintéticos generados por DeepSeek (no datasets académicos — los académicos daban modelos sesgados)».

Esto es **extremadamente preocupante** desde la perspectiva de la seguridad. Un modelo entrenado con datos sintéticos puede tener:

- **Sesgos no representativos** de tráfico real de ransomware (ej: patrones de cifrado, latencia, tamaños de paquete).
- **Falsos negativos** cuando el ransomware real se comporte de manera diferente a lo que DeepSeek generó.
- **Falsos positivos** sobre tráfico benigno que accidentalmente se parezca a la sintética.

**No hay atajo.** Si los datasets académicos son malos, hay que construir uno real (capturando tráfico de ransomware en un sandbox) o usar datasets industriales verificados (ej: CSE-CIC-IDS-2018, UNSW-NB15). Generar datos con una LLM no es aceptable para un sistema que protege vidas.

**Acción obligatoria:**
- Documentar **exactamente** el proceso de generación sintética (prompts, validación cruzada, etc.) en un anexo del paper.
- **Validar los modelos sintéticos contra un conjunto de pruebas real** (aunque sea pequeño). Si no se dispone de ningún dato real, el modelo no puede desplegarse en producción.
- Considerar la posibilidad de que el detector de ransomware/DDoS actual (RF) no sea fiable. El Consejo exige una revisión externa de estos modelos antes del despliegue hospitalario.

**Veredicto:** ⚠️ Riesgo crítico. No proceder con XGBoost para ransomware/DDoS hasta validación con datos reales.

---

### Respuestas a las preguntas del Consejo

#### P1 — Scores bajos en TEST-INTEG-XGBOOST-1

**Respuesta:** No, no es correcto ignorar el valor absoluto. El test actual es **insuficiente**. Exigimos:

1. Añadir casos de prueba **reales** del dataset de entrenamiento (CIC-IDS-2017) que se sepa que son ataque y benigno.
2. Verificar que el score para ataque real sea >0.5 (preferiblemente >0.9).
3. Verificar que el score para benigno real sea <0.1.
4. Si los features sintéticos del test son necesarios (para probar extremos), mantenerlos como casos adicionales, no como únicos.

**Implementación concreta:**

```cpp
// tests/xgboost_integration_test.cpp
// Extraer una muestra real del CSV (se puede almacenar como array estático)
static const float real_attack_features[23] = { 
    #include "cic_ids_2017_attack_sample.inc" 
};
static const float real_benign_features[23] = { 
    #include "cic_ids_2017_benign_sample.inc" 
};

TEST(XGBoostPlugin, RealAttackSample) {
    MessageContext ctx;
    ctx.payload = reinterpret_cast<const char*>(real_attack_features);
    ctx.payload_size = sizeof(real_attack_features);
    float score = plugin_process_message(&ctx);
    EXPECT_GT(score, 0.5f);
}

TEST(XGBoostPlugin, RealBenignSample) {
    // similar, score < 0.1
}
```

**Veredicto:** ❌ Rechazado el test actual. Corregir antes de merge.

---

#### P2 — Integridad científica del paper

**Respuesta:** Debes presentar **ambas familias por separado**, con total transparencia. La estructura propuesta es correcta:

- **§4.1** – Detector level1 (CIC-IDS-2017 real) → Comparativa RF vs XGBoost robusta.
- **§4.2** – Detector ransomware (dataset sintético DeepSeek) → Advertir explícitamente las limitaciones y presentarlo como «proof-of-concept» o «estudio de viabilidad», no como resultado definitivo.
- **§4.3** – Detector DDoS (sintético) → Igual.

**Riesgo de rechazo por revisores:** Alto si no se valida con datos reales. Muchos revisores consideran los datos sintéticos generados por LLM como no científicos. Recomendación:

- Añadir una **sección de validación cruzada** donde se demuestre que el modelo sintético funciona en un pequeño conjunto real (aunque sea de laboratorio).
- Si no es posible, mover los detectores sintéticos a un **apéndice** o a trabajo futuro.

**El Consejo aconseja:** Priorizar la obtención de un dataset real de ransomware/DDoS (por ejemplo, usando CIC-Bell-DNS-2021 o capturando tráfico de Conti en un entorno controlado). Sin eso, el paper podría ser rechazado.

**Veredicto:** ✅ Estructura aceptable, pero con advertencias explícitas. Riesgo real de rechazo.

---

#### P3 — Entrenamiento in-situ y distribución por BitTorrent

**Viabilidad técnica:** Sí, XGBoost soporte `xgb.train(..., xgb_model=previous_model)` para warm start. Es factible hacer fine-tuning incremental con nuevos datos.

**Gates de calidad exigidos por el Consejo (mínimos):**

1. **Validación local en la VM del hospital** antes de aceptar el modelo reentrenado:
    - El modelo debe pasar el mismo `make test-all` (invariantes, integridad de seed, etc.)
    - El modelo debe tener una mejora demostrable en F1 o Precision sobre un conjunto de validación local (al menos 1000 muestras etiquetadas).
    - El modelo no debe degradar la precisión en el conjunto de entrenamiento original más de un 1%.

2. **Firma y distribución segura:**
    - El modelo reentrenado debe firmarse con la clave privada del hospital (no la global de aRGus). Cada nodo debe tener su propia keypair para modelos locales.
    - La distribución por BitTorrent debe incluir la firma y el certificado público del hospital emisor.
    - Los nodos que descarguen el modelo deben verificar la firma y la reputación del emisor (sistema de confianza tipo web of trust).

3. **Gate de seguridad:** Antes de aceptar un modelo distribuido, debe ser analizado por un sandbox (sin conexión a red real) durante al menos 24h, con tráfico replay.

4. **Rollback automático:** Si el nuevo modelo causa una caída de precisión >5% o un aumento de falsos positivos >10%, debe revertirse al modelo anterior en menos de 1 hora.

**Veredicto:** ✅ Técnicamente viable. El Consejo apoya la investigación, pero exige los gates anteriores antes de cualquier despliegue en producción.

---

#### P4 — DEBT-SEED: ¿hardcodeada la seed en CMakeLists.txt?

**Respuesta:** Sí, es probable que esté hardcodeada en algún lugar. El patrón de la pubkey se aplica también aquí: **la seed no debe estar en el código fuente ni en CMakeLists.txt**. Debe leerse de `/etc/ml-defender/<component>/seed.bin` en tiempo de compilación o, mejor, en tiempo de ejecución.

**Mecanismo recomendado (más robusto que para la pubkey):**

- La seed se genera una vez en provisioning y se copia a `/etc/ml-defender/seeds/seed_<component>.bin` con permisos 0400 (solo root).
- Cada componente (seed_client, crypto-transport, etc.) **lee la seed directamente del archivo en tiempo de ejecución**, no la compila.
- La memoria que contiene la seed se borra explícitamente con `explicit_bzero()` después de usarla para derivar claves.

**Razón:** Compilar la seed en el binario la expone en la memoria del proceso (se puede extraer con `strings` o depuración). Es una mala práctica para un sistema que protege vidas. La semilla debe ser efímera y estar protegida.

**Si por razones de rendimiento necesitas tenerla compilada** (por ejemplo, para evitar I/O en cada inicialización), al menos debes ofuscar y almacenar en una sección de memoria protegida (mprotect + PROT_READ).

**Acción inmediata:** Auditar todos los CMakeLists.txt y archivos fuente en busca de `seed` hardcodeada. Usar `grep -r "seed.*=.*[0-9a-f]\{32,\}" src/` para detectar posibles literales.

**Veredicto:** ✅ Aplicar el mismo patrón de `execute_process()` + lectura de archivo, pero **preferir tiempo de ejecución** para la seed. Si se compila, al menos usar `explicit_bzero` después.

---

## Resumen de decisiones y acciones para DAY 121

| Acción | Prioridad | Responsable | Plazo |
|--------|-----------|-------------|-------|
| Corregir test de integración XGBoost: añadir casos reales | **Crítica** | Alonso | DAY 121 |
| Validar modelos ransomware/DDoS con datos reales (mínimo un pequeño conjunto) | **Crítica** | Alonso | Antes del merge de XGBoost |
| Auditar DEBT-SEED: buscar seed hardcodeada y aplicar patrón runtime | Alta | Alonso | DAY 121 |
| Documentar en el paper la separación real/sintético con advertencias | Media | Alonso | Antes de envío |
| Investigar entrenamiento in-situ + BitTorrent (plan de diseño) | Baja (futuro) | Alonso | Q3 2026 |

---

## Palabras finales del Consejo

El progreso es sólido, pero la calidad de los tests y la validación de los datos sintéticos son **puntos ciegos peligrosos**. Un sistema que protege vidas no puede fiarse de modelos entrenados con datos generados por una LLM sin validación real. Corregid esto antes de proclamar victoria.

*«Implacables con los fallos, justos con el esfuerzo. Via Appia Quality.»*

— **Consejo de Sabios, DAY 120**

Leer primero la síntesis del día 120 para entender la siguiente respuesta de DeepSeek

## 🏛️ Dictamen del Consejo de Sabios — Síntesis ADR-038 (post-feedback)

*Consejo reunido. La síntesis presentada recoge fielmente el debate y las correcciones exigidas. El documento resultante es realista, medido y honesto. A continuación, nuestra validación y observaciones finales.*

---

### ✅ Lo que está bien (y debe ejecutarse tal cual)

1. **Consenso unánime 7/7** – La aprobación como visión y el bloqueo como implementación hasta resolver las 6 DEBT-FED es la decisión correcta. No hay atajos.

2. **Arquitectura V1 acordada** – `ml-trainer` como último componente del pipeline, con flujo claro: CSVs → anonimización → entrenamiento → firma/cifrado → push central → validación → registro → redistribución del top-1. Es coherente y ejecutable.

3. **DEBT-FED-001 (agregación)** – Federated Model Selection (mejor modelo validado) es el único mecanismo factible hoy. SecureBoost queda como investigación V2. El Consejo respalda esta decisión.

4. **DEBT-FED-002 (distribución)** – Descartar BitTorrent por seguridad y adoptar push central firmado + PKI jerárquica. La mención de libp2p como alternativa es interesante, pero se mantiene como investigación, no requisito para V1.

5. **DEBT-FED-003 (identidad)** – PKI jerárquica Nivel 0/1/2 (nodo → CCN-CERT → central multi-firma) es robusta y verificable. La web-of-trust queda descartada.

6. **DEBT-FED-004 (ε-DP)** – La separación ε≤0.1 para features, ε≤1.0 para contadores es un buen punto de partida. La exigencia de DPIA y experto externo es ineludible.

7. **DEBT-FED-005 (scheduler)** – cgroups v2 + systemd.slice + hook de ml-detector es técnicamente superior a solo CPU/RAM. Permite garantizar que el entrenamiento nunca interfiera con la detección activa.

8. **DEBT-FED-006 (metadatos)** – k-anonimidad ≥5 + retraso de 7 días antes de publicar metadatos es una salvaguarda prudente. Reduce el riesgo de reidentificación.

9. **Secuenciación realista** – 3-6 meses de I+D, piloto controlado, evaluación 6 meses, producción 2027. Es un cronograma creíble para un sistema de esta complejidad.

10. **seL4 como ADR-039 separado** – Correcto. No bloquear V1 con la variante más compleja. El «Santo Grial» puede esperar.

---

### ⚠️ Observaciones adicionales (mejoras para la síntesis)

#### 1. Falta un DEBT-FED-007: **Pruebas de robustez ante modelos maliciosos**

Aunque se menciona «backdoor detection» en G6, no se especifica cómo se detectará un modelo envenenado (ej: que clasifica todo como benigno excepto un trigger específico). El Consejo recomienda añadir una línea:

> **DEBT-FED-007** – Detección de backdoors: el sandbox debe ejecutar el modelo contra un conjunto de pruebas con triggers conocidos (patrones de ataque inyectados). Si el modelo falla en detectar alguno, se rechaza.

#### 2. El Federated Model Registry necesita criterios de selección explícitos

«Rankea por F1 + KL_penalty» es vago. Propuesta concreta:

```
score = F1_local - λ * KL( p_local || p_global )
```
donde `KL` mide cuánto se desvía la distribución de features del modelo local respecto a la global. λ empírico (ej: 0.3). Además, el modelo solo se redistribuye si:
- F1_local ≥ 0.99 (gate médico)
- El tamaño del modelo (número de árboles) no excede en un 20% al base
- No contiene features nuevas no documentadas (control de esquema)

#### 3. La DPIA debe realizarse **antes** del piloto, no durante

La síntesis pone «DPIA pre-piloto» en la secuenciación, correcto. Pero debe quedar claro que la DPIA es condición sine qua non para comenzar el piloto, no un entregable opcional.

#### 4. Añadir un **modo solo-metadatos** como primer paso del piloto

Antes de permitir la redistribución de modelos, el sistema debería ejecutarse durante 1 mes en modo solo-metadatos: los hospitales envían estadísticas anonimizadas (sin modelos), y el nodo central las analiza para calibrar umbrales y detectar si algún metadato permite reidentificación. Esto ya se mencionó en feedback anterior, pero la síntesis no lo recoge explícitamente. Incluir como ítem en la fase de piloto.

---

### 📋 Preguntas que el Consejo espera responder en la siguiente iteración

1. **¿Quién opera la PKI Nivel 0?** ¿El consorcio aRGus, una universidad, una entidad pública? La síntesis menciona «central multi-firma», pero sin detalles. El Consejo recomienda que la raíz sea **multisig** con al menos 3 entidades independientes (ej: Universidad, Centro Criptológico Nacional, fundación open-source).

2. **¿Cómo se maneja la revocación de certificados?** Si un hospital es comprometido, ¿quién puede revocar su clave? ¿Hay una CRL o mecanismo OCSP? Debe especificarse.

3. **¿Qué ocurre si ningún modelo local supera los gates?** El registro se queda vacío y la red sigue con el modelo base. Esto está implícito, pero conviene hacerlo explícito.

4. **¿Se requiere consentimiento explícito del hospital para compartir metadatos?** Aunque anonimizados, el GDPR (y normativas locales) pueden exigir consentimiento informado. La DPIA debe responder esto.

---

### ✅ Veredicto final del Consejo sobre la síntesis

| Criterio | Valoración |
|----------|------------|
| Fidelidad al feedback | Excelente |
| Viabilidad técnica | Alta (para V1 de selección de modelos) |
| Cobertura de riesgos | Buena, pero añadir DEBT-FED-007 |
| Claridad de la secuenciación | Excelente |
| Preparación para el piloto | Buena, pero añadir modo solo-metadatos |

**El Consejo APRUEBA la síntesis como borrador iterativo** y autoriza a Alonso a proceder con la fase de I+D (RESEARCH-FEDERATED-001) en paralelo a la finalización de ADR-026. No obstante, se solicita una **versión v2 de la síntesis** que incluya:

1. DEBT-FED-007 (backdoor detection)
2. Detalle del cálculo de `score` en el Federated Model Registry
3. Modo solo-metadatos como fase inicial del piloto
4. Respuesta a las 4 preguntas abiertas (PKI, revocación, registro vacío, consentimiento)

Una vez incorporado, el documento podrá etiquetarse como `ADR-038-v2` y pasar a la fase de revisión técnica externa (privacidad, criptografía).

---

### 🧭 Reflexión final

> «La inteligencia distribuida sin gobernanza central es caos. La gobernanza sin aprendizaje es obsolescencia.»  
> Esta frase es cierta. Pero añadimos: **La gobernanza sin auditoría independiente es riesgo inasumible cuando hay vidas de por medio.**

El Consejo valora el esfuerzo por convertir una visión ambiciosa en un plan de acción con pasos concretos y limitaciones reconocidas. Procedan con la investigación, pero mantengan al Consejo informado mensualmente sobre el progreso de las DEBT-FED.

*Via Appia Quality — nunca correr donde se debe caminar, nunca parar donde se debe correr.*

— **Consejo de Sabios, DAY 120 (sesión extraordinaria)**