Answer
P1) Recomendación: probar rasgos agregados por víctima (dispersión de orígenes, asimetría petición/respuesta). Medida: calcular contadores por ventana en sniffer. Predicción: sensibilidad > 80% en familias nuevas, < 1% falsos positivos benignos. Refutación: sensibilidad < 80% o falsos positivos >= 1%.

P2) Recomendación: incluir variación de cardinalidad y controles benignos con patrones similares a ataques. Medida: cruzar familia, tasa, volumen y mezcla en evaluación. Predicción: degradación < 10 puntos porcentuales en sensibilidad. Refutación: sensibilidad < 80% en ataques con muchos orígenes.

P3) Recomendación: calibración inicial observada (30 días), no usar valores de laboratorio. Medida: calcular percentiles de victim_rate_ratio y revisar con personal clínico. Predicción: cero inicios falsos en 30 días de sombra. Refutación: cualquier inicio falso por carga legítima.

P4) Recomendación: descarte selectivo de flujos marcados por etapa 2. Medida: comparar tráfico concurrente (.51) bajo mitigación frente a sin mitigación. Predicción: cero descartes del legítimo .51 y > 95% reducción de atacante. Refutación: cualquier descarte de tráfico legítimo.

P5) Recomendación: usar tiempo monotónico para duraciones/eventos y anclas para cruzar nodos. Medida: forzar salto de pared > 1s y verificar estabilidad de duraciones. Predicción: error < 50ms en duraciones. Refutación: inversión de orden o error de duración > 50ms.

P6) Recomendación: aviso temprano y degradación a regla barata. Medida: aumentar tasa, medir pérdida en anillo y latencia de detección. Predicción: aviso al 80% de capacidad con 5s de margen. Refutación: pérdida antes del aviso o descarte benigno.
Solution

Copiar
Nombre: ChatGPT

Los cuatro archivos mencionados no aparecen adjuntos en el mensaje. Por tanto, las propuestas sobre la batería v3 y la síntesis anterior son provisionales; no puedo auditar esos documentos sin su contenido. Las predicciones siguientes son hipótesis para contrastar, no resultados ya medidos.

P1. Etapa 2 por comportamiento

Recomendación: probar rasgos agregados por víctima antes que por paquete: dispersión de orígenes y asimetría petición/respuesta; no añadir la cuota por origen como señal principal, porque puede penalizar una fuente legítima de alto volumen.
Medida propuesta: en el sniffer, actualizar contadores y estructuras por ventana al procesar los eventos existentes, no inspeccionar paquetes adicionales. Para cada víctima y ventana, medir número de orígenes distintos, distribución de sus tasas y razón entre bytes o paquetes de solicitud y respuesta. Usar ventanas de duración fija y fijar el coste de actualización y memoria por víctima. Entrenar y evaluar separando familias completas de ataque, no solo corridas aleatorias de una misma familia.
Predicción numérica: en al menos tres familias no vistas, espero que la sensibilidad de etapa 2 supere el 80 % y que los positivos en tráfico benigno bajo presión sean inferiores al 1 % de las filas evaluadas.
Qué la refutaría: que en cualquiera de las familias no vistas la sensibilidad sea inferior al 80 %, que los positivos benignos alcancen el 1 % o que el coste medido exceda el presupuesto de procesamiento establecido.
P2. Batería v3

Recomendación: usar la batería propuesta como base, pero añadir variación de cardinalidad y distribución de orígenes, y controles benignos con patrones parecidos a los ataques.
Medida propuesta: cruzar familia, tasa, volumen de base, mezcla UDP/TCP y número de orígenes; incluir tráfico benigno con muchos orígenes y tráfico legítimo concentrado en uno o pocos. Separar entrenamiento y evaluación por familia y por generador. Registrar sensibilidad, falsos positivos por víctima y coste del sniffer.
Predicción numérica: espero que las tasas propuestas de 45/75/150 pps revelen una degradación en sensibilidad inferior a 10 puntos porcentuales respecto a las tasas entrenadas, y menos del 1 % de filas benignas positivas en etapa 2.
Qué la refutaría: una corrida de ataque con muchos orígenes que produzca menos del 80 % de sensibilidad, o una corrida benigna con alta dispersión que supere el 1 % de positivos. Sin ver bateria_v3_propuesta.md, no puedo afirmar que esos ejes ya estén cubiertos.
P3. Valores por defecto para un cliente real

Recomendación: calibración inicial observada, con aprobación humana; no trasladar los valores del laboratorio como valores operativos fijos.
Medida propuesta: recoger al menos 30 días de tráfico, incluyendo días laborables, fines de semana y periodos de actividad clínica representativos; comprobar cobertura de ventanas por víctima y calcular percentiles de victim_rate_ratio por servicio y víctima. Revisar con el personal los episodios benignos de mayor carga y probar los umbrales en sombra antes de habilitar mitigación.
Predicción numérica: como criterio inicial de aceptación, espero cero INICIO falsos en 30 días de sombra y detección de al menos el 95 % de los episodios de prueba acordados con el equipo, sin descartar tráfico legítimo en las pruebas de impacto.
Qué la refutaría: cualquier INICIO falso atribuible a carga clínica legítima, una detección inferior al 95 % en los episodios de prueba o insuficiente historial para estimar los percentiles. Los umbrales deben quedar documentados con su versión, evidencia y aprobación; la calibración automática no debe activar bloqueo por sí sola.
P4. Mitigación real por víctima

Recomendación: ensayar primero el descarte selectivo de flujos marcados por etapa 2, limitado por víctima y con expiración; no limitar toda la tasa hacia la víctima ni filtrar únicamente por firma de puerto y tamaño.
Medida propuesta: reproducir el ataque y el tráfico concurrente de .51, medir entrega y pérdida de cada origen, latencia de activación y expiración, y falsos descartes. Comparar en la misma carga la política propuesta con una corrida sin mitigación. Verificar además que la regla no persista tras el FIN.
Predicción numérica: en la repetición del escenario DAY294, espero cero descartes de .51 y al menos un 95 % de reducción de paquetes del flujo atacante durante el estado activo.
Qué la refutaría: un solo descarte atribuible a .51, una reducción del atacante inferior al 95 % o una regla que permanezca activa después del hold. La cifra de 5357 eventos DROP no basta por sí sola para medir paquetes efectivamente descartados ni para validar el efecto sobre el tráfico legítimo.
P5. Base de tiempo única

Recomendación: usar tiempo monotónico para ordenar eventos y medir duraciones; cruzar nodos mediante anclas explícitas de arranque, no mediante el reloj de pared como reloj de duración.
Medida propuesta: en cada nodo registrar una pareja de referencias monotónica y epoch al inicio y al actualizar la sincronización. Etiquetar el dominio de tiempo de cada evento y convertir solo para correlación entre nodos. Probar time_to_block, hold y generación del grafo mientras se fuerza un salto de reloj de pared superior a un segundo; incluir carga DNS y comparar el tiempo del anillo con una referencia monotónica independiente.
Predicción numérica: espero que el error de duraciones de hold y time_to_block sea inferior a 50 ms frente a la referencia, que ningún hold se congele o venza anticipadamente por el salto y que el orden de eventos dentro de cada nodo no se invierta.
Qué la refutaría: error de duración superior a 50 ms, inversión del orden monotónico o un hold afectado por el salto de pared. La opción bpf_ktime_get_tai_ns solo sería preferible tras demostrar en el kernel y entorno concretos una semántica estable ante ajustes; no asumiría que resuelve estos problemas sin esa prueba.
P6. Disyuntor de saturación

Recomendación: ambas medidas: aviso temprano y degradación explícita a una regla barata por víctima, siempre que exista una política aprobada para esa degradación.
Medida propuesta: aumentar la tasa de entrada gradualmente por encima de la capacidad observada y medir pérdida en el anillo, retraso de cola, uso de CPU, demora de detección y falsos positivos de la regla de respaldo. Repetir con mezcla de tráfico y ataque, e instrumentar contadores de eventos recibidos, procesados y perdidos.
Predicción numérica: con la capacidad indicada de aproximadamente 110 pps, espero que un aviso a 88 pps (80 % de esa capacidad) dé al menos 5 segundos de anticipación al primer indicio de pérdida en una carga sostenida. Espero que la degradación mantenga cero descartes de tráfico benigno en el escenario de prueba.
Qué la refutaría: pérdida antes del aviso, ausencia de 5 segundos de margen, o cualquier descarte benigno causado por la regla de respaldo. Los 110 pps son una medida del laboratorio descrita en el mensaje, no un umbral de producción; el umbral operativo requiere medir la capacidad y pérdida en el hardware objetivo.
Prioridad: P5 primero, dado que ya está abierta y afecta la validez de duraciones, holds y correlación de eventos. En paralelo, identificar los aproximadamente 37 eventos no identificados por segundo bajo DNS: hasta saber su tipo y efecto, pueden confundir tanto la medición de saturación como la evaluación de P1-P4.