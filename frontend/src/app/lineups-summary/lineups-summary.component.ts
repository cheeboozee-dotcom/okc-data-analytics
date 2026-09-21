import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LineupsService } from '../_services/lineups.service';

interface LineupPlayer {
  player_id: string;
  name: string;
}

interface Lineup {
  team_id: string | null;
  player_ids: string[];
  players: LineupPlayer[];

  offensive_possessions: number;
  defensive_possessions: number;
  total_possessions: number;

  offensive_points: number;
  defensive_points: number;
  net_points: number;

  offensive_fg_pct: number;
  defensive_fg_pct: number;
  offensive_fg2_pct: number;
  defensive_fg2_pct: number;
  offensive_fg3_pct: number;
  defensive_fg3_pct: number;

  offensive_efg_pct: number;
  defensive_efg_pct: number;

  offensive_turnover_rate: number;
  defensive_turnover_rate: number;

  offensive_rebound_rate: number;
  defensive_rebound_rate: number;

  offensive_points_per_possession: number;
  defensive_points_per_possession: number;
  net_points_per_possession: number;
}

@Component({
  imports: [CommonModule, FormsModule],
  selector: 'lineups-summary-component',
  templateUrl: './lineups-summary.component.html',
  styleUrl: './lineups-summary.component.scss',
})
export class LineupsSummaryComponent implements OnInit {
  private readonly lineupsService = inject(LineupsService);
  private readonly cdr = inject(ChangeDetectorRef);

  lineups: Lineup[] = [];
  filteredLineups: Lineup[] = [];

  lineupSize = 5;
  searchTerm = '';
  sortField: 'net_ppp' | 'off_ppp' | 'def_ppp' | 'possessions' = 'net_ppp';
  sortDescending = true;

  loading = true;
  error = '';

  ngOnInit(): void {
    this.loadLineups();
  }

  loadLineups(): void {
    this.loading = true;
    this.error = '';

    this.lineupsService.getLineupsLeagueSummary(this.lineupSize).subscribe({
      next: (data) => {
        this.lineups = (data.apiResponse as Lineup[]) ?? [];
        this.applyFilters();
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Unable to load lineup data:', error);
        this.error = 'Unable to load lineup data. Make sure the Django backend is running.';
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  changeLineupSize(size: number): void {
    if (this.lineupSize === size) {
      return;
    }

    this.lineupSize = size;
    this.searchTerm = '';
    this.loadLineups();
  }

  onSearchChange(): void {
    this.applyFilters();
  }

  changeSort(field: 'net_ppp' | 'off_ppp' | 'def_ppp' | 'possessions'): void {
    if (this.sortField === field) {
      this.sortDescending = !this.sortDescending;
    } else {
      this.sortField = field;
      this.sortDescending = true;
    }

    this.applyFilters();
  }

  private applyFilters(): void {
    const search = this.searchTerm.trim().toLowerCase();

    this.filteredLineups = this.lineups
      .filter((lineup) => {
        if (!search) {
          return true;
        }

        return lineup.players.some((player) =>
          player.name.toLowerCase().includes(search),
        );
      })
      .sort((a, b) => {
        const valueA = this.getSortValue(a);
        const valueB = this.getSortValue(b);

        return this.sortDescending ? valueB - valueA : valueA - valueB;
      });
  }

  private getSortValue(lineup: Lineup): number {
    switch (this.sortField) {
      case 'off_ppp':
        return lineup.offensive_points_per_possession;
      case 'def_ppp':
        return lineup.defensive_points_per_possession;
      case 'possessions':
        return lineup.total_possessions;
      case 'net_ppp':
      default:
        return lineup.net_points_per_possession;
    }
  }

  formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }

  formatNumber(value: number): string {
    return value.toFixed(2);
  }

  getRank(lineup: Lineup): number {
    return this.filteredLineups.indexOf(lineup) + 1;
  }

  trackByLineup(_index: number, lineup: Lineup): string {
    return lineup.player_ids.join('-');
  }
}

