export interface Video {
    id: string;
    name: string;
    url: string;
    thumbnail?: string;
    duration: number;
    uploadDate: Date;
    size: number;
    status: VideoStatus;
    metadata?: VideoMetadata;
}

export interface VideoMetadata {
    resolution: string;
    fps: number;
    codec: string;
    sport: string;
}

export enum VideoStatus {
    UPLOADING = 'uploading',
    PROCESSING = 'processing',
    READY = 'ready',
    ERROR = 'error'
}

export interface UploadProgress {
    videoId: string;
    progress: number;
    status: VideoStatus;
}
