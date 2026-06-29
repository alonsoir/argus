```
═══════════════════════════════════════════════════════════
CONSEJO DE SABIOS — RESPUESTA CLAUDE
DAY 156 · aRGus NDR · arXiv:2604.04952
═══════════════════════════════════════════════════════════

## VALORACIÓN DAY 156

La integración del plano de autonomía es arquitectónicamente correcta.
El patrón Publisher-bind-first resuelve el slow joiner de forma definitiva
y debe convertirse en regla de estilo del proyecto: cualquier par PUB/SUB
en aRGus debe seguir este orden sin excepción.

El uso de `etcd_client` como proxy de Vault en poll_callback es honesto —
está documentado como deuda, no enmascarado como feature. Eso es Via Appia.

---

## RESPUESTAS A LAS PREGUNTAS

### Q1 — State persistence: tmpfs vs etcd vs fichero regular

**Voto: tmpfs con firma Ed25519, con matiz.**

Razonamiento: en infraestructura hospitalaria, un reboot no planificado
durante AUTONOMOUS ocurre precisamente porque hay un incidente grave.
En ese momento, el sistema debe arrancar en AUTONOMOUS por defecto si
no puede verificar Vault — no en NORMAL.

Propuesta concreta:

```
Al arrancar etcd-server:
1. Leer /run/argus/crypto-autonomy-state.json (si existe)
2. Verificar firma Ed25519
3. Si estado=AUTONOMOUS y timestamp < 30 días → arrancar en AUTONOMOUS
4. Si no existe o firma inválida → arrancar en NORMAL (comportamiento actual)
```

tmpfs desaparece en reboot — esto es una ventaja, no un problema. Si el
fichero no existe, el sistema arranca en NORMAL e inmediatamente intenta
contactar Vault. Si Vault sigue caído, la SM transiciona a AUTONOMOUS en
los primeros 5 segundos (primer health-check). El gap de exposición es
mínimo y aceptable para MVP FEDER.

`/var/lib/argus/` solo si se implementa EXTENDED_AUTONOMY (>30 días)
en DEBT-CRYPTO-AUTONOMY-001. Para P1 DAY 157: tmpfs es suficiente.

### Q2 — poll_callback como proxy de Vault

**Voto: mantener el placeholder para MVP FEDER. No es sobreingeniería
evitarlo — es priorización correcta.**

El canal ZMQ correcto para el estado de salud ya existe: es el mismo
`ipc:///run/argus/autonomy.sock` que publica etcd-server. El firewall
ya tiene un SUB conectado a ese socket. El poll_callback reconciliador
debería leer el último estado conocido de esa misma suscripción, no
abrir un segundo canal.

Arquitectura correcta (post-FEDER):

```
AutonomySubscriber::run() → actualiza atomic<FirewallAutonomyMode> last_known_mode_
poll_callback → retorna last_known_mode_.load()
```

Esto elimina DEBT-CRYPTO-RECONCILIATION-001 sin añadir ningún canal nuevo.
Para DAY 157: registrar esta arquitectura en el ADR y dejar el placeholder.

### Q3 — Suricata: Eve JSON via file watcher

**Voto: Eve JSON via file watcher, exactamente como los CSVs actuales.**

Razones:

1. El file watcher de rag-ingester ya existe, está testeado (8/8) y
   maneja inotify IN_MODIFY + offset para append-only. Eve JSON es
   append-only por definición.

2. ZMQ directo desde Suricata requeriría modificar Suricata (compilar
   con output plugin) o usar un relay. Innecesario para MVP.

3. El formato Eve JSON es estable y bien documentado. Un parser
   `SuricataEveLoader` análogo a `FirewallCsvEventLoader` se implementa
   en una sesión.

4. La correlación con aRGus por `community_id` (DEBT-ARGUSPP-JOIN-ROBUSTNESS-001)
   funciona igual independientemente del transporte.

Ruta de implementación mínima:
```
/var/log/suricata/eve.json → inotify → SuricataEveLoader →
→ extraer alert.community_id, alert.signature, flow → correlación
```

AppArmor para Suricata debe estar en el alcance de DEBT-ARGUSPP-SENSOR-HARDENING-001
antes de cualquier despliegue. Suricata ha tenido RCEs históricos.

### Q4 — ZMQ slow joiner: ADR o nota técnica

**Voto: nota técnica en CONTRIBUTING.md o docs/technical-notes/, NO un ADR.**

Un ADR documenta una decisión de arquitectura con alternativas consideradas
y consecuencias. El slow joiner de ZMQ no es una decisión — es un
comportamiento documentado de la librería que tiene una solución canónica
(publisher bind primero).

Formato correcto:

```markdown
# docs/technical-notes/ZMQ-PUB-SUB-SLOW-JOINER.md

## Problema
En ZMQ PUB/SUB, si el subscriber conecta antes de que el publisher
haga bind, los primeros mensajes publicados se pierden silenciosamente.

## Regla en aRGus
SIEMPRE: publisher hace bind() ANTES de que cualquier subscriber conecte.
En tests: crear el publisher en SetUp() del fixture, antes de start_subscriber().

## Referencia
Descubierto en DAY 156, tests test_autonomy_integration y test_autonomy_e2e.
```

### Q5 — Keypair regeneration en EMECAS vs producción FEDER

**Voto: separar el ciclo de vida del keypair del ciclo de vida de la VM.**

El problema actual: `vagrant destroy` destruye el keypair. Esto es
correcto para aislamiento de desarrollo pero catastrófico en producción.

Propuesta para despliegue FEDER en CPD UEx:

```
Desarrollo (Vagrant):
  - Keypair generado en provision.sh (comportamiento actual)
  - Destruido en vagrant destroy (correcto)

Producción (CPD UEx):
  - Keypair generado UNA SOLA VEZ en bootstrap inicial
  - Almacenado en /etc/ml-defender/ con permisos 0600
  - NUNCA regenerado automáticamente
  - Rotación manual con protocolo documentado (futuro ADR)
  - Backup cifrado fuera del servidor (pendiente definir)
```

Para FEDER: el provisioning script debe detectar si está en entorno
de producción (variable de entorno o fichero sentinel) y OMITIR la
generación de keypair si ya existe uno válido.

DEBT nueva propuesta: DEBT-KEYPAIR-LIFECYCLE-PROD-001

---

## VALORACIÓN ADR-046 — Multi-Source Enriched Pipeline aRGus++

El ADR-046 tiene una visión correcta pero necesita cerrar tres puntos
antes de poder marcarse como ACCEPTED:

**Punto 1 — §8 datos empíricos (DEBT-PAPER-SYNTHETIC-001, P0)**

La sección de benchmarks de rendimiento con 4 fuentes simultáneas no
puede publicarse como resultado empírico si los datos son proyecciones.
El Consejo fue unánime en esto. Dos opciones:

a) Reformular como hipótesis: "Estimamos que la sobrecarga de correlación
con community_id será < X% basándonos en Y"
b) Ejecutar el experimento antes de arXiv v24

Para FEDER: la opción (a) es aceptable en el prospecto si se formula
como "hipótesis a verificar en el Año 1". Para arXiv: debe ser (b).

**Punto 2 — Label leakage (no resuelto en el ADR)**

El ADR establece que Suricata etiqueta tráfico y aRGus usa esas etiquetas
como features para el modelo XGBoost. Esto crea contaminación de etiquetas:
el modelo aprende a detectar lo que Suricata ya detectó, no amenazas nuevas.

Propuesta arquitectónica para el ADR:

```
Pipeline de entrenamiento:
  Features: solo aRGus (flujos de red, estadísticas temporales)
  Labels: Suricata (etiquetado automático)
  NUNCA mezclar: features de Suricata no entran en el vector de entrada

Pipeline de inferencia:
  aRGus detecta → Suricata corrobora (o no)
  Si Suricata corrobora: alta confianza
  Si aRGus detecta y Suricata no: falso positivo candidato → RAG
  Si Suricata detecta y aRGus no: gap de cobertura → reentrenamiento
```

Este diseño convierte la correlación en un mecanismo de validación cruzada
y evita el leakage. El ADR-046 debería incluir este diagrama explícitamente.

**Punto 3 — RPi5 fuera de aRGus++ (Kimi tenía razón)**

Suricata con 50K reglas ET requiere ~1GB RAM. RPi5 tiene 8GB pero comparte
con el sniffer eBPF, el ml-detector y el firewall. El headroom es insuficiente
para operación clínica sostenida.

Propuesta para el ADR: declarar explícitamente que aRGus++ (con Suricata)
solo se despliega en el edge server (miniPC x86 ≥16GB) o en el servidor
central. La RPi5 ejecuta aRGus Variant B (libpcap, sin Suricata) y envía
flujos al servidor para correlación centralizada.

Esto resuelve también la preocupación ética de Alonso: la RPi5 en el
hospital sigue protegiendo — solo que la correlación avanzada ocurre
en el servidor, no en el edge.

**Condición para cerrar ADR-046:**

El ADR puede marcarse como ACCEPTED-WITH-CONDITIONS si incluye:
1. §Label leakage policy (texto nuevo)
2. §Deployment matrix actualizado (RPi5 = aRGus-only, edge server = aRGus++)
3. §8 reformulado como hipótesis o con datos reales

---

## VEREDICTO GLOBAL DAY 156

DAY 156 es una de las sesiones más sólidas del proyecto. El plano de
autonomía funciona, los tests lo demuestran, y el EMECAS en VM limpia
valida que el código vive en disco, no en memoria.

La deuda técnica está bien identificada y priorizada. La arquitectura
de persistencia de estado (Q1) y el diseño correcto del poll_callback
(Q2) son las dos decisiones más importantes para DAY 157.

ADR-046 está cerca — necesita los tres puntos anteriores para cerrarse
con integridad científica.

Via Appia.

— Claude (Consejo de Sabios, voto #1 de 8)
═══════════════════════════════════════════════════════════
```