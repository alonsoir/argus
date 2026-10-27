# DAY308 — Notas para el paper (arXiv:2604.04952)

Material honesto y medido de DAY308 (26-oct-2026), rama `feat/sniffer-flow-expiry`, utilizable si el paper documenta el
coste del sniffer y el método. Fuentes: `docs/ml-heads/day308_paso1_diseno.md` (sección 7) y
`docs/ml-heads/day308_paso2_diseno.md` (sección 6). Todas las cifras son del defender (VM VirtualBox, i9-9980HK, sin
AVX-512), salvo donde se diga otra cosa.

## 1. Estado por flujo de tamaño fijo, sin cambiar los rasgos que se emiten

- **Antes:** cada flujo guardaba un vector por paquete (8 vectores, ~30 B por paquete sin límite: 292 MB para un flujo
  de 10 M paquetes) y cada evento copiaba el flujo entero y recalculaba medias, desviaciones y tiempos entre llegadas
  sobre todos sus paquetes: O(n) por evento (7,7 ms de copia a 1 M paquetes).
- **Después:** acumuladores de tamaño fijo con sumas enteras exactas (`__int128` para las sumas de cuadrados, con una
  cota demostrada: Σx² ≤ (Σx)² < 2^128). Copia por evento de 400 B, O(1).
- **Medido:** 0 B por paquete (10 M paquetes en un flujo: delta de RAM constante); copia a 1 M paquetes 7,7 ms →
  0,3 µs; coste propio de calcular los rasgos ~0,6 µs por evento, independiente del tamaño del flujo (antes 4,5 / 28,6 /
  183 µs según el flujo tuviera 1-20, 21-500 o más de 500 paquetes); RAM con un paquete por flujo 658 → 625,6 B.
- **Paridad:** 300 000 eventos deterministas; todos los rasgos que no dependen de una varianza, idénticos byte a byte;
  las varianzas, a 0 ulp de un oráculo en `long double` de dos pasadas. Esas varianzas cambian respecto a antes porque
  el cálculo antiguo (dos pasadas en float) se equivocaba hasta 1,5·10⁻⁵ relativo (~250 ulp) en flujos largos.
  Ningún rasgo con umbral cambió de escalón.

## 2. Caducidad de la tabla de flujos

- **Antes:** la configuración declaraba tres tiempos de caducidad (300 s en dos sitios del JSON, 120 s en el código) y
  ninguno se aplicaba: la función de limpieza existía pero nadie la llamaba, y era O(n²). Con la tabla llena, la LRU
  echaba flujos en silencio.
- **Después:** un solo sitio de configuración en el JSON, con defectos validados y el origen de cada valor en el log;
  limpieza desde la cola de la LRU, O(caducados); tope de duración activa perezoso, O(1), desactivado por defecto
  hasta medir su efecto en la cabeza DDoS; contadores visibles (caducados, desalojos, marcas futuras).
- **Medido** (80 000 flujos): limpieza con 72 000 caducados 6,0 s → 32 ms; con 8 000, 1,5 s → 2,5 ms; sin caducados,
  9 ms → 1,2 µs por pasada. E2E en el lab: caducidad funcionando con tráfico real, lock de shard ≤ 277 µs.
- **Una suposición medida, no dada por hecha:** que la marca de los paquetes (`bpf_ktime_get_ns`) y la hora de la
  tabla (`steady_clock`) son el mismo reloj. Se instrumentó un contador de marcas del futuro: 0 en el E2E.

## 3. Límites que quedan, dichos

- El histograma de longitudes por flujo (necesario para la entropía de la cabeza DDoS) sigue creciendo con las
  longitudes **distintas**: 70,8 kB por flujo en el peor caso medido (1 461 longitudes). Con la tabla llena se
  extrapola a ~11 GB (no medido). Un atacante puede forzarlo variando la longitud de sus paquetes: vector de
  agotamiento de memoria abierto como deuda propia. Además, la foto DDoS recorre ese histograma en cada evento y es hoy
  el coste dominante por evento (23-36 µs de media en flujos de más de 500 paquetes).
- Los defectos de caducidad (300 s, sin tope) son seguros, no óptimos: su efecto en la cabeza DDoS (entrenada sin
  caducidad) se medirá con un barrido.

## 4. Método: lo que salió mal y cómo se detectó

- **Predicciones escritas antes de cada medida.** De las que fallaron, cada una tiene su causa documentada: no calcular
  el `sizeof` antes de predecir RAM (relleno de `__int128`); suponer un coste fijo que en realidad era trabajo con
  vectores; llevar cifras absolutas de una máquina a otra con un factor supuesto, o de un tipo de trabajo a otro.
- **Un coste inexplicado se persiguió con hipótesis falsables.** Populate costaba en el defender 5,8 veces lo de otra
  máquina. Se falsaron, una a una y con medidas: el reloj de la VM, la memoria dinámica y el protobuf bajo VirtualBox, y
  la caché fría por el propio instrumento. Se confirmó en parte que escribir la salida en la carpeta compartida de
  VirtualBox añadía ~0,55 µs por evento. Lección: las medidas de tiempo no escriben en la carpeta compartida.
- **La referencia de paridad no era la del binario de producción.** El sniffer se compila con `-march=native -flto`;
  con esas banderas, la fusión FMA cambia en las últimas cifras 104 784 de 300 000 eventos del código antiguo
  (incluida la entropía de la cabeza DDoS). Desde DAY308 la paridad se compara en los dos perfiles. Las varianzas
  nuevas (en `long double`) no cambian con las banderas.
- **Pruebas de mutación para saber qué ve cada herramienta.** Cambiar la regla de pares de tiempos lo detecta el test
  y no el instrumento de paridad (su generador nunca repite marcas). Cuatro mutaciones de la caducidad: las cuatro las
  detecta el test nuevo.
- **Un indicador de calidad mal leído desde DAY307.** La comprobación de las pruebas miraba "82 tests", que resultó ser
  el número del firewall, no el total (128). Se corrigió a comprobar las cinco líneas de resumen.
- **Las secciones de un documento escritas antes de medir no se reescriben**: el resultado va en una sección aparte,
  para que se vea qué se predijo y qué se midió.
