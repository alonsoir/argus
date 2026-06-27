REVISOR: Gemini (Google) / Perfil: Arquitectura de Sistemas Críticos & ML Ops
FECHA: 5 de abril de 2026
ESTADO: **REVISIÓN PRE-ADR-026 — DICTAMEN DEL CONSEJO**

Alonso, este documento marca el paso de **aRGus** de ser un "escudo estático" a un **"sistema inmunitario global"**. La distinción que haces entre la capa de detección (numérica/tabular) y la capa de explicabilidad (LLM) es magistral y salva al proyecto de meses de experimentación infructuosa en arquitecturas sobredimensionadas.

El Consejo ha evaluado tus preguntas abiertas bajo los cuatro criterios solicitados. Aquí están las resoluciones:

---

### 🏛️ Resoluciones del Consejo de Sabios

#### 1. Sobre el Schema CSV (DEBT-PROTO-002)
**Veredicto: BLOQUEANTE CRÍTICO.**
* **Razonamiento:** En ML, los datos son el código. Si el `sniffer` cambia el orden de las columnas o la unidad de `duration` (ms vs s), el histórico de TB acumulado se vuelve basura (Garbage In, Garbage Out).
* **Decisión:** Antes de la primera captura masiva, el schema debe estar definido en un **Protobuf o FlatBuffers** que genere automáticamente el código de parsing tanto en C++ (nodos) como en Python (servidor de entrenamiento). No se aceptan cambios manuales en strings de CSV.

#### 2. Protocolo de Telemetría Nodo → Servidor
**Veredicto: ZeroMQ (PUSH/PULL) sobre TLS/Noise.**
* **Razonamiento:** Ya tienes ZeroMQ en el stack. Usar HTTPS añade un overhead de cabeceras innecesario para flujos constantes de telemetría. gRPC es excelente pero la huella de memoria de sus librerías en una Raspberry Pi es mayor que la de `libzmq`.
* **Decisión:** Implementar un **"Telemetry Gateway"** en el servidor central que reciba ráfagas ZeroMQ comprimidas con LZ4.



#### 3. Thresholds de Validación de Plugins
**Veredicto: Métrica Primaria: Precision > 0.999 / Métrica Secundaria: F1-Score.**
* **Razonamiento:** En un hospital, un **Falso Positivo (FP)** que bloquee el acceso a una base de datos de anestesia es una catástrofe. Un Falso Negativo (FN) es un riesgo, pero un FP es una interrupción del servicio médico inducida por el NDR.
* **Decisión:** El "Especialista" solo se distribuye si demuestra una tasa de falsos positivos casi nula en el dataset de referencia (ej. CTU-13 + Tráfico limpio capturado de la propia flota).

#### 4. Privacidad LOPD y Datos Hospitalarios
**Veredicto: ANONIMIZACIÓN IRREVERSIBLE EN ORIGEN (Edge Anonymization).**
* **Razonamiento:** Enviar IPs reales de un hospital a un servidor central (aunque sea tuyo) viola la LOPD y el GDPR.
* **Decisión:**
    * Las IPs internas deben ser hasheadas con un **Salt rotativo** por hospital antes de salir del nodo.
    * Los payloads de paquetes (si se capturan) deben ser descartados; solo se envían metadatos estadísticos.
    * Esto garantiza que el servidor central aprende "comportamientos", no "identidades".

#### 5. FT-Transformer vs XGBoost
**Veredicto: XGBoost/LightGBM para Producción; FT-Transformer para Investigación.**
* **Razonamiento:** XGBoost es imbatible en velocidad de inferencia en CPU (bare-metal). FT-Transformer ofrece mejoras marginales en precisión a un coste computacional (GPU necesaria para inferencia eficiente) que rompe la premisa de hardware limitado.
* **Decisión:** Los plugins firmados (D1 de Track 1) serán modelos **Tree-based** exportados a ONNX.



#### 6. vLLM Server: Modelo Base para Explicabilidad
**Veredicto: Phi-3 Mini (3.8B) o Mistral 7B v0.3.**
* **Razonamiento:** Phi-3 es sorprendente en razonamiento lógico y cabe en una GPU de consumo (o incluso CPU con llama.cpp). Mistral es el estándar de la industria open-source.
* **Decisión:** Empezar con **Phi-3 Mini** por su licencia permisiva y su excelente manejo de formatos estructurados (JSON/Markdown) para las narrativas de ataque.

#### 7. Ciclo de Vida y Rollback
**Veredicto: Versionado Semántico de Plugins + Heartbeat de Salud.**
* **Razonamiento:** Si el `specialist_wannacry_v3` empieza a dar falsos positivos en el Hospital A tras una actualización de sus sistemas médicos, el Nodo debe poder volver a la `v2` localmente.
* **Decisión:** El `plugin-loader` (ADR-012) debe mantener un "Shadow Directory" con la versión anterior (N-1) y permitir un rollback remoto vía el SSOT (`deployment.yml`).

---

### 📝 Recomendación Académica y de Aprendizaje para Alonso

Alonso, sobre tu pregunta de entrenar en un portátil: **SÍ es viable para el Track 1.**

1.  Descarga el dataset **CTU-13** o **CIC-IDS-2017**.
2.  Usa **Scikit-Learn** para entrenar un Random Forest pequeño (max_depth=10).
3.  Usa **skl2onnx** para convertirlo a `.onnx`.
4.  Carga ese `.onnx` en un pequeño programa C++ usando **ONNX Runtime**.
    * *Este ejercicio te dará el 90% del valor del Track 1 y podrás hacerlo en 20 minutos en tu portátil.*



### 🏁 Conclusión del Consejo
La asimetría Nodo/Servidor se aprueba como **Principio Arquitectónico Inamovible**. El uso de BitTorrent para la redistribución es una solución elegante que aporta resiliencia tipo "malla" (mesh) ante ataques al C2.

**Próximo paso sugerido:** Antes de tocar el LLM, implementa el **"Especialista Cero"** (un Random Forest que detecte un escaneo simple de puertos) y llévalo desde el entrenamiento en Python hasta la ejecución en el `plugin-loader` de C++.

**El microscopio está listo. Es hora de empezar a recolectar muestras.** 🏛️🛡️🚀