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
)
if(ARGUS_VAULT_ENABLED)
    list(APPEND CRYPTO_PROVIDER_SOURCES vault_provider.cpp)
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
)
if(ARGUS_VAULT_ENABLED)
    target_compile_definitions(crypto_provider PUBLIC ARGUS_VAULT_ENABLED)
endif()
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
        crypto_autonomy.h
        crypto_deriver.h
        etcd_registrar.h
        seed_file_provider.h
        include/reason_codes.hpp
        include/sentinel.hpp
        DESTINATION include/vault_client
)
if(ARGUS_VAULT_ENABLED)
    install(FILES vault_provider.h DESTINATION include/vault_client)
endif()

# ── Tests ─────────────────────────────────────────────────────────────────────
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()

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
    endif()
endif()