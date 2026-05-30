import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface DetectionResult {
    label: string;
    confidence: number;
    box: { x1: number; y1: number; x2: number; y2: number };
}

interface DetectResponse {
    detections: DetectionResult[];
    annotated_image: string;
    count: number;
    error?: string;
}

@Component({
    selector: 'app-detection',
    standalone: false,
    templateUrl: './detection.html',
    styleUrls: ['./detection.scss']
})
export class Detection {
    readonly API = environment.aiApiBaseUrl;

    selectedFile: File | null = null;
    previewUrl: string | null = null;
    annotatedUrl: string | null = null;
    detections: DetectionResult[] = [];
    count = 0;
    loading = false;
    error = '';
    apiStatus: 'unknown' | 'ok' | 'down' = 'unknown';

    constructor(private http: HttpClient) {
        this.checkHealth();
    }

    checkHealth() {
        this.http.get<{ status: string }>(`${this.API}/health`).subscribe({
            next: () => (this.apiStatus = 'ok'),
            error: () => (this.apiStatus = 'down')
        });
    }

    onFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files?.length) return;
        this.selectedFile = input.files[0];
        this.annotatedUrl = null;
        this.detections = [];
        this.error = '';
        // Preview
        const reader = new FileReader();
        reader.onload = () => (this.previewUrl = reader.result as string);
        reader.readAsDataURL(this.selectedFile);
    }

    detect() {
        if (!this.selectedFile) return;
        this.loading = true;
        this.error = '';
        this.annotatedUrl = null;
        this.detections = [];

        const form = new FormData();
        form.append('image', this.selectedFile);

        this.http.post<DetectResponse>(`${this.API}/detect`, form).subscribe({
            next: (res) => {
                this.loading = false;
                if (res.error) { this.error = res.error; return; }
                this.annotatedUrl = res.annotated_image;
                this.detections = res.detections;
                this.count = res.count;
            },
            error: (err) => {
                this.loading = false;
                this.error = err.message || 'Failed to reach the detection API.';
            }
        });
    }
}
