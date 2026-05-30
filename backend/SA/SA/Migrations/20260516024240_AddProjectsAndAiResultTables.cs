using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SA.Migrations
{
    /// <inheritdoc />
    public partial class AddProjectsAndAiResultTables : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<Guid>(
                name: "ProjectId",
                table: "videos",
                type: "uniqueidentifier",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "CsvDir",
                table: "processing_jobs",
                type: "nvarchar(500)",
                maxLength: 500,
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "ProjectId",
                table: "processing_jobs",
                type: "uniqueidentifier",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "action_predictions",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ProcessingJobId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    GameTime = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: false),
                    Label = table.Column<string>(type: "nvarchar(80)", maxLength: 80, nullable: false),
                    Team = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: true),
                    Position = table.Column<string>(type: "nvarchar(80)", maxLength: 80, nullable: true),
                    Half = table.Column<int>(type: "int", nullable: true),
                    Confidence = table.Column<decimal>(type: "numeric(8,6)", nullable: false),
                    Frame = table.Column<int>(type: "int", nullable: true),
                    ClassName = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: true),
                    Second = table.Column<int>(type: "int", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_action_predictions", x => x.Id);
                    table.ForeignKey(
                        name: "FK_action_predictions_processing_jobs_ProcessingJobId",
                        column: x => x.ProcessingJobId,
                        principalTable: "processing_jobs",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "ai_result_files",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ProcessingJobId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    FileType = table.Column<string>(type: "nvarchar(80)", maxLength: 80, nullable: false),
                    FileKey = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    StoragePath = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    MimeType = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ai_result_files", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ai_result_files_processing_jobs_ProcessingJobId",
                        column: x => x.ProcessingJobId,
                        principalTable: "processing_jobs",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "projects",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    OwnerUserId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    Name = table.Column<string>(type: "nvarchar(180)", maxLength: 180, nullable: false),
                    Description = table.Column<string>(type: "nvarchar(1000)", maxLength: 1000, nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_projects", x => x.Id);
                    table.ForeignKey(
                        name: "FK_projects_users_OwnerUserId",
                        column: x => x.OwnerUserId,
                        principalTable: "users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ai_statistics",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ProjectId = table.Column<Guid>(type: "uniqueidentifier", nullable: true),
                    ProcessingJobId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    VideoId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    UserId = table.Column<Guid>(type: "uniqueidentifier", nullable: true),
                    ModelModule = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    StatGroup = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    StatKey = table.Column<string>(type: "nvarchar(160)", maxLength: 160, nullable: false),
                    StatValue = table.Column<string>(type: "nvarchar(1000)", maxLength: 1000, nullable: true),
                    NumericValue = table.Column<decimal>(type: "numeric(18,4)", nullable: true),
                    JsonValue = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    TeamId = table.Column<string>(type: "nvarchar(80)", maxLength: 80, nullable: true),
                    PlayerId = table.Column<string>(type: "nvarchar(80)", maxLength: 80, nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ai_statistics", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ai_statistics_processing_jobs_ProcessingJobId",
                        column: x => x.ProcessingJobId,
                        principalTable: "processing_jobs",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_ai_statistics_projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_ai_statistics_users_UserId",
                        column: x => x.UserId,
                        principalTable: "users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_ai_statistics_videos_VideoId",
                        column: x => x.VideoId,
                        principalTable: "videos",
                        principalColumn: "Id");
                });

            migrationBuilder.CreateTable(
                name: "heatmaps",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ProjectId = table.Column<Guid>(type: "uniqueidentifier", nullable: true),
                    ProcessingJobId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    TargetType = table.Column<string>(type: "nvarchar(40)", maxLength: 40, nullable: false),
                    TargetId = table.Column<string>(type: "nvarchar(80)", maxLength: 80, nullable: false),
                    ImagePath = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    GeneratedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_heatmaps", x => x.Id);
                    table.ForeignKey(
                        name: "FK_heatmaps_processing_jobs_ProcessingJobId",
                        column: x => x.ProcessingJobId,
                        principalTable: "processing_jobs",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_heatmaps_projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateIndex(
                name: "IX_videos_ProjectId_UploadedAt",
                table: "videos",
                columns: new[] { "ProjectId", "UploadedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_processing_jobs_ProjectId_CreatedAt",
                table: "processing_jobs",
                columns: new[] { "ProjectId", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_action_predictions_ProcessingJobId_Label_Team",
                table: "action_predictions",
                columns: new[] { "ProcessingJobId", "Label", "Team" });

            migrationBuilder.CreateIndex(
                name: "IX_action_predictions_ProcessingJobId_Second",
                table: "action_predictions",
                columns: new[] { "ProcessingJobId", "Second" });

            migrationBuilder.CreateIndex(
                name: "IX_ai_result_files_FileType",
                table: "ai_result_files",
                column: "FileType");

            migrationBuilder.CreateIndex(
                name: "IX_ai_result_files_ProcessingJobId_FileKey",
                table: "ai_result_files",
                columns: new[] { "ProcessingJobId", "FileKey" });

            migrationBuilder.CreateIndex(
                name: "IX_ai_statistics_ModelModule_StatGroup",
                table: "ai_statistics",
                columns: new[] { "ModelModule", "StatGroup" });

            migrationBuilder.CreateIndex(
                name: "IX_ai_statistics_ProcessingJobId_StatGroup_StatKey",
                table: "ai_statistics",
                columns: new[] { "ProcessingJobId", "StatGroup", "StatKey" });

            migrationBuilder.CreateIndex(
                name: "IX_ai_statistics_ProjectId_StatGroup_CreatedAt",
                table: "ai_statistics",
                columns: new[] { "ProjectId", "StatGroup", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_ai_statistics_UserId",
                table: "ai_statistics",
                column: "UserId");

            migrationBuilder.CreateIndex(
                name: "IX_ai_statistics_VideoId_StatGroup_CreatedAt",
                table: "ai_statistics",
                columns: new[] { "VideoId", "StatGroup", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_heatmaps_ProcessingJobId_TargetType_TargetId",
                table: "heatmaps",
                columns: new[] { "ProcessingJobId", "TargetType", "TargetId" });

            migrationBuilder.CreateIndex(
                name: "IX_heatmaps_ProjectId_GeneratedAt",
                table: "heatmaps",
                columns: new[] { "ProjectId", "GeneratedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_projects_OwnerUserId_CreatedAt",
                table: "projects",
                columns: new[] { "OwnerUserId", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_projects_OwnerUserId_Name",
                table: "projects",
                columns: new[] { "OwnerUserId", "Name" });

            migrationBuilder.AddForeignKey(
                name: "FK_processing_jobs_projects_ProjectId",
                table: "processing_jobs",
                column: "ProjectId",
                principalTable: "projects",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);

            migrationBuilder.AddForeignKey(
                name: "FK_videos_projects_ProjectId",
                table: "videos",
                column: "ProjectId",
                principalTable: "projects",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_processing_jobs_projects_ProjectId",
                table: "processing_jobs");

            migrationBuilder.DropForeignKey(
                name: "FK_videos_projects_ProjectId",
                table: "videos");

            migrationBuilder.DropTable(
                name: "action_predictions");

            migrationBuilder.DropTable(
                name: "ai_result_files");

            migrationBuilder.DropTable(
                name: "ai_statistics");

            migrationBuilder.DropTable(
                name: "heatmaps");

            migrationBuilder.DropTable(
                name: "projects");

            migrationBuilder.DropIndex(
                name: "IX_videos_ProjectId_UploadedAt",
                table: "videos");

            migrationBuilder.DropIndex(
                name: "IX_processing_jobs_ProjectId_CreatedAt",
                table: "processing_jobs");

            migrationBuilder.DropColumn(
                name: "ProjectId",
                table: "videos");

            migrationBuilder.DropColumn(
                name: "CsvDir",
                table: "processing_jobs");

            migrationBuilder.DropColumn(
                name: "ProjectId",
                table: "processing_jobs");
        }
    }
}
