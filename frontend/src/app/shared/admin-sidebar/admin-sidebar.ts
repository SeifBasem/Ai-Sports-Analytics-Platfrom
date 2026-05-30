import { Component, OnDestroy, OnInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Observable, Subscription, filter } from 'rxjs';
import { NavigationService } from '../../services/navigation.service';

interface AdminMenuItem {
  id: string;
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-admin-sidebar',
  standalone: false,
  templateUrl: './admin-sidebar.html',
  styleUrl: './admin-sidebar.scss'
})
export class AdminSidebarComponent implements OnInit, OnDestroy {
  menuItems: AdminMenuItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard', route: '/admin/dashboard' },
    { id: 'users', label: 'Users', icon: 'users', route: '/admin/users' },
    { id: 'videos', label: 'Videos', icon: 'video', route: '/admin/videos' },
    { id: 'analysis-requests', label: 'Analysis Requests', icon: 'clipboard-list', route: '/admin/analysis-requests' },
    { id: 'analysis-results', label: 'Analysis Results', icon: 'brain-circuit', route: '/admin/analysis-results' }
  ];

  sidebarOpen$: Observable<boolean>;
  currentRoute = '';
  private routerSubscription?: Subscription;

  constructor(
    private navigationService: NavigationService,
    private router: Router
  ) {
    this.sidebarOpen$ = this.navigationService.sidebarOpen$;
  }

  ngOnInit(): void {
    this.currentRoute = this.router.url;
    this.routerSubscription = this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event) => {
        this.currentRoute = (event as NavigationEnd).urlAfterRedirects;
      });
  }

  ngOnDestroy(): void {
    this.routerSubscription?.unsubscribe();
  }

  navigate(route: string): void {
    this.router.navigate([route]);
    this.currentRoute = route;

    if (window.innerWidth < 1024) {
      this.navigationService.setSidebarOpen(false);
    }
  }

  closeSidebar(): void {
    this.navigationService.setSidebarOpen(false);
  }

  isActive(route: string): boolean {
    return this.currentRoute === route;
  }
}
