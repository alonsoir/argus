# Consejo del Consejo — DAY 160→161

He revisado el cierre de DEBT-ENTERPRISE-PLUGIN-001 y el plan para DAY 161. A continuación, mi posición sobre cada pregunta arquitectónica:

---

## Q1 — Imagen de producción: ¿.deb o Vagrant box?

**Producir ambos, pero con responsabilidades separadas:**

| Artefacto | Propósito | Prioridad FEDER |
|-----------|-----------|-----------------|
| **`.deb`** | Producción en hardware físico (RPi5, N100). Instalación limpia, gestionable con `apt`, integración con `systemd`. | **P0 — bloqueante** |
| **Vagrant box** | Validación rápida del pipeline y regresión local para desarrolladores. | P1 — acelerador |

**Recomendación concreta para DAY 161:**

1. **Pipeline Jenkins produce `.deb` como artefacto primario.** Usa `dpkg-deb` o mejor aún, `debhelper` + `dh-cmake` si ya tienes CMakeLists. Esto te obliga a resolver dependencias reales (`libsodium`, `libcurl`, `libzmq`, `libprotobuf`) en `DEBIAN/control`.
2. **Vagrant box como "test target", no como artefacto de release.** En el stage `Deploy a VM Vagrant-test`, el pipeline debería *instalar el `.deb generado`* en una VM Vagrant limpia (Bookworm), no generar una box custom. Esto valida que tu `.deb` realmente funciona en un sistema fresco.
3. **Post-FEDER:** Considera generar una OCI container image (Docker/podman) adicional para entornos cloud/k8s si aRGus escala horizontalmente.

> **Tradeoff clave:** Si generas Vagrant box como artefacto de release, estás acoplando el entorno de provision (Vagrant) con el entorno de ejecución (hardware físico). El `.deb` desacopla y es lo que realmente necesitarás en UEx.

---

## Q2 — Valores naive en JSON contrato: ¿hardcoded o generados?

**Hardcoded para DAY 161, pero con un generador *stubbed* en el repo.**

**Razonamiento:**
- Los valores óptimos (HWM, IO threads, batch size) dependen de throughput objetivo, latencia máxima aceptable, y capacidad del hardware. Calcularlos requiere benchmarking real que no tienes hasta tener UEx físico (BACKLOG-BENCHMARK-CAPACITY-001).
- Un "detector" de CPUs/RAM que genere valores "seguros" es engañoso: "seguro" para ZeroMQ en un N100 con 8GB no es lo mismo que en un RPi5 con 4GB si el workload es diferente.

**Recomendación concreta:**

```bash
# Estructura propuesta en repo
config/
├── templates/           # JSON con placeholders {{HWM}}, {{IO_THREADS}}
├── naive/
│   └── n100-default.json    # Valores hardcoded para N100 (DAY 161)
│   └── rpi5-default.json    # Valores hardcoded para RPi5
└── generated/           # Vacío en DAY 161; poblado post-benchmark
```

- **Pipeline DAY 161:** `make generate-config` copia `naive/n100-default.json` a `build/contract.json` y sustituye variables naive.
- **Post-FEDER (BACKLOG-ZMQ-TUNING-001):** Implementar `tools/tune-config.py` que lea `/proc/cpuinfo`, `/proc/meminfo`, y un modelo de capacidad (CSV/JSON) para generar config óptimo. Pero esto es P2 hasta tener datos reales.

> **Regla de oro:** No introduzcas heurísticas de auto-tuning sin datos de benchmark. Mejor hardcoded documentado que mágico y erróneo.

---

## Q3 — Token enterprise en CI/CD: ¿cómo se gestiona?

**Jenkins Credentials Store + inyección por variable de entorno en runtime. NUNCA fichero en disco de la VM.**

**Arquitectura recomendada:**

```
Jenkins Credentials (Secret text)
         │
         ▼
    env.VAULT_ENTERPRISE_TOKEN  (mascarada en logs)
         │
         ▼
    make test-enterprise-plugin
         │
         ▼
    VaultProvider (lee de env, nunca de disco)
```

**Detalles de implementación:**

1. **Jenkinsfile stage:**
   ```groovy
   withCredentials([string(credentialsId: 'vault-enterprise-token', variable: 'VAULT_ENTERPRISE_TOKEN')]) {
       sh 'make test-enterprise-plugin'
   }
   ```
2. **Código C++:** `VaultProvider` debe aceptar el token vía constructor/config, no leer `/etc/argus/enterprise.token`. En CI, el test inyecta `getenv("VAULT_ENTERPRISE_TOKEN")`.
3. **Rotación:** El token en Jenkins Credentials debe rotarse periódicamente (post-FEDER, integrar con Vault's AppRole o Kubernetes auth para CI). Por ahora, token de dev mode es aceptable.
4. **Seguridad:** `withCredentials` automáticamente enmascara la variable en logs de Jenkins. Asegúrate de que tu Makefile/test no hagan `echo $VAULT_ENTERPRISE_TOKEN`.

> **Implicación:** Fichero en disco en la VM es un vector de escape (snapshots de VM, backups, `ps aux` expone paths). Variables de entorno efímeras son más seguras en CI.

---

## Q4 — DEBT-WIRE-PROTOCOL-TEST-001 y DEBT-E2E-LIVE-DELTA-001

**Antes del pipeline CI/CD. Son cimientos, no decoración.**

**Posición:** Un pipeline que construye y empaqueta código sin wire protocol tests es un pipeline de "construcción ciega". Estás automatizando la entrega de algo que no has validado que se comunique correctamente.

**Plan recomendado:**

| Día | Enfoque |
|-----|---------|
| **DAY 161 (mañana)** | Pipeline CI/CD *con gate de calidad*. Incluye `make test-all` que ya debe contener wire protocol tests. Si DEBT-WIRE-PROTOCOL-TEST-001 no está cerrada, el pipeline falla. |
| **DAY 161+2** | Cerrar DEBT-E2E-LIVE-DELTA-001 (requiere posiblemente dos nodos Vagrant o mock). |

**Compromiso pragmático si el tiempo aprieta:**
- Pipeline DAY 161 puede tener un stage `smoke-test` mínimo (ping/pong entre dos procesos ZeroMQ) como proxy del wire protocol.
- Pero DEBT-WIRE-PROTOCOL-TEST-001 debe cerrarse antes de que el pipeline declare "SUCCESS" para FEDER. Propongo: **BACKLOG-FEDER-001 gate incluye ambas deudas P1 cerradas.**

---

## Q5 — Vault dev mode en CI/CD: ¿aceptable para gate FEDER?

**Aceptable para CI/CD (DAY 161), INACEPTABLE para gate FEDER.**

**Separación de entornos:**

| Entorno | Vault Mode | Propósito |
|---------|------------|-----------|
| **CI/CD (Jenkins)** | Dev mode (inmem) | Tests unitarios/integración del plugin. Rápido, idempotente, recreable en cada build. |
| **Staging/Pre-FEDER** | Prod mode (file storage, auto-unseal con Shamir o transit) | Validación operacional. DEBT-JENKINS-PROD-001. |
| **FEDER demo** | Prod mode + HA | Gate bloqueante. |

**Plan de transición:**

1. **DAY 161:** Vault dev mode en CI está bien. Tu `make vault-dev-start` en el Vagrantfile de dev es correcto.
2. **DAY 162-165 (DEBT-JENKINS-PROD-001):** Levantar Vault en prod mode en una VM separada (o contenedor dedicado) con:
  - File storage (`/opt/vault/data`)
  - 3 unseal keys (guardadas en Jenkins Credentials, no en repo)
  - Política `argus-enterprise` con capabilities `read` en `secret/argus/crypto`
3. **Gate FEDER:** El pipeline de release (no el de CI diario) debe apuntar al Vault de prod/staging y validar que el plugin funciona contra un Vault real.

> **No es bloqueante para DAY 161, pero sí lo es para BACKLOG-FEDER-001.** Recomiendo abrir un ticket `DEBT-VAULT-PROD-SETUP-001` con deadline 2 semanas antes de FEDER (principios de septiembre).

---

## Resumen de decisiones para DAY 161

| Pregunta | Decisión |
|----------|----------|
| **Artefacto** | `.deb` primario; Vagrant box como test target (instala el `.deb`) |
| **Config** | Hardcoded naive por hardware target; stub de generador para post-benchmark |
| **Token CI** | Jenkins Credentials Store → env var; nunca fichero en VM |
| **Wire/E2E** | Cerrar antes de declarar pipeline válido para FEDER; pueden ser DAY 161+2 |
| **Vault mode** | Dev mode OK para CI; prod mode obligatorio para gate FEDER (septiembre) |

¿Necesitas que profundice en algún punto, por ejemplo el `debian/rules` para el `.deb` o el `Jenkinsfile` con stages paralelos?