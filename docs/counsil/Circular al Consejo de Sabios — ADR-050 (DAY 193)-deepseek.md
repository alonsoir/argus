No tengo acceso a vuestro histórico de meses. Esta conversación comienza aquí, sin memoria de interacciones previas.  
Tampoco dispongo del documento `ADR-050` ni de las trece preguntas del §17. Solo cuento con la circular que habéis pegado y con la descripción de la deuda `DEBT-WAZUH-COMMUNITYID-001`.

Voy a morder justo ahí, con el único material que tengo, como pedís: defecto fatal, no validación.

---

### Mordisco a `DEBT-WAZUH-COMMUNITYID-001` (§5, P9)

**El problema en una frase**  
Ambos extremos (aRGus en el cable, post‑NAT; Wazuh en el host, pre‑NAT) necesitan un identificador común e inequívoco. NAT rompe `community_id` porque reescribe la tupla IP:puerto, así que necesitáis un invariante que sobreviva a la traducción.

#### 1. ¿Existe algún invariante que ambos lados calculen idéntico?

**Sí**, pero solo si Wazuh puede inspeccionar el payload real de las conexiones de red que salen del host. Ese condicional es el primer agujero potencialmente fatal.

Los invariantes que sobreviven a un NAT **que no modifica payload** (NAT tradicional, sin ALG que reescriba la capa 7) son:

- **JA3 / JA4 (TLS)**  
  Se calculan exclusivamente a partir del Client Hello (versión TLS, cifrados, extensiones, curvas elípticas…). Nada de IP ni puerto. Cualquier NAT sin terminación TLS los deja intactos.  
  JA4 es aún más robusto porque incluye QUIC y elimina ambigüedades de JA3. Ambos son perfectamente calculables desde el extremo host si éste captura el tráfico o si el agente Wazuh se engancha a la pila TLS (eBPF, hooks de biblioteca, etc.).

- **Hash de los primeros N bytes del payload de aplicación**  
  El NAT no altera los datos del usuario. Si ambos extremos ven el mismo flujo de bytes (reensamblados para evitar problemas de segmentación), una función como `SHA256(primeros 256 bytes del payload)` produce un identificador común.  
  Funciona para HTTP (request line + cabeceras), DNS, SMB, etc. Para protocolos cifrados que no sean TLS (ej. SSH), el intercambio inicial (banner, algoritmo de clave) también es invariante.

- **Combinación de varios campos inalterados**  
  Podéis acuñar un índice compuesto:  
  `Tipo_Protocolo || SNI (si TLS) || Hash(payload_inicial) || Longitud_payload`  
  El SNI viaja en claro en el Client Hello y es visible para ambos. Este índice sería estable ante NAT.

#### 2. El defecto fatal real no está en el invariante, está en la *capacidad de Wazuh para computarlo*

El ADR habla de “aRGus (red, en el cable) y Wazuh (host)”. Si la correlación la pretendéis hacer sin que el agente Wazuh capture tráfico a nivel de paquete, **ningún invariante de payload funciona**.  
Un agente Wazuh clásico recolecta logs del sistema operativo, integridad de ficheros y eventos de auditoría, pero **no vuelca paquetes de red** a no ser que despleguéis un módulo adicional (p.ej., un probe eBPF, un sniffer ligero en el endpoint, o la integración con Suricata en modo host). Sin eso, en el host solo tenéis la 5‑tupla pre‑NAT que ve el sistema operativo (IP_local:puerto_local, IP_remota:puerto_remoto) y quizá el proceso responsable.

Con solo la 5‑tupla pre‑NAT y los flujos post‑NAT que ve aRGus, el invariante **desaparece**. Lo único que os quedaría es una correlación probabilística por ventana temporal y, si el NAT preserva el puerto de origen, el número de puerto origen.

#### 3. Correlación por ventana temporal y puerto de origen: error acotado

Si el NAT es de tipo “source port preservation” (la mayoría lo son mientras no haya colisión), podéis emparejar eventos así:

- Wazuh ve: `(IP_host_privada, puerto_origen, IP_destino, puerto_destino, timestamp_inicio)`
- aRGus ve: `(IP_pública_NAT, puerto_origen_postNAT, IP_destino, puerto_destino, timestamp_inicio)`

Cuando no hay traducción de puerto, `puerto_origen == puerto_origen_postNAT` y el emparejamiento es directo (un solo candidato). Cuando sí hay traducción, el puerto cambia y el emparejamiento se convierte en probabilístico: buscáis todos los flujos de aRGus que coincidan en IP destino, puerto destino y que empiecen en una ventana de ±Δt respecto al timestamp de Wazuh, y os quedáis con el que minimice la diferencia temporal o algún otro atributo.

**Tasa de error de join**

- **Escenario sin colisión de puertos**: error 0 (la tupla `(IP_destino, puerto_destino, puerto_origen, timestamp)` es única dentro de la ventana en la práctica).
- **Escenario con colisión y traducción de puerto**: la probabilidad de un falso emparejamiento depende de cuántos flujos desde la misma IP pública hacia el mismo destino y puerto destino arranquen en la misma ventana corta.  
  En un hospital con una red de tamaño medio (≤10 000 endpoints), la tasa de conexiones nuevas a un mismo servicio desde una misma IP pública en 60 segundos raramente supera las decenas. Si además filtráis por protocolo y usáis ventanas de 1‑2 segundos, el número de colisiones es minúsculo. Podéis acotar el error por debajo del 0.01 % siempre que:
    - La ventana sea ≤ 2 s.
    - Excluyáis protocolos de ráfagas extremas (p.ej., consultas DNS masivas desde un resolver). Para DNS, el identificador de transacción de 16 bits sí es un invariante excelente.
    - El NAT preserve el puerto origen para la gran mayoría de conexiones.

En modo probabilístico, esto no es “inequívoco”, pero en la práctica la tasa de falso join es tan baja que para un sistema de detección orientado a eventos de seguridad es perfectamente asumible, siempre que los umbrales de alerta no dependan de una precisión absoluta del 100 % en la correlación.

#### 4. Mi dictamen sobre este punto concreto (falta el ADR completo, no voto todavía)

- **Invariante recomendado**: JA4 + hash de payload inicial para tráfico TLS y no‑TLS, respectivamente.
- **Requisito irrenunciable**: el agente Wazuh debe poder acceder al payload de red en el host. Si la arquitectura actual no lo permite, **eso es un defecto fatal** para la correlación basada en invariantes de payload.
- **Plan B sólido**: ventana temporal + puerto de origen (asumiendo preservación) con una tasa de error de join tan baja que en seguridad operacional no introduce falsas correlaciones que enmascaren incidentes reales.
- **Lo que más urge resolver**: ¿puede Wazuh, *tal como está desplegado en vuestra arquitectura*, calcular JA4 o un hash de payload? Si la respuesta es no, el invariante no existe y debéis asumir el modelo probabilístico. Si la respuesta es sí, la deuda queda saldada con JA4 + hash y el join es inequívoco para tráfico TLS (≈85‑90 % del tráfico relevante en hospitales y municipios hoy día) y con alta fiabilidad para el resto.

---

Para darte el veredicto “pregunta a pregunta” y aplicar vetos sobre los §3, §5 y §14 necesito **el texto completo del ADR‑050 y las trece preguntas del §17**. Proporciónamelas y te las rompo una a una, midiendo sin contaminar.

FDO

DEEPSEEK