import { Injectable } from '@angular/core';
import {
    HttpErrorResponse,
    HttpEvent,
    HttpHandler,
    HttpInterceptor,
    HttpRequest
} from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
    constructor(
        private authService: AuthService,
        private router: Router
    ) {}

    intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
        const authRequest = this.withAccessToken(request);

        return next.handle(authRequest).pipe(
            catchError((error: HttpErrorResponse) => {
                if (error.status !== 401 || this.isAuthRefreshRequest(request)) {
                    return throwError(() => error);
                }

                return this.authService.refreshSession().pipe(
                    switchMap((response) => next.handle(this.withToken(request, response.accessToken))),
                    catchError((refreshError) => {
                        this.authService.clearSession();
                        this.router.navigate(['/login']);
                        return throwError(() => refreshError);
                    })
                );
            })
        );
    }

    private withAccessToken(request: HttpRequest<unknown>): HttpRequest<unknown> {
        const token = this.authService.getAccessToken();
        return token ? this.withToken(request, token) : request;
    }

    private withToken(request: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
        return request.clone({
            setHeaders: {
                Authorization: `Bearer ${token}`
            }
        });
    }

    private isAuthRefreshRequest(request: HttpRequest<unknown>): boolean {
        return request.url.includes('/auth/login') ||
            request.url.includes('/auth/register') ||
            request.url.includes('/auth/refresh');
    }
}
