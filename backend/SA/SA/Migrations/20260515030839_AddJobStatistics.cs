using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SA.Migrations
{
    /// <inheritdoc />
    public partial class AddJobStatistics : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "job_statistics",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ProcessingJobId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    VideoId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    ModuleName = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    ModelName = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: true),
                    StatType = table.Column<string>(type: "nvarchar(80)", maxLength: 80, nullable: false),
                    StatsJson = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_job_statistics", x => x.Id);
                    table.ForeignKey(
                        name: "FK_job_statistics_processing_jobs_ProcessingJobId",
                        column: x => x.ProcessingJobId,
                        principalTable: "processing_jobs",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_job_statistics_videos_VideoId",
                        column: x => x.VideoId,
                        principalTable: "videos",
                        principalColumn: "Id");
                });

            migrationBuilder.CreateIndex(
                name: "IX_job_statistics_ModuleName_StatType",
                table: "job_statistics",
                columns: new[] { "ModuleName", "StatType" });

            migrationBuilder.CreateIndex(
                name: "IX_job_statistics_ProcessingJobId_StatType",
                table: "job_statistics",
                columns: new[] { "ProcessingJobId", "StatType" });

            migrationBuilder.CreateIndex(
                name: "IX_job_statistics_VideoId_StatType_CreatedAt",
                table: "job_statistics",
                columns: new[] { "VideoId", "StatType", "CreatedAt" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "job_statistics");
        }
    }
}
