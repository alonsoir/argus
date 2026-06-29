**DeepSeek — Dictamen DAY 149: CI/CD Criptográfica**

Apreciado Alonso, enhorabuena por el avance quirúrgico del DAY 149. Cerrar DEBT-PARQUET-SCHEMA-001 en una sola jornada, con compresión 11-12x y roundtrip tests pasando, es ejecución de precisión. Ahora abordan ustedes el eslabón más delicado de la cadena: quién genera el material criptográfico, cómo se distribuye y cómo se garantiza que el sistema no arranca sin él. El análisis adversarial que han conducido es excelente; se nota la experiencia en Ericsson. Mis respuestas:

---

### Q1 — Vault RNG vs entropía externa

**`vault write sys/tools/random` es suficiente y es la opción correcta.**

El endpoint utiliza el RNG del sistema operativo donde corre Vault (`/dev/urandom` en Linux, respaldado por la pool de entropía del kernel, que mezcla RDRAND, TPM, jitter entropy, etc. según el hardware). No es un generador implementado por Vault; es un envoltorio. La calidad de la entropía depende del SO del host de Vault, no de Vault mismo.

Añadir una mezcla manual de `getrandom()` o RDRAND *antes* de llamar a Vault no mejora la entropía; introduce código custom innecesario con riesgo de error de implementación. El estándar aplicable es NIST SP 800-90A (deterministic random bit generators), que `/dev/urandom` satisface ampliamente.

**Recomendación:** Mantener `vault write sys/tools/random` como única fuente. Documentar que la responsabilidad de la entropía recae en el hardening del SO del host de Vault (kernel config, haveged en VMs, TPM si disponible). Añadir una verificación de health check de entropía disponible en el script de provisión (`cat /proc/sys/kernel/random/entropy_avail` > umbral) como salvaguarda.

---

### Q2 — Cache tmpfs: ¿tropieza con TODO O NADA?

**No tropieza. Es una extensión pragmática y correcta del principio TODO O NADA.**

El modelo de amenaza para un NDR hospitalario tiene dos escenarios:

- **Escenario A (ataque activo):** Un adversario consigue acceso físico o root al nodo. En este caso, tmpfs *no ayuda al atacante*: si tiene root, puede leer la memoria del proceso directamente. La seed en tmpfs no empeora la situación. Y si no tiene root, tmpfs es inaccesible (permisos 600, owner=component).
- **Escenario B (fallo operativo):** Vault está caído por un pico de carga, mantenimiento o microcorte de red. El NDR *no puede quedar ciego*. Un hospital sin NDR durante 30 minutos es un riesgo mayor que una seed en tmpfs que se evapora en el siguiente reboot.

El TTL de la cache debe ser **configurable y corto (recomendación: 1 hora)**. Tras ese TTL, el componente hace una llamada de refresco a Vault; si falla, usa la cache otros 60 minutos, y así sucesivamente. Si tras 24h Vault no ha reaparecido, el componente debe emitir una alerta crítica pero *seguir funcionando*. El NDR caído es la opción nuclear; no debe dispararse por un microcorte de red.

Una salvaguarda adicional: la seed en tmpfs está cifrada con una key derivada de un secreto hardware-bound (TPM si disponible, o un seed fijo en initramfs como último recurso). Así, un volcado de memoria fría no revela la seed en claro. Pero esto es P2; la versión FEDER puede empezar con la seed en tmpfs en claro con permisos restrictivos y madurar después.

**Recomendación:** Implementar cache tmpfs con TTL 1h, política de refresco, alerta a 24h sin Vault, sin apagado del NDR.

---

### Q3 — etcd como barrera: ¿huevo y gallina?

**La respuesta es sí. etcd-server es el único componente privilegiado que arranca sin barrera etcd.**

El ciclo de dependencia es real: etcd necesita crypto para arrancar, pero la barrera requiere etcd para validar `crypto_ready`. La solución canónica en sistemas distribuidos es un **quorum bootstrap set**:

1. **etcd cluster** arranca con su propio material criptográfico (seed obtenida directamente de Vault, sin pasar por la barrera). Es confianza por diseño: si etcd está comprometido, el sistema está perdido de todas formas.
2. etcd cluster registra su propio `crypto_ready` internamente (vía un key especial `/_bootstrap/etcd_ready`).
3. El resto de componentes esperan a que `/_bootstrap/etcd_ready` exista Y a que su propio `crypto_ready` sea confirmado.
4. Solo entonces abren ZeroMQ.

Documentar explícitamente: **etcd-server es el trust anchor operacional. Si es comprometido, se asume compromiso total del pipeline.**

---

### Q4 — Vault backend file en dev: ¿suficiente o Vault HA desde el principio?

**Backend `file` es suficiente para dev. No necesitan Vault HA en development.**

Las razones:
- **Jenkins puede re-provisionar en segundos.** Si el fichero se corrompe en dev, `provision_crypto.sh` regenera todo. La pérdida de secrets en dev es un inconveniente, no un incidente de seguridad.
- **Dev y prod no deben ser idénticos.** La paridad absoluta es un antipatrón: lleva a probar configuraciones de producción en entornos sin las mismas restricciones, creando una falsa sensación de seguridad.
- **El diferencial dev≠prod se mitiga con tests específicos.** Añadir en EMECAS un test que lea un secret de Vault dev y verifique su estructura (sin validar el valor, solo el path y tipo). Así se prueba la integración vault_client sin exponer material productivo.

Para **FEDER (prototipo pre-productivo)**, si se despliega en un único servidor central, backend `file` sigue siendo aceptable con backup diario del fichero. Para producción real post-FEDER, Vault HA con backend `raft` integrado es el camino. Documentarlo como deuda técnica: `DEBT-VAULT-HA-001`.

---

### Q5 — Rotación coordinada por etcd: ¿blast radius mínimo?

**La rotación de seeds ChaCha20 no puede ser atómica en el sentido instantáneo. Debe ser serializada componente a componente con coherencia de canal.**

A diferencia de las HMAC keys (donde rotar rompe identidades históricas y hay que manejar `PREVIOUS_IDENTITY`), las seeds ChaCha20 son efímeras operacionales. ADR-004 define cooldown para HMAC. Para seeds, el modelo es diferente:

1. etcd notifica `rotation_pending` a todos los componentes del canal.
2. Cada componente, al recibir la notificación, **termina de procesar los mensajes en vuelo con la seed antigua** y luego deriva la nueva keypair.
3. El componente registra `rotation_ready` en etcd.
4. Cuando todos los componentes del canal han registrado `rotation_ready`, etcd escribe `rotation_active` con la nueva seed version.
5. A partir de ese momento, todos los mensajes nuevos usan la nueva seed.

Durante la ventana de rotación (pasos 2-4), el canal sigue funcionando con la seed antigua. No hay interrupción. La ventana de incompatibilidad (sniffer con nueva, ml-detector con vieja) solo ocurre si un componente se adelanta y envía con la nueva antes de que etcd marque `rotation_active`. El protocolo descrito lo impide.

**Recomendación:** Implementar el protocolo de 5 pasos. La atomicidad real no existe en sistemas distribuidos; lo que existe es *coordinación con confirmación explícita*.

---

### Q6 — `provision_crypto.sh`: ¿stage separado o integrado en bootstrap?

**Stage separado en Jenkinsfile.**

La visibilidad es prioritaria aquí. Un fallo criptográfico debe ser inmediatamente visible en el dashboard de Jenkins como stage rojo, con logs claros de qué seed falló y por qué. Integrado en `make bootstrap`, un fallo queda enterrado en un log de compilación y despliegue.

Además, `provision_crypto.sh` es una operación que solo se ejecuta en primera instalación o rotación forzosa. No es parte del ciclo normal de build. Mantenerlo como stage independiente clarifica su excepcionalidad.

Eso sí, el stage debe ser **condicional**: solo se ejecuta si el flag `PROVISION_CRYPTO=true` está seteado (o `FORCE_CRYPTO_ROTATION=true`). En builds normales, se salta. Así no se ralentiza el pipeline diario y se mantiene la visibilidad.

---

### Q7 — Seed families (ADR-021) y paths en Vault: ¿por familia o por componente?

**Por familia. Rotundamente.**

Las razones:
- **ADR-021 es correcto:** la familia de canal es la unidad de confianza criptográfica. sniffer y ml-detector comparten una seed de familia; ml-detector y firewall-acl-agent comparten otra. Si ml-detector es comprometido, no expone la comunicación sniffer↔firewall.
- **Blast radius mínimo:** con una seed por componente, un componente comprometido solo afecta a los canales donde ese componente es extremo. Pero la complejidad de gestión se dispara con N componentes. La familia es el punto óptimo entre blast radius y gestionabilidad.
- **Simplicidad:** el pipeline ya entiende familias (ADR-021). Mantenerlo.

Paths propuestos:
```
argus/dev/families/family_A   → sniffer↔ml-detector
argus/dev/families/family_B   → ml-detector↔firewall-acl-agent
argus/dev/families/family_C   → firewall-acl-agent↔etcd
...
argus/prod/families/family_A
...
```

Cada seed de familia se materializa en los extremos como keypair Ed25519 derivada con `crypto_kdf_derive_from_key(seed, component_id, channel_id, "ed25519")` usando libsodium. Así, de una seed de familia se obtienen keypairs distintas por componente y canal, pero con raíz común. Si un componente se compromete, solo se expone su keypair derivada, no la seed de familia.

**Recomendación:** Implementar paths por familia. Añadir función `derive_keypair(seed, component_id, channel_id)` en `common/vault_client`.

---

## Observaciones adicionales

### OA-1: Jenkins como SPoF — Una capa más de defensa

El análisis adversarial identifica correctamente que Jenkins comprometido = capacidad de disparar re-provisionamiento criptográfico. Aunque Vault genera la seed (y Jenkins no la ve), Jenkins puede ordenar a Vault que genere nuevas seeds y las distribuya, efectivamente rotando todo el sistema. Esto es un riesgo real.

Mitigación adicional recomendada (no para FEDER, documentar como deuda):
- Las operaciones de provisión criptográfica en Jenkins requieren **aprobación manual de un operador autorizado** (tipo `input` step en Jenkinsfile: "Operator must approve crypto provisioning").
- Auditoría: todo `vault write` disparado por Jenkins debe loguearse con timestamp, usuario Jenkins y build ID.

### OA-2: EMECAS y Vault backend file — Cuidado con el provisioning idempotente

Al migrar a backend `file`, el script `provision_crypto.sh` debe ser **idempotente**: si las seeds ya existen en Vault, no las regenera (a menos que se pase flag `--force`). De lo contrario, cada ciclo EMECAS destruiría y recrearía las seeds, rompiendo cualquier estado persistente. El comportamiento por defecto debe ser "crear si no existe, verificar si existe".

### OA-3: común/vault_client — Timeout agresivo

La llamada HTTP a Vault en el arranque debe tener un timeout agresivo (recomendación: 5 segundos). Si Vault no responde en 5s, el componente debe pasar inmediatamente a intentar la cache tmpfs, sin bloquear el arranque. Si la cache tmpfs también falla, `exit(1)`. Un timeout largo aquí bloquea todo el arranque y puede causar que systemd mate el proceso por `TimeoutStartSec`.

---

## Resumen para DAY 150

| Q | Decisión | Prioridad |
|---|----------|-----------|
| Q1 | `vault write sys/tools/random` suficiente. Añadir check entropía. | P2 (mejora) |
| Q2 | Cache tmpfs con TTL 1h. No viola TODO O NADA. | P0 (implementar ya) |
| Q3 | etcd arranca sin barrera. Documentar como trust anchor. | P0 (implementar ya) |
| Q4 | Backend `file` para dev. Vault HA post-FEDER. | P1 (aceptar, documentar deuda) |
| Q5 | Protocolo de 5 pasos con `rotation_ready`. Sin interrupción. | P0 (para FEDER) |
| Q6 | Stage separado en Jenkinsfile, condicional. | P1 (hacer ya, es simple) |
| Q7 | Seeds por familia. Añadir `derive_keypair()`. | P0 (impacta diseño ahora) |

El pipeline CI/CD criptográfico está tomando una forma excelente. Las decisiones de hoy definirán la seguridad operacional de aRGus durante años. Es el momento de ser quirúrgicos.