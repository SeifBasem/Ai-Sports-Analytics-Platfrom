using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SA.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "matches",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    UrlLocal = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    UrlYoutube = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    Halftime = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    HalfNumber = table.Column<int>(type: "int", nullable: false),
                    HalftimeMinutes = table.Column<int>(type: "int", nullable: false),
                    HomeTeam = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    AwayTeam = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    Competition = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    Season = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    MatchDate = table.Column<DateOnly>(type: "date", nullable: true),
                    ImportedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_matches", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "users",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    Username = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    Email = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    PasswordHash = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    FullName = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    Role = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    IsActive = table.Column<bool>(type: "bit", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_users", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "match_annotations",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    MatchId = table.Column<int>(type: "int", nullable: false),
                    GameTime = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    Half = table.Column<int>(type: "int", nullable: false),
                    GameTimeSeconds = table.Column<int>(type: "int", nullable: false),
                    Label = table.Column<string>(type: "nvarchar(60)", maxLength: 60, nullable: false),
                    Team = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: false),
                    Position = table.Column<int>(type: "int", nullable: false),
                    Visibility = table.Column<string>(type: "nvarchar(15)", maxLength: 15, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_match_annotations", x => x.Id);
                    table.ForeignKey(
                        name: "FK_match_annotations_matches_MatchId",
                        column: x => x.MatchId,
                        principalTable: "matches",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "audit_logs",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ActorUserId = table.Column<Guid>(type: "uniqueidentifier", nullable: true),
                    EntityType = table.Column<string>(type: "nvarchar(40)", maxLength: 40, nullable: false),
                    EntityId = table.Column<string>(type: "nvarchar(36)", maxLength: 36, nullable: false),
                    Action = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    Status = table.Column<string>(type: "nvarchar(60)", maxLength: 60, nullable: true),
                    Message = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    MetadataJson = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    IpAddress = table.Column<string>(type: "nvarchar(64)", maxLength: 64, nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_audit_logs", x => x.Id);
                    table.ForeignKey(
                        name: "FK_audit_logs_users_ActorUserId",
                        column: x => x.ActorUserId,
                        principalTable: "users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "videos",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    UploadedByUserId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    Title = table.Column<string>(type: "nvarchar(180)", maxLength: 180, nullable: false),
                    OriginalFilename = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    StoredFilename = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    MimeType = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    StoragePath = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    AnnotatedOutputPath = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    SizeBytes = table.Column<long>(type: "bigint", nullable: false),
                    DurationSeconds = table.Column<int>(type: "int", nullable: true),
                    Status = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    ErrorMessage = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    UploadedAt = table.Column<DateTime>(type: "datetime2", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_videos", x => x.Id);
                    table.ForeignKey(
                        name: "FK_videos_users_UploadedByUserId",
                        column: x => x.UploadedByUserId,
                        principalTable: "users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "processing_jobs",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    VideoId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    RequestedByUserId = table.Column<Guid>(type: "uniqueidentifier", nullable: true),
                    JobType = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: false),
                    Status = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    ModelName = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: true),
                    InputPath = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    OutputPath = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    ProgressPercent = table.Column<int>(type: "int", nullable: false),
                    FrameCount = table.Column<int>(type: "int", nullable: true),
                    ObjectCount = table.Column<int>(type: "int", nullable: true),
                    StartedAt = table.Column<DateTime>(type: "datetime2", nullable: true),
                    CompletedAt = table.Column<DateTime>(type: "datetime2", nullable: true),
                    ErrorMessage = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    MetadataJson = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_processing_jobs", x => x.Id);
                    table.ForeignKey(
                        name: "FK_processing_jobs_users_RequestedByUserId",
                        column: x => x.RequestedByUserId,
                        principalTable: "users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_processing_jobs_videos_VideoId",
                        column: x => x.VideoId,
                        principalTable: "videos",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "detections",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ProcessingJobId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    VideoId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    FrameIndex = table.Column<int>(type: "int", nullable: true),
                    TimestampSeconds = table.Column<decimal>(type: "numeric(10,3)", nullable: true),
                    Label = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    Confidence = table.Column<decimal>(type: "numeric(5,4)", nullable: false),
                    X1 = table.Column<decimal>(type: "numeric(10,2)", nullable: false),
                    Y1 = table.Column<decimal>(type: "numeric(10,2)", nullable: false),
                    X2 = table.Column<decimal>(type: "numeric(10,2)", nullable: false),
                    Y2 = table.Column<decimal>(type: "numeric(10,2)", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_detections", x => x.Id);
                    table.ForeignKey(
                        name: "FK_detections_processing_jobs_ProcessingJobId",
                        column: x => x.ProcessingJobId,
                        principalTable: "processing_jobs",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_detections_videos_VideoId",
                        column: x => x.VideoId,
                        principalTable: "videos",
                        principalColumn: "Id");
                });

            migrationBuilder.CreateTable(
                name: "reports",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    CreatedByUserId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    VideoId = table.Column<Guid>(type: "uniqueidentifier", nullable: true),
                    ProcessingJobId = table.Column<Guid>(type: "uniqueidentifier", nullable: true),
                    Title = table.Column<string>(type: "nvarchar(180)", maxLength: 180, nullable: false),
                    Description = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    ReportType = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: false),
                    Format = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: false),
                    Status = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    FilePath = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    GeneratedAt = table.Column<DateTime>(type: "datetime2", nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_reports", x => x.Id);
                    table.ForeignKey(
                        name: "FK_reports_processing_jobs_ProcessingJobId",
                        column: x => x.ProcessingJobId,
                        principalTable: "processing_jobs",
                        principalColumn: "Id");
                    table.ForeignKey(
                        name: "FK_reports_users_CreatedByUserId",
                        column: x => x.CreatedByUserId,
                        principalTable: "users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_reports_videos_VideoId",
                        column: x => x.VideoId,
                        principalTable: "videos",
                        principalColumn: "Id");
                });

            migrationBuilder.CreateIndex(
                name: "IX_audit_logs_ActorUserId",
                table: "audit_logs",
                column: "ActorUserId");

            migrationBuilder.CreateIndex(
                name: "IX_audit_logs_EntityType_EntityId_CreatedAt",
                table: "audit_logs",
                columns: new[] { "EntityType", "EntityId", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_detections_ProcessingJobId",
                table: "detections",
                column: "ProcessingJobId");

            migrationBuilder.CreateIndex(
                name: "IX_detections_VideoId_Label",
                table: "detections",
                columns: new[] { "VideoId", "Label" });

            migrationBuilder.CreateIndex(
                name: "IX_match_annotations_MatchId_GameTimeSeconds",
                table: "match_annotations",
                columns: new[] { "MatchId", "GameTimeSeconds" });

            migrationBuilder.CreateIndex(
                name: "IX_match_annotations_MatchId_Half",
                table: "match_annotations",
                columns: new[] { "MatchId", "Half" });

            migrationBuilder.CreateIndex(
                name: "IX_match_annotations_MatchId_Label",
                table: "match_annotations",
                columns: new[] { "MatchId", "Label" });

            migrationBuilder.CreateIndex(
                name: "IX_match_annotations_MatchId_Team",
                table: "match_annotations",
                columns: new[] { "MatchId", "Team" });

            migrationBuilder.CreateIndex(
                name: "IX_matches_Competition_Season",
                table: "matches",
                columns: new[] { "Competition", "Season" });

            migrationBuilder.CreateIndex(
                name: "IX_matches_MatchDate",
                table: "matches",
                column: "MatchDate");

            migrationBuilder.CreateIndex(
                name: "IX_matches_UrlLocal",
                table: "matches",
                column: "UrlLocal",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_processing_jobs_RequestedByUserId",
                table: "processing_jobs",
                column: "RequestedByUserId");

            migrationBuilder.CreateIndex(
                name: "IX_processing_jobs_Status_JobType",
                table: "processing_jobs",
                columns: new[] { "Status", "JobType" });

            migrationBuilder.CreateIndex(
                name: "IX_processing_jobs_VideoId_CreatedAt",
                table: "processing_jobs",
                columns: new[] { "VideoId", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_reports_CreatedByUserId_CreatedAt",
                table: "reports",
                columns: new[] { "CreatedByUserId", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_reports_ProcessingJobId",
                table: "reports",
                column: "ProcessingJobId");

            migrationBuilder.CreateIndex(
                name: "IX_reports_VideoId",
                table: "reports",
                column: "VideoId");

            migrationBuilder.CreateIndex(
                name: "IX_users_Email",
                table: "users",
                column: "Email",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_users_Username",
                table: "users",
                column: "Username",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_videos_Status",
                table: "videos",
                column: "Status");

            migrationBuilder.CreateIndex(
                name: "IX_videos_UploadedByUserId_UploadedAt",
                table: "videos",
                columns: new[] { "UploadedByUserId", "UploadedAt" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "audit_logs");

            migrationBuilder.DropTable(
                name: "detections");

            migrationBuilder.DropTable(
                name: "match_annotations");

            migrationBuilder.DropTable(
                name: "reports");

            migrationBuilder.DropTable(
                name: "matches");

            migrationBuilder.DropTable(
                name: "processing_jobs");

            migrationBuilder.DropTable(
                name: "videos");

            migrationBuilder.DropTable(
                name: "users");
        }
    }
}
