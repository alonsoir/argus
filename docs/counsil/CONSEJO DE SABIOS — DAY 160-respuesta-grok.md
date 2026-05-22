**Consejo de Sabios — Respuesta DAY 161**

Excelente avance en **DEBT-ENTERPRISE-PLUGIN-001**. Tener una interfaz C++20 pura, ABI C limpia y tests sólidos con `libvault_provider.so` es una base muy profesional. El setup de Jenkins + Vault dev en Vagrant ya da reproducibilidad. Vamos a las preguntas.

### Q1 — Imagen de producción: ¿.deb o Vagrant box?

**Recomendación: Ambos, con prioridad en `.deb`.**

- **.deb (prioridad alta para FEDER)**: Es la opción más limpia para hardware físico (RPi5, N100, etc.). Permite instalación nativa (`apt`), actualizaciones, dependencias declarativas y control de versiones. Ideal para producción y demo en hardware real. Usa herramientas como `dpkg-buildpackage`, `dh_make`, o integra con **CMake** + **CPack** (genera DEB directamente). Jenkins tiene plugins como **Debian Package Builder** y **pbuilder** para builds reproducibles en entornos limpios.

- **Vagrant box**: Excelente para validación rápida y entornos de test (VM). Exporta una caja con todo provisionado y permite `vagrant up` en minutos. Úsala como "golden image" para CI y pre-producción. No la uses como artefacto final de producción en hardware embebido.

**Plan DAY 161**:
1. Pipeline que produzca **ambos**.
2. `.deb` como artefacto principal (Jenkins archiveArtifacts + nexus/artifactory si escalas).
3. Vagrant box como artefacto secundario para pruebas locales.

### Q2 — Valores naive en JSON contrato: ¿hardcoded o generados?

**Mejor opción: Script de auto-tuning ligero (generado en build time).**

Hardcoded naive es aceptable para DAY 161 y demo inicial (rápido). Pero para robustez:

- Crea un script (Python/Bash/C++) que detecte hardware (`nproc`, `free -h`, `/proc/cpuinfo`, model de CPU) y aplique reglas conservadoras:
  - HWM, batch size, IO threads, timeouts basados en núcleos + RAM disponible.
  - Valores mínimos seguros + factor de escala (ej. 70-80% de recursos para dejar margen al sistema).
  - Fallback a valores naive si detección falla.

Esto se ejecuta durante la generación del JSON en el pipeline (o en post-instalación del .deb via maintainer script). Evita recompilaciones y prepara el terreno para **BACKLOG-ZMQ-TUNING-001** y benchmarks posteriores.

### Q3 — Token enterprise en CI/CD: ¿cómo se gestiona?

**Mejor práctica: Usa el HashiCorp Vault Plugin de Jenkins + AppRole (o JWT si aplica). No tokens estáticos largos.**

- **No** guardes un token enterprise largo en Jenkins Credentials como secreto plano (riesgo alto si Jenkins se compromete).
- **Recomendado**:
  - Configura **AppRole** auth en Vault para Jenkins (role-id + secret-id).
  - Almacena role-id y secret-id (o wrapped token) en **Jenkins Credentials**.
  - En el Pipeline usa `withVault` (o el plugin equivalente) para obtener secretos de forma efímera. El plugin enmascara valores en logs.
  - Para el plugin `libvault_provider.so`: inyecta el token corto como variable de entorno o fichero efímero solo durante la etapa de build/test que lo necesita (`withCredentials` + `withVault`).

- Alternativa segura: **Vault Agent** en el agente Jenkins (sidecar) que renderiza los secretos en archivos o env vars con TTL corto.

Seguridad: Least privilege (policy restringida al path `secret/argus/crypto`), rotación automática, audit logging en Vault. Fichero en VM solo si es efímero y con permisos estrictos (`600`, borrado post-uso).

### Q4 — DEBT-WIRE-PROTOCOL-TEST-001 y DEBT-E2E-LIVE-DELTA-001

**Hazlos antes del pipeline completo (o en paralelo en DAY 161).**

Un pipeline sin tests de wire protocol y E2E live-delta es "casa sin cimientos", como dices. Priorízalos como **P1 bloqueante** para el gate CI/CD. Inclúyelos en `make test-all` para que el pipeline falle rápido si hay regresiones en comunicación.

El enterprise plugin ya está verde → úsalo en estos tests.

### Q5 — Vault dev mode en CI/CD: ¿aceptable para el gate FEDER?

**Aceptable solo para CI dev y early validation (DAY 161). No para gate FEDER final.**

- Dev mode (inmem) es perfecto para tests rápidos y reproducibles en Vagrant/Jenkins.
- Para **BACKLOG-FEDER-001** y hardware real: pasa a **standalone/production mode** con almacenamiento persistente (file o Consul), TLS, unseal (incluso shamir con keys en Jenkins Credentials de forma segura o mejor con approle + auto-unseal si usas cloud).

**DEBT-JENKINS-PROD-001** no es 100% bloqueante para el primer demo si usas dev-mode en pipeline + Vault prod solo en el hardware destino. Pero planifícalo pronto (post-hardware UEx).

### Recomendaciones generales para el Pipeline DAY 161

```groovy
// Jenkinsfile sketch
pipeline {
    agent any
    stages {
        stage('Bootstrap & Test') {
            steps {
                sh 'make bootstrap && make test-all'
                // Inyectar Vault via plugin
                withVault(...) {
                    sh 'make test-enterprise-plugin'
                }
            }
        }
        stage('Build Artifacts') {
            steps {
                // CMake + CPack para .deb
                // Generar JSON con auto-tuning
                sh 'make package-deb'
                sh 'make package-vagrant' // opcional
            }
        }
        stage('Deploy Test') {
            steps {
                sh 'vagrant up --provision' // o deploy a VM test
            }
        }
    }
    post {
        success { archiveArtifacts artifacts: '*.deb, *.box' }
    }
}
```

**Próximos pasos sugeridos**:
- Instala **HashiCorp Vault Plugin** en Jenkins.
- Configura AppRole.
- Integra `make` targets con el pipeline.
- Documenta todo en ADR.

¡El proyecto avanza con muy buena disciplina! Si necesitas snippets concretos de Pipeline, CMake/CPack para .deb, o script de auto-tuning, pedidlos.

**Fuerza al Consejo.**