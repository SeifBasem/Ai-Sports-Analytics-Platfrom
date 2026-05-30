import { NgModule, provideBrowserGlobalErrorListeners } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HTTP_INTERCEPTORS, HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import {
  Activity,
  Ban,
  Braces,
  BrainCircuit,
  CheckCircle2,
  CircleDot,
  ClipboardList,
  Clock3,
  Download,
  Eye,
  FileText,
  Info,
  LayoutDashboard,
  LogOut,
  LucideAngularModule,
  Menu,
  Moon,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  ShieldCheck,
  Sun,
  Timer,
  Trash2,
  TriangleAlert,
  Upload,
  UserRound,
  Users,
  Video,
  X
} from 'lucide-angular';

import { AppRoutingModule } from './app-routing-module';
import { App } from './app';
import { Login } from './features/login/login';
import { Register } from './features/register/register';
import { Dashboard } from './features/dashboard/dashboard';
import { VideoUpload } from './features/video-upload/video-upload';
import { BallAction } from './features/ball-action/ball-action';
import { Analytics } from './features/analytics/analytics';
import { AnalyticsHistory } from './features/analytics-history/analytics-history';
import { Heatmap } from './features/heatmap/heatmap';
import { Settings } from './features/settings/settings';
import { Sidebar } from './shared/sidebar/sidebar';
import { Detection } from './features/detection/detection';
import { ActionRecognition } from './features/action-recognition/action-recognition';
import { AdminLayoutComponent } from './shared/admin-layout/admin-layout';
import { AdminSidebarComponent } from './shared/admin-sidebar/admin-sidebar';
import { StatCardComponent } from './shared/stat-card/stat-card';
import { StatusBadgeComponent } from './shared/status-badge/status-badge';
import { DataTableComponent } from './shared/data-table/data-table';
import { ModalComponent } from './shared/modal/modal';
import { AdminDashboard } from './features/admin-dashboard/admin-dashboard';
import { UsersPage } from './features/users/users';
import { VideosPage } from './features/videos/videos';
import { AnalysisRequestsPage } from './features/analysis-requests/analysis-requests';
import { AnalysisResultsPage } from './features/analysis-results/analysis-results';
import { AuthInterceptor } from './interceptors/auth.interceptor';
import { PlayerActionAnalytics } from './features/player-action-analytics/player-action-analytics';

@NgModule({
  declarations: [
    App,
    Login,
    Register,
    Dashboard,
    VideoUpload,
    BallAction,
    Analytics,
    AnalyticsHistory,
    Heatmap,
    Settings,
    Sidebar,
    Detection,
    ActionRecognition,
    AdminLayoutComponent,
    AdminSidebarComponent,
    StatCardComponent,
    StatusBadgeComponent,
    DataTableComponent,
    ModalComponent,
    AdminDashboard,
    UsersPage,
    VideosPage,
    AnalysisRequestsPage,
    AnalysisResultsPage,
    PlayerActionAnalytics
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    FormsModule,
    HttpClientModule,
    CommonModule,
    LucideAngularModule.pick({
      Activity,
      Ban,
      Braces,
      BrainCircuit,
      CheckCircle2,
      CircleDot,
      ClipboardList,
      Clock3,
      Download,
      Eye,
      FileText,
      Info,
      LayoutDashboard,
      LogOut,
      Menu,
      Moon,
      Pencil,
      Play,
      Plus,
      RotateCcw,
      ShieldCheck,
      Sun,
      Timer,
      Trash2,
      TriangleAlert,
      Upload,
      UserRound,
      Users,
      Video,
      X
    })
  ],
  providers: [
    provideBrowserGlobalErrorListeners(),
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }
  ],
  bootstrap: [App]
})
export class AppModule { }
