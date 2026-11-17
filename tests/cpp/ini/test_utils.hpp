/**
 * @file tests/cpp/ini/test_utils.hpp
 * @brief Common test fixtures and utilities for lotm::ini Catch2 test suite.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <atomic>
#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <string>
#include <string_view>

#ifdef _WIN32
#include <share.h>
#endif

namespace lotm::ini::testing {

    /**
     * @brief RAII temporary directory fixture for deterministic filesystem tests.
     */
    class TempDirFixture {
    public:
        TempDirFixture() {
            static std::atomic<std::uint64_t> counter{ 0 };
            const auto now = std::chrono::steady_clock::now().time_since_epoch().count();
            const std::string dir_name = "lotm_ini_test_" + std::to_string(now) + "_" + std::to_string(++counter);
            root_ = std::filesystem::temp_directory_path() / dir_name;
            std::filesystem::create_directories(root_);
        }

        ~TempDirFixture() {
            std::error_code ec;
            std::filesystem::remove_all(root_, ec);
        }

        TempDirFixture(const TempDirFixture&) = delete;
        TempDirFixture& operator=(const TempDirFixture&) = delete;

        [[nodiscard]] const std::filesystem::path& root() const noexcept { return root_; }

        [[nodiscard]] std::filesystem::path write_file(std::string_view rel_path, std::string_view content) const {
            const std::u8string_view u8_rel(
                reinterpret_cast<const char8_t*>(rel_path.data()),
                rel_path.size()
            );
            const std::filesystem::path full_path = root_ / std::filesystem::path(u8_rel);
            std::filesystem::create_directories(full_path.parent_path());
            std::ofstream out(full_path, std::ios::binary);
            out.write(content.data(), static_cast<std::streamsize>(content.size()));
            out.close();
            return full_path;
        }

    private:
        std::filesystem::path root_;
    };

#ifdef _WIN32
    /**
     * @brief RAII exclusive file lock using Windows _fsopen(_SH_DENYRW) to force deterministic I/O read failures.
     */
    class ScopedExclusiveFileLock {
    public:
        explicit ScopedExclusiveFileLock(const std::filesystem::path& path)
            : handle_(_fsopen(path.string().c_str(), "rb", _SH_DENYRW)) {
        }

        ~ScopedExclusiveFileLock() {
            if (handle_ != nullptr) {
                std::fclose(handle_);
            }
        }

        ScopedExclusiveFileLock(const ScopedExclusiveFileLock&) = delete;
        ScopedExclusiveFileLock& operator=(const ScopedExclusiveFileLock&) = delete;

        [[nodiscard]] bool is_locked() const noexcept { return handle_ != nullptr; }

    private:
        std::FILE* handle_{ nullptr };
    };
#endif

} // namespace lotm::ini::testing
