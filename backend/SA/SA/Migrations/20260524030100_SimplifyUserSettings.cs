using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SA.Migrations
{
    /// <inheritdoc />
    public partial class SimplifyUserSettings : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "AnalysisFinishedAlerts",
                table: "user_settings");

            migrationBuilder.DropColumn(
                name: "AutoSaveReports",
                table: "user_settings");

            migrationBuilder.DropColumn(
                name: "DataSharing",
                table: "user_settings");

            migrationBuilder.DropColumn(
                name: "EmailAlerts",
                table: "user_settings");

            migrationBuilder.DropColumn(
                name: "WeeklyReport",
                table: "user_settings");

            migrationBuilder.AddColumn<string>(
                name: "StartPage",
                table: "user_settings",
                type: "nvarchar(80)",
                maxLength: 80,
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "StartPage",
                table: "user_settings");

            migrationBuilder.AddColumn<bool>(
                name: "AnalysisFinishedAlerts",
                table: "user_settings",
                type: "bit",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<bool>(
                name: "AutoSaveReports",
                table: "user_settings",
                type: "bit",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<bool>(
                name: "DataSharing",
                table: "user_settings",
                type: "bit",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<bool>(
                name: "EmailAlerts",
                table: "user_settings",
                type: "bit",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<bool>(
                name: "WeeklyReport",
                table: "user_settings",
                type: "bit",
                nullable: false,
                defaultValue: false);
        }
    }
}
