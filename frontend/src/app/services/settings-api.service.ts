import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ThemeMode } from './theme.service';

export interface UserSettingsResponse {
  fullName: string;
  email: string;
  username: string;
  themeMode: ThemeMode;
  startPage: string;
  confidenceThreshold: number;
  updatedAt: string;
}

export interface UpdateUserSettingsRequest {
  fullName: string;
  email: string;
  themeMode: ThemeMode;
  startPage: string;
  confidenceThreshold: number;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsApiService {
  private readonly apiUrl = `${environment.apiBaseUrl}/settings`;

  constructor(private http: HttpClient) {}

  getSettings(): Observable<UserSettingsResponse> {
    return this.http.get<UserSettingsResponse>(this.apiUrl);
  }

  updateSettings(request: UpdateUserSettingsRequest): Observable<UserSettingsResponse> {
    return this.http.put<UserSettingsResponse>(this.apiUrl, request);
  }
}
