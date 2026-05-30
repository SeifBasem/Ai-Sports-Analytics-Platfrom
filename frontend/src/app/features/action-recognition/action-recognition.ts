import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

interface ActionResult {
  action: string;
  confidence: number;
  start_frame: number;
  end_frame: number;
  start_time: number;
  end_time: number;
  sourceVideo?: string;  // track which video this came from
}

interface RecognitionResponse {
  job_id: string;
  status: string;
  progress: number;
  stage?: string;
  actions?: ActionResult[];
  annotated_video_url?: string;
  thumbnail_url?: string;
  error?: string;
  total_actions?: number;
  video_duration?: number;
}

export interface VideoEntry {
  file: File;
  previewUrl: string;
  status: 'pending' | 'uploading' | 'processing' | 'done' | 'error';
  jobId: string | null;
  jobStage: string;
  progress: number;
  error: string;
  actions: ActionResult[];
  totalActions: number;
  videoDuration: number;
  annotatedVideoUrl: string | null;
}

@Component({
  selector: 'app-action-recognition',
  standalone: false,
  templateUrl: './action-recognition.html',
  styleUrls: ['./action-recognition.scss']
})
export class ActionRecognition {
  readonly API = environment.aiApiBaseUrl;

  apiStatus: 'unknown' | 'ok' | 'down' = 'unknown';
  playerName = '';
  private uploadBatchId = '';

  // Multi-video queue
  videos: VideoEntry[] = [];
  loading = false;
  showResults = false;
  error = '';

  // Combined results
  allActions: ActionResult[] = [];
  totalActions = 0;
  totalDuration = 0;

  // Filters
  filterAction = '';
  minConfidence = 0;
  sortBy: 'time' | 'confidence' | 'action' = 'time';
  sortDir: 'asc' | 'desc' = 'asc';

  // Processing state
  currentVideoIndex = -1;
  pollingInterval: any = null;

  // Action color mapping (matches the 10 model classes)
  readonly actionColors: Record<string, string> = {
    'corner':       '#f97316',
    'foul':         '#ef4444',
    'freekick':     '#14b8a6',
    'goalkick':     '#3b82f6',
    'longpass':     '#8b5cf6',
    'ontarget':     '#ec4899',
    'penalty':      '#eab308',
    'shortpass':    '#6366f1',
    'substitution': '#10b981',
    'throw-in':     '#06b6d4',
  };

  constructor(private http: HttpClient, private router: Router) {
    this.checkHealth();
  }

  checkHealth(): void {
    this.http.get<{ status: string }>(`${this.API}/health`).subscribe({
      next: () => (this.apiStatus = 'ok'),
      error: () => (this.apiStatus = 'down')
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;
    this.addFiles(Array.from(input.files));
    input.value = '';  // allow re-selecting same files
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    const files = event.dataTransfer?.files;
    if (files?.length) {
      const videoFiles = Array.from(files).filter(f => f.type.startsWith('video/'));
      if (videoFiles.length) {
        this.addFiles(videoFiles);
      } else {
        this.error = 'Please drop video files only.';
      }
    }
  }

  private addFiles(files: File[]): void {
    this.error = '';
    this.showResults = false;
    for (const file of files) {
      // Prevent duplicates by name+size
      const exists = this.videos.some(v => v.file.name === file.name && v.file.size === file.size);
      if (!exists) {
        this.videos.push({
          file,
          previewUrl: URL.createObjectURL(file),
          status: 'pending',
          jobId: null,
          jobStage: '',
          progress: 0,
          error: '',
          actions: [],
          totalActions: 0,
          videoDuration: 0,
          annotatedVideoUrl: null
        });
      }
    }
  }

  removeVideo(index: number): void {
    if (this.loading) return;
    URL.revokeObjectURL(this.videos[index].previewUrl);
    this.videos.splice(index, 1);
  }

  get overallProgress(): number {
    if (!this.videos.length) return 0;
    const totalProgress = this.videos.reduce((sum, v) => {
      if (v.status === 'done') return sum + 100;
      if (v.status === 'error') return sum + 100;
      return sum + v.progress;
    }, 0);
    return Math.round(totalProgress / this.videos.length);
  }

  get completedCount(): number {
    return this.videos.filter(v => v.status === 'done').length;
  }

  recognizeAll(): void {
    if (!this.videos.length) return;
    this.loading = true;
    this.error = '';
    this.showResults = false;
    this.allActions = [];
    this.totalActions = 0;
    this.totalDuration = 0;
    this.currentVideoIndex = 0;
    this.uploadBatchId = crypto.randomUUID();
    this.processNextVideo();
  }

  private processNextVideo(): void {
    if (this.currentVideoIndex >= this.videos.length) {
      // All done — combine results
      this.combineResults();
      return;
    }

    const video = this.videos[this.currentVideoIndex];
    video.status = 'uploading';
    video.progress = 0;

    const form = new FormData();
    form.append('video', video.file);
    form.append('upload_batch_id', this.uploadBatchId);
    form.append('upload_batch_title', this.sessionTitle);
    form.append('upload_batch_video_count', String(this.videos.length));
    form.append('upload_batch_index', String(this.currentVideoIndex + 1));
    form.append('player_name', this.playerName.trim());

    this.http.post<RecognitionResponse>(`${this.API}/recognize_action`, form).subscribe({
      next: (res) => {
        if (res.error) {
          video.status = 'error';
          video.error = res.error;
          this.currentVideoIndex++;
          this.processNextVideo();
          return;
        }
        video.jobId = res.job_id;
        video.status = 'processing';
        video.progress = res.progress;
        this.startPolling(video);
      },
      error: (err) => {
        video.status = 'error';
        video.error = err.error?.error || err.message || 'Failed to reach the action recognition API.';
        this.currentVideoIndex++;
        this.processNextVideo();
      }
    });
  }

  private startPolling(video: VideoEntry): void {
    if (this.pollingInterval) clearInterval(this.pollingInterval);

    this.pollingInterval = setInterval(() => {
      if (!video.jobId) return;

      this.http.get<RecognitionResponse>(`${this.API}/action_job_status/${video.jobId}`).subscribe({
        next: (res) => {
          video.jobStage = res.stage || res.status;
          video.progress = res.progress;

          if (res.status === 'done') {
            this.stopPolling();
            video.status = 'done';
            video.actions = (res.actions || []).map(a => ({
              ...a,
              sourceVideo: video.file.name
            }));
            video.totalActions = res.total_actions || video.actions.length;
            video.videoDuration = res.video_duration || 0;
            video.annotatedVideoUrl = res.annotated_video_url
              ? `${this.API}${res.annotated_video_url}` : null;
            video.progress = 100;

            // Move to next video
            this.currentVideoIndex++;
            this.processNextVideo();
          } else if (res.status === 'error') {
            this.stopPolling();
            video.status = 'error';
            video.error = res.error || 'An unknown error occurred during action recognition.';

            this.currentVideoIndex++;
            this.processNextVideo();
          }
        },
        error: () => {
          this.stopPolling();
          video.status = 'error';
          video.error = 'Lost connection to the server while polling for results.';

          this.currentVideoIndex++;
          this.processNextVideo();
        }
      });
    }, 1500);
  }

  private stopPolling(): void {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  private combineResults(): void {
    this.loading = false;
    this.allActions = [];
    this.totalActions = 0;
    this.totalDuration = 0;

    const videoResults: any[] = [];
    for (const video of this.videos) {
      if (video.status === 'done') {
        this.allActions.push(...video.actions);
        this.totalActions += video.totalActions;
        this.totalDuration += video.videoDuration;
        videoResults.push({
          name: video.file.name,
          totalActions: video.totalActions,
          videoDuration: video.videoDuration,
          annotatedVideoUrl: video.annotatedVideoUrl,
          actions: video.actions
        });
      }
    }

    if (this.allActions.length > 0) {
      this.showResults = true;
      this.router.navigate(['/player-action-analytics']);
    } else {
      this.error = 'No results were obtained. All videos failed processing.';
    }
  }

  getActionColor(action: string): string {
    const key = action.toLowerCase().replace(/\s+/g, '-');
    return this.actionColors[key] || '#6366f1';
  }

  getStageLabel(video: VideoEntry): string {
    const stage = video.jobStage || video.status;
    switch (stage) {
      case 'uploading':       return 'Uploading video…';
      case 'queued':          return 'Queued for processing…';
      case 'extracting':      return 'Extracting video metadata…';
      case 'analyzing':       return 'Running AI model inference…';
      case 'model_inference': return 'Running VGG16+GRU action recognition…';
      case 'post_processing': return 'Post-processing results…';
      case 'encoding':        return 'Encoding annotated video…';
      case 'done':            return 'Complete!';
      case 'error':           return 'Error occurred';
      default:                return 'Processing…';
    }
  }

  formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  formatFileSize(bytes: number): string {
    return (bytes / 1024 / 1024).toFixed(1);
  }

  get filteredActions(): ActionResult[] {
    let result = [...this.allActions];

    if (this.filterAction) {
      const q = this.filterAction.toLowerCase();
      result = result.filter(a => a.action.toLowerCase().includes(q));
    }

    if (this.minConfidence > 0) {
      result = result.filter(a => a.confidence >= this.minConfidence / 100);
    }

    result.sort((a, b) => {
      let cmp = 0;
      switch (this.sortBy) {
        case 'time':       cmp = a.start_time - b.start_time; break;
        case 'confidence': cmp = a.confidence - b.confidence; break;
        case 'action':     cmp = a.action.localeCompare(b.action); break;
      }
      return this.sortDir === 'asc' ? cmp : -cmp;
    });

    return result;
  }

  get uniqueActions(): string[] {
    return [...new Set(this.allActions.map(a => a.action))].sort();
  }

  get actionSummary(): { action: string; count: number; avgConf: number }[] {
    const map = new Map<string, { count: number; totalConf: number }>();
    for (const a of this.allActions) {
      const entry = map.get(a.action) || { count: 0, totalConf: 0 };
      entry.count++;
      entry.totalConf += a.confidence;
      map.set(a.action, entry);
    }
    return Array.from(map.entries())
      .map(([action, { count, totalConf }]) => ({
        action,
        count,
        avgConf: totalConf / count
      }))
      .sort((a, b) => b.count - a.count);
  }

  get hasAnnotatedVideos(): boolean {
    return this.videos.some(v => !!v.annotatedVideoUrl);
  }

  get sessionTitle(): string {
    const player = this.playerName.trim();
    const clipLabel = `${this.videos.length} clip${this.videos.length === 1 ? '' : 's'}`;
    return player ? `${player} - ${clipLabel}` : `Player action session - ${clipLabel}`;
  }

  toggleSort(field: 'time' | 'confidence' | 'action'): void {
    if (this.sortBy === field) {
      this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortBy = field;
      this.sortDir = 'asc';
    }
  }

  resetAll(): void {
    this.stopPolling();
    for (const v of this.videos) {
      URL.revokeObjectURL(v.previewUrl);
    }
    this.videos = [];
    this.loading = false;
    this.error = '';
    this.showResults = false;
    this.allActions = [];
    this.totalActions = 0;
    this.totalDuration = 0;
    this.currentVideoIndex = -1;
    this.filterAction = '';
    this.minConfidence = 0;
    this.uploadBatchId = '';
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }
}
