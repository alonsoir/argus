Nota previa: los cuatro adjuntos (`bloque1_day293.md`, `bloque2_day294.md`, etc.) no han llegado al chat — solo vemos el texto del mensaje. Respondemos sobre lo que hay; si lo re-adjuntáis, afinamos. — *Marta*

---

## 0. Auditoría adversaria de lo medido

**Marta (medición):** El "0 DROPs del inocente" no está aislado por diseño. Con solo un atacante y un inocente, la etapa 2 puede estar discriminando por **correlación con la víctima saturada**, no por origen. Además, con 1 sola corrida E2E no tenéis varianza: 1,3 s de latencia es un punto, no una distribución. **Medida:** 20 repeticiones E2E idénticas con semillas de generador distintas; registrar percentiles de `time_to_block`. **Predicción:** p50 ≈ 1,2–1,5 s, p95 < 2,5 s, 0 falsos INICIO en inocente. **Refutación:** dispersión p50 > ±50 % entre corridas (entonces la latencia la domina algo no controlado, p. ej. el EWMA de arranque).

**Elif (confusores):** El 0,55 s/s de reloj bajo dns100 sugiere **cola de eventos, no semántica de reloj**: 37 eventos/s no-flow apuntan a que un consumidor bloquea. Antes de P5, medid el delta de ingesta vs. consumo. **Medida:** contador de profundidad de cola en el canal de eventos + ratio en/s procesados. **Predicción:** la cola crece monótonamente bajo dns100 y drena al terminar → es capacidad, no tiempo. **Refutación:** cola plana con reloj desfasado → bug de reloj real.

**Tomas (alcance):** "0 positivos en TCP 50 KB/s" mejora al bosque viejo, pero el inocente benigno *nunca superó K=3 al mismo tiempo que el atacante*. El sistema no ha demostrado que mantiene su especificidad **cuando la víctima está bajo presión real y el inocente compite por ancho de banda** — ese es el hueco de P4.

---

## P1. Etapa 2 por comportamiento

**Recomendación (Tomas):** tres rasgos por víctima-ventana, sin estado por paquete: **(1) source_ip_dispersion** (orígenes distintos con ≥1 paquete a la víctima, contador incremental), **(2) cuota del top origen** sobre la tasa de la víctima (argmax de un mapa origen→contador, O(1) por paquete con actualización lazy), **(3) ratio paquetes in/out** por origen (solo requiere el contador ya existente de respuestas por flujo). Un ataque de reflexión desde pocos orígenes → dispersión baja + cuota alta; un flash-crowd legítimo → dispersión alta. **Medida:** reentrenar etapa 2 con estos 3 añadidos y correr familias fuera de entrenamiento (SSDP, memcached, SYN). **Predicción:** detección en familia no vista pasa de ~0 % a > 70 % de ventanas de ataque, con < 2 % de positivos en dns100. **Refutación:** que la reflexión *pura* (miles de orígenes spoofed, cuota baja, dispersión alta) siga sin detectarse — entonces el rasgo discriminante real es la asimetría in/out, y hay que reponderar.

## P2. Batería v3

**Recomendación (Elif):** los ejes propuestos miden robustez de tamaño y tasa, pero falta el eje crítico: **atacante e inocente concurrentes bajo presión de la víctima** (hoy cada corrida es uno u otro), y **spoofed multi-origen** (un generador que emite desde N IPs, rompe source_ip_dispersion). **Medida:** añadir 2 corridas: (a) ataque + dns100 + TCP simultáneos sobre .1; (b) reflexión desde 200 orígenes falsos. **Predicción:** (a) inocente mantiene 0 INICIO pero sus positivos de etapa 2 suben a < 5; (b) etapa 2 con rasgos P1 detecta > 60 % de ventanas. **Refutación:** si (a) produce INICIO en el inocente, el firewall por víctima contamina orígenes y P4-(b) muere.

## P3. Calibración para un cliente real

**Recomendación (Marta):** captura previa de **7 días completos** (incluye fin de semana + pico laboral), defectos fijos documentados, calibración automática solo como *sugerencia* con aprobación humana. **Método:** K = max(3, 2× p99,9 de victim_rate_ratio por víctima en la semana); m/k/n del histórico de INICIOs espurios; hold = 2× duración observada del p99 de ráfagas legítimas. **Criterio de aceptación:** 0 INICIO en la semana de referencia con la nueva K, y retención de la detección del laboratorio (regresión con los pcaps propios). **Predicción:** en red hospitalaria, p99,9 de ratio ≈ 2–3 para servicios DHCP/DNS internos (ojo: los arrancadores de red médica generan ráfagas sincronizadas → K≥3 puede ser justo ahí). **Refutación:** > 10 víctimas con p99,9 > 5 → el EWMA con τ=3600 s no absorbe su ciclo diario y hay que hacerlo por-hora-del-día.

## P4. Mitigación real

**Recomendación (Tomas):** opción **(b)** — descartar solo los flujos que la etapa 2 marca, por origen, durante el hold; con (c) como respaldo *si* la firma está disponible. (a) castiga por definición al inocente que compite por la misma víctima. **Medida en lab:** mitigación real activa con ataque .50 + inocente .51 concurrente; medir throughput/pérdida del inocente durante ataque con y sin mitigación. **Predicción:** inocente conserva ≥ 95 % de su tasa de entrega; víctima baja de ~60 pps de ataque a < 5 pps en < 3 s de aplicar. **Refutación:** si el atacante rota orígenes dentro del hold y la mitigación pierde > 30 % de su eficacia en 30 s, entonces hace falta (c) con firma por-puerto.

## P5. Base de tiempo única

**Recomendación (Elif):** opción **(b)** con ancla explícita: monotónico para ordenar/durar dentro del nodo, ancla realtime guardada al arranque y en cada `makestep` para cruzar nodos y Parquet. Con `makestep 1 -1`, epoch en todo (opción a) rompe `time_to_block` en el instante del salto. La (c) añade dependencia de kernel sin resolver el cruce de nodos. **Medida:** test de caos: durante una corrida E2E, forzar salto de pared de +5 s (`chronyc makestep` artificial) y verificar que latencias, hold y el grafo no cambian. **Predicción:** `time_to_block` pre/post salto difiere < 50 ms; los hold siguen contando en monotónico sin reinicio. **Refutación:** cualquier hold que se acorte/alargue por el salto → hay cronómetro apoyado en pared sin convertir.

## P6. Disyuntor de saturación

**Recomendación (Marta):** ambas: **degradar a regla barata por víctima + avisar**. Umbral: medir en el anillo la **cola de eventos** (la de P5/Elif), no los pps brutos — la saturación observable es la cola, no la tasa. Umbral sugerido: cola > X eventos sostenida 2 ventanas → modo degradado (solo etapa 1 + política m/k/n). **Medida:** inyectar 2× la capacidad (~220 pps) y registrar pérdida de eventos, latencia de decisión e INICIOs. **Predicción:** en modo degradado la latencia de decisión vuelve a < 2 s y se pierde < 1 % de eventos, con 1 falso negativo aceptado documentado. **Refutación:** si la regla degradada produce INICIO en dns100 (que ya sabéis que presiona etapa 1), el umbral de degradación está mal puesto y hay que subirlo.

---

**Prioridad (consejo, unánime):** P5 primero — no porque sea lo más valioso, sino porque con dos relojes y una cola que crece bajo carga, **cualquier medida que toméis después está contaminada**: el 0,55 s/s hace que P1/P2/P6 se midan contra un reloj que no es. Orden: P5 → diagnóstico de los 37 eventos/s (es gratis una vez P5 instrumente la cola) → P2 con el eje concurrente → P1 → P4 → P3.