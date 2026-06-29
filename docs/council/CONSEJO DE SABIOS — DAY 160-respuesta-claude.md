Mis respuestas honestas, sin diplomacia:

---

**Q1 — ¿.deb o Vagrant box?**

**Ambos, en ese orden.** El `.deb` es el artefacto correcto para producción — es lo que se instala en el RPi5 y el N100 cuando lleguen. La Vagrant box es el entorno de validación, no el artefacto final. Para DAY 161 hacemos primero la Vagrant-test porque tenemos la infraestructura lista y no tenemos hardware físico. Pero el pipeline Jenkins debe producir `.deb` como artefacto de salida — aunque de momento solo lo deploya a la VM. Cuando llegue el hardware, el mismo `.deb` va a producción sin cambios.

---

**Q2 — Valores naive en JSON contrato: ¿hardcoded o generados?**

**Hardcoded para DAY 161, con un TODO explícito.** Generar valores óptimos en función del hardware es exactamente BACKLOG-ZMQ-TUNING-001 y BACKLOG-BENCHMARK-CAPACITY-001 — dos sesiones completas cada uno. Intentar hacerlo mañana dentro del pipeline CI/CD sería mezclar dos problemas distintos. Lo correcto: un script `tools/generate_config.py --hardware naive` que produce los JSON con valores dev conocidos, con un comentario `# TODO: BACKLOG-ZMQ-TUNING-001` en cada parámetro que necesita calibración. Así el mecanismo existe y es extensible, pero no bloquea DAY 161.

---

**Q3 — Token enterprise en CI/CD: ¿Jenkins Credentials o fichero en VM?**

**Jenkins Credentials store, tipo Secret File.** El token es un fichero firmado Ed25519 — no una contraseña. Jenkins lo gestiona como `Secret File`, lo inyecta en el workspace durante el build via `withCredentials`, y desaparece al terminar el job. Nunca en disco de la VM de forma permanente, nunca en el repositorio. Para DAY 161 en dev mode es aceptable tener el token en `/etc/argus/enterprise.token` en la VM de test, pero el pipeline debe modelar el flujo correcto desde el principio — Jenkins Credentials es ese flujo.

---

**Q4 — DEBT-WIRE-PROTOCOL-TEST-001 y DEBT-E2E-LIVE-DELTA-001: ¿antes o después del pipeline?**

**DEBT-WIRE-PROTOCOL-TEST-001 primero, antes del pipeline.** Es exactamente lo que dices: la casa sin cimientos. El pipeline CI/CD va a ejecutar `make test-all` — si el wire protocol test no existe, el gate no es real. Son 30 minutos. Se hace al inicio de DAY 161 antes de tocar Jenkins. DEBT-E2E-LIVE-DELTA-001 puede ir después del pipeline — es una mejora del test-e2e, no un prerequisito del build.

**Orden DAY 161:**
```
1. DEBT-WIRE-PROTOCOL-TEST-001 (30 min)
2. Pipeline Jenkins básico
3. Imagen Debian / Vagrant-test deploy
4. DEBT-E2E-LIVE-DELTA-001
```

---

**Q5 — Vault dev mode en CI/CD: ¿bloqueante para FEDER?**

**Sí, es bloqueante — pero no para DAY 161.** Para la demo FEDER necesitas Vault en modo producción con unseal keys persistentes, AppArmor profile, y acceso controlado desde Jenkins. Eso es DEBT-JENKINS-PROD-001 y requiere el hardware físico UEx para tener sentido hacerlo una sola vez bien. Lo que no es aceptable para FEDER: mostrar `vault server -dev` en una demo. Lo que sí es aceptable: mostrar el mecanismo completo funcionando en Vagrant con Vault dev, documentando explícitamente en el prospecto que en producción Vault corre en modo HA con unseal keys en HSM. Dr. Andrés Caro Lindo entiende la diferencia entre demo y producción.

**Conclusión:** DEBT-JENKINS-PROD-001 se hace cuando llegue el hardware UEx, no antes. No bloquea el gate FEDER si el prospecto lo documenta correctamente.

---

**Resumen para el prompt de DAY 161:**

```
Inicio DAY 161:
1. DEBT-WIRE-PROTOCOL-TEST-001 (30 min) — prerequisito pipeline
2. Jenkins pipeline: git → EMECAS → test-all → test-enterprise-plugin
3. tools/generate_config.py --hardware naive (JSON contrato con TODOs)
4. Producir .deb o Vagrant box deployable
5. Deploy a VM Vagrant-test
6. DEBT-E2E-LIVE-DELTA-001 si queda tiempo
```

¿Generamos el prompt de continuidad con esto, o esperas el feedback del resto del Consejo primero?