using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SA.Migrations
{
    /// <inheritdoc />
    public partial class AddUserSettingsDefaults : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("UPDATE user_settings SET ThemeMode = 'dark' WHERE ThemeMode IS NULL OR LTRIM(RTRIM(ThemeMode)) = ''");
            migrationBuilder.Sql("UPDATE user_settings SET StartPage = '/dashboard' WHERE StartPage IS NULL OR LTRIM(RTRIM(StartPage)) = ''");

            migrationBuilder.AlterColumn<string>(
                name: "ThemeMode",
                table: "user_settings",
                type: "nvarchar(20)",
                maxLength: 20,
                nullable: false,
                defaultValue: "dark",
                oldClrType: typeof(string),
                oldType: "nvarchar(20)",
                oldMaxLength: 20);

            migrationBuilder.AlterColumn<string>(
                name: "StartPage",
                table: "user_settings",
                type: "nvarchar(80)",
                maxLength: 80,
                nullable: false,
                defaultValue: "/dashboard",
                oldClrType: typeof(string),
                oldType: "nvarchar(80)",
                oldMaxLength: 80);

            migrationBuilder.AlterColumn<int>(
                name: "ConfidenceThreshold",
                table: "user_settings",
                type: "int",
                nullable: false,
                defaultValue: 80,
                oldClrType: typeof(int),
                oldType: "int");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterColumn<string>(
                name: "ThemeMode",
                table: "user_settings",
                type: "nvarchar(20)",
                maxLength: 20,
                nullable: false,
                oldClrType: typeof(string),
                oldType: "nvarchar(20)",
                oldMaxLength: 20,
                oldDefaultValue: "dark");

            migrationBuilder.AlterColumn<string>(
                name: "StartPage",
                table: "user_settings",
                type: "nvarchar(80)",
                maxLength: 80,
                nullable: false,
                oldClrType: typeof(string),
                oldType: "nvarchar(80)",
                oldMaxLength: 80,
                oldDefaultValue: "/dashboard");

            migrationBuilder.AlterColumn<int>(
                name: "ConfidenceThreshold",
                table: "user_settings",
                type: "int",
                nullable: false,
                oldClrType: typeof(int),
                oldType: "int",
                oldDefaultValue: 80);
        }
    }
}
