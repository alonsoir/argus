**CONSEJO DE SABIOS — VEREDICTO SOBRE ADR-046**
*Fecha: 2026-05-19*

El Consejo ha examinado la ADR-046 con la profundidad requerida. Es, sin duda, el documento de diseño más ambicioso y de mayor calidad presentado hasta la fecha. La visión es nítida, la justificación es sólida y el modelo de negocio open-core queda perfectamente apuntalado. Sin embargo, como es tradición en este foro, nos centraremos en identificar los puntos débiles y las omisiones, para que la construcción sea tan robusta como el resto del sistema.

---

### Respuestas a las Preguntas Abiertas (§13)

**1. Ventana de correlación — ±500ms**
**Veredicto:** La 5-tupla con ventana temporal fija es un excelente punto de partida para un prototipo, pero insuficiente para un sistema de producción o un paper científico sólido. El Consejo identifica dos debilidades:
- **NAT y Túneles:** La 5-tupla puede colapsar flujos distintos en uno solo, generando correlaciones falsas.
- **Eventos Asíncronos:** Una alerta de Suricata sobre un flujo malicioso puede generarse varios segundos *después* de que Zeek cierre el `conn.log` del mismo flujo. Una ventana fija de 500ms perderá esta correlación crucial.
  **Recomendación:** Adoptar el **`community_id`** (hash estándar de la 5-tupla, usado por Suricata, Zeek y otros) como clave primaria de correlación. Implementar una ventana configurable **por tipo de evento**, con un buffer de correlación que permita un "grace period" más largo para alertas (por ejemplo, hasta 30 segundos) antes de expirar la entrada.

**2. Orden de integración — ¿Suricata o Zeek primero?**
**Veredicto: Suricata.** Es la decisión de mayor retorno inmediato. Suricata habilita el **etiquetado automático de alta confianza** y el inicio del flywheel de aprendizaje. Es el multiplicador de fuerza del dataset. Zeek es el pintor que añade color al grafo; Suricata es el que proporciona la chapa y la pintura base.

**3. Wazuh en el edge — ¿P1 o P2?**
**Veredicto: P2 incondicional.** La visibilidad de host es el santo grial, pero Wazuh es un ecosistema complejo (manager, agentes, reglas, decodificadores) que introduce un coste operativo y una superficie de ataque un orden de magnitud superior a Suricata/Zeek. Primero demostremos que el NDR enriquecido (aRGus + Suricata + Zeek) funciona y es sostenible. Luego añadiremos la dimensión de host.

**4. `correlation-engine` scope mínimo v1**
**Veredicto: aRGus + Suricata.** Esta combinación ya produce un entregable científico y operativo de primer nivel: detección de anomalías (aRGus) + etiquetado automático y detección de firmas (Suricata). El join entre flujos y alertas es la base del grafo y del dataset enriquecido. Zeek se integra en v1.1, convirtiendo el grafo en una herramienta de investigación y no solo de alerta.

**5. `mitre-generator` — ¿ADR propio o sección?**
**Veredicto: ADR propio.** Es una herramienta de infraestructura de validación, no un componente del producto. Su lógica (orquestación de tareas, comunicación con agentes, generación de manifiestos) es compleja y específica, y merece su propio diseño documentado. La ADR-046 debe referenciarlo, pero no contenerlo.

**6. Experimento de mezcla datasets — ¿Prioridad?**
**Veredicto: Máxima prioridad para el paper.** Si los datos del experimento existen en forma recuperable, reconstruir la curva F1 vs. ratio académico/sintético es una **contribución científica de primer orden**. Es la evidencia empírica que respalda su tesis central. Si no existen, documenten el resultado sin la curva como un hallazgo cualitativo. Pero intenten recuperarlos; esa gráfica vale más que mil palabras.

---

### Puntos Débiles y Omisiones en la ADR (Más Allá de las Preguntas)

**A. La Superficie de Ataque como Riesgo Arquitectónico de Primer Orden**
El ADR introduce Suricata y Zeek como cajas negras confiables. El Consejo ve aquí el mayor riesgo no declarado. Ambos son analizadores de protocolos complejos escritos en C que históricamente han tenido vulnerabilidades de ejecución remota de código (RCE). Un adversario sofisticado que reconozca aRGus++ podría atacar el NDR a través de sus propios sensores pasivos. Un paquete malicioso diseñado para explotar un parser de HTTP de Suricata podría comprometer el nodo edge completo.
**Mitigación necesaria:** El ADR debe incluir una sección de "Hardening de Sensores". Suricata y Zeek deben ejecutarse como usuarios no privilegiados, en jaulas `systemd` o contenedores mínimos, con perfiles AppArmor/SELinux heredados del modelo EMECAS. Si un sensor es comprometido, no debe tener capacidad de afectar al `firewall-acl-agent` ni a la interfaz de red. Esta es una deuda de seguridad crítica (`DEBT-ARGUSPP-SENSOR-HARDENING-001`).

**B. Fragilidad de `std::unordered_map` para Correlación en Producción**
La descripción de la implementación (§3.3) es un esbozo de prototipo, no una arquitectura. Un mapa en memoria es volátil y no sobrevive a un reinicio, lo que causaría una pérdida de contexto de correlación y datasets incompletos. Para un sistema que debe ser "construido para permanecer", esto es un punto débil.
**Recomendación:** Diseñar el `correlation-engine` con un buffer de estado persistente, como RocksDB o un log de escritura anticipada (WAL) en disco, que permita reconstruir el estado de correlación tras un reinicio. Esto es esencial para la robustez del flywheel de aprendizaje en entornos con cortes de luz o mantenimiento.

**C. El Riesgo de la "Generalización del Sintético Puro" (§8)**
El hallazgo es brillante, pero la redacción actual puede llevar a una sobre-generalización peligrosa. La afirmación "el único que funcionó" es cierta para la detección de anomalías de comportamiento de red (botnets, C2) donde los invariantes estadísticos son el rey. **No funcionará para ataques que dependen del contexto de host o de protocolos.** Un ataque de "living-off-the-land" con herramientas legítimas o una exfiltración de datos por DNS son invisibles para los invariantes de flujo, y requieren justo el contexto de Zeek (consultas DNS a dominios DGA) y Wazuh (proceso `powershell.exe` contactando un servidor externo). El paper v24 debe matizar con precisión quirúrgica qué clase de amenazas se benefician de este enfoque y cuáles no, para no crear un punto débil académico.

**D. Ausencia de un Plan de Degradación Elegante en el Edge**
Si el edge está en modo `EXTENDED_AUTONOMY` (sin servidor central), el `correlation-engine` está fuera de línea. El edge se queda solo con aRGus básico. Esto es operativamente correcto, pero el ADR no lo menciona explícitamente. Se debe añadir una línea: "Durante la autonomía extendida, el pipeline multi-source se interrumpe; el nodo revierte a detección pura aRGus y almacena logs localmente para su envío y correlación al recuperar la conectividad." Esto evita una falsa expectativa y refuerza el valor del modo autónomo ya construido.

---

### Veredicto Final del Consejo

La ADR-046 es **APROBADA con condiciones**. Es el camino correcto, pero debe ser fortalecida en los siguientes flancos:

1.  **Añadir ADR de seguridad de sensores:** Un plan para ejecutar Suricata y Zeek con el mínimo privilegio y en aislamiento (heredero de EMECAS).
2.  **Refinar el diseño del `correlation-engine`:** Comprometerse con una arquitectura de buffer persistente (RocksDB) desde el inicio, abandonando el mapa en memoria como solución final.
3.  **Matizar la tesis del sintético puro:** En el paper v24, acotar el hallazgo al dominio de anomalías de comportamiento de red para evitar una generalización falsa.
4.  **Comenzar con un alcance mínimo viable:** aRGus + Suricata. El pipeline de dos fuentes es un hito de validación científica y operativa que debe ser alcanzado y probado antes de expandir a Zeek y Wazuh.

La expansión a multi-fuente es la evolución natural y poderosa de aRGus. Con estas correcciones, el sistema no solo será un NDR/EDR híbrido, sino que lo será con la solidez arquitectónica de un sistema diseñado para durar.