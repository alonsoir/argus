## Deliberación del Consejo de Sabios — Día 165

He revisado la propuesta de EMECAS++ Enterprise. A continuación mis respuestas estructuradas a las seis preguntas, con justificación técnica y de arquitectura.

---

### Pregunta 1 — Arquitectura del protocolo: **Opción (C) Targets anidados**

**Voto: `make emecas` = OSS, `make emecas++` = OSS + enterprise.**

**Justificación:**
- **No breaking changes:** `make emecas` sigue funcionando exactamente igual para la comunidad OSS. No rompemos el contrato social con contribuidores externos.
- **Intuitivo:** `++` comunica naturalmente "versión extendida" sin inventar nuevas siglas.
- **Composición limpia:** `emecas++` puede depender internamente de `emecas` como prerequisito, evitando duplicación en el Makefile.
- **Escalable:** Si en el futuro hay un modo "Enterprise HA" o "Federated", la notación `emecas+++` o `emecas-ha` mantiene coherencia.

**Makefile sugerido:**
```makefile
emecas: bootstrap test-all test-e2e-synthetic
emecas++: emecas test-enterprise test-e2e-enterprise
```

---

### Pregunta 2 — Vault dev como gate: **Suficiente, con una condición**

**Voto: Vault dev es gate aceptable para merge, pero se requiere un test de reconexión explícito.**

**Justificación:**
- El objetivo de EMECAS es validar la **lógica de integración**, no la resiliencia de infraestructura. Vault dev cubre 100% de la superficie funcional que necesitamos gatear.
- **Condición sine qua non:** Añadir `test_vault_reconnect` — un test que simule caída de Vault (kill del proceso) y verifique que el pipeline:
    1. Entra en modo degradado (`VaultProvider` mantiene última clave en caché RCU)
    2. Reconecta automáticamente cuando Vault vuelve
    3. No pierde eventos durante la ventana de reconexión

Este test no requiere Vault HA; basta con un script que haga `pkill vault` y `vault server -dev` en el Vagrantfile. Es ~2 minutos adicionales y elimina el riesgo de que un bug de manejo de conexión pase inadvertido.

**No se requiere:** segundo Vagrantfile ni Vault server/file para el gate de merge. Eso es validación de infraestructura, no de código.

---

### Pregunta 3 — Live epoch rotation: **Opción (B) Live rotation con pipeline activo**

**Voto: Incluir live rotation en `test-e2e-enterprise`.**

**Justificación:**
- `FakeEtcdServer` valida la lógica unitaria del coordinador, pero no la **orquestación real** entre: etcd watch → callback en thread del coordinator → RCU swap en CryptoProviderHandle → actualización de wire header en thread del sniffer → firewall con nueva clave.
- La rotación de claves criptográficas en caliente es el **feature más crítico y de mayor superficie de fallo** del enterprise. Un bug en la sincronización entre estos componentes no es detectable con mocks.
- **Mitigación de coste:** El test live no necesita 100 eventos post-rotation. Basta con:
    1. Inyectar 50 eventos pre-rotation
    2. Trigger rotation (script etcd)
    3. Inyectar 50 eventos post-rotation
    4. Verificar `events_processed == 100` y `crypto_errors == 0`
    5. Verificar que `epoch_id` en headers de los últimos 10 mensajes coincide con nuevo epoch

Esto es ~3 minutos, no 5. El valor de confianza justifica el coste.

---

### Pregunta 4 — Test negativo (epoch_id incorrecto): **Requisito del gate de merge**

**Voto: Obligatorio en `test-e2e-enterprise`. No admite deuda técnica.**

**Justificación:**
- Un firewall que acepte mensajes con `epoch_id` inválido es una **vulnerabilidad de seguridad**, no un bug funcional. La deuda técnica no aplica a vectores de ataque.
- El test es trivial (~20 líneas):
    1. Inyectar mensaje con `epoch_id = 0xFFFF` (no existente)
    2. Assert: `crypto_errors == 1`, `events_processed` no incrementa
    3. Inyectar mensaje válido inmediatamente después
    4. Assert: pipeline continúa operativo (no hay estado corrupto)
- **Coste:** ~1 minuto. No hay justificación para diferirlo.

---

### Pregunta 5 — Gate de Jenkins: **Aceptar gate manual con backlog P1**

**Voto: Merge permitido con gate manual. Jenkins es BACKLOG-CI-ENTERPRISE-001 P1, no prerequisito.**

**Justificación:**
- El veto del Consejo (DAY 162) era sobre **validación funcional**, no sobre automatización. El criterio era: "Fases 0-4 verdes con EMECAS". Eso se cumple con `make emecas++` manual.
- Bloquear merge por Jenkins introduce **dependencia circular**: Jenkins necesita el código en main para integrarse propiamente (especialmente si Jenkins corre en infraestructura del proyecto).
- **Condición:** El backlog debe tener owner asignado y milestone. Sugiero: owner = Alonso (PI), milestone = 2 semanas post-merge.

---

### Pregunta 6 — Naming: **Opción (B) EMECAS++ como estándar oficial**

**Voto: Redefinir EMECAS++ como "EMECAS OSS + Enterprise". Documentar en README.md y arXiv.**

**Justificación:**
- **Ya existe mindshare:** El equipo usa informalmente "EMECAS++" desde DAY 161. Formalizarlo es menor fricción que educar sobre "EMECAS-E" o "TDH-Gate".
- **Semántica clara:** `++` en C++ es incremento. EMECAS++ = EMECAS + más capacidades. Es un naming que resuena con la audiencia técnica del proyecto.
- **Unificación filosófica:** No fragmentamos el protocolo en dos entidades. Hay un solo EMECAS, con dos niveles de validación. Esto refuerza la idea de que enterprise no es un producto separado, sino una **capacidad adicional** del mismo sistema.
- **arXiv:** En el paper, definir: *"EMECAS++ denotes the extended validation protocol covering both Community (OSS) and Enterprise cryptographic modes."*

---

## Resumen de decisiones para Alonso

| Pregunta | Decisión | Acción inmediata |
|----------|----------|------------------|
| 1 | (C) Targets anidados | Refactor Makefile: `emecas++` depende de `emecas` |
| 2 | Vault dev + test reconexión | Añadir `test_vault_reconnect` a `test-enterprise` |
| 3 | (B) Live rotation | Implementar `test-e2e-enterprise` con rotation en vivo (~3 min) |
| 4 | Test negativo obligatorio | Añadir `test_epoch_id_rejection` a `test-e2e-enterprise` |
| 5 | Gate manual aceptado | Crear BACKLOG-CI-ENTERPRISE-001 P1, owner Alonso |
| 6 | (B) EMECAS++ oficial | Actualizar README.md, arXiv draft, y comentarios en Makefile |

**Pronunciamiento:** El Consejo autoriza merge a `main` una vez implementados los puntos 1-4 y documentado el 6. El punto 5 (Jenkins) es post-merge con seguimiento P1.

---

*Deliberación completa. Quedo a la espera de la decisión final del árbitro.*