export interface PagedResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
}

export interface AdminDashboardApiResponse {
  totalUsers: number;
  activeUsers: number;
  totalVideos: number;
  processingJobs: number;
  completedJobs: number;
  failedJobs: number;
  reports: number;
  matches: number;
  storedStatistics: number;
  jobStatusCounts: StatusCountApiResponse[];
  videoStatusCounts: StatusCountApiResponse[];
}

export interface StatusCountApiResponse {
  status: string;
  count: number;
}

export interface UserApiResponse {
  id: string;
  username: string;
  email: string;
  fullName: string;
  role: string;
  isActive: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface VideoApiResponse {
  id: string;
  uploadedByUserId: string;
  uploadedBy: string;
  title: string;
  originalFilename: string;
  storedFilename: string;
  mimeType: string;
  storagePath: string;
  annotatedOutputPath?: string | null;
  sizeBytes: number;
  durationSeconds?: number | null;
  status: string;
  errorMessage?: string | null;
  uploadedAt: string;
  updatedAt: string;
}

export interface CreateVideoRecordApiRequest {
  title: string;
  originalFilename: string;
  storedFilename: string;
  mimeType: string;
  storagePath: string;
  sizeBytes: number;
  durationSeconds?: number | null;
}

export interface ProcessingJobApiResponse {
  id: string;
  videoId: string;
  videoTitle: string;
  requestedByUserId?: string | null;
  requestedBy?: string | null;
  jobType: string;
  status: string;
  modelName?: string | null;
  inputPath: string;
  outputPath?: string | null;
  progressPercent: number;
  frameCount?: number | null;
  objectCount?: number | null;
  startedAt?: string | null;
  completedAt?: string | null;
  errorMessage?: string | null;
  metadataJson?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateProcessingJobApiRequest {
  videoId: string;
  jobType: string;
  modelName?: string | null;
  inputPath: string;
}

export interface UpdateProcessingJobStatusApiRequest {
  status: string;
  progressPercent?: number | null;
  frameCount?: number | null;
  objectCount?: number | null;
  outputPath?: string | null;
  errorMessage?: string | null;
}

export interface JobStatisticApiResponse {
  id: string;
  processingJobId: string;
  videoId: string;
  moduleName: string;
  modelName?: string | null;
  statType: string;
  statsJson: string;
  createdAt: string;
}

export interface ReportApiResponse {
  id: string;
  createdByUserId: string;
  createdBy: string;
  videoId?: string | null;
  videoTitle?: string | null;
  processingJobId?: string | null;
  title: string;
  description?: string | null;
  reportType: string;
  format: string;
  status: string;
  filePath?: string | null;
  generatedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}
