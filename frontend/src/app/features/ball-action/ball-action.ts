import { Component, OnDestroy, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

interface JobResponse {
  job_id: string;
  status: string;
  progress?: number;
  stage?: string;
  error?: string;
}

export interface BallActionStats {
  team_1: { throw_in: number; out: number; high_pass: number; header: number };
  team_2: { throw_in: number; out: number; high_pass: number; header: number };
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
  ball_action_stats?: BallActionStats;
}

interface HealthResponse {
  status: string;
  ball_action_model_loaded?: boolean;
  ball_action_model_error?: string | null;
}

@Component({
  selector: 'app-ball-action',
  standalone: false,
  templateUrl: './ball-action.html',
  styleUrl: './ball-action.scss',
})
export class BallAction implements OnInit, OnDestroy {
  readonly API = environment.aiApiBaseUrl;

  selectedFile: File | null = null;
  previewUrl: string | null = null;
  annotatedVideoUrl: string | null = null;

  loading = false;
  processingMsg = '';
  error = '';
  modelWarning = '';
  apiStatus: 'unknown' | 'ok' | 'down' = 'unknown';
  ballModelReady = false;
  progress = 0;
  currentStage = 'queued';
  processedFrames = 0;
  totalFrames = 0;

  private pollSubscription?: Subscription;
  private annotatedVideoObjectUrl: string | null = null;

  constructor(private http: HttpClient, private router: Router) {
    this.checkHealth();
  }

  ngOnInit() {
    const activeJobId = localStorage.getItem('active_ball_job');

    localStorage.removeItem('last_completed_ball_job_url');
    localStorage.removeItem('last_completed_ball_job_path');

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
            localStorage.removeItem('active_ball_job');
            localStorage.removeItem('last_completed_ball_job_url');
            localStorage.removeItem('last_completed_ball_job_path');
          }
        },
        error: () => {
          // API unreachable — just clear the stale job silently
          localStorage.removeItem('active_ball_job');
        }
      });
    }
  }

  ngOnDestroy() {
    this.stopPolling();
    this.releasePreviewUrl();
    this.releaseAnnotatedVideoUrl();
  }

  checkHealth() {
    this.http.get<HealthResponse>(`${this.API}/health`).subscribe({
      next: (res) => {
        this.apiStatus = 'ok';
        this.ballModelReady = !!res.ball_action_model_loaded;
        this.modelWarning = this.ballModelReady
          ? ''
          : this.buildModelUnavailableMessage(res.ball_action_model_error);
      },
      error: () => {
        this.apiStatus = 'down';
        this.ballModelReady = false;
        this.modelWarning = 'AI API is offline, so action spotting cannot run right now.';
      },
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
    if (!this.ballModelReady) {
      this.error = this.modelWarning || this.buildModelUnavailableMessage();
      this.checkHealth();
      return;
    }

    this.loading = true;
    this.error = '';
    this.annotatedVideoUrl = null;
    this.progress = 2;
    this.currentStage = 'uploading';
    this.processingMsg = 'Uploading video...';
    this.processedFrames = 0;
    this.totalFrames = 0;
    localStorage.removeItem('last_completed_ball_job_url');
    localStorage.removeItem('last_completed_ball_job_path');
    this.clearBallActionStatsCache();

    const form = new FormData();
    form.append('video', this.selectedFile);

    this.http.post<JobResponse>(`${this.API}/ball_action_video`, form).subscribe({
      next: (res) => {
        if (res.error) {
          this.loading = false;
          this.error = res.error;
          return;
        }

        this.progress = res.progress ?? 5;
        this.currentStage = res.stage ?? 'queued';
        this.processingMsg = this.buildStatusMessage();
        localStorage.setItem('active_ball_job', res.job_id);
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
    this.releasePreviewUrl();
    this.releaseAnnotatedVideoUrl();
    this.previewUrl = null;
    this.annotatedVideoUrl = null;
    this.error = '';
    this.loading = false;
    this.processingMsg = '';
    this.progress = 0;
    this.currentStage = 'queued';
    this.processedFrames = 0;
    this.totalFrames = 0;
    this.stopPolling();
    localStorage.removeItem('active_ball_job');
    localStorage.removeItem('last_completed_ball_job_url');
    localStorage.removeItem('last_completed_ball_job_path');
    this.clearBallActionStatsCache();
  }

  private handleFile(file: File) {
    this.reset();

    if (!file.type.startsWith('video/')) {
      this.error = `File type '${file.type || 'unknown'}' is not supported. Please upload a video (.mp4, .mov, etc).`;
      return;
    }

    this.selectedFile = file;
    this.previewUrl = URL.createObjectURL(file);
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
            localStorage.removeItem('active_ball_job');
            if (!this.hasBallActionStats(res.ball_action_stats)) {
              this.error = 'The backend finished, but it did not return action spotting stats.';
              return;
            }
            this.clearBallActionStatsCache();
            this.router.navigate(['/analytics'], { queryParams: { jobId } });
            return;
          }

          if (res.status === 'error') {
            this.stopPolling();
            this.loading = false;
            this.currentStage = 'error';
            this.processingMsg = '';
            this.error = res.error || 'The backend encountered an error processing the video.';
            localStorage.removeItem('active_ball_job');
            return;
          }

          if (res.status === 'not_found') {
            this.stopPolling();
            this.loading = false;
            this.currentStage = 'not_found';
            this.processingMsg = '';
            this.error = 'The processing job was not found on the backend.';
            localStorage.removeItem('active_ball_job');
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
      case 'spotting_events':
        if (this.totalFrames > 0) {
          return `Spotting match events ${Math.min(this.processedFrames, this.totalFrames)} / ${this.totalFrames}...`;
        }
        return 'Spotting match events...';
      case 'post_processing':
        return 'Writing detected events...';
      case 'persisting_results':
        return 'Saving match event results...';
      case 'encoding':
        return 'Finalizing action statistics...';
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

  private hasBallActionStats(stats?: BallActionStats): boolean {
    return !!stats?.team_1 && !!stats.team_2;
  }

  private clearBallActionStatsCache(): void {
    localStorage.removeItem('latest_ball_action_stats');
    localStorage.removeItem('latest_ball_action_stats_source');
  }

  private buildModelUnavailableMessage(detail?: string | null): string {
    return [
      'Action spotting model is not loaded on the AI backend.',
      detail ? `Backend detail: ${detail}` : 'Check ball_model_FULL_OBJECT.pt and restart the Flask API.'
    ].join(' ');
  }

  private loadAnnotatedVideo(videoPath: string) {
    const separator = videoPath.includes('?') ? '&' : '?';
    this.http.get(`${this.API}${videoPath}${separator}t=${Date.now()}`, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        this.releaseAnnotatedVideoUrl();
        this.annotatedVideoObjectUrl = URL.createObjectURL(blob);
        this.annotatedVideoUrl = this.annotatedVideoObjectUrl;
        localStorage.setItem('last_completed_ball_job_path', videoPath);
        localStorage.removeItem('last_completed_ball_job_url');
      },
      error: () => {
        this.error = 'Could not load the processed video.';
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

