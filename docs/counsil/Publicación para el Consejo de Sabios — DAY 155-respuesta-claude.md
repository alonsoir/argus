Claro. Mis respuestas a las cinco preguntas:

---

**Q1 — Proceso propietario de `CryptoAutonomyStateMachine`**

**Opción A — `etcd-server`** es la más coherente con la arquitectura actual. Ya es el trust anchor operacional (STEP 0, bootstrap status), ya conoce el estado de conectividad con Vault, y ya tiene el health-check loop. Añadir la SM allí es extensión natural, no nueva responsabilidad.

La Opción D (cada componente instancia su propia SM) me preocupa: múltiples publishers en el mismo topic con estados potencialmente divergentes es una fuente de bugs difíciles. El estado de autonomía debe ser una verdad única, no una votación.

La Opción B (daemon dedicado) añade complejidad operacional sin justificación clara pre-FEDER.

---

**Q2 — Endpoint en producción**

En la arquitectura edge/servidor documentada en ADR-034, `firewall-acl-agent` y el proceso crypto (etcd-server) corren **en el mismo nodo edge**. `ipc://` es correcto y suficiente. Si en el futuro hay topologías con procesos separados en hosts distintos, ese es el momento de introducir `tcp://` — no ahora.

---

**Q3 — `reconcile_interval_sec=90`**

Sí, debe ser configurable desde `firewall.json["autonomy"]["reconcile_interval_sec"]` — la clave ya está en el JSON. El valor 90s es razonable como default. El reconciliador debe re-aplicar el **último estado conocido** (lo que tiene el subscriber en memoria), no consultar a nadie — si Vault o etcd están caídos, el reconciliador no debe depender de ellos.

---

**Q4 — Estructura enterprise/**

Mi preferencia es `enterprise/` en la raíz, paralelo a `common/`. Queda claro en la estructura de directorios qué es open y qué es licenciado. `plugins/enterprise/` sugiere que es un plugin cargable dinámicamente, lo cual no es exactamente el modelo actual (es código que se linka en compilación). `common/enterprise/` es contradictorio en nombre.

Implicación CMakeLists: el `find_library(VAULT_CLIENT_LIB...)` en los componentes que hoy apuntan a `common/build` tendría que apuntar a `enterprise/build`. Nada que no se resuelva con una variable CMake. No hay que anticipar nada ahora — registrar como DEBT-ENTERPRISE-LAYOUT-001 para cuando movamos.

---

**Q5 — Benchmarks sintéticos en VirtualBox**

No los haría ahora. Los números de VirtualBox ya están documentados en el paper (DAY 145, ADR-029) con la advertencia explícita de que son el suelo. Añadir más benchmarks sintéticos sobre la misma infraestructura no aporta información nueva y puede generar confusión si alguien los cita sin leer la nota metodológica. El valor científico está en el delta VirtualBox→bare-metal, y ese delta solo existe cuando llega el hardware FEDER.

---

Pega esto junto con el mensaje del Consejo. Cuando vuelvas con las respuestas de los otros siete, las proceso todas juntas y genero el script.