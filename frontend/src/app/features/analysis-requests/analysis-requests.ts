import { Component, OnInit } from '@angular/core';
import { AnalysisRequest } from '../../models/admin.model';
import { AdminApiService } from '../../services/admin-api.service';
import { DataTableAction, DataTableActionEvent, DataTableColumn, DataTableRow } from '../../shared/data-table/data-table';

@Component({
  selector: 'app-analysis-requests-page',
  standalone: false,
  templateUrl: './analysis-requests.html',
  styleUrl: './analysis-requests.scss'
})
export class AnalysisRequestsPage implements OnInit {
  requests: AnalysisRequest[] = [];
  selectedRequest: AnalysisRequest | null = null;
  notice = '';

  columns: DataTableColumn[] = [
    { key: 'id', label: 'Id' },
    { key: 'videoTitle', label: 'Video Title' },
    { key: 'requestedBy', label: 'Requested By' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'requestedAt', label: 'Requested At' },
    { key: 'startedAt', label: 'Started At' },
    { key: 'completedAt', label: 'Completed At' },
    { key: 'errorMessage', label: 'Error Message', type: 'longText' }
  ];

  actions: DataTableAction[] = [
    { id: 'view', label: 'View', icon: 'eye', variant: 'secondary' },
    { id: 'retry', label: 'Retry', icon: 'rotate-ccw', variant: 'warning', visibleForStatus: ['Failed'] },
    { id: 'cancel', label: 'Cancel', icon: 'ban', variant: 'danger', visibleForStatus: ['Pending', 'Processing'] }
  ];

  constructor(private adminData: AdminApiService) { }

  ngOnInit(): void {
    this.loadRequests();
  }

  get rows(): DataTableRow[] {
    return this.requests.map((request) => ({
      id: request.id,
      videoTitle: request.videoTitle,
      requestedBy: request.requestedBy,
      status: request.status,
      requestedAt: request.requestedAt,
      startedAt: request.startedAt,
      completedAt: request.completedAt,
      errorMessage: request.errorMessage
    }));
  }

  handleAction(event: DataTableActionEvent): void {
    const id = String(event.row['id']);
    const request = this.requests.find((item) => item.id === id);

    if (!request) {
      return;
    }

    if (event.actionId === 'view') {
      this.selectedRequest = request;
    }

    if (event.actionId === 'retry') {
      this.adminData.retryRequest(request).subscribe((retry) => {
        this.notice = `${retry.id} has been started as a retry.`;
        this.loadRequests();
      });
    }

    if (event.actionId === 'cancel') {
      this.adminData.cancelRequest(id).subscribe(() => {
        this.notice = `${request.id} has been cancelled.`;
        this.loadRequests();
      });
    }
  }

  closeNotice(): void {
    this.notice = '';
  }

  private loadRequests(): void {
    this.adminData.getAnalysisRequests().subscribe((requests) => {
      this.requests = requests;
    });
  }
}
