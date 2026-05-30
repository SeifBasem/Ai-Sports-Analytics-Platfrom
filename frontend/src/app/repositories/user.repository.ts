import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthResponse, LoginCredentials, RegisterData, User } from '../models/user.model';

@Injectable({
    providedIn: 'root'
})
export class UserRepository {
    private apiUrl = `${environment.apiBaseUrl}/auth`;

    constructor(private http: HttpClient) {}

    login(credentials: LoginCredentials): Observable<AuthResponse> {
        return this.http.post<AuthResponse>(`${this.apiUrl}/login`, credentials);
    }

    register(data: RegisterData): Observable<AuthResponse> {
        return this.http.post<AuthResponse>(`${this.apiUrl}/register`, data);
    }

    refreshToken(refreshToken: string): Observable<AuthResponse> {
        return this.http.post<AuthResponse>(`${this.apiUrl}/refresh`, { refreshToken });
    }

    logout(refreshToken?: string): Observable<{ success: boolean; message: string }> {
        return this.http.post<{ success: boolean; message: string }>(`${this.apiUrl}/logout`, { refreshToken });
    }

    me(): Observable<User> {
        return this.http.get<User>(`${this.apiUrl}/me`);
    }

    getCurrentUser(): Observable<User | null> {
        return this.me();
    }
}
