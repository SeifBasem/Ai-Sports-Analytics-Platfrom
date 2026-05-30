import numpy as np
import supervision as sv
class gk_cls:
    def resolve_goalkeepers_team_id(self, players, goalkeepers):
        if len(goalkeepers) == 0 or len(players) == 0:
            return np.zeros(len(goalkeepers), dtype=int)
        goalkeepers_xy = goalkeepers.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
        players_xy = players.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
        team_0_mask = players.class_id == 0
        team_1_mask = players.class_id == 1
        if not np.any(team_0_mask) or not np.any(team_1_mask):
            return np.zeros(len(goalkeepers), dtype=int)
        #  نحسب centroid بس في أول كام فريم
        if self.centroid_frames < self.max_centroid_frames:
            team_0_centroid = players_xy[team_0_mask].mean(axis=0)
            team_1_centroid = players_xy[team_1_mask].mean(axis=0)

            # نحفظهم
            if self.team_0_centroid is None:
                self.team_0_centroid = team_0_centroid
                self.team_1_centroid = team_1_centroid
            else:
                # ممكن نعمل smoothing بسيط
                self.team_0_centroid = 0.9 * self.team_0_centroid + 0.1 * team_0_centroid
                self.team_1_centroid = 0.9 * self.team_1_centroid + 0.1 * team_1_centroid

            self.centroid_frames += 1

        #  بعد كده نستخدم القيم الثابتة
        team_0_centroid = self.team_0_centroid
        team_1_centroid = self.team_1_centroid
        goalkeepers_team_id = []
        for gk_xy in goalkeepers_xy:
            dist_0 = np.linalg.norm(gk_xy - team_0_centroid)
            dist_1 = np.linalg.norm(gk_xy - team_1_centroid)
            goalkeepers_team_id.append(0 if dist_0 < dist_1 else 1)
        return np.array(goalkeepers_team_id)
