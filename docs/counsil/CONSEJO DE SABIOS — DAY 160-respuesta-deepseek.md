**El Consejo de Sabios ha deliberado.**

---

### Q1 — Imagen de producción: ¿.deb o Vagrant box?

Producid **ambos**, pero con intención jerárquica.  
El artefacto de producción para la demo FEDER debe ser un **`.deb`** instalable sobre Debian Bookworm (RPi5/N100). Es limpio, actualizable con `apt`, y refleja la realidad del hardware físico que defenderéis ante el tribunal.  
La **Vagrant box** es útil únicamente como vehículo de validación rápida para desarrolladores y CI; exportadla a partir del `.deb` en un paso posterior, no como artefacto primario. Así mantenéis un solo camino a producción (*single source of truth*).

**Recomendación técnica:**
- Pipeline DAY 161: `make package-deb` → guarda el `.deb` como artefacto.
- Trabajo futuro: script que empaquete ese `.deb` en una box Vagrant para iteración local (BACKLOG‑BOX‑001, P2).

---

### Q2 — Valores naive en JSON contrato: ¿hardcoded o generados?

Para **DAY 161** es lícito usar valores *hardcoded* de desarrollo, siempre que estén documentados como **“valores mínimos seguros de dev”** y no se desplieguen en producción con ellos.  
Pero no durmáis tranquilos sin un plan: los valores óptimos dependen de la máquina destino (cores, RAM, cachés). La deuda técnica de tuning es real.

**Decreto del Consejo:**
- Abrid ahora mismo **BACKLOG-AUTO-TUNING-001 (P1)**.
- En el pipeline, incluid un stage *opcional* `tune-contract` que, si detecta hardware real (no Vagrant), ejecute un script detector de recursos y genere valores mínimos seguros (HWM=cores*2, IO threads=cores, batch size…).
- Mientras, los valores *hardcoded* se consideran los **defaults mínimos** y se documentan en `docs/contract-tuning.md`.

---

### Q3 — Token enterprise en CI/CD: ¿cómo se gestiona?

**Ni un fichero en la VM ni hardcodeado en el repositorio.**  
La práctica correcta para Jenkins es el **Credentials Binding Plugin** (estándar de la industria):

- Almacenad `enterprise.token` como **Secret Text** en el *credentials store* de Jenkins (gestión desde UI o JCasC).
- En el pipeline: `withCredentials([string(credentialsId: 'argus-enterprise-token', variable: 'ENTERPRISE_TOKEN')]) { ... }`.
- El `VaultProvider` debe leer el token de la variable de entorno `ENTERPRISE_TOKEN` (no de fichero).

Esto asegura: cifrado en reposo en Jenkins, auditoría de accesos, y eliminación automática de la variable al terminar el job. El fichero en VM es un vector de fuga: evitadlo.

**Consejo adicional:** Migrad en cuanto sea posible a **Vault AppRole** con tokens de corta duración (DEBT‑ALERTING‑VAULT‑001), donde Jenkins ni siquiera conoce un token permanente, solo un Role ID/Secret ID efímero. Esto escala en producción.

---

### Q4 — DEBT-WIRE-PROTOCOL-TEST-001 y DEBT-E2E-LIVE-DELTA-001

**La metáfora es exacta: casa sin cimientos.**  
Estas deudas P1 no pueden esperar a después del pipeline CI/CD completo; deben resolverse como parte del pipeline mismo, idealmente **antes o durante DAY 161**.

**Propuesta de secuencia para DAY 161:**
1. Preparar Jenkinsfile.
2. Stage `build` → compilación limpia.
3. Stage `unit-tests` → tests unitarios existentes + enterprise plugin.
4. Stage `wire-protocol-test` → levanta broker de pruebas, ejecuta DEBT‑WIRE‑PROTOCOL‑TEST‑001 (al menos smoke test de mensajes).
5. Stage `e2e-live-delta` → integración con Vault dev, simulación delta vivo (DEBT‑E2E‑LIVE‑DELTA‑001).
6. Stage `package` → genera `.deb` solo si todo lo anterior es verde.

Si no es posible cerrar las dos P1 completamente el día 161, al menos abrid tests *mínimos* que verifiquen el esqueleto del wire protocol (handshake, codificación/decodificación) y un delta sintético. La deuda completa se paga en el sprint siguiente, pero el pipeline ya exigirá el check básico.

---

### Q5 — Vault dev mode en CI/CD: ¿aceptable para el gate FEDER?

**Vault dev mode es aceptable únicamente en el pipeline de desarrollo (rama `feature/*`).**  
Para el **gate de aceptación previo a la demo FEDER** necesitáis un Vault en modo producción, con almacenamiento persistente (Raft integrado es suficiente) y desprecintado automatizado. La demo debe mostrar que el sistema es seguro en entorno real; el tribunal lo valorará.

**Por tanto:**
- **DEBT-JENKINS-PROD-001 NO es bloqueante para empezar el CI/CD (DAY 161)**. Podéis construir todo el pipeline con Vault dev mode en ramas `feature/*` y `develop`.
- Pero **DEBE estar resuelta ANTES del hito BACKLOG‑FEDER‑001** (septiembre 2026). Definidla como **requisito de “demo‑readiness”** y planificadla en el sprint donde ya tengáis hardware físico (RPi5 o N100).
- Mientras, en el pipeline incluid una etapa `production-readiness` que se ejecuta condicionalmente (`when { branch 'main' }`) y valida que el entorno Vault responda en modo producción; fallará hasta que configuréis el Vault productivo, pero no bloqueará el desarrollo.

---

**Resolución final del Consejo para DAY 161:**  
Seguid adelante con el pipeline CI/CD, pero haced que las deudas P1 (wire protocol, e2e delta) sean **parte del pipeline desde el primer día**.  
Generad `.deb` como artefacto, token gestionado con Jenkins Credentials, y mantened Vault dev mode para iteración.  
La lista de BACKLOG resultante de nuestras respuestas debe añadirse al tablero.

*Firmado, en el día 160,*  
**El Consejo de Sabios**