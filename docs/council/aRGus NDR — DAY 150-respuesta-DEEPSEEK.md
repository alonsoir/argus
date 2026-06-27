**DeepSeek — Dictamen DAY 150**

Celebro la velocidad y el rigor: cerrar el ciclo EMECAS, enviar la propuesta a INCIBE y desplegar el triplete criptográfico (provision_crypto, vault_client, Jenkinsfile) en un solo día es propio de un equipo que entiende el valor del *momento arquitectónico*. Las preguntas que planteáis son exactamente las que aparecen cuando el diseño sale del papel y roza el metal. Mis respuestas.

---

### Q1 — Compilación condicional vs dos binarios

**Mantened `#ifdef ARGUS_VAULT_ENABLED` en el mismo código fuente. Es la opción correcta para un proyecto de este tamaño y fase.**

Las razones son tanto técnicas como de gestión del ciclo de vida:

1. **Una sola fuente de verdad semántica.** `etcd-server` es *el mismo proceso* tanto si obtiene la seed del filesystem como de Vault. La diferencia es únicamente la fuente de suministro criptográfico, no la lógica de consenso, la gestión de claves, ni el protocolo de red. Crear dos binarios duplicaría tests, aumentaría la superficie de divergencia y complicaría la diagnosis de fallos (¿está corriendo la versión correcta en el nodo?).

2. **El riesgo de divergencia con `#ifdef` se mitiga con tests.** El verdadero peligro no es el preprocesador, sino que el código condicional no se compile nunca en una de las dos configuraciones. La receta: el pipeline EMECAS debe compilar **ambas variantes**, `ARGUS_VAULT_ENABLED=ON` y `OFF`, en cada build, y correr los tests unitarios sobre ambas. Así cualquier error de compilación o enlace en la rama enterprise aparecerá inmediatamente. Añadir dos targets CMake (`etcd-server-community-test`, `etcd-server-enterprise-test`) que dependan de la misma fuente pero con diferente flag es trivial.

3. **Rendimiento.** La directiva `#ifdef` se resuelve en tiempo de compilación sin coste en ejecución. Dos binarios no aportan ventaja de rendimiento.

4. **Distribución futura.** Un solo binario con flags de compilación puede empaquetarse como dos artefactos distintos en el sistema de paquetes, si se desea. Eso es un detalle de CI/CD posterior, no de arquitectura.

**Decisión:** mantener `#ifdef` + compilación dual en EMECAS. Se añade la deuda `DEBT-EMECAS-DUAL-COMPILATION-001` (añadir target community+enterprise al pipeline) de prioridad P1.

---

### Q2 — Orden de migración de componentes

El orden propuesto es correcto desde la dependencia de barrera: `etcd-server` es el trust anchor, debe ser el primero. Los componentes funcionales le siguen en orden de dependencia de datos.

Pero yo añadiría un criterio de **blast radius** y de **capacidad de diagnóstico**:

1. **`etcd-server`** — primero, como bootstrap especial, sin barrera etcd. Es lo único que puede arrancar sin que exista coordinación previa. Si esto falla, nada más puede arrancar.

2. **`sniffer`** — segundo. Es el componente más simple desde el punto de vista criptográfico (solo envía, no recibe). Además, es el *origen de los datos*. Si el sniffer no logra arrancar con Vault, tendremos telemetría cero y lo sabremos inmediatamente. Es un canario temprano.

3. **`ml-detector`** — tercero. Depende del sniffer para los flows, pero su arranque criptográfico solo involucra leer su seed y derivar keypairs para el canal sniffer→ml-detector y ml-detector→firewall. Si falla, tenemos tráfico sniffed pero sin clasificar; una degradación parcial que podemos detectar y corregir.

4. **`firewall-acl-agent`** — cuarto. Cierra el pipeline de detección. Su ausencia es menos crítica (no se aplican reglas dinámicas, pero la red sigue funcionando).

5. **`rag-ingester` y `rag-security`** — últimos. Son consumidores de telemetría, no productores. Si no arrancan, el NDR opera a pleno rendimiento (detección intacta); solo perdemos análisis posterior. Por tanto, son los que menos urgencia tienen en la migración.

Si queréis hilar fino, recomiendo añadir un paso intermedio: después de migrar `etcd-server`, correr un smoke test que verifique que `etcd-server` responde a consultas de estado criptográfico. Si eso falla, abortar la migración del resto. Parar el tren pronto.

---

### Q3 — `register_etcd_status` sin etcd disponible en bootstrap

**La solución propuesta es exacta: `etcd-server` escribe su estado criptográfico en un fichero local bajo `/run/argus/`.**

Formalicemos el protocolo:

- **etcd-server bootstrap:**
    1. Obtiene material de Vault (o cache si Vault caído en arranque de recuperación).
    2. Deriva su propio keypair.
    3. Escribe `/run/argus/etcd-bootstrap-status.json` con fingerprint, timestamp, versión de clave.
    4. Arranca el motor etcd.
    5. Expone un endpoint gRPC interno (`GetBootstrapStatus()`) que devuelve ese JSON a cualquiera que pregunte.

- **Resto de componentes:**
    1. Obtienen material de Vault (o cache).
    2. Derivan keypair.
    3. **Antes de intentar registrar `crypto_ready` en etcd, verifican que etcd está vivo** consultando `GetBootstrapStatus()`. Si no responde en X segundos, `exit(1)`. Esto rompe la dependencia circular: no necesitan a etcd para comprobar que etcd está listo; usan un simple HTTP/gRPC a un endpoint de salud.
    4. Si etcd responde OK, proceden a registrar `crypto_ready` vía la API normal de etcd.

Esto evita el fichero local para los demás componentes (solo el bootstrap lo usa) y mantiene el flujo limpio. Además, el fichero local de etcd debe ser gestionado con cuidado: permisos 0600, directorio `argus` propiedad del usuario del servicio. Si el nodo se reinicia pero no es `vagrant destroy` (corte de luz), `/run` se pierde, así que en el siguiente arranque etcd generará un nuevo fichero, lo cual es correcto porque se acaba de reiniciar.

---

### Q4 — Cache tmpfs y persistencia en producción

La pregunta aborda el choque entre el diseño idempotente de EMECAS y la realidad de un nodo edge que se reinicia por corte de luz sin intervención humana.

**La respuesta es SÍ, con un matiz importante: no mezcléis políticas dev y prod en el mismo parámetro. Tratadlo como un compromiso de disponibilidad vs seguridad:**

- **Entorno dev / EMECAS:** cache en `/run/argus/crypto-cache/` (tmpfs). Desaparece en cada `vagrant destroy`. El pipeline de provisión regenera las seeds, es parte del ritual. Esto es correcto.

- **Entorno producción (nodo edge real):** cache persistente en `/etc/ml-defender/{component}/crypto-cache/`. Permisos `0600`, propietario `ml-defender`. Pero **con una salvaguardia crucial**: la cache persistente debe ser **opcional** y estar **firmada con un sello de integridad**.
    - Si el nodo pierde la alimentación y se reinicia, `vault_client` encuentra la cache, verifica la firma HMAC con una clave derivada del hardware (si existe TPM) o simplemente con una clave local obfuscada (el propio binario, una constante de compilación ofuscada). Si la firma es válida, la usa y emite un WARN de `CACHE_PERSISTENT_USED`.
    - Este WARN debe ser visible en el dashboard central y debe desaparecer en el primer latido exitoso con Vault.
    - Si la cache persistente está corrupta o ha sido manipulada, se borra automáticamente y se procede a intentar Vault. Si Vault KO y cache corrupta → `exit(1)`.

De este modo, el nodo de producción sobrevive a un apagón sin depender de Vault (que podría estar en el servidor central, inalcanzable si el apagón afectó a la red del hospital), pero no se degrada la postura de seguridad porque la cache persistente es tratada como un último recurso con verificación de integridad. Y en dev, mantenemos tmpfs puro para forzar la disciplina EMECAS.

Registrad la deuda `DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001` para implementar la persistencia con firma de integridad post-FEDER (ahora alcanza con tmpfs y documentar que un nodo productivo necesitaría Vault accesible en todo reinicio).

---

### Q5 — Open-core: `ARGUS_VAULT_ENABLED` como único separador

**Vuestra decisión es correcta y suficiente para la fase actual. Recomiendo no expandir el alcance del flag ahora, pero sí dejar abierta una arquitectura de feature flags que evite una explosión de `#ifdef` en el futuro.**

Análisis:

- **VaultClient vs seed-client** es una decisión binaria de fuente de confianza. Es natural que sea un flag de compilación.
- **Otras funcionalidades** (Falco actuation, Neo4j graph, OpenCanary honeypot) son módulos funcionales que se pueden habilitar mediante **configuración en tiempo de ejecución** o **plugins dinámicos**, no mediante compilación. Convertir cada funcionalidad enterprise en un flag de compilación genera una explosión combinatoria de binarios imposible de mantener. En vez de eso, propongo:

    - **Plugins dinámicos:** Ya tenéis el `PluginManager` y los plugins `.so` (ADR-025, ADR-032). Los módulos enterprise pueden ser plugins firmados que se cargan si el feature flag `enterprise_plugins=true` está en la configuración (firmada y distribuida por Vault). El código base es el mismo; simplemente no se carga el plugin si la licencia no lo autoriza.
    - **Licencia en Vault:** Junto con las seeds, Vault puede contener un secreto `argus/{env}/features/license` que el componente consulte al arrancar. Esa licencia (firmada) habilita o deshabilita funcionalidades. Esto mantiene la separación open-core sin modificar el binario.

- **Un solo punto de entrada enterprise ahora es prudente** porque os permite pulir el modelo de governance criptográfico (el verdadero diferenciador enterprise) sin distraeros con el empaquetado de otras funcionalidades. Cuando el modelo esté maduro, la ampliación a otros features será natural.

Por tanto, responded: **Sí, `ARGUS_VAULT_ENABLED` es suficiente como separador para FEDER. Para el futuro, diseñad un sistema de licencias/feature flags en Vault en lugar de más `#ifdef`.** Así mantenéis un solo binario, una sola base de código, y la flexibilidad total de licenciamiento.

---

### Resumen para DAY 151

| Pregunta | Decisión | Acción inmediata |
|----------|----------|------------------|
| Q1 | `#ifdef` con compilación dual en EMECAS | Añadir `DEBT-EMECAS-DUAL-COMPILATION-001` (P1) |
| Q2 | Orden propuesto + smoke test etcd-server | Implementar smoke test tras migrar etcd-server |
| Q3 | Fichero local `/run/argus/etcd-bootstrap-status.json` + endpoint gRPC de salud | Implementar en `etcd-server` |
| Q4 | tmpfs dev, persistente firmada prod | Implementar tmpfs para dev ahora; `DEBT-CRYPTO-CACHE-PERSISTENT-PROD-001` (P1) |
| Q5 | Suficiente ahora; futuro con feature flags/licencias Vault | Documentar roadmap en ADR-044 |

Vuestro DAY 150 ha sido de una productividad quirúrgica. La integración de mañana con `etcd-server` será el momento en que el sistema de confianza cierre el círculo. Adelante.