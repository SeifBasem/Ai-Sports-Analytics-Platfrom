export type UserRole = 'Admin' | 'User';

export interface User {
    id: string;
    username: string;
    email: string;
    fullName: string;
    role: UserRole;
    isActive?: boolean;
    createdAt?: string;
    avatar?: string;
}

export interface LoginCredentials {
    username: string;
    password: string;
}

export interface AuthResponse {
    success: boolean;
    message: string;
    user: User;
    accessToken: string;
    refreshToken: string;
    expiresAt: string;
}

export interface RegisterData {
    username: string;
    email: string;
    password: string;
    fullName: string;
}
