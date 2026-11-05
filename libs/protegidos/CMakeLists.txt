# libs/protegidos — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 F-B: el verificador del manifiesto firmado de protegidos y los
# rangos, UNO solo para el firewall-acl-agent y el etcd-server (dos verificadores acabarían divergiendo).
# Librería ESTÁTICA a propósito, incluida con add_subdirectory desde cada componente: se compila con las opciones del
# componente (production: -O3 -flto -Werror ...) y queda DENTRO de su binario, cubierta por su firma (ADR-025). Una .so
# en /usr/local/lib se podría cambiar por una que lo acepte todo sin tocar el binario.
# La clave pública va en un objetivo aparte, argus_protegidos_clave (src/claves.cpp con los -D de la clave), que
# enlazan el firewall-acl-agent y el etcd-server (ADR-060 F-A: el etcd-server verifica con la misma clave compilada).
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

# ============================================================================
# [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D3 / D-E: clave PÚBLICA del manifiesto de protegidos (Vault transit del
# hospital), compilada en dos ranuras (patrón ADR-025). No es un secreto. Sin la ranura actual NO se compila: no hay
# defecto sano para una clave de confianza.
#   -DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX=<64 hex>     (producción: la pasa Jenkins)
#   -DARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX=<64 hex>  (solo durante una rotación; si no, vacía)
# Sin -D se leen de /etc/ml-defender/firewall-acl-agent/protegidos_pubkey_{actual,siguiente}.hex; en el lab los
# trae de la VM etcd `make protegidos-pubkey` (bootstrap [4b/8]). En el lab el firewall-acl-agent y el etcd-server se
# compilan los dos en el defender: leen el mismo fichero (ADR-060 F-A).
# ============================================================================
set(ARGUS_PROTEGIDOS_PUBKEY_DIR /etc/ml-defender/firewall-acl-agent)
foreach(RANURA ACTUAL SIGUIENTE)
    string(TOLOWER ${RANURA} ranura)
    set(_fich ${ARGUS_PROTEGIDOS_PUBKEY_DIR}/protegidos_pubkey_${ranura}.hex)
    if(DEFINED ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX)
        set(_origen "-D")
    elseif(EXISTS ${_fich})
        file(READ ${_fich} _v)
        string(STRIP "${_v}" _v)
        set(ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX "${_v}")
        set(_origen "fichero ${_fich}")
    else()
        set(ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX "")
        set(_origen "ausente: ni -D ni ${_fich}")
    endif()
    set(_v "${ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX}")
    if(RANURA STREQUAL "ACTUAL" AND _v STREQUAL "")
        message(FATAL_ERROR "[PROTEGIDOS-CLAVE] falta la clave pública ACTUAL del manifiesto de protegidos (${_origen}). "
                            "Lab: make protegidos-pubkey desde el Mac. Producción: -DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX=<64 hex>")
    endif()
    string(LENGTH "${_v}" _n)
    if(NOT _v STREQUAL "" AND (NOT _n EQUAL 64 OR NOT _v MATCHES "^[0-9a-f]+$"))
        message(FATAL_ERROR "[PROTEGIDOS-CLAVE] clave pública ${RANURA} mal formada (${_origen}): 64 caracteres hex en minúsculas")
    endif()
    if(_v STREQUAL "")
        message(STATUS "[PROTEGIDOS-CLAVE] ${RANURA}: ninguna (${_origen})")
    else()
        string(SUBSTRING "${_v}" 0 16 _ini)
        message(STATUS "[PROTEGIDOS-CLAVE] ${RANURA}: ${_ini}... (${_origen})")
    endif()
endforeach()

add_library(argus_protegidos_clave STATIC src/claves.cpp)
set_target_properties(argus_protegidos_clave PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_link_libraries(argus_protegidos_clave PUBLIC argus_protegidos)
target_compile_definitions(argus_protegidos_clave PRIVATE
        ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX="${ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX}"
        ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX="${ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX}")

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
    # la clave compilada es la de CMake, en las dos ranuras
    add_executable(test_protegidos_claves tests/test_protegidos_claves.cpp)
    target_include_directories(test_protegidos_claves PRIVATE ${PROT_SODIUM_INCLUDE})
    target_link_libraries(test_protegidos_claves PRIVATE argus_protegidos_clave ${PROT_SODIUM_LIB})
    target_compile_definitions(test_protegidos_claves PRIVATE
            ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX="${ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX}"
            ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX="${ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX}")
    add_test(NAME test_protegidos_claves COMMAND test_protegidos_claves)
endif()
