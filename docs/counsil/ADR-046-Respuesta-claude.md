## Feedback Claude — ADR-046 · Consejo DAY 156

---

### Veredicto general

Arquitecturalmente sólido. Científicamente honesto. El §8 (datasets sintéticos vs académicos) es la contribución más valiosa del documento — y la más arriesgada si los datos del experimento no existen en forma recuperable.

Cinco observaciones técnicas para el Consejo:

---

### 1. ZeroMQ — backpressure no resuelta (§3.2)

El canal existente fue calibrado para CSV de flujos aRGus. Zeek `conn.log` y Suricata `eve.json` en una red hospitalaria activa pueden generar tasas de eventos cualitativamente distintas, especialmente durante un incidente. BACKLOG-ZMQ-TUNING-001 estaba optimizado para el perfil de aRGus solo.

**Riesgo concreto:** HWM actual puede producir drop silencioso de eventos Zeek/Suricata bajo carga sin que el sistema lo detecte.

**Deuda sugerida:** `DEBT-ARGUSPP-ZMQ-BACKPRESSURE-001` — calibrar HWM para las cuatro fuentes activas simultáneamente, con métricas de drop explícitas.

---

### 2. Semántica de timestamps en Zeek para el join (§3.3)

El join por 5-tupla con ventana ±500ms asume que todos los timestamps son de inicio de evento. Pero `conn.log` de Zeek registra la conexión al **cierre**, no al primer paquete. En conexiones de larga duración, el timestamp de Zeek puede diferir horas del momento en que Suricata disparó la alerta sobre los primeros paquetes.

**Consecuencia:** joins incorrectos o ausentes para exactamente las conexiones más interesantes — las que duran mucho y disparan alertas al inicio.

**Solución:** usar `ts` (timestamp inicio) de Zeek, no el timestamp de escritura del log. Documentar explícitamente qué campo se usa como clave temporal en cada fuente antes de implementar `correlation-engine`.

---

### 3. Lenguaje de `mitre-generator` (§7)

El ADR dice C++20 para el orquestador. Pero `mitre-generator` no está en el pipeline de producción — es una herramienta de laboratorio para experimentos controlados. Su función es: lanzar procesos, registrar timestamps, escribir un JSON. La regla "sin Python en producción" no aplica aquí.

C++20 para esto añade complejidad sin beneficio de seguridad ni rendimiento. Un script Python o incluso bash produce el mismo manifiesto JSON con un décimo del esfuerzo.

**Propuesta al Consejo:** `mitre-generator` como herramienta de investigación en `tools/research/`, lenguaje pragmático (Python), explícitamente fuera del pipeline de producción. La regla C++20 protege el pipeline edge/servidor — no los scripts de experimento.

---

### 4. La hipótesis del §4 necesita cualificación

```
F1(ensemble enriquecido) > F1(aRGus solo) > F1(Suricata solo) > F1(Zeek solo)
```

Esta ordenación es verdadera **sobre ataques desconocidos/comportamentales**. Sobre firmas conocidas, Suricata ganará a aRGus por diseño — es para lo que existe. Si el conjunto de evaluación mezcla ambos tipos, la ordenación puede invertirse y la hipótesis publicada quedaría refutada por el propio experimento.

**Corrección sugerida:** añadir la condición explícita: *"sobre técnicas ATT&CK no presentes en el conjunto de reglas ET Open activas en el momento del experimento"*. Eso es lo que aRGus realmente afirma y es defendible.

---

### 5. §8 — el experimento de mezcla: publicar sin los datos es riesgo

§8.3 documenta que los datos del experimento (curva F1 vs ratio) *podrían no existir en forma recuperable*. §13 Q6 lo reconoce como pregunta abierta.

**Posición clara:** si los datos no existen, §8 en el paper v24 debe formularse como hipótesis teórica con justificación (Sommer & Paxson + argumento de sesgo de construcción), no como resultado empírico. Afirmar un resultado experimental sin los datos es el tipo de imprecisión que Sebastian Garcia detectará en revisión.

**Decisión binaria para el Consejo:** ¿reconstruimos el experimento (coste: tiempo, requiere MITRE ATT&CK activo), o documentamos la justificación teórica sin curva? Ambas son opciones honestas. La mezcla no lo es.

---

### Resumen para el acta

| # | Observación | Severidad |
|---|---|---|
| 1 | ZeroMQ backpressure no calibrada para 4 fuentes | Alta — registrar deuda |
| 2 | Timestamp semantics Zeek conn.log para join | Alta — especificar antes de implementar |
| 3 | C++20 para mitre-generator innecesario | Media — decisión de política |
| 4 | Hipótesis §4 sin cualificación del conjunto de evaluación | Media — corrección de paper |
| 5 | §8 sin datos: resultado vs hipótesis | Alta — integridad científica |

**Voto:** ADR-046 aprobado como borrador con las cinco observaciones como condiciones de cierre antes de implementación de `correlation-engine`.

---

¿Lo integro así en el documento de actas del Consejo, o quieres ajustar algún punto antes?