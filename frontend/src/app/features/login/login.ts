import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { SettingsApiService } from '../../services/settings-api.service';
import { ThemeMode, ThemeService } from '../../services/theme.service';

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  username = '';
  password = '';
  isLoading = false;
  errorMessage = '';
  theme$: Observable<ThemeMode>;

  constructor(
    private authService: AuthService,
    private settingsApi: SettingsApiService,
    private themeService: ThemeService,
    private router: Router
  ) {
    this.theme$ = this.themeService.theme$;
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  onSubmit(): void {
    if (!this.username || !this.password) {
      this.errorMessage = 'Please enter both username and password';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.authService.login({ username: this.username, password: this.password }).subscribe({
      next: (response) => {
        if (response.user.role === 'Admin') {
          this.router.navigate(['/admin/dashboard']);
          return;
        }

        this.settingsApi.getSettings().subscribe({
          next: (settings) => this.router.navigate([settings.startPage || '/dashboard']),
          error: () => this.router.navigate(['/dashboard'])
        });
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Invalid credentials. Please try again.';
        this.isLoading = false;
      },
      complete: () => {
        this.isLoading = false;
      }
    });
  }

  goToRegister(): void {
    this.router.navigate(['/register']);
  }
}
