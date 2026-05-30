export interface HeatmapData {
    id: string;
    videoId: string;
    playerPositions: Position[];
    intensity: IntensityMap;
    timestamp: number;
}

export interface Position {
    x: number;
    y: number;
    playerId: string;
    intensity: number;
}

export interface IntensityMap {
    [key: string]: number;
}

export interface HeatmapConfig {
    width: number;
    height: number;
    colorScheme: string[];
    gridSize: number;
}
