import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { JobStatisticsApiService } from '../../services/job-statistics-api.service';
import { ProcessingJobApiResponse } from '../../models/api.model';

export interface MatchStat {
  label: string;
  homeValue: number;
  awayValue: number;
  icon: string;
}

export interface BallActionStats {
  team_1: { throw_in: number; out: number; high_pass: number; header: number };
  team_2: { throw_in: number; out: number; high_pass: number; header: number };
}

@Component({
  selector: 'app-analytics',
  standalone: false,
  templateUrl: './analytics.html',
  styleUrl: './analytics.scss',
})
export class Analytics implements OnInit {
  hasData = false;
  stats: MatchStat[] = [];
  historyJobs: ProcessingJobApiResponse[] = [];
  selectedHistoryJobId = '';
  selectedHistoryTitle = '';
  loadingHistory = false;

  constructor(
    private jobStatistics: JobStatisticsApiService,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.loadHistoryJobs();
    this.route.queryParamMap.subscribe((params) => {
      const jobId = params.get('jobId') ?? '';
      if (jobId) {
        this.selectedHistoryJobId = jobId;
        this.loadStats(jobId);
      } else {
        this.loadStats();
      }
    });
  }

  loadStats(processingJobId?: string): void {
    this.clearLegacyStatsCache();

    if (processingJobId) {
      this.loadStatsFromHistory(processingJobId);
      return;
    }

    this.selectedHistoryJobId = '';
    this.selectedHistoryTitle = '';

    this.jobStatistics.getCompletedJobs('BallActionAnalysis', 1).subscribe({
      next: (jobs) => {
        const latestJob = jobs[0];
        if (!latestJob) {
          this.clearLoadedStats();
          return;
        }

        this.selectedHistoryTitle = this.jobLabel(latestJob);
        this.jobStatistics.getLatestByJobAndType<BallActionStats>(latestJob.id, 'ball_action_stats').subscribe({
          next: (data) => {
            if (!data || !this.hasAnyCount(data)) {
              this.clearLoadedStats();
              return;
            }

            this.applyStats(data);
          },
          error: () => {
            this.clearLoadedStats();
          }
        });
      },
      error: () => {
        this.clearLoadedStats();
      }
    });
  }

  loadHistoryJobs(): void {
    this.loadingHistory = true;
    this.jobStatistics.getCompletedJobs('BallActionAnalysis').subscribe({
      next: (jobs) => {
        this.historyJobs = jobs;
        this.loadingHistory = false;
        if (this.selectedHistoryJobId) {
          this.selectedHistoryTitle = this.jobLabel(
            jobs.find((job) => job.id === this.selectedHistoryJobId) ?? null
          );
        }
      },
      error: () => {
        this.loadingHistory = false;
      }
    });
  }

  onHistorySelect(jobId: string): void {
    this.selectedHistoryJobId = jobId;
    if (!jobId) {
      this.selectedHistoryTitle = '';
      this.loadStats();
      return;
    }

    this.loadStatsFromHistory(jobId);
  }

  jobLabel(job: ProcessingJobApiResponse | null): string {
    if (!job) return 'Selected analysis';
    const title = job.videoTitle || `Analysis ${job.id.substring(0, 8)}`;
    const date = job.completedAt || job.createdAt;
    return `${title} - ${new Date(date).toLocaleString()}`;
  }

  private loadStatsFromHistory(processingJobId: string): void {
    this.jobStatistics.getLatestByJobAndType<BallActionStats>(processingJobId, 'ball_action_stats').subscribe({
      next: (data) => {
        this.selectedHistoryTitle = this.jobLabel(
          this.historyJobs.find((job) => job.id === processingJobId) ?? null
        );

        if (!data || !this.hasAnyCount(data)) {
          this.clearLoadedStats();
          return;
        }

        this.applyStats(data);
      },
      error: () => {
        this.clearLoadedStats();
      }
    });
  }

  private applyStats(data: BallActionStats): void {
    if (!this.hasAnyCount(data)) {
      this.clearLoadedStats();
      return;
    }

    this.stats = [
      { label: 'Throw In', homeValue: data.team_1.throw_in, awayValue: data.team_2.throw_in, icon: 'TI' },
      { label: 'Out', homeValue: data.team_1.out, awayValue: data.team_2.out, icon: 'OUT' },
      { label: 'High Pass', homeValue: data.team_1.high_pass, awayValue: data.team_2.high_pass, icon: 'HP' },
      { label: 'Header', homeValue: data.team_1.header, awayValue: data.team_2.header, icon: 'HD' },
    ];
    this.hasData = true;
  }

  private hasAnyCount(data: BallActionStats): boolean {
    return [
      data.team_1?.throw_in,
      data.team_1?.out,
      data.team_1?.high_pass,
      data.team_1?.header,
      data.team_2?.throw_in,
      data.team_2?.out,
      data.team_2?.high_pass,
      data.team_2?.header,
    ].some((value) => Number(value ?? 0) > 0);
  }

  private clearLoadedStats(): void {
    this.hasData = false;
    this.stats = [];
  }

  private clearLegacyStatsCache(): void {
    localStorage.removeItem('latest_ball_action_stats');
    localStorage.removeItem('latest_ball_action_stats_source');
  }

  getHomePercent(stat: MatchStat): number {
    const total = stat.homeValue + stat.awayValue;
    return total === 0 ? 50 : Math.round((stat.homeValue / total) * 100);
  }

  getAwayPercent(stat: MatchStat): number {
    const total = stat.homeValue + stat.awayValue;
    return total === 0 ? 50 : Math.round((stat.awayValue / total) * 100);
  }

  getDominantTeam(stat: MatchStat): 'home' | 'away' | 'equal' {
    if (stat.homeValue > stat.awayValue) return 'home';
    if (stat.awayValue > stat.homeValue) return 'away';
    return 'equal';
  }

  getTotalHome(): number {
    return this.stats.reduce((sum, stat) => sum + stat.homeValue, 0);
  }

  getTotalAway(): number {
    return this.stats.reduce((sum, stat) => sum + stat.awayValue, 0);
  }

  clearStats(): void {
    this.selectedHistoryJobId = '';
    this.selectedHistoryTitle = '';
    this.clearLoadedStats();
  }
}
