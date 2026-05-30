import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { JobStatisticApiResponse, PagedResponse, ProcessingJobApiResponse } from '../models/api.model';

@Injectable({
  providedIn: 'root'
})
export class JobStatisticsApiService {
  private readonly apiUrl = `${environment.apiBaseUrl}/job-statistics`;
  private readonly jobsUrl = `${environment.apiBaseUrl}/processing-jobs`;

  constructor(private http: HttpClient) {}

  getLatestByType<T>(statType: string): Observable<T | null> {
    const params = new HttpParams()
      .set('page', '1')
      .set('pageSize', '1')
      .set('statType', statType);

    return this.http.get<PagedResponse<JobStatisticApiResponse>>(this.apiUrl, { params }).pipe(
      map((page) => {
        const row = page.items[0];
        return row ? this.parseJson<T>(row.statsJson) : null;
      })
    );
  }

  getLatestByJobAndType<T>(processingJobId: string, statType: string): Observable<T | null> {
    const params = new HttpParams()
      .set('page', '1')
      .set('pageSize', '1')
      .set('processingJobId', processingJobId)
      .set('statType', statType);

    return this.http.get<PagedResponse<JobStatisticApiResponse>>(this.apiUrl, { params }).pipe(
      map((page) => {
        const row = page.items[0];
        return row ? this.parseJson<T>(row.statsJson) : null;
      })
    );
  }

  getAllByType<T>(statType: string, pageSize = 100): Observable<T[]> {
    const params = new HttpParams()
      .set('page', '1')
      .set('pageSize', String(pageSize))
      .set('statType', statType);

    return this.http.get<PagedResponse<JobStatisticApiResponse>>(this.apiUrl, { params }).pipe(
      map((page) => page.items
        .map((row) => this.parseJson<T>(row.statsJson))
        .filter((row): row is T => row !== null))
    );
  }

  getCompletedJobs(jobType?: string, pageSize = 100): Observable<ProcessingJobApiResponse[]> {
    let params = new HttpParams()
      .set('page', '1')
      .set('pageSize', String(pageSize))
      .set('status', 'Completed');

    if (jobType) {
      params = params.set('jobType', jobType);
    }

    return this.http.get<PagedResponse<ProcessingJobApiResponse>>(this.jobsUrl, { params }).pipe(
      map((page) => page.items)
    );
  }

  private parseJson<T>(value: string): T | null {
    try {
      return JSON.parse(value) as T;
    } catch {
      return null;
    }
  }
}
