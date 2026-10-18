// Gemini Pro 3.1

#pragma once

#include <nanobind/nanobind.h>
#include <vector>
#include <functional>

namespace lotm::python {

    using InitFn = std::function<void(nanobind::module_&)>;

    inline std::vector<InitFn>& get_registry() {
        static std::vector<InitFn> registry;
        return registry;
    }

    struct BindingRegistrar {
        explicit BindingRegistrar(InitFn fn) {
            get_registry().push_back(std::move(fn));
        }
    };

} // namespace lotm::python
