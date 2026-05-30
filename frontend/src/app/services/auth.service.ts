import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, finalize, shareReplay, tap, throwError } from 'rxjs';
import { UserRepository } from '../repositories/user.repository';
import { AuthResponse, LoginCredentials, RegisterData, User, UserRole } from '../models/user.model';

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private readonly userKey = 'currentUser';
    private readonly accessTokenKey = 'accessToken';
    private readonly refreshTokenKey = 'refreshToken';
    private readonly expiresAtKey = 'tokenExpiresAt';

    private currentUserSubject = new BehaviorSubject<User | null>(null);
    public currentUser$ = this.currentUserSubject.asObservable();

    private isAuthenticatedSubject = new BehaviorSubject<boolean>(false);
    public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();
    private refreshInFlight$?: Observable<AuthResponse>;

    constructor(private userRepository: UserRepository) {
        this.loadStoredUser();
    }

    private loadStoredUser(): void {
        const storedUser = localStorage.getItem(this.userKey);
        const storedAccessToken = localStorage.getItem(this.accessTokenKey);
        const storedRefreshToken = localStorage.getItem(this.refreshTokenKey);

        if (storedUser && (storedAccessToken || storedRefreshToken)) {
            this.currentUserSubject.next(JSON.parse(storedUser));
            this.isAuthenticatedSubject.next(true);
        }
    }

    login(credentials: LoginCredentials): Observable<AuthResponse> {
        return this.userRepository.login(credentials).pipe(
            tap(response => this.storeSession(response))
        );
    }

    register(data: RegisterData): Observable<AuthResponse> {
        return this.userRepository.register(data).pipe(
            tap(response => this.storeSession(response))
        );
    }

    logout(): void {
        const refreshToken = this.getRefreshToken();
        this.userRepository.logout(refreshToken ?? undefined).subscribe({
            next: () => this.clearSession(),
            error: () => this.clearSession()
        });
    }

    clearSession(): void {
        localStorage.removeItem(this.userKey);
        localStorage.removeItem(this.accessTokenKey);
        localStorage.removeItem(this.refreshTokenKey);
        localStorage.removeItem(this.expiresAtKey);
        localStorage.removeItem('authToken');
        this.currentUserSubject.next(null);
        this.isAuthenticatedSubject.next(false);
    }

    getCurrentUser(): User | null {
        return this.currentUserSubject.value;
    }

    updateStoredUser(changes: Partial<User>): void {
        const currentUser = this.currentUserSubject.value;
        if (!currentUser) return;

        const nextUser = { ...currentUser, ...changes };
        localStorage.setItem(this.userKey, JSON.stringify(nextUser));
        this.currentUserSubject.next(nextUser);
    }

    isAuthenticated(): boolean {
        return this.isAuthenticatedSubject.value && !!this.currentUserSubject.value;
    }

    isAdmin(): boolean {
        return this.currentUserSubject.value?.role === 'Admin';
    }

    hasRole(roles: UserRole[]): boolean {
        const role = this.currentUserSubject.value?.role;
        return !!role && roles.includes(role);
    }

    getAccessToken(): string | null {
        return localStorage.getItem(this.accessTokenKey);
    }

    getRefreshToken(): string | null {
        return localStorage.getItem(this.refreshTokenKey);
    }

    refreshSession(): Observable<AuthResponse> {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            this.clearSession();
            return throwError(() => new Error('No refresh token available.'));
        }

        if (!this.refreshInFlight$) {
            this.refreshInFlight$ = this.userRepository.refreshToken(refreshToken).pipe(
                tap(response => this.storeSession(response)),
                finalize(() => {
                    this.refreshInFlight$ = undefined;
                }),
                shareReplay(1)
            );
        }

        return this.refreshInFlight$;
    }

    private storeSession(response: AuthResponse): void {
        localStorage.setItem(this.userKey, JSON.stringify(response.user));
        localStorage.setItem(this.accessTokenKey, response.accessToken);
        localStorage.setItem(this.refreshTokenKey, response.refreshToken);
        localStorage.setItem(this.expiresAtKey, response.expiresAt);
        localStorage.removeItem('authToken');
        this.currentUserSubject.next(response.user);
        this.isAuthenticatedSubject.next(true);
    }
}
