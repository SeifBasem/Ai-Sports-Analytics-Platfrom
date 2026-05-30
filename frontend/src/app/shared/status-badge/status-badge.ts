import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-status-badge',
  standalone: false,
  templateUrl: './status-badge.html',
  styleUrl: './status-badge.scss'
})
export class StatusBadgeComponent {
  @Input() status = '';

  get normalizedStatus(): string {
    return this.status.toLowerCase().replace(/\s+/g, '-');
  }

  get iconName(): string {
    switch (this.normalizedStatus) {
      case 'active':
      case 'completed':
      case 'ready':
        return 'check-circle-2';
      case 'processing':
        return 'timer';
      case 'pending':
      case 'draft':
      case 'uploaded':
        return 'circle-dot';
      case 'failed':
        return 'triangle-alert';
      case 'inactive':
      case 'archived':
        return 'ban';
      case 'admin':
        return 'shield-check';
      case 'user':
        return 'user-round';
      default:
        return 'info';
    }
  }

  get badgeClasses(): string {
    switch (this.normalizedStatus) {
      case 'active':
      case 'completed':
      case 'ready':
        return 'border-green-500/30 bg-green-500/15 text-green-300';
      case 'processing':
        return 'border-blue-500/30 bg-blue-500/15 text-blue-300';
      case 'pending':
      case 'draft':
        return 'border-amber-500/30 bg-amber-500/15 text-amber-300';
      case 'uploaded':
        return 'border-cyan-500/30 bg-cyan-500/15 text-cyan-300';
      case 'failed':
        return 'border-red-500/30 bg-red-500/15 text-red-300';
      case 'inactive':
      case 'archived':
        return 'border-gray-600/50 bg-gray-700/35 text-gray-300';
      case 'admin':
        return 'border-purple-500/30 bg-purple-500/15 text-purple-300';
      case 'user':
        return 'border-cyan-500/30 bg-cyan-500/15 text-cyan-300';
      default:
        return 'border-gray-700 bg-gray-800/50 text-gray-300';
    }
  }
}
