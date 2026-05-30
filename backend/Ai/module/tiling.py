class tiling:
    def tile_frame(self, frame, tile_size=(320, 320), overlap=0.2):
        h, w = frame.shape[:2]
        tw, th = tile_size
        step_x = int(tw * (1 - overlap))
        step_y = int(th * (1 - overlap))
        tiles = []
        for y in range(0, max(1, h - th + 1), step_y):
            for x in range(0, max(1, w - tw + 1), step_x):
                x2 = min(x + tw, w)
                y2 = min(y + th, h)
                x1 = max(0, x2 - tw)
                y1 = max(0, y2 - th)
                crop = frame[y1:y2, x1:x2]
                tiles.append(((x1, y1, x2, y2), crop))
            if (w - tw) % step_x != 0:
                x1 = max(0, w - tw)
                for y in range(0, max(1, h - th + 1), step_y):
                    y2 = min(y + th, h)
                    y1 = max(0, y2 - th)
                    crop = frame[y1:y2, x1:w]
                    tiles.append(((x1, y1, w, y2), crop))
        if (h - th) % step_y != 0:
            y1 = max(0, h - th)
            for x in range(0, max(1, w - tw + 1), step_x):
                x2 = min(x + tw, w)
                x1 = max(0, x2 - tw)
                crop = frame[y1:h, x1:x2]
                tiles.append(((x1, y1, x2, h), crop))
            if (w - tw) % step_x != 0:
                x1 = max(0, w - tw)
                crop = frame[y1:h, x1:w]
                tiles.append(((x1, y1, w, h), crop))
        return tiles

