cmake_minimum_required(VERSION 3.10)
project(bolt-tempest-prng VERSION 1.0.0 LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Compiler flags
if(NOT MSVC)
    add_compile_options(-O3 -Wall -Wextra)
    # Platform-specific tuning
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
        add_compile_options(-march=native)
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|ARM64")
        add_compile_options(-march=native)
    endif()
endif()

# Library targets
add_library(adcbolt STATIC src/adcbolt.c)
target_include_directories(adcbolt PUBLIC src)

add_library(tempest STATIC src/tempest_v3.c)
target_include_directories(tempest PUBLIC src)

# Test programs (separate executables — each has its own main())
add_executable(test_bolt test_bolt.c)
target_include_directories(test_bolt PRIVATE src)
target_link_libraries(test_bolt adcbolt)

add_executable(test_tempest test_tempest.c)
target_include_directories(test_tempest PRIVATE src)
target_link_libraries(test_tempest tempest)

# Custom target to run all tests
add_custom_target(test_all
    COMMAND test_bolt
    COMMAND test_tempest
    DEPENDS test_bolt test_tempest
)

# Benchmark
add_executable(benchmark benchmark.c)
target_include_directories(benchmark PRIVATE src)
target_link_libraries(benchmark adcbolt tempest)

# Install
install(TARGETS adcbolt tempest DESTINATION lib)
install(FILES src/adcbolt.h src/tempest_v3.h src/platform.h DESTINATION include)
