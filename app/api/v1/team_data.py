from fastapi import APIRouter, HTTPException
import httpx

from app.config import settings
from app.schemas.team_stats import TeamStats, PlayerStats, Season, Totals, PassingStats, ReceivingStats, RushingStats
from app.constants import name_to_id

router = APIRouter()

headers = {
    "x-api-key": settings.x_api_key
}
base_url = "https://api.sportradar.com/nfl/official/trial/v7/en"

def gather_player_stats(player_data: dict, team: str, total_passing_attempts: int, total_rushing_attempts: int) -> PlayerStats:
    total_fantasy_points = 0
    passing_stats, receiving_stats, rushing_stats = None, None, None
    if "rushing" in player_data:
        rushing_stats = RushingStats(
            name = player_data["name"],
            attempts = player_data["rushing"]["attempts"],
            rushingShare = player_data["rushing"]["attempts"] / total_rushing_attempts,
            yards = player_data["rushing"]["yards"],
            ypc = player_data["rushing"]["avg_yards"],
            rushingTouchdowns = player_data["rushing"]["touchdowns"]
        )
        total_fantasy_points += rushing_stats.yards * 0.1 + rushing_stats.rushingTouchdowns * 6
        
    if "receiving" in player_data:
        receiving_stats = ReceivingStats(
            name = player_data["name"],
            targetShare = player_data["receiving"]["targets"] / total_passing_attempts,
            receptions = player_data["receiving"]["receptions"],
            yards = player_data["receiving"]["yards"],
            receivingTouchdowns = player_data["receiving"]["touchdowns"]
        )
        total_fantasy_points += receiving_stats.yards * 0.1 + receiving_stats.receivingTouchdowns * 6 + receiving_stats.receptions * 1.0
        
    if "passing" in player_data:
        passing_stats = PassingStats(
            name = player_data["name"],
            completions = player_data["passing"]["completions"],
            attempts = player_data["passing"]["attempts"],
            completionPercentage = player_data["passing"]["completions"] / player_data["passing"]["attempts"] if player_data["passing"]["attempts"] > 0 else 0,
            yards = player_data["passing"]["yards"],
            passingTouchdowns = player_data["passing"]["touchdowns"]
        )
        total_fantasy_points += passing_stats.yards * 0.04 + passing_stats.passingTouchdowns * 4
        
    return PlayerStats(
        name = player_data["name"],
        position = player_data["position"],
        team = team,
        passingStats = passing_stats,
        receivingStats = receiving_stats,  
        rushingStats = rushing_stats,
        totalFantasyPoints = total_fantasy_points,
        fantasyPointsPerGame = total_fantasy_points / player_data["games_played"]
    ) 

def create_team_stats(team_data: dict) -> TeamStats:
    passingAttempts = team_data["record"]["passing"]["attempts"]
    rushingAttempts = team_data["record"]["rushing"]["attempts"]
    total_points = team_data["record"]["touchdowns"]["total"] * 7 + team_data["record"]["field_goals"]["made"] * 3
    
    totals = Totals(
        points = total_points,
        pointsPerGame = total_points / team_data["record"]["games_played"],
        touchdowns = team_data["record"]["touchdowns"]["total"],
        passingTouchdowns = team_data["record"]["touchdowns"]["pass"],
        rushingTouchdowns = team_data["record"]["touchdowns"]["rush"],
        yards = team_data["record"]["rushing"]["yards"] + team_data["record"]["passing"]["net_yards"],
        passingAttempts = passingAttempts,
        passingCompletions = team_data["record"]["passing"]["completions"],
        passingYards = team_data["record"]["passing"]["net_yards"],
        rushingAttempts = rushingAttempts,
        rushingYards = team_data["record"]["rushing"]["yards"]
    )
    
    player_stats_list = []
    for player_data in team_data["players"]:
        position = player_data["position"]
        if (position == "QB" or position == "RB" or position == "WR" or position == "TE") and player_data["games_played"] > 0:
            player_stats_list.append(gather_player_stats(player_data, team_data["name"], passingAttempts, rushingAttempts))
            
    sorted_players = sorted(
        player_stats_list, 
        key=lambda player: player.fantasyPointsPerGame, 
        reverse=True
    )
    
    qb_limit, rb_limit, wr_limit, te_limit = 1, 1, 2, 1
    quarterback, runnningBack, receivers, tightEnd = None, None, [], None
    for player in sorted_players:
        if player.position == "QB" and qb_limit > 0:
            quarterback = player
            qb_limit -= 1
        elif player.position == "RB" and rb_limit > 0:
            runnningBack = player
            rb_limit -= 1
        elif player.position == "WR" and wr_limit > 0:
            receivers.append(player)
            wr_limit -= 1
        elif player.position == "TE" and te_limit > 0:
            tightEnd = player
            te_limit -= 1
    
    return TeamStats(
        id=team_data["id"],
        isPrediction = False,
        name=team_data["name"],
        season=Season(
            year=team_data["season"]["year"],
            type=team_data["season"]["type"]
        ),
        totals=totals,
        quarterback = quarterback,
        receivers = receivers,
        runningBack = runnningBack,
        tightEnd = tightEnd
    )
    
async def fetch_all_teams():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{base_url}/league/teams.json", headers=headers)
        r.raise_for_status()
    
    all_teams = []
    for team in r.json()["teams"]:
        if team["name"] == "TBD":
            continue
        all_teams.append(team["name"])
    
    return all_teams

async def fetch_team_stats(team: str, season: int):
    async with httpx.AsyncClient() as client: 
        team_id = name_to_id[team.lower()]
        if not team_id:
            raise ValueError("Unknown team")
        
        r = await client.get(f"{base_url}/seasons/{season}/REG/teams/{team_id}/statistics.json", headers=headers)
        r.raise_for_status()
    
    return create_team_stats(r.json())

@router.get("/{team}/{season}", response_model=TeamStats)
async def get_team_stats(team: str, season: int):
    try:
        return await fetch_team_stats(team, season)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Upstream API error")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/all-teams", response_model=list[str])
async def get_all_teams():
    try:
        return await fetch_all_teams()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Upstream API error")