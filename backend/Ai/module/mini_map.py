import cv2
import numpy as np
import supervision as sv
from sports.annotators.soccer import draw_pitch, draw_points_on_pitch
from sports.common.view import ViewTransformer

class minimap:
    def _draw_player_ids_on_minimap(
        self,
        pitch,
        player_points,
        player_ids,
        config,
        text_color=(255, 255, 255),
        outline_color=(0, 0, 0),
        font_scale=0.75,
        thickness=2,
        offset_x=10,
        offset_y=-10
    ):
        if len(player_points) == 0 or len(player_ids) == 0:
            return pitch
    
        output = pitch.copy()
        h, w = output.shape[:2]
    
        vertices = np.array(config.vertices, dtype=np.float32)
        x_min, y_min = vertices.min(axis=0)
        x_max, y_max = vertices.max(axis=0)
    
        for (x, y), pid in zip(player_points, player_ids):
            px = int((x - x_min) / (x_max - x_min + 1e-6) * (w - 1))
            py = int((y - y_min) / (y_max - y_min + 1e-6) * (h - 1))
    
            text = str(pid)
            tx = px + offset_x
            ty = py + offset_y
    
            # outline أسود عشان يبقى واضح على أي خلفية
            cv2.putText(
                output,
                text,
                (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                outline_color,
                thickness + 2,
                cv2.LINE_AA
            )
    
            cv2.putText(
                output,
                text,
                (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                text_color,
                thickness,
                cv2.LINE_AA
            )
    
        return output   
    def draw_minimap(
        self,
        frame,
        ball,
        players,
        goalkeepers,
        keypoints,
        config,
        alpha=0.5,
        scale=0.28,
        show_player_ids=True
    ):
        # ================== INIT ==================
        if not hasattr(self, "transformer"):
            self.transformer = None
        if not hasattr(self, "frame_count"):
            self.frame_count = 0
        if not hasattr(self, "update_interval"):
            self.update_interval = 20
        if not hasattr(self, "prev_positions"):
            self.prev_positions = {}
        if not hasattr(self, "pitch"):
            self.pitch = None

        # self.frame_count += 1

        # ================== UPDATE TRANSFORMER ==================
        if keypoints is not None and len(keypoints.xy[0]) > 0:
            if self.transformer is None or self.frame_count % self.update_interval == 0:
                mask = keypoints.confidence[0] > 0.5

                if np.sum(mask) >= 4:
                    frame_points = keypoints.xy[0][mask]
                    pitch_points = np.array(config.vertices)[mask]

                    self.transformer = ViewTransformer(
                        source=frame_points,
                        target=pitch_points
                    )

        # لو مفيش transformer لسه → نرجع الفريم
        if self.transformer is None:
            return frame

        # ================== GET COORDINATES ==================
        ball_xy = ball.get_anchors_coordinates(sv.Position.BOTTOM_CENTER) if len(ball) > 0 else np.empty((0, 2))
        players_xy = players.get_anchors_coordinates(sv.Position.BOTTOM_CENTER) if len(players) > 0 else np.empty((0, 2))
        goalkeepers_xy = goalkeepers.get_anchors_coordinates(sv.Position.BOTTOM_CENTER) if len(goalkeepers) > 0 else np.empty((0, 2))

        # ================== TRANSFORM ==================
        if len(ball_xy) > 0:
            ball_xy = self.transformer.transform_points(ball_xy)

        if len(players_xy) > 0:
            players_xy = self.transformer.transform_points(players_xy)

        if len(goalkeepers_xy) > 0:
            goalkeepers_xy = self.transformer.transform_points(goalkeepers_xy)

        # ================== SMOOTHING (TRACKING) ==================
        smoothed_players = []
        if len(players_xy) > 0:
            for i, tid in enumerate(players.tracker_id):
                curr = players_xy[i]

                if tid in self.prev_positions:
                    prev = self.prev_positions[tid]
                    curr = 0.7 * prev + 0.3 * curr

                self.prev_positions[tid] = curr
                smoothed_players.append(curr)

            players_xy = np.array(smoothed_players)

        # goalkeepers smoothing (بنفس الـ tracker)
        smoothed_gk = []
        if len(goalkeepers_xy) > 0:
            for i, tid in enumerate(goalkeepers.tracker_id):
                curr = goalkeepers_xy[i]

                if tid in self.prev_positions:
                    prev = self.prev_positions[tid]
                    curr = 0.7 * prev + 0.3 * curr

                self.prev_positions[tid] = curr
                smoothed_gk.append(curr)

            goalkeepers_xy = np.array(smoothed_gk)

        # ball smoothing
        if len(ball_xy) > 0:
            if "ball" in self.prev_positions:
                ball_xy[0] = 0.8 * self.prev_positions["ball"] + 0.2 * ball_xy[0]

            self.prev_positions["ball"] = ball_xy[0]

        # ================== DRAW PITCH ==================
        if self.pitch is None:
            self.pitch = draw_pitch(config)

        pitch = self.pitch.copy()

        # ================== DRAW PLAYERS ==================
        if len(players_xy) > 0:
            pitch = draw_points_on_pitch(
                config=config,
                xy=players_xy[players.class_id == 0],
                face_color=sv.Color.from_hex('00BFFF'),
                edge_color=sv.Color.BLACK,
                radius=18,
                pitch=pitch
            )

            pitch = draw_points_on_pitch(
                config=config,
                xy=players_xy[players.class_id == 1],
                face_color=sv.Color.from_hex('FF1493'),
                edge_color=sv.Color.BLACK,
                radius=18,
                pitch=pitch
            )

        # ================== DRAW GOALKEEPERS ==================
        if len(goalkeepers_xy) > 0:
            pitch = draw_points_on_pitch(
                config=config,
                xy=goalkeepers_xy[goalkeepers.class_id == 0],
                face_color=sv.Color.from_hex('00BFFF'),
                edge_color=sv.Color.BLACK,
                radius=18,
                pitch=pitch
            )

            pitch = draw_points_on_pitch(
                config=config,
                xy=goalkeepers_xy[goalkeepers.class_id == 1],
                face_color=sv.Color.from_hex('FF1493'),
                edge_color=sv.Color.BLACK,
                radius=18,
                pitch=pitch
            )

        # ================== DRAW BALL (LAST) ==================
        if len(ball_xy) > 0:
            pitch = draw_points_on_pitch(
                config=config,
                xy=ball_xy,
                face_color=sv.Color.WHITE,
                edge_color=sv.Color.BLACK,
                radius=10,
                pitch=pitch
            )
        if show_player_ids and len(players_xy) > 0:
            pitch = self._draw_player_ids_on_minimap(
                pitch=pitch,
                player_points=players_xy,
                player_ids=players.tracker_id,
                config=config
            )            

        # ================== RESIZE ==================
        h, w = frame.shape[:2]
        ph, pw = pitch.shape[:2]

        new_w = int(w * scale)
        new_h = int(ph * (new_w / pw))

        pitch = cv2.resize(pitch, (new_w, new_h))

        # ================== POSITION (BOTTOM CENTER) ==================
        x1 = (w - new_w) // 2
        y1 = h - new_h - 20
        x2 = x1 + new_w
        y2 = y1 + new_h

        roi = frame[y1:y2, x1:x2]

        if roi.shape[:2] != pitch.shape[:2]:
            return frame

        # border
        cv2.rectangle(frame, (x1-2, y1-2), (x2+2, y2+2), (0, 0, 0), 2)

        # ================== BLEND ==================
        blended = cv2.addWeighted(roi, 1 - alpha, pitch, alpha, 0)
        frame[y1:y2, x1:x2] = blended

        return frame

