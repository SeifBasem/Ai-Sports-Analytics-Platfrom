import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-modal',
  standalone: false,
  templateUrl: './modal.html',
  styleUrl: './modal.scss'
})
export class ModalComponent {
  @Input() isOpen = false;
  @Input() title = '';
  @Input() size: 'md' | 'lg' | 'xl' = 'md';

  @Output() closed = new EventEmitter<void>();

  close(): void {
    this.closed.emit();
  }

  get panelSizeClasses(): string {
    switch (this.size) {
      case 'xl':
        return 'max-w-4xl';
      case 'lg':
        return 'max-w-2xl';
      case 'md':
      default:
        return 'max-w-lg';
    }
  }
}
