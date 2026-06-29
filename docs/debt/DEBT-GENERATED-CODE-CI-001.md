# DEBT-GENERATED-CODE-CI-001 — CI Gate para Código Generado (protobuf, XGBoost)

**Estado:** BACKLOG
**Prioridad:** P2 — post-FEDER
**Bloqueado por:** servidor CI/CD disponible
**Estimación:** 1 sesión
**Fecha de registro:** 2026-05-03 (DAY 140)

## Descripción

Los ficheros generados (`network_security.pb.cc`, `internal_detector.cpp`) tienen
warnings suprimidos por fichero en CMake. Si se regeneran con una nueva versión
de protoc o del exportador XGBoost, pueden aparecer warnings nuevos que rompan
el build silenciosamente con `-Werror` activo.

## Implementación

### Target Makefile

```makefile
check-generated:
    @echo "Verifying generated code compiles clean with -Werror..."
    @make generate-protobuf
    $(CXX) -std=c++20 -Werror -Wall -Wextra -c \
        ml-detector/src/network_security.pb.cc \
        -o /tmp/pb_test.o 2>&1 | \
        grep -i "error|warning" && { echo "FAIL"; exit 1; } || echo "PASS"
```

### Jenkinsfile (semanal)

```groovy
triggers { cron('0 4 * * 1') }  // Lunes 4AM
stage('Generated Code Check') {
    steps {
        sh 'make check-generated'
    }
}
```

## Mitigación actual

Comentario en el target `proto` del Makefile advirtiendo que tras regenerar
hay que verificar `make all 2>&1 | grep -c warning:` = 0.

## Test de cierre

`make check-generated` verde tras regenerar protobuf con nueva versión de protoc.

## Referencias

- Consejo DAY 140 (mayoría): supresión + CI gate obligatorio
- `ml-detector/CMakeLists.txt` — supresiones activas para protobuf y XGBoost
