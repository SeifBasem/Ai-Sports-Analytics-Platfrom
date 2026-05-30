# AI Sports Analytics Dashboard - Angular

Modern sports analytics dashboard built with Angular, featuring a clean **repository and service architecture** pattern.

## 🏗️ Architecture

This application follows a layered architecture with clear separation of concerns:

- **Models Layer**: TypeScript interfaces for type safety
- **Repository Layer**: Data access and API communication
- **Service Layer**: Business logic and state management
- **Component Layer**: UI and user interactions
- **Guards**: Route protection and authorization

## 🚀 Quick Start

### Prerequisites
- Node.js 20.x or higher
- npm 11.x or higher

### Installation

```bash
# Install dependencies
npm install
```

### Development Server

```bash
# Start development server
ng serve

# Or with auto-open browser
ng serve --open
```

Navigate to `http://localhost:4200/`. The application will automatically reload if you change any source files.

### Build

```bash
# Build for production
ng build

# Build output will be in dist/ai-sports-analytics-angular/
```

## 📁 Project Structure

```
src/app/
├── models/          # TypeScript interfaces and enums
├── repositories/    # Data access layer (API calls, mock data)
├── services/        # Business logic and state management
├── guards/          # Route protection
├── features/        # Feature modules (lazy-loadable)
│   ├── login/
│   ├── dashboard/
│   ├── video-upload/
│   ├── analytics/
│   ├── heatmap/
│   ├── reports/
│   └── settings/
└── shared/          # Shared components and utilities
    └── sidebar/
```

## 🔐 Authentication

The application includes a complete authentication system:
- Login page with form validation
- JWT token storage in localStorage
- Route guards for protected routes
- Auth service with reactive state management

**Demo Login**: Use any username/password (mock authentication)

## 🎨 Styling

- **TailwindCSS 3.x** for utility-first styling
- Custom dark theme with gradient accents
- Glassmorphism effects with backdrop blur
- Fully responsive design (mobile, tablet, desktop)
- Smooth animations and transitions

## 📊 Features

### Implemented
- ✅ User authentication with route guards
- ✅ Dashboard with stats and quick actions
- ✅ Video upload interface
- ✅ Analytics visualization placeholders
- ✅ Heatmap visualization area
- ✅ Reports generation
- ✅ Settings page
- ✅ Responsive sidebar navigation

### Ready to Implement
- 📊 Real chart integrations (ng2-charts, recharts)
- 🔌 Backend API integration
- 📹 Actual video upload functionality
- 🗺️ Real heatmap rendering
- 📄 PDF report generation

## 🛠️ Technologies

- **Angular 20.1.5** - Latest stable framework
- **TypeScript** - Type-safe JavaScript
- **RxJS** - Reactive programming
- **TailwindCSS 3.x** - Utility-first CSS
- **Angular Router** - Client-side routing
- **FormsModule** - Template-driven forms

## 📝 Code Examples

### Using the Repository Pattern

```typescript
// In a component
constructor(private videoService: VideoService) {}

ngOnInit() {
  this.videoService.getVideos().subscribe(videos => {
    this.videos = videos;
  });
}
```

### Service Layer

```typescript
@Injectable({ providedIn: 'root' })
export class VideoService {
  constructor(private videoRepository: VideoRepository) {}
  
  getVideos(): Observable<Video[]> {
    return this.videoRepository.getAll();
  }
}
```

### Repository Layer

```typescript
@Injectable({ providedIn: 'root' })
export class VideoRepository extends BaseRepository<Video> {
  constructor(private http: HttpClient) { super(); }
  
  getAll(): Observable<Video[]> {
    return this.http.get<Video[]>(`${this.apiUrl}/videos`);
  }
}
```

## 🧪 Testing

```bash
# Run unit tests
ng test

# Run e2e tests
ng e2e

# Generate code coverage
ng test --code-coverage
```

## 📦 Building for Production

```bash
# Production build with optimizations
ng build --configuration production

# Analyze bundle size
ng build --stats-json
npx webpack-bundle-analyzer dist/ai-sports-analytics-angular/stats.json
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## 📄 License

MIT License - feel free to use this project for learning or production.

## 🙏 Credits

Original design from Figma: [AI Sports Analytics Dashboard](https://www.figma.com/design/I54wZzL6CQsAoAVHAv14GL/AI-Sports-Analytics-Dashboard)

---

**Built with ❤️ using Angular and TailwindCSS**
