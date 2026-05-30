using Microsoft.EntityFrameworkCore;
using SA.Models.Entities;
using SA.Models.Enums;

namespace SA.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    // ── Core tables ───────────────────────────────────────────────────────────
    public DbSet<User> Users => Set<User>();
    public DbSet<Project> Projects => Set<Project>();
    public DbSet<Video> Videos => Set<Video>();
    public DbSet<ProcessingJob> ProcessingJobs => Set<ProcessingJob>();
    public DbSet<Detection> Detections => Set<Detection>();
    public DbSet<JobStatistic> JobStatistics => Set<JobStatistic>();
    public DbSet<AIStatistic> AIStatistics => Set<AIStatistic>();
    public DbSet<AIResultFile> AIResultFiles => Set<AIResultFile>();
    public DbSet<ActionPrediction> ActionPredictions => Set<ActionPrediction>();
    public DbSet<Heatmap> Heatmaps => Set<Heatmap>();
    public DbSet<Report> Reports => Set<Report>();
    public DbSet<AuditLog> AuditLogs => Set<AuditLog>();
    public DbSet<UserSetting> UserSettings => Set<UserSetting>();

    // ── Phase 2: Match Stats ──────────────────────────────────────────────────
    public DbSet<Match> Matches => Set<Match>();
    public DbSet<MatchAnnotation> MatchAnnotations => Set<MatchAnnotation>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // ── User ──────────────────────────────────────────────────────────────
        modelBuilder.Entity<User>(e =>
        {
            e.ToTable("users");
            e.HasKey(u => u.Id);
            e.Property(u => u.Username).HasMaxLength(50).IsRequired();
            e.Property(u => u.Email).HasMaxLength(255).IsRequired();
            e.Property(u => u.PasswordHash).HasMaxLength(255).IsRequired();
            e.Property(u => u.FullName).HasMaxLength(120).IsRequired();
            e.Property(u => u.RefreshTokenHash).HasMaxLength(255);
            e.Property(u => u.Role)
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();

            e.HasIndex(u => u.Username).IsUnique();
            e.HasIndex(u => u.Email).IsUnique();

            e.HasMany(u => u.UploadedVideos)
                .WithOne(v => v.UploadedByUser)
                .HasForeignKey(v => v.UploadedByUserId)
                .OnDelete(DeleteBehavior.Restrict);

            e.HasMany(u => u.RequestedJobs)
                .WithOne(j => j.RequestedByUser)
                .HasForeignKey(j => j.RequestedByUserId)
                .OnDelete(DeleteBehavior.SetNull);

            e.HasMany(u => u.CreatedReports)
                .WithOne(r => r.CreatedByUser)
                .HasForeignKey(r => r.CreatedByUserId)
                .OnDelete(DeleteBehavior.Restrict);

            e.HasMany(u => u.AuditLogs)
                .WithOne(al => al.ActorUser)
                .HasForeignKey(al => al.ActorUserId)
                .OnDelete(DeleteBehavior.SetNull);

            e.HasMany(u => u.Projects)
                .WithOne(p => p.OwnerUser)
                .HasForeignKey(p => p.OwnerUserId)
                .OnDelete(DeleteBehavior.Restrict);

            e.HasMany(u => u.AIStatistics)
                .WithOne(s => s.User)
                .HasForeignKey(s => s.UserId)
                .OnDelete(DeleteBehavior.SetNull);

            e.HasOne(u => u.Settings)
                .WithOne(s => s.User)
                .HasForeignKey<UserSetting>(s => s.UserId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<UserSetting>(e =>
        {
            e.ToTable("user_settings");
            e.HasKey(s => s.Id);
            e.Property(s => s.ThemeMode).HasMaxLength(20).IsRequired().HasDefaultValue("dark");
            e.Property(s => s.StartPage).HasMaxLength(80).IsRequired().HasDefaultValue("/dashboard");
            e.Property(s => s.ConfidenceThreshold).IsRequired().HasDefaultValue(80);

            e.HasIndex(s => s.UserId).IsUnique();
        });

        modelBuilder.Entity<Project>(e =>
        {
            e.ToTable("projects");
            e.HasKey(p => p.Id);
            e.Property(p => p.Name).HasMaxLength(180).IsRequired();
            e.Property(p => p.Description).HasMaxLength(1000);

            e.HasIndex(p => new { p.OwnerUserId, p.CreatedAt });
            e.HasIndex(p => new { p.OwnerUserId, p.Name });
        });

        // ── Video ─────────────────────────────────────────────────────────────
        modelBuilder.Entity<Video>(e =>
        {
            e.ToTable("videos");
            e.HasKey(v => v.Id);
            e.Property(v => v.Title).HasMaxLength(180).IsRequired();
            e.Property(v => v.OriginalFilename).HasMaxLength(255).IsRequired();
            e.Property(v => v.StoredFilename).HasMaxLength(255).IsRequired();
            e.Property(v => v.MimeType).HasMaxLength(100).IsRequired();
            e.Property(v => v.StoragePath).HasMaxLength(500).IsRequired();
            e.Property(v => v.AnnotatedOutputPath).HasMaxLength(500);
            e.Property(v => v.Status)
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();

            e.HasOne(v => v.Project)
                .WithMany(p => p.Videos)
                .HasForeignKey(v => v.ProjectId)
                .OnDelete(DeleteBehavior.SetNull);

            e.HasIndex(v => new { v.UploadedByUserId, v.UploadedAt });
            e.HasIndex(v => new { v.ProjectId, v.UploadedAt });
            e.HasIndex(v => v.Status);
        });

        // ── ProcessingJob ─────────────────────────────────────────────────────
        modelBuilder.Entity<ProcessingJob>(e =>
        {
            e.ToTable("processing_jobs");
            e.HasKey(j => j.Id);
            e.Property(j => j.JobType)
                .HasConversion<string>()
                .HasMaxLength(30)
                .IsRequired();
            e.Property(j => j.Status)
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            e.Property(j => j.ModelName).HasMaxLength(120);
            e.Property(j => j.InputPath).HasMaxLength(500).IsRequired();
            e.Property(j => j.OutputPath).HasMaxLength(500);
            e.Property(j => j.CsvDir).HasMaxLength(500);

            e.HasOne(j => j.Project)
                .WithMany(p => p.ProcessingJobs)
                .HasForeignKey(j => j.ProjectId)
                .OnDelete(DeleteBehavior.SetNull);

            e.HasOne(j => j.Video)
                .WithMany(v => v.ProcessingJobs)
                .HasForeignKey(j => j.VideoId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasIndex(j => new { j.VideoId, j.CreatedAt });
            e.HasIndex(j => new { j.ProjectId, j.CreatedAt });
            e.HasIndex(j => new { j.Status, j.JobType });
        });

        modelBuilder.Entity<AIResultFile>(e =>
        {
            e.ToTable("ai_result_files");
            e.HasKey(f => f.Id);
            e.Property(f => f.FileType).HasMaxLength(80).IsRequired();
            e.Property(f => f.FileKey).HasMaxLength(120).IsRequired();
            e.Property(f => f.StoragePath).HasMaxLength(500).IsRequired();
            e.Property(f => f.MimeType).HasMaxLength(100);

            e.HasOne(f => f.ProcessingJob)
                .WithMany(j => j.AIResultFiles)
                .HasForeignKey(f => f.ProcessingJobId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasIndex(f => new { f.ProcessingJobId, f.FileKey });
            e.HasIndex(f => f.FileType);
        });

        modelBuilder.Entity<AIStatistic>(e =>
        {
            e.ToTable("ai_statistics");
            e.HasKey(s => s.Id);
            e.Property(s => s.ModelModule).HasMaxLength(120).IsRequired();
            e.Property(s => s.StatGroup).HasMaxLength(120).IsRequired();
            e.Property(s => s.StatKey).HasMaxLength(160).IsRequired();
            e.Property(s => s.StatValue).HasMaxLength(1000);
            e.Property(s => s.NumericValue).HasColumnType("numeric(18,4)");
            e.Property(s => s.TeamId).HasMaxLength(80);
            e.Property(s => s.PlayerId).HasMaxLength(80);

            e.HasOne(s => s.Project)
                .WithMany(p => p.AIStatistics)
                .HasForeignKey(s => s.ProjectId)
                .OnDelete(DeleteBehavior.SetNull);

            e.HasOne(s => s.ProcessingJob)
                .WithMany(j => j.AIStatistics)
                .HasForeignKey(s => s.ProcessingJobId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasOne(s => s.Video)
                .WithMany(v => v.AIStatistics)
                .HasForeignKey(s => s.VideoId)
                .OnDelete(DeleteBehavior.NoAction);

            e.HasOne(s => s.User)
                .WithMany(u => u.AIStatistics)
                .HasForeignKey(s => s.UserId)
                .OnDelete(DeleteBehavior.SetNull);

            e.HasIndex(s => new { s.ProcessingJobId, s.StatGroup, s.StatKey });
            e.HasIndex(s => new { s.VideoId, s.StatGroup, s.CreatedAt });
            e.HasIndex(s => new { s.ProjectId, s.StatGroup, s.CreatedAt });
            e.HasIndex(s => new { s.ModelModule, s.StatGroup });
        });

        modelBuilder.Entity<ActionPrediction>(e =>
        {
            e.ToTable("action_predictions");
            e.HasKey(p => p.Id);
            e.Property(p => p.GameTime).HasMaxLength(30).IsRequired();
            e.Property(p => p.Label).HasMaxLength(80).IsRequired();
            e.Property(p => p.Team).HasMaxLength(30);
            e.Property(p => p.Position).HasMaxLength(80);
            e.Property(p => p.Confidence).HasColumnType("numeric(8,6)").IsRequired();
            e.Property(p => p.ClassName).HasMaxLength(120);

            e.HasOne(p => p.ProcessingJob)
                .WithMany(j => j.ActionPredictions)
                .HasForeignKey(p => p.ProcessingJobId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasIndex(p => new { p.ProcessingJobId, p.Second });
            e.HasIndex(p => new { p.ProcessingJobId, p.Label, p.Team });
        });

        modelBuilder.Entity<Heatmap>(e =>
        {
            e.ToTable("heatmaps");
            e.HasKey(h => h.Id);
            e.Property(h => h.TargetType).HasMaxLength(40).IsRequired();
            e.Property(h => h.TargetId).HasMaxLength(80).IsRequired();
            e.Property(h => h.ImagePath).HasMaxLength(500).IsRequired();

            e.HasOne(h => h.Project)
                .WithMany(p => p.Heatmaps)
                .HasForeignKey(h => h.ProjectId)
                .OnDelete(DeleteBehavior.SetNull);

            e.HasOne(h => h.ProcessingJob)
                .WithMany(j => j.Heatmaps)
                .HasForeignKey(h => h.ProcessingJobId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasIndex(h => new { h.ProcessingJobId, h.TargetType, h.TargetId });
            e.HasIndex(h => new { h.ProjectId, h.GeneratedAt });
        });

        // ── Detection ─────────────────────────────────────────────────────────
        modelBuilder.Entity<Detection>(e =>
        {
            e.ToTable("detections");
            e.HasKey(d => d.Id);
            e.Property(d => d.Label).HasMaxLength(100).IsRequired();
            e.Property(d => d.Confidence).HasColumnType("numeric(5,4)").IsRequired();
            e.Property(d => d.X1).HasColumnType("numeric(10,2)").IsRequired();
            e.Property(d => d.Y1).HasColumnType("numeric(10,2)").IsRequired();
            e.Property(d => d.X2).HasColumnType("numeric(10,2)").IsRequired();
            e.Property(d => d.Y2).HasColumnType("numeric(10,2)").IsRequired();
            e.Property(d => d.TimestampSeconds).HasColumnType("numeric(10,3)");

            e.HasOne(d => d.ProcessingJob)
                .WithMany(j => j.Detections)
                .HasForeignKey(d => d.ProcessingJobId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasOne(d => d.Video)
                .WithMany(v => v.Detections)
                .HasForeignKey(d => d.VideoId)
                .OnDelete(DeleteBehavior.NoAction);

            e.HasIndex(d => d.ProcessingJobId);
            e.HasIndex(d => new { d.VideoId, d.Label });
        });

        // ── Report ────────────────────────────────────────────────────────────
        modelBuilder.Entity<JobStatistic>(e =>
        {
            e.ToTable("job_statistics");
            e.HasKey(s => s.Id);
            e.Property(s => s.ModuleName).HasMaxLength(120).IsRequired();
            e.Property(s => s.ModelName).HasMaxLength(120);
            e.Property(s => s.StatType).HasMaxLength(80).IsRequired();
            e.Property(s => s.StatsJson).IsRequired();

            e.HasOne(s => s.ProcessingJob)
                .WithMany(j => j.Statistics)
                .HasForeignKey(s => s.ProcessingJobId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasOne(s => s.Video)
                .WithMany(v => v.Statistics)
                .HasForeignKey(s => s.VideoId)
                .OnDelete(DeleteBehavior.NoAction);

            e.HasIndex(s => new { s.ProcessingJobId, s.StatType });
            e.HasIndex(s => new { s.VideoId, s.StatType, s.CreatedAt });
            e.HasIndex(s => new { s.ModuleName, s.StatType });
        });

        modelBuilder.Entity<Report>(e =>
        {
            e.ToTable("reports");
            e.HasKey(r => r.Id);
            e.Property(r => r.Title).HasMaxLength(180).IsRequired();
            e.Property(r => r.ReportType)
                .HasConversion<string>()
                .HasMaxLength(30)
                .IsRequired();
            e.Property(r => r.Format)
                .HasConversion<string>()
                .HasMaxLength(10)
                .IsRequired();
            e.Property(r => r.Status)
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            e.Property(r => r.FilePath).HasMaxLength(500);

            e.HasOne(r => r.Video)
                .WithMany(v => v.Reports)
                .HasForeignKey(r => r.VideoId)
                .OnDelete(DeleteBehavior.NoAction);

            e.HasOne(r => r.ProcessingJob)
                .WithMany(j => j.Reports)
                .HasForeignKey(r => r.ProcessingJobId)
                .OnDelete(DeleteBehavior.NoAction);

            e.HasIndex(r => new { r.CreatedByUserId, r.CreatedAt });
        });

        // ── AuditLog ──────────────────────────────────────────────────────────
        modelBuilder.Entity<AuditLog>(e =>
        {
            e.ToTable("audit_logs");
            e.HasKey(al => al.Id);
            e.Property(al => al.EntityType)
                .HasConversion<string>()
                .HasMaxLength(40)
                .IsRequired();
            e.Property(al => al.EntityId).HasMaxLength(36).IsRequired();
            e.Property(al => al.Action).HasMaxLength(120).IsRequired();
            e.Property(al => al.Status).HasMaxLength(60);
            e.Property(al => al.IpAddress).HasMaxLength(64);

            e.HasIndex(al => new { al.EntityType, al.EntityId, al.CreatedAt });
        });

        // ── Match ─────────────────────────────────────────────────────────────
        modelBuilder.Entity<Match>(e =>
        {
            e.ToTable("matches");
            e.HasKey(m => m.Id);
            e.Property(m => m.Id).UseIdentityColumn();
            e.Property(m => m.UrlLocal).HasMaxLength(500).IsRequired();
            e.Property(m => m.UrlYoutube).HasMaxLength(500);
            e.Property(m => m.Halftime).HasMaxLength(20).IsRequired();
            e.Property(m => m.HomeTeam).HasMaxLength(120).IsRequired();
            e.Property(m => m.AwayTeam).HasMaxLength(120).IsRequired();
            e.Property(m => m.Competition).HasMaxLength(120).IsRequired();
            e.Property(m => m.Season).HasMaxLength(20).IsRequired();

            e.HasIndex(m => m.UrlLocal).IsUnique();
            e.HasIndex(m => new { m.Competition, m.Season });
            e.HasIndex(m => m.MatchDate);
        });

        // ── MatchAnnotation ───────────────────────────────────────────────────
        modelBuilder.Entity<MatchAnnotation>(e =>
        {
            e.ToTable("match_annotations");
            e.HasKey(a => a.Id);
            e.Property(a => a.Id).UseIdentityColumn();
            e.Property(a => a.GameTime).HasMaxLength(20).IsRequired();
            e.Property(a => a.Label).HasMaxLength(60).IsRequired();
            e.Property(a => a.Team).HasMaxLength(10).IsRequired();
            e.Property(a => a.Visibility)
                .HasConversion<string>()
                .HasMaxLength(15)
                .IsRequired();

            e.HasOne(a => a.Match)
                .WithMany(m => m.Annotations)
                .HasForeignKey(a => a.MatchId)
                .OnDelete(DeleteBehavior.Cascade);

            e.HasIndex(a => new { a.MatchId, a.Label });
            e.HasIndex(a => new { a.MatchId, a.Team });
            e.HasIndex(a => new { a.MatchId, a.Half });
            e.HasIndex(a => new { a.MatchId, a.GameTimeSeconds });
        });
    }
}
