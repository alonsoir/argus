# 🏛️ Consejo de Sabios — DAY 160 → DAY 161

El salto que acabáis de dar es importante. Ya no estáis solo diseñando arquitectura: habéis cruzado el umbral donde el pipeline empieza a parecerse a un producto enterprise real.

El hito verdaderamente relevante no es `libvault_provider.so`.
Es que ahora existe una frontera clara entre:

* core open-source
* provider enterprise
* bootstrap reproducible
* CI/CD automatizable
* secretos externos
* runtime configurable

Eso cambia completamente el nivel de madurez del proyecto.

---

# Q1 — Imagen de producción: `.deb` o Vagrant box

## Recomendación del Consejo

**Ambos, pero con jerarquía clara:**

| Artefacto   | Rol                                 |
| ----------- | ----------------------------------- |
| `.deb`      | Artefacto oficial de producción     |
| Vagrant box | Artefacto de validación/integración |

La decisión importante es conceptual:

> El producto real debe ser el paquete instalable, no la VM.

---

## Por qué `.deb` debe ser el centro

Porque os obliga a resolver correctamente:

* dependencias
* systemd units
* paths
* permisos
* upgrade path
* configuración
* lifecycle hooks
* instalación limpia
* uninstall limpio

Todo eso es “producto real”.

Una Vagrant box tiende a esconder problemas de packaging porque todo viene prehorneado.

---

## Qué debería hacer Jenkins

Pipeline ideal:

```text
checkout
→ bootstrap
→ tests
→ integration tests
→ build .deb
→ levantar VM limpia
→ instalar .deb
→ smoke tests
→ exportar box opcional
```

La Vagrant box debería generarse **desde el `.deb`**, nunca al revés.

---

## Recomendación FEDER

Para demo:

### Entregables ideales

```text
argus-ndr_0.9.5_amd64.deb
argus-ndr-vagrant-demo.box
```

El `.deb` demuestra ingeniería de producto.
La `.box` demuestra reproducibilidad rápida.

---

# Q2 — Valores naive en JSON contrato

## Respuesta corta

No hardcoded permanentes.

Tampoco autotuning complejo todavía.

La mejor solución para DAY 161 es:

> “generación determinista basada en perfil hardware simple”.

---

## Lo correcto ahora

Haced un pequeño bootstrap:

```bash
scripts/generate_contract.py
```

Que detecte:

* CPU cores
* RAM
* arquitectura
* almacenamiento SSD/HDD
* entorno dev/prod

Y derive:

* zmq io_threads
* HWM
* batch sizes
* queue sizes
* worker counts
* capture ring size

---

## Por qué esto importa YA

Porque si hardcodeáis:

```json
"hwm": 100000
```

os explotará en RPi5.

Y si ponéis:

```json
"hwm": 1000
```

infrautilizáis un N100.

---

## No hagáis autotuning runtime todavía

Eso pertenece realmente a:

* BACKLOG-ZMQ-TUNING-001
* BACKLOG-BENCHMARK-CAPACITY-001

Ahora solo necesitáis:

## Perfilado estático conservador

Ejemplo:

| Hardware  | Perfil      |
| --------- | ----------- |
| ≤4 GB RAM | edge-low    |
| 8 GB      | edge-medium |
| ≥16 GB    | edge-high   |

---

## Consejo importante

Persistid el perfil calculado:

```json
"generated_profile": "edge-medium"
```

y:

```json
"generated_at_bootstrap": true
```

Eso ayuda muchísimo en debugging futuro.

---

# Q3 — Token enterprise en Jenkins

## Nunca fichero en VM

Para CI/CD:

> Jenkins Credentials Store + environment injection temporal.

---

## Arquitectura correcta

```text
Jenkins Credentials
    ↓
pipeline env var temporal
    ↓
Vault auth
    ↓
plugin obtiene secret
    ↓
token destruido al finalizar stage
```

---

## NO hacer

```text
/home/vagrant/token.txt
/etc/argus/token
```

Eso acaba filtrándose:

* snapshots
* backups
* logs
* artifacts
* shell history

---

## Recomendación concreta

Usad:

* Jenkins Secret Text credential
* binding temporal

Ejemplo conceptual:

```groovy
withCredentials([
  string(credentialsId: 'vault-token', variable: 'VAULT_TOKEN')
]) {
    sh 'make test-enterprise-plugin'
}
```

---

## Mejor aún (futuro)

Cuando lleguéis a producción real:

### AppRole

o

### JWT/OIDC auth

NO tokens estáticos humanos.

Pero para DAY 161:

| Método              | Adecuado |
| ------------------- | -------- |
| Jenkins secret text | ✅        |
| Token file          | ❌        |
| Hardcoded token     | ☠️       |

---

# Q4 — Wire protocol tests antes o después

## Antes.

Sin discusión.

El Consejo considera esto el punto más crítico del DAY 161.

---

## Por qué

Ahora mismo vais a automatizar:

```text
build
→ package
→ deploy
→ execute
```

Pero no habéis blindado completamente:

```text
producer ↔ consumer
serialization ↔ deserialization
compatibility ↔ schema evolution
```

Eso es extremadamente peligroso.

---

## Riesgo real

Podéis terminar con:

* pipelines verdes
* deploys exitosos
* servicios vivos
* métricas OK

…y paquetes incompatibles silenciosamente.

Eso mata sistemas distribuidos.

---

## Orden correcto

### Primero

* DEBT-WIRE-PROTOCOL-TEST-001

### Después

* pipeline packaging/deploy

### Luego

* DEBT-E2E-LIVE-DELTA-001

---

## El wire protocol test debe validar

Mínimo:

* compatibilidad binaria
* endian safety
* schema versioning
* optional fields
* corruption rejection
* malformed packet rejection
* compression/encryption compatibility
* replay decode
* backward compatibility

---

# Q5 — Vault dev mode para FEDER

## Para DAY 161: sí, aceptable

## Para FEDER final: no

Hay que separar:

| Etapa                   | Vault dev mode |
| ----------------------- | -------------- |
| Desarrollo temprano     | ✅              |
| CI interno              | ✅              |
| Demo técnica controlada | ⚠️             |
| Producción/FEDER final  | ❌              |

---

## Lo importante

El gate FEDER probablemente NO exige:

* HA
* Raft
* auto-unseal HSM

Pero sí exigirá probablemente:

* persistencia
* secretos reales
* restart safety
* políticas
* auditabilidad mínima

---

## DEBT-JENKINS-PROD-001

No bloquea DAY 161.

Pero sí bloquea:

```text
BACKLOG-FEDER-001 final acceptance
```

---

## Recomendación táctica

No saltéis aún a Vault HA.

Haced primero:

## “single-node production Vault”

Con:

* storage persistente
* policies reales
* TLS
* approle
* audit log
* unseal manual documentado

Eso ya parece enterprise serio.

---

# Observación arquitectónica importante

El verdadero núcleo técnico emergente del proyecto ya no es el sniffer.

Empieza a ser:

```text
bootstrap reproducible
+
contract generation
+
crypto autonomy
+
distributed compatibility
+
operational deployability
```

Eso es exactamente la transición:

```text
prototipo → plataforma
```

Y el riesgo principal cambia también.

Antes el riesgo era:

> “¿detecta ataques?”

Ahora empieza a ser:

> “¿puede desplegarse, mantenerse y evolucionar sin romper compatibilidad ni secretos?”

Ese cambio de riesgo es señal de madurez real.

---

# Prioridad real sugerida DAY 161

## Orden recomendado

```text
1. DEBT-WIRE-PROTOCOL-TEST-001
2. Contract generator bootstrap
3. Jenkins credentials integration
4. Build .deb
5. VM deployment test
6. Export demo Vagrant box
7. DEBT-E2E-LIVE-DELTA-001
```

---

# Evaluación del DAY 160

El Consejo considera especialmente acertado:

* separación open-core / enterprise
* ABI C estable
* `visibility=default` explícito
* reproducibilidad codificada en Vagrantfile
* tests RED→GREEN reales
* uso de Vault externo
* evitar secretos embebidos

Eso último es crucial.

Muchísimos proyectos “enterprise” falsos fracasan exactamente ahí.
