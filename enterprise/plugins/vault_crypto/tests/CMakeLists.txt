cmake_minimum_required(VERSION 3.16)
project(test_vault_provider LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_library(SODIUM_LIB sodium PATHS /usr/local/lib /usr/lib NO_DEFAULT_PATH)
find_path(SODIUM_INCLUDE sodium.h PATHS /usr/local/include /usr/include NO_DEFAULT_PATH)
find_package(CURL REQUIRED)

# T1-T5 usan VaultProvider directamente (C++ class).
# Compilamos vault_provider.cpp como objeto — no linkeamos el .so.
# T6 hace dlopen del .so ya compilado — prueba el C ABI real.
add_executable(test_vault_provider
    test_vault_provider.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../vault_provider.cpp
)

target_include_directories(test_vault_provider PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/..
    ${CMAKE_CURRENT_SOURCE_DIR}/../../../../common/include
    ${SODIUM_INCLUDE}
    ${CURL_INCLUDE_DIRS}
)

target_link_libraries(test_vault_provider PRIVATE
    ${SODIUM_LIB}
    ${CURL_LIBRARIES}
    dl
)

# Sin -fvisibility=hidden aqui: los simbolos son visibles para el test
target_compile_options(test_vault_provider PRIVATE
    -Wall -Wextra -Wpedantic -Werror
)

enable_testing()
add_test(NAME test_vault_provider COMMAND test_vault_provider)
