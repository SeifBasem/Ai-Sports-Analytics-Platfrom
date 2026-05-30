import { Component, OnInit } from '@angular/core';
import { SportsVideo } from '../../models/admin.model';
import { AdminApiService } from '../../services/admin-api.service';
import { DataTableAction, DataTableActionEvent, DataTableColumn, DataTableRow } from '../../shared/data-table/data-table';

@Component({
  selector: 'app-videos-page',
  standalone: false,
  templateUrl: './videos.html',
  styleUrl: './videos.scss'
})
export class VideosPage implements OnInit {
  videos: SportsVideo[] = [];
  selectedVideo: SportsVideo | null = null;
  notice = '';
  selectedFileName = '';
  selectedFile: File | null = null;

  uploadForm = {
    title: '',
    description: '',
    uploadedBy: ''
  };

  columns: DataTableColumn[] = [
    { key: 'id', label: 'Id' },
    { key: 'title', label: 'Title' },
    { key: 'description', label: 'Description', type: 'longText' },
    { key: 'uploadedBy', label: 'Uploaded By' },
    { key: 'uploadDate', label: 'Upload Date' },
    { key: 'status', label: 'Status', type: 'status' }
  ];

  actions: DataTableAction[] = [
    { id: 'view', label: 'View details', icon: 'eye', variant: 'secondary' },
    { id: 'start', label: 'Start Analysis', icon: 'play', variant: 'primary', visibleForStatus: ['Uploaded', 'Failed'] },
    { id: 'delete', label: 'Delete', icon: 'trash-2', variant: 'danger' }
  ];

  constructor(private adminData: AdminApiService) { }

  ngOnInit(): void {
    this.loadVideos();
  }

  get rows(): DataTableRow[] {
    return this.videos.map((video) => ({
      id: video.id,
      title: video.title,
      description: video.description,
      uploadedBy: video.uploadedBy,
      uploadDate: video.uploadDate,
      status: video.status
    }));
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.item(0);
    this.selectedFile = file ?? null;
    this.selectedFileName = file?.name ?? '';
  }

  submitUpload(): void {
    const title = this.uploadForm.title.trim();
    const description = this.uploadForm.description.trim();
    const uploadedBy = this.uploadForm.uploadedBy.trim();

    if (!title || !description || !uploadedBy || !this.selectedFile) {
      this.notice = 'Please complete the upload form.';
      return;
    }

    this.adminData.addVideo(title, description, this.selectedFile).subscribe((video) => {
      this.notice = `${video.title} has been added to uploaded videos.`;
      this.uploadForm = { title: '', description: '', uploadedBy: '' };
      this.selectedFileName = '';
      this.selectedFile = null;
      this.loadVideos();
    });
  }

  handleAction(event: DataTableActionEvent): void {
    const id = String(event.row['id']);
    const video = this.videos.find((item) => item.id === id);

    if (!video) {
      return;
    }

    if (event.actionId === 'view') {
      this.selectedVideo = video;
    }

    if (event.actionId === 'start') {
      this.adminData.startAnalysis(video).subscribe((request) => {
        this.notice = `Analysis request ${request.id} started for ${video.title}.`;
        this.loadVideos();
      });
    }

    if (event.actionId === 'delete') {
      this.adminData.deleteVideo(id).subscribe(() => {
        this.notice = `${video.title} has been deleted.`;
        this.loadVideos();
      });
    }
  }

  closeNotice(): void {
    this.notice = '';
  }

  private loadVideos(): void {
    this.adminData.getVideos().subscribe((videos) => {
      this.videos = videos;
    });
  }
}
