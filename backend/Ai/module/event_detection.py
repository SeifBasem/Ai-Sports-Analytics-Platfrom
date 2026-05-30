import numpy as np
import pandas as pd


class event_detector:
    def compute_events(self):
        if (self.possession_control_df is None or self.possession_gains_df is None or self.possession_losses_df is None):
            control_df, gains_df, losses_df = self.compute_possession()
        else:
            control_df = self.possession_control_df
            gains_df = self.possession_gains_df
            losses_df = self.possession_losses_df

        frames_df = pd.DataFrame(self.ball_positions_log)
        players_df = pd.DataFrame(getattr(self, "player_positions_log", []))
    
        events_df, dead_df, transitions_df = self.run_event_detection(
            control_df=control_df,
            gains_df=gains_df,
            losses_df=losses_df,
            frames_df=frames_df,
            players_df=players_df,
        )
    
        self.events_df = events_df
        self.dead_ball_intervals_df = dead_df
        self.event_transitions_df = transitions_df
    
        return events_df, dead_df, transitions_df
    def _unit_to_meter(self):
        return float(getattr(self, "coordinate_scale", 1.0))
    def _norm_player_id(self, pid):
        if pid is None or pd.isna(pid):
            return None
    
        s = str(pid)
    
        if s.startswith("GK_"):
            return s
    
        try:
            return str(int(float(pid)))
        except Exception:
            return s
    
    
    def _same_player(self, a, b):
        return self._norm_player_id(a) == self._norm_player_id(b)        
    def _ball_path_distance(self, frames_lookup, f_start, f_end):
        if pd.isna(f_start) or pd.isna(f_end) or frames_lookup.empty:
            return np.nan
    
        f_start = int(f_start)
        f_end = int(f_end)
    
        points = []
    
        for f in range(f_start, f_end + 1):
            if f not in frames_lookup.index:
                continue
    
            row = frames_lookup.loc[f]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[-1]
    
            x = row["ball_x"]
            y = row["ball_y"]
    
            if pd.isna(x) or pd.isna(y):
                continue
    
            # تجاهل أي نقطة خارج الملعب بهامش بسيط
            if not self._is_inside_pitch(float(x), float(y), margin=5.0):
                continue
    
            points.append((float(x), float(y)))
    
        if len(points) < 2:
            return np.nan
    
        total = 0.0
        valid_steps = 0
        big_jump_seen = False
    
        for p1, p2 in zip(points[:-1], points[1:]):
            step = float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))
    
            if step < 0.15:
                continue
    
            if step > 12.0:
                big_jump_seen = True
                continue
    
            total += step
            valid_steps += 1
    
        direct = float(np.hypot(
            points[-1][0] - points[0][0],
            points[-1][1] - points[0][1],
        ))
    
        # لو مفيش خطوات صالحة وكان فيه jump كبير، ماينفعش نرجع direct
        if valid_steps == 0 and big_jump_seen:
            return np.nan
    
        if valid_steps == 0:
            return direct if direct <= 12.0 else np.nan
    
        # رجّع path الحقيقي، ولو direct أكبر بسبب مسار نضيف ومش glitch خليه
        if not big_jump_seen:
            return max(total, direct)
    
        return total
    def _ball_flight_after_frame(self, frames_lookup, start_frame, window_frames=None):
        if frames_lookup.empty or pd.isna(start_frame):
            return {
                "distance": np.nan,
                "end_frame": np.nan,
                "end_x": np.nan,
                "end_y": np.nan,
            }
    
        if window_frames is None:
            window_frames = int(self.fps * 2.5)
    
        start_frame = int(start_frame)
        sx, sy = self._frame_ball_xy(frames_lookup, start_frame)
    
        if pd.isna(sx) or pd.isna(sy):
            return {
                "distance": np.nan,
                "end_frame": np.nan,
                "end_x": np.nan,
                "end_y": np.nan,
            }
    
        sx, sy = float(sx), float(sy)
    
        if not self._is_inside_pitch(sx, sy, margin=5.0):
            return {
                "distance": np.nan,
                "end_frame": np.nan,
                "end_x": np.nan,
                "end_y": np.nan,
            }
    
        max_dist = 0.0
        best_frame = start_frame
        best_x, best_y = sx, sy
    
        prev_x, prev_y = sx, sy
    
        for f in range(start_frame + 1, start_frame + window_frames + 1):
            if f not in frames_lookup.index:
                continue
    
            x, y = self._frame_ball_xy(frames_lookup, f)
    
            if pd.isna(x) or pd.isna(y):
                continue
    
            x, y = float(x), float(y)
    
            if not self._is_inside_pitch(x, y, margin=5.0):
                continue
    
            step = self._dist(prev_x, prev_y, x, y)
    
            # tracking glitch guard
            if not pd.isna(step) and step > 12.0:
                continue
    
            direct_dist = self._dist(sx, sy, x, y)
    
            if not pd.isna(direct_dist) and direct_dist > max_dist:
                max_dist = direct_dist
                best_frame = f
                best_x, best_y = x, y
    
            prev_x, prev_y = x, y
    
        if max_dist <= 0:
            return {
                "distance": np.nan,
                "end_frame": np.nan,
                "end_x": np.nan,
                "end_y": np.nan,
            }
    
        return {
            "distance": float(max_dist),
            "end_frame": int(best_frame),
            "end_x": float(best_x),
            "end_y": float(best_y),
        }        
    def _max_ball_distance_after_frame(self, start_frame, window_frames=None):
        frames_lookup = getattr(self, "_event_frames_lookup", pd.DataFrame())
        if frames_lookup.empty or pd.isna(start_frame):
            return np.nan
    
        if window_frames is None:
            window_frames = int(self.fps * 2.5)
    
        start_frame = int(start_frame)
        sx, sy = self._frame_ball_xy(frames_lookup, start_frame)
    
        if pd.isna(sx) or pd.isna(sy):
            return np.nan
    
        if not self._is_inside_pitch(float(sx), float(sy), margin=5.0):
            return np.nan
    
        max_dist = 0.0
        prev = (float(sx), float(sy))
    
        for f in range(start_frame + 1, start_frame + window_frames + 1):
            if f not in frames_lookup.index:
                continue
    
            x, y = self._frame_ball_xy(frames_lookup, f)
    
            if pd.isna(x) or pd.isna(y):
                continue
    
            x, y = float(x), float(y)
    
            if not self._is_inside_pitch(x, y, margin=5.0):
                continue
    
            step = self._dist(prev[0], prev[1], x, y)
    
            if not pd.isna(step) and step > 12.0:
                continue
    
            d = self._dist(sx, sy, x, y)
            if not pd.isna(d):
                max_dist = max(max_dist, d)
    
            prev = (x, y)
    
        return max_dist if max_dist > 0 else np.nan

    def _is_referee_id(self, tracker_id):
        """
        Returns True if the tracker id belongs to a referee-like object.
        """
        if tracker_id is None or pd.isna(tracker_id):
            return False
    
        return str(tracker_id).upper().startswith("REF")    
    def _has_notable_speed_change_at_pass(self, control_df, frame):
        """
        Returns speed features around a release frame.
        Used for pass/shot speed proxy.
        """
    
        result = {
            "notable_speed_change": False,
            "speed_delta": np.nan,
            "speed_in": np.nan,
            "speed_out": np.nan,
            "ball_speed": np.nan,
            "reason": None,
        }
    
        if control_df is None or control_df.empty or pd.isna(frame):
            return result
    
        if "frame" not in control_df.columns:
            return result
    
        control = control_df.copy()
        control["frame"] = pd.to_numeric(control["frame"], errors="coerce")
        control = control.dropna(subset=["frame"])
    
        if control.empty:
            return result
    
        frame = int(frame)
        window = int(getattr(self, "speed_change_lookup_window_frames", 2))
    
        near = control[
            (control["frame"] >= frame - window)
            & (control["frame"] <= frame + window)
        ].sort_values("frame")
    
        if near.empty:
            return result
    
        row = near.iloc[-1]
    
        speed_delta = pd.to_numeric(row.get("speed_delta", np.nan), errors="coerce")
        speed_in = pd.to_numeric(row.get("speed_in", np.nan), errors="coerce")
        speed_out = pd.to_numeric(row.get("speed_out", np.nan), errors="coerce")
        ball_speed = pd.to_numeric(row.get("ball_speed", np.nan), errors="coerce")
    
        result["speed_delta"] = speed_delta
        result["speed_in"] = speed_in
        result["speed_out"] = speed_out
        result["ball_speed"] = ball_speed
    
        min_abs_delta = getattr(self, "notable_min_speed_delta_mps", 2.0)
        min_out_speed = getattr(self, "notable_min_out_speed_mps", 6.0)
        min_ratio = getattr(self, "notable_min_speed_ratio", 1.50)
    
        checks = []
    
        if not pd.isna(speed_delta) and abs(float(speed_delta)) >= min_abs_delta:
            checks.append("abs_speed_delta")
    
        if not pd.isna(speed_out) and float(speed_out) >= min_out_speed:
            checks.append("high_speed_out")
    
        if (
            not pd.isna(speed_in)
            and not pd.isna(speed_out)
            and float(speed_in) > 0.1
            and float(speed_out) / float(speed_in) >= min_ratio
        ):
            checks.append("speed_ratio_jump")
    
        if checks:
            result["notable_speed_change"] = True
            result["reason"] = "+".join(checks)
    
        return result
    def _get_ball_xy_from_sources(self, frame, frames_lookup=None, control_lookup=None):
        """
        Get ball x/y at a frame.
    
        Priority:
        1. frames_lookup: from frames_df / ball_positions_log
        2. control_lookup: from possession_control_df if it contains ball_x/ball_y
           or ball_x_smooth/ball_y_smooth
        """
    
        if pd.isna(frame):
            return np.nan, np.nan
    
        frame = int(frame)
    
        # 1) Try frames lookup first
        if frames_lookup is not None and not frames_lookup.empty:
            if frame in frames_lookup.index:
                row = frames_lookup.loc[frame]
    
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]
    
                x = row.get("ball_x", np.nan)
                y = row.get("ball_y", np.nan)
    
                if not pd.isna(x) and not pd.isna(y):
                    return float(x), float(y)
    
        # 2) Try control lookup
        if control_lookup is not None and not control_lookup.empty:
            if frame in control_lookup.index:
                row = control_lookup.loc[frame]
    
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]
    
                if "ball_x" in row.index and "ball_y" in row.index:
                    x = row.get("ball_x", np.nan)
                    y = row.get("ball_y", np.nan)
                elif "ball_x_smooth" in row.index and "ball_y_smooth" in row.index:
                    x = row.get("ball_x_smooth", np.nan)
                    y = row.get("ball_y_smooth", np.nan)
                else:
                    x, y = np.nan, np.nan
    
                if not pd.isna(x) and not pd.isna(y):
                    return float(x), float(y)
    
        return np.nan, np.nan    
    def _control_features_at_frame(self, control_df, frame):
        if control_df is None or control_df.empty or pd.isna(frame):
            return {}
    
        hit = control_df[control_df["frame"] == int(frame)]
        if hit.empty:
            return {}
    
        r = hit.iloc[0]
        return {
            "ball_speed": r.get("ball_speed", np.nan),
            "speed_in": r.get("speed_in", np.nan),
            "speed_out": r.get("speed_out", np.nan),
            "speed_delta": r.get("speed_delta", np.nan),
            "ball_displacement": r.get("ball_displacement", np.nan),
        }
        
    def _point_to_segment_distance(self, px, py, ax, ay, bx, by):
        if any(pd.isna(v) for v in [px, py, ax, ay, bx, by]):
            return np.nan
    
        px, py = float(px), float(py)
        ax, ay = float(ax), float(ay)
        bx, by = float(bx), float(by)
    
        abx = bx - ax
        aby = by - ay
        apx = px - ax
        apy = py - ay
    
        denom = abx * abx + aby * aby
    
        if denom <= 1e-9:
            return self._dist(px, py, ax, ay)
    
        t = max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
    
        cx = ax + t * abx
        cy = ay + t * aby
    
        return self._dist(px, py, cx, cy)
    
    
    def _ball_towards_goal(self, sx, sy, ex, ey, team_id):
        if any(pd.isna(v) for v in [sx, sy, ex, ey, team_id]):
            return False, np.nan
    
        goal = self._active_goal_center(team_id)
    
        ball_vec = np.array([float(ex) - float(sx), float(ey) - float(sy)], dtype=float)
        goal_vec = np.array([float(goal[0]) - float(sx), float(goal[1]) - float(sy)], dtype=float)
    
        ball_norm = np.linalg.norm(ball_vec)
        goal_norm = np.linalg.norm(goal_vec)
    
        if ball_norm <= 1e-9 or goal_norm <= 1e-9:
            return False, np.nan
    
        cos = float(np.dot(ball_vec, goal_vec) / (ball_norm * goal_norm))
    
        return cos >= getattr(self, "shot_goal_cos_min", 0.65), cos
    
    
    def _shot_distance_to_goal(self, x, y, team_id):
        if any(pd.isna(v) for v in [x, y, team_id]):
            return np.nan
    
        goal = self._active_goal_center(team_id)
        return self._dist(x, y, goal[0], goal[1])
    
    
    def _segment_crosses_goal_mouth(self, sx, sy, ex, ey, team_id):
        """
        Checks if the ball segment crosses the opponent goal line
        inside or near the goal mouth.
        """
    
        if any(pd.isna(v) for v in [sx, sy, ex, ey, team_id]):
            return False, np.nan
    
        x_min, x_max, y_min, y_max = self._pitch_bounds()
        y_mid = (y_min + y_max) / 2.0
    
        goal_side = self._attacking_goal_side(team_id)
        goal_x = x_max if goal_side == "right" else x_min
    
        sx, sy, ex, ey = float(sx), float(sy), float(ex), float(ey)
    
        # لازم الخط يعدي على goal_x
        if (sx - goal_x) * (ex - goal_x) > 0:
            return False, np.nan
    
        dx = ex - sx
    
        if abs(dx) < 1e-9:
            return False, np.nan
    
        t = (goal_x - sx) / dx
    
        if t < 0 or t > 1:
            return False, np.nan
    
        y_at_goal = sy + t * (ey - sy)
    
        goal_half_width = getattr(self, "goal_half_width_m", 3.66)
        goal_mouth_margin = getattr(self, "goal_mouth_margin_m", 1.25)
    
        on_mouth = abs(y_at_goal - y_mid) <= goal_half_width + goal_mouth_margin
    
        return bool(on_mouth), float(y_at_goal)
    
    
    def _shot_goal_corridor_distance(self, sx, sy, ex, ey, team_id):
        if any(pd.isna(v) for v in [sx, sy, ex, ey, team_id]):
            return np.nan
    
        goal = self._active_goal_center(team_id)
        return self._point_to_segment_distance(goal[0], goal[1], sx, sy, ex, ey)
    
    
    def _ball_trajectory_after_frame(
        self,
        frames_lookup,
        control_lookup,
        start_frame,
        window_s=2.5,
    ):
        """
        Returns the furthest valid ball point after start_frame.
        Used to estimate shot endpoint.
        """
    
        if pd.isna(start_frame):
            return None
    
        start_frame = int(start_frame)
        sx, sy = self._get_ball_xy_from_sources(start_frame, frames_lookup, control_lookup)
    
        if pd.isna(sx) or pd.isna(sy):
            return None
    
        window_frames = int(window_s * self.fps) if self.fps > 0 else 60
    
        best = {
            "start_frame": start_frame,
            "end_frame": start_frame,
            "start_x": float(sx),
            "start_y": float(sy),
            "end_x": float(sx),
            "end_y": float(sy),
            "direct_distance": 0.0,
        }
    
        prev_x, prev_y = float(sx), float(sy)
    
        for f in range(start_frame + 1, start_frame + window_frames + 1):
            x, y = self._get_ball_xy_from_sources(f, frames_lookup, control_lookup)
    
            if pd.isna(x) or pd.isna(y):
                continue
    
            x, y = float(x), float(y)
    
            if not self._is_inside_pitch(x, y, margin=6.0):
                continue
    
            step = self._dist(prev_x, prev_y, x, y)
    
            # tracking glitch guard
            if not pd.isna(step) and step > getattr(self, "shot_tracking_jump_guard_m", 12.0):
                continue
    
            d = self._dist(sx, sy, x, y)
    
            if not pd.isna(d) and d > best["direct_distance"]:
                best.update({
                    "end_frame": int(f),
                    "end_x": float(x),
                    "end_y": float(y),
                    "direct_distance": float(d),
                })
    
            prev_x, prev_y = x, y
    
        if best["direct_distance"] <= 0:
            return None
    
        return best
    
    def _make_interception_event(
        self,
        frame,
        team_id,
        player_id,
        start_x,
        start_y,
        end_x,
        end_y,
        related_loss_frame,
        confidence=0.78,
        notes="opponent_next_control_after_pass_cross_shot",
    ):
        return {
            "event_id": None,
            "event_name": "interception",
            "event_family": "defensive",
            "event_priority": 25,
    
            "frame": int(frame),
            "time": float(frame) / self.fps if self.fps > 0 else np.nan,
    
            "team_id": team_id,
            "player_id": player_id,
    
            "start_x": float(end_x) if not pd.isna(end_x) else np.nan,
            "start_y": float(end_y) if not pd.isna(end_y) else np.nan,
            "end_x": float(end_x) if not pd.isna(end_x) else np.nan,
            "end_y": float(end_y) if not pd.isna(end_y) else np.nan,
    
            "related_loss_frame": int(related_loss_frame) if not pd.isna(related_loss_frame) else np.nan,
            "related_gain_frame": int(frame),
    
            "successful": True,
            "interception": True,
            "confidence": float(confidence),
            "notes": notes,
    
            "is_pass": False,
            "receiver_player": None,
            "receiver_team": None,
            "dead_ball_event": None,
        }


    def detect_interception_events_from_passes(self, events_df):
        """
        Creates standalone interception events from unsuccessful passes/crosses.
        In your current pass logic:
        - successful = False when next control is opponent
        - interception = True
        """
        if events_df is None or events_df.empty:
            return pd.DataFrame()
    
        rows = []
    
        src = events_df[
            (events_df["event_name"].isin(["pass", "cross"]))
            & (events_df.get("interception", False).astype(bool))
        ].copy()
    
        for _, r in src.iterrows():
            gain_frame = r.get("related_gain_frame", np.nan)
            receiver_player = r.get("receiver_player", None)
            receiver_team = self._safe_int_team(r.get("receiver_team", None))
    
            if pd.isna(gain_frame) or receiver_player is None or receiver_team is None:
                continue
    
            rows.append(
                self._make_interception_event(
                    frame=gain_frame,
                    team_id=receiver_team,
                    player_id=receiver_player,
                    start_x=r.get("start_x", np.nan),
                    start_y=r.get("start_y", np.nan),
                    end_x=r.get("end_x", np.nan),
                    end_y=r.get("end_y", np.nan),
                    related_loss_frame=r.get("related_loss_frame", r.get("frame", np.nan)),
                    confidence=0.80 if r.get("event_name") == "pass" else 0.82,
                    notes=f"standalone_interception_from_{r.get('event_name')}",
                )
            )
    
        return pd.DataFrame(rows)    
    def _is_goalkeeper_id(self, player_id):
        norm = self._norm_player_id(player_id)
        return norm is not None and str(norm).startswith("GK_")
    
    
    def _nearest_goalkeeper_to_point(
        self,
        players_df,
        defending_team,
        frame,
        x,
        y,
        max_distance=5.0,
    ):
        if players_df is None or players_df.empty or pd.isna(frame) or pd.isna(x) or pd.isna(y):
            return None
    
        pf = self._players_at_frame(players_df, frame, window=5)
        if pf is None or pf.empty:
            return None
    
        pf = pf[
            (pf["team_id"].apply(lambda t: self._safe_int_team(t) == int(defending_team)))
            & (pf["is_goalkeeper"].astype(bool))
        ]
    
        if pf.empty:
            return None
    
        candidates = []
    
        for r in pf.itertuples():
            d = self._dist(x, y, getattr(r, "x", np.nan), getattr(r, "y", np.nan))
            if pd.isna(d):
                continue
    
            if float(d) <= max_distance:
                candidates.append({
                    "tracker_id": getattr(r, "tracker_id", None),
                    "team_id": int(defending_team),
                    "distance": float(d),
                })
    
        if not candidates:
            return None
    
        return min(candidates, key=lambda z: z["distance"])
    
    
    def _make_gk_save_event(
        self,
        frame,
        team_id,
        player_id,
        shot_row,
        save_type="save",
        confidence=0.82,
        notes="gk_save_after_on_target_shot",
    ):
        return {
            "event_id": None,
            "event_name": save_type,  # save / save_retain / save_deflect / reflex_save
            "event_family": "goalkeeper",
            "event_priority": 15,
    
            "frame": int(frame),
            "time": float(frame) / self.fps if self.fps > 0 else np.nan,
    
            "team_id": team_id,
            "player_id": player_id,
    
            "start_x": shot_row.get("end_x", np.nan),
            "start_y": shot_row.get("end_y", np.nan),
            "end_x": shot_row.get("end_x", np.nan),
            "end_y": shot_row.get("end_y", np.nan),
    
            "related_loss_frame": shot_row.get("frame", np.nan),
            "related_gain_frame": int(frame),
    
            "shot_player": shot_row.get("player_id", None),
            "shot_team": shot_row.get("team_id", None),
            "shot_outcome": shot_row.get("shot_outcome", None),
    
            "successful": True,
            "interception": False,
            "confidence": float(confidence),
            "notes": notes,
    
            "is_pass": False,
            "receiver_player": None,
            "receiver_team": None,
            "dead_ball_event": None,
        }
    
    
    def detect_goalkeeper_save_events(self, shot_events, players_df=None, control_df=None):
        """
        Detect GK saves from detected shots.
        Best case:
        - shot outcome is on_target
        - next possession/control is goalkeeper of defending team
        Fallback:
        - nearest defending GK near shot endpoint.
        """
        if shot_events is None or shot_events.empty:
            return pd.DataFrame()
    
        rows = []
    
        for _, shot in shot_events.iterrows():
            if shot.get("event_name") != "shot":
                continue
    
            outcome = shot.get("shot_outcome", None)
    
            # save only for on target / blocked by GK-like endpoint
            if outcome not in ["on_target"]:
                continue
    
            shooter_team = self._safe_int_team(shot.get("team_id", None))
            if shooter_team is None:
                continue
    
            defending_team = 1 - int(shooter_team)
    
            shot_frame = int(shot.get("frame"))
            end_frame = shot.get("related_gain_frame", np.nan)
            if pd.isna(end_frame):
                end_frame = shot_frame + int(self.fps * 1.5) if self.fps > 0 else shot_frame + 40
    
            end_x = shot.get("end_x", np.nan)
            end_y = shot.get("end_y", np.nan)
    
            gk_player = None
            save_frame = int(end_frame)
    
            # 1) Try from control dataframe: first GK possession after shot
            if control_df is not None and not control_df.empty:
                after = control_df[
                    (control_df["frame"] >= shot_frame)
                    & (control_df["frame"] <= shot_frame + int(self.fps * 2.5))
                    & (control_df["ball_control"].eq("possession"))
                ].copy()
    
                if not after.empty:
                    after["team_norm"] = after["controller_team"].apply(self._safe_int_team)
                    after = after[after["team_norm"] == defending_team]
    
                    gk_hits = after[
                        after["controller_id"].apply(lambda x: self._is_goalkeeper_id(x))
                    ]
    
                    if not gk_hits.empty:
                        first = gk_hits.iloc[0]
                        gk_player = first["controller_id"]
                        save_frame = int(first["frame"])
    
            # 2) Fallback: nearest GK to shot endpoint
            if gk_player is None:
                nearest_gk = self._nearest_goalkeeper_to_point(
                    players_df=players_df,
                    defending_team=defending_team,
                    frame=int(end_frame),
                    x=end_x,
                    y=end_y,
                    max_distance=getattr(self, "gk_save_endpoint_max_distance_m", 6.0),
                )
    
                if nearest_gk is not None:
                    gk_player = nearest_gk["tracker_id"]
                    save_frame = int(end_frame)
    
            if gk_player is None:
                continue
    
            retain = False
            if control_df is not None and not control_df.empty:
                window = int(getattr(self, "goalkeeper_hold_seconds", 1.0) * self.fps)
                after_hold = control_df[
                    (control_df["frame"] >= save_frame)
                    & (control_df["frame"] <= save_frame + window)
                    & (control_df["ball_control"].eq("possession"))
                    & (control_df["controller_id"].apply(lambda x: self._same_player(x, gk_player)))
                ]
                retain = len(after_hold) >= max(2, int(window * 0.4))
    
            distance_to_goal = shot.get("distance_to_goal", np.nan)
            if not pd.isna(distance_to_goal) and float(distance_to_goal) <= getattr(self, "reflex_save_max_shot_distance_m", 12.0):
                save_type = "reflex_save"
                conf = 0.86
                notes = "near_distance_on_target_shot_gk_save"
            else:
                save_type = "save_retain" if retain else "save_deflect"
                conf = 0.84 if retain else 0.80
                notes = "on_target_shot_gk_save_retain" if retain else "on_target_shot_gk_save_deflect"
    
            rows.append(
                self._make_gk_save_event(
                    frame=save_frame,
                    team_id=defending_team,
                    player_id=gk_player,
                    shot_row=shot,
                    save_type=save_type,
                    confidence=conf,
                    notes=notes,
                )
            )
    
        return pd.DataFrame(rows)
    def _nearest_opponent_to_player(
        self,
        players_df,
        frame,
        player_id,
        team_id,
        max_distance=2.5,
    ):
        if players_df is None or players_df.empty or pd.isna(frame):
            return None
    
        px, py = self._player_xy_at_frame(players_df, player_id, frame, window=3)
    
        if pd.isna(px) or pd.isna(py):
            return None
    
        pf = self._players_at_frame(players_df, frame, window=3)
        if pf is None or pf.empty:
            return None
    
        candidates = []
    
        for r in pf.itertuples():
            opp_team = self._safe_int_team(getattr(r, "team_id", None))
            tracker_id = getattr(r, "tracker_id", None)
    
            if opp_team is None or int(opp_team) == int(team_id):
                continue
    
            if self._is_referee_id(tracker_id):
                continue
    
            d = self._dist(px, py, getattr(r, "x", np.nan), getattr(r, "y", np.nan))
            if pd.isna(d):
                continue
    
            if float(d) <= max_distance:
                candidates.append({
                    "tracker_id": tracker_id,
                    "team_id": opp_team,
                    "distance": float(d),
                })
    
        if not candidates:
            return None
    
        return min(candidates, key=lambda z: z["distance"])
    
    
    def _progress_towards_goal(self, sx, sy, ex, ey, team_id):
        if any(pd.isna(v) for v in [sx, sy, ex, ey, team_id]):
            return np.nan
    
        goal = self._active_goal_center(team_id)
        start_d = self._dist(sx, sy, goal[0], goal[1])
        end_d = self._dist(ex, ey, goal[0], goal[1])
    
        if pd.isna(start_d) or pd.isna(end_d):
            return np.nan
    
        return float(start_d) - float(end_d)
    
    
    def _make_dribble_event(
        self,
        frame,
        team_id,
        player_id,
        opponent_player,
        start_x,
        start_y,
        end_x,
        end_y,
        distance,
        progress,
        successful,
        confidence,
        notes,
    ):
        return {
            "event_id": None,
            "event_name": "dribble",
            "event_family": "duel",
            "event_priority": 22,
    
            "frame": int(frame),
            "time": float(frame) / self.fps if self.fps > 0 else np.nan,
    
            "team_id": team_id,
            "player_id": player_id,
            "opponent_player": opponent_player,
    
            "start_x": float(start_x),
            "start_y": float(start_y),
            "end_x": float(end_x),
            "end_y": float(end_y),
    
            "related_loss_frame": np.nan,
            "related_gain_frame": np.nan,
    
            "distance": float(distance) if not pd.isna(distance) else np.nan,
            "progress_to_goal": float(progress) if not pd.isna(progress) else np.nan,
    
            "successful": bool(successful),
            "interception": False,
            "confidence": float(confidence),
            "notes": notes,
    
            "is_pass": False,
            "receiver_player": None,
            "receiver_team": None,
            "dead_ball_event": None,
        }
    
    
    def detect_dribble_events(self, control_df, players_df=None, frames_df=None, dead_df=None):
        """
        Proxy dribble:
        - Same player keeps possession for a short carrying interval
        - Ball/player moves enough
        - Opponent is close near start/mid interval
        - Successful if player/team keeps ball after the carry and progresses or escapes pressure
        """
        if control_df is None or control_df.empty or players_df is None or players_df.empty:
            return pd.DataFrame()
    
        control = control_df.copy()
        control["frame"] = pd.to_numeric(control["frame"], errors="coerce")
        control = control.dropna(subset=["frame"]).sort_values("frame").reset_index(drop=True)
    
        if control.empty:
            return pd.DataFrame()
    
        if "interval_id" not in control.columns:
            work = control.copy()
            work["is_possession"] = work["ball_control"].eq("possession")
            work["player_norm"] = work["controller_id"].apply(lambda x: self._norm_player_id(x))
            work["team_norm"] = work["controller_team"].apply(lambda x: self._safe_int_team(x))
    
            change = (
                (work["is_possession"] != work["is_possession"].shift())
                | (work["player_norm"] != work["player_norm"].shift())
                | (work["team_norm"] != work["team_norm"].shift())
                | (work["frame"].diff().fillna(1) > 1)
            )
    
            work["interval_id"] = change.cumsum()
            control = work
    
        events = []
    
        min_carry_distance = getattr(self, "dribble_min_carry_distance_m", 2.0)
        min_duration_frames = getattr(self, "dribble_min_duration_frames", max(3, int(self.fps * 0.25)))
        max_duration_frames = getattr(self, "dribble_max_duration_frames", int(self.fps * 5.0))
        opponent_radius = getattr(self, "dribble_opponent_radius_m", 2.75)
        min_progress = getattr(self, "dribble_min_progress_m", 0.75)
    
        for _, g in control.groupby("interval_id"):
            g = g.sort_values("frame")
    
            first = g.iloc[0]
            if first.get("ball_control") != "possession":
                continue
    
            player = first.get("controller_id", None)
            team = self._safe_int_team(first.get("controller_team", None))
    
            if player is None or pd.isna(player) or team is None:
                continue
    
            if self._is_goalkeeper_id(player) or self._is_referee_id(player):
                continue
    
            start_frame = int(g["frame"].min())
            end_frame = int(g["frame"].max())
            duration_frames = end_frame - start_frame + 1
    
            if duration_frames < min_duration_frames or duration_frames > max_duration_frames:
                continue
    
            sx, sy = self._player_xy_at_frame(players_df, player, start_frame, window=3)
            ex, ey = self._player_xy_at_frame(players_df, player, end_frame, window=3)
    
            if any(pd.isna(v) for v in [sx, sy, ex, ey]):
                continue
    
            distance = self._dist(sx, sy, ex, ey)
            if pd.isna(distance) or float(distance) < min_carry_distance:
                continue
    
            mid_frame = int((start_frame + end_frame) / 2)
    
            nearest_opp = self._nearest_opponent_to_player(
                players_df=players_df,
                frame=mid_frame,
                player_id=player,
                team_id=team,
                max_distance=opponent_radius,
            )
    
            if nearest_opp is None:
                continue
    
            progress = self._progress_towards_goal(sx, sy, ex, ey, team)
    
            # success proxy:
            # player progressed, or at least carried enough while escaping pressure
            successful = (
                (not pd.isna(progress) and float(progress) >= min_progress)
                or float(distance) >= getattr(self, "dribble_success_distance_m", 4.0)
            )
    
            progress_txt = f"{progress:.2f}" if not pd.isna(progress) else "nan"
            
            notes = (
                "dribble_proxy_possession_carry_vs_near_opponent"
                f"; opponent={nearest_opp['tracker_id']}"
                f"; opp_dist={nearest_opp['distance']:.2f}"
                f"; carry={distance:.2f}"
                f"; progress={progress_txt}"
            )
    
            confidence = 0.74 if successful else 0.64
    
            events.append(
                self._make_dribble_event(
                    frame=start_frame,
                    team_id=team,
                    player_id=player,
                    opponent_player=nearest_opp["tracker_id"],
                    start_x=sx,
                    start_y=sy,
                    end_x=ex,
                    end_y=ey,
                    distance=distance,
                    progress=progress,
                    successful=successful,
                    confidence=confidence,
                    notes=notes,
                )
            )
    
        out = pd.DataFrame(events)
    
        if not out.empty:
            out = out.drop_duplicates(
                subset=["frame", "player_id", "opponent_player"],
                keep="first",
            ).sort_values("frame").reset_index(drop=True)
    
        return out    
    def _nearest_opponent_or_gk_near_segment(
        self,
        players_df,
        team_id,
        frame,
        sx,
        sy,
        ex,
        ey,
        max_distance=2.0,
    ):
        """
        Rough blocked-shot proxy:
        opponent/GK close to the ball path.
        """
    
        if players_df is None or players_df.empty or pd.isna(frame):
            return None
    
        pf = self._players_at_frame(players_df, frame, window=3)
    
        if pf is None or pf.empty:
            return None
    
        candidates = []
    
        for r in pf.itertuples():
            tracker_id = getattr(r, "tracker_id", None)
    
            if tracker_id is None or pd.isna(tracker_id):
                continue
    
            if self._is_referee_id(tracker_id):
                continue
    
            p_team = self._safe_int_team(getattr(r, "team_id", None))
    
            if p_team is None:
                continue
    
            if int(p_team) == int(team_id):
                continue
    
            x = getattr(r, "x", np.nan)
            y = getattr(r, "y", np.nan)
    
            if pd.isna(x) or pd.isna(y):
                continue
    
            d = self._point_to_segment_distance(x, y, sx, sy, ex, ey)
    
            if pd.isna(d):
                continue
    
            if d <= max_distance:
                candidates.append({
                    "tracker_id": tracker_id,
                    "team_id": p_team,
                    "distance_to_path": float(d),
                })
    
        if not candidates:
            return None
    
        return min(candidates, key=lambda z: z["distance_to_path"])
    
    
    def _make_shot_event(
        self,
        frame,
        team_id,
        player_id,
        start_x,
        start_y,
        end_x,
        end_y,
        end_frame,
        outcome,
        distance_to_goal,
        shot_distance,
        shot_speed_mps,
        goal_cos,
        goal_corridor_distance,
        confidence,
        notes,
    ):
        return {
            "event_id": None,
            "event_name": "shot",
            "event_family": "open_play",
            "event_priority": 10,
    
            "frame": int(frame),
            "time": float(frame) / self.fps if self.fps > 0 else np.nan,
    
            "team_id": team_id,
            "player_id": player_id,
    
            "start_x": float(start_x),
            "start_y": float(start_y),
            "end_x": float(end_x),
            "end_y": float(end_y),
    
            "related_loss_frame": int(frame),
            "related_gain_frame": int(end_frame) if not pd.isna(end_frame) else np.nan,
    
            "shot_outcome": outcome,
            "distance_to_goal": float(distance_to_goal) if not pd.isna(distance_to_goal) else np.nan,
            "shot_distance": float(shot_distance) if not pd.isna(shot_distance) else np.nan,
            "shot_speed_mps": float(shot_speed_mps) if not pd.isna(shot_speed_mps) else np.nan,
            "goal_cos": float(goal_cos) if not pd.isna(goal_cos) else np.nan,
            "goal_corridor_distance": (
                float(goal_corridor_distance)
                if not pd.isna(goal_corridor_distance)
                else np.nan
            ),
    
            "successful": outcome in ["on_target", "goal"],
            "confidence": float(confidence),
            "notes": notes,
    
            # compatibility columns with pass events
            "is_pass": False,
            "receiver_player": None,
            "receiver_team": None,
            "interception": False,
            "dead_ball_event": None,
        }   
        
    def detect_shot_events(
        self,
        control_df,
        players_df=None,
        frames_df=None,
        dead_df=None,
    ):
        if control_df is None or control_df.empty:
            return pd.DataFrame()
    
        control = control_df.copy()
        control["frame"] = pd.to_numeric(control["frame"], errors="coerce")
        control = control.dropna(subset=["frame"]).sort_values("frame").reset_index(drop=True)
    
        if control.empty:
            return pd.DataFrame()
    
        frames_lookup = pd.DataFrame()
    
        if frames_df is not None and not frames_df.empty:
            frames = frames_df.copy()
            frames["frame"] = pd.to_numeric(frames["frame"], errors="coerce")
            frames = frames.dropna(subset=["frame"]).sort_values("frame")
    
            if "ball_x" in frames.columns and "ball_y" in frames.columns:
                frames_lookup = (
                    frames
                    .drop_duplicates(subset=["frame"], keep="last")
                    .set_index("frame")
                )
    
        control_lookup = (
            control
            .drop_duplicates(subset=["frame"], keep="last")
            .set_index("frame")
        )
    
        # ---------- Build possession intervals ----------
        interval_rows = []
    
        if "interval_id" in control.columns:
            grouped = control.groupby("interval_id")
        else:
            work = control.copy()
            work["is_possession"] = work["ball_control"].eq("possession")
            work["player_norm"] = work["controller_id"].apply(lambda x: self._norm_player_id(x))
            work["team_norm"] = work["controller_team"].apply(lambda x: self._safe_int_team(x))
    
            change = (
                (work["is_possession"] != work["is_possession"].shift())
                | (work["player_norm"] != work["player_norm"].shift())
                | (work["team_norm"] != work["team_norm"].shift())
                | (work["frame"].diff().fillna(1) > 1)
            )
    
            work["interval_id"] = change.cumsum()
            grouped = work.groupby("interval_id")
    
        min_interval_frames = getattr(self, "shot_min_possession_interval_frames", 2)
    
        for interval_id, g in grouped:
            g = g.sort_values("frame")
            first = g.iloc[0]
    
            if first.get("ball_control", None) != "possession":
                continue
    
            player = first.get("controller_id", None)
            team = self._safe_int_team(first.get("controller_team", None))
    
            if player is None or pd.isna(player) or team is None:
                continue
    
            if self._is_referee_id(player):
                continue
    
            if len(g) < min_interval_frames:
                continue
    
            interval_rows.append({
                "start_frame": int(g["frame"].min()),
                "end_frame": int(g["frame"].max()),
                "player": player,
                "team": team,
                "interval_df": g,
            })
    
        if not interval_rows:
            return pd.DataFrame()
    
        events = []
    
        max_shot_distance_to_goal = getattr(self, "shot_max_distance_to_goal_m", 40.0)
        min_shot_travel = getattr(self, "shot_min_travel_m", 5.0)
        min_shot_speed = getattr(self, "shot_min_speed_mps", 6.0)
        max_goal_corridor = getattr(self, "shot_goal_corridor_m", 6.5)
    
        for item in interval_rows:
            release_frame = int(item["end_frame"])
            shooter_player = item["player"]
            shooter_team = self._safe_int_team(item["team"])
    
            if shooter_player is None or shooter_team is None:
                continue
    
            if dead_df is not None and not dead_df.empty:
                has_dead, deadball_id = self._dead_between(
                    dead_df,
                    release_frame,
                    release_frame + int(self.fps * 1.0) if self.fps > 0 else release_frame + 25,
                )
                if has_dead:
                    continue
    
            sx, sy = self._get_ball_xy_from_sources(
                release_frame,
                frames_lookup,
                control_lookup,
            )
    
            if not self._is_valid_ball_point(sx, sy, margin=4.0):
                continue
    
            distance_to_goal = self._shot_distance_to_goal(sx, sy, shooter_team)
    
            if pd.isna(distance_to_goal):
                continue
    
            # لازم تكون من مسافة منطقية للتسديد
            if float(distance_to_goal) > max_shot_distance_to_goal:
                continue
    
            traj = self._ball_trajectory_after_frame(
                frames_lookup=frames_lookup,
                control_lookup=control_lookup,
                start_frame=release_frame,
                window_s=getattr(self, "shot_trajectory_window_s", 2.5),
            )
    
            if traj is None:
                continue
    
            ex = traj["end_x"]
            ey = traj["end_y"]
            end_frame = traj["end_frame"]
            shot_distance = traj["direct_distance"]
    
            if pd.isna(shot_distance) or float(shot_distance) < min_shot_travel:
                continue
    
            duration_s = (int(end_frame) - int(release_frame)) / self.fps if self.fps > 0 else np.nan
    
            shot_speed_mps = (
                float(shot_distance) / duration_s
                if not pd.isna(duration_s) and duration_s > 0
                else np.nan
            )
    
            speed_info = self._has_notable_speed_change_at_pass(
                control_df=control,
                frame=release_frame,
            )
    
            speed_out = speed_info.get("speed_out", np.nan)
            ball_speed = speed_info.get("ball_speed", np.nan)
            speed_delta = speed_info.get("speed_delta", np.nan)
    
            speed_ok = False
    
            if not pd.isna(shot_speed_mps) and float(shot_speed_mps) >= min_shot_speed:
                speed_ok = True
    
            if not pd.isna(speed_out) and float(speed_out) >= min_shot_speed:
                speed_ok = True
    
            if not pd.isna(ball_speed) and float(ball_speed) >= min_shot_speed:
                speed_ok = True
    
            if not pd.isna(speed_delta) and abs(float(speed_delta)) >= getattr(self, "shot_min_speed_delta_mps", 2.0):
                speed_ok = True
    
            if not speed_ok:
                continue
    
            towards_goal, goal_cos = self._ball_towards_goal(
                sx,
                sy,
                ex,
                ey,
                shooter_team,
            )
    
            if not towards_goal:
                continue
    
            crosses_goal_mouth, y_at_goal = self._segment_crosses_goal_mouth(
                sx,
                sy,
                ex,
                ey,
                shooter_team,
            )
    
            corridor_distance = self._shot_goal_corridor_distance(
                sx,
                sy,
                ex,
                ey,
                shooter_team,
            )
    
            if pd.isna(corridor_distance):
                continue
    
            # لازم المسار يكون في corridor حوالين المرمى
            if not crosses_goal_mouth and float(corridor_distance) > max_goal_corridor:
                continue
    
            blocker = self._nearest_opponent_or_gk_near_segment(
                players_df=players_df,
                team_id=shooter_team,
                frame=end_frame,
                sx=sx,
                sy=sy,
                ex=ex,
                ey=ey,
                max_distance=getattr(self, "shot_block_path_distance_m", 2.0),
            )
    
            if crosses_goal_mouth:
                outcome = "on_target"
                confidence = 0.90
                notes = f"shot_zone+towards_goal+goal_mouth y_at_goal={y_at_goal:.2f}"
            elif blocker is not None:
                outcome = "blocked"
                confidence = 0.82
                notes = (
                    "shot_zone+towards_goal+blocked_proxy"
                    f"; blocker={blocker['tracker_id']}"
                    f"; path_dist={blocker['distance_to_path']:.2f}"
                )
            else:
                outcome = "off_target"
                confidence = 0.76
                notes = (
                    "shot_zone+towards_goal+goal_corridor"
                    f"; corridor_distance={corridor_distance:.2f}"
                )
    
            notes += (
                f"; distance_to_goal={distance_to_goal:.2f}"
                f"; shot_distance={shot_distance:.2f}"
                f"; speed={shot_speed_mps:.2f}"
                f"; goal_cos={goal_cos:.2f}"
            )
    
            events.append(
                self._make_shot_event(
                    frame=release_frame,
                    team_id=shooter_team,
                    player_id=shooter_player,
                    start_x=sx,
                    start_y=sy,
                    end_x=ex,
                    end_y=ey,
                    end_frame=end_frame,
                    outcome=outcome,
                    distance_to_goal=distance_to_goal,
                    shot_distance=shot_distance,
                    shot_speed_mps=shot_speed_mps,
                    goal_cos=goal_cos,
                    goal_corridor_distance=corridor_distance,
                    confidence=confidence,
                    notes=notes,
                )
            )
    
        events_df = pd.DataFrame(events)
    
        if not events_df.empty:
            events_df = events_df.drop_duplicates(
                subset=["frame", "player_id"],
                keep="first",
            ).sort_values("frame").reset_index(drop=True)
    
        return events_df        
    
    def _remove_passes_overlapping_shots(self, events_df):
        if events_df is None or events_df.empty:
            return events_df
    
        if "event_name" not in events_df.columns:
            return events_df
    
        shots = events_df[events_df["event_name"] == "shot"].copy()
    
        if shots.empty:
            return events_df
    
        keep_mask = []
        overlap_window = getattr(self, "shot_pass_overlap_window_frames", 4)
    
        for _, row in events_df.iterrows():
            if row.get("event_name") not in ["pass", "cross"]:
                keep_mask.append(True)
                continue
    
            frame = row.get("frame", np.nan)
            player = row.get("player_id", None)
    
            if pd.isna(frame) or player is None:
                keep_mask.append(True)
                continue
    
            overlapping = shots[
                (shots["frame"].between(int(frame) - overlap_window, int(frame) + overlap_window))
                & (shots["player_id"].apply(lambda x: self._same_player(x, player)))
            ]
    
            keep_mask.append(overlapping.empty)
    
        return events_df[keep_mask].reset_index(drop=True)
        
    def _is_in_wide_channel(self, x, y):
        """
        Wide/flank channel based on pitch width thirds.
        Wyscout divides pitch width into left/middle/right thirds.
        """
        if pd.isna(x) or pd.isna(y):
            return False, None
    
        x_min, x_max, y_min, y_max = self._pitch_bounds()
        width = y_max - y_min
    
        left_limit = y_min + width / 3.0
        right_limit = y_max - width / 3.0
    
        y = float(y)
    
        if y <= left_limit:
            return True, "left"
    
        if y >= right_limit:
            return True, "right"
    
        return False, None
    
    
    def _is_in_attacking_half_or_final_60(self, x, team_id):
        """
        Crosses normally happen from advanced wide areas.
        We allow attacking half plus a small tolerance.
        """
        if pd.isna(x) or pd.isna(team_id):
            return False
    
        x_min, x_max, y_min, y_max = self._pitch_bounds()
        mid_x = (x_min + x_max) / 2.0
        pitch_len = x_max - x_min
    
        # tolerance: allow crosses from just before halfway
        tolerance = pitch_len * 0.08
    
        x = float(x)
    
        if int(team_id) == 0:  # attacking right
            return x >= mid_x - tolerance
    
        else:  # attacking left
            return x <= mid_x + tolerance
    
    
    def _is_in_opponent_penalty_area(self, x, y, attacking_team):
        """
        Standard penalty area proxy:
        - depth: 16.5m from goal line
        - width: 40.32m centered on goal
        """
        if any(pd.isna(v) for v in [x, y, attacking_team]):
            return False
    
        x_min, x_max, y_min, y_max = self._pitch_bounds()
        y_mid = (y_min + y_max) / 2.0
    
        box_depth = getattr(self, "penalty_area_depth_m", 16.5)
        box_half_width = getattr(self, "penalty_area_half_width_m", 20.16)
    
        x = float(x)
        y = float(y)
    
        if int(attacking_team) == 0:  # attacking right
            in_x = x >= x_max - box_depth
        else:  # attacking left
            in_x = x <= x_min + box_depth
    
        in_y = abs(y - y_mid) <= box_half_width
    
        return bool(in_x and in_y)
    
    
    def _is_in_cross_target_zone(self, x, y, attacking_team):
        """
        Target zone for crosses:
        1. inside opponent penalty area
        OR
        2. central zone within ~25m of opponent goal
        """
        if any(pd.isna(v) for v in [x, y, attacking_team]):
            return False, None
    
        if self._is_in_opponent_penalty_area(x, y, attacking_team):
            return True, "penalty_area"
    
        goal = self._active_goal_center(attacking_team)
        dist_to_goal = self._dist(x, y, goal[0], goal[1])
    
        x_min, x_max, y_min, y_max = self._pitch_bounds()
        y_mid = (y_min + y_max) / 2.0
    
        central_half_width = getattr(self, "cross_target_central_half_width_m", 22.0)
        max_goal_distance = getattr(self, "cross_target_max_goal_distance_m", 25.0)
    
        if (
            not pd.isna(dist_to_goal)
            and dist_to_goal <= max_goal_distance
            and abs(float(y) - y_mid) <= central_half_width
        ):
            return True, "central_goal_area"
    
        return False, None
    
    
    def _cross_moves_from_wide_to_danger(self, sx, sy, ex, ey, team_id):
        """
        Prevents random wide passes from being crosses.
        A cross should move from flank toward a dangerous central/box area.
        """
        if any(pd.isna(v) for v in [sx, sy, ex, ey, team_id]):
            return False
    
        x_min, x_max, y_min, y_max = self._pitch_bounds()
        y_mid = (y_min + y_max) / 2.0
    
        start_wide_dist = abs(float(sy) - y_mid)
        end_wide_dist = abs(float(ey) - y_mid)
    
        moved_central = end_wide_dist <= start_wide_dist - getattr(self, "cross_min_central_movement_m", 2.0)
    
        # أو انتهت جوه منطقة الجزاء، حتى لو الحركة مش مركزية جدًا
        in_box = self._is_in_opponent_penalty_area(ex, ey, team_id)
    
        return bool(moved_central or in_box)
    
    
    def _is_cross_candidate_event(self, row):
        """
        Decides whether a pass event should be labelled as cross.
        """
        if row.get("event_name") != "pass":
            return False, None, None
    
        team_id = row.get("team_id", None)
    
        sx = row.get("start_x", np.nan)
        sy = row.get("start_y", np.nan)
        ex = row.get("end_x", np.nan)
        ey = row.get("end_y", np.nan)
    
        distance = row.get("distance", np.nan)
    
        if any(pd.isna(v) for v in [sx, sy, ex, ey, distance]):
            return False, None, None
    
        # cross attempts should have some meaningful travel
        min_cross_distance = getattr(self, "cross_min_distance_m", 8.0)
        if float(distance) < min_cross_distance:
            return False, None, None
    
        # origin must be wide/flank
        in_wide, flank = self._is_in_wide_channel(sx, sy)
    
        if not in_wide:
            return False, None, None
    
        # origin should be reasonably advanced
        if not self._is_in_attacking_half_or_final_60(sx, team_id):
            return False, None, None
    
        # target should be box or dangerous central zone
        target_ok, target_zone = self._is_in_cross_target_zone(ex, ey, team_id)
    
        if not target_ok:
            return False, None, None
    
        # ball should move from flank toward danger
        if not self._cross_moves_from_wide_to_danger(sx, sy, ex, ey, team_id):
            return False, None, None
    
        return True, flank, target_zone        
    def _label_crosses_from_passes(self, events_df, players_df=None):
        """
        Converts pass events into cross events when Wyscout-style cross logic matches.
    
        Cross remains a pass subtype:
        - is_pass = True
        - successful stays as pass successful value
        """
        if events_df is None or events_df.empty:
            return events_df
    
        out = events_df.copy()
    
        # columns for compatibility/debugging
        if "cross_flank" not in out.columns:
            out["cross_flank"] = None
    
        if "cross_target_zone" not in out.columns:
            out["cross_target_zone"] = None
    
        if "is_cross" not in out.columns:
            out["is_cross"] = False
    
        for idx, row in out.iterrows():
            is_cross, flank, target_zone = self._is_cross_candidate_event(row)
    
            if not is_cross:
                continue
    
            out.at[idx, "event_name"] = "cross"
            out.at[idx, "event_family"] = "open_play"
            out.at[idx, "event_priority"] = 18
            out.at[idx, "is_pass"] = True
            out.at[idx, "is_cross"] = True
            out.at[idx, "cross_flank"] = flank
            out.at[idx, "cross_target_zone"] = target_zone
    
            old_notes = row.get("notes", "")
            out.at[idx, "notes"] = (
                f"{old_notes}; cross_proxy=wide_origin+danger_target"
                f"; flank={flank}; target_zone={target_zone}"
            )
    
            # confidence boost بسيط لو كانت ناجحة
            if bool(row.get("successful", False)):
                old_conf = row.get("confidence", 0.75)
                try:
                    out.at[idx, "confidence"] = min(0.92, float(old_conf) + 0.03)
                except Exception:
                    out.at[idx, "confidence"] = 0.85
    
        return out        
    def run_event_detection(self, control_df, gains_df, losses_df, frames_df, players_df):
        frames_df = self._prepare_frames(frames_df)
        players_df = self._prepare_players(players_df)
    
        self._event_frames_lookup = (
            frames_df.drop_duplicates(subset=["frame"], keep="last").set_index("frame")
            if not frames_df.empty else pd.DataFrame()
        )
    
        dead_df = self.detect_dead_ball_intervals(frames_df)
        transitions_df = pd.DataFrame()
    
        pass_events = self.detect_pass_events(
            control_df=control_df,
            players_df=players_df,
            frames_df=frames_df,
            dead_df=dead_df,
        )
    

        pass_events = self._label_crosses_from_passes(
            events_df=pass_events,
            players_df=players_df,
        )
    
        shot_events = self.detect_shot_events(
            control_df=control_df,
            players_df=players_df,
            frames_df=frames_df,
            dead_df=dead_df,
        )
        
        gk_save_events = self.detect_goalkeeper_save_events(
            shot_events=shot_events,
            players_df=players_df,
            control_df=control_df,
        )
        
        dribble_events = self.detect_dribble_events(
            control_df=control_df,
            players_df=players_df,
            frames_df=frames_df,
            dead_df=dead_df,
        )
        
        events_df = pd.concat(
            [pass_events, shot_events, gk_save_events, dribble_events],
            ignore_index=True,
        )
        
        if not events_df.empty:
            events_df = self._remove_passes_overlapping_shots(events_df)
        
            interception_events = self.detect_interception_events_from_passes(events_df)
        
            events_df = pd.concat(
                [events_df, interception_events],
                ignore_index=True,
            )
        
            allowed_events = {
                "pass",
                "cross",
                "shot",
                "interception",
                "save",
                "save_retain",
                "save_deflect",
                "reflex_save",
                "dribble",
            }
        
            events_df = events_df[events_df["event_name"].isin(allowed_events)].reset_index(drop=True)
            events_df = events_df.sort_values(["frame", "event_priority"]).reset_index(drop=True)
            events_df["event_id"] = np.arange(1, len(events_df) + 1)
    
        return events_df, dead_df, transitions_df
    
    def _prepare_frames(self, frames_df):
        out = frames_df.copy()
        if out.empty:
            return out
    
        out["frame"] = pd.to_numeric(out["frame"], errors="coerce").astype("Int64")
        out["time"] = pd.to_numeric(out["time"], errors="coerce")
        out["ball_x"] = pd.to_numeric(out["ball_x"], errors="coerce")
        out["ball_y"] = pd.to_numeric(out["ball_y"], errors="coerce")
    
        if "ball_visible" not in out.columns:
            out["ball_visible"] = ~(out["ball_x"].isna() | out["ball_y"].isna())
    
        if "ball_used_fallback" not in out.columns:
            out["ball_used_fallback"] = False
    
        return out.dropna(subset=["frame"]).sort_values("frame").reset_index(drop=True)
    
    def _prepare_players(self, players_df):
        out = players_df.copy()
        if out.empty:
            return out
    
        out["frame"] = pd.to_numeric(out["frame"], errors="coerce").astype("Int64")
        out["x"] = pd.to_numeric(out["x"], errors="coerce")
        out["y"] = pd.to_numeric(out["y"], errors="coerce")
        out["team_id"] = pd.to_numeric(out["team_id"], errors="coerce")
    
        if "is_goalkeeper" not in out.columns:
            out["is_goalkeeper"] = out["tracker_id"].astype(str).str.startswith("GK_")
    
        return out.dropna(subset=["frame", "x", "y"]).sort_values(["frame", "team_id"]).reset_index(drop=True)
        
    def _pitch_bounds(self):
        vertices = np.array(self.pitch_config.vertices, dtype=np.float32) / 100.0
        x_min, y_min = vertices.min(axis=0)
        x_max, y_max = vertices.max(axis=0)
        return float(x_min), float(x_max), float(y_min), float(y_max)
        
    def _is_inside_pitch(self, x, y, margin=0.0):
        """
        Check whether a point is inside the pitch boundaries.
    
        margin:
        - positive margin allows a small tolerance outside the pitch
        - margin=4.0 means accept points up to 4 meters outside the pitch
        """
        if pd.isna(x) or pd.isna(y):
            return False
    
        x_min, x_max, y_min, y_max = self._pitch_bounds()
    
        x = float(x)
        y = float(y)
        margin = float(margin)
    
        return (
            x_min - margin <= x <= x_max + margin
            and y_min - margin <= y <= y_max + margin
        )
    def _center_mark(self):
        x_min, x_max, y_min, y_max = self._pitch_bounds()
        return np.array([(x_min + x_max) / 2.0, (y_min + y_max) / 2.0], dtype=float)
    
    def _goal_centers(self):
        x_min, x_max, y_min, y_max = self._pitch_bounds()
        y_mid = (y_min + y_max) / 2.0
        return {
            "left": np.array([x_min, y_mid], dtype=float),
            "right": np.array([x_max, y_mid], dtype=float),
        }
    
    def _attacking_goal_side(self, team_id):
        return "right" if int(team_id) == 0 else "left"
    
    def _active_goal_center(self, team_id):
        return self._goal_centers()[self._attacking_goal_side(team_id)]
    
    def _dist(self, x1, y1, x2, y2):
        if any(pd.isna(v) for v in [x1, y1, x2, y2]):
            return np.nan
        return float(np.hypot(float(x1) - float(x2), float(y1) - float(y2)))
    
    def _players_at_frame(self, players_df, frame, window=2):
        if players_df.empty or pd.isna(frame):
            return players_df.iloc[0:0] if not players_df.empty else players_df
        frame = int(frame)
        return players_df[(players_df["frame"] >= frame - window) & (players_df["frame"] <= frame + window)]
    def _player_xy_at_frame(self, players_df, tracker_id, frame, window=3):
        if players_df.empty or tracker_id is None or pd.isna(frame):
            return np.nan, np.nan
    
        pf = self._players_at_frame(players_df, frame, window=window)
        if pf.empty:
            return np.nan, np.nan
    
        hit = pf[pf["tracker_id"].apply(lambda x: self._same_player(x, tracker_id))]
        if hit.empty:
            return np.nan, np.nan
    
        r = hit.iloc[0]
        return float(r["x"]), float(r["y"])
    
    
    def _player_to_player_distance(
        self,
        players_df,
        from_player,
        from_frame,
        to_player,
        to_frame,
    ):
        x1, y1 = self._player_xy_at_frame(players_df, from_player, from_frame)
        x2, y2 = self._player_xy_at_frame(players_df, to_player, to_frame)
    
        if any(pd.isna(v) for v in [x1, y1, x2, y2]):
            return np.nan
    
        return self._dist(x1, y1, x2, y2)        
    
    def _count_attackers_in_box(self, players_df, frame, attacking_team):
        pf = self._players_at_frame(players_df, frame)
        if pf.empty:
            return 0
        mask = pf["team_id"].astype(int) == int(attacking_team)
        return int(sum(self._is_in_penalty_area(r.x, r.y, attacking_team=attacking_team) for r in pf[mask].itertuples()))
    
    def detect_dead_ball_intervals(self, frames_df):
        if frames_df.empty:
            return pd.DataFrame()
    
        out = frames_df.copy()
    
        visible = out["ball_visible"].astype(bool) if "ball_visible" in out.columns else ~(out["ball_x"].isna() | out["ball_y"].isna())
        out["ball_missing_real"] = ~visible
    
        out["outside_pitch"] = [
            False if pd.isna(r.ball_x) or pd.isna(r.ball_y)
            else not self._is_inside_pitch(r.ball_x, r.ball_y, margin=4.0)
            for r in out.itertuples()
        ]
    
        # fallback مش dead ball
        out["dead_candidate"] = out["ball_missing_real"] | out["outside_pitch"]
    
        min_frames = getattr(self, "min_dead_ball_frames", max(25, int(self.fps * 1.2)))
    
        intervals = []
        start = None
    
        for i, row in out.iterrows():
            is_dead = bool(row["dead_candidate"])
            frame = int(row["frame"])
    
            if is_dead and start is None:
                start = frame
    
            if (not is_dead or i == len(out) - 1) and start is not None:
                end = int(out.iloc[i - 1]["frame"]) if not is_dead else frame
    
                if end - start + 1 >= min_frames:
                    intervals.append({
                        "deadball_id": len(intervals) + 1,
                        "start_frame": start,
                        "end_frame": end,
                        "duration_frames": end - start + 1,
                        "start_time": start / self.fps if self.fps > 0 else np.nan,
                        "end_time": end / self.fps if self.fps > 0 else np.nan,
                    })
    
                start = None
    
        return pd.DataFrame(intervals)
    
    def _dead_between(self, dead_df, f1, f2):
        if dead_df.empty or pd.isna(f1) or pd.isna(f2):
            return False, None
        lo, hi = sorted([int(f1), int(f2)])
        hit = dead_df[(dead_df["start_frame"] <= hi) & (dead_df["end_frame"] >= lo)]
        if hit.empty:
            return False, None
        return True, int(hit.iloc[0]["deadball_id"])
    
    
    def _frame_ball_xy(self, frames_lookup, frame):
        if pd.isna(frame) or frames_lookup.empty:
            return np.nan, np.nan
        frame = int(frame)
        if frame not in frames_lookup.index:
            return np.nan, np.nan
        return frames_lookup.loc[frame, "ball_x"], frames_lookup.loc[frame, "ball_y"]
    
    def build_transition_table(self, control_df, gains_df, losses_df, frames_df, players_df, dead_df):
        if losses_df.empty:
            return pd.DataFrame()
    
        transitions = []
        gains_sorted = gains_df.sort_values("frame").reset_index(drop=True) if not gains_df.empty else pd.DataFrame()
        frames_lookup = (
                frames_df
                .drop_duplicates(subset=["frame"], keep="last")
                .set_index("frame")
            )
    
        for loss in losses_df.sort_values("frame").itertuples():
            loss_frame = int(loss.frame)
    
            next_gain = None
            if not gains_sorted.empty:
                cand = gains_sorted[gains_sorted["frame"] > loss_frame]
                if not cand.empty:
                    next_gain = cand.iloc[0]
    
            if next_gain is not None and self._same_player(loss.tracker_id, next_gain["tracker_id"]):
                continue
    
            gain_frame = int(next_gain["frame"]) if next_gain is not None else np.nan
            start_x, start_y = self._frame_ball_xy(frames_lookup, loss_frame)
            end_x, end_y = self._frame_ball_xy(frames_lookup, gain_frame)
    
            has_dead, deadball_id = self._dead_between(
                dead_df,
                loss_frame,
                gain_frame if not pd.isna(gain_frame) else loss_frame + int(self.fps * 5)
            )
            duration_frames = (
                int(gain_frame) - int(loss_frame)
                if not pd.isna(gain_frame)
                else np.nan
            )
            
            duration_s = (
                duration_frames / self.fps
                if not pd.isna(duration_frames) and self.fps > 0
                else np.nan
            )
            
            travel_distance = self._ball_path_distance(frames_lookup, loss_frame, gain_frame)
            
            flight = self._ball_flight_after_frame(
                frames_lookup=frames_lookup,
                start_frame=loss_frame,
                window_frames=int(self.fps * 2.5),
            )
            
            flight_distance = flight["distance"]
            
            if (
                pd.isna(travel_distance)
                or float(travel_distance) < 5.0
            ):
                if not pd.isna(flight_distance):
                    travel_distance = flight_distance
                    end_x = flight["end_x"]
                    end_y = flight["end_y"]
            
            duration_for_speed_s = duration_s
            
            if (
                not pd.isna(flight.get("end_frame", np.nan))
                and int(flight["end_frame"]) > loss_frame
            ):
                duration_for_speed_s = (int(flight["end_frame"]) - loss_frame) / self.fps
            
            transition_speed_mps = (
                travel_distance / duration_for_speed_s
                if not pd.isna(travel_distance)
                and not pd.isna(duration_for_speed_s)
                and duration_for_speed_s > 0
                else np.nan
            )
            
            loss_features = self._control_features_at_frame(control_df, loss_frame)
            gain_features = self._control_features_at_frame(control_df, gain_frame)
            transitions.append({
                "loss_frame": loss_frame,
                "loss_player": loss.tracker_id,
                "loss_team": loss.team_id,
                "gain_frame": gain_frame,
                "gain_player": next_gain["tracker_id"] if next_gain is not None else None,
                "gain_team": next_gain["team_id"] if next_gain is not None else None,
                "has_dead_ball": has_dead,
                "deadball_id": deadball_id,
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "travel_distance": travel_distance,
                "flight_distance": flight_distance,
                "flight_end_frame": flight["end_frame"],
                "flight_end_x": flight["end_x"],
                "flight_end_y": flight["end_y"],
                "duration_frames": duration_frames,
                "duration_s": duration_s,
                "duration_for_speed_s": duration_for_speed_s,
                "transition_speed_mps": transition_speed_mps,
                "loss_ball_speed": loss_features.get("ball_speed", np.nan),
                "loss_speed_out": loss_features.get("speed_out", np.nan),
                "loss_speed_delta": loss_features.get("speed_delta", np.nan),
                "gain_ball_speed": gain_features.get("ball_speed", np.nan),
                "source": "gain_loss",
            })
    
        return pd.DataFrame(transitions)
    
    def build_interval_transitions(self, control_df, frames_df, players_df, dead_df):
        if control_df.empty:
            return pd.DataFrame()
    
        out = control_df.copy().sort_values("frame").reset_index(drop=True)
    
        if "interval_id" not in out.columns:
            out = self.build_control_intervals(out)
    
        frames_lookup = (
            frames_df
            .drop_duplicates(subset=["frame"], keep="last")
            .set_index("frame")
        )
        intervals = []
        for _, g in out.groupby("interval_id"):
            first = g.iloc[0]
            last = g.iloc[-1]
    
            if first["ball_control"] != "possession":
                continue
    
            intervals.append({
                "start_frame": int(first["frame"]),
                "end_frame": int(last["frame"]),
                "player": first["controller_id"],
                "team": first["controller_team"],
            })
    
        transitions = []
        for i in range(len(intervals) - 1):
            a = intervals[i]
            b = intervals[i + 1]
        
            if self._same_player(a["player"], b["player"]):
                continue
            has_dead, deadball_id = self._dead_between(dead_df, a["end_frame"], b["start_frame"])
            if has_dead:
                continue
    
            sx, sy = self._frame_ball_xy(frames_lookup, a["end_frame"])
            ex, ey = self._frame_ball_xy(frames_lookup, b["start_frame"])
            duration_frames = int(b["start_frame"]) - int(a["end_frame"])
            duration_s = duration_frames / self.fps if self.fps > 0 else np.nan
    
            travel_distance = self._ball_path_distance(
                frames_lookup,
                a["end_frame"],
                b["start_frame"]
            )
            
            flight = self._ball_flight_after_frame(
                frames_lookup=frames_lookup,
                start_frame=a["end_frame"],
                window_frames=int(self.fps * 2.5),
            )
            
            flight_distance = flight["distance"]
            
            if (
                pd.isna(travel_distance)
                or float(travel_distance) < 5.0
            ):
                if not pd.isna(flight_distance):
                    travel_distance = flight_distance
                    ex = flight["end_x"]
                    ey = flight["end_y"]
            
            duration_for_speed_s = duration_s
            
            if (
                not pd.isna(flight.get("end_frame", np.nan))
                and int(flight["end_frame"]) > int(a["end_frame"])
            ):
                duration_for_speed_s = (int(flight["end_frame"]) - int(a["end_frame"])) / self.fps
            
            transition_speed_mps = (
                travel_distance / duration_for_speed_s
                if not pd.isna(travel_distance)
                and not pd.isna(duration_for_speed_s)
                and duration_for_speed_s > 0
                else np.nan
            )
            
            loss_features = self._control_features_at_frame(control_df, a["end_frame"])
            gain_features = self._control_features_at_frame(control_df, b["start_frame"]) 
            transitions.append({
                "loss_frame": a["end_frame"],
                "loss_player": a["player"],
                "loss_team": a["team"],
                "gain_frame": b["start_frame"],
                "gain_player": b["player"],
                "gain_team": b["team"],
                "has_dead_ball": False,
                "deadball_id": None,
                "start_x": sx,
                "start_y": sy,
                "end_x": ex,
                "end_y": ey,
                "travel_distance": travel_distance,
                "duration_frames": duration_frames,
                "duration_s": duration_s,
            
                # ضيف ده
                "duration_for_speed_s": duration_for_speed_s,
            
                "transition_speed_mps": transition_speed_mps,
                "loss_ball_speed": loss_features.get("ball_speed", np.nan),
                "loss_speed_out": loss_features.get("speed_out", np.nan),
                "loss_speed_delta": loss_features.get("speed_delta", np.nan),
                "gain_ball_speed": gain_features.get("ball_speed", np.nan),
                "source": "control_interval_transition",
            
                "flight_distance": flight_distance,
                "flight_end_frame": flight["end_frame"],
                "flight_end_x": flight["end_x"],
                "flight_end_y": flight["end_y"],
            })
    
        return pd.DataFrame(transitions)
    
    def _safe_int_team(self, team_id):
        if team_id is None or pd.isna(team_id):
            return None
        try:
            return int(float(team_id))
        except Exception:
            return None
    
    
    def _is_valid_ball_point(self, x, y, margin=4.0):
        if pd.isna(x) or pd.isna(y):
            return False
        return self._is_inside_pitch(float(x), float(y), margin=margin)
    
    
    
    def _make_pass_event(
        self,
        event_id,
        loss_frame,
        gain_frame,
        passer_player,
        passer_team,
        receiver_player,
        receiver_team,
        start_x,
        start_y,
        end_x,
        end_y,
        distance,
        duration_s,
        speed_mps,
        successful,
        interception,
        confidence,
        notes,
    ):
        return {
            "event_id": event_id,
            "event_name": "pass",
            "event_family": "open_play",
            "event_priority": 20,
    
            "frame": int(loss_frame),
            "time": float(loss_frame) / self.fps if self.fps > 0 else np.nan,
    
            "team_id": passer_team,
            "player_id": passer_player,
    
            "start_x": float(start_x),
            "start_y": float(start_y),
            "end_x": float(end_x),
            "end_y": float(end_y),
    
            "receiver_player": receiver_player,
            "receiver_team": receiver_team,
    
            "successful": bool(successful),
            "interception": bool(interception),
    
            "related_loss_frame": int(loss_frame),
            "related_gain_frame": int(gain_frame),
    
            "distance": float(distance) if not pd.isna(distance) else np.nan,
            "duration_s": float(duration_s) if not pd.isna(duration_s) else np.nan,
            "speed_mps": float(speed_mps) if not pd.isna(speed_mps) else np.nan,
    
            "confidence": float(confidence),
            "notes": notes,
    
            # للـ compatibility مع باقي الكلاس
            "is_pass": True,
            "dead_ball_event": None,
        }
    
        
    def detect_pass_events(
        self,
        control_df,
        players_df=None,
        gains_df=None,
        losses_df=None,
        frames_df=None,
        dead_df=None,
    ):
        """
        Wyscout-style Pass detector from possession intervals.
    
        Logic:
        - Find real possession intervals from control_df.
        - Merge tiny same-player re-control intervals.
        - For every player-to-player possession transition:
            same team  => successful pass
            opponent   => unsuccessful pass / intercepted pass
        """
    
        if control_df is None or control_df.empty:
            return pd.DataFrame()
    
        control = control_df.copy()
    
        control["frame"] = pd.to_numeric(control["frame"], errors="coerce")
        control = control.dropna(subset=["frame"]).sort_values("frame").reset_index(drop=True)
    
        if control.empty:
            return pd.DataFrame()
    
        max_pass_gap_s = getattr(self, "max_pass_gap_s", 6.0)
        min_pass_distance_m = getattr(self, "min_pass_distance_m", 0.20)
        merge_same_player_gap_s = getattr(self, "merge_same_player_retouch_gap_s", 2.0)
    
        max_pass_gap_frames = int(max_pass_gap_s * self.fps) if self.fps > 0 else 150
        merge_same_player_gap_frames = int(merge_same_player_gap_s * self.fps) if self.fps > 0 else 50
    
        # ---------- 1) Build possession intervals ----------
        min_possession_interval_frames = getattr(self, "min_possession_interval_frames", 3)
        merge_same_player_gap_s = getattr(self, "merge_same_player_retouch_gap_s", 0.40)
        merge_same_player_gap_frames = int(merge_same_player_gap_s * self.fps) if self.fps > 0 else 10
        
        interval_rows = []
        
        if "interval_id" in control.columns:
            grouped = control.groupby("interval_id")
        else:
            work = control.copy()
            work["is_possession"] = work["ball_control"].eq("possession")
            work["player_norm"] = work["controller_id"].apply(lambda x: self._norm_player_id(x))
            work["team_norm"] = work["controller_team"].apply(lambda x: self._safe_int_team(x))
        
            change = (
                (work["is_possession"] != work["is_possession"].shift())
                | (work["player_norm"] != work["player_norm"].shift())
                | (work["team_norm"] != work["team_norm"].shift())
                | (work["frame"].diff().fillna(1) > 1)
            )
        
            work["interval_id"] = change.cumsum()
            grouped = work.groupby("interval_id")
        
        for interval_id, g in grouped:
            g = g.sort_values("frame")
            first = g.iloc[0]
        
            if first.get("ball_control", None) != "possession":
                continue
        
            player = first.get("controller_id", None)
            team = self._safe_int_team(first.get("controller_team", None))
        
            if player is None or pd.isna(player) or team is None:
                continue
        
            n_frames = int(len(g))
        
            # مهم جدًا:
            # شيل اللمسات الصغيرة جدًا لأنها غالبًا retouch/glitch
            # ودي كانت بتبوظ نقطة بداية الباص.
            if n_frames < min_possession_interval_frames:
                continue
        
            interval_rows.append({
                "start_frame": int(g["frame"].min()),
                "end_frame": int(g["frame"].max()),
                "player": player,
                "team": team,
                "n_frames": n_frames,
            })
        
        intervals = pd.DataFrame(interval_rows)
        
        if intervals.empty:
            return pd.DataFrame()
        
        intervals = intervals.sort_values("start_frame").reset_index(drop=True)
        
        # ---------- 2) Merge same-player intervals carefully ----------
        merged = []
        
        for row in intervals.itertuples(index=False):
            item = {
                "start_frame": int(row.start_frame),
                "end_frame": int(row.end_frame),
                "player": row.player,
                "team": int(row.team),
                "n_frames": int(row.n_frames),
            }
        
            if not merged:
                merged.append(item)
                continue
        
            prev = merged[-1]
            gap = item["start_frame"] - prev["end_frame"]
            same_player = self._same_player(prev["player"], item["player"])
            same_team = int(prev["team"]) == int(item["team"])
        
            # دمج حذر جدًا:
            # نفس اللاعب + نفس الفريق + gap صغير فقط
            if same_player and same_team and gap <= merge_same_player_gap_frames:
                prev["end_frame"] = max(prev["end_frame"], item["end_frame"])
                prev["n_frames"] += item["n_frames"]
            else:
                merged.append(item)
        
        intervals = pd.DataFrame(merged)
        
        if len(intervals) < 2:
            return pd.DataFrame()
    
        # ---------- 3) Prepare ball coordinate lookup ----------
        frames_lookup = pd.DataFrame()
    
        if frames_df is not None and not frames_df.empty:
            frames = frames_df.copy()
            frames["frame"] = pd.to_numeric(frames["frame"], errors="coerce")
            frames = frames.dropna(subset=["frame"]).sort_values("frame")
    
            if "ball_x" in frames.columns and "ball_y" in frames.columns:
                frames_lookup = (
                    frames
                    .drop_duplicates(subset=["frame"], keep="last")
                    .set_index("frame")
                )
    
        control_lookup = (
            control
            .drop_duplicates(subset=["frame"], keep="last")
            .set_index("frame")
        )
    
        def get_ball_xy(frame):
            frame = int(frame)
    
            if not frames_lookup.empty and frame in frames_lookup.index:
                r = frames_lookup.loc[frame]
                x = r.get("ball_x", np.nan)
                y = r.get("ball_y", np.nan)
    
                if not pd.isna(x) and not pd.isna(y):
                    return float(x), float(y)
    
            if frame in control_lookup.index:
                r = control_lookup.loc[frame]
    
                if "ball_x" in r.index and "ball_y" in r.index:
                    x = r.get("ball_x", np.nan)
                    y = r.get("ball_y", np.nan)
                else:
                    x = r.get("ball_x_smooth", np.nan)
                    y = r.get("ball_y_smooth", np.nan)
    
                if not pd.isna(x) and not pd.isna(y):
                    return float(x), float(y)
    
            return np.nan, np.nan
    
        def path_distance(f_start, f_end):
            points = []
    
            for f in range(int(f_start), int(f_end) + 1):
                x, y = get_ball_xy(f)
    
                if pd.isna(x) or pd.isna(y):
                    continue
    
                if not self._is_inside_pitch(x, y, margin=5.0):
                    continue
    
                points.append((x, y))
    
            if len(points) < 2:
                sx, sy = get_ball_xy(f_start)
                ex, ey = get_ball_xy(f_end)
                return self._dist(sx, sy, ex, ey)
    
            total = 0.0
    
            for p1, p2 in zip(points[:-1], points[1:]):
                step = float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))
    
                # tracking glitch guard
                if step > 12.0:
                    continue
    
                if step < 0.05:
                    continue
    
                total += step
    
            direct = float(np.hypot(
                points[-1][0] - points[0][0],
                points[-1][1] - points[0][1],
            ))
    
            return max(total, direct)
    
        # ---------- 4) Detect passes ----------
        events = []
    
        for i in range(len(intervals) - 1):
            a = intervals.iloc[i]
            b = intervals.iloc[i + 1]
    
            passer_player = a["player"]
            passer_team = self._safe_int_team(a["team"])
    
            receiver_player = b["player"]
            receiver_team = self._safe_int_team(b["team"])
    
            if passer_player is None or receiver_player is None:
                continue
    
            if passer_team is None or receiver_team is None:
                continue
    
            # نفس اللاعب كمل سيطرة / رجع لمس الكرة => مش pass
            if self._same_player(passer_player, receiver_player):
                continue
    
            loss_frame = int(a["end_frame"])
            gain_frame = int(b["start_frame"])
    
            gap_frames = gain_frame - loss_frame
    
            if gap_frames <= 0:
                continue
    
            if gap_frames > max_pass_gap_frames:
                continue
    
            if dead_df is not None and not dead_df.empty:
                has_dead, deadball_id = self._dead_between(dead_df, loss_frame, gain_frame)
                if has_dead:
                    continue
    
            start_x, start_y = get_ball_xy(loss_frame)
            end_x, end_y = get_ball_xy(gain_frame)
    
            if not self._is_valid_ball_point(start_x, start_y, margin=4.0):
                continue
    
            if not self._is_valid_ball_point(end_x, end_y, margin=4.0):
                continue
    
            distance = self._dist(start_x, start_y, end_x, end_y)
            
            if pd.isna(distance):
                continue
    
            if pd.isna(distance):
                continue
    
            if float(distance) < min_pass_distance_m:
                continue
    
            duration_s = gap_frames / self.fps if self.fps > 0 else np.nan
    
            speed_mps = (
                float(distance) / duration_s
                if not pd.isna(duration_s) and duration_s > 0
                else np.nan
            )
    
            successful = int(passer_team) == int(receiver_team)
            interception = not successful
    
            notes = (
                "wyscout_interval_pass_successful_next_control_teammate"
                if successful
                else "wyscout_interval_pass_unsuccessful_next_control_opponent"
            )
    
            confidence = 0.88 if successful else 0.80
    
            events.append(
                self._make_pass_event(
                    event_id=None,
                    loss_frame=loss_frame,
                    gain_frame=gain_frame,
                    passer_player=passer_player,
                    passer_team=passer_team,
                    receiver_player=receiver_player,
                    receiver_team=receiver_team,
                    start_x=start_x,
                    start_y=start_y,
                    end_x=end_x,
                    end_y=end_y,
                    distance=distance,
                    duration_s=duration_s,
                    speed_mps=speed_mps,
                    successful=successful,
                    interception=interception,
                    confidence=confidence,
                    notes=notes,
                )
            )
    
        events_df = pd.DataFrame(events)
    
        if not events_df.empty:
            events_df = events_df.reset_index(drop=True)
            events_df["event_id"] = np.arange(1, len(events_df) + 1)
    
        return events_df
    def detect_open_play_events(self, transitions_df, players_df, dead_df):
        events = []
        if transitions_df.empty:
            return pd.DataFrame()
    
        for tr in transitions_df.itertuples():
            if pd.isna(tr.loss_team):
                continue
    
            if self._same_player(tr.loss_player, tr.gain_player):
                continue
            event_name, confidence, notes = self.classify_loss_event(tr, players_df, dead_df)
            is_pass_event = event_name in ["pass", "long_pass", "cross"]
    
            same_team_reception = (
                is_pass_event
                and not pd.isna(tr.gain_team)
                and not pd.isna(tr.loss_team)
                and int(tr.gain_team) == int(tr.loss_team)
            )
            
            opponent_reception = (
                is_pass_event
                and not pd.isna(tr.gain_team)
                and not pd.isna(tr.loss_team)
                and int(tr.gain_team) != int(tr.loss_team)
            )
            
            if is_pass_event:
                    pass_successful = bool(same_team_reception)
            else:
                    pass_successful = None
                
            pass_interception = (
                opponent_reception
                and not getattr(tr, "has_dead_ball", False)
            )
    
            events.append(self._make_event(
                frame=tr.loss_frame,
                team_id=tr.loss_team,
                player_id=tr.loss_player,
                event_name=event_name,
                event_family="open_play",
                event_priority=20,
                start_x=tr.start_x,
                start_y=tr.start_y,
                end_x=tr.end_x,
                end_y=tr.end_y,
                related_loss_frame=tr.loss_frame,
                related_gain_frame=tr.gain_frame,
                confidence=confidence,
                notes=notes,
                is_pass=is_pass_event,
                successful=pass_successful,
                receiver_player=tr.gain_player if is_pass_event else None,
                receiver_team=tr.gain_team if is_pass_event else None,
                interception=pass_interception,
            ))
            gain_event = None
            if not pd.isna(tr.gain_frame) and tr.gain_player is not None:
                gain_event = self.classify_gain_event(tr, players_df, prior_loss_event=event_name)
            
            if gain_event is not None and gain_event.get("event_name") == "interception":
                events.append(gain_event)
    
        return pd.DataFrame(events)
    
    def classify_loss_event(self, tr, players_df, dead_df):
        team = int(tr.loss_team)
        sx, sy, ex, ey = tr.start_x, tr.start_y, tr.end_x, tr.end_y
    
        if any(pd.isna(v) for v in [sx, sy, ex, ey]):
            return "pass", 0.45, "missing_ball_endpoint"
    
        towards_goal, goal_cos = self._ball_towards_goal(sx, sy, ex, ey, team)
        intersects_goal = self._ball_intersects_goal_mouth(sx, sy, ex, ey, team)
        in_shot_zone = self._is_in_shot_zone(sx, sy, team)
        in_cross_zone = self._is_in_cross_zone(sx, sy, team)
    
        attackers_in_box = self._count_attackers_in_box(players_df, tr.loss_frame, team)
        gain_in_box = self._is_in_penalty_area(ex, ey, attacking_team=team)
    
        speed = getattr(tr, "transition_speed_mps", np.nan)
        loss_speed_out = getattr(tr, "loss_speed_out", np.nan)
    
        usable_speed = speed
        if pd.isna(usable_speed):
            usable_speed = loss_speed_out
    
        min_shot_speed = getattr(self, "shot_min_speed_mps", 6.0)
        min_cross_speed = getattr(self, "cross_min_speed_mps", 4.0)
    
        speed_ok_for_shot = not pd.isna(usable_speed) and usable_speed >= min_shot_speed
        speed_ok_for_cross = pd.isna(usable_speed) or usable_speed >= min_cross_speed
    
        if in_shot_zone and towards_goal and intersects_goal and speed_ok_for_shot:
            return "shot_on_target", 0.88, f"shot_zone+towards_goal+speed={usable_speed:.2f} cos={goal_cos:.2f}"
    
        if in_shot_zone and towards_goal and tr.has_dead_ball and speed_ok_for_shot:
            return "shot_off_target", 0.76, f"shot_zone+dead_ball+speed={usable_speed:.2f} cos={goal_cos:.2f}"
    
        if in_cross_zone and gain_in_box and attackers_in_box >= 2 and speed_ok_for_cross:
            return "cross", 0.82, f"cross_zone+target_box+attackers={attackers_in_box}+speed={usable_speed:.2f}"
    
        is_long, long_conf, long_notes = self._is_long_pass_proxy(tr, players_df)
        if is_long:
            return "long_pass", long_conf, long_notes
    
        return "pass", 0.70, f"default_open_play_loss speed={usable_speed}"
    
    def classify_gain_event(self, tr, players_df, prior_loss_event):
        if pd.isna(tr.gain_team):
            return None
    
    
        gain_team = int(tr.gain_team)
        loss_team = int(tr.loss_team)
        gain_player = tr.gain_player
    
        if self._same_player(gain_player, tr.loss_player):
            return None
    
        norm_gp = self._norm_player_id(gain_player)
        is_gk = norm_gp is not None and norm_gp.startswith("GK_")
        same_team = gain_team == loss_team
        if is_gk:
            if same_team and prior_loss_event in ["pass", "long_pass"]:
                return self._make_event(
                    frame=tr.gain_frame,
                    team_id=gain_team,
                    player_id=gain_player,
                    event_name="reception",
                    event_family="open_play",
                    event_priority=30,
                    start_x=tr.end_x,
                    start_y=tr.end_y,
                    related_loss_frame=tr.loss_frame,
                    related_gain_frame=tr.gain_frame,
                    confidence=0.72,
                    notes="same_team_gk_reception",
                )
        
            gk_event_name, conf, notes = self.classify_goalkeeper_event(
                tr, players_df, prior_loss_event
            )
        
            return self._make_event(
                frame=tr.gain_frame,
                team_id=gain_team,
                player_id=gain_player,
                event_name=gk_event_name,
                event_family="goalkeeper",
                event_priority=30,
                start_x=tr.end_x,
                start_y=tr.end_y,
                related_loss_frame=tr.loss_frame,
                related_gain_frame=tr.gain_frame,
                confidence=conf,
                notes=notes,
            )
        event_name = "reception" if same_team else "interception"
        conf = 0.72 if same_team else 0.76
    
        return self._make_event(
            frame=tr.gain_frame,
            team_id=gain_team,
            player_id=gain_player,
            event_name=event_name,
            event_family="open_play",
            event_priority=30,
            start_x=tr.end_x,
            start_y=tr.end_y,
            related_loss_frame=tr.loss_frame,
            related_gain_frame=tr.gain_frame,
            confidence=conf,
            notes="same_team_reception" if same_team else "opponent_interception",
        )
    
    def classify_goalkeeper_event(self, tr, players_df, prior_loss_event):
        if prior_loss_event in ["shot_on_target", "shot_off_target"]:
            retain = self._goalkeeper_retains_after_gain(tr)
            return f"save_{'retain' if retain else 'deflect'}", 0.80, "gk_gain_after_shot"
    
        if prior_loss_event == "cross":
            retain = self._goalkeeper_retains_after_gain(tr)
            return f"claim_{'retain' if retain else 'deflect'}", 0.74, "gk_gain_after_cross"
    
        return "reception_from_loose_ball", 0.60, "gk_gain_without_shot_cross"
    
    def _goalkeeper_retains_after_gain(self, tr):
        if pd.isna(tr.gain_frame) or tr.gain_player is None:
            return False
    
        control_df = self.possession_control_df
        if control_df is None or control_df.empty:
            return False
    
        window = int(getattr(self, "goalkeeper_hold_seconds", 1.0) * self.fps)
    
        after = control_df[
            (control_df["frame"] >= int(tr.gain_frame))
            & (control_df["frame"] <= int(tr.gain_frame) + window)
        ]
    
        if after.empty:
            return False
    
        same_gk_frames = after[
            (after["ball_control"] == "possession")
            & (after["controller_id"].apply(lambda x: self._same_player(x, tr.gain_player)))
        ]
    
        return len(same_gk_frames) >= max(2, int(window * 0.5))
    
    def _first_control_after(self, control_df, frame):
        after = control_df[
            (control_df["frame"] > frame)
            & (control_df["ball_control"].isin(["possession", "duel"]))
        ]
        if after.empty:
            return None
        return int(after.iloc[0]["frame"])
    
    
    def _executor_row(self, frame, executor, players_df):
        pf = self._players_at_frame(players_df, frame, window=3)
        if pf.empty:
            return None
        hit = pf[pf["tracker_id"].apply(lambda x: self._same_player(x, executor))]
        if hit.empty:
            return None
        return hit.iloc[0]
    
    def _make_event(
        self,
        frame,
        team_id,
        player_id,
        event_name,
        event_family,
        event_priority,
        start_x=np.nan,
        start_y=np.nan,
        end_x=np.nan,
        end_y=np.nan,
        related_loss_frame=np.nan,
        related_gain_frame=np.nan,
        confidence=0.5,
        dead_ball_event=None,
        notes="",
        is_pass=False,
        successful=None,
        receiver_player=None,
        receiver_team=None,
        interception=False,
    ):
        return {
            "event_id": None,
            "frame": int(frame) if not pd.isna(frame) else np.nan,
            "time": float(frame) / self.fps if not pd.isna(frame) and self.fps > 0 else np.nan,
            "team_id": team_id,
            "player_id": player_id,
            "event_name": event_name,
            "event_family": event_family,
            "event_priority": event_priority,
            "dead_ball_event": dead_ball_event,
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "related_loss_frame": related_loss_frame,
            "related_gain_frame": related_gain_frame,
            "confidence": float(confidence),
            "notes": notes,
            "is_pass": bool(is_pass),
            "successful": successful,
            "receiver_player": receiver_player,
            "receiver_team": receiver_team,
            "interception": bool(interception),
        }
