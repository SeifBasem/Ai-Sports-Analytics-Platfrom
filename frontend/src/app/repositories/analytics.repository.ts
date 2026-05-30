import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { AdminDashboardApiResponse } from '../models/api.model';
import { AnalyticsData, ChartType } from '../models/analytics.model';

@Injectable({
    providedIn: 'root'
})
export class AnalyticsRepository {
    private readonly apiUrl = `${environment.apiBaseUrl}/admin/dashboard`;

    constructor(private http: HttpClient) { }

    getAnalytics(): Observable<AnalyticsData> {
        return this.http.get<AdminDashboardApiResponse>(this.apiUrl).pipe(
            map((dashboard) => ({
                overview: {
                    totalVideos: dashboard.totalVideos,
                    totalAnalysis: dashboard.processingJobs,
                    accuracy: dashboard.processingJobs === 0
                        ? 0
                        : (dashboard.completedJobs / dashboard.processingJobs) * 100,
                    processingTime: dashboard.storedStatistics
                },
                charts: [
                    {
                        id: 'jobs-by-status',
                        type: ChartType.BAR,
                        title: 'Jobs by Status',
                        data: dashboard.jobStatusCounts.map((row) => ({
                            label: row.status,
                            value: row.count
                        }))
                    },
                    {
                        id: 'videos-by-status',
                        type: ChartType.PIE,
                        title: 'Videos by Status',
                        data: dashboard.videoStatusCounts.map((row) => ({
                            label: row.status,
                            value: row.count
                        }))
                    }
                ],
                insights: []
            }))
        );
    }
}
