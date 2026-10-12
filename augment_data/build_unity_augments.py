"""
Unity Augmented Armor table builder.

Populates augment_tables.json (and the static/data copy) with Unity Concord
Wanted-battle +1 gear augment data (Path A, ranks 1-15).

Rank 15 max stats sourced from BG-Wiki (https://www.bg-wiki.com/ffxi/Unity_Rewards
and per-item pages). Ranks 1-14 are interpolated using the standard Unity
augment progression verified against BG-Wiki per-item rank tables
(e.g. Gelatinous Ring +1, Sailfi Belt +1, Blistering Sallet +1, Loxotic Mace +1,
Warder's Charm +1):
  - augment slot 1 unlocks at rank 1 and scales linearly to max at rank 15
  - augment slot 2 unlocks at rank 6 and scales linearly to max at rank 15
  - augment slot 3 unlocks at rank 11 and scales linearly to max at rank 15
Interpolated tiers are flagged `interpolated: true`, matching the existing
`interpolation_applied` convention used for JSE necks.

Run:  python3 augment_data/build_unity_augments.py
"""

import json
import math
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent

# =============================================================================
# Rank-15 augment data (BG-Wiki "Unity Rewards", verified against item pages).
# Each entry: item name (windower `en` short name) -> list of augment slots.
# Each slot is a stat-description string parsed by parse_stat_group().
# Slot order matters: index 0 unlocks R1, index 1 unlocks R6, index 2 unlocks R11.
# =============================================================================

UNITY_R15 = {
    # ----- Melee weapons -----
    "Aizkora +1":         ["Acc & M.Acc +45", "Triple Attack +3%", "Quad Attack +3%"],
    "Anathema Harpe +1":  ["DMG +20", "Acc & M.Acc +40", "Crit Hit Rate +10%"],
    "Beheader +1":        ["DMG +53", "Acc & M.Acc +40", "Haste +10%"],
    "Buramgh +1":         ["DMG +30", "Pet: Acc & M.Acc +30", "Acc & M.Acc +35"],
    "Combuster +1":       ["DMG +19", "Acc & M.Acc +40", "Store TP +10"],
    "Comeuppances +1":    ["DEX +20", "Acc & M.Acc & Pet: Acc & M.Acc +40", "Store TP +10"],
    "Demers. Degen +1":   ["Acc & M.Acc +45", "DEX +10", "Sword Enhancement Spell Dmg +50"],
    "Emeici +1":          ["DMG +30", "Acc & M.Acc +30", "Crit Hit Rate +10%"],
    "Fists of Fury +1":   ["DMG +14", "Acc & M.Acc +40", "Regen +5"],
    "Flyssa +1":          ["DMG +10", "Acc & M.Acc +40", "Damage Taken -5%"],
    "Gae Derg +1":        ["DMG +62", "Acc & M.Acc +40", "Store TP +8"],
    "Habilitator +1":     ["DMG +21", "Acc & M.Acc & Pet: Acc & M.Acc +40", "STR/DEX/CHR +10"],
    "Jugo Kukri +1":      ["DMG +13", "Acc & M.Acc +40", "Evasion +20"],
    "Kladenets +1":       ["DMG +50", "Acc & M.Acc +40", "Fast Cast +10%"],
    "Kunimune +1":        ["TP Bonus +500", "Acc & M.Acc +30", "STR +10"],
    "Kustawi +1":         ["Ranged Attack +20", "Rng. Acc & M.Acc +40", "Enmity -5"],
    "Loxotic Mace +1":    ["DMG +33", "Acc & M.Acc +40", "Weapon Skill Dmg +10%"],
    "Mdomo Axe +1":       ["DMG +24", "Acc & M.Acc +40", "Pet: Acc & M.Acc +50"],
    "Montante +1":        ["DMG +20", "Acc & M.Acc +40", "HP +100"],
    "Norifusa +1":        ["DMG +10", "Acc & M.Acc +40", "Skillchain Dmg +20%"],
    "Nullis +1":          ["DMG +33", "Acc & M.Acc +40", "Dark Magic Skill +10"],
    "Perun +1":           ["Ranged Attack +45", "Rng. Acc & M.Acc +30", "Snapshot +5"],
    "Pixquizpan +1":      ["DMG +36", "Acc & M.Acc +40", "Magic Attack Bonus +50"],
    "Pukulatmuj +1":      ["DMG +38", "Acc & M.Acc +30", "Sword Enhancement Spell Dmg +150"],
    "Raicho +1":          ["DMG +20", "Acc & M.Acc +40", "Magic Defense Bonus +5"],
    "Sangarius +1":       ["DMG +35", "Acc & M.Acc +30", "Quad Attack +3%"],
    "Tancho +1":          ["DMG +25", "Acc, R.Acc, & M.Acc +20", "Magic Attack Bonus +20"],
    "Tanmogayi +1":       ["DMG +11", "Acc & M.Acc +40", "Attack +40"],
    "Ternion Dagger +1":  ["DMG +17", "Acc & M.Acc +40", "Weapon Skill Dmg +5%"],
    "Triska Scythe +1":   ["DMG +56", "Acc & M.Acc +40", "Crit Hit Rate +10%"],
    "Ushenzi +1":         ["DMG +28", "Acc & M.Acc +40", "Cure Potency Received +10%"],
    # ----- Mage weapons -----
    "Ababinili +1":       ["Healing Magic Skill +10", "Enhancing Magic Skill +10", "Damage Taken -10%"],
    "Contemplator +1":    ["M.Acc +70", "Enfeebling Magic Skill +20", "MND +10"],
    "Magesmasher +1":     ["DMG +45", "Acc & M.Acc +30", "Weapon Skill Dmg +15%"],
    "Marin Staff +1":     ["Magic Attack Bonus +40", "Acc & M.Acc +40", "INT/MND +10"],
    "Pouwhenua +1":       ["DMG +45", "Acc & M.Acc +30", "Store TP +10"],
    "Septoptic +1":       ["DMG +10", "Acc & M.Acc +40", "Magic Attack Bonus +30"],
    # ----- Ranged weapons -----
    "Antitail +1":        ["Magic Evasion +15", "Double Attack +3%"],
    "Imati +1":           ["DMG +17", "Ranged Acc +40", "Snapshot +10"],
    "Malison +1":         ["Ranged Attack +45", "Rng. Acc & M.Acc +40", "DMG +5"],
    "Mengado +1":         ["Snapshot +15", "DMG +10", "Ranged Acc +20"],
    "Paloma Bow +1":          ["DMG +9", "Ranged Acc +40", "Rapid Shot +15"],
    "Wingcutter +1":      ["Accuracy +10", "Evasion +10"],
    # ----- Shields & grips -----
    "Ajax +1":            ["Shield Block Rate +10%", "Enh. Magic Received Duration +10%"],
    "Deliverance +1":     ["Acc & M.Acc +30", "Shield Skill +10"],
    "Evalach +1":         ["HP +150", "Shield Skill +10", "Acc & M.Acc +20"],
    "Forfend +1":         ["Acc & M.Acc +15", "Enhancing Magic Skill +10"],
    "Refined Grip +1":    ["DEF +20", "Parrying Skill +10"],
    "Rigorous Grip +1":   ["Attack +30", "STR +15"],
    # ----- Unity armor -----
    "Adorned Helm +1":    ["Acc & M.Acc +45", "Attack +50", "All Base Stats +10"],
    "Alhazen Hat +1":     ["All Base Stats +30", "Evasion +50", "Acc, R.Acc, & M.Acc +25"],
    "Blistering Sallet +1": ["Acc & M.Acc +45", "Crit Hit Rate +10%", "STR/DEX +25"],
    "Hike Khat +1":       ["Phys. Damage Taken -10%", "Pet: Damage Taken -5%", "All Base Stats +10"],
    "Imp. Wing Hair. +1": ["Accuracy +35", "Magic Evasion +100", "Crit Hit Rate +10%"],
    "Loess Barbuta +1":   ["Enmity +10", "Damage Taken -10%", "All Base Stats +10"],
    "Stinger Helm +1":    ["Acc & M.Acc +30", "Phys. Damage Limit +5%", "All Base Stats +10"],
    "Agony Jerkin +1":    ["Attack +60", "Store TP +10", "All Base Stats +10"],
    "Cohort Cloak +1":    ["M.Acc +100", "Magic Attack Bonus +100", "All Base Stats +20"],
    "Emet Harness +1":    ["Evasion +30", "Accuracy +40", "All Base Stats +10"],
    "Hime Domaru +1":     ["Accuracy +45", "Double Attack +5%", "All Base Stats +10"],
    "Lugra Cloak +1":     ["M.Acc +60", "Spell Interruption Rate -20%", "All Base Stats +20"],
    "Obviat. Cuirass +1": ["Magic Evasion +60", "Enmity +5", "All Base Stats +10"],
    "Ros. Jaseran +1":    ["M.Acc +45", "Damage Taken -5%", "All Base Stats +10"],
    "Shomonjijoe +1":     ["Avatar: TP Bonus +300", "Avatar: Acc & M.Acc +30", "Avatar: All Base Stats +10"],
    "Tatena. Harama. +1": ["Accuracy +30", "All Base Stats +10", "Triple Attack +5%"],
    "Asteria Mitts +1":   ["MP +45", "Avatar: Acc & M.Acc +40", "Avatar: Magic Burst Bonus +10%"],
    "Gazu Bracelets +1":  ["Accuracy +50", "Haste +10%", "All Base Stats +10"],
    "Kachi. Kote +1":     ["Attack +45", "Acc & M.Acc +30", "All Base Stats +10"],
    "Lamassu Mitts +1":   ["Avatar: All Base Stats +30", "Avatar: Acc & M.Acc +40", "Avatar: Perpetuation Cost -5"],
    "Macabre Gaunt. +1":  ["Magic Evasion +75", "Occ. Resist Status Ailments +10%", "All Base Stats +10"],
    "Shigure Tekko +1":   ["Evasion +90", "Magic Evasion +80", "All Base Stats +10"],
    "Tatena. Gote +1":    ["Accuracy +40", "All Base Stats +10", "Triple Attack +4%"],
    "Assid. Pants +1":    ["Avatar: Acc & M.Acc +35", "Avatar: All Base Stats +20", "MP +20"],
    "Augury Cuisses +1":  ["Attack +60", "Magic Attack Bonus +30", "All Base Stats +10"],
    "Tatena. Haidate +1": ["Accuracy +60", "All Base Stats +10", "Triple Attack +3%"],
    "Zoar Subligar +1":   ["Accuracy +30", "Crit Hit Rate +5%", "All Base Stats +10"],
    "Hippo. Socks +1":    ["Resist Bind +45", "Evasion +20", "All Base Stats +10"],
    "Hygieia Clogs +1":   ["Cure Potency +15%", "Healing Magic Skill +10", "All Base Stats +10"],
    "Jute Boots +1":      ["DEX/AGI +15", "Magic Evasion +30", "All Base Stats +10"],
    "Regal Pumps +1":     ["Healing Magic Skill +10", "Enhancing Magic Skill +10", "All Base Stats +10"],
    "Tatena. Sune. +1":   ["Accuracy +60", "All Base Stats +10", "Triple Attack +3%"],
    # ----- Unity accessories -----
    "Acuity Belt +1":     ["M.Acc +15", "INT +10"],
    "Apeile Ring +1":     ["DEF +20", "Magic Defense Bonus +5"],
    "Arete del Luna +1":  ["Resist Sleep +15%", "Resist Charm +15%"],
    "Aurist's Cape +1":   ["Acc & M.Acc +25", "INT/MND +25"],
    "Bathy Choker +1":    ["Evasion +15", "Counter +10"],
    "Cacoethic Ring +1":  ["DEX +10", "AGI +10"],
    "Canto Necklace +1":  ["M.Acc +15", "CHR +10"],
    "Domin. Earring +1":  ["Accuracy +10", "DEX +6"],
    "Fi Follet Cape +1":  ["Fast Cast +10%", "Spell Interruption Rate -5%"],
    "Gelatinous Ring +1": ["VIT +15", "HP +100"],
    "Ghastly Tathlum +1": ["Magic Damage +10", "INT +5"],
    "Ground. Mantle +1":  ["Accuracy +15", "DEX +10"],
    "Handler's Earring +1": ["Pet: Acc & M.Acc +15", "Accuracy +10"],
    "Kentarch Belt +1":   ["STR +10", "DEX +10"],
    "Loricate Torque +1": ["DEF +45", "Spell Interruption Rate -5%"],
    "Lugra Earring +1":   ["DEF +20", "STR/DEX/VIT/INT +8"],
    "Mephitas's Ring +1": ["Conserve MP +15%", "INT +5"],
    "Metamor. Ring +1":   ["M.Acc +10", "INT/MND/CHR +10"],
    "Nourish. Earring +1": ["Resist Silence +15%", "Spell Interruption Rate -5%"],
    "Odnowa Earring +1":  ["DEF +30", "Damage Taken -3%"],
    "Sailfi Belt +1":     ["STR +15", "Double Attack +5%"],
    "Shinjutsu-no-Obi +1": ["Conserve MP +15%", "Fast Cast +5%"],
    "Seeth. Bomblet +1":  ["STR +10", "Haste +5%"],
    "Unmoving Collar +1": ["DEF +30", "HP +200"],
    "Vim Torque +1":      ["Accuracy +15", "Store TP +10"],
    "Warder's Charm +1":  ["Skillchain Dmg +15%", "Magic Burst Bonus +10%"],
    "Zwazo Earring +1":   ["HP +45", "Shield Block Rate +3%"],
}

# =============================================================================
# Stat-string parsing
# =============================================================================

ALL_BASE = ["STR", "DEX", "VIT", "AGI", "INT", "MND", "CHR"]

# phrase -> list of canonical stat keys (JSON keys understood by
# path_augment_db._convert_to_stats / STAT_NAME_MAP, or intentionally
# special-effect keys for stats the simulator does not model)
PHRASE_MAP = {
    "acc & m.acc": ["accuracy", "magic_accuracy"],
    "rng. acc & m.acc": ["ranged_accuracy", "magic_accuracy"],
    "acc, r.acc, & m.acc": ["accuracy", "ranged_accuracy", "magic_accuracy"],
    "acc & m.acc & pet: acc & m.acc": ["accuracy", "magic_accuracy", "pet_accuracy", "pet_magic_accuracy"],
    "accuracy": ["accuracy"],
    "ranged acc": ["ranged_accuracy"],
    "m.acc": ["magic_accuracy"],
    "attack": ["attack"],
    "ranged attack": ["ranged_attack"],
    "dmg": ["damage"],
    "hp": ["HP"],
    "mp": ["MP"],
    "def": ["defense"],
    "str": ["STR"], "dex": ["DEX"], "vit": ["VIT"], "agi": ["AGI"],
    "int": ["INT"], "mnd": ["MND"], "chr": ["CHR"],
    "all base stats": ALL_BASE,
    "double attack": ["double_attack"],
    "triple attack": ["triple_attack"],
    "quad attack": ["quad_attack"],
    "crit hit rate": ["crit_rate"],
    "haste": ["gear_haste"],
    "store tp": ["store_tp"],
    "tp bonus": ["tp_bonus"],
    "fast cast": ["fast_cast"],
    "regen": ["regen"],
    "evasion": ["evasion"],
    "magic evasion": ["magic_evasion"],
    "enmity": ["enmity"],
    "damage taken": ["damage_taken"],
    "phys. damage taken": ["physical_dt"],
    "phys. damage limit": ["physical_damage_limit"],
    "magic attack bonus": ["magic_attack"],
    "magic defense bonus": ["magic_defense"],
    "magic damage": ["magic_damage"],
    "magic burst bonus": ["magic_burst_bonus"],
    "weapon skill dmg": ["ws_damage"],
    "skillchain dmg": ["skillchain_bonus"],
    "spell interruption rate": ["spell_interruption_rate_down"],
    "cure potency": ["cure_potency"],
    "healing magic skill": ["healing_magic_skill"],
    "enhancing magic skill": ["enhancing_magic_skill"],
    "enfeebling magic skill": ["enfeebling_magic_skill"],
    "dark magic skill": ["dark_magic_skill"],
    "shield skill": ["shield_skill"],
    "parrying skill": ["parrying_skill"],
    "sword enhancement spell dmg": ["sword_enhancement_flat"],
    "pet: acc & m.acc": ["pet_accuracy", "pet_magic_accuracy"],
    "pet: damage taken": ["pet_damage_taken"],
    "avatar: acc & m.acc": ["pet_accuracy", "pet_magic_accuracy"],
    "avatar: all base stats": ["pet_all_attributes"],
    # Stats the simulator does not model -> stored as special effects by the
    # converter (hasattr check fails), but preserved in the data for the UI.
    "snapshot": ["snapshot"],
    "rapid shot": ["rapid_shot"],
    "counter": ["counter"],
    "conserve mp": ["conserve_mp"],
    "cure potency received": ["cure_potency_received"],
    "shield block rate": ["shield_block_rate"],
    "enh. magic received duration": ["enh_magic_received_duration"],
    "occ. resist status ailments": ["resist_status_ailments"],
    "resist bind": ["resist_bind"],
    "resist sleep": ["resist_sleep"],
    "resist charm": ["resist_charm"],
    "resist silence": ["resist_silence"],
    "avatar: tp bonus": ["pet_tp_bonus"],
    "avatar: magic burst bonus": ["pet_magic_burst_bonus"],
    "avatar: perpetuation cost": ["avatar_perpetuation_cost"],
}


def parse_stat_group(text):
    """Parse a stat-description string like 'STR/DEX +25' into {key: value}."""
    m = re.match(r"^(.*?)\s*([+-]\d+)%?$", text.strip())
    if not m:
        raise ValueError(f"Cannot parse stat group: {text!r}")
    phrase, value = m.group(1).strip().rstrip("+").strip(), int(m.group(2))
    key = phrase.lower()
    if key in PHRASE_MAP:
        keys = PHRASE_MAP[key]
    elif "/" in phrase:  # e.g. "STR/DEX/CHR", "INT/MND"
        keys = []
        for part in phrase.split("/"):
            part = part.strip().lower()
            if part not in PHRASE_MAP:
                raise ValueError(f"Unknown stat {part!r} in group {text!r}")
            keys.extend(PHRASE_MAP[part])
    else:
        raise ValueError(f"Unknown stat phrase {phrase!r} in {text!r}")
    return {k: value for k in keys}


# Slot unlock ranks (verified on BG-Wiki per-rank tables)
SLOT_UNLOCK = {0: 1, 1: 6, 2: 11}


def tier_value(max_value, rank, unlock):
    """Interpolated value of a stat at a given rank (max reached at rank 15)."""
    if rank < unlock:
        return 0
    steps = 15 - unlock + 1
    progressed = rank - unlock + 1
    v = max_value * progressed / steps
    return math.ceil(v) if max_value > 0 else -math.ceil(-v)  # ceil toward |max|


def build_item_entry(name, slots, item_id, item_type):
    tiers = {}
    for rank in range(1, 16):
        stats = {}
        for idx, slot_text in enumerate(slots):
            unlock = SLOT_UNLOCK[idx]
            for key, max_val in parse_stat_group(slot_text).items():
                val = tier_value(max_val, rank, unlock)
                if val:
                    stats[key] = stats.get(key, 0) + val
        tiers[str(rank)] = {
            "stats": stats,
            "description": ("R15 (BG-Wiki): " + "  ".join(slots)) if rank == 15
                           else "Interpolated from R15 values",
            "interpolated": rank != 15,
        }
    wiki_name = name.replace(" ", "_").replace("'", "%27").replace("+", "%2B")
    return {
        "name": name,
        "item_type": item_type,
        "category": item_type,
        "max_rank": 15,
        "source_url": f"https://www.bg-wiki.com/ffxi/{wiki_name}",
        "has_full_wiki_table": False,
        "interpolation_applied": True,
        "paths": {"A": {"tiers": tiers, "is_complete": True}},
    }


# =============================================================================
# Item ID resolution from Windower resources (items.lua)
# =============================================================================

WEAPON_CATEGORIES = {"Weapon"}


def load_item_index(items_lua_path):
    """Map lowercase en/enl names -> (id, category) from Windower items.lua."""
    index = {}
    pat = re.compile(r'\[(\d+)\]\s*=\s*\{.*?en="([^"]*)".*?\}')
    cat_pat = re.compile(r'category="([^"]*)"')
    enl_pat = re.compile(r'enl="([^"]*)"')
    with open(items_lua_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pat.search(line)
            if not m:
                continue
            item_id, en = int(m.group(1)), m.group(2)
            cat = (cat_pat.search(line) or [None, ""])[1] if cat_pat.search(line) else ""
            entry = (item_id, cat)
            index.setdefault(en.lower(), entry)
            enl_m = enl_pat.search(line)
            if enl_m:
                index.setdefault(enl_m.group(1).lower(), entry)
    return index


def main():
    items_index = load_item_index(REPO_DIR / "items.lua")

    entries = {}
    unmatched = []
    for name, slots in UNITY_R15.items():
        hit = items_index.get(name.lower())
        if not hit:
            unmatched.append(name)
            continue
        item_id, cat = hit
        item_type = "unity_weapon" if cat in WEAPON_CATEGORIES else "unity_armor"
        entries[str(item_id)] = build_item_entry(name, slots, item_id, item_type)

    if unmatched:
        print("WARNING - could not resolve item IDs for:")
        for n in unmatched:
            print("  ", n)

    targets = [
        REPO_DIR / "augment_data" / "augment_tables.json",
        REPO_DIR / "static" / "data" / "augment_tables.json",
    ]
    for target in targets:
        with open(target, encoding="utf-8") as f:
            data = json.load(f)
        before = len(data["items"])
        # Remove any previous unity entries, then merge fresh
        data["items"] = {k: v for k, v in data["items"].items()
                         if not str(v.get("category", "")).startswith("unity")}
        data["items"].update(entries)
        data["items"] = dict(sorted(data["items"].items(), key=lambda kv: int(kv[0])))
        note = data["metadata"].get("unity_note")
        data["metadata"]["unity_note"] = (
            "Unity (Wanted battle) +1 gear: R15 stats from BG-Wiki Unity Rewards; "
            "R1-14 interpolated (slot1 unlocks R1, slot2 R6, slot3 R11)."
        )
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"{target}: {before} -> {len(data['items'])} items "
              f"(+{len(data['items']) - before})")

    print(f"Unity entries written: {len(entries)} / {len(UNITY_R15)} defined")
    return 0 if not unmatched else 1


if __name__ == "__main__":
    sys.exit(main())
