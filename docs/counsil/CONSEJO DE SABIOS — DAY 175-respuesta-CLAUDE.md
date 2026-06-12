Tienes razón — soy parte del Consejo, no solo quien redacta el parte. Aquí van mis respuestas a las tres, como Claude y sin esconderme detrás del rol de escriba.

**Q1 — Orden de batalla: (A) injectors primero. Coincido con tu instinto, y con más convicción de la que tú mismo le pones.**

No es solo que (A) sea más barato. Es que **hoy has demostrado que no tienes forma determinista de generar bronce.** El paso 4 funcionó, pero dependió de levantar etcd + ml-detector + sniffer eBPF + VM cliente + replay de un pcap real. Eso no entra en un gate de CI. Significa que ahora mismo, si alguien rompe el writer mañana, el `test_correlation_roundtrip` lo caza a nivel de contrato pero **nada caza una regresión de integración** sin montar todo el circo. Los injectors con community_id son lo que convierte "verifiqué el bronce una vez a mano un viernes" en "el bronce se verifica en cada EMECAS". (B) produce una pieza nueva y vistosa; (A) protege todo lo que ya construiste. Cuando dudes entre construir hacia adelante y asegurar el terreno ganado, a 109 días de la deadline FEDER, asegura el terreno. (A).

Un matiz que añado: cuando toques los injectors, **el `synthetic_sniffer_injector` primero** (es el que alimenta el camino que hoy ejercita el bronce), y hazlo calculando community_id con la *misma* función que el sniffer real (`sniffer::flow::compute_community_id`), no con una reimplementación. Si el injector calcula el hash de otra forma, introduces una segunda fuente de verdad y un día divergirán. Reusa, no reimplementes.

**Q2 — int vs string en la columna 17: me mojo, y voto por cambiarlo a string simbólico. Esta es la que más me preocupa de las tres a nivel de contrato.**

Hoy lo dejamos en int por inercia (el writer ya hacía `static_cast`). Pero piénsalo desde el principio que tú mismo defiendes — *"JSON is the law"*, contratos auto-descriptivos, congelar vectores. Un `4` en la columna 17 es opaco: no se puede leer, no se puede auditar a ojo, y es **frágil ante un cambio del enum en el `.proto`**. Si alguien reordena `DetectorSource` o inserta un valor (algo que un proto evoluciona y permite), todo tu bronce histórico queda reinterpretado en silencio — un `4` que significaba `ML_PRIORITY` pasa a significar otra cosa, y el HMAC sigue validando porque el HMAC no sabe de semántica. Es exactamente la clase de deriva silenciosa que llevamos toda la sesión cazando, solo que diferida en el tiempo.

El nombre simbólico (`ML_PRIORITY`) cuesta ~10 bytes más por fila y es **estable frente a la evolución del enum**: el nombre no cambia aunque el número sí. Para una zona que tú mismo defines como *"bronce PRESERVA"*, preservar el símbolo legible es más fiel al principio que preservar el entero. El coste de tamaño es irrelevante (Avro/Parquet aguas arriba lo comprimen a nada). Mi voto: string simbólico, y que Kuzu mapee el nombre, no el número.

Lo único que me haría dudar: si el contrato `correlation_v1` ya estuviera congelado y desplegado en sensores en campo, cambiarlo ahora sería romper compatibilidad. Pero no lo está — estamos en el primer día que produce bronce real. **Es el momento más barato de la historia del proyecto para hacer este cambio.** Mañana es más caro. Dentro de un mes, carísimo.

**Q3 — Modelo de confianza del HMAC a escala: sí, hay una grieta, y merece ADR antes de escribir el lado consumidor. Pero no la que parece.**

El HMAC simétrico no es el problema *todavía*. Dentro de un nodo, writer y reader comparten clave de etcd y funciona. El problema aparece en el salto que tu propia arquitectura describe: **miles de sensores → un Kuzu central.** Ahí el HMAC simétrico te obliga a una de dos cosas malas: o el servidor central conoce la clave HMAC de los N sensores (superficie de ataque enorme — comprometes el central y puedes *falsificar* bronce de cualquier sensor, porque HMAC simétrico = quien verifica también puede firmar), o cada sensor tiene su clave y el central mantiene un llavero de N claves (pesadilla de rotación).

La pregunta de fondo: **¿qué propiedad quieres del bronce a escala?** Si es solo *integridad en reposo dentro del nodo* (detectar fila corrupta/truncada por el append no-atómico), el HMAC simétrico sobra y está bien. Pero si es *autenticidad de origen cross-nodo* (el central confía en que esta fila vino de *este* hospital y nadie la falsificó), necesitas firma **asimétrica** — y ya tienes Ed25519 rodando para plugins (ADR-025) y para los binarios de producción. El sensor firma con su clave privada, el central verifica con la pública, y comprometer el central **no** permite falsificar bronce ajeno. Esa es la propiedad que un sistema que protege infraestructura crítica de verdad quiere.

Mi recomendación concreta: **no cambies el HMAC ahora** (sirve para la integridad intra-nodo de hoy), pero **abre un ADR** —algo como "ADR-051: modelo de confianza de la zona bronce a escala multi-nodo"— que documente explícitamente que el HMAC simétrico es para integridad local, y que el salto a correlación central requiere reevaluar hacia firma asimétrica por-sensor. Anclarlo ahora, en una línea de ADR, cuesta una tarde. Descubrirlo cuando tengas tres hospitales mandando bronce a un Kuzu central cuesta un rediseño del transporte. Tú plantaste la semilla bien en la pregunta; mi respuesta es: sí, riégala, pero como ADR de diseño futuro, no como cambio de código de mañana.

---

Resumen de mis votos para que los tengas separados del resto del Consejo cuando integres: **Q1 → injectors primero (A), reusando `compute_community_id`. Q2 → cambiar a string simbólico ahora, es el momento más barato. Q3 → no tocar HMAC, abrir ADR-051 de modelo de confianza a escala.**

La que defiendo con más fuerza es Q2 — esa la cambiaría antes de que el Consejo responda siquiera, porque cada fila de bronce que escribas hasta entonces es una fila con un int opaco que algún día habrá que migrar. Las otras dos pueden esperar al consenso. Esa no.

FDO

CLAUDE