/**
 * @file src/bindings/py_utils.hpp
 * @brief Shared RAII Python Buffer Protocol wrapper for nanobind binding modules.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <nanobind/nanobind.h>
#include <cstddef>
#include <cstdint>
#include <span>

namespace lotm::python {

    /**
     * @brief RAII wrapper around Py_buffer for zero-copy Python Buffer Protocol ingestion.
     */
    struct ScopedPyBuffer {
        Py_buffer view{};
        bool valid{ false };

        explicit ScopedPyBuffer(nanobind::handle obj) {
            if (PyObject_GetBuffer(obj.ptr(), &view, PyBUF_SIMPLE) != 0) {
                throw nanobind::python_error();
            }
            valid = true;
        }

        ScopedPyBuffer(const ScopedPyBuffer&) = delete;
        ScopedPyBuffer& operator=(const ScopedPyBuffer&) = delete;

        ScopedPyBuffer(ScopedPyBuffer&& other) noexcept
            : view(other.view), valid(other.valid) {
            other.valid = false;
        }

        ScopedPyBuffer& operator=(ScopedPyBuffer&& other) noexcept {
            if (this != &other) {
                if (valid) {
                    PyBuffer_Release(&view);
                }
                view = other.view;
                valid = other.valid;
                other.valid = false;
            }
            return *this;
        }

        ~ScopedPyBuffer() {
            if (valid) {
                PyBuffer_Release(&view);
            }
        }

        [[nodiscard]] std::span<const uint8_t> as_span() const noexcept {
            return std::span<const uint8_t>(
                static_cast<const uint8_t*>(view.buf),
                static_cast<std::size_t>(view.len)
            );
        }
    };

} // namespace lotm::python
