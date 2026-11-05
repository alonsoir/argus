# libs/protegidos — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 F-B: el verificador del manifiesto firmado de protegidos y los
# rangos, UNO solo para el firewall-acl-agent y el etcd-server (dos verificadores acabarían divergiendo).
# Librería ESTÁTICA a propósito, incluida con add_subdirectory desde cada componente: se compila con las opciones del
# componente (production: -O3 -flto -Werror ...) y queda DENTRO de su binario, cubierta por su firma (ADR-025). Una .so
# en /usr/local/lib se podría cambiar por una que lo acepte todo sin tocar el binario.
# La clave pública NO está aquí: claves_protegidos_compiladas() la define cada componente con sus -D (patrón ADR-025).
# Opción ARGUS_PROTEGIDOS_TESTS (defecto OFF): el firewall la enciende con sus tests; el etcd-server no la repite.
cmake_minimum_required(VERSION 3.16)
project(argus_protegidos LANGUAGES CXX)

find_package(PkgConfig REQUIRED)
pkg_check_modules(PROT_JSONCPP REQUIRED jsoncpp)
# La libsodium compilada desde el código fuente (1.0.19), como plugin-loader (DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001)
find_library(PROT_SODIUM_LIB sodium PATHS /usr/local/lib /usr/lib NO_DEFAULT_PATH)
find_path(PROT_SODIUM_INCLUDE sodium.h PATHS /usr/local/include /usr/include NO_DEFAULT_PATH)
if(NOT PROT_SODIUM_LIB OR NOT PROT_SODIUM_INCLUDE)
    message(FATAL_ERROR "[PROTEGIDOS-CLAVE] libsodium no encontrada (lib=${PROT_SODIUM_LIB} include=${PROT_SODIUM_INCLUDE})")
endif()
message(STATUS "[PROTEGIDOS] libsodium: ${PROT_SODIUM_LIB}")

add_library(argus_protegidos STATIC src/manifiesto.cpp)
set_target_properties(argus_protegidos PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_compile_features(argus_protegidos PUBLIC cxx_std_20)
target_include_directories(argus_protegidos PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../../common/include  # argus/ip_cidr_validator.hpp
        PRIVATE ${PROT_JSONCPP_INCLUDE_DIRS} ${PROT_SODIUM_INCLUDE})
target_link_libraries(argus_protegidos PRIVATE ${PROT_JSONCPP_LIBRARIES} ${PROT_SODIUM_LIB})

option(ARGUS_PROTEGIDOS_TESTS "Tests de libs/protegidos" OFF)
if(ARGUS_PROTEGIDOS_TESTS)
    enable_testing()
    # rangos (header-only, CHECK propio) [PROTEGIDOS-D300]
    add_executable(test_protegidos_rangos tests/test_protegidos_rangos.cpp)
    target_link_libraries(test_protegidos_rangos PRIVATE argus_protegidos)
    add_test(NAME test_protegidos_rangos COMMAND test_protegidos_rangos)
    # verificador (ADR-060 8e.1a): clave desechable generada en el propio test, CHECK propio
    add_executable(test_protegidos_manifiesto tests/test_protegidos_manifiesto.cpp)
    target_include_directories(test_protegidos_manifiesto PRIVATE ${PROT_JSONCPP_INCLUDE_DIRS} ${PROT_SODIUM_INCLUDE})
    target_link_libraries(test_protegidos_manifiesto PRIVATE argus_protegidos ${PROT_JSONCPP_LIBRARIES} ${PROT_SODIUM_LIB})
    add_test(NAME test_protegidos_manifiesto COMMAND test_protegidos_manifiesto)
endif()
