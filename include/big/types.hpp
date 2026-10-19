// Gemini Pro 3.1

#pragma once

#include <cstdint>
#include <string>
#include <string_view>

namespace lotm::big {

    inline constexpr std::string_view BIG4_MAGIC = "BIG4";
    inline constexpr uint32_t HEADER_BASE_SIZE = 16;
    inline constexpr uint32_t EA_PADDING_SIZE = 8;
    inline constexpr std::string_view EA_PADDING_TAG = "L219    ";

    struct BigEntry {
        uint32_t offset{ 0 };
        uint32_t size{ 0 };
        std::string name;
    };

} // namespace lotm::big
