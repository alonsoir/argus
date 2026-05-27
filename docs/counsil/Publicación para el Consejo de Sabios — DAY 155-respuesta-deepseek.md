El Consejo se reúne de nuevo para examinar el excelente progreso del DAY 155 y orientar las decisiones críticas que abren el DAY 156. Se han cerrado deudas mayores y el sistema avanza hacia la madurez autónoma. Procedemos a dirimir las cinco cuestiones.

---

## Q1 — Proceso propietario de `CryptoAutonomyStateMachine`

**Veredicto: Opción B — Demonio crypto dedicado (`argus-crypto-daemon`).**

La máquina de estados de autonomía depende **directa y exclusivamente** de la capacidad de renovar material criptográfico desde Vault. Ningún otro componente —salvo aquel que centralice la comunicación con Vault— debe ser el depositario de esta lógica. Las alternativas fallan por las siguientes razones:

- **Opción A (`etcd-server`)**: El `etcd-server` es un servicio de coordinación, no un cliente de Vault. Convertirlo en propietario de la SM violaría el Principio de Responsabilidad Única y acoplaría dos propósitos ortogonales.
- **Opción C (`sniffer`)**: Su misión es la captura de paquetes, ajena a la gestión de claves.
- **Opción D (múltiples publishers)**: Implicaría múltiples instancias de `VaultClient`, potenciales condiciones de carrera en las transiciones de estado y un uso ineficiente de recursos. La autonomía es un estado **global del nodo**, no una suma de opiniones locales.

El demonio crypto dedicado **`argus-crypto-daemon`** centraliza:
- La única instancia de `VaultClient` y, por tanto, de `CryptoAutonomyStateMachine`.
- La publicación de eventos de autonomía vía ZMQ.
- El servicio de material criptográfico al resto de componentes (a través del `CryptoTransport` ya existente).

El coste de un proceso adicional es ínfimo comparado con la claridad arquitectónica, la testabilidad y la eliminación de duplicidades. El Consejo considera que esta es la opción natural y la que garantiza que el estado de autonomía sea una única fuente de verdad.

**Decisión**: Crear el componente `argus-crypto-daemon` en DAY 156, extrayendo de él la instanciación del `VaultClient`, la SM y el `AutonomyPublisher`. El resto de componentes seguirán siendo consumidores a través de ZMQ.

---

## Q2 — Endpoint del pub/sub en producción

**Veredicto: `ipc://` es correcto y suficiente para el modelo de despliegue actual.**

En la arquitectura edge desplegada en hospitales o escuelas, **todos los componentes de un nodo aRGus residen en la misma máquina física o virtual**. El `firewall-acl-agent` aplica reglas `iptables` locales, y la condición de autonomía es una propiedad de ese mismo nodo (pérdida de conectividad con Vault). Un nodo remoto no puede dictar el estado de autonomía de otro, pues cada uno tiene su propia conectividad.

Por tanto, `ipc:///run/argus/autonomy.sock` es el transporte idóneo: cero latencia de red, sin exposición externa y con los mecanismos de seguridad del sistema de ficheros (permisos 0600, AppArmor). Si en el futuro se contempla una topología de firewall centralizado, el cambio a `tcp://` podrá hacerse parametrizando el endpoint en la configuración, pero no es necesario ahora.

**Decisión**: Mantener `ipc://`. Documentar que cualquier cambio futuro requerirá una revisión del modelo de seguridad.

---

## Q3 — Reconcile interval y comportamiento del reconcilier

**Veredicto**:
1. **El intervalo debe ser configurable** desde `firewall.json["autonomy"]["reconcile_interval_sec"]`. Un hospital puede requerir una red de seguridad más rápida (30 s) o más lenta (120 s) según su perfil de riesgo. Ya que el campo existe, debe ser inyectado en el constructor del `AutonomySubscriber`.
2. **El reconcilier no debe simplemente reaplicar el último estado conocido**, sino consultar activamente la fuente de autoridad. Si la comunicación ZMQ falla durante un tiempo y luego se restaura, el último estado cacheado podría estar obsoleto (p. ej., se perdió una transición `AUTONOMOUS → NORMAL`). Para ello se recomienda uno de estos dos mecanismos (a implementar en orden de complejidad):
    - **Opción inmediata (recomendada)**: El `AutonomyPublisher` mantiene un archivo de estado firmado en `/run/argus/autonomy_state.json` (con fingerprint y nonce). El subscriber, en el ciclo de reconciliación, lee este archivo y aplica el estado si difiere. Esto ya encaja con la deuda `DEBT-AUTONOMY-STATE-PERSISTENCE-001`.
    - **Opción futura**: Un socket `REQ/REP` separado donde el subscriber pregunta explícitamente el estado al demonio crypto. Más robusto pero añade otro canal.

**Decisión para DAY 156**: Hacer configurable el intervalo y, en la persistencia del estado autónomo, habilitar la lectura de ese archivo como fuente de verdad en el reconcilier.

---

## Q4 — Separación del código enterprise

**Veredicto: Carpeta `enterprise/` en la raíz del proyecto.**

La estructura open-core exige una división nítida entre el núcleo comunitario (`common`, `sniffer`, `firewall-acl-agent`, etc.) y el código que depende de Vault y solo se compila con `ARGUS_VAULT_ENABLED`. Las opciones:

- **`enterprise/` (recomendada)**: Visible, explícita y estándar en proyectos open-core. Contendrá `enterprise/vault/` con `VaultClient`, `VaultProvider` y el futuro `argus-crypto-daemon`. El `CMakeLists.txt` raíz añade `add_subdirectory(enterprise)` condicionalmente. Esta estructura es entendida por cualquier colaborador.
- **`plugins/enterprise/`**: Sugiere que es un plugin cargable en caliente, pero hoy es código enlazado estáticamente. Puede llevar a confusión.
- **`common/enterprise/`**: Mezcla código abierto y privativo en el mismo árbol, complicando la auditoría y el licenciamiento.

No hay implicaciones técnicas complejas, pero sí de gobernanza: mantener el núcleo comunitario libre de símbolos enterprise es una promesa del proyecto. Una carpeta `enterprise/` en la raíz refuerza ese compromiso.

**Decisión**: Mover `vault_client.cpp`, `VaultProvider` y afines a `enterprise/vault/` durante la integración del demonio crypto (post-FEDER o como parte de DAY 156 si el tiempo lo permite). Anticipar en el `CMakeLists.txt` raíz la variable `ENTERPRISE_DIR` para facilitar la transición.

---

## Q5 — Benchmarks sintéticos en VirtualBox

**Veredicto: Sí, ejecútenlos ahora, con las siguientes salvaguardas.**

Esperar al hardware físico introduce un riesgo: descubrir tarde problemas metodológicos o cuellos de botella evitables que sesgarían las pruebas reales. Los benchmarks sintéticos en VirtualBox servirán para:

- Validar el *framework* de medición (métricas de latencia, throughput, pérdida de mensajes con HWM).
- Detectar regresiones tempranas en el pipeline ZMQ recién tunado.
- Obtener una **línea base de suelo** (no de techo) que permita comparar mejoras relativas cuando llegue el hardware.

**Precaución obligatoria**: Los resultados deben etiquetarse explícitamente como **«VirtualBox Synthetic Baseline — No representative of production performance»**. No deben publicarse como cifras oficiales de rendimiento del sistema. Se trata de una herramienta de desarrollo, no de un informe de capacidad.

**Decisión**: Proceder con los benchmarks sintéticos (BM-A a BM-D) en VirtualBox en cuanto el bucle de autonomía esté completo. Documentar la metodología y las limitaciones. El Consejo confía en que la comunidad entenderá la distinción si se comunica con transparencia.

---

## Resumen para el acta — DAY 156

| Ítem | Decisión |
|------|----------|
| **Dueño de la SM** | Nuevo componente `argus-crypto-daemon` (Opción B). |
| **Endpoint pub/sub** | `ipc://` definitivo para el modelo edge actual. |
| **Reconciliación** | Intervalo configurable; fuente de verdad en archivo de estado firmado. |
| **Separación enterprise** | Carpeta `enterprise/` en raíz. |
| **Benchmarks** | Ejecución sintética inmediata con etiqueta de "no representativo". |

El Consejo felicita al equipo por un DAY 155 impecable y queda a la espera del `argus-crypto-daemon` y del estado firmado en tmpfs. Que el EMECAS siga verde y la autonomía sea la nueva normalidad.