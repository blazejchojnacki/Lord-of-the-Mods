/**
 * @file src/ini/include_resolver.cpp
 * @brief Implementation of chroot-jailed #include path validation and resolution.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "parser_utils.hpp"
#include "ini/parser.hpp"
#include <core/path_utils.hpp>

#include <filesystem>
#include <system_error>

namespace lotm::ini {

    namespace {

        using lotm::core::utf8_to_path;

        inline std::string path_to_utf8(const std::filesystem::path& p) {
            return lotm::core::to_utf8(p);
        }

        [[nodiscard]] bool is_path_within_root(
            const std::filesystem::path& candidate,
            const std::filesystem::path& root
        ) {
            const auto cand_it_end = candidate.end();
            const auto root_it_end = root.end();

            auto cand_it = candidate.begin();
            auto root_it = root.begin();

            while (root_it != root_it_end) {
                if (cand_it == cand_it_end) {
                    return false;
                }
                if (*cand_it != *root_it) {
                    // Case-insensitive component comparison on Windows. Does not need the if on POSIX
                    if (!detail::iequals_ascii(path_to_utf8(*cand_it), path_to_utf8(*root_it))) {
                        return false;
                    }
                }
                ++cand_it;
                ++root_it;
            }
            return true;
        }

    } // namespace

    std::filesystem::path validate_include(
        const IncludeNode& node,
        const std::filesystem::path& current_file,
        const std::filesystem::path& virtual_root
    ) {
        const std::string clean = node.clean_path();
        const std::filesystem::path target_rel = utf8_to_path(clean);

        std::error_code ec;
        const std::filesystem::path canon_root = std::filesystem::weakly_canonical(virtual_root, ec);
        if (ec) {
            throw IniParseError("Invalid virtual root: " + path_to_utf8(virtual_root));
        }

        const std::filesystem::path local_candidate = std::filesystem::weakly_canonical(
            current_file.parent_path() / target_rel, ec
        );
        const bool local_in_root = !ec && is_path_within_root(local_candidate, canon_root);
        if (local_in_root && std::filesystem::is_regular_file(local_candidate, ec)) {
            return local_candidate;
        }

        const std::filesystem::path root_candidate = std::filesystem::weakly_canonical(
            canon_root / target_rel, ec
        );
        const bool root_in_root = !ec && is_path_within_root(root_candidate, canon_root);
        if (root_in_root && std::filesystem::is_regular_file(root_candidate, ec)) {
            return root_candidate;
        }

        if (!local_in_root && !root_in_root) {
            throw IniParseError(
                "Security violation: " + node.raw_path + " escapes virtual root " + path_to_utf8(virtual_root)
            );
        }

        throw IniParseError("Include file not found: " + node.raw_path);
    }

} // namespace lotm::ini
