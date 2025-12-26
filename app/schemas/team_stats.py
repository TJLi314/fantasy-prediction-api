from pydantic import BaseModel
from typing import List, Optional


class Season(BaseModel):
    year: int
    type: str


class Totals(BaseModel):
    points: int
    pointsPerGame: float
    touchdowns: int
    passingTouchdowns: int
    rushingTouchdowns: int
    yards: int
    passingAttempts: int
    passingCompletions: int
    passingYards: int
    rushingAttempts: int
    rushingYards: int


class PassingStats(BaseModel):
    name: str
    completions: int
    yards: int
    passingTouchdowns: int


class ReceivingStats(BaseModel):
    name: str
    targetShare: float
    receptions: int
    yards: int
    receivingTouchdowns: int


class RushingStats(BaseModel):
    name: str
    attempts: int
    rushingShare: float
    yards: int
    ypc: float
    rushingTouchdowns: int


class PlayerStats(BaseModel):
    name: str
    position: str
    team: str
    passingStats: Optional[PassingStats]
    receivingStats: Optional[ReceivingStats]
    rushingStats: Optional[RushingStats]
    totalFantasyPoints: float
    fantasyPointsPerGame: float


class TeamStats(BaseModel):
    id: str
    isPrediction: bool
    name: str
    season: Season
    totals: Totals
    quarterback: PlayerStats
    receivers: List[PlayerStats]
    runningBack: PlayerStats
    tightEnd: PlayerStats
    
