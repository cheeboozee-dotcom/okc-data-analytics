from __future__ import annotations

"""Helpers for the lineup summary API."""

from collections import defaultdict
from itertools import combinations
from typing import Any

from app.dbmodels.models import Player, Possession


LineupRecord = dict[str, Any]

POSSESSION_COUNTING_FIELDS = (
    'period',
    'seconds',
    'fg2_made',
    'fg2_attempted',
    'fg3_made',
    'fg3_attempted',
    'fg_made',
    'fg_attempted',
    'ft_made',
    'ft_attempted',
    'rebounds_offense',
    'rebounds_defense',
    'rebound_opportunities',
    'assists',
    'steals',
    'turnovers',
    'blocks',
    'offensive_fouls',
    'defensive_fouls',
    'shooting_fouls',
    'points',
    'shot_attempts',
    'shot_attempt_points',
    'ft_potential_points',
    'transition_take_fouls',
)


def _normalize_lineup_size(lineup_size: Any) -> int:
    try:
        normalized_lineup_size = int(lineup_size)
    except (TypeError, ValueError):
        return 5

    return max(1, min(5, normalized_lineup_size))


def _empty_stats() -> dict[str, int | float]:
    return {
        'possessions': 0,
        **{field: 0 for field in POSSESSION_COUNTING_FIELDS},
    }


def _add_possession_stats(
    target: dict[str, int | float],
    possession: Possession,
) -> None:
    target['possessions'] += 1

    for field in POSSESSION_COUNTING_FIELDS:
        target[field] += getattr(possession, field)


def _percentage(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0

    return numerator / denominator


def _build_side_stats(
    stats: dict[str, int | float],
    prefix: str,
) -> dict[str, int | float]:
    possessions = stats['possessions']

    result = {
        f'{prefix}_possessions': possessions,
    }

    for field in POSSESSION_COUNTING_FIELDS:
        if field == 'period' or field == 'seconds':
            continue
        result[f'{prefix}_{field}'] = stats[field]

    fg_attempted = stats['fg_attempted']
    fg2_attempted = stats['fg2_attempted']
    fg3_attempted = stats['fg3_attempted']

    result[f'{prefix}_fg_pct'] = _percentage(
        stats['fg_made'],
        fg_attempted,
    )
    result[f'{prefix}_fg2_pct'] = _percentage(
        stats['fg2_made'],
        fg2_attempted,
    )
    result[f'{prefix}_fg3_pct'] = _percentage(
        stats['fg3_made'],
        fg3_attempted,
    )

    # Points scored/allowed per possession.
    result[f'{prefix}_points_per_possession'] = _percentage(
        stats['points'],
        possessions,
    )

    return result


def _build_additional_metrics(
    offensive: dict[str, int | float],
    defensive: dict[str, int | float],
) -> dict[str, float]:
    offensive_possessions = offensive['possessions']
    defensive_possessions = defensive['possessions']

    offensive_rebound_opportunities = offensive['rebound_opportunities']
    defensive_rebound_opportunities = defensive['rebound_opportunities']

    offensive_efg = _percentage(
        offensive['fg_made'] + 0.5 * offensive['fg3_made'],
        offensive['fg_attempted'],
    )

    defensive_efg = _percentage(
        defensive['fg_made'] + 0.5 * defensive['fg3_made'],
        defensive['fg_attempted'],
    )

    offensive_turnover_rate = _percentage(
        offensive['turnovers'],
        offensive_possessions,
    )

    defensive_turnover_rate = _percentage(
        defensive['turnovers'],
        defensive_possessions,
    )

    offensive_rebound_rate = _percentage(
        offensive['rebounds_offense'],
        offensive_rebound_opportunities,
    )

    defensive_rebound_rate = _percentage(
        defensive['rebounds_defense'],
        defensive_rebound_opportunities,
    )

    offensive_points_per_possession = _percentage(
        offensive['points'],
        offensive_possessions,
    )

    defensive_points_per_possession = _percentage(
        defensive['points'],
        defensive_possessions,
    )

    return {
        'offensive_efg_pct': offensive_efg,
        'defensive_efg_pct': defensive_efg,
        'offensive_turnover_rate': offensive_turnover_rate,
        'defensive_turnover_rate': defensive_turnover_rate,
        'offensive_rebound_rate': offensive_rebound_rate,
        'defensive_rebound_rate': defensive_rebound_rate,
        'offensive_points_per_possession': offensive_points_per_possession,
        'defensive_points_per_possession': defensive_points_per_possession,
        'net_points_per_possession': (
            offensive_points_per_possession
            - defensive_points_per_possession
        ),
        'net_points': offensive['points'] - defensive['points'],
    }


def get_lineup_league_summary_stats(lineup_size: int = 5) -> list[LineupRecord]:
    """Return lineup summaries across the entire league."""

    lineup_size = _normalize_lineup_size(lineup_size)

    offensive_lineups: dict[tuple[str, ...], dict[str, Any]] = defaultdict(
        lambda: {
            'team_id': None,
            'stats': _empty_stats(),
        }
    )

    defensive_lineups: dict[tuple[str, ...], dict[str, Any]] = defaultdict(
        lambda: {
            'team_id': None,
            'stats': _empty_stats(),
        }
    )

    possessions = Possession.objects.all().iterator()

    for possession in possessions:
        offensive_players = tuple(
            sorted(str(player_id) for player_id in possession.offensive_player_ids)
        )
        defensive_players = tuple(
            sorted(str(player_id) for player_id in possession.defensive_player_ids)
        )

        if len(offensive_players) >= lineup_size:
            for lineup in combinations(offensive_players, lineup_size):
                record = offensive_lineups[lineup]

                if record['team_id'] is None:
                    record['team_id'] = str(possession.offensive_team_id)

                _add_possession_stats(record['stats'], possession)

        if len(defensive_players) >= lineup_size:
            for lineup in combinations(defensive_players, lineup_size):
                record = defensive_lineups[lineup]

                if record['team_id'] is None:
                    record['team_id'] = str(possession.defensive_team_id)

                _add_possession_stats(record['stats'], possession)

    all_lineups = set(offensive_lineups) | set(defensive_lineups)

    player_ids = {
        player_id
        for lineup in all_lineups
        for player_id in lineup
    }

    players = Player.objects.filter(id__in=player_ids)

    player_lookup = {
        str(player.id): player
        for player in players
    }

    results: list[LineupRecord] = []

    for lineup in sorted(all_lineups):
        offensive = offensive_lineups[lineup]['stats']
        defensive = defensive_lineups[lineup]['stats']

        team_id = (
            offensive_lineups[lineup]['team_id']
            or defensive_lineups[lineup]['team_id']
        )

        result: LineupRecord = {
            **_build_side_stats(offensive, 'offensive'),
            **_build_side_stats(defensive, 'defensive'),
            'total_possessions': (
                offensive['possessions'] + defensive['possessions']
            ),
            'team_id': team_id,
            'player_ids': list(lineup),
            'players': [
                {
                    'player_id': player_id,
                    'name': player_lookup[player_id].name,
                }
                for player_id in lineup
                if player_id in player_lookup
            ],
            **_build_additional_metrics(offensive, defensive),
        }

        results.append(result)

    return results