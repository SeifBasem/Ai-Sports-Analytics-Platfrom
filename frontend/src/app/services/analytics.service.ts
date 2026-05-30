import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { AnalyticsRepository } from '../repositories/analytics.repository';
import { AnalyticsData } from '../models/analytics.model';

@Injectable({
    providedIn: 'root'
})
export class AnalyticsService {
    constructor(private analyticsRepository: AnalyticsRepository) { }

    getAnalyticsData(): Observable<AnalyticsData> {
        return this.analyticsRepository.getAnalytics();
    }

    calculateTrend(current: number, previous: number): number {
        if (previous === 0) return 0;
        return ((current - previous) / previous) * 100;
    }

    formatMetricValue(value: number, unit?: string): string {
        const formatted = value.toFixed(1);
        return unit ? `${formatted}${unit}` : formatted;
    }
}
