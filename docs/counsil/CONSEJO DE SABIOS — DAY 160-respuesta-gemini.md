Menudo sprint el del DAY 160. Domar la rotación de claves de Jenkins, la migración forzada a Java 21 y el dolor de cabeza de la visibilidad de símbolos (-fvisibility=hidden vs. el ABI de C) en una sola jornada es ingeniería de trinchera de la buena. Esos 6 tests de RED a GREEN dejan el terreno perfectamente abonado.

Aquí tenéis la perspectiva del Consejo para abordar el **DAY 161** con las ideas claras y sin perder el foco del objetivo FEDER.

---

## Q1 — Imagen de producción: ¿.deb o Vagrant box?

**Dictamen: El .deb es el entregable real; Vagrant es solo tu laboratorio.**

Apuntando a hardware físico real como Raspberry Pi 5 (ARM64) e Intel N100 (x86_64), **el .deb es el rey absoluto**. Introducir una Vagrant box en producción añade una capa de virtualización totalmente innecesaria, ineficiente para el rendimiento de un NDR (Network Detection and Response) y compleja de gestionar en arquitecturas mixtas como ARM64.

* **Estrategia para el pipeline:** El pipeline de Jenkins debe compilar y empaquetar un archivo .deb nativo para la arquitectura destino.
* **El rol de Vagrant:** Utilizad Vagrant únicamente al final del pipeline como un entorno de *smoke test* efímero. Levantar una box limpia de Debian, instalar el .deb recién generado, y verificar que el servicio arranca.

---

## Q2 — Valores naive en JSON contrato: ¿hardcoded o generados?

**Dictamen: Hardcoded para el DAY 161. No caigáis en la parálisis por análisis.**

El objetivo de mañana es que el pipeline funcione de extremo a extremo (*green pipeline*). Meter lógica de autodetección de hardware y cálculo dinámico de hilos de ZeroMQ e IO en este punto añadirá ruido y posibles falsos negativos al flujo de CI/CD.

* Mantened los valores naive hardcodeados en un archivo de configuración por defecto (ej. config.json.template).
* Dejad la optimización real blindada en el backlog bajo las tareas BACKLOG-ZMQ-TUNING-001 y BACKLOG-BENCHMARK-CAPACITY-001 para cuando tengáis el hierro de la UEx sobre la mesa.

---

## Q3 — Token enterprise en CI/CD: ¿cómo se gestiona?

**Dictamen: Jenkins Credentials Store inyectado al vuelo en memoria.**

Dejar ficheros con tokens estáticos en el disco de la máquina virtual es una vulnerabilidad crítica y rompe la inmutabilidad de la infraestructura de integración continua.

La solución limpia y segura para mañana:

1. Guardad el enterprise.token en el **Jenkins Credentials Store** como un elemento de tipo *Secret Text*.
2. En el Jenkinsfile, haced referencia a esa credencial y pasadla como variable de entorno efímera solo durante la fase de testing. El plugin de Vault la leerá del entorno y nunca se escribirá en disco.

```groovy
stage('Enterprise Plugin Tests') {
    steps {
        withCredentials([string(credentialsId: 'vault-enterprise-token', variable: 'VAULT_TOKEN')]) {
            sh 'make test-enterprise-plugin'
        }
    }
}

```

---

## Q4 — Deudas técnicas de protocolo de red: ¿antes o después?

**Dictamen: Paralelo o inmediatamente después, pero no lo ignoréis.**

Construir un pipeline de despliegue automatizado sin testear el protocolo de red (DEBT-WIRE-PROTOCOL-TEST-001) es, efectivamente, empaquetar una casa sin cimientos. Sin embargo, bloquear el pipeline por esto mañana puede romper el ritmo del equipo.

* **Compromiso para el DAY 161:** Añadid las etapas correspondientes a estos tests en el Jenkinsfile de mañana, aunque inicialmente ejecuten un esqueleto básico o un *stub*.
* En cuanto el flujo dev→prod esté verde, la prioridad absoluta P1 debe ser rellenar esos tests antes de avanzar hacia cualquier lógica de autonomía criptográfica.

---

## Q5 — Vault dev mode en CI/CD: ¿aceptable para el gate FEDER?

**Dictamen: Sí para CI/CD, No para la demo final.**

Es una práctica estándar de la industria que los entornos de CI/CD utilicen instancias efímeras e inseguras (como el modo dev in-memory de Vault) porque se destruyen en cada ejecución y garantizan aislamiento total entre builds. No bloquea para nada el hito del pipeline de mañana.

Sin embargo, para el hito final de la demo con el hardware de la UEx, necesitaréis un Vault productivo persistente o delegar en la máquina de estados de DEBT-CRYPTO-AUTONOMY-001.

---

## Estado del Tablero de Deudas (Recomendación del Consejo)

Sugerimos priorizar el cierre del core del pipeline mañana y reordenar las P1 críticas justo después:

| DEBT / BACKLOG | Prioridad | Acción DAY 161 |
| --- | --- | --- |
| **Generación de .deb + Jenkinsfile** | **P0** | **Enfoque principal de mañana** |
| DEBT-WIRE-PROTOCOL-TEST-001 | P1 | Añadir esqueleto en pipeline |
| DEBT-E2E-LIVE-DELTA-001 | P1 | Bloqueante post-pipeline |
| DEBT-JENKINS-PROD-001 | P1 | Esperar a hardware físico UEx |