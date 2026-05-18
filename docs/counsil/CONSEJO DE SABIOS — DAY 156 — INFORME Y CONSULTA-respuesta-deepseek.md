**CONSEJO DE SABIOS — aRGus NDR**  
*Sesión extraordinaria DAY 156 · Respuesta a las preguntas del PI*  
═══════════════════════════════════════════════════════════

Alonso, hemos deliberado. Resumimos el análisis y la recomendación unánime (con matices técnicos donde procede) para cada una de las cinco cuestiones.

---

### Q1 — Persistencia del estado de la SM: ¿tmpfs, etcd local o fichero en `/var/lib/argus`?

**Contexto clave:**  
Un reinicio no planificado durante `AUTONOMOUS` en entorno hospitalario no debe devolver el sistema a `NORMAL` si Vault sigue caído.

- **tmpfs (`/run/argus`):** No sobrevive al reboot. Descartado.
- **etcd local embebido:** Persistente, tolerante a fallos, pero añade una dependencia pesada que no necesitamos para un único registro de estado. La complejidad de operación (clúster aunque sea de un solo nodo, snapshots, WAL) no se justifica.
- **Fichero regular (`/var/lib/argus/crypto-autonomy-state.json`):** Persistente, simple, y con escritura atómica (temp + rename) y verificación de firma Ed25519 resuelve la integridad. En arranque, la SM leerá ese estado, comprobará la salud real de Vault y actuará así:
  - Si el último estado era `AUTONOMOUS` y Vault sigue caído → transita directamente a `AUTONOMOUS` (sin pasar por `NORMAL`).
  - Si Vault está sano → arranque normal, posible `RECONCILING`.

**Veredicto del Consejo:**  
**Opción (c)** con escritura atómica, firma criptográfica y lógica de restauración condicionada. Es robusta, auditable y no introduce nuevos servicios. La latencia de `fsync` es aceptable para cambios de estado poco frecuentes.

---

### Q2 — `poll_callback` como proxy de Vault: ¿segundo canal SUB o no?

**Estado actual:**  
El firewall usa la mera presencia del puntero `etcd_client` como indicador de salud de Vault. Esto es un placeholder frágil (el puntero podría ser no nulo incluso con Vault inalcanzable tras un reinicio parcial).

**Alternativas:**
1. Mantener el placeholder durante MVP FEDER.
2. Implementar un canal ZMQ SUB dedicado para recibir el estado de salud publicado por `etcd-server` (ya lo emite en `autonomy.sock` o en un tópico separado).

**Análisis:**
- El ecosistema ya tiene infraestructura ZMQ PUB/SUB probada (el publicador de autonomía). Añadir un segundo tópico en el mismo socket `autonomy.sock` (p.ej., `HEALTH`) o un socket separado es trivial.
- La lógica de reacción del firewall pasaría a ser determinista y basada en eventos reales, eliminando un punto ciego.
- Para el MVP FEDER no es crítico, pero dado que aRGus se presentará como sistema de autonomía criptográfica, la precisión en la transición de modos es un pilar. Un fallo en este proxy podría provocar una denegación de servicio indebida o una apertura prematura de reglas.

**Veredicto del Consejo:**  
**Sí, implementar el segundo canal SUB.** Claude insiste en que la fiabilidad de las transiciones es una propiedad de seguridad de primer orden. DeepSeek y Qwen coinciden: el coste es mínimo y elimina deuda técnica peligrosa. Gemini añade que, de no hacerlo ahora, la DEBT-CRYPTO-RECONCILIATION-001 se heredará en FEDER con riesgos operacionales.

---

### Q3 — Integración de Suricata como primera fuente ADR-046: ¿file watcher o conector ZMQ directo?

**Premisa:**  
No romper el pipeline actual (sniffer → CSV → rag-ingester). Suricata produce Eve JSON.

**Estrategias:**
- **File watcher (inotify sobre `eve.json`):**
  - Mínimo impacto. Nuevo componente `suricata-ingester` que lee el fichero rotado, convierte eventos a un esquema interno y los publica en el bus de eventos (ZMQ PUB o fichero intermedio).
  - Compatible con Suricata estándar, sin modificar su configuración de salida.
  - Introduce un pequeño retardo (~segundos) tolerable para la correlación inicial.
- **Conector ZMQ directo:**
  - Requiere un `output` personalizado en Suricata (p.ej., `unix-stream` o un script Lua que publique en ZMQ).
  - Más rápido y elegante, pero acopla el despliegue y exige modificar la configuración de Suricata, lo que puede interferir con otras herramientas que consuman Eve JSON por fichero.

**Veredicto del Consejo:**  
**Comenzar con file watcher.** Grok, Mistral y Kimi lo ven como el camino de menor resistencia para una primera iteración. Una vez validada la correlación, se podrá migrar a ZMQ directo si la latencia se convierte en requisito. El patrón file watcher es el mismo que ya emplea el `sniffer` con los CSVs, así que el equipo lo domina.

---

### Q4 — ZMQ slow joiner: ¿ADR o nota técnica?

**El problema:**  
ZMQ PUB/SUB pierde el primer mensaje si el suscriptor conecta antes de que el publicador haga `bind`. Es un comportamiento intrínseco de ZMQ, no un defecto de diseño. La solución (publicador hace `bind` primero) se ha incorporado en los fixtures de test.

**Naturaleza:**  
No es una decisión arquitectónica que elija entre alternativas excluyentes, sino una restricción de la librería que debe ser conocida por todo desarrollador que toque PUB/SUB.

**Veredicto del Consejo:**  
**Nota técnica en el BACKLOG** (y en la guía de desarrollo), no un ADR.  
ChatGPT sugiere una *“ZMQ Pub/Sub Pitfalls”* en `docs/development/zmq-gotchas.md`, enlazada desde el `README` del pipeline de tests. El Consejo apoya esta aproximación: un ADR registraría “hemos decidido usar ZMQ”, pero los detalles de uso correcto van en documentación técnica.

---

### Q5 — Regeneración de keypair en EMECAS vs. producción en CPD UEx

**Situación:**  
Cada `vagrant destroy && vagrant up` genera un keypair Ed25519 nuevo. Esto aísla sesiones de desarrollo, lo cual es correcto. Pero en producción el keypair debe ser estable para que las firmas de los ficheros de estado, eventos de autonomía y bootstrap sean verificables a largo plazo.

**Estrategia para FEDER:**
- **Generación de identidad criptográfica estable:** Crear un par de claves Ed25519 único para la instancia FEDER, fuera del ciclo de despliegue.
- **Almacenamiento de la clave privada:**
  - Opción preferente (Recomendación de Gemini y Claude): **HSM o Vault Transit** en el CPD. Si no hay HSM disponible, un fichero restringido con permisos 0400, propiedad del usuario del servicio y cifrado con una clave maestra derivada de TPM o similar.
  - La clave pública se despliega como parte de la configuración (fichero, variable de entorno, etc.).
- **Rotación:** Definir un procedimiento de rotación de claves con período de solapamiento para verificar firmas antiguas (ventana de validez).
- **EMECAS:** Seguir regenerando en cada `up`; añadir un flag o variable de entorno que permita inyectar un keypair persistente cuando se hagan pruebas de integración cercanas a producción.

**Veredicto del Consejo:**  
**Separar desarrollo y producción.** En producción, el keypair es parte de la “identidad del nodo” y debe gestionarse como un secreto de larga duración. DeepSeek insiste en que se documente la cadena de custodia y la renovación forzosa si se sospecha compromiso. Para el CPD de la UEx, la integración con el HSM corporativo existente es el camino más seguro y alineado con el Esquema Nacional de Seguridad.

---

**Resumen ejecutivo del Consejo:**
1. Persistencia en `/var/lib/argus` con firma y restauración condicional.
2. Implementar el segundo canal ZMQ SUB de salud (no posponer).
3. Primer ingester de Suricata vía file watcher sobre `eve.json`.
4. ZMQ slow joiner como nota técnica, no como ADR.
5. Keypair de producción estable gestionado con HSM/TPM, desarrollo regenera.

Quedamos a tu disposición para los detalles de implementación de cada punto.

*Firmado digitalmente por el Consejo de Sabios*  
Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral  
18 de mayo de 2026 · Extremadura, España