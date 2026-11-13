/**
 * @file tools/ini_validator.cpp
 * @brief Standalone CLI verification tool to batch-test lotm::ini on real SAGE datasets.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "ini/parser.hpp"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace fs = std::filesystem;

static bool is_config_file(const fs::path& path) {
    const std::string ext = path.extension().string();
    return lotm::ini::detail::iequals_ascii(ext, ".ini") ||
        lotm::ini::detail::iequals_ascii(ext, ".inc") ||
        lotm::ini::detail::iequals_ascii(ext, ".str");
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: lotm_ini_validator <path-to-ini-folder-or-file> [--strict] [--check-roundtrip] [-o <output-file>]\n";
        return EXIT_FAILURE;
    }

    const fs::path target{ argv[1] };
    bool strict = false;
    bool check_roundtrip = false;
    fs::path output_path;

    for (int i = 2; i < argc; ++i) {
        const std::string_view arg{ argv[i] };
        if (arg == "--strict") {
            strict = true;
        }
        else if (arg == "--check-roundtrip") {
            check_roundtrip = true;
        }
        else if ((arg == "-o" || arg == "--output") && (i + 1 < argc)) {
            output_path = argv[++i];
        }
    }

    if (!fs::exists(target)) {
        std::cerr << "Error: Target path does not exist: " << target << '\n';
        return EXIT_FAILURE;
    }

    std::vector<fs::path> files;
    if (fs::is_regular_file(target)) {
        files.push_back(target);
    }
    else {
        std::error_code ec;
        for (const auto& entry : fs::recursive_directory_iterator(
            target,
            fs::directory_options::skip_permission_denied,
            ec
        )) {
            if (entry.is_regular_file(ec) && is_config_file(entry.path())) {
                files.push_back(entry.path());
            }
        }
    }

    std::ranges::sort(files);

    std::cout << "Testing lotm::ini against " << files.size() << " files...\n";

    std::size_t passed = 0;
    std::size_t failed = 0;
    std::size_t roundtrip_mismatches = 0;
    std::vector<std::pair<std::string, std::vector<std::string>>> files_with_errors;

    const auto start_time = std::chrono::steady_clock::now();

    for (const auto& file_path : files) {
        const std::string path_str = file_path.string();
        try {
            lotm::ini::ConstructFile parsed{ path_str, strict };

            if (!parsed.errors.empty()) {
                files_with_errors.emplace_back(path_str, parsed.errors);
                std::cerr << "[PARSE WARNING/ERROR] " << path_str << ":\n";
                for (const auto& err : parsed.errors) {
                    std::cerr << "  - " << err << '\n';
                }
                if (strict) {
                    ++failed;
                    continue;
                }
            }

            const std::string serialized = parsed.print();

            if (!output_path.empty() && files.size() == 1) {
                std::ofstream out_file(output_path, std::ios::binary);
                if (!out_file.is_open()) {
                    std::cerr << "Error: Failed to open output file: " << output_path << '\n';
                    return EXIT_FAILURE;
                }
                out_file << serialized;
            }

            if (check_roundtrip) {
                lotm::ini::ConstructFile reparsed{ path_str, strict, serialized };
                const std::string second_print = reparsed.print();

                if (serialized != second_print) {
                    std::cerr << "[ROUNDTRIP FAILED] " << path_str << " (output mutated on second pass)\n";
                    ++roundtrip_mismatches;
                    ++failed;
                    continue;
                }
            }

            ++passed;
        }
        catch (const std::exception& ex) {
            std::cerr << "[EXCEPTION] " << path_str << ": " << ex.what() << '\n';
            ++failed;
        }
    }

    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start_time
    ).count();

    const std::size_t clean_passes = (passed >= files_with_errors.size())
        ? (passed - files_with_errors.size())
        : 0;

    std::cout << "\n================ VALIDATION REPORT ================\n"
        << "Scanned Files:        " << files.size() << '\n'
        << "Passed (Clean):       " << clean_passes << '\n'
        << "Files with Warnings:  " << files_with_errors.size() << '\n'
        << "Failed:               " << failed << '\n'
        << "Roundtrip Mismatches: " << roundtrip_mismatches << '\n'
        << "Elapsed Time:         " << elapsed << " ms\n";

    if (!files_with_errors.empty()) {
        std::cout << "\nFiles with delimiter or structural errors:\n";
        for (const auto& [file, errs] : files_with_errors) {
            std::cout << "  - " << file << " (" << errs.size() << " error"
                << (errs.size() > 1 ? "s" : "") << ")\n";
        }
    }
    std::cout << "===================================================\n";

    return (failed == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
