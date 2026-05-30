import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';
import { adminGuard } from './guards/admin.guard';
import { Login } from './features/login/login';
import { Register } from './features/register/register';
import { Dashboard } from './features/dashboard/dashboard';
import { VideoUpload } from './features/video-upload/video-upload';
import { BallAction } from './features/ball-action/ball-action';
import { Analytics } from './features/analytics/analytics';
import { AnalyticsHistory } from './features/analytics-history/analytics-history';
import { Heatmap } from './features/heatmap/heatmap';
import { Settings } from './features/settings/settings';
import { Detection } from './features/detection/detection';
import { ActionRecognition } from './features/action-recognition/action-recognition';
import { PlayerActionAnalytics } from './features/player-action-analytics/player-action-analytics';
import { AdminLayoutComponent } from './shared/admin-layout/admin-layout';
import { AdminDashboard } from './features/admin-dashboard/admin-dashboard';
import { UsersPage } from './features/users/users';
import { VideosPage } from './features/videos/videos';
import { AnalysisRequestsPage } from './features/analysis-requests/analysis-requests';
import { AnalysisResultsPage } from './features/analysis-results/analysis-results';

const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: Login },
  { path: 'register', component: Register },
  { path: 'dashboard', component: Dashboard, canActivate: [authGuard] },
  { path: 'upload', component: VideoUpload, canActivate: [authGuard] },
  { path: 'ball-action', component: BallAction, canActivate: [authGuard] },
  { path: 'analytics', component: Analytics, canActivate: [authGuard] },
  { path: 'analytics-history', component: AnalyticsHistory, canActivate: [authGuard] },
  { path: 'heatmap', component: Heatmap, canActivate: [authGuard] },
  { path: 'settings', component: Settings, canActivate: [authGuard] },
  { path: 'detection', component: Detection, canActivate: [authGuard] },
  { path: 'action-recognition', component: ActionRecognition, canActivate: [authGuard] },
  { path: 'player-action-analytics', component: PlayerActionAnalytics, canActivate: [authGuard] },
  {
    path: 'admin',
    component: AdminLayoutComponent,
    canActivate: [adminGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', component: AdminDashboard },
      { path: 'users', component: UsersPage },
      { path: 'videos', component: VideosPage },
      { path: 'analysis-requests', component: AnalysisRequestsPage },
      { path: 'analysis-results', component: AnalysisResultsPage }
    ]
  },
  { path: '**', redirectTo: '/login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
