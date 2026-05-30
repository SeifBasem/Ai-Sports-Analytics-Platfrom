import { Component, OnDestroy, OnInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter, Observable, Subscription } from 'rxjs';
import { NavigationService } from '../../services/navigation.service';

export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: false,
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss'
})
export class Sidebar implements OnInit, OnDestroy {
  menuItems: MenuItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: 'home', route: '/dashboard' },
    { id: 'upload', label: 'Player Tracking', icon: 'upload', route: '/upload' },
    { id: 'heatmap', label: 'Movement Heatmaps', icon: 'flame', route: '/heatmap' },
    { id: 'ball-action', label: 'Match Event Spotting', icon: 'play', route: '/ball-action' },
    { id: 'analytics', label: 'Match Event Analytics', icon: 'bar-chart', route: '/analytics' },
    { id: 'action-recognition', label: 'Player Action Detection', icon: 'cycle', route: '/action-recognition' },
    { id: 'player-action-analytics', label: 'Player Review', icon: 'bar-chart', route: '/player-action-analytics' },
    { id: 'analytics-history', label: 'Analysis History', icon: 'clock', route: '/analytics-history' },
    { id: 'settings', label: 'Settings', icon: 'settings', route: '/settings' }
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
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event) => {
        this.currentRoute = event.urlAfterRedirects.split('?')[0];
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
    return this.currentRoute.split('?')[0] === route;
  }
}
