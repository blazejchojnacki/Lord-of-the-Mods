/**
 * @file include/big/exceptions.hpp
 * @brief Domain-specific exception hierarchy for BIG archives
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <stdexcept>

namespace lotm::big {

    class BigArchiveError : public std::runtime_error {
        using std::runtime_error::runtime_error;
    };

    class BigFormatError : public BigArchiveError {
        using BigArchiveError::BigArchiveError;
    };

    class BigSecurityError : public BigArchiveError {
        using BigArchiveError::BigArchiveError;
    };

} // namespace lotm::big
