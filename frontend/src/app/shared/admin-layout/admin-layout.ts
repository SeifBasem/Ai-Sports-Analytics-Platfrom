import { Component, OnDestroy, OnInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Observable, Subscription, filter } from 'rxjs';
import { NavigationService } from '../../services/navigation.service';
import { ThemeMode, ThemeService } from '../../services/theme.service';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models/user.model';

@Component({
  selector: 'app-admin-layout',
  standalone: false,
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss'
})
export class AdminLayoutComponent implements OnInit, OnDestroy {
  sidebarOpen$: Observable<boolean>;
  theme$: Observable<ThemeMode>;
  currentUser$: Observable<User | null>;
  pageTitle = 'Dashboard';
  private routerSubscription?: Subscription;

  private readonly titles: Record<string, string> = {
    '/admin/dashboard': 'Dashboard',
    '/admin/users': 'Users',
    '/admin/videos': 'Videos',
    '/admin/analysis-requests': 'Analysis Requests',
    '/admin/analysis-results': 'Analysis Results'
  };

  constructor(
    private navigationService: NavigationService,
    private themeService: ThemeService,
    private authService: AuthService,
    private router: Router
  ) {
    this.sidebarOpen$ = this.navigationService.sidebarOpen$;
    this.theme$ = this.themeService.theme$;
    this.currentUser$ = this.authService.currentUser$;
  }

  ngOnInit(): void {
    this.setTitle(this.router.url);
    this.routerSubscription = this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event) => this.setTitle((event as NavigationEnd).urlAfterRedirects));
  }

  ngOnDestroy(): void {
    this.routerSubscription?.unsubscribe();
  }

  toggleSidebar(): void {
    this.navigationService.toggleSidebar();
  }

  closeSidebar(): void {
    this.navigationService.setSidebarOpen(false);
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  getUserInitials(user: User | null): string {
    const value = user?.fullName || user?.username || 'Admin';
    return value
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part[0])
      .join('')
      .toUpperCase();
  }

  private setTitle(url: string): void {
    const path = url.split('?')[0] ?? '/dashboard';
    this.pageTitle = this.titles[path] ?? 'Dashboard';
  }
}
