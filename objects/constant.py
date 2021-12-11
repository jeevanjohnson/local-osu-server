import enum

@enum.unique
class Gamemode(enum.IntEnum):
    STD   = 0
    TAIKO = 1
    CTB = 2
    MANIA = 3

@enum.unique
class Mods(enum.IntFlag):
    NOMOD = 0
    NOFAIL = 1 << 0
    EASY = 1 << 1
    TOUCHSCREEN = 1 << 2
    HIDDEN = 1 << 3
    HARDROCK = 1 << 4
    SUDDENDEATH = 1 << 5
    DOUBLETIME = 1 << 6
    RELAX = 1 << 7
    HALFTIME = 1 << 8
    NIGHTCORE = 1 << 9
    FLASHLIGHT = 1 << 10
    AUTOPLAY = 1 << 11
    SPUNOUT = 1 << 12
    AUTOPILOT = 1 << 13
    PERFECT = 1 << 14
    KEY4 = 1 << 15
    KEY5 = 1 << 16
    KEY6 = 1 << 17
    KEY7 = 1 << 18
    KEY8 = 1 << 19
    FADEIN = 1 << 20
    RANDOM = 1 << 21
    CINEMA = 1 << 22
    TARGET = 1 << 23
    KEY9 = 1 << 24
    KEYCOOP = 1 << 25
    KEY1 = 1 << 26
    KEY3 = 1 << 27
    KEY2 = 1 << 28
    SCOREV2 = 1 << 29
    MIRROR = 1 << 30
    
    def __repr__(self) -> str:
        _mod_dict = {
           Mods.NOFAIL: 'NF',
           Mods.EASY: 'EZ',
           Mods.TOUCHSCREEN: 'TD',
           Mods.HIDDEN: 'HD',
           Mods.HARDROCK: 'HR',
           Mods.SUDDENDEATH: 'SD',
           Mods.DOUBLETIME: 'DT',
           Mods.RELAX: 'RX',
           Mods.HALFTIME: 'HT',
           Mods.NIGHTCORE: 'NC',
           Mods.FLASHLIGHT: 'FL',
           Mods.AUTOPLAY: 'AU',
           Mods.SPUNOUT: 'SO',
           Mods.AUTOPILOT: 'AP',
           Mods.PERFECT: 'PF',
           Mods.KEY4: 'K4',
           Mods.KEY5: 'K5',
           Mods.KEY6: 'K6',
           Mods.KEY7: 'K7',
           Mods.KEY8: 'K8',
           Mods.FADEIN: 'FI',
           Mods.RANDOM: 'RN',
           Mods.CINEMA: 'CN',
           Mods.TARGET: 'TP',
           Mods.KEY9: 'K9',
           Mods.KEYCOOP: 'CO',
           Mods.KEY1: 'K1',
           Mods.KEY3: 'K3',
           Mods.KEY2: 'K2',
           Mods.SCOREV2: 'V2',
           Mods.MIRROR: 'MI'
       }
        if not self:
           return 'NM'
            # dt/nc is a special case, as osu! will send
            # the mods as 'DTNC' while only NC is applied.
        if self & Mods.NIGHTCORE:
            self &= ~Mods.DOUBLETIME
        
        return ''.join(v for k, v in _mod_dict.items() if self & k)