import { Component, EventEmitter, Input, Output } from '@angular/core';

export type DataTableCell = string | number | boolean | null | undefined;
export type DataTableRow = Record<string, DataTableCell>;
export type ColumnType = 'text' | 'status' | 'longText';
export type ActionVariant = 'primary' | 'secondary' | 'danger' | 'warning';

export interface DataTableColumn {
  key: string;
  label: string;
  type?: ColumnType;
}

export interface DataTableAction {
  id: string;
  label: string;
  icon: string;
  variant?: ActionVariant;
  visibleForStatus?: string[];
}

export interface DataTableActionEvent {
  actionId: string;
  row: DataTableRow;
}

@Component({
  selector: 'app-data-table',
  standalone: false,
  templateUrl: './data-table.html',
  styleUrl: './data-table.scss'
})
export class DataTableComponent {
  @Input() columns: DataTableColumn[] = [];
  @Input() rows: DataTableRow[] = [];
  @Input() actions: DataTableAction[] = [];
  @Input() emptyMessage = 'No records found.';
  @Input() statusKey = 'status';

  @Output() actionSelected = new EventEmitter<DataTableActionEvent>();

  getCellText(row: DataTableRow, key: string): string {
    const value = row[key];

    if (value === null || value === undefined || value === '') {
      return '-';
    }

    return String(value);
  }

  isActionVisible(action: DataTableAction, row: DataTableRow): boolean {
    if (!action.visibleForStatus || action.visibleForStatus.length === 0) {
      return true;
    }

    return action.visibleForStatus.includes(this.getCellText(row, this.statusKey));
  }

  selectAction(actionId: string, row: DataTableRow): void {
    this.actionSelected.emit({ actionId, row });
  }

  actionClasses(variant: ActionVariant | undefined): string {
    switch (variant) {
      case 'primary':
        return 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300 hover:border-cyan-400/50 hover:bg-cyan-500/20';
      case 'danger':
        return 'border-red-500/30 bg-red-500/10 text-red-300 hover:border-red-400/50 hover:bg-red-500/20';
      case 'warning':
        return 'border-amber-500/30 bg-amber-500/10 text-amber-300 hover:border-amber-400/50 hover:bg-amber-500/20';
      case 'secondary':
      default:
        return 'border-gray-700/70 bg-gray-800/40 text-gray-300 hover:border-gray-600 hover:bg-gray-800/70 hover:text-white';
    }
  }

  trackByIndex(index: number): number {
    return index;
  }
}
