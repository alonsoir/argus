cat << 'EOF'
=== Desde el host, en test-zeromq-docker, rama main al día (6808e847) ===

git checkout -b day204/close-roundtrip-orphaned

git add ml-detector/include/correlation_writer.hpp \
        ml-detector/src/correlation_writer.cpp \
        ml-detector/tests/integration/test_correlation_roundtrip.cpp

git status
# (verificar que solo estos 3 ficheros entran, nada mas)

git commit -m "fix(correlation_writer): Stats::current_final_path — cierra DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001

get_stats().current_file devolvia current_tmp_path_ (el .csv.tmp abierto
ahora mismo), no el path final post-rename. test_correlation_roundtrip
capturaba ese valor mientras el writer seguia vivo; al destruirse, el
propio finalize_segment_locked() renombraba el .tmp -> .csv, dejando el
path capturado inexistente. No era un bug del rename (que funciona bien,
verificado en EMECAS++ DAY 203) sino un campo de observabilidad que no
distinguia 'segmento en curso' de 'segmento cerrado y legible'.

Fix quirurgico:
- Stats: nuevo campo current_final_path junto a current_file (que
  mantiene su semantica: tmp del segmento actualmente abierto).
- get_stats() puebla current_final_path con current_final_path_.
- test_correlation_roundtrip.cpp: los 4 tests leen current_final_path
  en vez de current_file para verificar el segmento cerrado.

Causa raiz confirmada por eliminacion, no supuesta:
1) add_test SI estaba presente en tests/CMakeLists.txt (contra lo que
   registraba la nota DAY203) -- el build dir de la VM tenia cache de
   CMake sin reconfigurar desde que se añadio el bloque.
2) Tras reconfigurar (rm CMakeCache.txt+CMakeFiles && cmake ..), el
   target compilaba y ctest lo listaba, pero las 4 pruebas fallaban RED
   contra el bronce segmentado -- ese RED es el que este commit corrige.

EMECAS++: test_correlation_roundtrip 4/4 PASSED (ctest -R, VM defender).

Authors: Alonso Isidoro Roman + Claude (Anthropic)"

git push -u origin day204/close-roundtrip-orquést...
EOF
Salida

=== Desde el host, en test-zeromq-docker, rama main al día (6808e847) ===

git checkout -b day204/close-roundtrip-orphaned

git add ml-detector/include/correlation_writer.hpp \
        ml-detector/src/correlation_writer.cpp \
        ml-detector/tests/integration/test_correlation_roundtrip.cpp

git status
# (verificar que solo estos 3 ficheros entran, nada mas)

git commit -m "fix(correlation_writer): Stats::current_final_path — cierra DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001

get_stats().current_file devolvia current_tmp_path_ (el .csv.tmp abierto
ahora mismo), no el path final post-rename. test_correlation_roundtrip
capturaba ese valor mientras el writer seguia vivo; al destruirse, el
propio finalize_segment_locked() renombraba el .tmp -> .csv, dejando el
path capturado inexistente. No era un bug del rename (que funciona bien,
verificado en EMECAS++ DAY 203) sino un campo de observabilidad que no
distinguia 'segmento en curso' de 'segmento cerrado y legible'.

Fix quirurgico:
- Stats: nuevo campo current_final_path junto a current_file (que
  mantiene su semantica: tmp del segmento actualmente abierto).
- get_stats() puebla current_final_path con current_final_path_.
- test_correlation_roundtrip.cpp: los 4 tests leen current_final_path
  en vez de current_file para verificar el segmento cerrado.

Causa raiz confirmada por eliminacion, no supuesta:
1) add_test SI estaba presente en tests/CMakeLists.txt (contra lo que
   registraba la nota DAY203) -- el build dir de la VM tenia cache de
   CMake sin reconfigurar desde que se añadio el bloque.
2) Tras reconfigurar (rm CMakeCache.txt+CMakeFiles && cmake ..), el
   target compilaba y ctest lo listaba, pero las 4 pruebas fallaban RED
   contra el bronce segmentado -- ese RED es el que este commit corrige.

EMECAS++: test_correlation_roundtrip 4/4 PASSED (ctest -R, VM defender).

Authors: Alonso Isidoro Roman + Claude (Anthropic)"

git push -u origin day204/close-roundtrip-orquést...