export interface Report {
    id: string;
    title: string;
    description: string;
    type: ReportType;
    createdDate: Date;
    status: ReportStatus;
    data: any;
    format: ReportFormat;
}

export enum ReportType {
    PERFORMANCE = 'performance',
    TEAM_ANALYSIS = 'team-analysis',
    PLAYER_STATS = 'player-stats',
    MATCH_SUMMARY = 'match-summary'
}

export enum ReportStatus {
    GENERATING = 'generating',
    READY = 'ready',
    ERROR = 'error'
}

export enum ReportFormat {
    PDF = 'pdf',
    EXCEL = 'excel',
    JSON = 'json'
}

export interface ReportConfig {
    type: ReportType;
    dateRange?: { start: Date; end: Date };
    filters?: Record<string, any>;
    format: ReportFormat;
}
