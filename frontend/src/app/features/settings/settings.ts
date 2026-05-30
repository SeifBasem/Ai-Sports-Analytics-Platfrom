import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { SettingsApiService, UpdateUserSettingsRequest } from '../../services/settings-api.service';
import { ThemeMode, ThemeService } from '../../services/theme.service';
import { User } from '../../models/user.model';

interface UserSettings {
  fullName: string;
  email: string;
  username: string;
  themeMode: ThemeMode;
  startPage: string;
  confidenceThreshold: number;
}

@Component({
  selector: 'app-settings',
  standalone: false,
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
})
export class Settings implements OnInit {
  currentUser: User | null = null;
  currentTheme: ThemeMode = 'dark';
  saved = false;
  loading = false;
  saving = false;
  error = '';
  updatedAt = '';

  settings: UserSettings = {
    fullName: '',
    email: '',
    username: '',
    themeMode: 'dark',
    startPage: '/dashboard',
    confidenceThreshold: 80
  };

  readonly startPageOptions = [
    { value: '/dashboard', label: 'Dashboard' },
    { value: '/upload', label: 'Player Tracking' },
    { value: '/heatmap', label: 'Movement Heatmaps' },
    { value: '/ball-action', label: 'Match Event Spotting' },
    { value: '/analytics', label: 'Match Event Analytics' },
    { value: '/action-recognition', label: 'Player Action Detection' },
    { value: '/player-action-analytics', label: 'Player Review' },
    { value: '/analytics-history', label: 'Analysis History' }
  ];

  constructor(
    private authService: AuthService,
    private settingsApi: SettingsApiService,
    private themeService: ThemeService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.currentTheme = this.themeService.currentTheme;
    this.themeService.theme$.subscribe((theme) => {
      this.currentTheme = theme;
    });

    this.currentUser = this.authService.getCurrentUser();
    this.loadSettings();
  }

  setTheme(theme: ThemeMode): void {
    this.settings.themeMode = theme;
    this.themeService.setTheme(theme);
  }

  saveSettings(): void {
    this.saving = true;
    this.error = '';

    this.settingsApi.updateSettings(this.toRequest()).subscribe({
      next: (settings) => {
        this.applySettings(settings);
        this.authService.updateStoredUser({
          fullName: settings.fullName,
          email: settings.email
        });
        this.saved = true;
        this.saving = false;
        window.setTimeout(() => {
          this.saved = false;
        }, 2200);
      },
      error: (err) => {
        this.saving = false;
        this.error = err?.error?.message || 'Could not save settings.';
      }
    });
  }

  resetSettings(): void {
    this.loadSettings();
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  get initials(): string {
    const source = this.settings.fullName || this.settings.username || 'User';
    return source
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase();
  }

  private loadSettings(): void {
    this.loading = true;
    this.error = '';

    this.settingsApi.getSettings().subscribe({
      next: (settings) => {
        this.applySettings(settings);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'Could not load account settings.';
        this.settings = {
          ...this.settings,
          fullName: this.currentUser?.fullName || 'User',
          email: this.currentUser?.email || '',
          username: this.currentUser?.username || 'user',
          themeMode: this.currentTheme,
          startPage: '/dashboard'
        };
      }
    });
  }

  private applySettings(settings: UserSettings & { updatedAt?: string }): void {
    this.settings = {
      fullName: settings.fullName,
      email: settings.email,
      username: settings.username,
      themeMode: settings.themeMode,
      startPage: settings.startPage,
      confidenceThreshold: settings.confidenceThreshold,
    };
    this.updatedAt = settings.updatedAt ?? '';
    this.setTheme(settings.themeMode);
  }

  private toRequest(): UpdateUserSettingsRequest {
    return {
      fullName: this.settings.fullName,
      email: this.settings.email,
      themeMode: this.settings.themeMode,
      startPage: this.settings.startPage,
      confidenceThreshold: this.settings.confidenceThreshold
    };
  }
}
