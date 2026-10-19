// Gemini Pro 3.1

#pragma once

#include <bit>
#include <concepts>
#include <cstdint>

namespace lotm::core {

    template <std::integral T>
    [[nodiscard]] constexpr T byteswap(T value) noexcept {
        if constexpr (sizeof(T) == 1) {
            return value;
        }
        else if constexpr (sizeof(T) == 2) {
            auto unsigned_val = static_cast<uint16_t>(value);
            return static_cast<T>((unsigned_val << 8) | (unsigned_val >> 8));
        }
        else if constexpr (sizeof(T) == 4) {
            auto unsigned_val = static_cast<uint32_t>(value);
            return static_cast<T>(
                ((unsigned_val & 0x000000FFu) << 24) |
                ((unsigned_val & 0x0000FF00u) << 8) |
                ((unsigned_val & 0x00FF0000u) >> 8) |
                ((unsigned_val & 0xFF000000u) >> 24)
                );
        }
        else if constexpr (sizeof(T) == 8) {
            auto unsigned_val = static_cast<uint64_t>(value);
            return static_cast<T>(
                ((unsigned_val & 0x00000000000000FFull) << 56) |
                ((unsigned_val & 0x000000000000FF00ull) << 40) |
                ((unsigned_val & 0x0000000000FF0000ull) << 24) |
                ((unsigned_val & 0x00000000FF000000ull) << 8) |
                ((unsigned_val & 0x000000FF00000000ull) >> 8) |
                ((unsigned_val & 0x0000FF0000000000ull) >> 24) |
                ((unsigned_val & 0x00FF000000000000ull) >> 40) |
                ((unsigned_val & 0xFF00000000000000ull) >> 56)
                );
        }
    }

    template <std::integral T>
    [[nodiscard]] constexpr T from_big_endian(T value) noexcept {
        if constexpr (std::endian::native == std::endian::little) {
            return byteswap(value);
        }
        else {
            return value;
        }
    }

    template <std::integral T>
    [[nodiscard]] constexpr T to_big_endian(T value) noexcept {
        return from_big_endian(value);
    }

} // namespace lotm::core
