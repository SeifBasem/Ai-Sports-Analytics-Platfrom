export interface AnalyticsData {
    overview: OverviewMetrics;
    charts: ChartData[];
    insights: Insight[];
}

export interface OverviewMetrics {
    totalVideos: number;
    totalAnalysis: number;
    accuracy: number;
    processingTime: number;
}

export interface ChartData {
    id: string;
    type: ChartType;
    title: string;
    data: DataPoint[];
}

export enum ChartType {
    LINE = 'line',
    BAR = 'bar',
    PIE = 'pie',
    AREA = 'area'
}

export interface DataPoint {
    label: string;
    value: number;
    color?: string;
}

export interface Insight {
    id: string;
    title: string;
    description: string;
    category: string;
    importance: 'high' | 'medium' | 'low';
}

export interface Metric {
    label: string;
    value: number;
    unit?: string;
    trend?: number;
}
