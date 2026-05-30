import { Component, OnInit } from '@angular/core';
import { AdminUser } from '../../models/admin.model';
import { AdminApiService } from '../../services/admin-api.service';
import { DataTableAction, DataTableActionEvent, DataTableColumn, DataTableRow } from '../../shared/data-table/data-table';

@Component({
  selector: 'app-users-page',
  standalone: false,
  templateUrl: './users.html',
  styleUrl: './users.scss'
})
export class UsersPage implements OnInit {
  users: AdminUser[] = [];
  selectedUser: AdminUser | null = null;
  editingUser: AdminUser | null = null;
  notice = '';

  columns: DataTableColumn[] = [
    { key: 'id', label: 'Id' },
    { key: 'fullName', label: 'Full Name' },
    { key: 'email', label: 'Email' },
    { key: 'role', label: 'Role', type: 'status' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'createdAt', label: 'Created At' }
  ];

  actions: DataTableAction[] = [
    { id: 'view', label: 'View', icon: 'eye', variant: 'secondary' },
    { id: 'edit', label: 'Edit', icon: 'pencil', variant: 'primary' },
    { id: 'deactivate', label: 'Deactivate', icon: 'ban', variant: 'warning', visibleForStatus: ['Active'] },
    { id: 'delete', label: 'Delete', icon: 'trash-2', variant: 'danger' }
  ];

  constructor(private adminData: AdminApiService) { }

  ngOnInit(): void {
    this.loadUsers();
  }

  get rows(): DataTableRow[] {
    return this.users.map((user) => ({
      id: user.id,
      fullName: user.fullName,
      email: user.email,
      role: user.role,
      status: user.status,
      createdAt: user.createdAt
    }));
  }

  handleAction(event: DataTableActionEvent): void {
    const id = String(event.row['id']);
    const user = this.users.find((item) => item.id === id);

    if (!user) {
      return;
    }

    if (event.actionId === 'view') {
      this.selectedUser = user;
    }

    if (event.actionId === 'edit') {
      this.editingUser = { ...user };
    }

    if (event.actionId === 'deactivate') {
      this.adminData.deactivateUser(id).subscribe(() => {
        this.notice = `${user.fullName} has been deactivated.`;
        this.loadUsers();
      });
    }

    if (event.actionId === 'delete') {
      this.adminData.deleteUser(id).subscribe(() => {
        this.notice = `${user.fullName} has been deactivated.`;
        this.loadUsers();
      });
    }
  }

  saveUser(): void {
    if (!this.editingUser) {
      return;
    }

    this.adminData.updateUser(this.editingUser).subscribe((updatedUser) => {
      this.notice = `${updatedUser.fullName} has been updated.`;
      this.editingUser = null;
      this.loadUsers();
    });
  }

  closeNotice(): void {
    this.notice = '';
  }

  private loadUsers(): void {
    this.adminData.getUsers().subscribe((users) => {
      this.users = users;
    });
  }
}
