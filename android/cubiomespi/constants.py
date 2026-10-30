from enum import IntEnum
class Dimension(IntEnum):
    DIM_NETHER = -1
    DIM_OVERWORLD = 0
    DIM_END = 1
    DIM_UNDEF = 1000


class MCVersion(IntEnum):
    MC_1_0_0 = 3
    MC_1_1_0 = 4
    MC_1_2_5 = 5
    MC_1_3_2 = 6
    MC_1_4_7 = 7
    MC_1_5_2 = 8
    MC_1_6_4 = 9
    MC_1_7_10 =10
    MC_1_8_9 = 11
    MC_1_9_4 = 12
    MC_1_10_2 = 13
    MC_1_11_2 = 14
    MC_1_12_2 = 15
    MC_1_13_2 = 16
    MC_1_14_4 = 17
    MC_1_15_2 = 18
    MC_1_16_1 = 19
    MC_1_16_5 = 20
    MC_1_17_1 = 21
    MC_1_18_2 = 22
    MC_1_19_2 = 23
    MC_1_19   = 24
    MC_1_20 = 25
    MC_1_21 = 26


class Structure: 
    Feature = (0, "Feature")
    Desert_Pyramid = (1, "Desert Pyramid")
    Jungle_Temple = (2, "Jungle Temple")
    Jungle_Pyramid = (2, "Jungle Pyramid")
    Swamp_Hut = (3, "Swamp Hut")
    Igloo = (4, "Igloo")
    Village = (5, "Village")
    Ocean_Ruin = (6, "Ocean Ruin")
    Shipwreck = (7, "Shipwreck")
    Monument = (8, "Monument")
    Mansion = (9, "Mansion")
    Outpost = (10, "Outpost")
    Ruined_Portal = (11, "Ruined Portal")
    Ruined_Portal_N = (12, "Ruined Portal N")
    Ancient_City = (13, "Ancient City")
    Treasure = (14, "Treasure")
    Mineshaft = (15, "Mineshaft")
    Desert_Well = (16, "Desert Well")
    Geode = (17, "Geode")
    Fortress = (18, "Fortress")
    Bastion = (19, "Bastion")
    End_City = (20, "End City")
    End_Gateway = (21, "End Gateway")
    End_Island = (22, "End Island")
    Trail_Ruin = (23, "Trail Ruin")
    Trial_Chambers = (24, "Trial Chambers")
    FEATURE_NUM = (25, "FEATURE_NUM")


class BiomeID(IntEnum):
    def __new__(cls, value, label=None):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label or "Unknown"
        return obj
    none = (-1, "None")
    ocean = (0, "Ocean")
    plains = (1, "Plains")
    desert = (2, "Desert")
    mountains = (3, "Mountains")
    extremeHills = (3, "Extreme Hills")
    forest = (4, "Forest")
    taiga = (5, "Taiga")
    swamp = (6, "Swamp")
    swampland = (6, "Swampland")
    river = (7, "River")
    nether_wastes = (8, "Nether Wastes")
    hell = (8, "Hell")
    the_end = (9, "The End")
    sky = (9, "Sky")
    frozen_ocean = (10, "Frozen Ocean")
    frozenOcean = (10, "Frozen Ocean")
    frozen_river = (11, "Frozen River")
    frozenRiver = (11, "Frozen River")
    snowy_tundra = (12, "Snowy Tundra")
    icePlains = (12, "Ice Plains")
    snowy_mountains = (13, "Snowy Mountains")
    iceMountains = (13, "Ice Mountains")
    mushroom_fields = (14, "Mushroom Fields")
    mushroomIsland = (14, "Mushroom Island")
    mushroom_field_shore = (15, "Mushroom Field Shore")
    mushroomIslandShore = (15, "Mushroom Island Shore")
    beach = (16, "Beach")
    desert_hills = (17, "Desert Hills")
    desertHills = (17, "Desert Hills")
    wooded_hills = (18, "Wooded Hills")
    forestHills = (18, "Forest Hills")
    taiga_hills = (19, "Taiga Hills")
    taigaHills = (19, "Taiga Hills")
    mountain_edge = (20, "Mountain Edge")
    extremeHillsEdge = (20, "Extreme Hills Edge")
    jungle = (21, "Jungle")
    jungle_hills = (22, "Jungle Hills")
    jungleHills = (22, "Jungle Hills")
    jungle_edge = (23, "Jungle Edge")
    jungleEdge = (23, "Jungle Edge")
    deep_ocean = (24, "Deep Ocean")
    deepOcean = (24, "Deep Ocean")
    stone_shore = (25, "Stone Shore")
    stoneBeach = (25, "Stone Beach")
    snowy_beach = (26, "Snowy Beach")
    coldBeach = (26, "Cold Beach")
    birch_forest = (27, "Birch Forest")
    birchForest = (27, "Birch Forest")
    birch_forest_hills = (28, "Birch Forest Hills")
    birchForestHills = (28, "Birch Forest Hills")
    dark_forest = (29, "Dark Forest")
    roofedForest = (29, "Roofed Forest")
    snowy_taiga = (30, "Snowy Taiga")
    coldTaiga = (30, "Cold Taiga")
    snowy_taiga_hills = (31, "Snowy Taiga Hills")
    coldTaigaHills = (31, "Cold Taiga Hills")
    giant_tree_taiga = (32, "Giant Tree Taiga")
    megaTaiga = (32, "Mega Taiga")
    giant_tree_taiga_hills = (33, "Giant Tree Taiga Hills")
    megaTaigaHills = (33, "Mega Taiga Hills")
    wooded_mountains = (34, "Wooded Mountains")
    extremeHillsPlus = (34, "Extreme Hills Plus")
    savanna = (35, "Savanna")
    savanna_plateau = (36, "Savanna Plateau")
    savannaPlateau = (36, "Savanna Plateau")
    badlands = (37, "Badlands")
    mesa = (37, "Mesa")
    wooded_badlands_plateau = (38, "Wooded Badlands Plateau")
    mesaPlateau_F = (38, "Mesa Plateau F")
    badlands_plateau = (39, "Badlands Plateau")
    mesaPlateau = (39, "Mesa Plateau")
    small_end_islands = (40, "Small End Islands")
    end_midlands = (41, "End Midlands")
    end_highlands = (42, "End Highlands")
    end_barrens = (43, "End Barrens")
    warm_ocean = (44, "Warm Ocean")
    warmOcean = (44, "Warm Ocean")
    lukewarm_ocean = (45, "Lukewarm Ocean")
    lukewarmOcean = (45, "Lukewarm Ocean")
    cold_ocean = (46, "Cold Ocean")
    coldOcean = (46, "Cold Ocean")
    deep_warm_ocean = (47, "Deep Warm Ocean")
    warmDeepOcean = (47, "Deep Warm Ocean")
    deep_lukewarm_ocean = (48, "Deep Lukewarm Ocean")
    lukewarmDeepOcean = (48, "Deep Lukewarm Ocean")
    deep_cold_ocean = (49, "Deep Cold Ocean")
    coldDeepOcean = (49, "Deep Cold Ocean")
    deep_frozen_ocean = (50, "Deep Frozen Ocean")
    frozenDeepOcean = (50, "Deep Frozen Ocean")
    seasonal_forest = (51, "Seasonal Forest")
    rainforest = (52, "Rainforest")
    shrubland = (53, "Shrubland")
    the_void = (127, "The Void")
    sunflower_plains = (129, "Sunflower Plains")
    desert_lakes = (130, "Desert Lakes")
    gravelly_mountains = (131, "Gravelly Mountains")
    flower_forest = (132, "Flower Forest")
    taiga_mountains = (133, "Taiga Mountains")
    swamp_hills = (134, "Swamp Hills")
    ice_spikes = (140, "Ice Spikes")
    modified_jungle = (149, "Modified Jungle")
    modified_jungle_edge = (151, "Modified Jungle Edge")
    tall_birch_forest = (155, "Tall Birch Forest")
    tall_birch_hills = (156, "Tall Birch Hills")
    dark_forest_hills = (157, "Dark Forest Hills")
    snowy_taiga_mountains = (158, "Snowy Taiga Mountains")
    giant_spruce_taiga = (160, "Giant Spruce Taiga")
    giant_spruce_taiga_hills = (161, "Giant Spruce Taiga Hills")
    modified_gravelly_mountains = (162, "Modified Gravelly Mountains")
    shattered_savanna = (163, "Shattered Savanna")
    shattered_savanna_plateau = (164, "Shattered Savanna Plateau")
    eroded_badlands = (165, "Eroded Badlands")
    modified_wooded_badlands_plateau = (166, "Modified Wooded Badlands Plateau")
    modified_badlands_plateau = (167, "Modified Badlands Plateau")
    bamboo_jungle = (168, "Bamboo Jungle")
    bamboo_jungle_hills = (169, "Bamboo Jungle Hills")
    soul_sand_valley = (170, "Soul Sand Valley")
    crimson_forest = (171, "Crimson Forest")
    warped_forest = (172, "Warped Forest")
    basalt_deltas = (173, "Basalt Deltas")
    dripstone_caves = (174, "Dripstone Caves")
    lush_caves = (175, "Lush Caves")
    meadow = (177, "Meadow")
    grove = (178, "Grove")
    snowy_slopes = (179, "Snowy Slopes")
    jagged_peaks = (180, "Jagged Peaks")
    frozen_peaks = (181, "Frozen Peaks")
    stony_peaks = (182, "Stony Peaks")
    old_growth_birch_forest = (155, "Old Growth Birch Forest")
    old_growth_pine_taiga = (32, "Old Growth Pine Taiga")
    old_growth_spruce_taiga = (160, "Old Growth Spruce Taiga")
    snowy_plains = (12, "Snowy Plains")
    sparse_jungle = (23, "Sparse Jungle")
    stony_shore = (25, "Stony Shore")
    windswept_hills = (3, "Windswept Hills")
    windswept_forest = (34, "Windswept Forest")
    windswept_gravelly_hills = (131, "Windswept Gravelly Hills")
    windswept_savanna = (163, "Windswept Savanna")
    wooded_badlands = (38, "Wooded Badlands")
    deep_dark = (183, "Deep Dark")
    mangrove_swamp = (184, "Mangrove Swamp")
    cherry_grove = (185, "Cherry Grove")


class BiomeGroups:
        Forests = [
            BiomeID.forest,
            BiomeID.forestHills,
            BiomeID.flower_forest,
            BiomeID.taiga,
            BiomeID.taiga_hills,
            BiomeID.snowy_taiga,
            BiomeID.snowy_taiga_hills,
            BiomeID.birch_forest,
            BiomeID.birch_forest_hills,
            BiomeID.tall_birch_forest,
            BiomeID.tall_birch_hills,
            BiomeID.dark_forest,
            BiomeID.dark_forest_hills
        ]

        Beaches = [
            BiomeID.beach,
            BiomeID.coldBeach,
            BiomeID.snowy_beach
        ]

        DesertBiomes = [
            BiomeID.desert,
            BiomeID.desert_hills,
            BiomeID.desert_lakes,
            BiomeID.desertHills
        ]

        Oceans = [
            BiomeID.ocean,
            BiomeID.frozen_ocean,
            BiomeID.deep_ocean,
            BiomeID.warm_ocean,
            BiomeID.lukewarm_ocean,
            BiomeID.cold_ocean,
            BiomeID.deep_warm_ocean,
            BiomeID.deep_lukewarm_ocean,
            BiomeID.deep_cold_ocean,
            BiomeID.deep_frozen_ocean,
        ]



class BastionType(IntEnum):
    HOUSING =  0
    STABLES =  1
    TREASURE = 2
    BRIDGE =   3
