Estimado Alonso (PI, aRGus NDR), es un honor para este **Consejo de Sabios** comparecer en el **DAY 175**.

La consecución del cableado E2E de la Zona Bronce y la validación quirúrgica del flujo real (*sniffer eBPF → community_id → ZMQ → ml-detector → bronce → reader*) es un hito de ingeniería extraordinario. Tu máxima de **"medir, no presuponer"** ha vuelto a salvar el proyecto de un falso verde que habría sido catastrófico aguas abajo. La detección temprana del `DEBT-BRONZE-KEY-PROVISIONING-001` justifica por sí sola la rigurosidad de tu metodología.

A continuación, emitimos nuestro dictamen técnico unificado y fundamentado para las batallas inmediatas.

---

## 4. Respuestas a las Preguntas del Consejo

### Q1 — Orden de batalla: ¿(A) Injectors sintéticos o (B) Consumidor del Engine?

El Consejo **coincide unánimemente contigo: (A) debe ir primero**.

* **Fundamento de CI/CD y Determinismo:** Diseñar el lado consumidor (B) sin una fuente de datos sintética, determinista y controlada en el entorno de testing (CI) te obligaría a depender de replays de PCAP y del stack eBPF vivo para cada prueba de regresión. Esto introduce flujos no deterministas y eleva el coste de ejecución del pipeline de test.
* **Aislamiento de Errores:** Al dotar primero a los `synthetic_*_injector` de la capacidad de generar `community_id`, garantizas que cuando construyas el *file_watch* y el procesador Avro del engine (B), dispondrás de un generador de carga sintética calibrado para estresar el consumidor de inmediato.

> **[SUGERENCIA-GEMINI]:** Al actualizar los injectors sintéticos, implementa la generación del `community_id` mediante una función auxiliar compartida (utilizando los campos de la tupla de 5 elementos estándar: IP origen/destino, puertos y protocolo) para garantizar que los IDs sintéticos sigan exactamente el mismo algoritmo de hashing que el sniffer real.

---

### Q2 — `authoritative_source` como int crudo vs String Simbólico (Columna 17)

El Consejo determina que **el bronce debe migrar a String Simbólico (`ML_PRIORITY`, `DIVERGENCE`, etc.)**.

Aunque la premisa *"bronce preserva, gold decide"* es arquitectónicamente sacrosanta, el almacenamiento de un `int` crudo (derivado de un `enum` de Protobuf) en un archivo de texto CSV plano de persistencia a largo plazo rompe el principio de desacoplamiento y estabilidad del contrato por las siguientes razones:

1. **Fragilidad ante la evolución de Protobuf:** Si en el futuro se reordenan los enums, se elimina uno intermedio o se cambia su numeración en el `.proto`, los archivos de bronce históricos almacenados en disco quedarán **corrompidos retroactivamente** o requerirán un mapa de traducción por versión histórica extremadamente complejo.
2. **Transparencia de la Zona Bronce:** El almacenamiento en Bronce (CSV) se beneficia enormemente de ser auto-descriptivo. El trade-off de rendimiento/tamaño por escribir `"ML_PRIORITY"` en lugar de `"4"` en un string CSV es insignificante comparado con la inmunidad que otorga frente al cambio de esquemas.

> **[SUGERENCIA-GEMINI]:** Modifica el `CorrelationWriter` para que escriba `DetectorSource_Name(event.authoritative_source())`. El `parse_and_verify` del engine debe aceptar este string simbólico. Kuzu seguirá decidiendo aguas arriba, pero basándose en un contrato de texto inmune a la reordenación de enums de Protobuf.

---

### Q3 — `DEBT-BRONZE-KEY-PROVISIONING-001` y el Modelo de Confianza Multitenant / Descentralizado

Has detectado una **grieta tectónica potencial** en la escalabilidad a largo plazo de la arquitectura medallion. El HMAC simétrico por componente funciona perfectamente bajo el supuesto de un único nodo (*Single-node deployment*), pero colapsa bajo el modelo de miles de sensores remotos reportando a un Kuzu central por los siguientes motivos:

* **Problema de Distribución de Secretos:** Si el Kuzu central debe validar HMACs simétricos de $N$ sensores, o bien todos comparten la misma clave (un desastre de seguridad: un sensor comprometido compromete la integridad del bronce de toda la red), o el nodo central debe gestionar y almacenar $N$ claves simétricas de forma segura.
* **Falta de No-Repudio:** El HMAC simétrico demuestra que la fila fue generada por alguien que posee la clave, pero no diferencia de forma unívoca al emisor frente al receptor si ambos comparten la misma clave.

**Dictamen del Consejo:** El HMAC simétrico actual es perfectamente válido para la actual fase de desarrollo y para asegurar el transporte local *intra-nodo*. Sin embargo, la proyección multitenant exige **firma asimétrica**.

* El sensor (origen) debe firmar el bloque/fichero de bronce utilizando su **clave privada Ed25519** (infraestructura que ya has validado para los plugins).
* El Kuzu central (consumidor) solo requerirá la **clave pública** de dicho sensor para verificar la autenticidad y el no-repudio, eliminando la necesidad de transmitir secretos críticos por la red.

> **[SUGERENCIA-GEMINI]:** Consolida el HMAC simétrico para cerrar el hito local del `correlation-engine` mañana, pero abre de inmediato un **ADR-046 (Modelo de Confianza Asimétrico para la Zona Bronce Multitenant)**. Esto evitará que la lógica de aprovisionamiento de claves de etcd que vas a programar en el engine mañana se convierta en una barrera arquitectónica rígida cuando aRGus NDR dé el salto a la infraestructura distribuida.

---

El camino hacia el 22 de septiembre (FEDER) se mantiene firme y despejado gracias a que rehúsas operar sobre supuestos no verificados. Quedamos a la espera de las órdenes para el DAY 176.

FDO GEMINI