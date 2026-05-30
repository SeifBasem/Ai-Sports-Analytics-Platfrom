import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-stat-card',
  standalone: false,
  templateUrl: './stat-card.html',
  styleUrl: './stat-card.scss'
})
export class StatCardComponent {
  @Input() label = '';
  @Input() value: string | number = '';
  @Input() icon = 'activity';
  @Input() accent: 'teal' | 'indigo' | 'amber' | 'emerald' | 'rose' | 'sky' = 'teal';

  get accentClasses(): string {
    const classes = {
      teal: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      indigo: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      emerald: 'bg-green-500/10 text-green-400 border-green-500/20',
      rose: 'bg-red-500/10 text-red-400 border-red-500/20',
      sky: 'bg-sky-500/10 text-sky-400 border-sky-500/20'
    };

    return classes[this.accent];
  }
}
