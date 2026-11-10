/**
 * @file include/ini/schema.hpp
 * @brief Compile-time constexpr delimiter schemas and zero-allocation rule evaluation helpers.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lotm::ini {

    inline constexpr std::size_t MAX_RULE_TOKENS = 8;

    /**
     * @brief Pre-tokenized delimiter rule isomorphic to a constexpr table entry.
     */
    struct DelimiterRule {
        std::string_view raw{};
        std::array<std::string_view, MAX_RULE_TOKENS> match_tokens{};
        std::size_t token_count{ 0 };
        std::size_t word_count{ 0 };

        [[nodiscard]] constexpr std::span<const std::string_view> tokens() const noexcept {
            return std::span<const std::string_view>{match_tokens.data(), token_count};
        }
    };

    namespace detail {

        [[nodiscard]] constexpr bool is_delim_space(char c) noexcept {
            return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v' || c == '\f';
        }

    } // namespace detail

    /**
     * @brief Tokenizes a raw delimiter specification into a DelimiterRule at compile time or runtime without heap allocation.
     *
     * Note: For runtime usage, the backing memory of `delim` must outlive the returned DelimiterRule.
     */
    [[nodiscard]] constexpr DelimiterRule compile_delimiter_rule(std::string_view delim) noexcept {
        DelimiterRule rule{};
        rule.raw = delim;

        std::size_t pos = 0;
        const std::size_t len = delim.size();

        while (pos < len) {
            while (pos < len && detail::is_delim_space(delim[pos])) {
                ++pos;
            }
            if (pos >= len) {
                break;
            }

            if (delim[pos] == '=') {
                if (rule.token_count < MAX_RULE_TOKENS) {
                    rule.match_tokens[rule.token_count++] = "=";
                }
                ++pos;
            }
            else if (delim[pos] == ':') {
                if (rule.token_count < MAX_RULE_TOKENS) {
                    rule.match_tokens[rule.token_count++] = ":";
                }
                ++pos;
            }
            else {
                const std::size_t start = pos;
                while (pos < len && !detail::is_delim_space(delim[pos]) && delim[pos] != '=' && delim[pos] != ':') {
                    ++pos;
                }
                if (rule.token_count < MAX_RULE_TOKENS) {
                    rule.match_tokens[rule.token_count++] = delim.substr(start, pos - start);
                }
                ++rule.word_count;
            }
        }

        return rule;
    }

    /**
     * @brief Compiles and stably sorts an array of raw delimiter strings at compile time by descending token count.
     */
    template <std::size_t N>
    [[nodiscard]] constexpr std::array<DelimiterRule, N> compile_static_rules(
        const std::array<std::string_view, N>& raw_delims
    ) noexcept {
        std::array<DelimiterRule, N> rules{};
        for (std::size_t i = 0; i < N; ++i) {
            rules[i] = compile_delimiter_rule(raw_delims[i]);
        }
        for (std::size_t i = 1; i < N; ++i) {
            const DelimiterRule key = rules[i];
            std::size_t j = i;
            while (j > 0 && rules[j - 1].token_count < key.token_count) {
                rules[j] = rules[j - 1];
                --j;
            }
            rules[j] = key;
        }
        return rules;
    }

    /**
     * @brief Compiles and stably sorts a dynamic list of delimiter strings by descending token count.
     *
     * Note: The strings in `delimiter_list` must outlive the returned vector of `DelimiterRule` objects.
     */
    [[nodiscard]] inline std::vector<DelimiterRule> compile_delimiter_rules(
        std::span<const std::string> delimiter_list
    ) {
        std::vector<DelimiterRule> rules;
        rules.reserve(delimiter_list.size());
        for (const auto& delim : delimiter_list) {
            const auto rule = compile_delimiter_rule(delim);
            if (rule.token_count > 0) {
                rules.push_back(rule);
            }
        }
        std::ranges::stable_sort(rules, [](const DelimiterRule& a, const DelimiterRule& b) {
            return a.token_count > b.token_count;
            });
        return rules;
    }

    /**
     * @brief Matches a tokenized line against pre-compiled delimiter rules without allocation.
     */
    [[nodiscard]] constexpr const DelimiterRule* match_delimiter_rule(
        std::span<const std::string_view> line_tokens,
        std::span<const DelimiterRule> rules
    ) noexcept {
        const std::size_t token_count = line_tokens.size();
        for (const auto& rule : rules) {
            const std::size_t k = rule.token_count;
            if (k > 0 && token_count >= k) {
                bool matched = true;
                for (std::size_t i = 0; i < k; ++i) {
                    if (line_tokens[i] != rule.match_tokens[i]) {
                        matched = false;
                        break;
                    }
                }
                if (matched) {
                    return &rule;
                }
            }
        }
        return nullptr;
    }

    namespace schema_tables {

        // Group 0
        inline constexpr auto G0_L0 = std::to_array<std::string_view>({
            "AudioEvent", "Multisound", "StreamedSound", "AmbientStream", "Animation",
            "Armor", "AudioSettings", "AnimationSoundClientBehaviorGlobalSetting",
            "ModifierList", "BannerType", "ButtonSet", "CommandButton", "CommandMap",
            "DebugCommandMap", "CommandSet", "ControlBarResizer", "SpecialPower",
            "DamageFX", "DrawGroupInfo", "EmotionNugget", "SkyboxTextureSet",
            "GlowEffect", "RingEffect", "FireEffect", "CloudEffect", "ShadowMap",
            "Fire", "FontDefaultSettings", "FontSubstitution", "GameData",
            "StaticGameLOD", "DynamicGameLOD", "AudioLOD", "HouseColor",
            "LargeGroupAudioUnusedKnownKeys", "LightPointLevel", "LivingWorldSound",
            "LivingWorldObject", "LivingWorldAnimObject", "LivingWorldAITemplate",
            "AutoResolveArmor", "AutoResolveBody", "AutoResolveCombatChain",
            "AutoResolveHandicapLevel", "AutoResolveReinforcementSchedule",
            "AutoResolveWeapon", "LivingWorldPlayerTemplate", "Locomotor",
            "MappedImage", "MeshNameMatches", "MiscAudio", "Mouse", "MouseCursor",
            "OnlineChatColors", "MultiplayerSettings", "MultiplayerColor",
            "MusicTrack", "OptionGroup", "ParticleSystem", "Pathfinder",
            "PlayerAIType", "PlayerTemplate", "Rank", "Bridge", "Road",
            "ShellMenuScheme", "Science", "ScoredKillEvaAnnouncer", "SpecialPower",
            "DialogEvent", "Terrain", "Upgrade", "VictorySystemData",
            "FactionVictoryData", "Video", "WaterSet", "WaterTransparency",
            "WaterTextureList", "Weather", "WeatherData", "WebpageURL", "AIBase",
            "AIDozerAssignment", "LoadSubsystem", "SpawnArmy",
            "Credits", "AptButtonTooltipMap"
            });
        inline constexpr auto G0_L0_RULES = compile_static_rules(G0_L0);
        inline constexpr std::array<std::span<const std::string_view>, 1> G0 = { G0_L0 };
        inline constexpr std::array<std::span<const DelimiterRule>, 1> G0_RULES = { G0_L0_RULES };

        // Group 1
        inline constexpr auto G1_L0 = std::to_array<std::string_view>({ "ArmySummaryDescription" });
        inline constexpr auto G1_L1 = std::to_array<std::string_view>({ "UnitCategory" });
        inline constexpr auto G1_L0_RULES = compile_static_rules(G1_L0);
        inline constexpr auto G1_L1_RULES = compile_static_rules(G1_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G1 = { G1_L0, G1_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G1_RULES = { G1_L0_RULES, G1_L1_RULES };

        // Group 2
        inline constexpr auto G2_L0 = std::to_array<std::string_view>({ "AwardSystem" });
        inline constexpr auto G2_L1 = std::to_array<std::string_view>({ "ObjectAward", "ThingStat" });
        inline constexpr auto G2_L2 = std::to_array<std::string_view>({ "Trigger" });
        inline constexpr auto G2_L0_RULES = compile_static_rules(G2_L0);
        inline constexpr auto G2_L1_RULES = compile_static_rules(G2_L1);
        inline constexpr auto G2_L2_RULES = compile_static_rules(G2_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G2 = { G2_L0, G2_L1, G2_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G2_RULES = { G2_L0_RULES, G2_L1_RULES, G2_L2_RULES };

        // Group 3
        inline constexpr auto G3_L0 = std::to_array<std::string_view>({ "ControlBarScheme" });
        inline constexpr auto G3_L1 = std::to_array<std::string_view>({ "ImagePart" });
        inline constexpr auto G3_L0_RULES = compile_static_rules(G3_L0);
        inline constexpr auto G3_L1_RULES = compile_static_rules(G3_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G3 = { G3_L0, G3_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G3_RULES = { G3_L0_RULES, G3_L1_RULES };

        // Group 4
        inline constexpr auto G4_L0 = std::to_array<std::string_view>({
            "Object", "ChildObject", "ObjectReskin", "CrateData", "FormationAssistant", "FXParticleSystem", "FXList"
            });
        inline constexpr auto G4_L1 = std::to_array<std::string_view>({
            "Draw", "Body", "ArmorSet", "WeaponSet", "LocomotorSet", "UnitSpecificSounds", "Flammability",
            "ThreatBreakdown", "ClientUpdate", "ClientBehavior", "Behavior", "AutoResolveArmor", "AutoResolveWeapon",
            "AddModule", "ReplaceModule", "InheritableModule", "FormationPreviewDecal", "FormationPreviewItemDecal",
            "UnitDefinition", "FormationTemplate", "FormationSelection", "Alpha", "Update", "Physics", "EmissionVelocity",
            "EmissionVolume", "Event", "Emitter", "Wind", "System", "Color", "Sound", "ParticleSystem", "DynamicDecal",
            "TerrainScorch", "BuffNugget", "ViewShake", "CameraShakerVolume", "TintDrawable", "FXListAtBonePos",
            "LightPulse", "EvaEvent", "AttachedModel"
            });
        inline constexpr auto G4_L2 = std::to_array<std::string_view>({
            "LodOptions", "DefaultModelConditionState", "ModelConditionState", "IdleAnimationState", "AnimationState",
            "TransitionState", "SoundState", "ProductionModifier", "FireWeaponNugget", "InvisibilityNugget", "FloodMember",
            "SoundUpgrade", "Turret", "ReplaceObject", "DecalTemplate", "GridDecalTemplate", "MeleeBehavior", "Behavior",
            "Body", "ClientBehavior", "Rows", "AddEmotion = OVERRIDE"
            });
        inline constexpr auto G4_L3 = std::to_array<std::string_view>({
            "Animation", "BeginScript", "MeleeBehavior", "UnitSpecificSounds"
            });
        inline constexpr auto G4_L0_RULES = compile_static_rules(G4_L0);
        inline constexpr auto G4_L1_RULES = compile_static_rules(G4_L1);
        inline constexpr auto G4_L2_RULES = compile_static_rules(G4_L2);
        inline constexpr auto G4_L3_RULES = compile_static_rules(G4_L3);
        inline constexpr std::array<std::span<const std::string_view>, 4> G4 = { G4_L0, G4_L1, G4_L2, G4_L3 };
        inline constexpr std::array<std::span<const DelimiterRule>, 4> G4_RULES = {
            G4_L0_RULES, G4_L1_RULES, G4_L2_RULES, G4_L3_RULES
        };

        // Group 5
        inline constexpr auto G5_L0 = std::to_array<std::string_view>({ "CreateAHeroSystem" });
        inline constexpr auto G5_L1 = std::to_array<std::string_view>({
            "CreateAHeroBlingBinder", "CreateAHeroBling", "CreateAHeroClass"
            });
        inline constexpr auto G5_L2 = std::to_array<std::string_view>({ "SubClass" });
        inline constexpr auto G5_L3 = std::to_array<std::string_view>({ "Attribute", "ViewInfo" });
        inline constexpr auto G5_L0_RULES = compile_static_rules(G5_L0);
        inline constexpr auto G5_L1_RULES = compile_static_rules(G5_L1);
        inline constexpr auto G5_L2_RULES = compile_static_rules(G5_L2);
        inline constexpr auto G5_L3_RULES = compile_static_rules(G5_L3);
        inline constexpr std::array<std::span<const std::string_view>, 4> G5 = { G5_L0, G5_L1, G5_L2, G5_L3 };
        inline constexpr std::array<std::span<const DelimiterRule>, 4> G5_RULES = {
            G5_L0_RULES, G5_L1_RULES, G5_L2_RULES, G5_L3_RULES
        };

        // Group 6
        inline constexpr auto G6_L0 = std::to_array<std::string_view>({ "CrowdResponse" });
        inline constexpr auto G6_L1 = std::to_array<std::string_view>({ "Threshold" });
        inline constexpr auto G6_L2 = std::to_array<std::string_view>({ "UnitSpecificSounds" });
        inline constexpr auto G6_L0_RULES = compile_static_rules(G6_L0);
        inline constexpr auto G6_L1_RULES = compile_static_rules(G6_L1);
        inline constexpr auto G6_L2_RULES = compile_static_rules(G6_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G6 = { G6_L0, G6_L1, G6_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G6_RULES = { G6_L0_RULES, G6_L1_RULES, G6_L2_RULES };

        // Group 7
        inline constexpr auto G7_L0 = std::to_array<std::string_view>({ "AIData" });
        inline constexpr auto G7_L1 = std::to_array<std::string_view>({ "SideInfo", "SkirmishBuildList", "AttackPriority" });
        inline constexpr auto G7_L2 = std::to_array<std::string_view>({ "Structure" });
        inline constexpr auto G7_L0_RULES = compile_static_rules(G7_L0);
        inline constexpr auto G7_L1_RULES = compile_static_rules(G7_L1);
        inline constexpr auto G7_L2_RULES = compile_static_rules(G7_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G7 = { G7_L0, G7_L1, G7_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G7_RULES = { G7_L0_RULES, G7_L1_RULES, G7_L2_RULES };

        // Group 8
        inline constexpr auto G8_L0 = std::to_array<std::string_view>({ "PredefinedEvaEvent", "NewEvaEvent", "MiscEvaData" });
        inline constexpr auto G8_L1 = std::to_array<std::string_view>({ "SideSound" });
        inline constexpr auto G8_L0_RULES = compile_static_rules(G8_L0);
        inline constexpr auto G8_L1_RULES = compile_static_rules(G8_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G8 = { G8_L0, G8_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G8_RULES = { G8_L0_RULES, G8_L1_RULES };

        // Group 9
        inline constexpr auto G9_L0 = std::to_array<std::string_view>({ "ExperienceScalarTable", "ExperienceLevel" });
        inline constexpr auto G9_L1 = std::to_array<std::string_view>({ "SelectionDecal" });
        inline constexpr auto G9_L0_RULES = compile_static_rules(G9_L0);
        inline constexpr auto G9_L1_RULES = compile_static_rules(G9_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G9 = { G9_L0, G9_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G9_RULES = { G9_L0_RULES, G9_L1_RULES };

        // Group 10
        inline constexpr auto G10_L0 = std::to_array<std::string_view>({ "FireLogicSystem" });
        inline constexpr auto G10_L1 = std::to_array<std::string_view>({ "TerrainCellType" });
        inline constexpr auto G10_L0_RULES = compile_static_rules(G10_L0);
        inline constexpr auto G10_L1_RULES = compile_static_rules(G10_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G10 = { G10_L0, G10_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G10_RULES = { G10_L0_RULES, G10_L1_RULES };

        // Group 11
        inline constexpr auto G11_L0 = std::to_array<std::string_view>({ "FormationAssistant" });
        inline constexpr auto G11_L1 = std::to_array<std::string_view>({
            "UnitDefinition", "FormationTemplate", "FormationSelection"
            });
        inline constexpr auto G11_L2 = std::to_array<std::string_view>({ "Rows" });
        inline constexpr auto G11_L0_RULES = compile_static_rules(G11_L0);
        inline constexpr auto G11_L1_RULES = compile_static_rules(G11_L1);
        inline constexpr auto G11_L2_RULES = compile_static_rules(G11_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G11 = { G11_L0, G11_L1, G11_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G11_RULES = {
            G11_L0_RULES, G11_L1_RULES, G11_L2_RULES
        };

        // Group 12
        inline constexpr auto G12_L0 = std::to_array<std::string_view>({ "InGameNotificationBox" });
        inline constexpr auto G12_L1 = std::to_array<std::string_view>({ "NotificationType" });
        inline constexpr auto G12_L0_RULES = compile_static_rules(G12_L0);
        inline constexpr auto G12_L1_RULES = compile_static_rules(G12_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G12 = { G12_L0, G12_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G12_RULES = { G12_L0_RULES, G12_L1_RULES };

        // Group 13
        inline constexpr auto G13_L0 = std::to_array<std::string_view>({ "InGameUI" });
        inline constexpr auto G13_L1 = std::to_array<std::string_view>({ "RadiusCursorTemplate" });
        inline constexpr auto G13_L0_RULES = compile_static_rules(G13_L0);
        inline constexpr auto G13_L1_RULES = compile_static_rules(G13_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G13 = { G13_L0, G13_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G13_RULES = { G13_L0_RULES, G13_L1_RULES };

        // Group 14
        inline constexpr auto G14_L0 = std::to_array<std::string_view>({
            "LargeGroupAudioMap", "LargeGroupAudioUnusedKnownKeys"
            });
        inline constexpr auto G14_L1 = std::to_array<std::string_view>({ "Sound" });
        inline constexpr auto G14_L0_RULES = compile_static_rules(G14_L0);
        inline constexpr auto G14_L1_RULES = compile_static_rules(G14_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G14 = { G14_L0, G14_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G14_RULES = { G14_L0_RULES, G14_L1_RULES };

        // Group 15
        inline constexpr auto G15_L0 = std::to_array<std::string_view>({ "LinearCampaign" });
        inline constexpr auto G15_L1 = std::to_array<std::string_view>({ "Mission" });
        inline constexpr auto G15_L0_RULES = compile_static_rules(G15_L0);
        inline constexpr auto G15_L1_RULES = compile_static_rules(G15_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G15 = { G15_L0, G15_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G15_RULES = { G15_L0_RULES, G15_L1_RULES };

        // Group 16
        inline constexpr auto G16_L0 = std::to_array<std::string_view>({
            "LivingWorldMapInfo", "LivingWorldArmyIcon", "LivingWorldSound", "LivingWorldObject",
            "LivingWorldAnimObject", "LivingWorldBuildingIcon", "LivingWorldBuildPlotIcon"
            });
        inline constexpr auto G16_L1 = std::to_array<std::string_view>({ "Object" });
        inline constexpr auto G16_L0_RULES = compile_static_rules(G16_L0);
        inline constexpr auto G16_L1_RULES = compile_static_rules(G16_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G16 = { G16_L0, G16_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G16_RULES = { G16_L0_RULES, G16_L1_RULES };

        // Group 17
        inline constexpr auto G17_L0 = std::to_array<std::string_view>({ "AutoResolveLeadership" });
        inline constexpr auto G17_L1 = std::to_array<std::string_view>({ "BonusForLevel" });
        inline constexpr auto G17_L0_RULES = compile_static_rules(G17_L0);
        inline constexpr auto G17_L1_RULES = compile_static_rules(G17_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G17 = { G17_L0, G17_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G17_RULES = { G17_L0_RULES, G17_L1_RULES };

        // Group 18
        inline constexpr auto G18_L0 = std::to_array<std::string_view>({
            "LivingWorldAutoResolveResourceBonus", "LivingWorldAutoResolveSciencePurchasePointBonus"
            });
        inline constexpr auto G18_L1 = std::to_array<std::string_view>({ "Bonus" });
        inline constexpr auto G18_L0_RULES = compile_static_rules(G18_L0);
        inline constexpr auto G18_L1_RULES = compile_static_rules(G18_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G18 = { G18_L0, G18_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G18_RULES = { G18_L0_RULES, G18_L1_RULES };

        // Group 19
        inline constexpr auto G19_L0 = std::to_array<std::string_view>({ "LivingWorldBuilding" });
        inline constexpr auto G19_L1 = std::to_array<std::string_view>({ "BuildingNugget" });
        inline constexpr auto G19_L2 = std::to_array<std::string_view>({ "ArmyToSpawn" });
        inline constexpr auto G19_L0_RULES = compile_static_rules(G19_L0);
        inline constexpr auto G19_L1_RULES = compile_static_rules(G19_L1);
        inline constexpr auto G19_L2_RULES = compile_static_rules(G19_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G19 = { G19_L0, G19_L1, G19_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G19_RULES = {
            G19_L0_RULES, G19_L1_RULES, G19_L2_RULES
        };

        // Group 20
        inline constexpr auto G20_L0 = std::to_array<std::string_view>({ "LivingWorldRegionEffects" });
        inline constexpr auto G20_L1 = std::to_array<std::string_view>({
            "BordersEffect", "FilledOwnershipEffect", "MouseoverEffectFlareup", "MouseoutEffectFlareup",
            "HomeRegionHighlight", "RegionSelectionEffect", "UnifiedEffect"
            });
        inline constexpr auto G20_L2 = std::to_array<std::string_view>({ "ColorIntensityControlPoint" });
        inline constexpr auto G20_L0_RULES = compile_static_rules(G20_L0);
        inline constexpr auto G20_L1_RULES = compile_static_rules(G20_L1);
        inline constexpr auto G20_L2_RULES = compile_static_rules(G20_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G20 = { G20_L0, G20_L1, G20_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G20_RULES = {
            G20_L0_RULES, G20_L1_RULES, G20_L2_RULES
        };

        // Group 21
        inline constexpr auto G21_L0 = std::to_array<std::string_view>({ "ObjectCreationList" });
        inline constexpr auto G21_L1 = std::to_array<std::string_view>({ "CreateObject", "CreateDebris", "FireWeapon" });
        inline constexpr auto G21_L0_RULES = compile_static_rules(G21_L0);
        inline constexpr auto G21_L1_RULES = compile_static_rules(G21_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G21 = { G21_L0, G21_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G21_RULES = { G21_L0_RULES, G21_L1_RULES };

        // Group 22
        inline constexpr auto G22_L0 = std::to_array<std::string_view>({ "StanceTemplate" });
        inline constexpr auto G22_L1 = std::to_array<std::string_view>({ "Stance" });
        inline constexpr auto G22_L2 = std::to_array<std::string_view>({ "MeleeBehavior" });
        inline constexpr auto G22_L0_RULES = compile_static_rules(G22_L0);
        inline constexpr auto G22_L1_RULES = compile_static_rules(G22_L1);
        inline constexpr auto G22_L2_RULES = compile_static_rules(G22_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G22 = { G22_L0, G22_L1, G22_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G22_RULES = {
            G22_L0_RULES, G22_L1_RULES, G22_L2_RULES
        };

        // Group 23
        inline constexpr auto G23_L0 = std::to_array<std::string_view>({ "StrategicHUD" });
        inline constexpr auto G23_L1 = std::to_array<std::string_view>({
            "ArmyDetailsPanel", "BattleResolver", "BuildQueueDetailsPanel", "CancelArmyMemberMoveButton",
            "CancelArmyMoveButton", "Checklist", "DestroyBuildingButton", "CancelBuildingConstructionButton",
            "DisbandArmyMemberButton", "DynamicAutoResolveDialog", "OptionsButton", "ObjectivesButton",
            "RegionDetailsPanelStructuresPage", "RegionDisplay", "StatsDisplay", "ToggleSelectionDetailsButton",
            "TypeImages", "UpgradeUnitButton"
            });
        inline constexpr auto G23_L0_RULES = compile_static_rules(G23_L0);
        inline constexpr auto G23_L1_RULES = compile_static_rules(G23_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G23 = { G23_L0, G23_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G23_RULES = { G23_L0_RULES, G23_L1_RULES };

        // Group 24
        inline constexpr auto G24_L0 = std::to_array<std::string_view>({ "Weapon" });
        inline constexpr auto G24_L1 = std::to_array<std::string_view>({
            "DamageNugget", "DamageFieldNugget", "DOTNugget", "AttributeModifierNugget", "StealMoneyNugget",
            "ProjectileNugget", "MetaImpactNugget", "SlaveAttackNugget", "EmotionWeaponNugget", "FireLogicNugget",
            "WeaponOCLNugget", "HordeAttackNugget", "DamageContainedNugget", "LuaEventNugget", "ParalyzeNugget",
            "SpawnAndFadeNugget", "GrabNugget", "SpecialModelConditionNugget", "OpenGateNugget"
            });
        inline constexpr auto G24_L0_RULES = compile_static_rules(G24_L0);
        inline constexpr auto G24_L1_RULES = compile_static_rules(G24_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G24 = { G24_L0, G24_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G24_RULES = { G24_L0_RULES, G24_L1_RULES };

        // Group 25
        inline constexpr auto G25_L0 = std::to_array<std::string_view>({ "WindowTransition" });
        inline constexpr auto G25_L1 = std::to_array<std::string_view>({ "Window" });
        inline constexpr auto G25_L2 = std::to_array<std::string_view>({ "Transition" });
        inline constexpr auto G25_L0_RULES = compile_static_rules(G25_L0);
        inline constexpr auto G25_L1_RULES = compile_static_rules(G25_L1);
        inline constexpr auto G25_L2_RULES = compile_static_rules(G25_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G25 = { G25_L0, G25_L1, G25_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G25_RULES = {
            G25_L0_RULES, G25_L1_RULES, G25_L2_RULES
        };

        // Group 26
        inline constexpr auto G26_L0 = std::to_array<std::string_view>({ "SkirmishAIData" });
        inline constexpr auto G26_L1 = std::to_array<std::string_view>({
            "CombatChainDefinition", "BrutalDifficultyCheats", "DifficultyTuning"
            });
        inline constexpr auto G26_L0_RULES = compile_static_rules(G26_L0);
        inline constexpr auto G26_L1_RULES = compile_static_rules(G26_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G26 = { G26_L0, G26_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G26_RULES = { G26_L0_RULES, G26_L1_RULES };

        // Group 27
        inline constexpr auto G27_L0 = std::to_array<std::string_view>({ "ArmyDefinition" });
        inline constexpr auto G27_L1 = std::to_array<std::string_view>({
            "AIEconomyAssigment", "AIWallNodeAssignment", "ArmyMemberDefinition"
            });
        inline constexpr auto G27_L0_RULES = compile_static_rules(G27_L0);
        inline constexpr auto G27_L1_RULES = compile_static_rules(G27_L1);
        inline constexpr std::array<std::span<const std::string_view>, 2> G27 = { G27_L0, G27_L1 };
        inline constexpr std::array<std::span<const DelimiterRule>, 2> G27_RULES = { G27_L0_RULES, G27_L1_RULES };

        // Group 28
        inline constexpr auto G28_L0 = std::to_array<std::string_view>({ "LivingWorldRegionCampaign", "RegionCampain" });
        inline constexpr auto G28_L1 = std::to_array<std::string_view>({
            "Region", "LivingWorldPlayerArmy", "ConcurrentRegionBonus"
            });
        inline constexpr auto G28_L2 = std::to_array<std::string_view>({ "Connection", "RestrictBuildings", "ArmyEntry" });
        inline constexpr auto G28_L0_RULES = compile_static_rules(G28_L0);
        inline constexpr auto G28_L1_RULES = compile_static_rules(G28_L1);
        inline constexpr auto G28_L2_RULES = compile_static_rules(G28_L2);
        inline constexpr std::array<std::span<const std::string_view>, 3> G28 = { G28_L0, G28_L1, G28_L2 };
        inline constexpr std::array<std::span<const DelimiterRule>, 3> G28_RULES = {
            G28_L0_RULES, G28_L1_RULES, G28_L2_RULES
        };

        // Group 29
        inline constexpr auto G29_L0 = std::to_array<std::string_view>({ "LivingWorldCampaign" });
        inline constexpr auto G29_L1 = std::to_array<std::string_view>({
            "Scenario", "Act", "AddPlayer", "Tutorial", "LivingWorldVictoryType"
            });
        inline constexpr auto G29_L2 = std::to_array<std::string_view>({
            "PlayerDefeatCondition", "TeamDefeatCondition", "TeamVictoryCondition", "EyeTowerPoints",
            "OwnershipSet", "Turn", "SpawnArmy", "StartingRestriction"
            });
        inline constexpr auto G29_L3 = std::to_array<std::string_view>({ "SpawnBuildings", "SpawnArmies", "Phase" });
        inline constexpr auto G29_L4 = std::to_array<std::string_view>({ "Session" });
        inline constexpr auto G29_L5 = std::to_array<std::string_view>({ "TaskAfterAudio" });
        inline constexpr auto G29_L0_RULES = compile_static_rules(G29_L0);
        inline constexpr auto G29_L1_RULES = compile_static_rules(G29_L1);
        inline constexpr auto G29_L2_RULES = compile_static_rules(G29_L2);
        inline constexpr auto G29_L3_RULES = compile_static_rules(G29_L3);
        inline constexpr auto G29_L4_RULES = compile_static_rules(G29_L4);
        inline constexpr auto G29_L5_RULES = compile_static_rules(G29_L5);
        inline constexpr std::array<std::span<const std::string_view>, 6> G29 = {
            G29_L0, G29_L1, G29_L2, G29_L3, G29_L4, G29_L5
        };
        inline constexpr std::array<std::span<const DelimiterRule>, 6> G29_RULES = {
            G29_L0_RULES, G29_L1_RULES, G29_L2_RULES, G29_L3_RULES, G29_L4_RULES, G29_L5_RULES
        };

    } // namespace schema_tables

    /**
     * @brief Compile-time 3D table of SAGE INI/INC structural delimiter strings (Groups -> Levels -> Keywords).
     */
    inline constexpr std::array<std::span<const std::span<const std::string_view>>, 30> INI_DELIMITERS = {
        schema_tables::G0,  schema_tables::G1,  schema_tables::G2,  schema_tables::G3,  schema_tables::G4,
        schema_tables::G5,  schema_tables::G6,  schema_tables::G7,  schema_tables::G8,  schema_tables::G9,
        schema_tables::G10, schema_tables::G11, schema_tables::G12, schema_tables::G13, schema_tables::G14,
        schema_tables::G15, schema_tables::G16, schema_tables::G17, schema_tables::G18, schema_tables::G19,
        schema_tables::G20, schema_tables::G21, schema_tables::G22, schema_tables::G23, schema_tables::G24,
        schema_tables::G25, schema_tables::G26, schema_tables::G27, schema_tables::G28, schema_tables::G29
    };

    /**
     * @brief Pre-compiled and pre-sorted constexpr rule tables corresponding to INI_DELIMITERS.
     */
    inline constexpr std::array<std::span<const std::span<const DelimiterRule>>, 30> INI_DELIMITER_RULES = {
        schema_tables::G0_RULES,  schema_tables::G1_RULES,  schema_tables::G2_RULES,  schema_tables::G3_RULES,
        schema_tables::G4_RULES,  schema_tables::G5_RULES,  schema_tables::G6_RULES,  schema_tables::G7_RULES,
        schema_tables::G8_RULES,  schema_tables::G9_RULES,  schema_tables::G10_RULES, schema_tables::G11_RULES,
        schema_tables::G12_RULES, schema_tables::G13_RULES, schema_tables::G14_RULES, schema_tables::G15_RULES,
        schema_tables::G16_RULES, schema_tables::G17_RULES, schema_tables::G18_RULES, schema_tables::G19_RULES,
        schema_tables::G20_RULES, schema_tables::G21_RULES, schema_tables::G22_RULES, schema_tables::G23_RULES,
        schema_tables::G24_RULES, schema_tables::G25_RULES, schema_tables::G26_RULES, schema_tables::G27_RULES,
        schema_tables::G28_RULES, schema_tables::G29_RULES
    };

    /**
     * @brief Compile-time table of SAGE .str category delimiter strings.
     */
    inline constexpr auto STR_DELIMITERS = std::to_array<std::string_view>({
        "LETTER", "NUMBER", "TIME", "Color", "Team", "MSG", "GUI", "APT", "Apt", "URL",
        "TOOLTIP", "ToolTip", "Tooltip", "MOTD", "ERROR", "Buddy", "QM", "FTP",
        "FtpError", "WOL", "CHAT", "Chat", "LAN", "Network", "INI", "SIDE", "KEYBOARD",
        "MapTransfer", "CAMPAIGN", "DOZER", "UPGRADE", "Upgrade", "Mouse", "SCRIPT",
        "SCIENCE", "CONTROLBAR", "CONTROLBar", "Controlbar", "RADAR", "OBJECT",
        "Object", "CampaignName", "MAP", "Map", "DIALOGEVENT", "Audio", "LABEL",
        "MESSAGE", "ThingTemplate", "CREDITS", "STAT", "Stat", "LW", "LWScenario",
        "LWA", "WOTR", "WOTRTutorial", "WOTRSCRIPT", "BANNERUI", "SUBTITLE",
        "BONUSROUND", "FESL", "APPDATA", "RULE", "VALUE", "CAH", "CreateAHero",
        "WIZARD", "STRATEGICHUD", "HUD", "CP", "Award", "CLAN", "Version"
        });

    /**
     * @brief Pre-compiled and pre-sorted constexpr rule table corresponding to STR_DELIMITERS.
     */
    inline constexpr auto STR_DELIMITER_RULES = compile_static_rules(STR_DELIMITERS);

} // namespace lotm::ini
