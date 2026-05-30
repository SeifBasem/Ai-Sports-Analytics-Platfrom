export type AdminRole = 'Admin' | 'User';
export type AccountStatus = 'Active' | 'Inactive';
export type VideoStatus = 'Uploaded' | 'Processing' | 'Completed' | 'Failed';
export type AnalysisStatus = 'Pending' | 'Processing' | 'Completed' | 'Failed';
export type ReportStatus = 'Ready' | 'Draft' | 'Archived';

export interface AdminUser {
  id: string;
  fullName: string;
  email: string;
  role: AdminRole;
  status: AccountStatus;
  createdAt: string;
}

export interface SportsVideo {
  id: string;
  title: string;
  description: string;
  uploadedBy: string;
  uploadDate: string;
  status: VideoStatus;
  storagePath?: string;
  originalFilename?: string;
  sizeBytes?: number;
}

export interface AnalysisRequest {
  id: string;
  videoId?: string;
  videoTitle: string;
  requestedBy: string;
  status: AnalysisStatus;
  requestedAt: string;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
  inputPath?: string;
  jobType?: string;
  modelName?: string | null;
}

export interface DetectedAction {
  timestamp: string;
  action: string;
  confidence: number;
}

export interface AnalysisResult {
  id: string;
  videoTitle: string;
  resultSummary: string;
  detectedSportAction: string;
  confidenceScore: number;
  recommendations: string;
  createdAt: string;
  detectedActions: DetectedAction[];
}

export interface Report {
  id: string;
  title: string;
  relatedVideo: string;
  summary: string;
  generatedAt: string;
  status: ReportStatus;
}

export interface DashboardStats {
  totalUsers: number;
  totalUploadedVideos: number;
  totalAnalysisRequests: number;
  completedAnalyses: number;
  pendingAnalyses: number;
  failedAnalyses: number;
}
