# RESPUESTA DEL CONSEJO DE SABIOS — Auditoría de features ML

**DAY 209 · Deliberación sobre hallazgos de auditoría**

---

## Respuesta a las preguntas planteadas

### 1. Desactivación de la cabeza de ransomware embebida actual

**Decisión: DESACTIVAR INMEDIATAMENTE** (`enabled: false` en config)

**Fundamento:** El diagnóstico es concluyente. Un modelo con desajuste de dominio estructural —entrenado sobre features de host, alimentado con proxies de red sin correlación semántica— no está "degradado": está generando falsos positivos/negativos sistemáticos. Mantenerlo activo contamina:
- Cualquier métrica de evaluación que se intente medir
- La confianza del usuario en el sistema
- La validez científica de la validación

**Acciones requeridas:**
- ADR (Architecture Decision Record) documentando: (a) el desajuste de dominio detectado, (b) la imposibilidad de rescate en arquitectura NDR pura, (c) la decisión de desactivación
- Etiqueta explícita en config: `ransomware_detector: { enabled: false, status: "domain_mismatch_detected", debt_ref: "DEBT-RANSOMWARE-DOMAIN-MISMATCH-001" }`
- El detector no debe participar en veredictos de producción hasta que exista un modelo con features del dominio correcto

**Alternativa rechazada:** Mantenerlo activo con etiqueta "proxy-based, no fiable". Esto sigue contaminando métricas y confunde al usuario. La honestidad epistémica exige silencio, no ruido etiquetado.

---

### 2. Registro de DEBT para el XGBoost de 45 features anónimas

**Decisión: REGISTRAR Y AUTORIZAR BORRADO**

**DEBT ID:** `DEBT-RANSOMWARE-PROTO-ALIGNED-DEAD-001`

**Fundamento:** El artefacto es inoperable (45 features anónimas, sin contrato documentado, imposible de alimentar). Pero su existencia es un hecho histórico que debe preservarse como lección arquitectónica: "intentamos un XGBoost de red, falló por falta de contrato de features, abandonamos la línea".

**Acciones requeridas:**
- Crear fichero `DEBTS/RANSOMWARE-PROTO-ALIGNED-DEAD-001.md` documentando:
    - Por qué se creó (intento de detector de red para ransomware)
    - Por qué falla (features anónimas, sin trazabilidad al entrenamiento)
    - Por qué se abandona (desajuste de dominio, §2 de la auditoría)
    - Referencia al commit original y al autor
- Borrado vía `git rm` (no `rm`) para preservar historial
- El DEBT permanece como registro, el artefacto se elimina del árbol de producción

---

### 3. Registro de DEBT para features constantes del DDoS

**Decisión: REGISTRAR SIN ACCIÓN INMEDIATA**

**DEBT ID:** `DEBT-DDOS-FEATURES-CONSTANT-001`

**Fundamento:** El detector DDoS funciona en lo esencial (6 features reales, incluyendo las de mayor peso). Las 3 features constantes ([2], [3], [7]) son deuda, no emergencia. El modelo no está roto; está subóptimo.

**Acciones requeridas:**
- Crear fichero `DEBTS/DDOS-FEATURES-CONSTANT-001.md` documentando:
    - Las 3 features afectadas y sus valores constantes
    - El análisis de código que lo demuestra (líneas 224–264 de `feature_extractor.cpp`)
    - Impacto: degradación menor, no funcionalidad crítica
    - Prioridad: baja (arreglar o justificar en iteración futura)
- No desactivar el detector DDoS
- No asignar recursos inmediatos; se abordará en sprint de refactor de features

**Nota:** Si en el futuro se mide que estas features constantes afectan significativamente la precisión, se reclasificará a prioridad media.

---

### 4. Entrenamiento de modelo comportamental de ransomware

**Decisión: AUTORIZAR OPCIÓN A (modelo de red) PARA PRE-FEDER**

**Fundamento:** La Opción A es:
- **Realista:** está dentro del alcance pre-FEDER
- **Honesta:** detecta las fases de red del ransomware (C2, discovery, lateral, exfil), no el cifrado
- **Alineada con la arquitectura:** aRGus es NDR; un modelo de red es coherente con su dominio
- **Entrenable:** los datos de Atomic Red Team (§7) generan la señal necesaria
- **Validable:** la matriz de ablación mide qué detecta y qué no, con huecos declarados

**La Opción B (híbrido red+host) se difiere a post-FEDER** porque:
- Requiere integración con Wazuh (nuevo pipeline de telemetría)
- Amplía el alcance del proyecto más allá de lo comprometido
- Es técnicamente más compleja (fusión de features heterogéneas)
- No es urgente: la Opción A ya cubre las fases de red, que son las que aRGus puede ver

**Entregable pre-FEDER:**
- Modelo RandomForest embebido en C++, 10 features de red, entrenado con datos de Atomic Red Team
- Documentación explícita de limitaciones: "detecta C2/beaconing, discovery, lateral movement, exfiltración; NO detecta cifrado de ficheros (T1486), que requiere HIDS"
- Matriz de ablación que valida empíricamente la frontera

---

### 5. Aprobación de la línea MITRE ATT&CK / Atomic Red Team

**Decisión: APROBAR COMO TRABAJO REAL PRE-FEDER**

**Fundamento:** Esta línea es:
- **Legal:** Atomic Red Team es open source (MIT), no usa malware real, emula técnicas documentadas
- **Científicamente riguroso:** la matriz de ablación (sensores × técnicas × componentes) es un método de validación defendible
- **Genera datos:** produce el tráfico necesario para entrenar el modelo de la Opción A
- **Responde a Andrés:** la matriz con huecos declarados es más fuerte que cualquier número inflado
- **Publicable:** el método y los resultados son auditables y reproducibles

**Montaje aprobado:**
- Topología reutilizada de CTU-13 (VM `client` inyecta, `defender` observa en `eth1`)
- Atomics de Linux (LockBit perfilado por terceros)
- Sensores: aRGus (cabezas activables una a una), Suricata, Zeek, Wazuh
- Entregable: matriz de detección por técnica ATT&CK, con declaración explícita de qué sensor ve qué

**Criterio de éxito:** la matriz demuestra empíricamente la frontera NDR/HIDS, con huecos honestos. No se busca "detectar todo"; se busca "saber qué detecta cada capa y por qué".

---

## Resumen de decisiones

| Pregunta | Decisión | Acción inmediata |
|---|---|---|
| 1. Ransomware embebido | Desactivar | ADR + `enabled: false` |
| 2. XGBoost muerto | Registrar DEBT + borrar | Documentar + `git rm` |
| 3. DDoS constante | Registrar DEBT | Documentar, sin acción |
| 4. Modelo ransomware real | Opción A (red) | Entrenar con Atomic Red Team |
| 5. MITRE ATT&CK | Aprobar | Ejecutar matriz de ablación |

---

## Nota final del Consejo

La auditoría ha cumplido su propósito: **medir, no votar**. Los hallazgos son structuralmente sólidos, trazados a código, y el diagnóstico es defendible. La frontera NDR/HIDS no es un fracaso; es un hecho arquitectónico que debe publicarse con honestidad.

El proyecto avanza con rigor científico. La transparencia en el uso de IA, el código abierto como obligación ética, y la democratización de la seguridad empresarial se cumplen cuando admitimos las sombras del sistema.

**Via Appia Quality — un escudo que conoce sus propias sombras.**

---

*Respuesta del Consejo de Sabios, 6 de julio de 2026.*
</think>

# RESPUESTA DEL CONSEJO DE SABIOS — Deliberación sobre la auditoría de features

**DAY 209 · Resolución**

---

## Dictamen general

La auditoría presentada cumple con el estándar epistémico del proyecto: **medir, no votar**. Cada afirmación está trazada a un fichero, cada diagnóstico distingue entre lo medido y lo supuesto, y la frontera NDR/HIDS se formula como un hecho arquitectónico, no como un fracaso. El método es defendible y los hallazgos son structuralmente sólidos.

A continuación, las decisiones del Consejo sobre cada pregunta.

---

## 1. Desactivación de la cabeza de ransomware embebida actual

**Decisión: DESACTIVAR INMEDIATAMENTE.**

El diagnóstico es terminal. Un modelo entrenado sobre entropía de ficheros que recibe varianza de longitud de paquete no está "degradado": está produciendo decisiones sin fundamento semántico. Mantenerlo activo con cualquier nivel de confianza —aunque sea etiquetado como "no fiable"— contamina las métricas de evaluación y falsea la validación científica.

**Acciones:**
- ADR (Architecture Decision Record) documentando el desajuste de dominio, la imposibilidad de rescate en arquitectura NDR pura, y la decisión de desactivación.
- Config: `enabled: false`, con campo `status: "domain_mismatch_detected"` y referencia al DEBT.
- El detector queda excluido de cualquier veredicto de producción hasta que exista un modelo con contrato de features del dominio correcto.

**Alternativa rechazada:** mantenerlo activo con etiqueta "proxy-based, no fiable". La honestidad epistémica exige silencio cuando la señal es ruido. Un score sin fundamento es peor que la ausencia de score.

---

## 2. Registro de `DEBT-RANSOMWARE-PROTO-ALIGNED-DEAD-001`

**Decisión: REGISTRAR Y AUTORIZAR BORRADO.**

El XGBoost de 45 features anónimas es un artefacto muerto, pero su existencia es un hecho histórico con valor pedagógico: documenta un intento fallido de detector de red para ransomware, abandonado por falta de contrato de features. Ese conocimiento no debe perderse.

**Acciones:**
- Crear `DEBTS/RANSOMWARE-PROTO-ALIGNED-DEAD-001.md` con: motivo de creación, causa de fallo (features anónimas, sin trazabilidad), razón del abandono (desajuste de dominio, §2 de la auditoría), referencia al commit y al autor.
- Borrado vía `git rm` —nunca `rm`— para preservar el historial.
- El DEBT permanece como registro; el artefacto se elimina del árbol de producción.

Las discrepancias afloran como DEBT, no se resuelven en silencio. Principio confirmado.

---

## 3. Registro de `DEBT-DDOS-FEATURES-CONSTANT-001`

**Decisión: REGISTRAR, SIN ACCIÓN INMEDIATA.**

El detector DDoS funciona en lo esencial: sus features de mayor peso (`syn_ack_ratio`, `packet_symmetry`) son legítimas y el fenómeno es de red pura. Las tres features constantes ([2], [3], [7]) son deuda técnica, no emergencia funcional. El modelo está subóptimo, no roto.

**Acciones:**
- Crear `DEBTS/DDOS-FEATURES-CONSTANT-001.md` documentando las features afectadas, los valores constantes, el análisis de código (líneas 224–264), el impacto (degradación menor), y la prioridad (baja).
- No desactivar el detector. No asignar recursos inmediatos.
- Se abordará en iteración futura de refactor de features. Si métricas posteriores muestran impacto significativo en precisión, se reclasificará a prioridad media.

---

## 4. Entrenamiento de modelo comportamental de ransomware

**Decisión: AUTORIZAR OPCIÓN A (modelo de red) PARA PRE-FEDER. OPCIÓN B (híbrido) QUEDA COMO ROADMAP POST-FEDER.**

**Opción A — modelo de red:**
- Está dentro del alcance pre-FEDER.
- Es coherente con la arquitectura: aRGus es NDR, un modelo de red respeta su dominio.
- Los datos de Atomic Red Team (§7) generan la señal necesaria para entrenarlo.
- Es honesto: detecta C2/beaconing, network discovery (T1046), lateral movement (T1021), exfiltración (T1048). No detecta cifrado (T1486), y eso se declara explícitamente.
- Es validable: la matriz de ablación mide qué detecta y qué no, con huecos declarados.

**Opción B — modelo híbrido red+host:**
- Requiere integración con Wazuh (nuevo pipeline de telemetría, fusión de features heterogéneas).
- Amplía el alcance más allá de lo comprometido en FEDER.
- Es técnicamente más compleja y no es urgente: la Opción A ya cubre las fases que aRGus puede ver por construcción.
- Se registra como objetivo post-FEDER, cuando la integración HIDS esté en la hoja de ruta.

**Entregable pre-FEDER:** modelo RandomForest embebido en C++, 10 features de red, entrenado con datos de Atomic Red Team, con documentación explícita de limitaciones y matriz de ablación que valida empíricamente la frontera.

---

## 5. Aprobación de la línea MITRE ATT&CK / Atomic Red Team

**Decisión: APROBAR COMO TRABAJO REAL PRE-FEDER.**

Esta línea cumple todos los criterios del proyecto:
- **Legal y ética:** Atomic Red Team es open source (MIT), emula técnicas documentadas sin malware real, alineado con el marco ético de no facilitar daño.
- **Científicamente riguroso:** la matriz de ablación (sensores × técnicas ATT&CK × componentes) es un método de validación defendible y publicable.
- **Genera datos:** produce el tráfico comportamental necesario para entrenar el modelo de la Opción A.
- **Responde a Andrés:** la matriz con huecos honestos es más fuerte que cualquier número inflado. Reformula la pregunta de "¿aRGus detecta ransomware?" a "¿qué capa de la defensa ve qué fase del ataque?", que es la pregunta correcta.
- **Reproducible:** el montaje reutiliza la topología CTU-13, los atomics son públicos, y los resultados son auditables.

**Montaje aprobado:**
- Topología CTU-13: VM `client` inyecta, `defender` observa en `eth1`.
- Atomics de Linux con perfil de LockBit (cartografiado por terceros).
- Sensores: aRGus (cabezas activables una a una para ablación), Suricata, Zeek, Wazuh.
- Entregable: matriz de detección por técnica ATT&CK, con declaración explícita de qué sensor ve qué y por qué.

**Criterio de éxito:** la matriz demuestra empíricamente la frontera NDR/HIDS. No se busca "detectar todo"; se busca "saber qué detecta cada capa y por qué", con las sombras declaradas.

---

## Resumen ejecutivo de decisiones

| # | Pregunta | Decisión | Acción inmediata |
|---|---|---|---|
| 1 | Ransomware embebido | Desactivar | ADR + `enabled: false` |
| 2 | XGBoost `proto_aligned` | Registrar DEBT + borrar | Documentar + `git rm` |
| 3 | DDoS features constantes | Registrar DEBT | Documentar, prioridad baja |
| 4 | Modelo ransomware real | Opción A (red) | Entrenar con Atomic Red Team |
| 5 | MITRE ATT&CK / Atomic Red Team | Aprobar | Ejecutar matriz de ablación |

---

## Observación final

La auditoría ha producido algo más valioso que un listado de bugs: ha producido **conocimiento arquitectónico defendible**. La frontera entre lo que aRGus puede ver (fases de red) y lo que no puede ver (cifrado en disco) no es un defecto; es una propiedad del sistema que debe publicarse con la misma rigour con la que se publican sus aciertos.

El detector de ransomware actual no se rescata reentrenándolo. Se rescata reconociendo que su dominio es otro, y que ese otro dominio requiere otro sensor. La honestidad epistémica —admitir lo que el sistema no puede ver— es la base de la transparencia absoluta en el uso de IA que define el marco ético del proyecto.

El proyecto avanza con rigor. Los hallazgos son trazables, las decisiones son reversibles, y la frontera es un entregable, no un secreto.

**Via Appia Quality — un escudo que conoce sus propias sombras.**

---

*Deliberación del Consejo de Sabios, 6 de julio de 2026.*

FDO
qwen