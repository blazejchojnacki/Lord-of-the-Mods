# Gemini Pro 3.1

add_library(lotm_core INTERFACE)

target_include_directories(lotm_core INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(lotm_core INTERFACE cxx_std_20)
