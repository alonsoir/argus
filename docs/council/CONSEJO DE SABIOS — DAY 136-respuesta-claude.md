**Respuesta Claude — Consejo DAY 136**

---

**Pregunta 1 — Riesgos antes de demo FEDER (1 agosto)**

El riesgo más concreto es `DEBT-IRP-NFTABLES-001`. `argus-network-isolate` está referenciado en la unit systemd pero no implementado. Si durante la demo ocurre cualquier evento que dispare el IRP, el sistema intenta ejecutar un binario inexistente. Eso en una demo ante evaluadores FEDER es un fail catastrófico. Lo priorizaría sobre cualquier otra deuda.

El segundo es `DEBT-SEEDS-SECURE-TRANSFER-001`. No bloquea la demo Vagrant, pero si un evaluador técnico pregunta "¿cómo despliegan los seeds en producción real?" la respuesta honesta actual es "pasan por el Mac host". Hay que tener una respuesta preparada o el protocolo esbozado, aunque no implementado.

**Pregunta 2 — Delta XDP vs libpcap para el paper**

Las diferencias científicamente publicables son tres. Primero, punto de captura: XDP opera antes del stack de red del kernel, libpcap después — eso implica diferencias medibles en latencia y en paquetes perdidos bajo carga. Segundo, consumo de CPU por paquete capturado — XDP con eBPF maps vs libpcap con copy-to-userspace. Tercero, y más relevante para infraestructura crítica con hardware limitado: el mínimo de hardware necesario para F1≥0.9985 con 0 paquetes perdidos en cada variante. Ese es el dato que justifica científicamente por qué aRGus puede correr en un hospital sin servidor dedicado.

**Pregunta 3 — Deuda más preocupante para infraestructura crítica**

`DEBT-SEEDS-BACKUP-001`. En un hospital o municipio sin equipo técnico dedicado, si el nodo falla catastróficamente y los seeds se pierden, el pipeline no arranca. Nadie sabe regenerarlos. Eso no es una deuda técnica — es un riesgo operacional real para el usuario final. Necesita un procedimiento documentado, simple, ejecutable por alguien sin conocimientos de criptografía.

---

Cuando tengas las demás respuestas hacemos la síntesis. 🎯