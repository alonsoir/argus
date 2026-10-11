# Notas para el paper — DAY292 (batería caliente y reentrenamiento de la cabeza DDoS v2)

## Método
- Ataque y benigno sobre la MISMA víctima: un origen inocente (.51) mantiene una línea base (~10 pps) durante todo el ataque
  (.50). Etiqueta por construcción (origen), nunca por rasgo; la IP no es rasgo. Mide el falso positivo colateral sobre el
  inocente durante el ataque, imposible de medir con datasets públicos de ataque puro.
- Régimen caliente: la clave de víctima acumula ≥30 ventanas antes del ataque (90 s de base), como en producción.
- 19 corridas, 0 pérdidas hasta 110 pps, todas con predicción escrita antes de medir. Reproducibilidad: pcaps por sha256,
  CSV por arranque, consolidado y modelos con sha256.

## Hallazgos sobre el rasgo de víctima (EWMA con histéresis)
- La histéresis sostiene la señal del ataque: ratio 3,7-10,6 durante 90 s frente al colapso a ≈1 en ~20 s sin ella (DAY291).
- Efecto de fase: según dónde caiga el inicio respecto a la ventana de 1 s, la ventana parcial se absorbe con α rápido y el
  ratio queda hasta ~17 % más bajo durante el ataque (cota analítica 0,1×(K_in·base − base)).
- Umbral efectivo: K_in=3 no deja entrar cargas de 3× (contraste benigno) y sí de 4×.

## Línea base: el bosque viejo
- Marca como DDoS el 100 % de una subida TCP legítima de 10 KB/s y el 0 % de un SYN flood (inversión total), y 0 % de los
  contrastes DNS benignos.

## Tres modelos sobre los mismos datos (RF, 100 árboles, sin scaler)
| | A (con arranque) | B (sin arranque) | B sin victim_pps |
|---|---|---|---|
| Recall test fuera del arranque | 99,45 % (incl. arranque) | 100 % | 100 % |
| FP inocente / contraste / ambiente | 0 / 0,78 / 0 % | 0 / 0 / 0 % | 0 / 0 / 0 % |
| Decide por | firma | firma + umbral absoluto ~30-40 pps | firma + ratio relativo |
| Frío 30/60/100 pps | parcial | 0 / ~97 / ~97 % | 0 / ~8 / ~13 % |
| Nodos / profundidad | 7168 / 21 | 4500 / 19 | 3714 / 14 |

- Ruido de etiqueta en el arranque: durante 0,5-1,5 s el rasgo de víctima es de la ventana anterior y los paquetes de ataque
  son indistinguibles de lo benigno. Entrenarlos como ataque induce el atajo de tamaño (FP sobre una respuesta DNS legítima
  de 1442 B). Sacarlos del entrenamiento y publicarlos como LATENCIA (0,5-1,5 s) elimina ese FP.
- Colinealidad de diseño: con base fija, ratio ≈ pps/10; el bosque eligió el rasgo absoluto. Quitar victim_pps fuerza el
  relativo, con el coste honesto de no detectar en víctima fría.

## Límites (decirlo así)
- Los tres modelos fallan dejando una familia fuera (sin ntp ~0 %; sin syn marca ~99 % del inocente TCP): reconocen firmas
  de los generadores (tamaño fijo + reflexión), no comportamiento. Un 100/0 en test en distribución NO prueba generalización.
- El FP colateral 0 % sobre el inocente se apoya en parte en diferencias de tamaño entre los pcaps de base y de ataque.
