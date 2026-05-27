Como **Gemini (Consejo de Sabios)**, he analizado las cuestiones abiertas del **ADR-024** para el proyecto **aRGus NDR**. Nos encontramos en una fase crítica donde la teoría criptográfica debe aterrizar en el hardware limitado de un hospital rural. Aquí los compromisos no son fallos, sino decisiones de ingeniería.

A continuación, presento el veredicto técnico para las **OQ-5 a OQ-8**:

---

## 🏛️ Veredicto OQ-5 — Revocación de clave estática X25519

**Veredicto:** **CONDICIONAL** (Implementar **A** + **B** como proceso atómico).
**Recomendación técnica:** La Blocklist en `etcd` es el "freno de mano", pero si la `seed_family` (PSK) está comprometida, el atacante puede corromper el propio `etcd`. La única garantía real es un **re-provisioning total** que rote la `seed_family`. El mecanismo primario debe ser un script de emergencia que invalide la `seed_family` actual, forzando a todos los nodos a un estado "desconectado" hasta recibir la nueva clave física.
**Riesgo residual:** Ventana de tiempo entre el robo físico y la ejecución del re-provisioning donde el atacante tiene acceso pasivo al tráfico cifrado previo (si no hay FS) o activo si emula un nodo.

---

## 🏛️ Veredicto OQ-6 — Continuidad de sesión (Zero Downtime)

**Veredicto:** **IMPLEMENTAR Opción B** (Versioned deployment.yml).
**Recomendación técnica:** `etcd` debe distribuir el nuevo `deployment.yml` con la clave pública actualizada. Los componentes deben mantener en memoria un pequeño histórico de "Claves Válidas" (la actual y la inmediatamente anterior). Al recibir un handshake con una clave nueva presente en el YAML, el componente actualiza su peer-map en caliente. Esto evita la complejidad de la ventana de gracia temporal manual.
**Riesgo residual:** Ligero aumento de superficie de ataque al aceptar dos claves válidas para un mismo peer durante la propagación del YAML.

---

## 🏛️ Veredicto OQ-7 — Replay protection en handshake

**Veredicto:** **ACEPTAR** riesgo documentado para v1.
**Recomendación técnica:** En una LAN hospitalaria cerrada, el riesgo de replay del primer mensaje sin poseer el PSK es despreciable, ya que el atacante no puede completar el handshake ni derivar claves de sesión. Implementar un timestamp (Opción B) introduce una dependencia crítica en el tiempo del sistema (NTP), que en entornos aislados suele fallar, causando denegaciones de servicio accidentales.
**Riesgo residual:** Un atacante podría causar un consumo menor de CPU/Memoria inundando con handshakes replayeados, pero nunca acceder a los datos.

---

## 🏛️ Veredicto OQ-8 — Noise_IKpsk3 vs Noise_KK en ARMv8

**Veredicto:** **IMPLEMENTAR Noise_IKpsk3** (Mantener decisión original).
**Recomendación técnica:** El *identity hiding* del iniciador en **IK** es un beneficio marginal en una LAN estática, pero el **PSK binding (psk3)** es la "joya de la corona" para aRGus, ya que integra la `seed_family` directamente en la derivación de claves de forma nativa. Sobre `libsodium`, `noise-c` es solo un wrapper; si supera los 200KB, una implementación manual siguiendo el patrón IKpsk3 sobre libsodium es criptográficamente idéntica y más ligera.
**Riesgo residual:** Mayor complejidad de implementación manual frente a usar un patrón más simple como KK.

---

### 📊 Análisis de Rendimiento Estimado (ARMv8 Cortex-A72)

Para un nodo Raspberry Pi 4, las operaciones criptográficas no son el cuello de botella, sino la latencia de red de la propia LAN.



| Operación | Tiempo estimado (μs) | Ciclos de reloj |
| :--- | :--- | :--- |
| **X25519 (Key Exchange)** | ~500 - 800 μs | ~1.2M |
| **ChaCha20-Poly1305 (Encrypt/Decrypt)** | ~10 - 20 μs | ~30k |
| **HKDF-SHA256 (Key Derivation)** | ~50 - 100 μs | ~150k |
| **Total Handshake Latency** | **< 2 ms** | **Insignificante** |

**Conclusión de Rendimiento:** El umbral de **50 ms** es extremadamente conservador. En una Raspberry Pi 4, el pipeline de aRGus procesará el handshake en menos de **5 ms** (CPU time). El límite real será la pila de red y el scheduler de Linux.

---

### 🛡️ Posición Minoritaria Registrada
*Se registra una nota de cautela respecto a la **OQ-7**: Si en el futuro aRGus NDR permite la conexión de nodos vía WAN/VPN, el riesgo de replay pasará de "Aceptable" a "Crítico", requiriendo la implementación inmediata de un esquema de frescura (nonces o timestamps).*

**¿Damos por cerradas estas OQ para desbloquear la implementación de la PHASE 3 en el pipeline?** 🏛️🛡️🚀