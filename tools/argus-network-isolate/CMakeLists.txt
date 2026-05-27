cmake_minimum_required(VERSION 3.20)
project(argus-network-isolate VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "CXX Flags: ${CMAKE_CXX_FLAGS}")

find_package(spdlog REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(Threads REQUIRED)

add_executable(argus-network-isolate
    main.cpp
    isolate.cpp
)

target_include_directories(argus-network-isolate
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_options(argus-network-isolate
    PRIVATE
    -Wall -Wextra -Wpedantic
)

target_link_libraries(argus-network-isolate
    PRIVATE
    spdlog::spdlog
    nlohmann_json::nlohmann_json
    Threads::Threads
)

install(TARGETS argus-network-isolate RUNTIME DESTINATION /usr/local/bin)

message(STATUS "========================================")
message(STATUS "argus-network-isolate — ADR-042 IRP")
message(STATUS "========================================")
# ── Unit tests (ADR-042 DAY 143) ─────────────────────────────────────────
add_executable(test_isolate_config
    test_isolate_config.cpp
    isolate.cpp
)
target_include_directories(test_isolate_config PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(test_isolate_config PRIVATE spdlog::spdlog nlohmann_json::nlohmann_json Threads::Threads)
enable_testing()
add_test(NAME test_isolate_config COMMAND test_isolate_config)

