import { Component, OnDestroy, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../../environments/environment';
import { JobStatisticsApiService } from '../../services/job-statistics-api.service';

interface Job {
  job_id: string;
  status: string;
  title?: string;
  original_filename?: string;
  model_name?: string;
  processed_frames?: number;
  total_frames?: number;
}

interface PlayerStat {
  player_id: number;
  team_id: number;
  frame_count: number;
  distance_km: number;
}

@Component({
  selector: 'app-heatmap',
  standalone: false,
  templateUrl: './heatmap.html',
  styleUrl: './heatmap.scss',
})
export class Heatmap implements OnInit, OnDestroy {
  readonly API = environment.aiApiBaseUrl;

  // Job selection
  jobs: Job[] = [];
  selectedJobId: string | null = null;

  // Player / Team selection
  mode: 'player' | 'team' = 'player';
  playerIds: number[] = [];
  playerStats: { [id: string]: PlayerStat } = {};
  selectedPlayerId: number | null = null;
  selectedTeamId: 0 | 1 = 0;

  // Heatmap display
  heatmapUrl: string | null = null;
  loading = false;
  loadingJobs = false;
  error = '';
  private heatmapObjectUrl: string | null = null;

  constructor(
    private http: HttpClient,
    private jobStatistics: JobStatisticsApiService,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.loadJobs();
    this.route.queryParamMap.subscribe((params) => {
      const jobId = params.get('jobId');
      if (jobId) {
        this.onJobSelect(jobId);
      }
    });
  }

  ngOnDestroy(): void {
    this.releaseHeatmapUrl();
  }

  loadJobs(): void {
    this.loadingJobs = true;
    this.jobStatistics.getCompletedJobs('VideoDetection').subscribe({
      next: (jobs) => {
        this.jobs = jobs.map((job) => ({
          job_id: job.id,
          status: job.status,
          title: job.videoTitle,
          original_filename: job.videoTitle,
          model_name: job.modelName ?? undefined,
          processed_frames: job.frameCount ?? undefined,
          total_frames: job.frameCount ?? undefined
        }));
        this.loadingJobs = false;
      },
      error: () => {
        this.http.get<Job[]>(`${this.API}/jobs`).subscribe({
          next: (jobs) => {
            this.jobs = jobs;
            this.loadingJobs = false;
          },
          error: () => {
            this.error = 'Could not load completed tracking jobs.';
            this.loadingJobs = false;
          }
        });
      }
    });
  }

  onJobSelect(jobId: string): void {
    this.selectedJobId = jobId;
    this.releaseHeatmapUrl();
    this.heatmapUrl = null;
    this.playerIds = [];
    this.playerStats = {};
    this.selectedPlayerId = null;
    this.error = '';

    if (!jobId) return;

    // Load player list
    this.http.get<{ player_ids: number[] }>(`${this.API}/job/${jobId}/players`).subscribe({
      next: (res) => {
        this.playerIds = res.player_ids;
        if (this.playerIds.length) {
          this.selectedPlayerId = this.playerIds[0];
        }
      }
    });

    // Load stats
    this.http.get<{ stats: { [id: string]: PlayerStat } }>(`${this.API}/job/${jobId}/stats`).subscribe({
      next: (res) => { this.playerStats = res.stats; }
    });
  }

  jobLabel(job: Job): string {
    const title = (job.title || job.original_filename || `Job ${job.job_id.substring(0, 8)}`).trim();
    return `${title} (${job.job_id.substring(0, 8)})`;
  }

  get selectedJob(): Job | null {
    if (!this.selectedJobId) return null;
    return this.jobs.find((job) => job.job_id === this.selectedJobId) ?? null;
  }

  get selectedJobTitle(): string {
    const job = this.selectedJob;
    return job?.title || job?.original_filename || (this.selectedJobId ? `Job ${this.selectedJobId.substring(0, 8)}` : '');
  }

  generateHeatmap(): void {
    if (!this.selectedJobId) return;
    this.heatmapUrl = null;
    this.loading = true;
    this.error = '';

    let url: string;
    if (this.mode === 'player') {
      if (this.selectedPlayerId === null) {
        this.error = 'Please select a player.';
        this.loading = false;
        return;
      }
      url = `${this.API}/heatmap/player/${this.selectedJobId}/${this.selectedPlayerId}`;
    } else {
      url = `${this.API}/heatmap/team/${this.selectedJobId}/${this.selectedTeamId}`;
    }

    this.http.get(`${url}?t=${Date.now()}`, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        this.releaseHeatmapUrl();
        this.heatmapObjectUrl = URL.createObjectURL(blob);
        this.heatmapUrl = this.heatmapObjectUrl;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.heatmapUrl = null;
        this.error = 'Failed to generate heatmap for the selected target.';
      }
    });
  }

  onHeatmapLoad(): void { this.loading = false; }
  onHeatmapError(): void {
    this.loading = false;
    this.heatmapUrl = null;
    this.error = 'Failed to generate heatmap for the selected target.';
  }

  get statForSelected(): PlayerStat | null {
    if (this.mode !== 'player' || this.selectedPlayerId === null) return null;
    return this.playerStats[String(this.selectedPlayerId)] ?? null;
  }

  get teamLabel(): string {
    return this.selectedTeamId === 0 ? 'Team A (Blue)' : 'Team B (Pink)';
  }

  private releaseHeatmapUrl(): void {
    if (this.heatmapObjectUrl) {
      URL.revokeObjectURL(this.heatmapObjectUrl);
      this.heatmapObjectUrl = null;
    }
  }
}
