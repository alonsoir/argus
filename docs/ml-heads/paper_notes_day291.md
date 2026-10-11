# Notas para el paper — DAY291 (histéresis en la línea base por víctima)

## 1. Un umbral sin estado hace que la existencia de un ataque dependa del jitter
La línea base por víctima (EWMA con dos tasas de aprendizaje, DAY286) cambiaba a la tasa lenta cuando la
ventana ACTUAL superaba ratio ≥ 5, sin memoria. Medido en el laboratorio, con la víctima en régimen caliente:
- ataque de 3× (30 pps sobre 10): nunca activa la tasa lenta; la señal del ratio dura ~15 s y el resto del
  ataque es indistinguible de la base (ratio ≈ 1);
- ataque de 7× (60 pps): la ventana parcial del inicio (4,78) deja que la tasa rápida absorba un tercio del
  margen; entra al filo (5,07), y una sola ventana con 0,2 pps menos de jitter (4,95) lo devuelve a la tasa
  rápida. El ataque desaparece en ~20 s.
Lección: protegerse de los falsos positivos permanentes (aprender la nueva normalidad) y detectar ataques
sostenidos son objetivos contrapuestos; una regla por ventana sin estado los resuelve por azar. La
histéresis (entrada con K_in, salida con K_out, tasa lenta expresada como tiempo de absorción τ) los separa:
el ataque se sostiene durante τ y un cambio legítimo se acepta después de τ.

## 2. Método: parámetros elegidos por coste medido, no por intuición
- Arnés offline sobre 18 días de ventanas del contador en el kernel (150 688 ventanas, 83 arranques),
  misma fórmula que el código, cada arranque con estado vacío.
- K_in=3, K_out=1,5, τ=3600 s, clave caliente = 30 ventanas: 33 episodios en ambiente en 18 días (máx 10 s);
  sin la condición de clave caliente, 328 (10×). Episodios largos del laboratorio: todos con tráfico
  elevado real; ninguno se queda atascado tras el fin del ataque.
- Resultado en vivo: ratio sostenido 3,8 → 3,6 (30 pps) y 6,9 → 6,2 (60 pps) durante los 90 s del ataque;
  antes ≈ 1 a los 20 s. Tras el ataque el ratio vuelve a ≈ 1 en lugar de hundirse a 0,3–0,4: la base ya no
  se contamina.
- Paridad exacta offline ↔ vivo (float32, mismo formato): 0 discrepancias en 184 y 197 ventanas.

## 3. Etiquetado por construcción y el daño colateral
- La línea base benigna se envía desde un origen distinto (.51) al ataque (.50), hacia la MISMA clave de
  víctima: la etiqueta sale de la IP, que NO es un rasgo del modelo.
- Consecuencia medida: durante el ataque, las filas benignas comparten exactamente los rasgos de víctima
  del ataque. Solo los rasgos de flujo/paquete pueden separarlas. Decisión: entrenarlas como benignas y
  reservar corridas para medir aparte el falso positivo colateral, que es exactamente el bloqueo de un
  inocente.
- Límite esperado (a medir): respuestas DNS legítimas grandes (DNSSEC/TXT) y paquetes de reflexión son
  indistinguibles paquete a paquete; la señal correcta (respuesta no solicitada) exige ver las consultas
  salientes, que esta topología no ofrece.

## 4. Disponibilidad frente a fallo seguro en la configuración
En una infraestructura crítica (hospital), un proceso que se niega a arrancar por un error de configuración
puede dejar la red sin protección durante días si nadie lee el aviso. Política adoptada: un campo ausente o
inválido se sustituye por un valor por defecto validado por medición, con un aviso explícito y buscable, y
el proceso arranca. El riesgo restante (un valor válido pero inadecuado) se ataca con validación previa al
despliegue y pruebas automáticas dentro del rango.

## 5. Honestidad del proceso
Las predicciones escritas antes de medir destaparon cuatro defectos en mis propios scripts de medida (origen
temporal tomado del tráfico propio del cliente; filas de fast alert sin filtrar; registro de la ventana
anterior a la salida; cierre por fin de arranque confundido con salida por histéresis). Ninguno era del
sistema medido; todos se detectaron porque el resultado no coincidía con lo predicho y se paró a mirar.
