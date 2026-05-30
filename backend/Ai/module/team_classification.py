import supervision as sv
PLAYER_ID = 0
class team_classification:
    def fit_team_classifier(self, video_path, stride=30):
        frame_generator = sv.get_video_frames_generator(source_path=video_path, stride=stride)
        crops = []
        for frame in frame_generator:
            if frame is None:
                continue
            results = self.model.predict(frame, conf=0.3,verbose=False)[0]
            detections = sv.Detections(
                xyxy=results.boxes.xyxy.cpu().numpy(),
                confidence=results.boxes.conf.cpu().numpy(),
                class_id=results.boxes.cls.cpu().numpy().astype(int)
            )
            players = detections[detections.class_id == PLAYER_ID]
            for xyxy in players.xyxy:
                crop = sv.crop_image(frame, xyxy)
                if crop is not None and crop.size > 0:
                    crops.append(crop)
        if len(crops) > 0:
            self.team_classifier.fit(crops)