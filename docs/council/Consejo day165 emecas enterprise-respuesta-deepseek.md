**Intervención del Consejo de Sabios — DAY 165**
*Tras deliberación completa, con quórum 8/8, se emite la siguiente respuesta a cada pregunta.*

---

### Pregunta 1 — Arquitectura del protocolo

El Consejo recomienda la **opción (C)**, `targets anidados`, con los siguientes nombres y comportamiento:

- `make emecas` ≡ OSS gate (sin cambios, mantiene compatibilidad hacia atrás).
- `make emecas++` ≡ OSS gate + gate enterprise completo (test-enterprise + test-e2e-enterprise).

**Justificación:**  
La opción (A) (superset) rompe el flujo mental de quien ya confía en EMECAS OSS. La (B) (paralelos) fragmenta innecesariamente el protocolo de validación integral. Con (C) se preserva el target histórico, se introduce un nuevo target que expresa claramente “EMECAS extendido con validación empresarial”, y se minimiza la complejidad del Makefile: `emecas++` depende de `emecas` y añade las fases enterprise. Esto es intuitivo, mantenible y alineado con la nomenclatura del proyecto.

**Veredicto:** Opción (C). El cambio se implementará con `make emecas++` que llama a `emecas` y después ejecuta `test-enterprise` y `test-e2e-enterprise`.

---

### Pregunta 2 — Vault dev como gate suficiente

El Consejo considera que **Vault dev, tal como está provisionado por `vagrant up`, es suficiente para el gate de merge**, por las siguientes razones:

- El Modelo B garantiza que el keypair nunca toca disco y que Vault es el único custodio. Validar esto con Vault dev real ya cubre el camino funcional crítico.
- Un Vault dev efímero, destruido y recreado en cada ejecución de `emecas++`, asegura repetibilidad total y ausencia de estado oculto, que es la esencia de EMECAS.
- La validación de HA, TLS y reconexión tras caída pertenece al dominio de hardware y de pruebas de resiliencia, no al gate de merge diario.

El Consejo pide que se registre deuda técnica explícita:

> **DEBT‑VAULT‑HA‑001**: test de reconexión tras reinicio de Vault y test de failover con Vault HA (server/file) en entorno hardware. No bloquea el merge actual.

**Veredicto:** Vault dev es suficiente. No se requiere un segundo Vagrantfile ni tests de reconexión para mergear a `main`.

---

### Pregunta 3 — Live epoch rotation en EMECAS

El Consejo, tras sopesar el costo (~5 minutos extra) frente al riesgo de defectos de integración no detectados por `FakeEtcdServer`, opta por la **opción (B): live rotation con pipeline activo**.

**Razonamiento:**
- El `FakeEtcdServer` valida la lógica del coordinador de forma determinista y rápida, pero no comprueba la cadena completa: Vault → etcd → watch → `CryptoProviderHandle` atómico → wire header → firewall.
- Un fallo en la actualización real del `epoch_id` dentro del pipeline en ejecución sería silencioso hasta producción, y el costo de detectarlo *ahora* es solo de 5 minutos adicionales.
- EMECAS debe garantizar que *todo* el camino feliz funciona con componentes reales. La rotación en vivo es el cierre perfecto de las Fases 0‑4.

Para no sobrecargar el flujo diario, se sugiere que `make emecas++` incluya esta verificación, pero que exista un target rápido opcional (`make test-e2e-rotation-live`) para el día a día del desarrollador, que en CI siempre se ejecute completo.

**Veredicto:** Live rotation entra en el gate (`emecas++`). Se acepta el coste temporal.

---

### Pregunta 4 — Test negativo (epoch_id incorrecto)

El Consejo juzga que este test es **importante pero no un bloqueante de merge**.  
Un mensaje con `epoch_id` erróneo es un escenario de defensa ante adversario o corrupción, no un camino feliz de integración. Las Fases 0‑4 han demostrado que el camino nominal es sólido. El test negativo puede añadirse sin riesgo de regresión en el código ya validado.

Se registra la deuda:

> **DEBT‑CRYPTO‑NEGATIVE‑TEST‑001**: test de rechazo de `epoch_id` inválido, con métrica `crypto_errors`. Prioridad P2, no bloquea merge.

**Veredicto:** Diferir como deuda técnica. El gate actual no lo exige.

---

### Pregunta 5 — Gate de Jenkins

El Consejo **acepta el merge con gate manual**, bajo las siguientes condiciones:

- El procedimiento manual (`make emecas++`) esté documentado en `docs/EMECAS++.md` y en el mensaje de merge request.
- Se cree el backlog con prioridad explícita:

> **BACKLOG‑CI‑ENTERPRISE‑001**: automatizar `emecas++` en Jenkins (P1). Debe ejecutarse en cada push a `main` y en PRs hacia `main`.

El razonamiento es que la integridad del gate no depende de la automatización, sino de la existencia del protocolo. Mientras el protocolo esté definido y se ejecute manualmente antes del merge, el riesgo está controlado. Jenkins es una optimización del flujo, no un habilitador de seguridad.

**Veredicto:** Merge manual aceptado. Jenkins es P1 post‑merge, no prerequisito.

---

### Pregunta 6 — Naming y documentación

El Consejo recomienda oficializar el nombre **EMECAS++**, opción (B), por las siguientes razones:

- Ya tiene arraigo informal en el equipo, en el código y en las discusiones del Consejo.
- “EMECAS” queda como el protocolo OSS original, y “EMECAS++” denota claramente la extensión empresarial, sin ambigüedad.
- La opción (A) (EMECAS‑E) es correcta pero más fría; la opción (C) (TDH‑Gate) diluye la trazabilidad con el artículo arXiv y la comunidad.

Para el paper y la comunidad, se documentará:

> **EMECAS** – Entorno Mínimo Ejecutable y Comparable de Arranque y Seguridad (modo Community).  
> **EMECAS++** – Extensión Enterprise de EMECAS, que valida adicionalmente VaultProvider, rotación de épocas y pipeline empresarial completo.

Esto preserva la identidad del proyecto y facilita la comunicación con usuarios externos.

**Veredicto:** Nombre oficial **EMECAS++**. README y arXiv se actualizarán en consecuencia.

---

*Resolución final: el Consejo aprueba la propuesta de EMECAS++ con los ajustes indicados (target anidado, live rotation incluida, deuda registrada). El árbitro Alonso tiene la decisión última. Queda acta levantada.*