import csv
import pandas as pd


class saving:
    def save_detections_csv(self, csv_path):
        with open(csv_path, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["frame_index", "x1", "y1", "x2", "y2", "confidence", "class_id", "tracker_id"])
            for fi, frame_log in enumerate(self.detections_log):
                for det in frame_log["detections"]:
                    x1, y1, x2, y2 = det["xyxy"]
                    writer.writerow([fi, x1, y1, x2, y2, det["confidence"], det["class_id"], det["tracker_id"]])
    def save_ball_positions_csv(self, csv_path):
        df = pd.DataFrame(self.ball_positions_log)
        df.to_csv(csv_path, index=False)

    def save_frame_states_csv(self, csv_path):
        df = pd.DataFrame(self.frame_states_log)
        df.to_csv(csv_path, index=False)

    def save_possession_outputs(self, control_csv_path, gains_csv_path, losses_csv_path):
        if (
            self.possession_control_df is None
            or self.possession_gains_df is None
            or self.possession_losses_df is None
            or self.possession_control_df.empty
        ):
            self.compute_possession()

        self.possession_control_df.to_csv(control_csv_path, index=False)
        self.possession_gains_df.to_csv(gains_csv_path, index=False)
        self.possession_losses_df.to_csv(losses_csv_path, index=False)         
    def save_player_positions_csv(self, csv_path):
        df = pd.DataFrame(getattr(self, "player_positions_log", []))
        df.to_csv(csv_path, index=False)
    
    def save_event_outputs(self, events_csv_path, dead_ball_csv_path=None, transitions_csv_path=None):
        if getattr(self, "events_df", None) is None:
            self.compute_events()
    
        self.events_df.to_csv(events_csv_path, index=False)
    
        if dead_ball_csv_path is not None:
            self.dead_ball_intervals_df.to_csv(dead_ball_csv_path, index=False)
    
        if transitions_csv_path is not None:
            self.event_transitions_df.to_csv(transitions_csv_path, index=False)
