import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { VideoRepository } from '../repositories/video.repository';
import { Video, UploadProgress } from '../models/video.model';

@Injectable({
    providedIn: 'root'
})
export class VideoService {
    private videosSubject = new BehaviorSubject<Video[]>([]);
    public videos$ = this.videosSubject.asObservable();

    constructor(private videoRepository: VideoRepository) {
        this.loadVideos();
    }

    loadVideos(): void {
        this.videoRepository.getAll().subscribe(videos => {
            this.videosSubject.next(videos);
        });
    }

    getVideos(): Observable<Video[]> {
        return this.videos$;
    }

    getVideoById(id: string): Observable<Video> {
        return this.videoRepository.getById(id);
    }

    uploadVideo(file: File): Observable<UploadProgress> {
        return this.videoRepository.upload(file);
    }

    deleteVideo(id: string): void {
        this.videoRepository.delete(id).subscribe(() => {
            const currentVideos = this.videosSubject.value;
            this.videosSubject.next(currentVideos.filter(v => v.id !== id));
        });
    }
}
