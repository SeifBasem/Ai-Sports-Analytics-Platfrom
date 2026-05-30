from scipy.ndimage import gaussian_filter
import cv2
from sports.annotators.soccer import draw_pitch
import numpy as np

class heatmap:

    def _add_overlay_title(
        self,
        image,
        title,
        font_scale=1.1,
        thickness=3,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0),
        margin=16,
        padding=10,
        bg_alpha=0.45
    ):
        output = image.copy()
        overlay = output.copy()
    
        font = cv2.FONT_HERSHEY_SIMPLEX
        (text_w, text_h), baseline = cv2.getTextSize(title, font, font_scale, thickness)
    
        x1 = margin
        y1 = margin
        x2 = x1 + text_w + padding * 2
        y2 = y1 + text_h + baseline + padding * 2
    
        # خلفية شفافة فوق الصورة نفسها
        cv2.rectangle(overlay, (x1, y1), (x2, y2), bg_color, -1)
        output = cv2.addWeighted(overlay, bg_alpha, output, 1 - bg_alpha, 0)
    
        text_x = x1 + padding
        text_y = y1 + padding + text_h
    
        cv2.putText(
            output,
            title,
            (text_x, text_y),
            font,
            font_scale,
            text_color,
            thickness,
            cv2.LINE_AA
        )
    
        return output    
    def generate_player_heatmap(
        self,
        player_id,
        config=None,
        bins=(30, 20),
        sigma=1.6,
        alpha=0.7,
        player_name=None
    ):

        if config is None:
            config = self.pitch_config
    
        # ملعب فاضي
        pitch = draw_pitch(config)
    
        # لو اللاعب مش موجود أو معندوش نقاط
        if player_id not in self.heatmap_coordinates:
            return pitch
    
        points = self.heatmap_coordinates[player_id]
        if len(points) == 0:
            return pitch
    
        points = np.array(points, dtype=np.float32)
    
        # حدود الملعب
        vertices = np.array(config.vertices, dtype=np.float32)
        x_min, y_min = vertices.min(axis=0)
        x_max, y_max = vertices.max(axis=0)
    
        # تنظيف أي نقاط خارج حدود الملعب
        mask = (
            (points[:, 0] >= x_min) & (points[:, 0] <= x_max) &
            (points[:, 1] >= y_min) & (points[:, 1] <= y_max)
        )
        points = points[mask]
    
        if len(points) == 0:
            return pitch
    
        # Histogram 2D
        heatmap, _, _ = np.histogram2d(
            points[:, 0],
            points[:, 1],
            bins=bins,
            range=[[x_min, x_max], [y_min, y_max]]
        )
    
        # Gaussian smoothing
        heatmap = gaussian_filter(heatmap, sigma=sigma)
    
        # Normalize
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
    
        # نحول heatmap لصورة
        h, w = pitch.shape[:2]
        heatmap_img = cv2.resize(
            (heatmap.T * 255).astype(np.uint8),
            (w, h),
            interpolation=cv2.INTER_CUBIC
        )
    
        heatmap_color = cv2.applyColorMap(heatmap_img, cv2.COLORMAP_JET)
    
        # دمج مع الملعب
        blended = cv2.addWeighted(pitch, 1 - alpha, heatmap_color, alpha, 0)
    
        # إعادة رسم الملعب فوق الـ heatmap عشان الخطوط تبان
        pitch_lines = draw_pitch(config)
        final = cv2.addWeighted(blended, 0.85, pitch_lines, 0.15, 0)
        title = f"Player Heatmap - #{player_id}" if player_name is None else f"Player Heatmap - {player_name} (#{player_id})"
        final = self._add_overlay_title(final, title)
        return final
    def generate_team_heatmap(
        self,
        team_id,
        config=None,
        bins=(30, 20),
        sigma=1.6,
        alpha=0.7,
        team_name=None
    ):

        if config is None:
            config = self.pitch_config
    
        pitch = draw_pitch(config)
    
        # اجمع كل نقاط اللاعبين اللي تابعين للفريق المطلوب
        all_points = []
    
        for tracker_id, points in self.heatmap_coordinates.items():
            if len(points) == 0:
                continue
    
            # نحدد الفريق الثابت للاعب من history
            history = list(self.player_team_history.get(tracker_id, []))
            if len(history) == 0:
                continue
    
            stable_team = max(set(history), key=history.count)
    
            if int(stable_team) != int(team_id):
                continue
    
            all_points.extend(points)
    
        if len(all_points) == 0:
            return pitch
    
        points = np.array(all_points, dtype=np.float32)
    
        # حدود الملعب
        vertices = np.array(config.vertices, dtype=np.float32)
        x_min, y_min = vertices.min(axis=0)
        x_max, y_max = vertices.max(axis=0)
    
        # تنظيف أي نقاط خارج حدود الملعب
        mask = (
            (points[:, 0] >= x_min) & (points[:, 0] <= x_max) &
            (points[:, 1] >= y_min) & (points[:, 1] <= y_max)
        )
        points = points[mask]
    
        if len(points) == 0:
            return pitch
    
        # Histogram 2D
        heatmap, _, _ = np.histogram2d(
            points[:, 0],
            points[:, 1],
            bins=bins,
            range=[[x_min, x_max], [y_min, y_max]]
        )
    
        # Gaussian smoothing
        heatmap = gaussian_filter(heatmap, sigma=sigma)
    
        # Normalize
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
    
        # نحول heatmap لصورة
        h, w = pitch.shape[:2]
        heatmap_img = cv2.resize(
            (heatmap.T * 255).astype(np.uint8),
            (w, h),
            interpolation=cv2.INTER_CUBIC
        )
    
        heatmap_color = cv2.applyColorMap(heatmap_img, cv2.COLORMAP_JET)
    
        # دمج مع الملعب
        blended = cv2.addWeighted(pitch, 1 - alpha, heatmap_color, alpha, 0)
    
        # إعادة رسم خطوط الملعب فوق الـ heatmap
        pitch_lines = draw_pitch(config)
        final = cv2.addWeighted(blended, 0.85, pitch_lines, 0.15, 0)
        title = f"Team Heatmap - Team {team_id}" if team_name is None else f"Team Heatmap - {team_name}"
        final = self._add_overlay_title(final, title)
        return final
