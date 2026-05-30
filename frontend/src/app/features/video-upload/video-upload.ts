import { Component, OnDestroy, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { Subscription, forkJoin, interval, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { ProcessingJobApiResponse } from '../../models/api.model';
import { JobStatisticsApiService } from '../../services/job-statistics-api.service';

interface JobResponse {
  job_id: string;
  status: string;
  progress?: number;
  stage?: string;
  error?: string;
}

interface CsvFileLink {
  path: string;
  url: string;
}

interface TeamPassStats {
  team_id: number;
  team_key: string;
  total_passes: number;
  successful_passes: number;
  unsuccessful_passes: number;
  completion_rate: number | null;
  completion_pct: number | null;
  crosses: number;
  interceptions: number;
  avg_distance_m: number | null;
  total_distance_m: number | null;
}

interface TeamPositioningStats {
  team_id: number;
  team_key: string;
  avg_x: number | null;
  avg_y: number | null;
  avg_width_m: number | null;
  avg_depth_m: number | null;
  avg_compactness_m: number | null;
  avg_players_visible: number | null;
  samples: number;
}

interface PlayerPositioningStats {
  tracker_id: string;
  team_id: number;
  team_key: string;
  avg_x: number | null;
  avg_y: number | null;
  min_x: number | null;
  max_x: number | null;
  min_y: number | null;
  max_y: number | null;
  samples: number;
  is_goalkeeper: boolean;
}

interface CsvDerivedStats {
  pass_totals?: Record<string, TeamPassStats>;
  positioning?: {
    teams?: Record<string, TeamPositioningStats>;
    players?: PlayerPositioningStats[];
  };
}

interface BallActionPrediction {
  label?: string;
  team?: string;
}

interface BallActionPredictionsPayload {
  predictions?: BallActionPrediction[];
}

interface StatusResponse {
  status: string;
  video_url?: string;
  error?: string;
  progress?: number;
  stage?: string;
  processed_frames?: number;
  total_frames?: number;
  has_preview?: boolean;
  ball_action_stats?: {
    team_1: { throw_in: number; out: number; high_pass: number; header: number };
    team_2: { throw_in: number; out: number; high_pass: number; header: number };
  };
  csv_files?: Record<string, CsvFileLink>;
  csv_derived_stats?: CsvDerivedStats;
}

@Component({
  selector: 'app-video-upload',
  standalone: false,
  templateUrl: './video-upload.html',
  styleUrl: './video-upload.scss',
})
export class VideoUpload implements OnInit, OnDestroy {
  readonly API = environment.aiApiBaseUrl;

  selectedFile: File | null = null;
  projectName = '';
  previewUrl: string | null = null;
  annotatedVideoUrl: string | null = null;

  loading = false;
  processingMsg = '';
  error = '';
  apiStatus: 'unknown' | 'ok' | 'down' = 'unknown';
  progress = 0;
  currentStage = 'queued';
  processedFrames = 0;
  totalFrames = 0;
  csvFiles: Record<string, CsvFileLink> = {};
  passStatsRows: TeamPassStats[] = [];
  teamPositionRows: TeamPositioningStats[] = [];
  playerPositionRows: PlayerPositioningStats[] = [];
  historyJobs: ProcessingJobApiResponse[] = [];
  selectedHistoryJobId = '';
  selectedHistoryTitle = '';
  loadingHistory = false;

  private pollSubscription?: Subscription;
  private annotatedVideoObjectUrl: string | null = null;
  private activeProjectTitle = '';

  constructor(
    private http: HttpClient,
    private jobStatistics: JobStatisticsApiService,
    private route: ActivatedRoute
  ) {
    this.checkHealth();
  }

  ngOnInit() {
    this.loadHistoryJobs();
    const initialHistoryJobId = this.route.snapshot.queryParamMap.get('jobId') ?? '';
    this.route.queryParamMap.subscribe((params) => {
      const jobId = params.get('jobId') ?? '';
      if (jobId) {
        this.selectedHistoryJobId = jobId;
        this.loadHistoricalTrackingStats(jobId);
      }
    });

    if (initialHistoryJobId) {
      return;
    }

    const activeJobId = localStorage.getItem('active_detection_job');
    const completedPath = localStorage.getItem('last_completed_job_path');

    if (activeJobId) {
      // Verify the job still exists on the server (server may have restarted)
      this.http.get<{ exists: boolean }>(`${this.API}/job_exists/${activeJobId}`).subscribe({
        next: (res) => {
          if (res.exists) {
            this.loading = true;
            this.progress = 5;
            this.currentStage = 'queued';
            this.processingMsg = 'Resuming previous job...';
            this.startPolling(activeJobId);
          } else {
            // Server restarted — job is gone, clear stale state
            localStorage.removeItem('active_detection_job');
            localStorage.removeItem('last_completed_job_url');
            localStorage.removeItem('last_completed_job_path');
          }
        },
        error: () => {
          // API unreachable — just clear the stale job silently
          localStorage.removeItem('active_detection_job');
        }
      });
    } else if (completedPath) {
      this.loadAnnotatedVideo(completedPath);
      this.progress = 100;
      this.currentStage = 'done';
      this.restoreDerivedStats();
    }
  }

  ngOnDestroy() {
    this.stopPolling();
    this.releasePreviewUrl();
    this.releaseAnnotatedVideoUrl();
  }

  checkHealth() {
    this.http.get<{ status: string }>(`${this.API}/health`).subscribe({
      next: () => (this.apiStatus = 'ok'),
      error: () => (this.apiStatus = 'down'),
    });
  }

  triggerFileInput(fileInput: HTMLInputElement) {
    fileInput.click();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;
    this.handleFile(input.files[0]);
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    const file = event.dataTransfer?.files[0];
    if (!file) return;
    this.handleFile(file);
  }

  detect() {
    if (!this.selectedFile) return;
    const title = this.projectName.trim() || this.defaultProjectName(this.selectedFile.name);
    this.activeProjectTitle = title;

    this.loading = true;
    this.error = '';
    this.annotatedVideoUrl = null;
    this.clearDerivedStats();
    this.progress = 2;
    this.currentStage = 'uploading';
    this.processingMsg = 'Uploading video...';
    this.processedFrames = 0;
    this.totalFrames = 0;
    localStorage.removeItem('last_completed_job_url');
    localStorage.removeItem('last_completed_job_path');
    localStorage.removeItem('last_detection_derived_stats');

    const form = new FormData();
    form.append('video', this.selectedFile);
    form.append('title', title);
    form.append('project_name', title);

    this.http.post<JobResponse>(`${this.API}/detect_video`, form).subscribe({
      next: (res) => {
        if (res.error) {
          this.loading = false;
          this.error = res.error;
          return;
        }

        this.progress = res.progress ?? 5;
        this.currentStage = res.stage ?? 'queued';
        this.processingMsg = this.buildStatusMessage();
        localStorage.setItem('active_detection_job', res.job_id);
        this.startPolling(res.job_id);
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.error || err.message || 'Failed to reach the detection API.';
      },
    });
  }

  reset() {
    this.selectedFile = null;
    this.projectName = '';
    this.releasePreviewUrl();
    this.releaseAnnotatedVideoUrl();
    this.previewUrl = null;
    this.annotatedVideoUrl = null;
    this.clearDerivedStats();
    this.error = '';
    this.loading = false;
    this.processingMsg = '';
    this.progress = 0;
    this.currentStage = 'queued';
    this.processedFrames = 0;
    this.totalFrames = 0;
    this.stopPolling();
    localStorage.removeItem('active_detection_job');
    localStorage.removeItem('last_completed_job_url');
    localStorage.removeItem('last_completed_job_path');
    localStorage.removeItem('last_completed_job_id');
    localStorage.removeItem('last_completed_job_title');
    localStorage.removeItem('last_detection_derived_stats');
  }

  runAnotherVideo() {
    this.reset();
  }

  loadHistoryJobs(): void {
    this.loadingHistory = true;
    this.jobStatistics.getCompletedJobs('VideoDetection').subscribe({
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
      this.reset();
      return;
    }

    this.loadHistoricalTrackingStats(jobId);
  }

  jobLabel(job: ProcessingJobApiResponse | null): string {
    if (!job) return 'Selected process';
    const title = job.videoTitle || `Process ${job.id.substring(0, 8)}`;
    const date = job.completedAt || job.createdAt;
    return `${title} - ${new Date(date).toLocaleString()}`;
  }

  private handleFile(file: File) {
    this.reset();

    if (!file.type.startsWith('video/')) {
      this.error = `File type '${file.type || 'unknown'}' is not supported. Please upload a video (.mp4, .mov, etc).`;
      return;
    }

    this.selectedFile = file;
    this.projectName = this.projectName.trim() || this.defaultProjectName(file.name);
    this.previewUrl = URL.createObjectURL(file);
  }

  private defaultProjectName(fileName: string): string {
    return fileName.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
  }

  private startPolling(jobId: string) {
    this.stopPolling();
    this.processingMsg = this.buildStatusMessage();

    this.pollSubscription = interval(1500)
      .pipe(switchMap(() => this.http.get<StatusResponse>(`${this.API}/job_status/${jobId}`)))
      .subscribe({
        next: (res) => {
          if (this.isCompletedStatus(res)) {
            this.stopPolling();
            this.loading = false;
            this.progress = 100;
            this.currentStage = 'done';
            this.processingMsg = 'Processing complete.';
            localStorage.removeItem('active_detection_job');
            localStorage.setItem('last_completed_job_id', jobId);
            localStorage.setItem('last_completed_job_title', this.activeProjectTitle || jobId);
            this.applyDerivedStats(res.csv_derived_stats, res.csv_files);
            if (res.video_url) {
              this.loadAnnotatedVideo(res.video_url);
            }
            return;
          }

          if (res.status === 'error') {
    this.stopPolling();
    this.activeProjectTitle = '';
            this.loading = false;
            this.currentStage = 'error';
            this.processingMsg = '';
            this.error = res.error || 'The backend encountered an error processing the video.';
            localStorage.removeItem('active_detection_job');
            return;
          }

          if (res.status === 'not_found') {
            this.stopPolling();
            this.loading = false;
            this.currentStage = 'not_found';
            this.processingMsg = '';
            this.error = 'The processing job was not found on the backend.';
            localStorage.removeItem('active_detection_job');
            return;
          }

          this.applyStatus(res);
        },
        error: () => {
          this.stopPolling();
          this.loading = false;
          this.processingMsg = '';
          this.error = 'Lost connection while polling for job status.';
        },
      });
  }

  private applyStatus(res: StatusResponse) {
    this.currentStage = res.stage ?? res.status;
    this.progress = Math.max(0, Math.min(100, Math.round(res.progress ?? this.progress)));
    this.processedFrames = res.processed_frames ?? this.processedFrames;
    this.totalFrames = res.total_frames ?? this.totalFrames;
    this.processingMsg = this.buildStatusMessage();
  }

  private isCompletedStatus(res: StatusResponse): boolean {
    return res.status === 'done'
      || res.stage === 'done'
      || (res.progress ?? 0) >= 100;
  }

  get hasDerivedStats(): boolean {
    return this.passStatsRows.length > 0 || this.teamPositionRows.length > 0 || this.playerPositionRows.length > 0;
  }

  get hasCompletedResult(): boolean {
    return this.currentStage === 'done' && (!!this.annotatedVideoUrl || this.hasDerivedStats);
  }

  get showMissingPassTotals(): boolean {
    return this.hasDerivedStats && this.passStatsRows.length === 0;
  }

  teamLabel(teamId: number | null | undefined): string {
    if (teamId === null || teamId === undefined || Number.isNaN(Number(teamId))) {
      return 'Unknown team';
    }

    return `Team ${Number(teamId) + 1}`;
  }

  formatCount(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return '-';
    }

    return Math.round(Number(value)).toLocaleString();
  }

  formatMeters(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return '-';
    }

    return `${Number(value).toFixed(1)} m`;
  }

  formatPercent(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return '-';
    }

    return `${Number(value).toFixed(1)}%`;
  }

  private hasAnyDerivedStats(stats: CsvDerivedStats): boolean {
    return Object.keys(stats.pass_totals ?? {}).length > 0
      || Object.keys(stats.positioning?.teams ?? {}).length > 0
      || (stats.positioning?.players?.length ?? 0) > 0;
  }

  private withBallActionPassTotals(
    stats: CsvDerivedStats | null,
    ballActions: BallActionPredictionsPayload | null
  ): CsvDerivedStats | null {
    if (stats?.pass_totals && Object.keys(stats.pass_totals).length > 0) {
      return stats;
    }

    const passTotals = this.passTotalsFromBallActions(ballActions);
    if (!passTotals) {
      return stats;
    }

    return {
      pass_totals: passTotals,
      positioning: stats?.positioning ?? { teams: {}, players: [] }
    };
  }

  private passTotalsFromBallActions(
    ballActions: BallActionPredictionsPayload | null
  ): Record<string, TeamPassStats> | null {
    const counts = new Map<number, number>();

    for (const prediction of ballActions?.predictions ?? []) {
      const label = String(prediction.label ?? '').trim().toUpperCase();
      if (label !== 'PASS' && label !== 'HIGH PASS') {
        continue;
      }

      const team = String(prediction.team ?? '').trim().toLowerCase();
      const teamId = team === 'left' ? 0 : team === 'right' ? 1 : null;
      if (teamId === null) {
        continue;
      }

      counts.set(teamId, (counts.get(teamId) ?? 0) + 1);
    }

    if (counts.size === 0) {
      return null;
    }

    const rows: Record<string, TeamPassStats> = {};
    for (const [teamId, total] of counts.entries()) {
      const teamKey = `team_${teamId}`;
      rows[teamKey] = {
        team_id: teamId,
        team_key: teamKey,
        total_passes: total,
        successful_passes: total,
        unsuccessful_passes: 0,
        completion_rate: 1,
        completion_pct: 100,
        crosses: 0,
        interceptions: 0,
        avg_distance_m: null,
        total_distance_m: null
      };
    }

    return rows;
  }

  private applyDerivedStats(stats?: CsvDerivedStats, csvFiles?: Record<string, CsvFileLink>) {
    this.csvFiles = csvFiles ?? {};

    if (!stats) {
      this.clearDerivedStats(false);
      return;
    }

    this.passStatsRows = Object.values(stats.pass_totals ?? {}).sort((a, b) => a.team_id - b.team_id);
    this.teamPositionRows = Object.values(stats.positioning?.teams ?? {}).sort((a, b) => a.team_id - b.team_id);
    this.playerPositionRows = [...(stats.positioning?.players ?? [])].sort((a, b) => {
      if (a.team_id !== b.team_id) return a.team_id - b.team_id;
      if (a.is_goalkeeper !== b.is_goalkeeper) return Number(a.is_goalkeeper) - Number(b.is_goalkeeper);
      return String(a.tracker_id).localeCompare(String(b.tracker_id), undefined, { numeric: true });
    });

    if (this.passStatsRows.length === 0 && (this.teamPositionRows.length > 0 || this.playerPositionRows.length > 0)) {
      this.passStatsRows = this.zeroPassRowsFromPositioning();
    }

    localStorage.setItem('last_detection_derived_stats', JSON.stringify(stats));
  }

  private zeroPassRowsFromPositioning(): TeamPassStats[] {
    const teamIds = new Set<number>();
    for (const row of this.teamPositionRows) {
      teamIds.add(Number(row.team_id));
    }
    for (const row of this.playerPositionRows) {
      teamIds.add(Number(row.team_id));
    }

    if (teamIds.size === 0) {
      teamIds.add(0);
      teamIds.add(1);
    }

    return [...teamIds]
      .filter((teamId) => !Number.isNaN(teamId))
      .sort((a, b) => a - b)
      .map((teamId) => ({
        team_id: teamId,
        team_key: `team_${teamId}`,
        total_passes: 0,
        successful_passes: 0,
        unsuccessful_passes: 0,
        completion_rate: 0,
        completion_pct: 0,
        crosses: 0,
        interceptions: 0,
        avg_distance_m: null,
        total_distance_m: null
      }));
  }

  private loadHistoricalTrackingStats(processingJobId: string): void {
    this.stopPolling();
    this.loading = false;
    this.error = '';
    this.currentStage = 'done';
    this.progress = 100;
    this.selectedFile = null;
    this.previewUrl = null;
    this.releaseAnnotatedVideoUrl();
    this.annotatedVideoUrl = null;
    this.selectedHistoryTitle = this.jobLabel(
      this.historyJobs.find((job) => job.id === processingJobId) ?? null
    );

    forkJoin({
      stats: this.jobStatistics.getLatestByJobAndType<CsvDerivedStats>(processingJobId, 'passes_and_positioning'),
      ballActions: this.jobStatistics
        .getLatestByJobAndType<BallActionPredictionsPayload>(processingJobId, 'ball_action_predictions')
        .pipe(catchError(() => of(null)))
    }).subscribe({
      next: ({ stats, ballActions }) => {
        const effectiveStats = this.withBallActionPassTotals(stats, ballActions);

        if (!effectiveStats || !this.hasAnyDerivedStats(effectiveStats)) {
          this.clearDerivedStats(false);
          this.error = 'This saved process does not have tracking statistics in the database.';
          return;
        }

        this.applyDerivedStats(effectiveStats);
        this.loadAnnotatedVideo(`/video/${processingJobId}`, true);
      },
      error: () => {
        this.clearDerivedStats(false);
        this.error = 'Could not load saved tracking statistics for this process.';
      }
    });
  }

  private restoreDerivedStats() {
    const rawStats = localStorage.getItem('last_detection_derived_stats');
    if (!rawStats) return;

    try {
      this.applyDerivedStats(JSON.parse(rawStats) as CsvDerivedStats);
    } catch {
      localStorage.removeItem('last_detection_derived_stats');
      this.clearDerivedStats();
    }
  }

  private clearDerivedStats(clearStorage = true) {
    this.csvFiles = {};
    this.passStatsRows = [];
    this.teamPositionRows = [];
    this.playerPositionRows = [];

    if (clearStorage) {
      localStorage.removeItem('last_detection_derived_stats');
    }
  }

  private buildStatusMessage(): string {
    switch (this.currentStage) {
      case 'uploading':
        return 'Uploading video...';
      case 'queued':
        return 'Queued and waiting to start...';
      case 'preparing_video':
        return 'Preparing video for analysis...';
      case 'training_team_classifier':
        return 'Learning team colors...';
      case 'processing_frames':
        if (this.totalFrames > 0) {
          return `Analyzing frames ${Math.min(this.processedFrames, this.totalFrames)} / ${this.totalFrames}...`;
        }
        return 'Analyzing video frames...';
      case 'encoding':
        return 'Encoding the result video...';
      case 'done':
        return 'Processing complete.';
      default:
        return 'Processing video...';
    }
  }

  private stopPolling() {
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
      this.pollSubscription = undefined;
    }
  }

  private releasePreviewUrl() {
    if (this.previewUrl) {
      URL.revokeObjectURL(this.previewUrl);
    }
  }

  private loadAnnotatedVideo(videoPath: string, silent = false) {
    const separator = videoPath.includes('?') ? '&' : '?';
    this.http.get(`${this.API}${videoPath}${separator}t=${Date.now()}`, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        this.releaseAnnotatedVideoUrl();
        this.annotatedVideoObjectUrl = URL.createObjectURL(blob);
        this.annotatedVideoUrl = this.annotatedVideoObjectUrl;
        localStorage.setItem('last_completed_job_path', videoPath);
        localStorage.removeItem('last_completed_job_url');
      },
      error: () => {
        if (!silent) {
          this.error = 'Could not load the processed video.';
        }
      }
    });
  }

  private releaseAnnotatedVideoUrl() {
    if (this.annotatedVideoObjectUrl) {
      URL.revokeObjectURL(this.annotatedVideoObjectUrl);
      this.annotatedVideoObjectUrl = null;
    }
  }
}

