/**
 * @file include/big/big_pack.hpp
 * @brief Declaration of BIG packing object
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <filesystem>

namespace lotm::big {

    class BigPacker {
    public:
        static void pack_from_directory(const std::filesystem::path& source_dir, const std::filesystem::path& output_file);
    };

} // namespace lotm::big
