import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { CreateVideoRecordApiRequest, PagedResponse, VideoApiResponse } from '../models/api.model';
import { UploadProgress, Video, VideoStatus } from '../models/video.model';
import { BaseRepository } from './base.repository';

@Injectable({
    providedIn: 'root'
})
export class VideoRepository extends BaseRepository<Video> {
    protected override apiUrl = `${environment.apiBaseUrl}/videos`;

    constructor(private http: HttpClient) {
        super();
    }

    override getAll(): Observable<Video[]> {
        const params = new HttpParams().set('page', '1').set('pageSize', '100');
        return this.http.get<PagedResponse<VideoApiResponse>>(this.apiUrl, { params }).pipe(
            map((page) => page.items.map((video) => this.mapVideo(video)))
        );
    }

    override getById(id: string): Observable<Video> {
        return this.http.get<VideoApiResponse>(`${this.apiUrl}/${id}`).pipe(
            map((video) => this.mapVideo(video))
        );
    }

    override create(video: Video): Observable<Video> {
        const payload: CreateVideoRecordApiRequest = {
            title: video.name,
            originalFilename: video.name,
            storedFilename: video.name,
            mimeType: 'video/mp4',
            storagePath: video.url,
            sizeBytes: video.size,
            durationSeconds: video.duration
        };

        return this.http.post<VideoApiResponse>(this.apiUrl, payload).pipe(
            map((created) => this.mapVideo(created))
        );
    }

    override update(id: string, video: Video): Observable<Video> {
        return this.http.put<VideoApiResponse>(`${this.apiUrl}/${id}`, {
            title: video.name,
            status: this.toApiStatus(video.status),
            annotatedOutputPath: video.url
        }).pipe(
            map((updated) => this.mapVideo(updated))
        );
    }

    override delete(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/${id}`);
    }

    upload(file: File): Observable<UploadProgress> {
        const storedFilename = `${Date.now()}-${file.name}`;
        const payload: CreateVideoRecordApiRequest = {
            title: file.name,
            originalFilename: file.name,
            storedFilename,
            mimeType: file.type || 'application/octet-stream',
            storagePath: `uploads/${storedFilename}`,
            sizeBytes: file.size,
            durationSeconds: null
        };

        return this.http.post<VideoApiResponse>(this.apiUrl, payload).pipe(
            map((video) => ({
                videoId: video.id,
                progress: 100,
                status: this.mapStatus(video.status)
            }))
        );
    }

    private mapVideo(video: VideoApiResponse): Video {
        return {
            id: video.id,
            name: video.title,
            url: video.annotatedOutputPath || video.storagePath,
            duration: video.durationSeconds ?? 0,
            uploadDate: new Date(video.uploadedAt),
            size: video.sizeBytes,
            status: this.mapStatus(video.status)
        };
    }

    private mapStatus(status: string): VideoStatus {
        switch (status.toLowerCase()) {
            case 'queued':
            case 'processing':
                return VideoStatus.PROCESSING;
            case 'failed':
                return VideoStatus.ERROR;
            case 'uploaded':
            case 'ready':
            default:
                return VideoStatus.READY;
        }
    }

    private toApiStatus(status: VideoStatus): string {
        switch (status) {
            case VideoStatus.PROCESSING:
                return 'Processing';
            case VideoStatus.ERROR:
                return 'Failed';
            case VideoStatus.READY:
            case VideoStatus.UPLOADING:
            default:
                return 'Uploaded';
        }
    }
}
