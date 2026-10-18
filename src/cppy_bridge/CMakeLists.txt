# Gemini Pro 3.1

nanobind_add_module(lotm
    NB_STATIC
    main.cpp
    bind_big.cpp
)

target_include_directories(lotm PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
)

target_link_libraries(lotm PRIVATE lotm_big)
