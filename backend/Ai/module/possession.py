import numpy as np
import pandas as pd

try:
    from scipy.signal import savgol_filter
except Exception:
    def savgol_filter(values, window_length, polyorder, mode="interp"):
        return pd.Series(values, dtype="float64").rolling(
            window=window_length,
            center=True,
            min_periods=1,
        ).mean().to_numpy()


class possession_detector:
    def __init__(self, debug=True, coordinate_scale=1.0):
        self.debug = debug
        self.coordinate_scale = coordinate_scale
        self.ball_positions_log = []
        self.frame_states_log = []
        self.last_control_state = {
        "ball_control": "no_possession",
        "controller_id": None,
        "controller_team": None,
        "dist_to_ball": None,
        "confidence_score": 0.0,
    }
                # ===== Temporal confidence system =====
        self.temporal_confirm_frames = 2
        self.temporal_release_frames = 4
        self.temporal_duel_frames = 2

        self.pending_state = None
        self.pending_count = 0

        self.release_candidate_count = 0
        self.duel_candidate_count = 0
        self.control_hold_frames = 0
        self.max_control_hold_frames = 10
        self.possession_control_df = pd.DataFrame()
        self.possession_gains_df = pd.DataFrame()
        self.possession_losses_df = pd.DataFrame()

        # ===== Hybrid thresholds =====
        # base thresholds (never go below these)
        self.eps_angle_deg_base = 20.0
        self.eps_speed_base = 0.12
        self.eps_disp_base = 0.18
        
        self.eps_angle_deg_min = 18.0
        self.eps_angle_deg_max = 50.0
        
        self.eps_speed_min = 0.10
        self.eps_speed_max = 0.40
        
        self.eps_disp_min = 0.15
        self.eps_disp_max = 0.80
        self.player_positions_log = []

    def _dbg(self, msg):
        if self.debug:
            print(msg)

    def _print_section(self, title):
        if self.debug:
            print("\n" + "=" * 80)
            print(title)
            print("=" * 80)

    def _print_df_sample(self, df, name, cols=None, n=10):
        if not self.debug:
            return
        print(f"\n--- {name} | shape={df.shape} ---")
        if df.empty:
            print("[EMPTY DATAFRAME]")
            return
        if cols is not None:
            cols = [c for c in cols if c in df.columns]
            print(df[cols].head(n).to_string(index=False))
        else:
            print(df.head(n).to_string(index=False))

    def _print_series_stats(self, df, cols, name):
        if not self.debug:
            return
        valid_cols = [c for c in cols if c in df.columns]
        if not valid_cols:
            print(f"\n[{name}] No valid columns found for stats.")
            return
        print(f"\n--- {name} stats ---")
        print(df[valid_cols].describe(include="all").to_string())
    def _states_equal(self, a, b):
        if a is None or b is None:
            return False
        return (
            a.get("ball_control") == b.get("ball_control")
            and a.get("controller_id") == b.get("controller_id")
            and a.get("controller_team") == b.get("controller_team")
        )

    def _make_no_possession_state(self):
        return {
            "ball_control": "no_possession",
            "controller_id": None,
            "controller_team": None,
            "dist_to_ball": None,
            "confidence_score": 0.0,
        }

    def _confirm_state(self, state):
        self.pending_state = None
        self.pending_count = 0
        self.release_candidate_count = 0
        self.duel_candidate_count = 0
    
        self._update_last_control_state(state)
        return state
    def _apply_temporal_confidence(self, candidate_state, players=None, keep_possession_radius=None):
        last_state = {
            "ball_control": self.last_control_state["ball_control"],
            "controller_id": self.last_control_state["controller_id"],
            "controller_team": self.last_control_state["controller_team"],
            "dist_to_ball": self.last_control_state["dist_to_ball"],
            "confidence_score": self.last_control_state.get("confidence_score", 0.0),
        }
    
        # 1) نفس الحالة القديمة -> تأكيد مباشر
        if self._states_equal(candidate_state, last_state):
            self.pending_state = None
            self.pending_count = 0
            self.release_candidate_count = 0
            self.duel_candidate_count = 0
            return self._confirm_state(candidate_state)
    
        # 2) possession جديد -> يحتاج confirmation
        if candidate_state["ball_control"] == "possession":
            self.duel_candidate_count = 0
            self.release_candidate_count = 0
    
            if self.pending_state is not None and self._states_equal(candidate_state, self.pending_state):
                self.pending_count += 1
            else:
                self.pending_state = candidate_state.copy()
                self.pending_count = 1
    
            prev_id = self.last_control_state.get("controller_id")
            prev_team = self.last_control_state.get("controller_team")
    
            if prev_id is not None and players is not None and keep_possession_radius is not None:
                prev_player = players[players["tracker_id"] == prev_id]
                if not prev_player.empty:
                    prev_dist = float(prev_player.iloc[0]["dist_to_ball"])
    
                    nearest_dist = None
                    if not players.empty:
                        nearest_dist = float(players["dist_to_ball"].min())
    
                    if (
                        prev_dist <= keep_possession_radius
                        and nearest_dist is not None
                        and prev_dist <= nearest_dist + 0.12
                    ):
                        return {
                            "ball_control": "possession",
                            "controller_id": prev_id,
                            "controller_team": prev_team,
                            "dist_to_ball": prev_dist,
                            "confidence_score": max(
                                float(candidate_state.get("confidence_score", 0.0)),
                                float(last_state.get("confidence_score", 0.0)),
                            ),
                        }
    
            confirm_frames = 1 if (
                candidate_state["dist_to_ball"] is not None
                and candidate_state["dist_to_ball"] < 0.6
                and candidate_state.get("confidence_score", 0.0) >= 0.75
            ) else self.temporal_confirm_frames
    
            if self.pending_count >= confirm_frames:
                return self._confirm_state(candidate_state)
            
            if last_state["ball_control"] == "possession":
                return self._fallback_to_last_control()
            
            return self._make_no_possession_state()
    
        # 3) duel -> يحتاج confirmation لكن أقل خنقًا من الأول
        if candidate_state["ball_control"] == "duel":
            self.pending_state = None
            self.pending_count = 0
            self.release_candidate_count = 0
            self.duel_candidate_count += 1
    
            duel_conf = float(candidate_state.get("confidence_score", 0.0))
            required_duel_frames = 1 if duel_conf >= 0.72 else self.temporal_duel_frames
    
            if self.duel_candidate_count >= required_duel_frames:
                self.control_hold_frames = 0
                return candidate_state
    
            # قلل خنق الـ duel:
            # لو عندنا possession قديمة، نتمسك بيها فقط لو الـ duel لسه ضعيفة جدًا
            if last_state["ball_control"] == "possession" and duel_conf < 0.60:
                return last_state
    
            return {
                "ball_control": "duel",
                "controller_id": None,
                "controller_team": None,
                "dist_to_ball": candidate_state.get("dist_to_ball"),
                "confidence_score": duel_conf,
            }
    
        # 4) no_possession -> يحتاج release confirmation
        if candidate_state["ball_control"] == "no_possession":
            self.pending_state = None
            self.pending_count = 0
            self.duel_candidate_count = 0
            self.release_candidate_count += 1
    
            if (
                last_state["ball_control"] == "possession"
                and self.release_candidate_count < self.temporal_release_frames
            ):
                return self._fallback_to_last_control()
    
            self.control_hold_frames = 0
            return self._make_no_possession_state()
    
        return candidate_state
        
    def _fallback_to_last_control(self):
        if (
            self.last_control_state["ball_control"] == "possession"
            and self.control_hold_frames < self.max_control_hold_frames
        ):
            self.control_hold_frames += 1
            return {
                "ball_control": "possession",
                "controller_id": self.last_control_state["controller_id"],
                "controller_team": self.last_control_state["controller_team"],
                "dist_to_ball": self.last_control_state["dist_to_ball"],
                "confidence_score": self.last_control_state.get("confidence_score", 0.0),
            }
    
        return {
            "ball_control": "no_possession",
            "controller_id": None,
            "controller_team": None,
            "dist_to_ball": None,
            "confidence_score": 0.0,
        }
    def _update_last_control_state(self, state):
        self.last_control_state = {
            "ball_control": state["ball_control"],
            "controller_id": state.get("controller_id"),
            "controller_team": state.get("controller_team"),
            "dist_to_ball": state.get("dist_to_ball"),
            "confidence_score": state.get("confidence_score", 0.0),
        }
        self.control_hold_frames = 0
    def validate_input_frames(self, frames_df: pd.DataFrame, frame_states_df: pd.DataFrame):
        self._print_section("INPUT VALIDATION")

        required_frames_cols = {"frame", "time", "ball_x", "ball_y"}
        required_states_cols = {"frame", "ball_control", "controller_id", "controller_team"}

        print("frames_df columns at validation:", frames_df.columns.tolist())
        print("frame_states_df columns at validation:", frame_states_df.columns.tolist())

        missing_frames = required_frames_cols - set(frames_df.columns)
        missing_states = required_states_cols - set(frame_states_df.columns)

        if missing_frames:
            raise ValueError(
                f"frames_df is missing columns: {missing_frames}. "
                f"Available columns: {frames_df.columns.tolist()}"
            )

        if missing_states:
            raise ValueError(
                f"frame_states_df is missing columns: {missing_states}. "
                f"Available columns: {frame_states_df.columns.tolist()}"
            )

        self._dbg(f"frames_df rows: {len(frames_df)}")
        self._dbg(f"frame_states_df rows: {len(frame_states_df)}")

        if frames_df["frame"].duplicated().any():
            dupes = frames_df[frames_df["frame"].duplicated()]["frame"].tolist()[:10]
            self._dbg(f"[WARNING] Duplicate frames in frames_df. Sample: {dupes}")

        if frame_states_df["frame"].duplicated().any():
            dupes = frame_states_df[frame_states_df["frame"].duplicated()]["frame"].tolist()[:10]
            self._dbg(f"[WARNING] Duplicate frames in frame_states_df. Sample: {dupes}")

    # =========================
    # Ball motion
    # =========================
    def _safe_unit_vectors(self, x_arr, y_arr):
        norm = np.sqrt(x_arr**2 + y_arr**2)
        ux = np.full_like(x_arr, np.nan, dtype=float)
        uy = np.full_like(y_arr, np.nan, dtype=float)

        valid = (~np.isnan(norm)) & (norm > 1e-12)
        ux[valid] = x_arr[valid] / norm[valid]
        uy[valid] = y_arr[valid] / norm[valid]
        return ux, uy

    def _angle_deg_between_vectors(self, ax, ay, bx, by):
        if any(pd.isna(v) for v in [ax, ay, bx, by]):
            return np.nan
        dot = ax * bx + ay * by
        dot = np.clip(dot, -1.0, 1.0)
        return float(np.degrees(np.arccos(dot)))

    def compute_ball_motion(
        self,
        df: pd.DataFrame,
        x_col: str = "ball_x",
        y_col: str = "ball_y",
        time_col: str = "time",
        smoothing: bool = True,
        window: int = 9,
        polyorder: int = 2,
    ):
        """
        Compute ball velocity, displacement, smoothed coordinates,
        incoming/outgoing directions and incoming/outgoing speeds.
        Robust against NaNs/Infs in ball positions.
        """
        self._print_section("STEP 1: COMPUTE BALL MOTION")

        out = df.copy()

        # -----------------------------
        # 1) safe numeric conversion
        # -----------------------------
        out[x_col] = pd.to_numeric(out[x_col], errors="coerce")
        out[y_col] = pd.to_numeric(out[y_col], errors="coerce")
        out[time_col] = pd.to_numeric(out[time_col], errors="coerce")

        x_raw = out[x_col].astype(float) 
        y_raw = out[y_col].astype(float) 
        t = out[time_col].astype(float)

        # replace inf with nan first
        x_raw = x_raw.replace([np.inf, -np.inf], np.nan)
        y_raw = y_raw.replace([np.inf, -np.inf], np.nan)
        t = t.replace([np.inf, -np.inf], np.nan)

        # time fallback
        if t.isna().any():
            t = t.interpolate(limit_direction="both")
            t = t.ffill().bfill()

        # -----------------------------
        # 2) fill ball NaNs before smoothing
        # -----------------------------
        x_filled = x_raw.interpolate(limit_direction="both")
        y_filled = y_raw.interpolate(limit_direction="both")

        # لو كل القيم NaN
        if x_filled.isna().all() or y_filled.isna().all():
            out["ball_x_smooth"] = np.nan
            out["ball_y_smooth"] = np.nan
            out["dx"] = np.nan
            out["dy"] = np.nan
            out["ball_vx"] = np.nan
            out["ball_vy"] = np.nan
            out["ball_speed"] = np.nan
            out["ball_displacement"] = np.nan
            out["dir_in_x"] = np.nan
            out["dir_in_y"] = np.nan
            out["speed_in"] = np.nan
            out["dir_out_x"] = np.nan
            out["dir_out_y"] = np.nan
            out["speed_out"] = np.nan
            out["speed_delta"] = np.nan
            out["ball_dir_cos_change"] = np.nan
            out["ball_angle_change"] = np.nan
            out["ball_speed_next"] = np.nan
            out["ball_speed_change"] = np.nan
            return out

        x = x_filled.to_numpy(dtype=float)
        y = y_filled.to_numpy(dtype=float)
        t = t.to_numpy(dtype=float)

        # -----------------------------
        # 3) smoothing safely
        # -----------------------------
        valid_len = len(out)
        use_smoothing = (
            smoothing
            and valid_len >= 3
            and polyorder < valid_len
        )

        if use_smoothing:
            # لازم window يبقى odd وكمان <= len(out)
            safe_window = min(window, valid_len if valid_len % 2 == 1 else valid_len - 1)
            if safe_window < 3:
                safe_window = 3
            if safe_window % 2 == 0:
                safe_window -= 1
            if safe_window <= polyorder:
                safe_window = polyorder + 2
                if safe_window % 2 == 0:
                    safe_window += 1
                if safe_window > valid_len:
                    safe_window = valid_len if valid_len % 2 == 1 else valid_len - 1

            if safe_window >= 3 and safe_window > polyorder:
                x_s = savgol_filter(x, window_length=safe_window, polyorder=polyorder, mode="interp")
                y_s = savgol_filter(y, window_length=safe_window, polyorder=polyorder, mode="interp")
                self._dbg(f"Savitzky-Golay smoothing applied | window={safe_window}, polyorder={polyorder}")
            else:
                x_s, y_s = x.copy(), y.copy()
                self._dbg("Smoothing skipped (safe window invalid).")
        else:
            x_s, y_s = x.copy(), y.copy()
            self._dbg("Smoothing skipped.")

        # رجع NaN في الأماكن اللي الكرة كانت غايبة فيها أصلًا
        orig_missing = x_raw.isna() | y_raw.isna()
        x_s = np.where(orig_missing.to_numpy(), np.nan, x_s)
        y_s = np.where(orig_missing.to_numpy(), np.nan, y_s)

        out["ball_x_smooth"] = x_s
        out["ball_y_smooth"] = y_s

        # -----------------------------
        # 4) motion with safe dt
        # -----------------------------
        dt = np.diff(t, prepend=np.nan)
        dx = np.diff(x_s, prepend=np.nan)
        dy = np.diff(y_s, prepend=np.nan)

        # أي dt <= 0 نخليه NaN عشان مفيش division by zero / inf
        dt = np.where((dt <= 0) | ~np.isfinite(dt), np.nan, dt)

        with np.errstate(divide="ignore", invalid="ignore"):
            vx = dx / dt
            vy = dy / dt

        speed = np.sqrt(vx**2 + vy**2)
        displacement = np.sqrt(dx**2 + dy**2)

        # clean infs
        vx = np.where(np.isfinite(vx), vx, np.nan)
        vy = np.where(np.isfinite(vy), vy, np.nan)
        speed = np.where(np.isfinite(speed), speed, np.nan)
        displacement = np.where(np.isfinite(displacement), displacement, np.nan)

        vx[0] = np.nan
        vy[0] = np.nan
        speed[0] = np.nan
        displacement[0] = np.nan

        out["dx"] = dx
        out["dy"] = dy
        out["ball_vx"] = vx
        out["ball_vy"] = vy
        out["ball_speed"] = speed
        out["ball_displacement"] = displacement

        # incoming direction/speed at frame f = motion from f-1 -> f
        dir_in_x, dir_in_y = self._safe_unit_vectors(dx, dy)
        out["dir_in_x"] = dir_in_x
        out["dir_in_y"] = dir_in_y
        out["speed_in"] = speed

        # outgoing direction/speed at frame f = motion from f -> f+1
        dx_next = np.roll(dx, -1)
        dy_next = np.roll(dy, -1)
        speed_next = np.roll(speed, -1)

        dx_next[-1] = np.nan
        dy_next[-1] = np.nan
        speed_next[-1] = np.nan

        dir_out_x, dir_out_y = self._safe_unit_vectors(dx_next, dy_next)
        out["dir_out_x"] = dir_out_x
        out["dir_out_y"] = dir_out_y
        out["speed_out"] = speed_next
        out["speed_delta"] = (out["speed_out"] - out["speed_in"]).abs()

        angle_deg_series = []
        cos_series = []
        for ax, ay, bx, by in zip(dir_in_x, dir_in_y, dir_out_x, dir_out_y):
            if any(np.isnan(v) for v in [ax, ay, bx, by]):
                cos_series.append(np.nan)
                angle_deg_series.append(np.nan)
            else:
                dot = float(np.clip(ax * bx + ay * by, -1.0, 1.0))
                cos_series.append(dot)
                angle_deg_series.append(float(np.degrees(np.arccos(dot)))) # radians for backward compatibility

        out["ball_dir_cos_change"] = cos_series
        out["ball_angle_change"] = angle_deg_series
        out["ball_speed_next"] = out["speed_out"]
        out["ball_speed_change"] = out["speed_delta"]

        self._print_df_sample(
            out,
            "ball motion sample",
            [
                "frame", "time", "ball_x", "ball_y",
                "ball_x_smooth", "ball_y_smooth",
                "dx", "dy", "ball_vx", "ball_vy",
                "ball_speed", "ball_displacement",
                "dir_in_x", "dir_in_y",
                "dir_out_x", "dir_out_y",
                "speed_in", "speed_out", "speed_delta",
            ],
            n=12
        )

        self._print_series_stats(
            out,
            ["ball_speed", "ball_displacement", "ball_vx", "ball_vy", "speed_delta"],
            "ball motion"
        )

        self._dbg(f"NaN ball_speed count: {out['ball_speed'].isna().sum()}")
        self._dbg(f"NaN ball_displacement count: {out['ball_displacement'].isna().sum()}")

        return out

    def compute_direction_angle(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Kept for compatibility. All needed features are already computed in compute_ball_motion.
        """
        self._print_section("STEP 2: COMPUTE DIRECTION ANGLE / SPEED CHANGE")

        out = df.copy()

        self._print_df_sample(
            out,
            "direction angle sample",
            [
                "frame",
                "dx", "dy",
                "ball_dir_cos_change",
                "ball_angle_change",
                "ball_speed",
                "ball_speed_next",
                "ball_speed_change",
                "dir_in_x", "dir_in_y",
                "dir_out_x", "dir_out_y",
                "speed_in", "speed_out", "speed_delta",
            ],
            n=12
        )

        self._print_series_stats(
            out,
            ["ball_dir_cos_change", "ball_angle_change", "ball_speed_change"],
            "direction/speed change"
        )

        self._dbg(f"NaN direction cosine count: {out['ball_dir_cos_change'].isna().sum()}")
        self._dbg(f"NaN angle count: {out['ball_angle_change'].isna().sum()}")
        self._dbg(f"NaN speed change count: {out['ball_speed_change'].isna().sum()}")

        return out

    def add_ball_direction_change(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.compute_direction_angle(df)

    # =========================
    # Control / intervals
    # =========================
    def classify_control_frame(
        self,
        ball_x,
        ball_y,
        players_df,
        pz_radius=1.18,
        dz_radius=1.75,
        keep_possession_radius=1.30,
        duel_margin=0.4,
    ):
        players = players_df.copy()
    
        # لو المدخلات ناقصة
        if players.empty or pd.isna(ball_x) or pd.isna(ball_y):
            candidate_state = self._make_no_possession_state()
            return self._apply_temporal_confidence(candidate_state)
    
        players["x"] = pd.to_numeric(players["x"], errors="coerce").astype(float) / self.coordinate_scale
        players["y"] = pd.to_numeric(players["y"], errors="coerce").astype(float) / self.coordinate_scale
        ball_x = float(ball_x) 
        ball_y = float(ball_y) 
    
        players = players.dropna(subset=["x", "y"]).copy()
        if players.empty:
            candidate_state = self._make_no_possession_state()
            return self._apply_temporal_confidence(candidate_state)
    
        players["dist_to_ball"] = np.hypot(players["x"] - ball_x, players["y"] - ball_y)
        players = players.sort_values("dist_to_ball").reset_index(drop=True)
    
        nearest = players.iloc[0]
        second = players.iloc[1] if len(players) > 1 else None
    
        nearest_id = nearest["tracker_id"]
        nearest_team = nearest["team_id"]
        nearest_dist = float(nearest["dist_to_ball"])
    
        second_dist = float(second["dist_to_ball"]) if second is not None else None
        second_team = second["team_id"] if second is not None else None
    
        dist_gap = None if second_dist is None else abs(second_dist - nearest_dist)
    
        # confidence للـ duel:
        # كل ما الفرق بين أول اتنين يقل، والثنين يبقوا قريبين من الكرة، الـ duel تبقى أقوى
        duel_confidence = 0.0
        if second_dist is not None:
            proximity_strength = max(0.0, 1.0 - (nearest_dist / (dz_radius + 1e-6)))
            balance_strength = max(0.0, 1.0 - (dist_gap / (duel_margin + 1e-6)))
            duel_confidence = 0.5 * proximity_strength + 0.5 * balance_strength
            duel_confidence = float(np.clip(duel_confidence, 0.0, 1.0))
    
        contested = (
            second is not None
            and nearest_dist <= dz_radius
            and second_dist <= dz_radius
            and second_team != nearest_team
            and (
                dist_gap <= duel_margin
                or nearest_dist > pz_radius * 0.90
            )
        )
    
        if contested:
            candidate_state = {
                "ball_control": "duel",
                "controller_id": None,
                "controller_team": None,
                "dist_to_ball": nearest_dist,
                "confidence_score": duel_confidence,
            }
            return self._apply_temporal_confidence(
                candidate_state,
                players=players,
                keep_possession_radius=keep_possession_radius,
            )
    
        # 2) direct possession
        score_ok = False
        possession_confidence = 0.0
    
        if second_dist is not None:
            score = nearest_dist / (second_dist + 1e-6)
            score_ok = (nearest_dist <= keep_possession_radius) and (score < 0.72)
    
            # confidence للـ possession:
            # أقرب لاعب لازم يكون قريب، وكمان أوضح من الثاني
            proximity_strength = max(0.0, 1.0 - (nearest_dist / (keep_possession_radius + 1e-6)))
            separation_strength = max(0.0, 1.0 - (score / 0.72))
            possession_confidence = 0.55 * proximity_strength + 0.45 * separation_strength
        else:
            # لو لاعب واحد ظاهر فقط
            if nearest_dist <= pz_radius:
                possession_confidence = max(0.0, 1.0 - (nearest_dist / (pz_radius + 1e-6)))
    
        possession_confidence = float(np.clip(possession_confidence, 0.0, 1.0))
    
        if nearest_dist <= pz_radius or score_ok:
            candidate_state = {
                "ball_control": "possession",
                "controller_id": nearest_id,
                "controller_team": nearest_team,
                "dist_to_ball": nearest_dist,
                "confidence_score": possession_confidence,
            }
            return self._apply_temporal_confidence(
                candidate_state,
                players=players,
                keep_possession_radius=keep_possession_radius,
            )
    
        # 3) fallback no possession
        candidate_state = self._make_no_possession_state()
        return self._apply_temporal_confidence(
            candidate_state,
            players=players,
            keep_possession_radius=keep_possession_radius,
        )

    def smooth_control_states(self, frame_states: pd.DataFrame, max_gap_frames: int = None) -> pd.DataFrame:
        out = frame_states.copy().sort_values("frame").reset_index(drop=True)
    
        if out.empty:
            return out
    
        if max_gap_frames is None:
            max_gap_frames = max(3, int(getattr(self, "fps", 25) * 0.20))
    
        # اقفل no_possession القصير بين نفس اللاعب
        intervals = self.build_control_intervals(out)
    
        for _, g in intervals.groupby("interval_id"):
            first = g.iloc[0]
    
            if first["ball_control"] != "no_possession":
                continue
    
            if len(g) > max_gap_frames:
                continue
    
            start_idx = g.index.min()
            end_idx = g.index.max()
    
            if start_idx == 0 or end_idx >= len(out) - 1:
                continue
    
            prev_row = out.iloc[start_idx - 1]
            next_row = out.iloc[end_idx + 1]
    
            same_prev_next = (
                prev_row["ball_control"] == "possession"
                and next_row["ball_control"] == "possession"
                and self._same_controller_id(prev_row["controller_id"], next_row["controller_id"])
            )
    
            if same_prev_next:
                out.loc[start_idx:end_idx, "ball_control"] = "possession"
                out.loc[start_idx:end_idx, "controller_id"] = prev_row["controller_id"]
                out.loc[start_idx:end_idx, "controller_team"] = prev_row["controller_team"]
                out.loc[start_idx:end_idx, "confidence_score"] = max(
                    float(prev_row.get("confidence_score", 0.5) or 0.5),
                    float(next_row.get("confidence_score", 0.5) or 0.5),
                )
    
        return out

    def build_control_intervals(self, frame_states: pd.DataFrame) -> pd.DataFrame:
        out = frame_states.copy()
        out = out.sort_values("frame").reset_index(drop=True)

        key = (
            out["ball_control"].astype(str) + "|" +
            out["controller_id"].astype(str) + "|" +
            out["controller_team"].astype(str)
        )
        out["interval_id"] = (key != key.shift(1)).cumsum()
        return out

    def remove_short_intervals(self, control_df: pd.DataFrame, min_frames: int = 2) -> pd.DataFrame:
        self._print_section("STEP 3: REMOVE SHORT INTERVALS")
    
        out = control_df.copy()
    
        while True:
            interval_sizes = out.groupby("interval_id").size().rename("interval_size")
            out = out.drop(columns=["interval_size"], errors="ignore").merge(interval_sizes, on="interval_id", how="left")
    
            self._dbg("Interval sizes before cleanup:")
            if self.debug:
                print(interval_sizes.describe().to_string())
    
            short_ids = interval_sizes[interval_sizes < min_frames].index.tolist()
            self._dbg(f"Short interval ids (<{min_frames} frames): {short_ids[:20]}")
            self._dbg(f"Short intervals count: {len(short_ids)}")
    
            if not short_ids:
                break
    
            changed_any = False
    
            for short_id in short_ids:
                idx = out.index[out["interval_id"] == short_id].tolist()
                if not idx:
                    continue
    
                first_idx = idx[0]
                last_idx = idx[-1]
    
                prev_idx = first_idx - 1
                next_idx = last_idx + 1
    
                prev_exists = prev_idx >= 0
                next_exists = next_idx < len(out)
    
                prev_state = out.loc[prev_idx, ["ball_control", "controller_id", "controller_team"]] if prev_exists else None
                next_state = out.loc[next_idx, ["ball_control", "controller_id", "controller_team"]] if next_exists else None
    
                replacement = None
                if prev_exists and next_exists and prev_state.equals(next_state):
                    replacement = prev_state
                if replacement is not None:
                    out.loc[idx, "ball_control"] = replacement["ball_control"]
                    out.loc[idx, "controller_id"] = replacement["controller_id"]
                    out.loc[idx, "controller_team"] = replacement["controller_team"]
                    changed_any = True
    
            out = out.drop(columns=["interval_size"], errors="ignore")
            out = self.build_control_intervals(out)
    
            if not changed_any:
                break
    
        new_interval_sizes = out.groupby("interval_id").size()
        self._dbg("Interval sizes after cleanup:")
        if self.debug:
            print(new_interval_sizes.describe().to_string())
    
        self._print_df_sample(
            out,
            "control after interval cleanup",
            ["frame", "ball_control", "controller_id", "controller_team", "interval_id"],
            n=20
        )
    
        return out
    # =========================
    # Threshold helpers (Hybrid)
    # =========================
    def _compute_hybrid_thresholds(self, control_df: pd.DataFrame):
        angle_deg_vals = []
        for ax, ay, bx, by in zip(
            control_df["dir_in_x"],
            control_df["dir_in_y"],
            control_df["dir_out_x"],
            control_df["dir_out_y"]
        ):
            ang = self._angle_deg_between_vectors(ax, ay, bx, by)
            if not pd.isna(ang):
                angle_deg_vals.append(ang)

        speed_delta_vals = control_df["speed_delta"].dropna().to_numpy()
        disp_vals = control_df["ball_displacement"].dropna().to_numpy()

        if len(angle_deg_vals) > 0:
            eps_angle_deg = np.percentile(angle_deg_vals, 70)
        else:
            eps_angle_deg = self.eps_angle_deg_base

        if len(speed_delta_vals) > 0:
            eps_speed = np.percentile(speed_delta_vals, 75)
        else:
            eps_speed = self.eps_speed_base

        if len(disp_vals) > 0:
            eps_disp = np.percentile(disp_vals, 60)
        else:
            eps_disp = self.eps_disp_base

        eps_angle_deg = float(np.clip(max(self.eps_angle_deg_base, eps_angle_deg),
                                      self.eps_angle_deg_min, self.eps_angle_deg_max))
        eps_speed = float(np.clip(max(self.eps_speed_base, eps_speed),
                                  self.eps_speed_min, self.eps_speed_max))
        eps_disp = float(np.clip(max(self.eps_disp_base, eps_disp),
                                 self.eps_disp_min, self.eps_disp_max))

        self._dbg(
            f"Hybrid thresholds | eps_angle_deg={eps_angle_deg:.4f}, "
            f"eps_speed={eps_speed:.4f}, eps_disp={eps_disp:.4f}"
        )

        return eps_angle_deg, eps_speed, eps_disp

    # =========================
    # Gains / losses (Hybrid)
    # =========================
    def detect_possession_gains(self, control_df: pd.DataFrame):
        self._print_section("STEP 4: DETECT POSSESSION GAINS")
    
        gains = []
        out = control_df.sort_values("frame").reset_index(drop=True)
    
        if "interval_id" not in out.columns:
            out = self.build_control_intervals(out)
    
        grouped = list(out.groupby("interval_id"))
    
        for i, (interval_id, group) in enumerate(grouped):
            first = group.iloc[0]
    
            if first["ball_control"] != "possession":
                continue
    
            controller_id = first["controller_id"]
            if controller_id is None or pd.isna(controller_id):
                continue
    
            # تجاهل intervals ضعيفة جدًا
            if len(group) < 1:
                continue
    
            if "ball_confidence" in group.columns:
                real_conf = group["ball_confidence"].fillna(0).mean()
                if real_conf < 0.10:
                    continue
    
            # لو نفس اللاعب كان ماسك قبلها بفاصل صغير، مش gain جديد
            if i > 0:
                prev_group = grouped[i - 1][1]
                prev_last = prev_group.iloc[-1]
    
                if (
                    prev_last["ball_control"] == "possession"
                    and self._same_controller_id(prev_last["controller_id"], controller_id)
                ):
                    gap = int(first["frame"]) - int(prev_last["frame"])
                    if gap <= max(4, int(getattr(self, "fps", 25) * 0.20)):
                        continue
    
            mean_conf = float(group["confidence_score"].mean()) if "confidence_score" in group.columns else np.nan
            max_conf = float(group["confidence_score"].max()) if "confidence_score" in group.columns else np.nan
    
            gains.append({
                "frame": int(first["frame"]),
                "tracker_id": controller_id,
                "team_id": first["controller_team"],
                "event": "possession_gain",
                "interval_id": int(interval_id),
                "frames_in_interval": int(len(group)),
                "interval_angle_deg": np.nan,
                "direction_changed": False,
                "speed_changed": False,
                "eps_angle_deg": np.nan,
                "eps_speed": np.nan,
                "mean_confidence": mean_conf,
                "max_confidence": max_conf,
            })
    
        gains_df = pd.DataFrame(gains)
        self._dbg(f"Total gains detected: {len(gains_df)}")
        self._print_df_sample(gains_df, "gains_df", None, n=30)
        return gains_df

    def _same_controller_id(self, a, b):
        if a is None or pd.isna(a) or b is None or pd.isna(b):
            return False
        try:
            return int(float(a)) == int(float(b))
        except Exception:
            return str(a) == str(b)
    
    
    def _ball_outside_pz_next_frame(self, control_df: pd.DataFrame, idx: int, controller_id, pz_radius: float):
        if idx + 1 >= len(control_df):
            return False
    
        next_row = control_df.iloc[idx + 1]
    
        curr_frame = int(control_df.iloc[idx]["frame"])
        next_frame = int(next_row["frame"])
        if next_frame != curr_frame + 1:
            return False
    
        same_controller = (
            next_row["ball_control"] == "possession"
            and self._same_controller_id(next_row["controller_id"], controller_id)
        )
    
        if same_controller:
            return False
        
        # لازم كمان الكرة تكون فعلاً خرجت بعيد
        if not pd.isna(next_row["dist_to_ball"]):
            return float(next_row["dist_to_ball"]) > (pz_radius * 1.2)
        
        return True
    def detect_possession_losses(self, control_df: pd.DataFrame):
        self._print_section("STEP 5: DETECT POSSESSION LOSSES")
    
        losses = []
        out = control_df.sort_values("frame").reset_index(drop=True)
    
        if "interval_id" not in out.columns:
            out = self.build_control_intervals(out)
    
        grouped = list(out.groupby("interval_id"))
    
        for i, (interval_id, group) in enumerate(grouped):
            first = group.iloc[0]
            last = group.iloc[-1]
    
            if first["ball_control"] != "possession":
                continue
    
            controller_id = first["controller_id"]
            controller_team = first["controller_team"]
    
            if controller_id is None or pd.isna(controller_id):
                continue
    
            # آخر possession interval مش لازم loss
            if i >= len(grouped) - 1:
                continue
    
            next_possession = None
    
            for j in range(i + 1, len(grouped)):
                ng = grouped[j][1]
                nf = ng.iloc[0]
    
                if nf["ball_control"] == "possession":
                    next_possession = nf
                    break
    
                # لو no_possession طويل جدًا، اعتبرها dead/open gap وسيبها
                gap = int(nf["frame"]) - int(last["frame"])
                if gap > max(25, int(getattr(self, "fps", 25) * 1.0)):
                    break
    
            if next_possession is None:
                continue
    
            next_controller = next_possession["controller_id"]
    
            if self._same_controller_id(controller_id, next_controller):
                continue
    
            frame_f = int(last["frame"])
            ball_disp_f = last.get("ball_displacement", np.nan)
            row_conf = float(last["confidence_score"]) if "confidence_score" in out.columns and not pd.isna(last["confidence_score"]) else np.nan
    
            losses.append({
                "frame": frame_f,
                "tracker_id": controller_id,
                "team_id": controller_team,
                "event": "possession_loss",
                "interval_id": int(interval_id),
                "ball_displacement": float(ball_disp_f) if not pd.isna(ball_disp_f) else np.nan,
                "left_pz_next": True,
                "to_state": "possession",
                "next_controller": next_controller,
                "eps_disp": np.nan,
                "confidence_score": row_conf,
            })
    
        losses_df = pd.DataFrame(losses)
        self._dbg(f"Total losses detected: {len(losses_df)}")
        self._print_df_sample(losses_df, "losses_df", None, n=30)
        return losses_df

    # =========================
    # Post-validation
    # =========================
    def validate_outputs(self, control_df, gains_df, losses_df):
        self._print_section("STEP 6: OUTPUT VALIDATION")

        self._dbg(f"control_df rows: {len(control_df)}")
        self._dbg(f"gains_df rows: {len(gains_df)}")
        self._dbg(f"losses_df rows: {len(losses_df)}")

        if not control_df.empty:
            self._dbg("\nball_control distribution:")
            print(control_df["ball_control"].value_counts(dropna=False).to_string())

            if "interval_id" in control_df.columns:
                interval_sizes = control_df.groupby("interval_id").size()
                self._dbg("\ninterval size stats:")
                print(interval_sizes.describe().to_string())

        if not gains_df.empty:
            self._dbg("\nGain count by player:")
            print(gains_df["tracker_id"].value_counts().to_string())
        else:
            self._dbg("[WARNING] gains_df is empty")

        if not losses_df.empty:
            self._dbg("\nLoss count by player:")
            print(losses_df["tracker_id"].value_counts().to_string())
        else:
            self._dbg("[WARNING] losses_df is empty")

        if not gains_df.empty and not losses_df.empty:
            self._dbg(f"\nGain/Loss diff = {len(gains_df) - len(losses_df)}")

        suspicious = []

        if gains_df.empty:
            suspicious.append("No possession gains detected")
        if losses_df.empty:
            suspicious.append("No possession losses detected")

        if not control_df.empty:
            if "confidence_score" in control_df.columns:
                self._dbg("\nconfidence_score stats:")
                print(control_df["confidence_score"].describe().to_string())
            
                self._dbg("\nAverage confidence by state:")
                print(control_df.groupby("ball_control")["confidence_score"].mean().to_string())
            possession_count = (control_df["ball_control"] == "possession").sum()
            if possession_count == 0:
                suspicious.append("No possession frames found at all")

            duel_count = (control_df["ball_control"] == "duel").sum()
            if duel_count > len(control_df) * 0.5:
                suspicious.append("Too many duel frames (>50%)")

        if not gains_df.empty and not losses_df.empty:
            if abs(len(gains_df) - len(losses_df)) > max(5, 0.3 * max(len(gains_df), 1)):
                suspicious.append("Large mismatch between gains and losses counts")

        if suspicious:
            self._dbg("\n[WARNINGS]")
            for s in suspicious:
                self._dbg(f"- {s}")
        else:
            self._dbg("\nNo major output warnings.")

    # =========================
    # Main run
    # =========================
    def compute_possession(self):
        frames_df = pd.DataFrame(self.ball_positions_log)
        frame_states_df = pd.DataFrame(self.frame_states_log)

        print("ball_positions_log first 3:", self.ball_positions_log[:3])
        print("frame_states_log first 3:", self.frame_states_log[:3])

        print("frames_df columns:", frames_df.columns.tolist())
        print("frame_states_df columns:", frame_states_df.columns.tolist())

        print("frames_df head:")
        print(frames_df.head())

        print("frame_states_df head:")
        print(frame_states_df.head())

        control_df, gains_df, losses_df = self.run(
            frames_df=frames_df,
            frame_states=frame_states_df
        )

        self.possession_control_df = control_df
        self.possession_gains_df = gains_df
        self.possession_losses_df = losses_df

        return control_df, gains_df, losses_df

    def run(self, frames_df: pd.DataFrame, frame_states: pd.DataFrame):
        self.validate_input_frames(frames_df, frame_states)

        frames_df = frames_df.sort_values("frame").reset_index(drop=True)
        frame_states = frame_states.sort_values("frame").reset_index(drop=True)

        frames_df = self.compute_ball_motion(
            frames_df,
            x_col="ball_x",
            y_col="ball_y",
            time_col="time"
        )

        frames_df = self.compute_direction_angle(frames_df)

        self._print_section("STEP 3.5: MERGE CONTROL WITH BALL FEATURES")

        frame_feature_cols = [
                    "frame",
                    "ball_speed",
                    "ball_displacement",
                    "ball_dir_cos_change",
                    "ball_angle_change",
                    "ball_speed_change",
                    "ball_x_smooth",
                    "ball_y_smooth",
                    "dir_in_x",
                    "dir_in_y",
                    "dir_out_x",
                    "dir_out_y",
                    "speed_in",
                    "speed_out",
                    "speed_delta",
                ]

        for col in ["ball_visible", "ball_used_fallback", "ball_confidence"]:
                    if col in frames_df.columns:
                        frame_feature_cols.append(col)

        control_df = frame_states.merge(
                    frames_df[frame_feature_cols],
                    on="frame",
                    how="left"
                )
        for col in ["has_pitch_transform", "num_players", "num_goalkeepers", "num_referees"]:
            if col in frame_states.columns and col not in control_df.columns:
                control_df[col] = frame_states[col].values
        self._print_df_sample(
            control_df,
            "merged control_df before intervals",
            [
                "frame", "ball_control", "controller_id", "controller_team",
                "dist_to_ball",
                "ball_speed", "ball_displacement",
                "ball_dir_cos_change", "ball_angle_change", "ball_speed_change",
                "dir_in_x", "dir_in_y", "dir_out_x", "dir_out_y",
                "speed_in", "speed_out", "speed_delta",
            ],
            n=20
        )

        control_df = self.smooth_control_states(control_df)
        control_df = self.build_control_intervals(control_df)
        control_df = self.remove_short_intervals(control_df, min_frames=2)
        gains_df = self.detect_possession_gains(control_df)
        losses_df = self.detect_possession_losses(control_df)

        self.validate_outputs(control_df, gains_df, losses_df)

        self._print_section("FINAL DEBUG SNAPSHOT")
        debug_cols = [
            "frame", "ball_control", "controller_id", "controller_team", "dist_to_ball",
            "ball_speed", "ball_displacement",
            "ball_dir_cos_change", "ball_angle_change",
            "ball_speed_change", "interval_id",
            "dir_in_x", "dir_in_y", "dir_out_x", "dir_out_y",
            "speed_in", "speed_out", "speed_delta","confidence_score",
        ]
        self._print_df_sample(control_df, "final control_df", debug_cols, n=50)

        return control_df, gains_df, losses_df
