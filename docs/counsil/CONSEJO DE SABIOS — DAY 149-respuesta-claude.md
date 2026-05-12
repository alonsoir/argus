Buena pregunta. Me pongo en modo Consejo adversarial.

---

## Problemas reales — sin piedad

### P0 — Críticos

**1. Jenkins como single point of failure criptográfico**
Si Jenkins cae o es comprometido, toda la cadena criptográfica cae. El atacante que controla Jenkins controla todas las seeds de todos los ambientes. Estás trasladando el problema del portátil del founder a Jenkins — es mejor, pero no es seguro por diseño.

*Mitigación necesaria:* Jenkins solo genera entropy. Vault genera la seed real internamente con su propio RNG (`vault write sys/tools/random`). Jenkins nunca ve la seed completa.

**2. `exit(1)` en el componente no es suficiente como TODO O NADA**
Si el componente falla después de que ZeroMQ ya había enviado un mensaje parcial al componente siguiente, el pipeline queda en estado inconsistente. El orden de inicialización importa — si sniffer arranca antes de que ml-detector tenga crypto, hay mensajes en el wire sin destinatario autenticado.

*Mitigación necesaria:* etcd como barrera de sincronización pre-arranque. Nadie abre ZeroMQ hasta que etcd confirma que TODOS los componentes tienen `crypto_ready`.

**3. Seed en Vault inmem en dev**
Vault dev mode es `inmem` — cada `vagrant destroy` destruye todas las seeds. El EMECAS ritual destruye la VM. Cada ciclo EMECAS requiere re-provisionar toda la criptografía. Esto rompe el ritual actual.

*Mitigación necesaria:* Vault con backend de fichero (`file`) incluso en dev, o el EMECAS incluye siempre `provision_crypto.sh` como paso obligatorio.

---

### P1 — Importantes

**4. Derivación de keypair en memoria — ¿cómo sobrevive un restart?**
Si un componente se reinicia (systemd restart, OOM killer), necesita volver a Vault a buscar la seed. Si Vault está temporalmente caído en ese momento, el componente no arranca. En producción, en un hospital, esto puede significar que el NDR queda offline durante una ventana de ataque.

*Tensión real:* TODO O NADA vs disponibilidad. En infraestructura crítica, un NDR offline es peor que un NDR con crypto degradada.

*Mitigación:* cache cifrada en memoria compartida (tmpfs) con TTL. No en disco. Si tmpfs tiene la seed y Vault está caído, el componente puede arrancar. Si tmpfs también está vacío y Vault está caído → TODO O NADA.

**5. Rotación coordinada por etcd asume que etcd es confiable**
Si etcd es comprometido, el atacante puede triggear una rotación falsa y poner a todos los componentes en estado de renegociación simultánea — ventana de ataque perfecta. O puede bloquear la rotación indefinidamente.

*Mitigación:* etcd no solicita seeds a Vault directamente. Solo coordina el timing. Jenkins/Vault son los únicos que generan y custodian seeds. etcd solo dice "es hora" — no tiene acceso a las claves.

**6. Seeds distintas por ambiente — ¿cómo se garantiza empíricamente?**
"Entropy del filesystem donde corre Jenkins" no es suficiente si Jenkins corre en la misma máquina para dev y prod. `/dev/urandom` en el mismo host puede producir bytes distintos, pero no hay ningún mecanismo que **aserte** que `seed_dev != seed_prod` antes de almacenarlas.

*Mitigación necesaria:* El script `provision_crypto.sh` hace un assert explícito y falla si las seeds son iguales. Trivial de implementar, crítico de tener.

---

### P2 — Deuda técnica aceptable

**7. `common/vault_client` en C++20 — latencia de arranque**
Cada componente hace una llamada HTTP a Vault en el arranque. En una red lenta o con Vault bajo carga, esto añade latencia al arranque del pipeline. No crítico, pero medible.

**8. Rotación parcial — ventana de incompatibilidad**
Durante la rotación, hay un momento en que sniffer tiene la clave nueva y ml-detector tiene la vieja. Los mensajes ZeroMQ cifrados con ChaCha20-Poly1305 con la clave nueva no pueden ser descifrados por ml-detector hasta que complete su rotación. etcd tiene que gestionar esta ventana.

**9. `key_rotation_hours` hardcodeado en JSON**
Si el JSON es generado por Ansible/Jinja2 y el valor viene de `group_vars`, cualquiera con acceso al repo puede ver cada cuánto rotan las claves. No es un secreto, pero es información operacional que un atacante puede usar para timing attacks.

---

## Resumen de la destrucción

| Problema | Severidad | ¿Bloquea FEDER? |
|---|---|---|
| Jenkins como SPoF criptográfico | P0 | No — mitigable con Vault RNG |
| Estado inconsistente ZeroMQ | P0 | Sí — necesita barrera etcd |
| Vault inmem rompe EMECAS | P0 | Sí — necesita backend file |
| Disponibilidad vs TODO O NADA | P1 | No — decisión de diseño |
| etcd comprometido | P1 | No — etcd no toca seeds |
| Assert dev≠prod | P1 | No — trivial añadir |
| Latencia arranque | P2 | No |
| Ventana rotación parcial | P2 | No — etcd serializa |
| key_rotation_hours visible | P2 | No |

**Los tres P0 son atacables hoy. ¿Empezamos por el Vault backend file?**