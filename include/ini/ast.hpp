/**
 * @file include/ini/ast.hpp
 * @brief AST node definitions, variants, and iterative serialization frame structures for lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <algorithm>
#include <array>
#include <compare>
#include <cstddef>
#include <initializer_list>
#include <iterator>
#include <memory>
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

    inline constexpr std::string_view LEVEL_INDENT = "    ";
    inline constexpr std::array<std::string_view, 3> INI_ENDS = { "End", "END", "end" };
    inline constexpr std::size_t MAX_INI_DEPTH = 16;
    inline constexpr std::size_t MAX_INI_FILE_SIZE = 64ULL * 1024ULL * 1024ULL;

    // Legacy 32-bit SAGE Engine string buffer limits for AST builders
    inline constexpr std::size_t SAGE_MAX_BLOCK_NAME_LEN = 256;
    inline constexpr std::size_t SAGE_MAX_IDENTIFIER_LEN = 512;

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
        if (token.size() != 3) {
            return false;
        }
        const char c0 = (token[0] >= 'A' && token[0] <= 'Z') ? static_cast<char>(token[0] + ('a' - 'A')) : token[0];
        const char c1 = (token[1] >= 'A' && token[1] <= 'Z') ? static_cast<char>(token[1] + ('a' - 'A')) : token[1];
        const char c2 = (token[2] >= 'A' && token[2] <= 'Z') ? static_cast<char>(token[2] + ('a' - 'A')) : token[2];
        return c0 == 'e' && c1 == 'n' && c2 == 'd';
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

        [[nodiscard]] std::string print(int level = 0, std::string_view file_type = ".ini") const;

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
    struct ConstructLevel {
        std::string _class;
        std::string name;
        std::string identifier;
        std::string comment;
        std::string header_comment;
        std::string end_token;
        std::string end_comment;
        StableVector<AstNode> items;

        ConstructLevel();
        explicit ConstructLevel(
            std::string cls,
            std::string blk_name = {},
            std::string ident = {},
            std::string cmt = {},
            std::string hdr_cmt = {},
            std::string end_tok = {},
            std::string end_cmt = {}
        );
        ~ConstructLevel();

        ConstructLevel(const ConstructLevel&);
        ConstructLevel& operator=(const ConstructLevel&);
        ConstructLevel(ConstructLevel&&) noexcept;
        ConstructLevel& operator=(ConstructLevel&&) noexcept;

        [[nodiscard]] std::size_t size() const noexcept;
        [[nodiscard]] bool empty() const noexcept;

        void append(AstNode item);

        [[nodiscard]] AstNode& operator[](std::size_t index);
        [[nodiscard]] const AstNode& operator[](std::size_t index) const;

        [[nodiscard]] StableVector<AstNode>::iterator begin() noexcept;
        [[nodiscard]] StableVector<AstNode>::iterator end() noexcept;
        [[nodiscard]] StableVector<AstNode>::const_iterator begin() const noexcept;
        [[nodiscard]] StableVector<AstNode>::const_iterator end() const noexcept;
        [[nodiscard]] StableVector<AstNode>::const_iterator cbegin() const noexcept;
        [[nodiscard]] StableVector<AstNode>::const_iterator cend() const noexcept;

        [[nodiscard]] std::string print(int level = 0, std::string_view file_type = ".ini") const;

        [[nodiscard]] bool operator==(const ConstructLevel&) const;
    };

    inline ConstructLevel::ConstructLevel() = default;

    inline ConstructLevel::ConstructLevel(
        std::string cls,
        std::string blk_name,
        std::string ident,
        std::string cmt,
        std::string hdr_cmt,
        std::string end_tok,
        std::string end_cmt
    )
        : _class(std::move(cls)),
        name(std::move(blk_name)),
        identifier(std::move(ident)),
        comment(std::move(cmt)),
        header_comment(std::move(hdr_cmt)),
        end_token(std::move(end_tok)),
        end_comment(std::move(end_cmt)) {
        validate_sage_bounds(name, identifier, _class);
    }

    inline ConstructLevel::~ConstructLevel() = default;
    inline ConstructLevel::ConstructLevel(const ConstructLevel&) = default;
    inline ConstructLevel& ConstructLevel::operator=(const ConstructLevel&) = default;
    inline ConstructLevel::ConstructLevel(ConstructLevel&&) noexcept = default;
    inline ConstructLevel& ConstructLevel::operator=(ConstructLevel&&) noexcept = default;

    inline std::size_t ConstructLevel::size() const noexcept { return items.size(); }
    inline bool ConstructLevel::empty() const noexcept { return items.empty(); }
    inline void ConstructLevel::append(AstNode item) { items.push_back(std::move(item)); }
    inline AstNode& ConstructLevel::operator[](std::size_t index) { return items[index]; }
    inline const AstNode& ConstructLevel::operator[](std::size_t index) const { return items[index]; }
    inline StableVector<AstNode>::iterator ConstructLevel::begin() noexcept { return items.begin(); }
    inline StableVector<AstNode>::iterator ConstructLevel::end() noexcept { return items.end(); }
    inline StableVector<AstNode>::const_iterator ConstructLevel::begin() const noexcept { return items.begin(); }
    inline StableVector<AstNode>::const_iterator ConstructLevel::end() const noexcept { return items.end(); }
    inline StableVector<AstNode>::const_iterator ConstructLevel::cbegin() const noexcept { return items.cbegin(); }
    inline StableVector<AstNode>::const_iterator ConstructLevel::cend() const noexcept { return items.cend(); }
    inline bool ConstructLevel::operator==(const ConstructLevel&) const = default;

    /**
     * @brief Child node variant allowed inside a localized .str entry.
     */
    using StrChildNode = std::variant<CommentNode, StatementNode>;

    /**
     * @brief Represents a single localized string entry inside a SAGE .str file.
     */
    struct StrEntry {
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

        [[nodiscard]] std::size_t size() const noexcept { return items.size(); }
        [[nodiscard]] bool empty() const noexcept { return items.empty(); }

        void append(StrChildNode item) { items.push_back(std::move(item)); }

        [[nodiscard]] StrChildNode& operator[](std::size_t index) { return items[index]; }
        [[nodiscard]] const StrChildNode& operator[](std::size_t index) const { return items[index]; }

        [[nodiscard]] auto begin() noexcept { return items.begin(); }
        [[nodiscard]] auto end() noexcept { return items.end(); }
        [[nodiscard]] auto begin() const noexcept { return items.begin(); }
        [[nodiscard]] auto end() const noexcept { return items.end(); }
        [[nodiscard]] auto cbegin() const noexcept { return items.cbegin(); }
        [[nodiscard]] auto cend() const noexcept { return items.cend(); }

        [[nodiscard]] std::string print() const;

        [[nodiscard]] bool operator==(const StrEntry&) const = default;
    };

    /**
     * @brief Top-level entry variant for SAGE .str localization documents.
     */
    using StrDocEntry = std::variant<StrEntry, CommentNode, StatementNode>;

    /**
     * @brief Flat AST representation for SAGE .str localization files.
     */
    struct StrDocument {
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

        [[nodiscard]] std::size_t size() const noexcept { return entries.size(); }
        [[nodiscard]] bool empty() const noexcept { return entries.empty(); }

        void append(StrDocEntry entry) { entries.push_back(std::move(entry)); }

        [[nodiscard]] StrDocEntry& operator[](std::size_t index) { return entries[index]; }
        [[nodiscard]] const StrDocEntry& operator[](std::size_t index) const { return entries[index]; }

        [[nodiscard]] auto begin() noexcept { return entries.begin(); }
        [[nodiscard]] auto end() noexcept { return entries.end(); }
        [[nodiscard]] auto begin() const noexcept { return entries.begin(); }
        [[nodiscard]] auto end() const noexcept { return entries.end(); }
        [[nodiscard]] auto cbegin() const noexcept { return entries.cbegin(); }
        [[nodiscard]] auto cend() const noexcept { return entries.cend(); }

        [[nodiscard]] std::string print() const;

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
