# CONTINUIDAD DAY258 — Housekeeping DDoS CERRADO (generadores + docs sobre-venta amputados). Siguiente: PR a main / Fase 2.

## Estado (medido, verificar al retomar)
    git branch --show-current      # diag/ml-heads
    git log --oneline -6           # HEAD = 708db2d8
    git status -sb                 # limpio salvo untracked conocidos (ver abajo)
Untracked que NO se tocan: evidence/seed-repro/*.json (regla propia),
run_crank_sandbox.sh (reliquia DAY255, muere aparte), "Cierre day255 reparacion ddos.md".

## HECHO DAY258 (cerrado y en origin/diag/ml-heads)
- `7a3d42be` Evidencia de la reparación trackeada: 5 patches (seed/geo/footgun/service-vector)
  + verify_seed_repro.sh. run_crank_sandbox.sh NO trackeado (reliquia DAY255: compara contra
  .hpp borrado, geo=16, coartada del skew pre-pin).
- `008b2d17` AMPUTADO el subsistema de generadores de cabezas (−400 líneas):
  generate_all_models.py + generate_ddos_inline.py + generate_traffic_cpp_forest.py +
  extract_full_forest.py. Desconectados del árbol vivo (0 callers en Makefile/Vagrant/manivela),
  producen cabezas con skew medido, generate_internal_inline.py era fantasma. NO arregla
  cabezas — despeja el terreno para Fase 2.
- `65c279a3` DEBT-ML-DEAD-GENERATORS-RETIRED en backlog.
- `c0a9d9aa` RETIRADO el nido documental que sobre-vendía las 4 cabezas (−888 líneas):
  README de scripts, TECHNICAL_INTEGRATION_GUIDE, INSTRUCCIONES_CLAUDE_INTEGRACION,
  TechnicalDocumentation.py. "BREAKTHROUGH / accuracy 1.0000" sobre cabezas rotas + geo
  documentada como feature viva del DDoS (ya amputada). Doc se recrea acoplada a cada
  cabeza fiable en Fase 2, NO antes.
- `708db2d8` DEBT-DDOS-DOCS-STALE-10FEAT CERRADA (test grep=0; los hits murieron con los ficheros).

## Verificado hoy (tranquiliza, no re-medir)
README raíz del proyecto NO sobre-vende — lenguaje del paper honesto: subconjunto curado
(646 flujos maliciosos CTU-13 Neris), F1=0.9985, "not the operational picture, stated as such".
El veneno de sobre-venta estaba contenido en ml-training/scripts/, ya retirado.

## Claim del paper (acotado, honesto — NO sobre-vender)
DDoS reproducible byte a byte FROM-SCRATCH (box debian + 8 versiones pinneadas, DAY257).
Censo (geo=0, 9 features, 240/340) = invariante PORTABLE que sobrevive al drift de sha.
NO afirmado: detector DDoS útil sobre Neris (Betas sintéticas, accuracy 1.0 = sintético = Fase 2).
El pin NO va al main.tex (paper v25 ya en arXiv; material de Fase 2, vive en la rama).

## PENDIENTE (barato primero; en orden)
1. **Copias .hpp duplicadas en internal_traffic/ + external_traffic/** (mismo patrón que
   DEBT-DDOS-HPP-COPIA-DUPLICADA, cerrada solo para DDoS). Medir con
   `git ls-files 'ml-training/scripts/**/*_trees_inline.hpp'` y barrer/registrar.
2. **PR de diag/ml-heads a main (CABEZA FRESCA, no a horas malas).** La rama lleva la
   reparación completa del skew (footgun+geo+propagación+contrato-servicio+reproducibilidad+pin)
   + amputación de generadores y docs. Gate: emecas+++ VERDE from-scratch. main PROTEGIDA (PR only, GH013).
3. **Fase 2 DDoS (LA P0 real, investigación, batalla larga).** Entrenar la cabeza sobre features
   REALES + labels Neris por el MISMO extractor (no Betas sintéticas). Único camino de
   "reproducible" → "detecta". Hermana: DEBT-RANSOMWARE-ML-HEAD-INERT-001.

## Invariantes
main PROTEGIDA (PR only). Un commit una idea. git grep o fichero concreto (NUNCA grep -rn desde raíz).
Comandos de salida grande en bloques separados. add explícito por fichero, nunca -u/-a.
La manivela gira DENTRO de la VM (deps pinneadas ahí). PUSH desde el HOST (macOS), no desde la VM.
sed BSD/osx: verificar con grep -c antes y después, Y confirmar el NOMBRE del fichero destino
(hoy un typo .mdd tragó un sed en silencio). Medir, no asumir.

## Nota personal (no borrar)
Alonso atiende a su padre en el hospital estos días; avanza en ratos sueltos a horas malas.
aRGus aguanta el ritmo lento — Via Appia, décadas. No forzar. Piano piano si arriva lontano.
