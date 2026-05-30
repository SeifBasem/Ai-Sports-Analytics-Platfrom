import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { ReportRepository } from '../repositories/report.repository';
import { Report, ReportConfig } from '../models/report.model';

@Injectable({
    providedIn: 'root'
})
export class ReportService {
    private reportsSubject = new BehaviorSubject<Report[]>([]);
    public reports$ = this.reportsSubject.asObservable();

    constructor(private reportRepository: ReportRepository) {
        this.loadReports();
    }

    loadReports(): void {
        this.reportRepository.getAll().subscribe(reports => {
            this.reportsSubject.next(reports);
        });
    }

    getReports(): Observable<Report[]> {
        return this.reports$;
    }

    getReportById(id: string): Observable<Report> {
        return this.reportRepository.getById(id);
    }

    generateReport(config: ReportConfig): Observable<Report> {
        return this.reportRepository.generate(config);
    }

    deleteReport(id: string): void {
        this.reportRepository.delete(id).subscribe(() => {
            const currentReports = this.reportsSubject.value;
            this.reportsSubject.next(currentReports.filter(r => r.id !== id));
        });
    }
}
