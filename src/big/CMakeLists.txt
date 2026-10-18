# Gemini Pro 3.1

add_library(lotm_big STATIC
    big_unpack.cpp
)

target_include_directories(lotm_big PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
)
