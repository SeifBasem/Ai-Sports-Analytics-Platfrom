import os
from pathlib import Path
from collections import Counter

import cv2
import numpy as np
from tensorflow.keras.applications.vgg16 import preprocess_input


class FootballActionAnalytics:
    """
    Clip-Based Football Action Analytics Dashboard

    This class analyzes multiple short clips that belong to ONE player.
    It does NOT use player ID, team ID, timestamp, tracking, or full-match timeline.

    Main input:
    - trained action classification model
    - folder path or list of video clip paths
    - class names
    - preprocessing settings

    Main output:
    - frontend-friendly dashboard dictionary / JSON
    """

    def __init__(
        self,
        model,
        clips,
        class_names,
        seq_len=10,
        frame_size=(150, 150),
        allowed_extensions=None,
        convert_bgr_to_rgb=True,
        verbose=False
    ):
        self.model = model
        self.clips = clips
        self.class_names = class_names
        self.seq_len = seq_len
        self.frame_size = frame_size
        self.allowed_extensions = allowed_extensions or [".mp4", ".avi", ".mov", ".mkv"]
        self.convert_bgr_to_rgb = convert_bgr_to_rgb
        self.verbose = verbose

        self.clip_paths = []
        self.prediction_records = []
        self.failed_clips = []

        self._validate_basic_inputs()
        self.clip_paths = self._load_clip_paths()

    # =========================================================
    # 1) Basic validation
    # =========================================================

    def _validate_basic_inputs(self):
        if self.model is None:
            raise ValueError("model cannot be None.")

        if not hasattr(self.model, "predict"):
            raise ValueError("model must have a predict() method.")

        if not self.class_names or not isinstance(self.class_names, list):
            raise ValueError("class_names must be a non-empty list.")

        if not isinstance(self.seq_len, int) or self.seq_len <= 0:
            raise ValueError("seq_len must be a positive integer.")

        if (
            not isinstance(self.frame_size, tuple)
            or len(self.frame_size) != 2
            or self.frame_size[0] <= 0
            or self.frame_size[1] <= 0
        ):
            raise ValueError("frame_size must be a tuple like (150, 150).")

    # =========================================================
    # 2) Load clips from folder or list
    # =========================================================

    def _load_clip_paths(self):
        if self.clips is None:
            return []

        clip_paths = []

        # Case 1: clips is a folder path
        if isinstance(self.clips, str):
            folder = Path(self.clips)

            if not folder.exists():
                self.failed_clips.append({
                    "clip_name": folder.name,
                    "clip_path": str(folder),
                    "error": "Folder path does not exist"
                })
                return []

            if not folder.is_dir():
                self.failed_clips.append({
                    "clip_name": folder.name,
                    "clip_path": str(folder),
                    "error": "Provided path is not a folder"
                })
                return []

            for file_path in sorted(folder.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in self.allowed_extensions:
                    clip_paths.append(str(file_path))
                elif file_path.is_file():
                    self.failed_clips.append({
                        "clip_name": file_path.name,
                        "clip_path": str(file_path),
                        "error": "Unsupported file extension"
                    })

        # Case 2: clips is a list of clip paths
        elif isinstance(self.clips, list):
            for clip in self.clips:
                clip_path = Path(clip)

                if clip_path.suffix.lower() not in self.allowed_extensions:
                    self.failed_clips.append({
                        "clip_name": clip_path.name,
                        "clip_path": str(clip_path),
                        "error": "Unsupported file extension"
                    })
                    continue

                if not clip_path.exists():
                    self.failed_clips.append({
                        "clip_name": clip_path.name,
                        "clip_path": str(clip_path),
                        "error": "Clip file does not exist"
                    })
                    continue

                clip_paths.append(str(clip_path))

        else:
            raise ValueError("clips must be either a folder path string or a list of clip paths.")

        return clip_paths

    # =========================================================
    # 3) Video reading and preprocessing
    # =========================================================

    def _get_clip_duration(self, clip_path):
        cap = cv2.VideoCapture(clip_path)

        if not cap.isOpened():
            return 0.0

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        cap.release()

        if fps is None or fps <= 0:
            return 0.0

        duration = frame_count / fps
        return round(float(duration), 3)

    def _read_video_frames(self, clip_path):
        cap = cv2.VideoCapture(clip_path)

        if not cap.isOpened():
            raise ValueError("Could not read video file")

        frames = []

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            if frame is None:
                continue

            # OpenCV reads frames as BGR.
            # We convert to RGB before using VGG16 preprocess_input.
            if self.convert_bgr_to_rgb:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # OpenCV resize expects size as (width, height).
            frame = cv2.resize(frame, self.frame_size)

            frames.append(frame)

        cap.release()

        if len(frames) == 0:
            raise ValueError("Video has zero readable frames")

        return frames

    def _sample_or_pad_frames(self, frames):
        """
        Convert any number of frames into exactly seq_len frames.

        If video has more frames:
            sample frames uniformly.

        If video has fewer frames:
            repeat the last frame until seq_len.
        """
        total_frames = len(frames)

        if total_frames == self.seq_len:
            return frames

        if total_frames > self.seq_len:
            indices = np.linspace(0, total_frames - 1, self.seq_len).astype(int)
            sampled_frames = [frames[i] for i in indices]
            return sampled_frames

        padded_frames = list(frames)
        last_frame = frames[-1]

        while len(padded_frames) < self.seq_len:
            padded_frames.append(last_frame)

        return padded_frames

    def _preprocess_clip(self, clip_path):
        """
        Preprocess one video clip for VGG16-based video model.

        Steps:
        1. Read video frames using OpenCV.
        2. Convert BGR to RGB.
        3. Resize each frame to frame_size.
        4. Uniformly sample or pad frames to seq_len.
        5. Convert frames to float32.
        6. Apply VGG16 preprocess_input.
        7. Add batch dimension.

        Final shape:
            (1, seq_len, height, width, 3)

        Important:
        - Do NOT divide by 255 when using VGG16 preprocess_input.
        """
        frames = self._read_video_frames(clip_path)
        frames = self._sample_or_pad_frames(frames)

        frames_array = np.array(frames).astype(np.float32)

        # VGG16 preprocessing:
        # This applies the ImageNet preprocessing expected by VGG16.
        # Do not normalize to [0, 1] before this.
        frames_array = preprocess_input(frames_array)

        model_input = np.expand_dims(frames_array, axis=0)

        return model_input

    # =========================================================
    # 4) Prediction
    # =========================================================

    def _predict_clip(self, clip_path):
        model_input = self._preprocess_clip(clip_path)

        predictions = self.model.predict(model_input, verbose=0)
        predictions = np.array(predictions)

        # Expected output: (1, num_classes)
        if predictions.ndim == 2:
            probs = predictions[0]

        # Sometimes output can be: (num_classes,)
        elif predictions.ndim == 1:
            probs = predictions

        else:
            raise ValueError(f"Unexpected model output shape: {predictions.shape}")

        if len(probs) != len(self.class_names):
            raise ValueError(
                f"Model output size ({len(probs)}) does not match number of class names ({len(self.class_names)})."
            )

        predicted_index = int(np.argmax(probs))
        confidence = float(probs[predicted_index])

        if np.isnan(confidence) or confidence < 0:
            raise ValueError("Invalid confidence value returned by model")

        predicted_action = self.class_names[predicted_index]

        if predicted_action not in self.class_names:
            raise ValueError("Unknown predicted action")

        return predicted_action, round(confidence, 4)

    def _build_prediction_record(self, clip_path):
        clip_name = os.path.basename(clip_path)
        duration = self._get_clip_duration(clip_path)

        predicted_action, confidence = self._predict_clip(clip_path)

        return {
            "clip_name": clip_name,
            "clip_path": clip_path,
            "predicted_action": predicted_action,
            "confidence": confidence,
            "duration": duration
        }

    def _process_all_clips(self):
        self.prediction_records = []

        for clip_path in self.clip_paths:
            try:
                record = self._build_prediction_record(clip_path)
                self.prediction_records.append(record)

                if self.verbose:
                    print(
                        f"Processed: {record['clip_name']} | "
                        f"{record['predicted_action']} | "
                        f"{record['confidence']}"
                    )

            except Exception as e:
                self.failed_clips.append({
                    "clip_name": os.path.basename(clip_path),
                    "clip_path": clip_path,
                    "error": str(e)
                })

    # =========================================================
    # 5) Analytics calculations
    # =========================================================

    def _get_action_counts(self):
        counts = Counter()

        for record in self.prediction_records:
            action = record.get("predicted_action")

            if action in self.class_names:
                counts[action] += 1

        return {
            class_name: counts.get(class_name, 0)
            for class_name in self.class_names
        }

    def _calculate_passing_style(self, action_counts):
        short_count = action_counts.get("shortpass", 0)
        long_count = action_counts.get("longpass", 0)
        total_passes = short_count + long_count

        if total_passes == 0:
            return {
                "short_pass_count": short_count,
                "long_pass_count": long_count,
                "total_passes": 0,
                "short_pass_ratio": 0,
                "long_pass_ratio": 0,
                "passing_profile": "Not enough passing data",
                "explanation": "No short pass or long pass clips were detected."
            }

        short_ratio = short_count / total_passes
        long_ratio = long_count / total_passes

        if short_ratio >= 0.70:
            passing_profile = "Short-passing oriented"
            explanation = "The player relies more on short passes than long passes."

        elif long_ratio >= 0.45:
            passing_profile = "Direct-passing oriented"
            explanation = "The player uses long passes frequently, suggesting a direct passing style."

        else:
            passing_profile = "Balanced passing profile"
            explanation = "The player shows a balanced use of short and long passes."

        return {
            "short_pass_count": short_count,
            "long_pass_count": long_count,
            "total_passes": total_passes,
            "short_pass_ratio": round(short_ratio, 3),
            "long_pass_ratio": round(long_ratio, 3),
            "passing_profile": passing_profile,
            "explanation": explanation
        }

    def _calculate_attacking_threat(self, action_counts):
        ontarget = action_counts.get("ontarget", 0)
        penalty = action_counts.get("penalty", 0)
        freekick = action_counts.get("freekick", 0)
        corner = action_counts.get("corner", 0)
        longpass = action_counts.get("longpass", 0)

        score = (
            (ontarget * 4)
            + (penalty * 5)
            + (freekick * 2)
            + (corner * 2)
            + (longpass * 0.5)
        )

        return {
            "score": round(score, 3),
            "components": {
                "ontarget": ontarget,
                "penalty": penalty,
                "freekick": freekick,
                "corner": corner,
                "longpass": longpass
            },
            "explanation": (
                "The player shows attacking involvement through shots on target, "
                "free kicks, corners, penalties, or long progressive passes. "
                "This is an estimated clip-based score only."
            )
        }

    def _calculate_discipline_risk(self, action_counts):
        foul_count = action_counts.get("foul", 0)
        risk_score = foul_count * 2

        if foul_count <= 10:
            risk_level = "Low"

        elif foul_count <= 15:
            risk_level = "Medium"

        else:
            risk_level = "High"

        warning = None

        if risk_level == "High":
            warning = (
                "High foul frequency may increase the risk of conceding dangerous "
                "free kicks or receiving cards."
            )

        return {
            "foul_count": foul_count,
            "discipline_risk_score": risk_score,
            "risk_level": risk_level,
            "warning": warning
        }

    def _calculate_set_piece_summary(self, action_counts, total_clips):
        corner = action_counts.get("corner", 0)
        freekick = action_counts.get("freekick", 0)
        penalty = action_counts.get("penalty", 0)
        throw_in = action_counts.get("throw-in", 0)
        goalkick = action_counts.get("goalkick", 0)

        set_piece_count = corner + freekick + penalty + throw_in + goalkick
        set_piece_ratio = set_piece_count / total_clips if total_clips > 0 else 0

        return {
            "corner": corner,
            "freekick": freekick,
            "penalty": penalty,
            "throw-in": throw_in,
            "goalkick": goalkick,
            "set_piece_count": set_piece_count,
            "set_piece_ratio": round(set_piece_ratio, 3),
            "explanation": "This shows how often the uploaded clips contain set-piece or restart situations."
        }

    def get_clip_review_list(self, sort_by="original", action_filter=None):
        """
        Optional helper method for frontend filtering/sorting.

        sort_by options:
        - original
        - highest_confidence
        - lowest_confidence

        action_filter example:
        - "shortpass"
        - "foul"
        - "longpass"
        """
        clips = list(self.prediction_records)

        if action_filter is not None:
            clips = [
                clip for clip in clips
                if clip.get("predicted_action") == action_filter
            ]

        if sort_by == "highest_confidence":
            clips = sorted(
                clips,
                key=lambda x: x.get("confidence", 0),
                reverse=True
            )

        elif sort_by == "lowest_confidence":
            clips = sorted(
                clips,
                key=lambda x: x.get("confidence", 0)
            )

        elif sort_by == "original":
            pass

        else:
            raise ValueError(
                "sort_by must be 'original', 'highest_confidence', or 'lowest_confidence'."
            )

        return clips

    def _calculate_top_confident_clips(self):
        top_clips = {}

        for record in self.prediction_records:
            action = record.get("predicted_action")
            confidence = record.get("confidence", 0)

            if action not in top_clips:
                top_clips[action] = {
                    "clip_name": record["clip_name"],
                    "clip_path": record["clip_path"],
                    "confidence": confidence
                }

            elif confidence > top_clips[action]["confidence"]:
                top_clips[action] = {
                    "clip_name": record["clip_name"],
                    "clip_path": record["clip_path"],
                    "confidence": confidence
                }

        return top_clips

    def _calculate_confidence_quality_summary(self):
        if not self.prediction_records:
            return {
                "average_confidence": 0,
                "high_confidence_count": 0,
                "medium_confidence_count": 0,
                "needs_review_count": 0,
                "needs_review_clips": [],
                "explanation": "No valid predictions were available."
            }

        confidences = [
            record.get("confidence", 0)
            for record in self.prediction_records
        ]

        average_confidence = sum(confidences) / len(confidences)

        high_count = 0
        medium_count = 0
        review_count = 0
        needs_review_clips = []

        for record in self.prediction_records:
            confidence = record.get("confidence", 0)

            if confidence >= 0.90:
                high_count += 1

            elif confidence >= 0.70:
                medium_count += 1

            else:
                review_count += 1

                needs_review_clips.append({
                    "clip_name": record["clip_name"],
                    "clip_path": record["clip_path"],
                    "predicted_action": record["predicted_action"],
                    "confidence": confidence
                })

        return {
            "average_confidence": round(average_confidence, 4),
            "high_confidence_count": high_count,
            "medium_confidence_count": medium_count,
            "needs_review_count": review_count,
            "needs_review_clips": needs_review_clips,
            "explanation": "This helps analysts know which predictions are reliable and which clips need manual checking."
        }

    # =========================================================
    # 6) Estimated playing style profile
    # =========================================================

    def _calculate_playing_style_profile(
        self,
        action_counts,
        passing_style,
        discipline_risk,
        total_clips
    ):
        if total_clips == 0:
            return {
                "main_style": "Unknown",
                "secondary_styles": [],
                "passing_profile": "Not enough data",
                "discipline_risk": "Unknown",
                "suitable_team_styles": [],
                "explanation": "No valid clips were processed.",
                "limitations_note": self._limitations_note()
            }

        shortpass = action_counts.get("shortpass", 0)
        longpass = action_counts.get("longpass", 0)
        ontarget = action_counts.get("ontarget", 0)
        penalty = action_counts.get("penalty", 0)
        freekick = action_counts.get("freekick", 0)
        corner = action_counts.get("corner", 0)
        foul = action_counts.get("foul", 0)

        total_passes = shortpass + longpass

        shortpass_ratio = shortpass / total_passes if total_passes > 0 else 0
        longpass_ratio = longpass / total_passes if total_passes > 0 else 0

        attacking_actions_ratio = (
            ontarget + penalty + freekick + corner
        ) / total_clips

        set_piece_execution_ratio = (
            freekick + penalty + corner
        ) / total_clips

        foul_ratio = foul / total_clips

        detected_styles = []
        style_reasons = []
        team_styles = []

        # A) Possession Player
        if shortpass_ratio >= 0.70:
            detected_styles.append("Possession Player")

            style_reasons.append(
                "The player has a high short pass ratio, showing a tendency to keep possession and connect play."
            )

            team_styles.extend([
                "Possession-based teams",
                "Build-up teams",
                "Teams that use short passing combinations",
                "Teams that rely on midfield control"
            ])

        # B) Direct Playmaker
        if longpass_ratio >= 0.45:
            detected_styles.append("Direct Playmaker")

            style_reasons.append(
                "The player uses long passes frequently, which may help progress the ball quickly or switch play."
            )

            team_styles.extend([
                "Direct football teams",
                "Counter-attacking teams",
                "Fast transition teams",
                "Teams that use long balls behind defenders"
            ])

        # C) Attacking Threat Player
        if attacking_actions_ratio >= 0.25:
            detected_styles.append("Attacking Threat Player")

            style_reasons.append(
                "The player appears involved in dangerous attacking situations such as shots on target, penalties, free kicks, or corners."
            )

            team_styles.extend([
                "Attacking teams",
                "High-pressing teams",
                "Teams that create many final-third chances"
            ])

        # D) Set-Piece Specialist
        if set_piece_execution_ratio >= 0.20:
            detected_styles.append("Set-Piece Specialist")

            style_reasons.append(
                "The player is frequently involved in set-piece execution such as free kicks, penalties, or corners."
            )

            team_styles.extend([
                "Teams that rely on set pieces",
                "Teams with strong aerial players",
                "Teams that create chances from corners and free kicks",
                "Teams needing a reliable penalty or free-kick taker"
            ])

        # E) Physical / Aggressive Player
        if foul_ratio >= 0.15:
            detected_styles.append("Physical / Aggressive Player")

            style_reasons.append(
                "The player commits fouls frequently, suggesting a more physical or aggressive profile."
            )

            team_styles.extend([
                "High-pressing teams",
                "Defensive teams",
                "Teams that rely on physical duels",
                "Teams using aggressive pressing"
            ])

        # F) Balanced Player
        if not detected_styles:
            detected_styles.append("Balanced Player")

            style_reasons.append(
                "No single action type strongly dominates, so the player appears to contribute across different actions."
            )

            team_styles.extend([
                "Flexible tactical systems",
                "Teams that change style during matches",
                "Teams needing adaptable players",
                "Utility roles or flexible midfield roles"
            ])

        main_style = detected_styles[0]
        secondary_styles = detected_styles[1:]

        unique_team_styles = list(dict.fromkeys(team_styles))

        explanation = " ".join(style_reasons)

        if discipline_risk.get("risk_level") == "High":
            explanation += (
                " High foul frequency may increase the risk of conceding dangerous free kicks or receiving cards."
            )

        return {
            "main_style": main_style,
            "secondary_styles": secondary_styles,
            "passing_profile": passing_style.get("passing_profile"),
            "discipline_risk": discipline_risk.get("risk_level"),
            "suitable_team_styles": unique_team_styles,
            "explanation": explanation,
            "limitations_note": self._limitations_note()
        }

    def _calculate_suitable_team_styles(self, player_profile):
        recommended_styles = player_profile.get("suitable_team_styles", [])
        main_style = player_profile.get("main_style", "Balanced Player")

        if main_style == "Possession Player":
            reason = (
                "The player appears to be short-passing oriented and may fit systems "
                "that depend on possession and build-up play."
            )

        elif main_style == "Direct Playmaker":
            reason = (
                "The player appears comfortable with long passes and may fit direct, "
                "counter-attacking, or fast-transition systems."
            )

        elif main_style == "Attacking Threat Player":
            reason = (
                "The player appears involved in attacking actions and may fit teams "
                "that create frequent final-third chances."
            )

        elif main_style == "Set-Piece Specialist":
            reason = (
                "The player appears frequently involved in set pieces and may fit teams "
                "that rely on corners, free kicks, or penalties."
            )

        elif main_style == "Physical / Aggressive Player":
            reason = (
                "The player appears physically involved and may fit high-pressing or defensive systems, "
                "but foul risk should be reviewed."
            )

        else:
            reason = (
                "The player appears balanced and may fit flexible tactical systems."
            )

        return {
            "recommended_team_styles": recommended_styles,
            "reason": reason
        }

    def _calculate_profile_reliability(self, total_clips, average_confidence):
        if total_clips >= 30 and average_confidence >= 0.85:
            reliability = "High"

        elif total_clips >= 15 and average_confidence >= 0.75:
            reliability = "Medium"

        else:
            reliability = "Low"

        return {
            "profile_reliability": reliability,
            "reason": (
                f"The profile is based on {total_clips} analyzed clips "
                f"with {round(average_confidence * 100, 2)}% average confidence."
            )
        }

    def _limitations_note(self):
        return (
            "This is an estimated style profile based only on uploaded single-player clips "
            "and model predictions. It does not use full-match tracking, team context, "
            "player identity, or timestamps."
        )

    # =========================================================
    # 7) Generate final dashboard
    # =========================================================

    def generate_dashboard(self):
        self._process_all_clips()
    
        total_input_clips = len(self.clip_paths)
        valid_clips = len(self.prediction_records)
    
        if valid_clips == 0:
            return {
                "status": "error",
                "message": "No valid clips were processed.",
                "total_clips": total_input_clips,
                "valid_clips": 0,
                "failed_clips_count": len(self.failed_clips)
            }
    
        # 1) Action counter
        action_distribution = self._get_action_counts()
    
        # 2) Analysis sections
        passing_style = self._calculate_passing_style(action_distribution)
    
        attacking_threat = self._calculate_attacking_threat(action_distribution)
    
        discipline_risk = self._calculate_discipline_risk(action_distribution)
    
        set_piece_summary = self._calculate_set_piece_summary(
            action_distribution,
            valid_clips
        )
    
        confidence_quality_summary = self._calculate_confidence_quality_summary()
    
        player_profile = self._calculate_playing_style_profile(
            action_counts=action_distribution,
            passing_style=passing_style,
            discipline_risk=discipline_risk,
            total_clips=valid_clips
        )
    
        suitable_team_styles = self._calculate_suitable_team_styles(player_profile)
    
        average_confidence = confidence_quality_summary.get("average_confidence", 0)
    
        profile_reliability = self._calculate_profile_reliability(
            total_clips=valid_clips,
            average_confidence=average_confidence
        )
    
        # 3) Clean final output
        # No prediction_records
        # No clip_review_list
        # No clip-level confidence details
        # No clip paths
        return {    
            "action_counter": action_distribution,
    
            "analysis": {
                "passing_style": passing_style,
                "estimated_attacking_threat": attacking_threat,
                "discipline_risk": discipline_risk,
                "set_piece_summary": set_piece_summary,
                "estimated_player_playing_style_profile": player_profile,
                "suitable_team_styles": suitable_team_styles,
                "profile_reliability": profile_reliability
            }
        }