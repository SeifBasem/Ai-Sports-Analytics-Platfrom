import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable } from 'rxjs';

export type Page = 'dashboard' | 'upload' | 'analytics' | 'heatmap' | 'settings' | 'admin';

@Injectable({
    providedIn: 'root'
})
export class NavigationService {
    private currentPageSubject = new BehaviorSubject<Page>('dashboard');
    public currentPage$ = this.currentPageSubject.asObservable();

    private sidebarOpenSubject = new BehaviorSubject<boolean>(true);
    public sidebarOpen$ = this.sidebarOpenSubject.asObservable();

    constructor(private router: Router) { }

    navigateTo(page: Page): void {
        this.currentPageSubject.next(page);
        this.router.navigate([page]);
    }

    toggleSidebar(): void {
        this.sidebarOpenSubject.next(!this.sidebarOpenSubject.value);
    }

    setSidebarOpen(isOpen: boolean): void {
        this.sidebarOpenSubject.next(isOpen);
    }

    getCurrentPage(): Page {
        return this.currentPageSubject.value;
    }
}
