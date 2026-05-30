import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { VideoService } from '../../services/video.service';
import { VideoStatus } from '../../models/video.model';

@Component({
  selector: 'app-dashboard',
  standalone: false,
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit {
  stats: Array<{ label: string; value: string; icon: string; color: string }> = [];

  recentVideos: any[] = [];

  constructor(
    private videoService: VideoService,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.videoService.getVideos().subscribe(videos => {
      this.recentVideos = videos.slice(0, 3);
      const completed = videos.filter((video) => video.status === VideoStatus.READY).length;
      const processing = videos.filter((video) => video.status === VideoStatus.PROCESSING).length;
      const failed = videos.filter((video) => video.status === VideoStatus.ERROR).length;
      this.stats = [
        { label: 'Total Videos', value: String(videos.length), icon: 'video', color: 'blue' },
        { label: 'Ready Videos', value: String(completed), icon: 'check', color: 'green' },
        { label: 'Processing', value: String(processing), icon: 'target', color: 'purple' },
        { label: 'Failed', value: String(failed), icon: 'clock', color: 'orange' }
      ];
    });
  }

  navigateToUpload(): void {
    this.router.navigate(['/upload']);
  }

  navigateToAnalytics(): void {
    this.router.navigate(['/analytics']);
  }

  formatVideoSize(sizeBytes: number | null | undefined): string | null {
    const size = Number(sizeBytes ?? 0);
    if (!Number.isFinite(size) || size <= 0) {
      return null;
    }

    return `${(size / 1048576).toFixed(1)} MB`;
  }
}
