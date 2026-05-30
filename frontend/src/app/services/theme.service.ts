import { DOCUMENT } from '@angular/common';
import { Inject, Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export type ThemeMode = 'dark' | 'light';

@Injectable({
    providedIn: 'root'
})
export class ThemeService {
    private readonly storageKey = 'ai-sports-theme';
    private themeSubject = new BehaviorSubject<ThemeMode>(this.getInitialTheme());
    theme$ = this.themeSubject.asObservable();

    constructor(@Inject(DOCUMENT) private document: Document) {
        this.applyTheme(this.themeSubject.value);
    }

    get currentTheme(): ThemeMode {
        return this.themeSubject.value;
    }

    toggleTheme(): void {
        this.setTheme(this.currentTheme === 'dark' ? 'light' : 'dark');
    }

    setTheme(theme: ThemeMode): void {
        this.themeSubject.next(theme);
        localStorage.setItem(this.storageKey, theme);
        this.applyTheme(theme);
    }

    private getInitialTheme(): ThemeMode {
        const savedTheme = localStorage.getItem(this.storageKey);
        return savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : 'dark';
    }

    private applyTheme(theme: ThemeMode): void {
        const root = this.document.documentElement;
        root.classList.toggle('light-theme', theme === 'light');
        root.classList.toggle('dark-theme', theme === 'dark');
        root.style.colorScheme = theme;
    }
}
