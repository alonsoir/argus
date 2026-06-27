**Respuesta del Consejo de Sabios — ADR-046 v2 (DAY 158)**

Apreciado Alonso y equipo,

Hemos revisado con detenimiento la v2 del ADR-046. La incorporación de Wazuh como cuarto plano ortogonal y el modelo de **crisis como ventana de correlación** son contribuciones sólidas. El documento está mucho más maduro. Pasamos directamente a responder las **preguntas abiertas** y a añadir observaciones de alto nivel.

### 1. Timeout de espera (60s)

**Acuerdo con 60s como default**, pero **debe ser configurable por tipo de disparador y por despliegue**.

- **Suricata/ZeeK/aRGus**: suelen ser casi inmediatos (sub-segundo a pocos segundos). Un timeout corto (10-15s) sería suficiente.
- **Wazuh**: asíncrono por naturaleza (agente → manager → servidor). En entornos con latencia de red o managers cargados puede tardar 10-40s fácilmente. 60s es prudente aquí.

**Recomendación de implementación:**
- Mapa de timeouts por `CrisisSource` (configurable vía JSON o etcd/consul).
- Timeout dinámico: al recibir el primer evento de una crisis, se establece el timeout según el disparador + un margen fijo (ej. +30s).
- Si llega señal de Wazuh después del timeout pero dentro de un margen ampliado (ej. 120s), permitir “late join” con marca explícita `late_arrival: true` en el registro enriquecido. Esto evita perder contexto valioso sin contaminar la mayoría de los casos.

Escenario donde 60s puede ser insuficiente: despliegues muy distribuidos (satélite, conexiones 4G/5G intermitentes en infra crítica). Escenario donde es excesivo: entornos de baja latencia con miles de nodos (ruido en buffers). → **Configurable + monitoring del % de late arrivals**.

### 2. Orden de integración en Vagrantfile / EMECAS

**Prioridad clara: Suricata primero.**

Razones:
- Aporta **ground truth inmediato** de alta confianza (reglas ET). Esto desbloquea etiquetado automático y validación temprana del correlation-engine aunque solo tengamos aRGus + Suricata.
- Integración más sencilla (eve.json → ZeroMQ ya existente).
- Menor curva de aprendizaje para el equipo.
- Impacto más rápido en el paper/experimentos.

Zeek segundo: su valor (contexto semántico L7, JA3, files.log, etc.) brilla más cuando ya tienes correlación y grafo. Wazuh tercero.

Orden propuesto: **Suricata → Zeek → Wazuh**.

### 3. Wazuh en el edge — Prioridad

**P1 junto a Suricata y Zeek**, pero con **faseo inteligente**.

No lo dejéis para P2. La cobertura host es el gran diferenciador de aRGus++ frente a soluciones NDR puras. Sin embargo, aceptamos que en Tier 1 (RPi5 puro) pueda ir desactivado por defecto.

**Propuesta de faseo:**
- Fase 1 (inmediata): Wazuh agent mínimo (FIM + auth + rootcheck).
- Fase 2 (post-hardware): syscalls (auditd integration) y active response (solo si se abre el ADR de enriquecer protobuf).

Esto permite validar pronto la correlación red-host, que es uno de los puntos más interesantes del diseño.

### 4. Scope mínimo de correlation-engine v1

**Total acuerdo con la propuesta.**

**v1 scope mínimo recomendado:**
- Disparador principal: aRGus (ML score) + Suricata (alert severity).
- Buffers circulares por nodo (tiempo fijo o tamaño).
- Flush on crisis → Parquet enriquecido (incluso si faltan fuentes).
- Soporte para registros “parciales” (campos null/empty).
- Métricas de latencia de llegada y % de completitud por crisis.

**v2** (post-hardware y mediciones): join completo con Zeek + Wazuh, lógica de late arrival, grafo Neo4j en caliente, y disparadores completos de 4 fuentes.

Esto reduce riesgo y permite avanzar en paralelo con las mediciones de recursos.

### 5. mitre-generator — ¿ADR propio?

**Sí, merece ADR-047 independiente.**

Es un componente con entidad propia: orquestador de experimentos, generador de ground truth verificable, y pieza clave del flywheel científico. Tiene implicaciones en reproducibilidad de investigación, que es material de paper. Tratarlo como sección diluye su importancia. ADR-047 puede ser corto pero debe definir claramente el manifiesto JSON como contrato.

### 6. Experimento de mezcla datasets (académico vs sintético)

Los datos del experimento existen (curvas F1 vs ratio académico/sintético). Están en los logs y notebooks de DAY ~142-148. Podemos recuperarlos. Incluidlos en el paper v24 con la sección propuesta *"On the inadequacy of academic datasets..."*. Es oro científico y fortalece mucho la narrativa de por qué aRGus aprende invariantes comportamentales.

---

### Observaciones adicionales del Consejo

- **NTP**: P0 sin discusión. Añadir healthcheck automático en rag-security (drift > 2s → alerta).
- **Rendimiento**: Exigimos las mediciones DEBT-ARGUSPP-RESOURCE-001 antes de cualquier claim de tiers. Especialmente crítico en RPi5 con Suricata + aRGus simultáneos.
- **Grafo Neo4j**: El nodo `Crisis` es la joya. Aseguraros de que las relaciones tengan propiedades temporales (`duration_ms`, `trigger_source`, `completeness_score`).
- **Hipótesis científica**: La mantenemos. El experimento MITRE ATT&CK en tiempo real será el árbitro definitivo.
- **Filosofía**: “Un escudo que aprende de su propia sombra” se mantiene como lema potente.

**Estado recomendado para ADR-046**: **APROBADO con las modificaciones arriba indicadas**. Pasar a **IMPLEMENTACIÓN** una vez incorporadas las respuestas.

Estamos listos para la revisión de ADR-047 (mitre-generator) cuando lo tengáis.

Que la señal sea clara y la correlación oportuna.

**Consejo de Sabios**  
*Via Appia Quality — DAY 158*