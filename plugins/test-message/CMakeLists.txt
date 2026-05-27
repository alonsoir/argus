cmake_minimum_required(VERSION 3.16)
project(plugin_test_message VERSION 0.1.0 LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_library(PLUGIN_LOADER_LIB plugin_loader
    PATHS /usr/local/lib
    NO_DEFAULT_PATH
)
find_path(PLUGIN_LOADER_INCLUDE plugin_loader/plugin_api.h
    PATHS /usr/local/include
    NO_DEFAULT_PATH
)

add_library(plugin_test_message SHARED plugin_test_message.cpp)
target_include_directories(plugin_test_message PRIVATE ${PLUGIN_LOADER_INCLUDE})
target_compile_options(plugin_test_message PRIVATE -Wall -Wextra)

install(TARGETS plugin_test_message
    LIBRARY DESTINATION /usr/lib/ml-defender/plugins)
