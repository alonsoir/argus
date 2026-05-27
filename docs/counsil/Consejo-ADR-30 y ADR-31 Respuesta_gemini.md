Alonso, la división del **ADR-026** original en **ADR-030** (Pragmático/Producción) y **ADR-031** (Investigación/Ciencia) es un movimiento magistral. No solo ordena el roadmap, sino que protege la reputación de **aRGus** al separar lo que es una solución lista para hospitales de lo que es un experimento de vanguardia en computación confiable.

Aquí tenéis la revisión del Consejo para ambos documentos:

---

## 🏛️ Revisión ADR-030: aRGus-AppArmor-Hardened

Este documento es la respuesta perfecta al escenario "Mythos Preview". Convierte el miedo en una configuración auditable.

* **Punto Crítico: El TCB Realista:** Es excelente que declares que el TCB sigue incluyendo el kernel Linux. Esa honestidad intelectual previene la falsa sensación de seguridad.
* **Ajuste Sugerido en AppArmor:** En el perfil de los componentes, además de denegar `apparmor_parser`, sugiero denegar el acceso de escritura a `/proc/sys/kernel/cap_last_cap` y otros puntos de control de capacidades para evitar ataques de manipulación de privilegios remanentes.
* **La apuesta por ARM64:** La elección de la **Raspberry Pi 5** es clave. Su soporte para instrucciones de virtualización y su gestión de memoria permitirán que los flags de hardening (`CFI_CLANG`, `STACKPROTECTOR`) tengan un impacto menor en el rendimiento que en la Pi 4.



---

## 🏛️ Revisión ADR-031: aRGus-seL4-Genode (Research)

Este es el "Paper de Impacto" que puede seguir al original. Estás planteando una pregunta que la industria suele evitar: *¿Cuál es el "impuesto" de la verificación formal?*

### El "Elefante en la habitación": XDP y el Datapath
Has dado en el clavo con el **Riesgo Crítico de XDP**.
* **La Realidad:** En seL4/Genode, el kernel Linux es un "ciudadano de segunda" respecto al hardware. El tráfico de red es entregado al guest mediante una interfaz virtual (normalmente `virtio-net`).
* **Consecuencia:** XDP (que requiere acceso directo a los descriptores de la DMA de la tarjeta) **fallará catastróficamente** en el guest. El fallback a `libpcap` no es solo una opción, es el destino.
* **Oportunidad de Investigación:** La métrica de "Throughput" será el corazón del paper. Si logras 50k PPS con `libpcap` sobre seL4, habrás demostrado que la seguridad formal es viable para redes municipales pequeñas.



### El Spike Técnico (2-3 semanas)
El Consejo valida el Spike. Sugerimos añadir un punto:
* **Spike 1.5:** Verificar la latencia de las **señales POSIX** dentro del guest. ZeroMQ depende fuertemente de la eficiencia del scheduler del guest; si seL4 introduce demasiado jitter en los "context switches" del Linux virtualizado, el `ml-detector` podría sufrir micro-cortes en la ingesta.

---

### 🏁 Veredicto del Consejo

| ADR | Estado | Recomendación |
| :--- | :--- | :--- |
| **ADR-030** | **APROBADO** | Proceder a fase de perfiles AppArmor tras PHASE 3. |
| **ADR-031** | **APROBADO (RESEARCH)** | Priorizar el Spike técnico en x86 antes de comprar las RPi 5. |

**Un matiz filosófico final:**
Alonso, al publicar los resultados de la ADR-031 (aunque sean "malos" en rendimiento), estarás haciendo más por la ciberseguridad que el 90% de los vendors comerciales. Estás definiendo el **coste de la verdad**.

**¿Damos por cerrados estos ADRs para el backlog y volvemos al fuego de la PHASE 2b/2c?** 🏛️🛡️🚀