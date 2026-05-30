import supervision as sv
from sports.common.team import TeamClassifier
from collections import defaultdict, deque
from sports.configs.soccer import SoccerPitchConfiguration
from .frame_processing import Processor
from .heat_map import heatmap
from .mini_map import minimap
from .saver import saving
from .team_classification import team_classification
from .tiling import tiling
from .goalkeeper_classification import gk_cls
from .possession import possession_detector
from .event_detection import event_detector

class FootballAnalyzer(
    heatmap,
    minimap,
    team_classification,
    tiling,
    gk_cls,
    saving,
    Processor,
    possession_detector,
    event_detector
):
    def __init__(self, model, fps=30.0, device="cuda", field_model=None, debug=False):
        super().__init__(debug=debug, coordinate_scale=1.0)

        self.model = model
        self.field_model = field_model
        self.fps = fps
        self.pitch_config = SoccerPitchConfiguration()
        self.player_motion_history = defaultdict(lambda: deque(maxlen=3))
        self.centroid_frames = 0
        self.max_centroid_frames = 30
        self.team_0_centroid = None
        self.team_1_centroid = None

        self.heatmap_coordinates = defaultdict(list)
        self.player_team_history = defaultdict(lambda: deque(maxlen=25))
        self.coordinates = defaultdict(lambda: deque(maxlen=int(self.fps * 2)))
        self.detections_log = []
        self.ball_positions_log = []
        self.frame_states_log = []
        self.possession_control_df = None
        self.possession_gains_df = None
        self.possession_losses_df = None

        # Tuned possession parameters
        self.pz_radius = 1.18
        self.dz_radius = 1.75
        self.keep_possession_radius = 1.30
        self.duel_margin = 0.40

        # Legacy motion thresholds kept for compatibility / metadata
        self.direction_cos_threshold = 0.95
        self.speed_change_threshold = 0.20
        self.displacement_threshold = 0.30

        self.transformer = None
        self.view_transformer = None
        self.frame_count = 0
        self.update_interval = 5

        self.prev_positions = {}
        self.prev_speed_positions = {}
        self.prev_control_positions = {}

        self.last_valid_ball_pitch = None
        self.ball_missing_frames = 0
        self.max_ball_hold_frames = 1

        self.pitch = None

        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.65,
            lost_track_buffer=260,
            minimum_matching_threshold=0.85,
            frame_rate=fps,
            minimum_consecutive_frames=8
        )
        self.team_classifier = TeamClassifier(device=device)

        self.palette = sv.ColorPalette.from_hex(['#00BFFF', '#FF1493', "#EEFF00"])
        self.ellipse_annotator = sv.EllipseAnnotator(color=self.palette, thickness=2)
        self.label_annotator = sv.LabelAnnotator(
            color=self.palette,
            text_color=sv.Color.from_hex('#000000'),
            text_position=sv.Position.BOTTOM_CENTER
        )
        self.triangle_annotator = sv.TriangleAnnotator(
            color=sv.Color.from_hex("#FFFFFF"),
            base=25,
            height=21,
            outline_thickness=1
        )

    def set_field_model(self, field_model):
        self.field_model = field_model
