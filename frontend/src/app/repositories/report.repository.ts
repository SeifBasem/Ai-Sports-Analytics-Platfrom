import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { PagedResponse, ReportApiResponse } from '../models/api.model';
import { Report, ReportConfig, ReportFormat, ReportStatus, ReportType } from '../models/report.model';
import { BaseRepository } from './base.repository';

@Injectable({
    providedIn: 'root'
})
export class ReportRepository extends BaseRepository<Report> {
    protected override apiUrl = `${environment.apiBaseUrl}/reports`;

    constructor(private http: HttpClient) {
        super();
    }

    override getAll(): Observable<Report[]> {
        const params = new HttpParams().set('page', '1').set('pageSize', '100');
        return this.http.get<PagedResponse<ReportApiResponse>>(this.apiUrl, { params }).pipe(
            map((page) => page.items.map((report) => this.mapReport(report)))
        );
    }

    override getById(id: string): Observable<Report> {
        return this.http.get<ReportApiResponse>(`${this.apiUrl}/${id}`).pipe(
            map((report) => this.mapReport(report))
        );
    }

    override create(report: Report): Observable<Report> {
        return this.http.post<ReportApiResponse>(this.apiUrl, {
            title: report.title,
            description: report.description,
            reportType: this.toApiReportType(report.type),
            format: this.toApiReportFormat(report.format),
            filePath: null
        }).pipe(
            map((created) => this.mapReport(created))
        );
    }

    override update(id: string, report: Report): Observable<Report> {
        return this.http.put<ReportApiResponse>(`${this.apiUrl}/${id}`, {
            title: report.title,
            description: report.description,
            status: this.toApiReportStatus(report.status),
            filePath: null
        }).pipe(
            map((updated) => this.mapReport(updated))
        );
    }

    override delete(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/${id}`);
    }

    generate(config: ReportConfig): Observable<Report> {
        const type = this.toApiReportType(config.type);
        return this.http.post<ReportApiResponse>(this.apiUrl, {
            title: `${type} Report`,
            description: 'Generated report',
            reportType: type,
            format: this.toApiReportFormat(config.format),
            filePath: null
        }).pipe(
            map((created) => this.mapReport(created))
        );
    }

    private mapReport(report: ReportApiResponse): Report {
        return {
            id: report.id,
            title: report.title,
            description: report.description ?? '',
            type: this.mapReportType(report.reportType),
            createdDate: new Date(report.createdAt),
            status: this.mapReportStatus(report.status),
            data: report,
            format: this.mapReportFormat(report.format)
        };
    }

    private mapReportType(type: string): ReportType {
        switch (type.toLowerCase()) {
            case 'teamanalysis':
                return ReportType.TEAM_ANALYSIS;
            case 'playerstats':
                return ReportType.PLAYER_STATS;
            case 'matchsummary':
                return ReportType.MATCH_SUMMARY;
            case 'performance':
            default:
                return ReportType.PERFORMANCE;
        }
    }

    private mapReportStatus(status: string): ReportStatus {
        switch (status.toLowerCase()) {
            case 'generating':
                return ReportStatus.GENERATING;
            case 'failed':
                return ReportStatus.ERROR;
            case 'ready':
            case 'draft':
            case 'archived':
            default:
                return ReportStatus.READY;
        }
    }

    private mapReportFormat(format: string): ReportFormat {
        switch (format.toLowerCase()) {
            case 'excel':
                return ReportFormat.EXCEL;
            case 'json':
                return ReportFormat.JSON;
            case 'pdf':
            default:
                return ReportFormat.PDF;
        }
    }

    private toApiReportType(type: ReportType): string {
        switch (type) {
            case ReportType.TEAM_ANALYSIS:
                return 'TeamAnalysis';
            case ReportType.PLAYER_STATS:
                return 'PlayerStats';
            case ReportType.MATCH_SUMMARY:
                return 'MatchSummary';
            case ReportType.PERFORMANCE:
            default:
                return 'Performance';
        }
    }

    private toApiReportStatus(status: ReportStatus): string {
        switch (status) {
            case ReportStatus.GENERATING:
                return 'Generating';
            case ReportStatus.ERROR:
                return 'Failed';
            case ReportStatus.READY:
            default:
                return 'Ready';
        }
    }

    private toApiReportFormat(format: ReportFormat): string {
        switch (format) {
            case ReportFormat.EXCEL:
                return 'Excel';
            case ReportFormat.JSON:
                return 'Json';
            case ReportFormat.PDF:
            default:
                return 'Pdf';
        }
    }
}
