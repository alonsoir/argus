**Respuesta de Claude al Consejo — DAY 161:**

---

## Análisis del ciclo de vida criptográfico enterprise

### El problema central: rotación coordinada

El riesgo más grave no es la generación ni la distribución — es la **rotación coordinada**. El comentario en `crypto_provider.h` lo dice explícitamente: "sniffer + ml-detector deben migrar SIMULTÁNEAMENTE". Si un componente rota y otro no, el canal ZMQ queda cifrado con keypairs incompatibles y el pipeline se rompe silenciosamente. Esto es peor que un crash: los mensajes llegan pero no se descifran, `crypto_errors` sube, y el sistema entra en degraded sin alarma clara.

### Arquitectura mínima viable — orden de implementación

**Pieza 1 (P0): `enterprise_vendor.key` a Vault**
Antes de cualquier automatización, la clave privada vendor debe salir de la VM. Sin esto, todo lo demás es teatro. Jenkins no puede rotar lo que no controla. Un `vagrant destroy` borra la clave y el sistema enterprise queda inoperativo sin forma de recuperarse automáticamente.

Implementación: un script de bootstrap que, en el primer arranque enterprise, sube la clave a `secret/argus/enterprise/vendor_key` en Vault con política de acceso restringida a Jenkins.

**Pieza 2 (P0): Coordinación de rotación vía etcd-server**
El etcd-server ya es el árbitro del pipeline. La rotación coordinada debe pasar por él:

```
Jenkins → Vault (nuevo seed) → etcd-server /rotate_seed → 
  broadcast ZMQ a todos los componentes → 
  cada componente ACK → 
  etcd-server confirma rotación completa
```

Sin el broadcast y el ACK, la rotación es una apuesta. El `AutonomyPublisher` ya existe — es el canal natural para este broadcast.

**Pieza 3 (P1): Ventana de gracia en CryptoTransport**
Durante la rotación, hay una ventana donde algunos componentes tienen el seed nuevo y otros el viejo. El canal ZMQ se rompe en esa ventana. La solución es que `CryptoTransport` mantenga el seed anterior durante N segundos como fallback de descifrado (double-key window). Esto da tiempo a que todos los componentes completen la rotación sin perder mensajes.

**Pieza 4 (P1): Jenkins pipeline de rotación**
Solo tiene sentido implementarlo después de Piezas 1 y 2. Un Jenkinsfile que:
1. Genera nuevo seed en Vault
2. Llama al endpoint de rotación del etcd-server
3. Espera confirmación de ACK de todos los componentes
4. Verifica que `crypto_errors=0` en todos tras la rotación
5. En caso de fallo: rollback al seed anterior

**Pieza 5 (P2): Token enterprise — distribución automática**
El token enterprise tiene vida larga (1 año). No necesita rotación frecuente. Distribuirlo vía Vault como `secret/argus/enterprise/token` es suficiente para la MVP. Jenkins lo renueva 30 días antes de expirar.

### Riesgos arquitecturales críticos

**Riesgo 1: Split-brain criptográfico**
Si la rotación falla a medias (etcd-server rotó, firewall no), el sistema queda en estado inconsistente indefinidamente. El `CryptoAutonomyStateMachine` debería tener un estado `CRYPTO_SPLIT_BRAIN` que active autonomía y alerte.

**Riesgo 2: Bootstrap enterprise en nodo nuevo**
Si se añade un nodo al cluster, necesita el seed actual de Vault. El flujo de bootstrap enterprise no está definido. Sin él, escalar horizontalmente requiere intervención manual.

**Riesgo 3: Revocación de token enterprise**
Si el token de un componente es comprometido, no hay mecanismo de revocación sin reiniciar ese componente. La pubkey está hardcodeada en el binario — revocar requiere recompilar y redesplegar.

### Veredicto

El orden correcto es: **Vault para vendor.key → coordinación vía etcd-server → ventana de gracia en CryptoTransport → Jenkins pipeline → distribución automática de token**.

Production-ready requiere al menos Piezas 1 y 2 cerradas y testadas con EMECAS. Las Piezas 3-5 son necesarias para producción real pero no bloquean un piloto controlado en hospital/municipio con rotación manual supervisada.

**No mergear a main hasta que Pieza 1 y Pieza 2 estén implementadas y con tests E2E verdes.**

---

Listo. Pega las respuestas de los otros 7 y consolidamos.