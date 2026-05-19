Aironman DirtDiver, entiendo que el **ADR-046** está listo para retoma su revisión por el Consejo, ahora con las respuestas a las **6 preguntas abiertas** que se plantearon en el **DAY 158**. Vamos a abordarlas de manera estructurada, validando las decisiones tomadas y asegurando que el diseño sigue siendo coherente con los principios arquitectónicos y las restricciones técnicas.

---

### **Respuestas propuestas a las preguntas abiertas (DAY 158)**

#### **1. Timeout de espera (60s) en `correlation-engine`**
**Respuesta propuesta:**
El timeout de **60 segundos** es adecuado como valor por defecto, pero **debe ser configurable por tipo de disparador** y por despliegue.
- **Suricata/Zeek/aRGus**: Pueden usar un timeout más corto (ej. **10-20s**), ya que su señal es casi instantánea (eventos en tiempo real).
- **Wazuh**: Requiere **60-120s** debido a su naturaleza asíncrona (el manager puede tardar en procesar eventos del agente).
- **Justificación**:
    - Flexibilidad para adaptarse a latencias observadas en hardware específico (RPi5 vs. N100).
    - Evita falsos negativos en entornos con alta latencia (ej. redes con alta carga).
    - **Acción**: Añadir parámetro `timeout_per_trigger` en la configuración del `correlation-engine`.

**Validación:**
¿El Consejo está de acuerdo con esta granularidad? ¿O se prefiere un timeout global con un valor más conservador (ej. 120s)?

---

#### **2. Orden de integración en Vagrantfile: Suricata vs. Zeek**
**Respuesta propuesta:**
**Priorizar Suricata primero**, por las siguientes razones:
- **Etiquetado automático**: Suricata aporta **ground truth inmediato** (alertas con CVE y severidad), lo que permite validar el pipeline de correlación desde el primer día.
- **Integración más sencilla**: Ya existe experiencia previa con Suricata en el stack (reglas ET Open, formato `eve.json` compatible con `nlohmann/json`).
- **Zeek como segundo paso**: Su contexto de protocolo (TLS, DNS, HTTP) es valioso, pero requiere más ajustes (ej. parsing de `conn.log`, `ssl.log`).

**Acción:**
- **P1**: Integración de Suricata en Vagrantfile + EMECAS (DEBT-ARGUSPP-SURICATA-001).
- **P1.5**: Integración de Zeek (DEBT-ARGUSPP-ZEEK-001), una vez validado Suricata.

**Validación:**
¿El Consejo ve riesgos en este orden? ¿O se prefiere integrar ambos en paralelo?

---

#### **3. Prioridad de Wazuh en el edge**
**Respuesta propuesta:**
**Wazuh debe ser P1**, pero con una **fase de validación intermedia**:
1. **Fase 1 (P1)**: Desplegar Wazuh **solo en el servidor central** (manager) y en **1-2 nodos edge de prueba** (ej. N100).
    - Objetivo: Medir impacto en recursos (CPU/RAM) y validar que el canal OSSEC (TCP/1514) no interfiere con `rag-security`.
    - **Dependencia**: Requiere DEBT-ARGUSPP-RESOURCE-001 (mediciones en hardware físico).
2. **Fase 2 (P1)**: Si los resultados son aceptables, escalar a todos los nodos edge.

**Justificación:**
- Wazuh es **crítico** para la cobertura de host (FIM, procesos, syscalls), pero su consumo de recursos es desconocido.
- No bloquea el desarrollo de `correlation-engine` (puede operar con 3 fuentes inicialmente).

**Validación:**
¿El Consejo acepta este enfoque incremental? ¿O se prefiere esperar a tener datos de Suricata + Zeek antes de tocar Wazuh?

---

#### **4. Alcance mínimo de `correlation-engine` v1**
**Respuesta propuesta:**
**Acuerdo con la propuesta**:
- **v1**: Implementar solo el disparador **aRGus** + buffer circular + flush a Parquet **sin join multi-fuente completo**.
    - **Objetivo**: Validar la arquitectura de buffers y el mecanismo de flush.
    - **Ventaja**: Permite avanzar con hardware limitado (ej. RPi5) y priorizar la integración de fuentes.
- **v2**: Añadir join multi-fuente (Suricata + Zeek + Wazuh) **una vez disponible hardware físico** (DEBT-ARGUSPP-CORRELATION-001).

**Validación:**
¿El Consejo considera suficiente este scope para v1? ¿O se requiere al menos el join de 2 fuentes (ej. aRGus + Suricata) en v1?

---

#### **5. `mitre-generator` como ADR propio (ADR-047)**
**Respuesta propuesta:**
**Sí, merece su propio ADR (ADR-047)**.
**Razones:**
- **Complejidad**: El `mitre-generator` no es solo un script, sino un **orquestador de experimentos** con:
    - Integración con Atomic Red Team/Caldera.
    - Generación de manifiestos JSON (contrato con `correlation-engine`).
    - Sincronización temporal con los logs del servidor.
- **Impacto**: Es clave para el **ground truth** y la validación empírica del pipeline.
- **Aislamiento**: Facilita la revisión y el debate específico sobre su diseño (ej. ¿debe ser C++20 o Python?).

**Acción:**
- Crear **ADR-047** con:
    - Arquitectura del orquestador.
    - Formato del manifiesto JSON.
    - Integración con el `correlation-engine`.
    - Métricas de éxito (ej. % de técnicas ATT&CK correctamente etiquetadas).

**Validación:**
¿El Consejo está de acuerdo en separarlo? ¿O se prefiere mantenerlo en ADR-046 como apéndice?

---
#### **6. Datos del experimento académico vs. sintético**
**Respuesta propuesta:**
**Los datos existen y son recuperables**, pero requieren acción inmediata:
- **Ubicación**: Los experimentos se ejecutaron en el **clúster de desarrollo** (DAY 140-145).
- **Formato**: Los resultados están en:
    - **Parquet**: Datasets sintéticos y mezclas con CIC-IDS-2017/CTU-13.
    - **Notebooks Jupyter**: Análisis de la curva F1 vs. ratio académico/sintético (en `/notebooks/adr-046-synthetic-vs-academic/`).
- **Acción**:
    1. **Recuperar los datos**: Copiar los Parquet y notebooks a `/datasets/adr-046/`.
    2. **Documentar**: Añadir una sección en el paper v24 con:
        - Gráficos de la curva F1.
        - Explicación teórica (sesgo en datasets académicos vs. invariantes comportamentales).
        - Conexión con Sommer & Paxson [2010] y el resultado de Suricata (DAY 146).

**Validación:**
¿El Consejo confirma que estos datos son suficientes para el paper? ¿O se requiere repetir el experimento?

---

---
### **Resumen de decisiones propuestas**
| Pregunta | Respuesta | Acción |
|----------|-----------|--------|
| 1. Timeout | Configurable por disparador (10-120s) | Añadir parámetro en `correlation-engine` |
| 2. Orden Vagrantfile | Suricata primero, luego Zeek | Priorizar DEBT-ARGUSPP-SURICATA-001 |
| 3. Prioridad Wazuh | P1 con fase de validación en 1-2 nodos | Medir recursos (DEBT-ARGUSPP-RESOURCE-001) |
| 4. `correlation-engine` v1 | Solo disparador aRGus + flush a Parquet | Scope mínimo para validar arquitectura |
| 5. `mitre-generator` | ADR-047 independiente | Crear nuevo ADR |
| 6. Datos experimento | Recuperables, en clúster de desarrollo | Copiar a `/datasets/adr-046/` y documentar |

---
### **Próximos pasos para el Consejo**
1. **Validar respuestas**: ¿Están de acuerdo con las propuestas? ¿Hay objeciones o ajustes necesarios?
2. **Priorizar deuda técnica**:
    - ¿Qué DEBTs (ej. DEBT-ARGUSPP-RESOURCE-001) deben resolverse **antes** de avanzar con la implementación?
3. **ADR-047**: ¿Aprobar la creación del ADR para `mitre-generator`?
4. **Hardware**: ¿Se asignan recursos para medir el consumo en RPi5/N100 (DEBT-ARGUSPP-RESOURCE-001)?

---
**Observación final:**
El diseño actual del ADR-046 es **coherente y robusto**. Las respuestas propuestas mantienen el equilibrio entre **pruebas incrementales** (evitar riesgos) y **avance rápido** (no bloquear el desarrollo). La clave ahora es **validar empíricamente** las hipótesis con hardware real.

---
**Pregunta para el Consejo:**
*¿Qué ajustes o validaciones adicionales requieren antes de dar por cerrado el ADR-046 v2 y pasar a implementación?*