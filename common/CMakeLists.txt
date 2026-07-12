cmake_minimum_required(VERSION 3.16)
project(vault_client VERSION 1.0.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── Opciones ──────────────────────────────────────────────────────────────────
# ARGUS_VAULT_ENABLED: único separador compile-time entre community y enterprise.
# OFF → SeedFileProvider  (community, default)
# ON  → VaultProvider     (enterprise)
option(ARGUS_VAULT_ENABLED "Enable Vault crypto provider (enterprise)" OFF)

# ── Dependencias ──────────────────────────────────────────────────────────────
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBSODIUM REQUIRED libsodium)
find_package(CURL REQUIRED)
find_package(OpenSSL REQUIRED)
pkg_check_modules(ZMQ REQUIRED libzmq)

# seed-client — requerido por SeedFileProvider (ambas compilaciones)
find_library(SEED_CLIENT_LIB seed_client
        PATHS /usr/local/lib
        REQUIRED
)
find_path(SEED_CLIENT_INCLUDE seed_client/seed_client.hpp
        PATHS /usr/local/include
        REQUIRED
)

# ── vault_client (sin cambios) ────────────────────────────────────────────────
add_library(vault_client SHARED
        vault_client.cpp
        crypto_deriver.cpp
        etcd_registrar.cpp
        vault_transport.cpp
        cache_manager.cpp
)
target_include_directories(vault_client
        PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
        PRIVATE
        ${LIBSODIUM_INCLUDE_DIRS}
        ${CURL_INCLUDE_DIRS}
)
target_link_libraries(vault_client
        PUBLIC
        ${LIBSODIUM_LIBRARIES}
        ${CURL_LIBRARIES}
)
set_target_properties(vault_client PROPERTIES
        VERSION   ${PROJECT_VERSION}
        SOVERSION 1
)

# ── crypto_provider (nuevo — ADR-044 DAY 151) ─────────────────────────────────
set(CRYPTO_PROVIDER_SOURCES
        crypto_provider.cpp
        seed_file_provider.cpp
        autonomy_publisher.cpp
        http_etcd_registrar.cpp
        crypto_epoch_coordinator.cpp
)
if(ARGUS_VAULT_ENABLED)
    list(APPEND CRYPTO_PROVIDER_SOURCES vault_provider.cpp)

    # NTP-1/2/3 — DEBT-ARGUSPP-NTP-001 (DAY 167)
    add_executable(test_ntp_health_check
            tests/test_ntp_health_check.cpp
            ntp_health_check.cpp
    )
    target_include_directories(test_ntp_health_check PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
    )
    target_link_libraries(test_ntp_health_check PRIVATE
            ntp_utils
    )
    add_test(NAME test_ntp_health_check COMMAND test_ntp_health_check)
    set_tests_properties(test_ntp_health_check PROPERTIES TIMEOUT 10)
endif()

add_library(crypto_provider SHARED
        ${CRYPTO_PROVIDER_SOURCES}
)
target_include_directories(crypto_provider
        PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
        PRIVATE
        ${LIBSODIUM_INCLUDE_DIRS}
        ${SEED_CLIENT_INCLUDE}
)
target_link_libraries(crypto_provider
        PUBLIC
        vault_client
        ${SEED_CLIENT_LIB}
        ${LIBSODIUM_LIBRARIES}
        ${ZMQ_LIBRARIES}
        ${CURL_LIBRARIES}
        OpenSSL::SSL
        OpenSSL::Crypto
)
if(ARGUS_VAULT_ENABLED)
    target_compile_definitions(crypto_provider PUBLIC ARGUS_VAULT_ENABLED)
endif()
target_compile_definitions(crypto_provider PUBLIC CPPHTTPLIB_OPENSSL_SUPPORT)
set_target_properties(crypto_provider PROPERTIES
        VERSION   ${PROJECT_VERSION}
        SOVERSION 1
)

# Resumen de compilación
message(STATUS "╔══════════════════════════════════════════════╗")
message(STATUS "║  crypto_provider — ADR-044 DAY 151           ║")
message(STATUS "╠══════════════════════════════════════════════╣")
if(ARGUS_VAULT_ENABLED)
    message(STATUS "║  Provider: VaultProvider  (enterprise)       ║")
else()
    message(STATUS "║  Provider: SeedFileProvider (community)      ║")
endif()
message(STATUS "╚══════════════════════════════════════════════╝")

# ── Instalación ───────────────────────────────────────────────────────────────
install(TARGETS vault_client
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
)
install(TARGETS crypto_provider
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
)
install(FILES
        vault_client.h
        vault_types.h
        vault_transport.h
        cache_manager.h
        crypto_provider.h
        crypto_provider_handle.hpp
        autonomy_publisher.h
        crypto_autonomy.h
        crypto_deriver.h
        etcd_registrar.h
        http_etcd_registrar.h
        crypto_epoch_coordinator.h
        seed_file_provider.h
        autonomy_state_writer.h
        include/reason_codes.hpp
        include/sentinel.hpp
        DESTINATION include/vault_client
)
if(ARGUS_VAULT_ENABLED)
    install(FILES vault_provider.h DESTINATION include/vault_client)
endif()

# ── ntp_utils (ADR-046 P0 — DAY 167) ─────────────────────────────────────────
# Librería STATIC sin dependencias externas.
# Cualquier componente puede linkearla sin arrastrar crypto/ZMQ/sodium.
add_library(ntp_utils STATIC
        ntp_health_check.cpp
)
target_include_directories(ntp_utils
        PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)
set_target_properties(ntp_utils PROPERTIES
        POSITION_INDEPENDENT_CODE ON
)
install(TARGETS ntp_utils ARCHIVE DESTINATION lib)
install(FILES include/ntp_health_check.hpp DESTINATION include/vault_client)

# ── Tests ─────────────────────────────────────────────────────────────────────
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()

# ── DAY 217 — DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001 ────────────────────────────
# Ancla el orden de las 23 features de L1 al contrato que el ONNX espera.
add_executable(test_l1_feature_contract tests/test_l1_feature_contract.cpp)
target_compile_definitions(test_l1_feature_contract PRIVATE
    ARGUS_L1_CONTRACT_JSON="${CMAKE_CURRENT_SOURCE_DIR}/../sniffer/config/features/rf_23_features.json"
)
add_test(NAME test_l1_feature_contract COMMAND test_l1_feature_contract)
# Test vault_client existente (sin cambios)
add_executable(test_crypto_deriver tests/test_crypto_deriver.cpp crypto_deriver.cpp)
target_include_directories(test_crypto_deriver PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${SODIUM_INCLUDE_DIRS})
target_link_libraries(test_crypto_deriver PRIVATE sodium)
add_test(NAME test_crypto_deriver COMMAND test_crypto_deriver)

add_executable(test_etcd_registrar tests/test_etcd_registrar.cpp etcd_registrar.cpp)
target_include_directories(test_etcd_registrar PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(test_etcd_registrar PRIVATE vault_client)
add_test(NAME test_etcd_registrar COMMAND test_etcd_registrar)

add_executable(test_vault_client
            tests/test_vault_client.cpp
    )
    target_include_directories(test_vault_client PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${LIBSODIUM_INCLUDE_DIRS}
            ${CURL_INCLUDE_DIRS}
    )
    target_link_libraries(test_vault_client PRIVATE
            vault_client
    )
    add_test(NAME test_vault_client COMMAND test_vault_client)

    # Tests crypto_provider — community (VAULT_ENABLED=OFF)
    add_executable(test_crypto_provider_community
            tests/test_crypto_provider.cpp
    )
    target_include_directories(test_crypto_provider_community PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${SEED_CLIENT_INCLUDE}
    )
    target_link_libraries(test_crypto_provider_community PRIVATE
            crypto_provider
            ${LIBSODIUM_LIBRARIES}
    )
    add_test(NAME test_crypto_provider_community
            COMMAND test_crypto_provider_community)
    # Test CryptoAutonomyStateMachine — sin red, sin Vault (DAY 152)
    add_executable(test_crypto_autonomy
            tests/test_crypto_autonomy.cpp
    )
    target_include_directories(test_crypto_autonomy PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
    )
    target_link_libraries(test_crypto_autonomy PRIVATE
            crypto_provider
    )
    add_test(NAME test_crypto_autonomy
            COMMAND test_crypto_autonomy)

    # test_autonomy_publisher — DEBT-AUTONOMY-ZMQ-EVENTS-001 (DAY 155)
    add_executable(test_autonomy_publisher
            tests/test_autonomy_publisher.cpp
            autonomy_publisher.cpp
    )
    target_include_directories(test_autonomy_publisher PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${ZMQ_INCLUDE_DIRS}
    )
    target_link_libraries(test_autonomy_publisher PRIVATE
            crypto_provider
            ${ZMQ_LIBRARIES}
    )
    add_test(NAME test_autonomy_publisher COMMAND test_autonomy_publisher)
    set_tests_properties(test_autonomy_publisher PROPERTIES TIMEOUT 30)
    # IVaultTransport tests (ADR-045 DAY 153)
    add_executable(test_vault_transport
            tests/test_vault_transport.cpp
            vault_transport.cpp
    )
    target_include_directories(test_vault_transport PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${CURL_INCLUDE_DIRS}
    )
    target_link_libraries(test_vault_transport PRIVATE
            vault_client
            ${CURL_LIBRARIES}
    )
    add_test(NAME test_vault_transport COMMAND test_vault_transport)

    # ICacheManager tests (ADR-045 DAY 153)
    add_executable(test_cache_manager
            tests/test_cache_manager.cpp
            cache_manager.cpp
    )
    target_include_directories(test_cache_manager PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${LIBSODIUM_INCLUDE_DIRS}
    )
    target_link_libraries(test_cache_manager PRIVATE
            vault_client
    )
    add_test(NAME test_cache_manager COMMAND test_cache_manager)
    # Tests crypto_provider — enterprise (VAULT_ENABLED=ON, solo si aplica)
    if(ARGUS_VAULT_ENABLED)
        add_executable(test_crypto_provider_enterprise
                tests/test_crypto_provider.cpp
        )
        target_include_directories(test_crypto_provider_enterprise PRIVATE
                ${CMAKE_CURRENT_SOURCE_DIR}
                ${SEED_CLIENT_INCLUDE}
        )
        target_compile_definitions(test_crypto_provider_enterprise
                PRIVATE ARGUS_VAULT_ENABLED)
        target_link_libraries(test_crypto_provider_enterprise PRIVATE
                crypto_provider
                ${LIBSODIUM_LIBRARIES}
        )
        add_test(NAME test_crypto_provider_enterprise
                COMMAND test_crypto_provider_enterprise)
        # NTP-1/2/3 — DEBT-ARGUSPP-NTP-001 (DAY 167)
    endif()

    # test_autonomy_state_writer — DEBT-AUTONOMY-STATE-PERSISTENCE-001 (DAY 157)
    add_executable(test_autonomy_state_writer
            tests/test_autonomy_state_writer.cpp
    )
    target_include_directories(test_autonomy_state_writer PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${LIBSODIUM_INCLUDE_DIRS}
            ${nlohmann_json_INCLUDE_DIRS}
    )
    target_link_libraries(test_autonomy_state_writer PRIVATE
            crypto_provider
            ${LIBSODIUM_LIBRARIES}
    )
    add_test(NAME test_autonomy_state_writer COMMAND test_autonomy_state_writer)

    # test_crypto_provider_handle — BACKLOG-CRYPTO-HOT-RELOAD-001 (DAY 163)
    add_executable(test_crypto_provider_handle
            tests/test_crypto_provider_handle.cpp
    )
    target_include_directories(test_crypto_provider_handle PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${LIBSODIUM_INCLUDE_DIRS}
    )
    target_link_libraries(test_crypto_provider_handle PRIVATE
            crypto_provider
            ${LIBSODIUM_LIBRARIES}
    )
    add_test(NAME test_crypto_provider_handle COMMAND test_crypto_provider_handle)

    # DEBT-WIRE-PROTOCOL-TEST-001 (DAY 161)
    # Verifica simetría del protocolo binario LZ4 LE uint32_t
    # entre ml-detector (serializador) y firewall-acl-agent (deserializador)
    add_executable(test_wire_protocol
            tests/test_wire_protocol.cpp
    )
    target_include_directories(test_wire_protocol PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
    )
    target_link_libraries(test_wire_protocol PRIVATE
            lz4
    )
    add_test(NAME test_wire_protocol COMMAND test_wire_protocol)

    # BACKLOG-CRYPTO-EPOCH-001 — DAY 164
    add_executable(test_crypto_epoch_coordinator
            tests/test_crypto_epoch_coordinator.cpp
            crypto_epoch_coordinator.cpp
            http_etcd_registrar.cpp
    )
    target_include_directories(test_crypto_epoch_coordinator PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${CURL_INCLUDE_DIRS}
    )
    target_link_libraries(test_crypto_epoch_coordinator PRIVATE
            vault_client
            ${CURL_LIBRARIES}
    )
    add_test(NAME test_crypto_epoch_coordinator COMMAND test_crypto_epoch_coordinator)

    # BACKLOG-CRYPTO-E2E-ROTATION-001 — DAY 165
    # Ciclo completo: FakeEtcdServer → CryptoEpochCoordinator → handle.reload()
    #                 → encrypt(epoch_id) → decrypt_v2 → epoch_id correcto
    add_executable(test_e2e_rotation
            tests/test_e2e_rotation.cpp
            crypto_epoch_coordinator.cpp
            http_etcd_registrar.cpp
    )
    target_include_directories(test_e2e_rotation PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${CURL_INCLUDE_DIRS}
            ${LIBSODIUM_INCLUDE_DIRS}
    )
    target_link_libraries(test_e2e_rotation PRIVATE
            vault_client
            crypto_transport
            ${SEED_CLIENT_LIB}
            ${CURL_LIBRARIES}
            ${LIBSODIUM_LIBRARIES}
    )
    add_test(NAME test_e2e_rotation COMMAND test_e2e_rotation)

    # NTP-1/2/3 — DEBT-ARGUSPP-NTP-001 (DAY 167)
endif()

# [DAY182] -UNDEBUG: assert() vivo en production (regla DAY 144)
# Reactiva assert() bajo -DNDEBUG en estos test standalone.
# if(TARGET) protege ante targets en bloques condicionales desactivados.
if(TARGET test_crypto_deriver)
    target_compile_options(test_crypto_deriver PRIVATE -UNDEBUG)
endif()
if(TARGET test_etcd_registrar)
    target_compile_options(test_etcd_registrar PRIVATE -UNDEBUG)
endif()
if(TARGET test_vault_client)
    target_compile_options(test_vault_client PRIVATE -UNDEBUG)
endif()
if(TARGET test_crypto_provider_community)
    target_compile_options(test_crypto_provider_community PRIVATE -UNDEBUG)
endif()
if(TARGET test_autonomy_publisher)
    target_compile_options(test_autonomy_publisher PRIVATE -UNDEBUG)
endif()
if(TARGET test_crypto_provider_enterprise)
    target_compile_options(test_crypto_provider_enterprise PRIVATE -UNDEBUG)
endif()
if(TARGET test_wire_protocol)
    target_compile_options(test_wire_protocol PRIVATE -UNDEBUG)
endif()

