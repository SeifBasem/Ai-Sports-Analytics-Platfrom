import { Component, OnInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';
import { AuthService } from './services/auth.service';
import { User } from './models/user.model';
import { NavigationService } from './services/navigation.service';
import { ThemeMode, ThemeService } from './services/theme.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  standalone: false,
  styleUrl: './app.scss'
})
export class App implements OnInit {
  title = 'Goalithm';
  isAuthenticated$: Observable<boolean>;
  currentUser$: Observable<User | null>;
  sidebarOpen$: Observable<boolean>;
  theme$: Observable<ThemeMode>;
  showLayout = false;

  constructor(
    private authService: AuthService,
    private navigationService: NavigationService,
    private themeService: ThemeService,
    private router: Router
  ) {
    this.isAuthenticated$ = this.authService.isAuthenticated$;
    this.currentUser$ = this.authService.currentUser$;
    this.sidebarOpen$ = this.navigationService.sidebarOpen$;
    this.theme$ = this.themeService.theme$;
  }

  ngOnInit(): void {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: any) => {
      this.showLayout = this.shouldShowUserLayout(event.urlAfterRedirects ?? event.url);
    });

    this.showLayout = this.shouldShowUserLayout(this.router.url);
  }

  toggleSidebar(): void {
    this.navigationService.toggleSidebar();
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  getUserInitials(user: User | null): string {
    const value = user?.fullName || user?.username || 'User';
    return value
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part[0])
      .join('')
      .toUpperCase();
  }

  private shouldShowUserLayout(url: string): boolean {
    return !url.includes('/login') && !url.includes('/register') && !url.startsWith('/admin');
  }
}
