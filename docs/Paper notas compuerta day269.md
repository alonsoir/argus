# Notas para el paper — La compuerta level1→level2 y la evaluación honesta de la cabeza DDoS (DAY269)

> Material para la sección de evaluación DDoS / amenazas a la validez. Todo lo de aquí
> está medido en DAY269. Redactar con el principio "medir, no votar" y "HECHO ≠ SOSPECHADO".

## 1. El hallazgo arquitectónico (no es una limitación, es un resultado)

El detector DDoS de aRGus (level2) no es un clasificador que ve todo el tráfico: opera
**detrás de una compuerta**. Solo puntúa flujos que el clasificador general (level1) ya ha
clasificado como ATTACK con confianza suficiente:

```
label_l1 == 1 && confidence_l1 >= threshold_level1_attack   →   se ejecuta level2 DDoS
label_l1 == 0 (BENIGN)                                       →   el flujo muere en level1
```

Consecuencia para el diseño: **la especificidad y el recall de la cabeza DDoS están
acotados aguas arriba por el enrutado de level1.** Un DDoS que level1 marque BENIGN nunca
llega a la cabeza DDoS, por buena que sea esta. La cadena es tan fuerte como su eslabón
más aguas arriba. Este es el patrón de diseño que el paper debe nombrar: la fiabilidad de
un detector especializado embebido no se mide en aislado, sino como parte de la cascada
que lo alimenta.

## 2. La medición (y por qué el primer número era ficción)

Sobre un replay del botnet Neris (CTU-13; 320 524 paquetes, 19 135 flujos):

| magnitud | valor |
|---|---|
| bloques de extracción de features en el log | 11 208 |
| flujos que pasaron la compuerta level1 → level2 DDoS | **6** |
| flujos marcados como DDoS por el detector desplegado | **0** |

FPR desplegado sobre Neris = 0/6. **N = 6 es demasiado bajo para afirmar especificidad.**
Lo que el número mide de verdad es la **selectividad de level1** ante tráfico botnet
no-DDoS: ~99,95 % del tráfico Neris fue despachado como BENIGN antes de alcanzar la cabeza.

### Ficción de medición a evitar en el paper
Una evaluación offline ingenua (puntuar TODOS los flujos extraídos con la cabeza, sin la
compuerta) daba FP@0,7 = 0,7 % sobre 2 291 flujos. **Ese número no representa el
comportamiento de producción**, porque en el pipeline la compuerta impide que esos flujos
lleguen a la cabeza. Reportarlo sin el contexto de la compuerta sería engañoso. Se
descarta como métrica de producción; a lo sumo sirve como caracterización del candidato
offline, con etiqueta explícita.

## 3. Caveats obligados (amenazas a la validez)

1. **Neris no es DDoS.** Es C&C de botnet. La medición prueba que la compuerta *bloquea*
   tráfico no-DDoS, NO que *deje pasar* DDoS real. El recall de la cadena completa sobre
   DDoS real está SIN medir (pendiente: CICDDoS2019 por el pipeline).
2. **Artefacto de replay (MTU).** Sobre VirtualBox, el tráfico Neris llega íntegramente
   unidireccional (flujos de 1 paquete) o como broadcast/multicast; no sobrevive ninguna
   sesión bidireccional de C&C. La calidad del flujo está degradada por el transporte, no
   por aRGus. Etiquetar cualquier número como "sobre Neris tal como lo entrega el harness",
   no "sobre Neris".
3. **Dos modelos.** El candidato offline evaluado (`ddos_head_A`, RandomForest sobre 9
   features CICFlowMeter) NO es el detector desplegado (bosque inline synthetic-9). No
   mezclar sus números.

## 4. Contexto del candidato offline (ddos_head_A), si se cita

Entrenado sobre CIC (metadata como fuente de verdad): `fp_benign_cic = 0,0878` (8,8 % de
FP sobre benigno CIC in-distribution), `sep_min = 0,6`, recall por ataque casi perfecto
salvo **Syn = 0,577** (debilidad conocida). El salto FP 23,7 % → 1,1 % entre umbrales 0,5
y 0,6 muestra una masa de flujos en la banda de probabilidad intermedia: el modelo "duda"
ante paquetes sueltos, coherente con un skew de dominio train (floods CIC) ↔ serve
(paquetes unidireccionales).

## 5. La frase honesta (borrador)

> El detector DDoS de aRGus opera tras una compuerta: solo puntúa flujos que el
> clasificador general (level1) ha marcado como ataque. En un replay del botnet Neris
> (320 k paquetes, 19 k flujos), 6 flujos atravesaron la compuerta y el detector no marcó
> ninguno como DDoS. El resultado caracteriza la selectividad de la compuerta ante tráfico
> botnet no-DDoS, no la especificidad aislada de la cabeza. Validar el recall de la cadena
> completa exige tráfico DDoS real atravesando el pipeline íntegro, medición que dejamos
> como trabajo inmediato.