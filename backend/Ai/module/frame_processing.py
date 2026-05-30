import numpy as np
import supervision as sv
import pandas as pd
from sports.common.view import ViewTransformer
from collections import deque


PLAYER_ID = 0
REFEREE_ID = 1
BALL_ID = 2
GOALKEEPER_ID = 3



class Processor:
    def _nms(self, boxes, scores, iou_threshold=0.45):
        if len(boxes) == 0:
            return np.array([], dtype=int)

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []

        while order.size > 0:
            i = order[0]
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]

        return np.array(keep, dtype=int)
    def _apply_nms_to_detections(self, detections, iou_threshold=0.55):
        if len(detections) == 0:
            return detections

        keep = self._nms(
            boxes=detections.xyxy,
            scores=detections.confidence,
            iou_threshold=iou_threshold
        )

        return detections[keep]
    def _smooth_detection_boxes(self, detections, alpha=0.25):
      if not hasattr(self, "prev_boxes"):
          self.prev_boxes = {}

      if len(detections) == 0 or detections.tracker_id is None:
          return detections

      smoothed_xyxy = detections.xyxy.copy()

      for i, tid in enumerate(detections.tracker_id):
          if tid is None or int(tid) < 0:
              continue

          key = int(tid)
          curr = detections.xyxy[i].astype(float)

          if key in self.prev_boxes:
              prev = self.prev_boxes[key]
              curr = (1 - alpha) * prev + alpha * curr

          self.prev_boxes[key] = curr
          smoothed_xyxy[i] = curr

      detections.xyxy = smoothed_xyxy
      return detections    
    def normalize_tracker_id(self, dets):
        if dets.tracker_id is None:
            dets.tracker_id = np.full(len(dets), -1, dtype=object)
        elif not isinstance(dets.tracker_id, np.ndarray):
            dets.tracker_id = np.array(dets.tracker_id, dtype=object)
        else:
            dets.tracker_id = dets.tracker_id.astype(object)
        return dets

    def update_dynamic_transformer(self, frame):
        if not hasattr(self, "field_model") or self.field_model is None:
            return None, False

        results = self.field_model.predict(frame, conf=0.3, verbose=False)[0]
        keypoints = None
        updated = False

        if hasattr(results, "keypoints") and results.keypoints is not None:
            xy = results.keypoints.xy
            if xy is not None:
                xy = xy.cpu().numpy()
                if len(xy.shape) == 3 and xy.shape[0] > 0 and xy.shape[2] == 2:
                    keypoints = sv.KeyPoints(
                        xy=xy,
                        confidence=results.keypoints.conf.cpu().numpy()
                    )

        if keypoints is not None and len(keypoints.xy[0]) > 0:
            if self.transformer is None or self.frame_count % self.update_interval == 0:
                mask = keypoints.confidence[0] > 0.5
                if np.sum(mask) >= 4:
                    frame_points = keypoints.xy[0][mask]
                    pitch_points = np.array(self.pitch_config.vertices)[mask]
                    self.transformer = ViewTransformer(
                        source=frame_points,
                        target=pitch_points
                    )
                    updated = True

        return keypoints, updated

    def _adjust_boxes_by_offset(self, boxes_xyxy, offset):
        x1_off, y1_off, _, _ = offset
        boxes = boxes_xyxy.copy()
        boxes[:, 0] += x1_off
        boxes[:, 1] += y1_off
        boxes[:, 2] += x1_off
        boxes[:, 3] += y1_off
        return boxes

    def stabilize_team_ids(self, players, predictions):
        stable_ids = []
        for tracker_id, pred in zip(players.tracker_id, predictions):
            self.player_team_history[tracker_id].append(int(pred))
            history = list(self.player_team_history[tracker_id])
            stable_team = max(set(history), key=history.count)
            stable_ids.append(stable_team)
        return np.array(stable_ids, dtype=int)

    def _smooth_point(self, key, point, alpha=0.3, store_name="prev_control_positions"):
        if not hasattr(self, store_name):
            setattr(self, store_name, {})
        store = getattr(self, store_name)

        point = np.array(point, dtype=np.float32)
        if key in store:
            point = (1.0 - alpha) * store[key] + alpha * point
        store[key] = point
        return point

    def _smooth_player_pitch_points(self, players, points):
        if len(players) == 0 or len(points) == 0:
            return points

        smoothed = []
        for tracker_id, point in zip(players.tracker_id, points):
            smoothed.append(self._smooth_point(int(tracker_id), point, alpha=0.6, store_name="prev_control_positions"))
        return np.array(smoothed, dtype=np.float32)
    def _smooth_goalkeeper_pitch_points(self, goalkeepers, points):
        if len(goalkeepers) == 0 or len(points) == 0:
            return points

        smoothed = []
        for tracker_id, point in zip(goalkeepers.tracker_id, points):
            smoothed.append(
                self._smooth_point(
                    tracker_id,
                    point,
                    alpha=0.4,
                    store_name="prev_control_positions"
                )
            )
        return np.array(smoothed, dtype=np.float32)
    def _smooth_ball_pitch_point(self, point):
        return self._smooth_point("ball_control", point, alpha=0.25, store_name="prev_control_positions")

    def _get_ball_pitch_position(self, ball):
        if self.transformer is None and self.view_transformer is None:
            return np.nan, np.nan, False
        ball_pitch_x = np.nan
        ball_pitch_y = np.nan
        used_fallback = False

        if len(ball) > 0:
            ball_points = ball.get_anchors_coordinates(anchor=sv.Position.BOTTOM_CENTER)
            if len(ball_points) > 0:
                if self.transformer is not None:
                    ball_points = self.transformer.transform_points(ball_points)
                elif self.view_transformer is not None:
                    ball_points = self.view_transformer.transform_points(ball_points)

                if len(ball_points) > 0:
                    smoothed_ball = self._smooth_ball_pitch_point(ball_points[0])
                    ball_pitch_x = float(smoothed_ball[0])
                    ball_pitch_y = float(smoothed_ball[1])
                    self.last_valid_ball_pitch = np.array([ball_pitch_x, ball_pitch_y], dtype=np.float32)
                    self.ball_missing_frames = 0
                    return ball_pitch_x, ball_pitch_y, used_fallback

        if hasattr(self, "last_valid_ball_pitch") and self.last_valid_ball_pitch is not None:
            if not hasattr(self, "ball_missing_frames"):
                self.ball_missing_frames = 0
            self.ball_missing_frames += 1
            if self.ball_missing_frames <= getattr(self, "max_ball_hold_frames", 2):
                ball_pitch_x = float(self.last_valid_ball_pitch[0])
                ball_pitch_y = float(self.last_valid_ball_pitch[1])
                used_fallback = True

        return ball_pitch_x, ball_pitch_y, used_fallback

    def process_frame(self, frame, use_tiling=True, tile_size=(640, 640), overlap=0.2, conf=0.3):
        if frame is None:
            return frame

        self.frame_count += 1
        keypoints, _ = self.update_dynamic_transformer(frame)

        if use_tiling:
            results = self.model.predict(
                frame,
                conf=0.7,
                classes=[PLAYER_ID, REFEREE_ID, GOALKEEPER_ID],
                verbose=False
            )[0]
            detections = sv.Detections(
                xyxy=results.boxes.xyxy.cpu().numpy(),
                confidence=results.boxes.conf.cpu().numpy(),
                class_id=results.boxes.cls.cpu().numpy().astype(int)
            )

            tiles = self.tile_frame(frame, tile_size=tile_size, overlap=overlap)
            ball_boxes = []
            ball_scores = []

            for offset, crop in tiles:
                if crop is None or crop.size == 0:
                    continue
                ball_results = self.model.predict(crop, conf=conf, classes=[BALL_ID], verbose=False)[0]
                boxes = ball_results.boxes.xyxy.cpu().numpy()
                scores = ball_results.boxes.conf.cpu().numpy()
                if boxes.size == 0:
                    continue
                boxes = self._adjust_boxes_by_offset(boxes, offset)
                ball_boxes.append(boxes)
                ball_scores.append(scores)

            if len(ball_boxes) > 0:
                ball_boxes = np.vstack(ball_boxes)
                ball_scores = np.concatenate(ball_scores)
                keep = self._nms(ball_boxes, ball_scores, 0.45)
                ball = sv.Detections(
                    xyxy=ball_boxes[keep],
                    confidence=ball_scores[keep],
                    class_id=np.full(len(keep), BALL_ID)
                )
                if len(ball) > 1:
                    best_idx = int(np.argmax(ball.confidence))
                    ball = sv.Detections(
                        xyxy=ball.xyxy[best_idx:best_idx+1],
                        confidence=ball.confidence[best_idx:best_idx+1],
                        class_id=ball.class_id[best_idx:best_idx+1],
                    )
            else:
                ball = sv.Detections(
                    xyxy=np.zeros((0, 4)),
                    confidence=np.zeros((0,)),
                    class_id=np.zeros((0,), dtype=int)
                )
        else:
            results = self.model.predict(frame, conf=conf, verbose=False)[0]
            detections = sv.Detections(
                xyxy=results.boxes.xyxy.cpu().numpy(),
                confidence=results.boxes.conf.cpu().numpy(),
                class_id=results.boxes.cls.cpu().numpy().astype(int)
            )
            ball = detections[detections.class_id == BALL_ID]
            ball.xyxy = sv.pad_boxes(xyxy=ball.xyxy, px=10)
            if len(ball) > 1:
                    best_idx = int(np.argmax(ball.confidence))
                    ball = sv.Detections(
                        xyxy=ball.xyxy[best_idx:best_idx+1],
                        confidence=ball.confidence[best_idx:best_idx+1],
                        class_id=ball.class_id[best_idx:best_idx+1],
                    )

        players = detections[detections.class_id == PLAYER_ID]
        goalkeepers = detections[detections.class_id == GOALKEEPER_ID]
        referees = detections[detections.class_id == REFEREE_ID]
        players = self._apply_nms_to_detections(players, iou_threshold=0.55)
        goalkeepers = self._apply_nms_to_detections(goalkeepers, iou_threshold=0.55)
        referees = self._apply_nms_to_detections(referees, iou_threshold=0.55)
        if len(players) > 0:
            players = self.tracker.update_with_detections(players)
            players = self._smooth_detection_boxes(players, alpha=0.20)
            player_crops = [sv.crop_image(frame, xyxy) for xyxy in players.xyxy]
            raw_team_preds = self.team_classifier.predict(player_crops)
            players.class_id = self.stabilize_team_ids(players, raw_team_preds)
        if len(goalkeepers) > 0:
            if len(players) > 0:
                goalkeepers.class_id = self.resolve_goalkeepers_team_id(players, goalkeepers)
            else:
                goalkeepers.class_id = np.zeros(len(goalkeepers), dtype=int)

            goalkeepers.tracker_id = np.array(
                [f"GK_{int(team_id)}" for team_id in goalkeepers.class_id],
                dtype=object
            )

        if len(referees) > 0:
            referees.class_id = np.full(len(referees), 2, dtype=int)

        players = self.normalize_tracker_id(players)
        goalkeepers = self.normalize_tracker_id(goalkeepers)
        referees = self.normalize_tracker_id(referees)
        ball = self.normalize_tracker_id(ball)

        frame_index = self.frame_count - 1
        time_sec = frame_index / self.fps if self.fps > 0 else 0.0

        points = players.get_anchors_coordinates(anchor=sv.Position.BOTTOM_CENTER)
        has_pitch_transform = self.transformer is not None or self.view_transformer is not None
        if len(points) > 0:
            if self.transformer is not None:
                points = self.transformer.transform_points(points)
            elif self.view_transformer is not None:
                points = self.view_transformer.transform_points(points)

        player_pitch_df = pd.DataFrame(columns=["tracker_id", "team_id", "x", "y"])
        control_points = np.empty((0, 2), dtype=np.float32)

        if len(players) > 0 and len(points) > 0:
            control_points = self._smooth_player_pitch_points(players, points)
            player_pitch_df = pd.DataFrame({
                "tracker_id": [int(tid) if tid is not None else None for tid in players.tracker_id],
                "team_id": [int(cid) for cid in players.class_id],
                "x": (control_points[:, 0]/ 100.0).astype(float),
                "y": (control_points[:, 1]/ 100.0).astype(float),
            })
        goalkeeper_pitch_df = pd.DataFrame(columns=["tracker_id", "team_id", "x", "y"])

        if len(goalkeepers) > 0:
            gk_points = goalkeepers.get_anchors_coordinates(anchor=sv.Position.BOTTOM_CENTER)

            if len(gk_points) > 0:
                if self.transformer is not None:
                    gk_points = self.transformer.transform_points(gk_points)
                elif self.view_transformer is not None:
                    gk_points = self.view_transformer.transform_points(gk_points)
            gk_points = self._smooth_goalkeeper_pitch_points(goalkeepers, gk_points)

            goalkeeper_pitch_df = pd.DataFrame({
                "tracker_id": [tid for tid in goalkeepers.tracker_id],
                "team_id": [int(cid) for cid in goalkeepers.class_id],
                "x": (gk_points[:, 0]/ 100.0).astype(float),
                "y": (gk_points[:, 1]/ 100.0).astype(float),
            })
        control_candidates_df = pd.concat([player_pitch_df, goalkeeper_pitch_df],ignore_index=True)
        if not hasattr(self, "player_positions_log"):
            self.player_positions_log = []

        for _, row in control_candidates_df.iterrows():
            self.player_positions_log.append({
                "frame": frame_index,
                "time": float(time_sec),
                "tracker_id": row["tracker_id"],
                "team_id": int(row["team_id"]) if not pd.isna(row["team_id"]) else None,
                "x": float(row["x"]),
                "y": float(row["y"]),
                "is_goalkeeper": str(row["tracker_id"]).startswith("GK_"),
            })

        ball_pitch_x, ball_pitch_y, ball_used_fallback = self._get_ball_pitch_position(ball)
        ball_pitch_x_m = ball_pitch_x / 100.0 if not np.isnan(ball_pitch_x) else np.nan
        ball_pitch_y_m = ball_pitch_y / 100.0 if not np.isnan(ball_pitch_y) else np.nan
        self.ball_positions_log.append({
            "frame": frame_index,
            "time": float(time_sec),
            "ball_x": ball_pitch_x_m,
            "ball_y": ball_pitch_y_m,
            "ball_visible": len(ball) > 0,
            "ball_used_fallback": bool(ball_used_fallback),
            "ball_confidence": float(ball.confidence[0]) if len(ball) > 0 else 0.0,
        })

        if (has_pitch_transform
                    and not ball_used_fallback
                    and not np.isnan(ball_pitch_x_m)
                    and not np.isnan(ball_pitch_y_m)
                ):
            if not control_candidates_df.empty:
                control_state = self.classify_control_frame(
                    ball_x=ball_pitch_x_m,
                    ball_y=ball_pitch_y_m,
                    players_df=control_candidates_df,
                    pz_radius=self.pz_radius,
                    dz_radius=self.dz_radius,
                    keep_possession_radius=self.keep_possession_radius,
                    duel_margin=self.duel_margin,
                )
            else:
                control_state = self._fallback_to_last_control()
        else:
            control_state = self._fallback_to_last_control()
        controller_id = control_state["controller_id"]

        if isinstance(controller_id, str) and controller_id.startswith("GK_"):
            controller_label = "GK"
        else:
            controller_label = controller_id
        self.frame_states_log.append({
            "frame": frame_index,
            "ball_control": control_state["ball_control"],
            "controller_id": control_state["controller_id"],      # داخلي للتحليل
            "controller_label": controller_label,                 # عرض بشري
            "controller_team": control_state["controller_team"],
            "dist_to_ball": control_state["dist_to_ball"],
            "confidence_score": control_state.get("confidence_score", 0.0)
        })
        self.frame_states_log[-1].update({
            "num_players": int(len(players)),
            "num_goalkeepers": int(len(goalkeepers)),
            "num_referees": int(len(referees)),
            "has_pitch_transform": bool(has_pitch_transform),
            "ball_visible": bool(len(ball) > 0),
            "ball_used_fallback": bool(ball_used_fallback),
            "ball_confidence": float(ball.confidence[0]) if len(ball) > 0 else 0.0,
        })
        # Movement/speed logging and heatmap should use the real transformed player points, not control-smoothed points.
        for tracker_id, (x, y) in zip(players.tracker_id, points):
            curr = np.array([float(x), float(y)], dtype=np.float32)
            if tracker_id in self.prev_speed_positions:
                prev = self.prev_speed_positions[tracker_id]
                curr = 0.85 * prev + 0.15 * curr
            self.prev_speed_positions[tracker_id] = curr
            self.coordinates[tracker_id].append((float(curr[0]), float(curr[1])))
            self.heatmap_coordinates[tracker_id].append((float(curr[0]), float(curr[1])))

        player_labels = []
        for tracker_id in players.tracker_id:
            coords = self.coordinates[tracker_id]
            window = max(5, int(self.fps / 2))
            if len(coords) < window + 1:
                player_labels.append(f"#{tracker_id}")
                continue
            coordinate_start = coords[-window - 1]
            coordinate_end = coords[-1]
            distance = np.hypot(
                coordinate_end[0] - coordinate_start[0],
                coordinate_end[1] - coordinate_start[1]
            )
            time_window = window / self.fps
            speed = (distance / time_window * 0.036) if time_window > 0 else 0
            player_labels.append(f"#{tracker_id} {int(speed)} km/h")

        gk_labels = [f"{tid}" for tid in goalkeepers.tracker_id]
        ref_labels = ["REF"] * len(referees)

        all_dets = sv.Detections.merge([players, goalkeepers, referees])
        all_dets.class_id = all_dets.class_id.astype(int)
        labels = player_labels + gk_labels + ref_labels

        annotated_frame = self.ellipse_annotator.annotate(frame, all_dets)
        annotated_frame = self.label_annotator.annotate(annotated_frame, all_dets, labels=labels)
        annotated_frame = self.triangle_annotator.annotate(annotated_frame, ball)

        annotated_frame = self.draw_minimap(
            frame=annotated_frame,
            ball=ball,
            players=players,
            goalkeepers=goalkeepers,
            keypoints=keypoints,
            config=self.pitch_config
        )

        frame_log = {
                "frame": frame_index,
                "frame_shape": frame.shape[:2],
                "detections": []
            }

        combined_tracker_ids = (
            [int(tid) if tid is not None else None for tid in players.tracker_id] +
            [tid if tid is not None else None for tid in goalkeepers.tracker_id] +
            [int(tid) if tid is not None else None for tid in referees.tracker_id]
        )

        for i, box in enumerate(all_dets.xyxy):
            entry = {
                "xyxy": box.tolist(),
                "confidence": float(all_dets.confidence[i]),
                "class_id": int(all_dets.class_id[i]),
                "tracker_id": combined_tracker_ids[i] if i < len(combined_tracker_ids) else None,
            }
            frame_log["detections"].append(entry)

        self.detections_log.append(frame_log)
        if not hasattr(self, "frame_buffer"):
            self.frame_buffer = deque(maxlen=int(self.fps * 6))

        self.frame_buffer.append({
                "frame": frame_index,
                "image": frame.copy(),
                "annotated": annotated_frame.copy(),
            })

        return annotated_frame