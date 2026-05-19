Perfecto, el orden correcto. Mis respuestas a las seis preguntas abiertas del Consejo:

---

**Pregunta 1 — Timeout de espera (60s)**

60s es correcto como default para FEDER pero debería ser configurable por tipo de disparador desde el JSON de configuración del correlation-engine. Mi propuesta concreta:

```json
{
  "correlation_timeouts_sec": {
    "argus":    15,
    "suricata": 10,
    "zeek":     20,
    "wazuh":    90
  }
}
```

Wazuh necesita más tiempo por su naturaleza asíncrona. Suricata es casi instantáneo. El timeout del correlation-engine para cerrar una CrisisWindow debería ser `max(timeouts) + margen` — es decir, ~120s como timeout de ventana completa. Si una fuente no llega en su timeout individual, se registra como vacía y no bloquea el cierre del registro.

---

**Pregunta 2 — Orden de integración en Vagrantfile**

**Suricata primero.** Tres razones:

La primera es que el valor es inmediato: desde el primer día de ejecución con Suricata activo tienes etiquetado automático de alta confianza para el entrenamiento. Zeek enriquece el grafo pero no etiqueta.

La segunda es complejidad de integración: Suricata en Vagrant es un `apt-get install suricata + suricata-update` más configurar la interfaz en modo pasivo. Ya tienes experiencia con él de los experimentos DAY 146-148. Zeek requiere más trabajo de configuración de scripts y parseo de sus logs en múltiples ficheros.

La tercera es que el valor científico es más directo: Suricata como ground truth automático resuelve el problema del etiquetado que lleva meses pendiente. Zeek como contexto de protocolo es valioso pero no desbloqueante.

---

**Pregunta 3 — Wazuh en el edge — prioridad**

**P2, después de validar Suricata + Zeek en hardware físico.** El razonamiento:

El agente Wazuh cabe en RPi5 de 8GB, pero la pregunta no es si cabe en reposo — es si cabe junto a aRGus + Suricata + Zeek bajo carga real de tráfico con pentesting MITRE activo. Eso solo se puede medir con hardware físico. Añadir Wazuh antes de tener esa medición es arriesgarse a descubrir en la demo FEDER que el RPi5 se satura.

La secuencia correcta: Suricata en Vagrant (DAY 158+) → Zeek en Vagrant → hardware físico → medir los tres juntos → si hay margen, añadir Wazuh agent → si no hay margen, Wazuh solo en N100 Tier 2.

---

**Pregunta 4 — `correlation-engine` v1 scope mínimo**

**Acuerdo completo con la propuesta.** El v1 que propongo:

- Un único disparador: aRGus ML score > umbral (el más simple y el que ya tienes)
- Buffer circular por nodo con timestamp
- Flush a Parquet cuando se dispara — sin join todavía, solo el registro aRGus enriquecido con su propio contexto temporal
- La infraestructura de CrisisWindow ya presente pero con los campos `suricata`, `zeek`, `wazuh` siempre vacíos en v1

El v1 es valiosa por sí misma: establece el patrón arquitectónico, tiene tests, y produce Parquet desde el primer día. El join multi-fuente es v2 cuando Suricata y Zeek estén integrados. El meta-learner es v3.

---

**Pregunta 5 — `mitre-generator` ADR propio**

**ADR-047 independiente.** El mitre-generator tiene suficiente complejidad propia para merecer su propio documento:

- Decisiones de diseño propias: ¿Atomic Red Team como dependencia externa o scripts propios? ¿Caldera para campañas completas o solo técnicas atómicas? ¿Formato del manifiesto JSON como contrato?
- Componente con su propio ciclo de vida: no forma parte del pipeline de producción, es infraestructura de investigación
- Implicaciones de seguridad propias: el orquestador de ataques debe estar completamente aislado de los nodos de producción — eso es una decisión arquitectónica mayor

ADR-046 lo referencia como dependencia. ADR-047 lo define.

---

**Pregunta 6 — Experimento de mezcla datasets**

Aquí necesito que me confirmes algo antes de responder definitivamente: ¿los datos del experimento de mezcla académico/sintético existen en alguna forma — logs, scripts, notebooks, apuntes — o solo existe el resultado final (sintético puro es el único que funcionó)?

Si los datos existen aunque sea parcialmente, la curva F1 vs ratio se puede reconstruir y vale la pena incluirla en v24 porque convierte una afirmación en evidencia empírica. Si no existen, el resultado sigue siendo publicable como hallazgo cualitativo con justificación teórica — menos contundente pero válido. La respuesta cambia lo que propongo para la sección §8 del paper.

---

Cuando tengas el feedback del Consejo y me confirmes la pregunta 6, preparo el diff de BACKLOG.md y README.md en un solo script.