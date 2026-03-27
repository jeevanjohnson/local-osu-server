from base64 import b64decode
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum, unique
from typing import TYPE_CHECKING

import ossapi.enums
import ossapi.models
from fastapi.datastructures import FormData
from py3rijndael import Pkcs7Padding, RijndaelCbc
from starlette.datastructures import UploadFile as StarletteUploadFile
from pydantic import BaseModel, ConfigDict

# from adapters import log
from models.bancho.scores import LazerScore, Score, StableScore
from models.database.scores import (
    CurrentScore as ProfileScore,
)
from models.domain.gameplay import Mods, osuGameMode, osuMods
from models.domain.scores import AcceptedScores, AllScores, ScoringAlgorithm

if TYPE_CHECKING:
    from models.database.beatmaps import CurrentBeatmap as Beatmap














