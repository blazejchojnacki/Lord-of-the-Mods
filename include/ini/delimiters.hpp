/**
 * @file include/ini/delimiters.hpp
 * @brief Static constexpr delimiter tables for SAGE .ini, .inc, and .str schemas
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <array>
#include <span>
#include <string_view>

namespace lotm::ini {

    using DelimiterLevel = std::span<const std::string_view>;
    using DelimiterGroup = std::span<const DelimiterLevel>;

    namespace detail {

        // Group 0
        inline constexpr std::array<std::string_view, 88> G0_L0 = {
            "AudioEvent", "Multisound", "StreamedSound", "AmbientStream", "Animation", "Armor",
            "AudioSettings", "AnimationSoundClientBehaviorGlobalSetting", "ModifierList", "BannerType",
            "ButtonSet", "CommandButton", "CommandMap", "DebugCommandMap", "CommandSet",
            "ControlBarResizer", "SpecialPower", "DamageFX", "DrawGroupInfo", "EmotionNugget",
            "SkyboxTextureSet", "GlowEffect", "RingEffect", "FireEffect", "CloudEffect", "ShadowMap",
            "Fire", "FontDefaultSettings", "FontSubstitution", "GameData", "StaticGameLOD",
            "DynamicGameLOD", "AudioLOD", "HouseColor", "LargeGroupAudioUnusedKnownKeys",
            "LightPointLevel", "LivingWorldSound", "LivingWorldObject", "LivingWorldAnimObject",
            "LivingWorldAITemplate", "AutoResolveArmor", "AutoResolveBody", "AutoResolveCombatChain",
            "AutoResolveHandicapLevel", "AutoResolveReinforcementSchedule", "AutoResolveWeapon",
            "LivingWorldPlayerTemplate", "Locomotor", "MappedImage", "MeshNameMatches", "MiscAudio",
            "Mouse", "MouseCursor", "OnlineChatColors", "MultiplayerSettings", "MultiplayerColor",
            "MusicTrack", "OptionGroup", "ParticleSystem", "Pathfinder", "PlayerAIType",
            "PlayerTemplate", "Rank", "Bridge", "Road", "ShellMenuScheme", "Science",
            "ScoredKillEvaAnnouncer", "SpecialPower", "DialogEvent", "Terrain", "Upgrade",
            "VictorySystemData", "FactionVictoryData", "Video", "WaterSet", "WaterTransparency",
            "WaterTextureList", "Weather", "WeatherData", "WebpageURL", "AIBase",
            "AIDozerAssignment", "LoadSubsystem", "SpawnArmy", "ConcurrentRegionBonus", "Credits"
        };
        inline constexpr std::array<DelimiterLevel, 1> GROUP_0 = { G0_L0 };

        // Group 1
        inline constexpr std::array<std::string_view, 1> G1_L0 = { "AptButtonTooltipMap" };
        inline constexpr std::array<std::string_view, 1> G1_L1 = { "ButtonMap" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_1 = { G1_L0, G1_L1 };

        // Group 2
        inline constexpr std::array<std::string_view, 1> G2_L0 = { "ArmySummaryDescription" };
        inline constexpr std::array<std::string_view, 1> G2_L1 = { "UnitCategory" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_2 = { G2_L0, G2_L1 };

        // Group 3
        inline constexpr std::array<std::string_view, 1> G3_L0 = { "AwardSystem" };
        inline constexpr std::array<std::string_view, 2> G3_L1 = { "ObjectAward", "ThingStat" };
        inline constexpr std::array<std::string_view, 1> G3_L2 = { "Trigger" };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_3 = { G3_L0, G3_L1, G3_L2 };

        // Group 4
        inline constexpr std::array<std::string_view, 1> G4_L0 = { "ControlBarScheme" };
        inline constexpr std::array<std::string_view, 1> G4_L1 = { "ImagePart" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_4 = { G4_L0, G4_L1 };

        // Group 5
        inline constexpr std::array<std::string_view, 7> G5_L0 = {
            "Object", "ChildObject", "ObjectReskin", "CrateData",
            "FormationAssistant", "FXParticleSystem", "FXList"
        };
        inline constexpr std::array<std::string_view, 44> G5_L1 = {
            "Draw", "Body", "ArmorSet", "WeaponSet", "LocomotorSet", "UnitSpecificSounds",
            "Flammability", "ThreatBreakdown", "ClientUpdate", "ClientBehavior", "Behavior",
            "AutoResolveArmor", "AutoResolveWeapon", "AddModule", "ReplaceModule", "InheritableModule",
            "FormationPreviewDecal", "FormationPreviewItemDecal", "UnitDefinition",
            "FormationTemplate", "FormationSelection", "Alpha", "Update", "Physics",
            "EmissionVelocity", "EmissionVolume", "Event", "Emitter", "Wind", "System", "Color",
            "Sound", "ParticleSystem", "DynamicDecal", "TerrainScorch", "BuffNugget", "ViewShake",
            "CameraShakerVolume", "TintDrawable", "FXListAtBonePos", "LightPulse", "EvaEvent",
            "AttachedModel"
        };
        inline constexpr std::array<std::string_view, 26> G5_L2 = {
            "LodOptions", "DefaultModelConditionState", "ModelConditionState", "IdleAnimationState",
            "AnimationState", "TransitionState", "SoundState", "ProductionModifier",
            "FireWeaponNugget", "InvisibilityNugget", "FloodMember", "SoundUpgrade", "Turret",
            "ReplaceObject", "Radius", "Opacity", "Angle", "DecalTemplate", "GridDecalTemplate",
            "MeleeBehavior", "Behavior", "Body", "ClientBehavior", "ObjectStatusOfContained =",
            "Rows", "AddEmotion = OVERRIDE"
        };
        inline constexpr std::array<std::string_view, 4> G5_L3 = {
            "Animation", "BeginScript", "MeleeBehavior", "UnitSpecificSounds"
        };
        inline constexpr std::array<DelimiterLevel, 4> GROUP_5 = { G5_L0, G5_L1, G5_L2, G5_L3 };

        // Group 6
        inline constexpr std::array<std::string_view, 1> G6_L0 = { "CreateAHeroSystem" };
        inline constexpr std::array<std::string_view, 3> G6_L1 = {
            "CreateAHeroBlingBinder", "CreateAHeroBling", "CreateAHeroClass"
        };
        inline constexpr std::array<std::string_view, 1> G6_L2 = { "SubClass" };
        inline constexpr std::array<std::string_view, 2> G6_L3 = { "Attribute", "ViewInfo" };
        inline constexpr std::array<DelimiterLevel, 4> GROUP_6 = { G6_L0, G6_L1, G6_L2, G6_L3 };

        // Group 7
        inline constexpr std::array<std::string_view, 1> G7_L0 = { "CrowdResponse" };
        inline constexpr std::array<std::string_view, 1> G7_L1 = { "Threshold" };
        inline constexpr std::array<std::string_view, 1> G7_L2 = { "UnitSpecificSounds" };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_7 = { G7_L0, G7_L1, G7_L2 };

        // Group 8
        inline constexpr std::array<std::string_view, 1> G8_L0 = { "AIData" };
        inline constexpr std::array<std::string_view, 3> G8_L1 = {
            "SideInfo", "SkirmishBuildList", "AttackPriority"
        };
        inline constexpr std::array<std::string_view, 1> G8_L2 = { "Structure" };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_8 = { G8_L0, G8_L1, G8_L2 };

        // Group 9
        inline constexpr std::array<std::string_view, 3> G9_L0 = {
            "PredefinedEvaEvent", "NewEvaEvent", "MiscEvaData"
        };
        inline constexpr std::array<std::string_view, 1> G9_L1 = { "SideSound" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_9 = { G9_L0, G9_L1 };

        // Group 10
        inline constexpr std::array<std::string_view, 2> G10_L0 = {
            "ExperienceScalarTable", "ExperienceLevel"
        };
        inline constexpr std::array<std::string_view, 1> G10_L1 = { "SelectionDecal" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_10 = { G10_L0, G10_L1 };

        // Group 11
        inline constexpr std::array<std::string_view, 1> G11_L0 = { "FireLogicSystem" };
        inline constexpr std::array<std::string_view, 1> G11_L1 = { "TerrainCellType" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_11 = { G11_L0, G11_L1 };

        // Group 12
        inline constexpr std::array<std::string_view, 1> G12_L0 = { "FormationAssistant" };
        inline constexpr std::array<std::string_view, 3> G12_L1 = {
            "UnitDefinition", "FormationTemplate", "FormationSelection"
        };
        inline constexpr std::array<std::string_view, 1> G12_L2 = { "Rows" };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_12 = { G12_L0, G12_L1, G12_L2 };

        // Group 13
        inline constexpr std::array<std::string_view, 1> G13_L0 = { "InGameNotificationBox" };
        inline constexpr std::array<std::string_view, 1> G13_L1 = { "NotificationType" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_13 = { G13_L0, G13_L1 };

        // Group 14
        inline constexpr std::array<std::string_view, 1> G14_L0 = { "InGameUI" };
        inline constexpr std::array<std::string_view, 1> G14_L1 = { "RadiusCursorTemplate" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_14 = { G14_L0, G14_L1 };

        // Group 15
        inline constexpr std::array<std::string_view, 2> G15_L0 = {
            "LargeGroupAudioMap", "LargeGroupAudioUnusedKnownKeys"
        };
        inline constexpr std::array<std::string_view, 1> G15_L1 = { "Sound" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_15 = { G15_L0, G15_L1 };

        // Group 16
        inline constexpr std::array<std::string_view, 1> G16_L0 = { "LinearCampaign" };
        inline constexpr std::array<std::string_view, 1> G16_L1 = { "Mission" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_16 = { G16_L0, G16_L1 };

        // Group 17
        inline constexpr std::array<std::string_view, 7> G17_L0 = {
            "LivingWorldMapInfo", "LivingWorldArmyIcon", "LivingWorldSound", "LivingWorldObject",
            "LivingWorldAnimObject", "LivingWorldBuildingIcon", "LivingWorldBuildPlotIcon"
        };
        inline constexpr std::array<std::string_view, 1> G17_L1 = { "Object" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_17 = { G17_L0, G17_L1 };

        // Group 18
        inline constexpr std::array<std::string_view, 1> G18_L0 = { "AutoResolveLeadership" };
        inline constexpr std::array<std::string_view, 1> G18_L1 = { "BonusForLevel" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_18 = { G18_L0, G18_L1 };

        // Group 19
        inline constexpr std::array<std::string_view, 2> G19_L0 = {
            "LivingWorldAutoResolveResourceBonus", "LivingWorldAutoResolveSciencePurchasePointBonus"
        };
        inline constexpr std::array<std::string_view, 1> G19_L1 = { "Bonus" };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_19 = { G19_L0, G19_L1 };

        // Group 20
        inline constexpr std::array<std::string_view, 1> G20_L0 = { "LivingWorldBuilding" };
        inline constexpr std::array<std::string_view, 1> G20_L1 = { "BuildingNugget" };
        inline constexpr std::array<std::string_view, 1> G20_L2 = { "ArmyToSpawn" };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_20 = { G20_L0, G20_L1, G20_L2 };

        // Group 21
        inline constexpr std::array<std::string_view, 1> G21_L0 = { "LivingWorldRegionEffects" };
        inline constexpr std::array<std::string_view, 7> G21_L1 = {
            "BordersEffect", "FilledOwnershipEffect", "MouseoverEffectFlareup",
            "MouseoutEffectFlareup", "HomeRegionHighlight", "RegionSelectionEffect", "UnifiedEffect"
        };
        inline constexpr std::array<std::string_view, 1> G21_L2 = { "ColorIntensityControlPoint" };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_21 = { G21_L0, G21_L1, G21_L2 };

        // Group 22
        inline constexpr std::array<std::string_view, 1> G22_L0 = { "ObjectCreationList" };
        inline constexpr std::array<std::string_view, 3> G22_L1 = {
            "CreateObject", "CreateDebris", "FireWeapon"
        };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_22 = { G22_L0, G22_L1 };

        // Group 23
        inline constexpr std::array<std::string_view, 1> G23_L0 = { "StanceTemplate" };
        inline constexpr std::array<std::string_view, 1> G23_L1 = { "Stance" };
        inline constexpr std::array<std::string_view, 1> G23_L2 = { "MeleeBehavior" };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_23 = { G23_L0, G23_L1, G23_L2 };

        // Group 24
        inline constexpr std::array<std::string_view, 1> G24_L0 = { "StrategicHUD" };
        inline constexpr std::array<std::string_view, 18> G24_L1 = {
            "ArmyDetailsPanel", "BattleResolver", "BuildQueueDetailsPanel",
            "CancelArmyMemberMoveButton", "CancelArmyMoveButton", "Checklist",
            "DestroyBuildingButton", "CancelBuildingConstructionButton", "DisbandArmyMemberButton",
            "DynamicAutoResolveDialog", "OptionsButton", "ObjectivesButton",
            "RegionDetailsPanelStructuresPage", "RegionDisplay", "StatsDisplay",
            "ToggleSelectionDetailsButton", "TypeImages", "UpgradeUnitButton"
        };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_24 = { G24_L0, G24_L1 };

        // Group 25
        inline constexpr std::array<std::string_view, 1> G25_L0 = { "Weapon" };
        inline constexpr std::array<std::string_view, 19> G25_L1 = {
            "DamageNugget", "DamageFieldNugget", "DOTNugget", "AttributeModifierNugget",
            "StealMoneyNugget", "ProjectileNugget", "MetaImpactNugget", "SlaveAttackNugget",
            "EmotionWeaponNugget", "FireLogicNugget", "WeaponOCLNugget", "HordeAttackNugget",
            "DamageContainedNugget", "LuaEventNugget", "ParalyzeNugget", "SpawnAndFadeNugget",
            "GrabNugget", "SpecialModelConditionNugget", "OpenGateNugget"
        };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_25 = { G25_L0, G25_L1 };

        // Group 26
        inline constexpr std::array<std::string_view, 1> G26_L0 = { "WindowTransition" };
        inline constexpr std::array<std::string_view, 1> G26_L1 = { "Window" };
        inline constexpr std::array<std::string_view, 1> G26_L2 = { "Transition" };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_26 = { G26_L0, G26_L1, G26_L2 };

        // Group 27
        inline constexpr std::array<std::string_view, 1> G27_L0 = { "SkirmishAIData" };
        inline constexpr std::array<std::string_view, 3> G27_L1 = {
            "CombatChainDefinition", "BrutalDifficultyCheats", "DifficultyTuning"
        };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_27 = { G27_L0, G27_L1 };

        // Group 28
        inline constexpr std::array<std::string_view, 1> G28_L0 = { "ArmyDefinition" };
        inline constexpr std::array<std::string_view, 3> G28_L1 = {
            "AIEconomyAssigment", "AIWallNodeAssignment", "ArmyMemberDefinition"
        };
        inline constexpr std::array<DelimiterLevel, 2> GROUP_28 = { G28_L0, G28_L1 };

        // Group 29
        inline constexpr std::array<std::string_view, 2> G29_L0 = {
            "LivingWorldRegionCampaign", "RegionCampain"
        };
        inline constexpr std::array<std::string_view, 2> G29_L1 = {
            "Region", "LivingWorldPlayerArmy"
        };
        inline constexpr std::array<std::string_view, 3> G29_L2 = {
            "Connection", "RestrictBuildings", "ArmyEntry"
        };
        inline constexpr std::array<DelimiterLevel, 3> GROUP_29 = { G29_L0, G29_L1, G29_L2 };

        // Group 30
        inline constexpr std::array<std::string_view, 1> G30_L0 = { "LivingWorldCampaign" };
        inline constexpr std::array<std::string_view, 5> G30_L1 = {
            "Scenario", "Act", "AddPlayer", "Tutorial", "LivingWorldVictoryType"
        };
        inline constexpr std::array<std::string_view, 8> G30_L2 = {
            "PlayerDefeatCondition", "TeamDefeatCondition", "TeamVictoryCondition",
            "EyeTowerPoints", "OwnershipSet", "Turn", "SpawnArmy", "StartingRestriction"
        };
        inline constexpr std::array<std::string_view, 3> G30_L3 = {
            "SpawnBuildings", "SpawnArmies", "Phase"
        };
        inline constexpr std::array<std::string_view, 1> G30_L4 = { "Session" };
        inline constexpr std::array<std::string_view, 1> G30_L5 = { "TaskAfterAudio" };
        inline constexpr std::array<DelimiterLevel, 6> GROUP_30 = {
            G30_L0, G30_L1, G30_L2, G30_L3, G30_L4, G30_L5
        };

    } // namespace detail

    inline constexpr std::array<DelimiterGroup, 31> INI_DELIMITERS = {
        detail::GROUP_0,  detail::GROUP_1,  detail::GROUP_2,  detail::GROUP_3,
        detail::GROUP_4,  detail::GROUP_5,  detail::GROUP_6,  detail::GROUP_7,
        detail::GROUP_8,  detail::GROUP_9,  detail::GROUP_10, detail::GROUP_11,
        detail::GROUP_12, detail::GROUP_13, detail::GROUP_14, detail::GROUP_15,
        detail::GROUP_16, detail::GROUP_17, detail::GROUP_18, detail::GROUP_19,
        detail::GROUP_20, detail::GROUP_21, detail::GROUP_22, detail::GROUP_23,
        detail::GROUP_24, detail::GROUP_25, detail::GROUP_26, detail::GROUP_27,
        detail::GROUP_28, detail::GROUP_29, detail::GROUP_30
    };

    inline constexpr std::array<std::string_view, 73> STR_DELIMITERS = {
        "LETTER", "NUMBER", "TIME", "Color", "Team", "MSG", "GUI", "APT", "Apt", "URL",
        "TOOLTIP", "ToolTip", "Tooltip", "MOTD", "ERROR", "Buddy", "QM", "FTP", "FtpError",
        "WOL", "CHAT", "Chat", "LAN", "Network", "INI", "SIDE", "KEYBOARD", "MapTransfer",
        "CAMPAIGN", "DOZER", "UPGRADE", "Upgrade", "Mouse", "SCRIPT", "SCIENCE", "CONTROLBAR",
        "CONTROLBar", "Controlbar", "RADAR", "OBJECT", "Object", "CampaignName", "MAP", "Map",
        "DIALOGEVENT", "Audio", "LABEL", "MESSAGE", "ThingTemplate", "CREDITS", "STAT", "Stat",
        "LW", "LWScenario", "LWA", "WOTR", "WOTRTutorial", "WOTRSCRIPT", "BANNERUI", "SUBTITLE",
        "BONUSROUND", "FESL", "APPDATA", "RULE", "VALUE", "CAH", "CreateAHero", "WIZARD",
        "STRATEGICHUD", "HUD", "CP", "Award", "CLAN", "Version"
    };

} // namespace lotm::ini
