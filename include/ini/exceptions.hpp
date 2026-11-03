/**
 * @file include/ini/exceptions.hpp
 * @brief Domain-specific exception hierarchy for INI/INC/STR parsing
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <stdexcept>

namespace lotm::ini {

    class IniError : public std::runtime_error {
        using std::runtime_error::runtime_error;
    };

    class IniParseError : public IniError {
        using IniError::IniError;
    };

} // namespace lotm::ini
