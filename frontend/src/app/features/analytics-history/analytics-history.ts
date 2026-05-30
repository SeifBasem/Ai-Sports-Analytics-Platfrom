import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { JobStatisticsApiService } from '../../services/job-statistics-api.service';
import { ProcessingJobApiResponse } from '../../models/api.model';

interface PlayerActionSessionMetadata {
  uploadBatchId?: string;
  uploadBatchTitle?: string;
  uploadBatchVideoCount?: string;
  uploadBatchIndex?: string;
  playerName?: string;
}

interface HistoryItem {
  id: string;
  jobType: string;
  title: string;
  jobs: ProcessingJobApiResponse[];
  primaryJob: ProcessingJobApiResponse;
  batchId?: string;
  completedAt?: string | null;
  updatedAt: string;
}

@Component({
  selector: 'app-analytics-history',
  standalone: false,
  templateUrl: './analytics-history.html',
  styleUrl: './analytics-history.scss',
})
export class AnalyticsHistory implements OnInit {
  jobs: ProcessingJobApiResponse[] = [];
  historyItems: HistoryItem[] = [];
  filteredItems: HistoryItem[] = [];
  loading = false;
  error = '';
  selectedType = 'All';

  readonly typeOptions = [
    { value: 'All', label: 'All analytics' },
    { value: 'VideoDetection', label: 'Player tracking' },
    { value: 'HeatmapGeneration', label: 'Movement heatmaps' },
    { value: 'BallActionAnalysis', label: 'Match event spotting' },
    { value: 'ActionRecognition', label: 'Player review' },
  ];

  constructor(
    private jobStatistics: JobStatisticsApiService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    this.loading = true;
    this.error = '';

    this.jobStatistics.getCompletedJobs(undefined, 100).subscribe({
      next: (jobs) => {
        this.jobs = jobs;
        this.applyFilter();
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'Could not load analytics history from the backend.';
      }
    });
  }

  applyFilter(): void {
    this.historyItems = this.buildHistoryItems(this.jobs);
    this.filteredItems = this.selectedType === 'All'
      ? [...this.historyItems]
      : this.historyItems.filter((item) => item.jobType === this.selectedType);
  }

  openItem(item: HistoryItem): void {
    const queryParams = item.batchId
      ? { batchId: item.batchId }
      : { jobId: item.primaryJob.id };

    switch (item.jobType) {
      case 'VideoDetection':
        this.router.navigate(['/upload'], { queryParams });
        break;
      case 'BallActionAnalysis':
        this.router.navigate(['/analytics'], { queryParams });
        break;
      case 'ActionRecognition':
        this.router.navigate(['/player-action-analytics'], { queryParams });
        break;
      case 'HeatmapGeneration':
        this.router.navigate(['/heatmap'], { queryParams });
        break;
      default:
        this.router.navigate(['/analytics'], { queryParams });
        break;
    }
  }

  typeLabel(jobType: string): string {
    return this.typeOptions.find((option) => option.value === jobType)?.label ?? jobType;
  }

  formatDate(value?: string | null): string {
    if (!value) return '-';
    return new Date(value).toLocaleString();
  }

  metricLabel(job: ProcessingJobApiResponse): string {
    return this.jobMetricLabel(job);
  }

  itemMetricLabel(item: HistoryItem): string {
    if (item.jobType === 'ActionRecognition') {
      const videoCount = this.sessionVideoCount(item);
      const frameCount = item.jobs.reduce((sum, job) => sum + Number(job.frameCount ?? 0), 0);
      const parts = [`${videoCount} video${videoCount === 1 ? '' : 's'}`];
      if (frameCount > 0) {
        parts.push(`${frameCount.toLocaleString()} frames`);
      }
      return parts.join(' / ');
    }

    return this.jobMetricLabel(item.primaryJob);
  }

  private buildHistoryItems(jobs: ProcessingJobApiResponse[]): HistoryItem[] {
    const items: HistoryItem[] = [];
    const actionGroups = new Map<string, ProcessingJobApiResponse[]>();

    for (const job of jobs) {
      if (job.jobType !== 'ActionRecognition') {
        items.push(this.singleJobItem(job));
        continue;
      }

      const metadata = this.parseMetadata(job);
      const groupId = metadata.uploadBatchId || job.id;
      const group = actionGroups.get(groupId) ?? [];
      group.push(job);
      actionGroups.set(groupId, group);
    }

    for (const [groupId, groupJobs] of actionGroups.entries()) {
      const sorted = [...groupJobs].sort((a, b) => this.dateMs(b.completedAt || b.updatedAt) - this.dateMs(a.completedAt || a.updatedAt));
      const primaryJob = sorted[0];
      const metadata = this.parseMetadata(primaryJob);
      items.push({
        id: groupId,
        jobType: 'ActionRecognition',
        title: metadata.uploadBatchTitle || this.actionSessionTitle(primaryJob, sorted),
        jobs: sorted,
        primaryJob,
        batchId: metadata.uploadBatchId,
        completedAt: primaryJob.completedAt,
        updatedAt: primaryJob.updatedAt
      });
    }

    return items.sort((a, b) => this.dateMs(b.completedAt || b.updatedAt) - this.dateMs(a.completedAt || a.updatedAt));
  }

  private singleJobItem(job: ProcessingJobApiResponse): HistoryItem {
    return {
      id: job.id,
      jobType: job.jobType,
      title: job.videoTitle || 'Untitled process',
      jobs: [job],
      primaryJob: job,
      completedAt: job.completedAt,
      updatedAt: job.updatedAt
    };
  }

  private actionSessionTitle(job: ProcessingJobApiResponse, jobs: ProcessingJobApiResponse[]): string {
    const metadata = this.parseMetadata(job);
    if (metadata.playerName) {
      return `${metadata.playerName} - ${jobs.length} clip${jobs.length === 1 ? '' : 's'}`;
    }
    return job.videoTitle || `Player review - ${jobs.length} clip${jobs.length === 1 ? '' : 's'}`;
  }

  private sessionVideoCount(item: HistoryItem): number {
    const metadata = this.parseMetadata(item.primaryJob);
    const count = Number(metadata.uploadBatchVideoCount);
    return Number.isFinite(count) && count > 0 ? count : item.jobs.length;
  }

  private jobMetricLabel(job: ProcessingJobApiResponse): string {
    const parts: string[] = [];

    if (job.frameCount) {
      parts.push(`${job.frameCount.toLocaleString()} frames`);
    }

    if (job.objectCount) {
      parts.push(`${job.objectCount.toLocaleString()} objects`);
    }

    return parts.length ? parts.join(' / ') : 'Saved analytics';
  }

  private parseMetadata(job: ProcessingJobApiResponse): PlayerActionSessionMetadata {
    if (!job.metadataJson) return {};
    try {
      return JSON.parse(job.metadataJson) as PlayerActionSessionMetadata;
    } catch {
      return {};
    }
  }

  private dateMs(value?: string | null): number {
    return value ? new Date(value).getTime() : 0;
  }
}
