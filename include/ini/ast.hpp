/**
 * @file include/ini/ast.hpp
 * @brief AST node definitions, variants, formatting options, and iterative serialization frame structures for lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <core/string_utils.hpp>

#include <algorithm>
#include <array>
#include <compare>
#include <cstddef>
#include <initializer_list>
#include <iterator>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

namespace lotm::ini {

    /**
     * @brief Domain-specific exception thrown on structural INI/INC/STR parsing or security violations.
     */
    class IniParseError : public std::runtime_error {
    public:
        using std::runtime_error::runtime_error;
    };

    /**
     * @brief Heap-stable sequence container that preserves element memory addresses across
     *        reallocations, insertions, and in-place replacements.
     */
    template <typename T>
    class StableVector {
    public:
        using value_type = T;
        using size_type = std::size_t;
        using difference_type = std::ptrdiff_t;
        using reference = T&;
        using const_reference = const T&;
        using pointer = T*;
        using const_pointer = const T*;

        template <bool IsConst>
        class Iterator {
        public:
            using VecIter = std::conditional_t<
                IsConst,
                typename std::vector<std::unique_ptr<T>>::const_iterator,
                typename std::vector<std::unique_ptr<T>>::iterator
            >;
            using iterator_category = std::random_access_iterator_tag;
            using iterator_concept = std::random_access_iterator_tag;
            using value_type = T;
            using difference_type = std::ptrdiff_t;
            using pointer = std::conditional_t<IsConst, const T*, T*>;
            using reference = std::conditional_t<IsConst, const T&, T&>;

            Iterator() noexcept = default;
            explicit Iterator(VecIter it) noexcept : it_(it) {}

            template <bool WasConst, typename = std::enable_if_t<IsConst && !WasConst>>
            Iterator(const Iterator<WasConst>& other) noexcept : it_(other.base()) {}

            [[nodiscard]] VecIter base() const noexcept { return it_; }

            [[nodiscard]] reference operator*() const noexcept { return **it_; }
            [[nodiscard]] pointer operator->() const noexcept { return it_->get(); }
            [[nodiscard]] reference operator[](difference_type n) const noexcept { return *it_[n]; }

            Iterator& operator++() noexcept { ++it_; return *this; }
            Iterator operator++(int) noexcept { Iterator tmp = *this; ++it_; return tmp; }
            Iterator& operator--() noexcept { --it_; return *this; }
            Iterator operator--(int) noexcept { Iterator tmp = *this; --it_; return tmp; }

            Iterator& operator+=(difference_type n) noexcept { it_ += n; return *this; }
            Iterator& operator-=(difference_type n) noexcept { it_ -= n; return *this; }

            [[nodiscard]] friend Iterator operator+(Iterator it, difference_type n) noexcept { return Iterator(it.it_ + n); }
            [[nodiscard]] friend Iterator operator+(difference_type n, Iterator it) noexcept { return Iterator(it.it_ + n); }
            [[nodiscard]] friend Iterator operator-(Iterator it, difference_type n) noexcept { return Iterator(it.it_ - n); }
            [[nodiscard]] friend difference_type operator-(const Iterator& a, const Iterator& b) noexcept { return a.it_ - b.it_; }

            [[nodiscard]] friend bool operator==(const Iterator& a, const Iterator& b) noexcept { return a.it_ == b.it_; }
            [[nodiscard]] friend auto operator<=>(const Iterator& a, const Iterator& b) noexcept { return a.it_ <=> b.it_; }

        private:
            VecIter it_{};
        };

        using iterator = Iterator<false>;
        using const_iterator = Iterator<true>;
        using reverse_iterator = std::reverse_iterator<iterator>;
        using const_reverse_iterator = std::reverse_iterator<const_iterator>;

        StableVector() = default;
        ~StableVector() = default;

        StableVector(std::initializer_list<T> init) {
            elements_.reserve(init.size());
            for (const auto& item : init) {
                elements_.push_back(std::make_unique<T>(item));
            }
        }

        StableVector(std::vector<T> vec) {
            elements_.reserve(vec.size());
            for (auto& item : vec) {
                elements_.push_back(std::make_unique<T>(std::move(item)));
            }
        }

        StableVector(const StableVector& other) {
            elements_.reserve(other.elements_.size());
            for (const auto& ptr : other.elements_) {
                elements_.push_back(std::make_unique<T>(*ptr));
            }
        }

        StableVector& operator=(const StableVector& other) {
            if (this != &other) {
                retire_active();
                elements_.reserve(other.elements_.size());
                for (const auto& ptr : other.elements_) {
                    elements_.push_back(std::make_unique<T>(*ptr));
                }
            }
            return *this;
        }

        StableVector(StableVector&& other) noexcept = default;

        StableVector& operator=(StableVector&& other) noexcept {
            if (this != &other) {
                retire_active();
                for (auto& ptr : other.retired_) {
                    if (ptr) {
                        retired_.push_back(std::move(ptr));
                    }
                }
                other.retired_.clear();
                elements_ = std::move(other.elements_);
            }
            return *this;
        }

        [[nodiscard]] size_type size() const noexcept { return elements_.size(); }
        [[nodiscard]] bool empty() const noexcept { return elements_.empty(); }
        void reserve(size_type n) { elements_.reserve(n); }

        void clear() {
            retire_active();
        }

        void push_back(const T& value) {
            elements_.push_back(std::make_unique<T>(value));
        }

        void push_back(T&& value) {
            elements_.push_back(std::make_unique<T>(std::move(value)));
        }

        template <typename... Args>
        reference emplace_back(Args&&... args) {
            return *elements_.emplace_back(std::make_unique<T>(std::forward<Args>(args)...));
        }

        void replace_at(size_type index, T value) {
            if (elements_[index]) {
                retired_.push_back(std::move(elements_[index]));
            }
            elements_[index] = std::make_unique<T>(std::move(value));
        }

        void erase_at(size_type index) {
            if (elements_[index]) {
                retired_.push_back(std::move(elements_[index]));
            }
            elements_.erase(elements_.begin() + static_cast<difference_type>(index));
        }

        void assign_from(std::vector<T> vec) {
            retire_active();
            elements_.reserve(vec.size());
            for (auto& item : vec) {
                elements_.push_back(std::make_unique<T>(std::move(item)));
            }
        }

        [[nodiscard]] reference operator[](size_type index) noexcept { return *elements_[index]; }
        [[nodiscard]] const_reference operator[](size_type index) const noexcept { return *elements_[index]; }

        [[nodiscard]] reference front() noexcept { return *elements_.front(); }
        [[nodiscard]] const_reference front() const noexcept { return *elements_.front(); }
        [[nodiscard]] reference back() noexcept { return *elements_.back(); }
        [[nodiscard]] const_reference back() const noexcept { return *elements_.back(); }

        [[nodiscard]] iterator begin() noexcept { return iterator(elements_.begin()); }
        [[nodiscard]] iterator end() noexcept { return iterator(elements_.end()); }
        [[nodiscard]] const_iterator begin() const noexcept { return const_iterator(elements_.begin()); }
        [[nodiscard]] const_iterator end() const noexcept { return const_iterator(elements_.end()); }
        [[nodiscard]] const_iterator cbegin() const noexcept { return const_iterator(elements_.cbegin()); }
        [[nodiscard]] const_iterator cend() const noexcept { return const_iterator(elements_.cend()); }

        [[nodiscard]] reverse_iterator rbegin() noexcept { return reverse_iterator(end()); }
        [[nodiscard]] reverse_iterator rend() noexcept { return reverse_iterator(begin()); }
        [[nodiscard]] const_reverse_iterator rbegin() const noexcept { return const_reverse_iterator(end()); }
        [[nodiscard]] const_reverse_iterator rend() const noexcept { return const_reverse_iterator(begin()); }
        [[nodiscard]] const_reverse_iterator crbegin() const noexcept { return const_reverse_iterator(cend()); }
        [[nodiscard]] const_reverse_iterator crend() const noexcept { return const_reverse_iterator(cbegin()); }

        [[nodiscard]] bool operator==(const StableVector& other) const {
            if (elements_.size() != other.elements_.size()) {
                return false;
            }
            for (size_type i = 0; i < elements_.size(); ++i) {
                if (!(*elements_[i] == *other.elements_[i])) {
                    return false;
                }
            }
            return true;
        }

    private:
        void retire_active() {
            retired_.reserve(retired_.size() + elements_.size());
            for (auto& ptr : elements_) {
                if (ptr) {
                    retired_.push_back(std::move(ptr));
                }
            }
            elements_.clear();
        }

        std::vector<std::unique_ptr<T>> elements_{};
        std::vector<std::unique_ptr<T>> retired_{};
    };

    /**
     * @brief CRTP mixin providing standard sequence operations over an underlying StableVector member.
     */
    template <typename Derived, typename ElementT>
    struct SequenceMixin {
        using value_type = ElementT;
        using size_type = std::size_t;
        using iterator = typename StableVector<ElementT>::iterator;
        using const_iterator = typename StableVector<ElementT>::const_iterator;

        [[nodiscard]] std::size_t size() const noexcept { return storage().size(); }
        [[nodiscard]] bool empty() const noexcept { return storage().empty(); }

        void append(ElementT item) { storage().push_back(std::move(item)); }

        [[nodiscard]] ElementT& operator[](std::size_t index) noexcept { return storage()[index]; }
        [[nodiscard]] const ElementT& operator[](std::size_t index) const noexcept { return storage()[index]; }

        [[nodiscard]] iterator begin() noexcept { return storage().begin(); }
        [[nodiscard]] iterator end() noexcept { return storage().end(); }
        [[nodiscard]] const_iterator begin() const noexcept { return storage().begin(); }
        [[nodiscard]] const_iterator end() const noexcept { return storage().end(); }
        [[nodiscard]] const_iterator cbegin() const noexcept { return storage().cbegin(); }
        [[nodiscard]] const_iterator cend() const noexcept { return storage().cend(); }

        [[nodiscard]] constexpr bool operator==(const SequenceMixin&) const noexcept = default;

    private:
        [[nodiscard]] constexpr StableVector<ElementT>& storage() noexcept {
            auto& self = static_cast<Derived&>(*this);
            if constexpr (requires { (self.items); }) {
                return self.items;
            }
            else {
                return self.entries;
            }
        }

        [[nodiscard]] constexpr const StableVector<ElementT>& storage() const noexcept {
            const auto& self = static_cast<const Derived&>(*this);
            if constexpr (requires { (self.items); }) {
                return self.items;
            }
            else {
                return self.entries;
            }
        }
    };

    inline constexpr std::string_view LEVEL_INDENT = "    ";
    inline constexpr std::string_view DEFAULT_END = "End";
    inline constexpr std::size_t MAX_INI_DEPTH = 16;
    inline constexpr std::size_t MAX_INI_FILE_SIZE = 64ULL * 1024ULL * 1024ULL;

    // Legacy 32-bit SAGE Engine string buffer limits for AST builders
    inline constexpr std::size_t SAGE_MAX_BLOCK_NAME_LEN = 256;
    inline constexpr std::size_t SAGE_MAX_IDENTIFIER_LEN = 512;

    /**
     * @brief Configurable serialization rules for AST printing and formatting.
     *
     * Default values guarantee 100% lossless roundtrip output matching original tokens.
     */
    struct FormatOptions {
        std::string indent{ LEVEL_INDENT };
        bool enforce_equals{ false };
        bool normalize_end_tokens{ false };
        bool normalize_header_spacing{ false };
        bool normalize_statement_equals{ false };
        bool normalize_comments{ false };
        bool coalesce_blank_lines{ false };

        [[nodiscard]] bool operator==(const FormatOptions&) const = default;
    };

    /**
     * @brief Validates string lengths against legacy SAGE engine buffer limits.
     * @throws IniParseError if bounds are exceeded.
     */
    inline void validate_sage_bounds(
        std::string_view name,
        std::string_view identifier = "",
        std::string_view class_token = ""
    ) {
        std::string_view clean_class = class_token;
        while (!clean_class.empty() && (clean_class.back() == '=' || clean_class.back() == ' ')) {
            clean_class.remove_suffix(1);
        }
        if (clean_class.size() > SAGE_MAX_BLOCK_NAME_LEN) {
            throw IniParseError("Security abort: Block class length (" + std::to_string(clean_class.size()) +
                ") exceeds SAGE engine limit (" + std::to_string(SAGE_MAX_BLOCK_NAME_LEN) + ")");
        }
        if (name.size() > SAGE_MAX_BLOCK_NAME_LEN) {
            throw IniParseError("Security abort: Block name length (" + std::to_string(name.size()) +
                ") exceeds SAGE engine limit (" + std::to_string(SAGE_MAX_BLOCK_NAME_LEN) + ")");
        }
        if (identifier.size() > SAGE_MAX_IDENTIFIER_LEN) {
            throw IniParseError("Security abort: Identifier length (" + std::to_string(identifier.size()) +
                ") exceeds SAGE engine limit (" + std::to_string(SAGE_MAX_IDENTIFIER_LEN) + ")");
        }
    }

    /**
     * @brief Checks case-insensitively whether a token matches the SAGE block closing keyword ("End").
     */
    [[nodiscard]] constexpr bool is_ini_end(std::string_view token) noexcept {
        return lotm::core::iequals_ascii(token, "end");
    }

    /**
     * @brief Represents a standalone or block-internal comment.
     */
    struct CommentNode {
        std::string text{};

        [[nodiscard]] bool operator==(const CommentNode&) const = default;
    };

    /**
     * @brief Represents a standard property assignment or value line.
     */
    struct StatementNode {
        std::string text{};
        std::string comment{};

        [[nodiscard]] bool operator==(const StatementNode&) const = default;
    };

    /**
     * @brief Represents a #include preprocessor directive.
     */
    struct IncludeNode {
        std::string raw_path{};
        std::string comment{};

        /**
         * @brief Returns normalized path with surrounding whitespace/quotes stripped and forward slashes.
         */
        [[nodiscard]] std::string clean_path() const {
            constexpr std::string_view strip_chars = " \t\"'";
            std::string_view view{ raw_path };

            const auto first = view.find_first_not_of(strip_chars);
            if (first == std::string_view::npos) {
                return {};
            }
            const auto last = view.find_last_not_of(strip_chars);
            view = view.substr(first, last - first + 1);

            std::string normalized{ view };
            std::ranges::replace(normalized, '\\', '/');
            return normalized;
        }

        [[nodiscard]] bool operator==(const IncludeNode&) const = default;
    };

    /**
     * @brief Represents a #define preprocessor macro directive.
     */
    struct DefineNode {
        std::string text{};
        std::string comment{};

        [[nodiscard]] bool operator==(const DefineNode&) const = default;
    };

    /**
     * @brief Represents an opaque embedded script block (BeginScript ... EndScript).
     */
    struct ScriptNode {
        std::string name{ "BeginScript" };
        std::string identifier{};
        std::string comment{};
        std::string header_comment{};
        std::string end_token{ "EndScript" };
        std::string end_comment{};
        std::vector<std::string> content{};

        ScriptNode() = default;

        explicit ScriptNode(
            std::string n,
            std::string ident = "",
            std::string cmt = "",
            std::string hdr_cmt = "",
            std::string end_tok = "EndScript",
            std::string end_cmt = "",
            std::vector<std::string> cont = {}
        )
            : name(std::move(n)),
            identifier(std::move(ident)),
            comment(std::move(cmt)),
            header_comment(std::move(hdr_cmt)),
            end_token(std::move(end_tok)),
            end_comment(std::move(end_cmt)),
            content(std::move(cont)) {
            validate_sage_bounds(name, identifier);
        }

        [[nodiscard]] std::string print(
            int level = 0,
            std::string_view file_type = ".ini",
            const FormatOptions& options = {}
        ) const;

        [[nodiscard]] bool operator==(const ScriptNode&) const = default;
    };

    struct ConstructLevel;

    /**
     * @brief Polymorphic value variant representing any node within an INI/INC hierarchy.
     */
    using AstNode = std::variant<
        CommentNode,
        StatementNode,
        IncludeNode,
        DefineNode,
        ScriptNode,
        ConstructLevel
    >;

    /**
     * @brief Represents an inner block or defined object within a parsed SAGE configuration file.
     */
    struct ConstructLevel : SequenceMixin<ConstructLevel, AstNode> {
        std::string _class;
        std::string name;
        std::string identifier;
        std::string comment;
        std::string header_comment;
        std::string end_token;
        std::string end_comment;
        std::string canonical_class{};
        bool missing_equals{ false };
        StableVector<AstNode> items;

        ConstructLevel();
        explicit ConstructLevel(
            std::string cls,
            std::string blk_name = {},
            std::string ident = {},
            std::string cmt = {},
            std::string hdr_cmt = {},
            std::string end_tok = {},
            std::string end_cmt = {},
            std::string canon_cls = {},
            bool no_eq = false
        );
        ~ConstructLevel();

        ConstructLevel(const ConstructLevel&);
        ConstructLevel& operator=(const ConstructLevel&);
        ConstructLevel(ConstructLevel&&) noexcept;
        ConstructLevel& operator=(ConstructLevel&&) noexcept;

        [[nodiscard]] ConstructLevel* find_block(
            std::string_view block_class,
            std::optional<std::string_view> block_name = std::nullopt,
            std::optional<std::string_view> block_identifier = std::nullopt,
            bool recursive = false
        );

        [[nodiscard]] const ConstructLevel* find_block(
            std::string_view block_class,
            std::optional<std::string_view> block_name = std::nullopt,
            std::optional<std::string_view> block_identifier = std::nullopt,
            bool recursive = false
        ) const;

        [[nodiscard]] std::vector<ConstructLevel*> find_all(
            std::string_view block_class,
            std::optional<std::string_view> block_name = std::nullopt,
            std::optional<std::string_view> block_identifier = std::nullopt,
            bool recursive = false
        );

        [[nodiscard]] std::vector<const ConstructLevel*> find_all(
            std::string_view block_class,
            std::optional<std::string_view> block_name = std::nullopt,
            std::optional<std::string_view> block_identifier = std::nullopt,
            bool recursive = false
        ) const;

        [[nodiscard]] std::optional<std::string> get_value(std::string_view key) const;
        [[nodiscard]] std::vector<std::string> get_all_values(std::string_view key) const;
        void set_value(std::string_view key, std::string_view value);
        bool remove_value(std::string_view key, bool all_occurrences = false);
        bool remove_block(
            std::string_view block_class,
            std::optional<std::string_view> block_name = std::nullopt,
            std::optional<std::string_view> block_identifier = std::nullopt
        );

        [[nodiscard]] std::string print(
            int level = 0,
            std::string_view file_type = ".ini",
            const FormatOptions& options = {}
        ) const;

        [[nodiscard]] bool operator==(const ConstructLevel& other) const {
            return _class == other._class &&
                name == other.name &&
                identifier == other.identifier &&
                comment == other.comment &&
                header_comment == other.header_comment &&
                end_token == other.end_token &&
                end_comment == other.end_comment &&
                items == other.items;
        }
    };

    inline ConstructLevel::ConstructLevel() = default;

    inline ConstructLevel::ConstructLevel(
        std::string cls,
        std::string blk_name,
        std::string ident,
        std::string cmt,
        std::string hdr_cmt,
        std::string end_tok,
        std::string end_cmt,
        std::string canon_cls,
        bool no_eq
    )
        : _class(std::move(cls)),
        name(std::move(blk_name)),
        identifier(std::move(ident)),
        comment(std::move(cmt)),
        header_comment(std::move(hdr_cmt)),
        end_token(std::move(end_tok)),
        end_comment(std::move(end_cmt)),
        canonical_class(std::move(canon_cls)),
        missing_equals(no_eq) {
        validate_sage_bounds(name, identifier, _class);
    }

    inline ConstructLevel::~ConstructLevel() = default;
    inline ConstructLevel::ConstructLevel(const ConstructLevel&) = default;
    inline ConstructLevel& ConstructLevel::operator=(const ConstructLevel&) = default;
    inline ConstructLevel::ConstructLevel(ConstructLevel&&) noexcept = default;
    inline ConstructLevel& ConstructLevel::operator=(ConstructLevel&&) noexcept = default;

    /**
     * @brief Child node variant allowed inside a localized .str entry.
     */
    using StrChildNode = std::variant<CommentNode, StatementNode>;

    /**
     * @brief Represents a single localized string entry inside a SAGE .str file.
     */
    struct StrEntry : SequenceMixin<StrEntry, StrChildNode> {
        std::string category{};
        std::string identifier{};
        std::string comment{};
        std::string header_comment{};
        std::string end_token{ "End" };
        std::string end_comment{};
        StableVector<StrChildNode> items{};

        StrEntry() = default;

        explicit StrEntry(
            std::string cat,
            std::string ident,
            std::string cmt = "",
            std::string hdr_cmt = "",
            std::string end_tok = "End",
            std::string end_cmt = "",
            StableVector<StrChildNode> itms = {}
        )
            : category(std::move(cat)),
            identifier(std::move(ident)),
            comment(std::move(cmt)),
            header_comment(std::move(hdr_cmt)),
            end_token(std::move(end_tok)),
            end_comment(std::move(end_cmt)),
            items(std::move(itms)) {
            validate_sage_bounds(category, identifier);
        }

        [[nodiscard]] std::string print(const FormatOptions& options = {}) const;

        [[nodiscard]] bool operator==(const StrEntry&) const = default;
    };

    /**
     * @brief Top-level entry variant for SAGE .str localization documents.
     */
    using StrDocEntry = std::variant<StrEntry, CommentNode, StatementNode>;

    /**
     * @brief Flat AST representation for SAGE .str localization files.
     */
    struct StrDocument : SequenceMixin<StrDocument, StrDocEntry> {
        std::string name{};
        StableVector<StrDocEntry> entries{};
        std::vector<std::string> errors{};

        StrDocument() = default;

        explicit StrDocument(
            std::string doc_name,
            StableVector<StrDocEntry> doc_entries = {},
            std::vector<std::string> doc_errors = {}
        )
            : name(std::move(doc_name)),
            entries(std::move(doc_entries)),
            errors(std::move(doc_errors)) {
        }

        [[nodiscard]] std::string print(const FormatOptions& options = {}) const;

        [[nodiscard]] bool operator==(const StrDocument&) const = default;
    };

    /**
     * @brief Top-level item variant stored in ConstructFile (supports both INI/INC AST nodes and STR entries).
     */
    using RootItem = std::variant<AstNode, StrEntry>;

    /**
     * @brief Non-owning pointer variant referencing any serializable AST node without copying.
     */
    using SerializableNodeRef = std::variant<
        const CommentNode*,
        const StatementNode*,
        const IncludeNode*,
        const DefineNode*,
        const ScriptNode*,
        const ConstructLevel*,
        const StrEntry*
    >;

    /**
     * @brief Explicit stack frame used by the iterative AST serializer to avoid call-stack recursion.
     */
    struct SerializationFrame {
        SerializableNodeRef node;
        int level{ 0 };
        bool is_closing{ false };
    };

    /**
     * @brief Converts an AstNode reference into a non-owning SerializableNodeRef.
     */
    [[nodiscard]] inline SerializableNodeRef to_serializable_ref(const AstNode& node) noexcept {
        return std::visit([](const auto& concrete) -> SerializableNodeRef {
            return &concrete;
            }, node);
    }

    /**
     * @brief Converts a StrChildNode reference into a non-owning SerializableNodeRef.
     */
    [[nodiscard]] inline SerializableNodeRef to_serializable_ref(const StrChildNode& node) noexcept {
        return std::visit([](const auto& concrete) -> SerializableNodeRef {
            return &concrete;
            }, node);
    }

    /**
     * @brief Converts a StrDocEntry reference into a non-owning SerializableNodeRef.
     */
    [[nodiscard]] inline SerializableNodeRef to_serializable_ref(const StrDocEntry& node) noexcept {
        return std::visit([](const auto& concrete) -> SerializableNodeRef {
            return &concrete;
            }, node);
    }

    /**
     * @brief Converts a RootItem reference into a non-owning SerializableNodeRef.
     */
    [[nodiscard]] inline SerializableNodeRef to_serializable_ref(const RootItem& item) noexcept {
        return std::visit([](const auto& concrete) -> SerializableNodeRef {
            using T = std::decay_t<decltype(concrete)>;
            if constexpr (std::is_same_v<T, AstNode>) {
                return to_serializable_ref(concrete);
            }
            else {
                return &concrete;
            }
            }, item);
    }

} // namespace lotm::ini
