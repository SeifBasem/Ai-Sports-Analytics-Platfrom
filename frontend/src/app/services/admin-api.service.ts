import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, forkJoin, map, switchMap, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  AdminDashboardApiResponse,
  CreateProcessingJobApiRequest,
  CreateVideoRecordApiRequest,
  JobStatisticApiResponse,
  PagedResponse,
  ProcessingJobApiResponse,
  UpdateProcessingJobStatusApiRequest,
  UserApiResponse,
  VideoApiResponse
} from '../models/api.model';
import {
  AdminUser,
  AnalysisRequest,
  AnalysisResult,
  DashboardStats,
  DetectedAction,
  SportsVideo
} from '../models/admin.model';

@Injectable({
  providedIn: 'root'
})
export class AdminApiService {
  private readonly apiUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<AdminDashboardApiResponse>(`${this.apiUrl}/admin/dashboard`).pipe(
      map((stats) => ({
        totalUsers: stats.totalUsers,
        totalUploadedVideos: stats.totalVideos,
        totalAnalysisRequests: stats.processingJobs,
        completedAnalyses: stats.completedJobs,
        pendingAnalyses: this.statusCount(stats.jobStatusCounts, 'Queued') + this.statusCount(stats.jobStatusCounts, 'Running'),
        failedAnalyses: stats.failedJobs
      }))
    );
  }

  getUsers(): Observable<AdminUser[]> {
    const params = this.pageParams();
    return this.http.get<PagedResponse<UserApiResponse>>(`${this.apiUrl}/users`, { params }).pipe(
      map((page) => page.items.map((user) => this.mapUser(user)))
    );
  }

  updateUser(user: AdminUser): Observable<AdminUser> {
    return this.http.put<UserApiResponse>(`${this.apiUrl}/users/${user.id}`, {
      fullName: user.fullName,
      email: user.email
    }).pipe(
      switchMap(() => this.http.patch<UserApiResponse>(`${this.apiUrl}/users/${user.id}/role`, { role: user.role })),
      switchMap(() => this.http.patch<UserApiResponse>(`${this.apiUrl}/users/${user.id}/status`, { isActive: user.status === 'Active' })),
      map((updated) => this.mapUser(updated))
    );
  }

  deactivateUser(id: string): Observable<AdminUser> {
    return this.http.patch<UserApiResponse>(`${this.apiUrl}/users/${id}/status`, { isActive: false }).pipe(
      map((user) => this.mapUser(user))
    );
  }

  deleteUser(id: string): Observable<AdminUser> {
    return this.deactivateUser(id);
  }

  getVideos(): Observable<SportsVideo[]> {
    const params = this.pageParams();
    return this.http.get<PagedResponse<VideoApiResponse>>(`${this.apiUrl}/videos`, { params }).pipe(
      map((page) => page.items.map((video) => this.mapVideo(video)))
    );
  }

  addVideo(title: string, description: string, file: File): Observable<SportsVideo> {
    const storedFilename = `${Date.now()}-${file.name}`;
    const payload: CreateVideoRecordApiRequest = {
      title,
      originalFilename: file.name,
      storedFilename,
      mimeType: file.type || 'application/octet-stream',
      storagePath: `admin-uploads/${storedFilename}`,
      sizeBytes: file.size,
      durationSeconds: null
    };

    return this.http.post<VideoApiResponse>(`${this.apiUrl}/videos`, payload).pipe(
      map((video) => ({
        ...this.mapVideo(video),
        description: description || `Original file: ${video.originalFilename}`
      }))
    );
  }

  deleteVideo(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/videos/${id}`);
  }

  startAnalysis(video: SportsVideo): Observable<AnalysisRequest> {
    const payload: CreateProcessingJobApiRequest = {
      videoId: video.id,
      jobType: 'VideoDetection',
      modelName: 'football_analyzer',
      inputPath: video.storagePath || video.originalFilename || video.title
    };

    return this.http.post<ProcessingJobApiResponse>(`${this.apiUrl}/processing-jobs`, payload).pipe(
      map((job) => this.mapJob(job))
    );
  }

  getAnalysisRequests(): Observable<AnalysisRequest[]> {
    const params = this.pageParams();
    return this.http.get<PagedResponse<ProcessingJobApiResponse>>(`${this.apiUrl}/processing-jobs`, { params }).pipe(
      map((page) => page.items.map((job) => this.mapJob(job)))
    );
  }

  retryRequest(request: AnalysisRequest): Observable<AnalysisRequest> {
    if (!request.videoId) {
      return throwError(() => new Error('This analysis request has no video id.'));
    }

    const payload: CreateProcessingJobApiRequest = {
      videoId: request.videoId,
      jobType: request.jobType || 'VideoDetection',
      modelName: request.modelName || 'football_analyzer',
      inputPath: request.inputPath || request.videoTitle
    };

    return this.http.post<ProcessingJobApiResponse>(`${this.apiUrl}/processing-jobs`, payload).pipe(
      map((job) => this.mapJob(job))
    );
  }

  cancelRequest(id: string): Observable<AnalysisRequest> {
    const payload: UpdateProcessingJobStatusApiRequest = {
      status: 'Cancelled',
      progressPercent: 100
    };

    return this.http.patch<ProcessingJobApiResponse>(`${this.apiUrl}/processing-jobs/${id}/status`, payload).pipe(
      map((job) => this.mapJob(job))
    );
  }

  getAnalysisResults(): Observable<AnalysisResult[]> {
    const params = this.pageParams();
    const stats$ = this.http.get<PagedResponse<JobStatisticApiResponse>>(`${this.apiUrl}/job-statistics`, { params });
    const jobs$ = this.http.get<PagedResponse<ProcessingJobApiResponse>>(`${this.apiUrl}/processing-jobs`, { params });

    return forkJoin({ stats: stats$, jobs: jobs$ }).pipe(
      map(({ stats, jobs }) => {
        const jobsById = new Map(jobs.items.map((job) => [job.id, job]));
        return stats.items.map((stat) => this.mapAnalysisResult(stat, jobsById.get(stat.processingJobId)));
      })
    );
  }

  private pageParams(): HttpParams {
    return new HttpParams().set('page', '1').set('pageSize', '100');
  }

  private statusCount(rows: Array<{ status: string; count: number }>, status: string): number {
    return rows.find((row) => row.status.toLowerCase() === status.toLowerCase())?.count ?? 0;
  }

  private mapUser(user: UserApiResponse): AdminUser {
    return {
      id: user.id,
      fullName: user.fullName,
      email: user.email,
      role: user.role === 'Admin' ? 'Admin' : 'User',
      status: user.isActive ? 'Active' : 'Inactive',
      createdAt: this.formatDateTime(user.createdAt)
    };
  }

  private mapVideo(video: VideoApiResponse): SportsVideo {
    return {
      id: video.id,
      title: video.title,
      description: video.errorMessage || `Original file: ${video.originalFilename}`,
      uploadedBy: video.uploadedBy || '-',
      uploadDate: this.formatDateTime(video.uploadedAt),
      status: this.mapVideoStatus(video.status),
      storagePath: video.storagePath,
      originalFilename: video.originalFilename,
      sizeBytes: video.sizeBytes
    };
  }

  private mapJob(job: ProcessingJobApiResponse): AnalysisRequest {
    return {
      id: job.id,
      videoId: job.videoId,
      videoTitle: job.videoTitle || job.inputPath || 'Untitled video',
      requestedBy: job.requestedBy || '-',
      status: this.mapAnalysisStatus(job.status),
      requestedAt: this.formatDateTime(job.createdAt),
      startedAt: job.startedAt ? this.formatDateTime(job.startedAt) : null,
      completedAt: job.completedAt ? this.formatDateTime(job.completedAt) : null,
      errorMessage: job.errorMessage ?? null,
      inputPath: job.inputPath,
      jobType: job.jobType,
      modelName: job.modelName
    };
  }

  private mapAnalysisResult(stat: JobStatisticApiResponse, job: ProcessingJobApiResponse | undefined): AnalysisResult {
    const parsed = this.parseStatsJson(stat.statsJson);
    const actions = this.extractDetectedActions(parsed);
    const confidenceScore = actions.length > 0
      ? Math.round(actions.reduce((sum, action) => sum + action.confidence, 0) / actions.length)
      : 100;

    return {
      id: stat.id,
      videoTitle: job?.videoTitle || `Job ${stat.processingJobId.slice(0, 8)}`,
      resultSummary: this.buildSummary(stat, parsed, actions.length),
      detectedSportAction: `${stat.moduleName} / ${stat.statType}`,
      confidenceScore,
      recommendations: 'Review the persisted AI statistics and compare low-confidence segments against the processed video.',
      createdAt: this.formatDateTime(stat.createdAt),
      detectedActions: actions
    };
  }

  private parseStatsJson(value: string): unknown {
    try {
      return JSON.parse(value) as unknown;
    } catch {
      return null;
    }
  }

  private extractDetectedActions(value: unknown): DetectedAction[] {
    if (!this.isRecord(value)) {
      return [];
    }

    const rawActions = Array.isArray(value['actions']) ? value['actions'] : [];
    return rawActions.map((action, index) => this.mapDetectedAction(action, index));
  }

  private mapDetectedAction(value: unknown, index: number): DetectedAction {
    if (!this.isRecord(value)) {
      return {
        timestamp: this.formatSeconds(index),
        action: 'Unknown',
        confidence: 0
      };
    }

    const confidenceValue = this.toNumber(value['confidence']);
    return {
      timestamp: this.formatSeconds(this.toNumber(value['start_time'])),
      action: String(value['action'] ?? value['label'] ?? 'Unknown'),
      confidence: confidenceValue <= 1 ? Math.round(confidenceValue * 100) : Math.round(confidenceValue)
    };
  }

  private buildSummary(stat: JobStatisticApiResponse, parsed: unknown, detectedActions: number): string {
    if (stat.statType === 'action_segments') {
      return `${detectedActions} action segment${detectedActions === 1 ? '' : 's'} persisted from the action recognition module.`;
    }

    if (stat.statType === 'ball_action_stats' && this.isRecord(parsed)) {
      const total = this.sumNestedNumbers(parsed);
      return `${total} ball action event${total === 1 ? '' : 's'} persisted from the ball action module.`;
    }

    if (stat.statType === 'player_stats' && this.isRecord(parsed)) {
      return `${Object.keys(parsed).length} tracked player profile${Object.keys(parsed).length === 1 ? '' : 's'} persisted from the analyzer.`;
    }

    return `Statistics persisted as ${stat.statType}.`;
  }

  private sumNestedNumbers(value: unknown): number {
    if (typeof value === 'number') {
      return value;
    }

    if (Array.isArray(value)) {
      return value.reduce((sum, item) => sum + this.sumNestedNumbers(item), 0);
    }

    if (this.isRecord(value)) {
      return Object.values(value).reduce<number>((sum, item) => sum + this.sumNestedNumbers(item), 0);
    }

    return 0;
  }

  private isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  private toNumber(value: unknown): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : 0;
  }

  private mapVideoStatus(status: string): SportsVideo['status'] {
    switch (status.toLowerCase()) {
      case 'processing':
      case 'queued':
        return 'Processing';
      case 'ready':
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'uploaded':
      default:
        return 'Uploaded';
    }
  }

  private mapAnalysisStatus(status: string): AnalysisRequest['status'] {
    switch (status.toLowerCase()) {
      case 'queued':
        return 'Pending';
      case 'running':
        return 'Processing';
      case 'completed':
        return 'Completed';
      case 'failed':
      case 'cancelled':
      default:
        return 'Failed';
    }
  }

  private formatDateTime(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    const datePart = date.toISOString().slice(0, 10);
    const timePart = date.toTimeString().slice(0, 5);
    return `${datePart} ${timePart}`;
  }

  private formatSeconds(value: number): string {
    const minutes = Math.floor(value / 60);
    const seconds = Math.floor(value % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }
}
