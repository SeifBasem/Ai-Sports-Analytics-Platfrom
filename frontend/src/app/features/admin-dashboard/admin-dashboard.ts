import { Component, OnInit } from '@angular/core';
import { AnalysisRequest, DashboardStats, SportsVideo } from '../../models/admin.model';
import { AdminApiService } from '../../services/admin-api.service';
import { DataTableColumn, DataTableRow } from '../../shared/data-table/data-table';

@Component({
  selector: 'app-admin-dashboard',
  standalone: false,
  templateUrl: './admin-dashboard.html',
  styleUrl: './admin-dashboard.scss'
})
export class AdminDashboard implements OnInit {
  stats: DashboardStats = {
    totalUsers: 0,
    totalUploadedVideos: 0,
    totalAnalysisRequests: 0,
    completedAnalyses: 0,
    pendingAnalyses: 0,
    failedAnalyses: 0
  };

  statCards: Array<{ label: string; value: number; icon: string; accent: 'teal' | 'indigo' | 'amber' | 'emerald' | 'rose' | 'sky' }> = [];

  recentVideoColumns: DataTableColumn[] = [
    { key: 'id', label: 'Id' },
    { key: 'title', label: 'Title' },
    { key: 'uploadedBy', label: 'Uploaded By' },
    { key: 'uploadDate', label: 'Upload Date' },
    { key: 'status', label: 'Status', type: 'status' }
  ];

  recentRequestColumns: DataTableColumn[] = [
    { key: 'id', label: 'Id' },
    { key: 'videoTitle', label: 'Video Title' },
    { key: 'requestedBy', label: 'Requested By' },
    { key: 'requestedAt', label: 'Requested At' },
    { key: 'status', label: 'Status', type: 'status' }
  ];

  recentVideoRows: DataTableRow[] = [];
  recentRequestRows: DataTableRow[] = [];

  constructor(private adminData: AdminApiService) { }

  ngOnInit(): void {
    this.loadDashboard();
  }

  private loadDashboard(): void {
    this.adminData.getDashboardStats().subscribe((stats) => {
      this.stats = stats;
      this.statCards = [
        { label: 'Total users', value: this.stats.totalUsers, icon: 'users', accent: 'teal' },
        { label: 'Total uploaded videos', value: this.stats.totalUploadedVideos, icon: 'video', accent: 'sky' },
        { label: 'Total analysis requests', value: this.stats.totalAnalysisRequests, icon: 'clipboard-list', accent: 'indigo' },
        { label: 'Completed analyses', value: this.stats.completedAnalyses, icon: 'check-circle-2', accent: 'emerald' },
        { label: 'Pending analyses', value: this.stats.pendingAnalyses, icon: 'clock-3', accent: 'amber' },
        { label: 'Failed analyses', value: this.stats.failedAnalyses, icon: 'triangle-alert', accent: 'rose' }
      ];
    });

    this.adminData.getVideos().subscribe((videos) => {
      this.recentVideoRows = videos.slice(0, 5).map((video) => this.mapVideoRow(video));
    });

    this.adminData.getAnalysisRequests().subscribe((requests) => {
      this.recentRequestRows = requests.slice(0, 5).map((request) => this.mapRequestRow(request));
    });
  }

  private mapVideoRow(video: SportsVideo): DataTableRow {
    return {
      id: video.id,
      title: video.title,
      uploadedBy: video.uploadedBy,
      uploadDate: video.uploadDate,
      status: video.status
    };
  }

  private mapRequestRow(request: AnalysisRequest): DataTableRow {
    return {
      id: request.id,
      videoTitle: request.videoTitle,
      requestedBy: request.requestedBy,
      requestedAt: request.requestedAt,
      status: request.status
    };
  }
}
