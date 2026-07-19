import os
import json
from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem
from PySide6.QtGui import QImage, QPainter, Qt, QPainterPath
from draw_tools import SelectableCircleItem, ResizableRectItem, ShapeItem
from draw_tools import SelectablePolygonItem

def save_outputs(self):


    folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
    if not folder:
        print("❌ Сохранение отменено.")
        return

    pieces_dir = os.path.join(folder, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)

    background = next((item for item in self.scene.items() if isinstance(item, QGraphicsPixmapItem)), None)
    if not background:
        print("❌ Фон не найден.")
        return

    original_image_path = background.data(Qt.UserRole) if background.data(Qt.UserRole) else ""
    original_image = background.pixmap().toImage()
    # ✅ гарантируем альфа-канал: иначе CompositionMode_Clear даст чёрный цвет вместо прозрачности
    if original_image.format() != QImage.Format_ARGB32:
        original_image = original_image.convertToFormat(QImage.Format_ARGB32)
    without_shape_image = QImage(original_image)
    clean_parent_image = QImage(original_image)

    # ✅ сохраняем фон рядом с проектом (относительный путь в shapes.json)
    bg_out_path = os.path.join(folder, 'background.png')
    try:
        original_image.save(bg_out_path)
    except Exception as e:
        print('⚠ Не удалось сохранить background.png:', e)
    bg_for_json = 'background.png'

    shape_data = []
    index = 1

    children = []
    parents = []

    for item in reversed(self.scene.items()):
        if not isinstance(item, ShapeItem):
            continue
        shape_id = next((sid for sid, obj in self.shape_registry.items() if obj == item), None)
        if shape_id and self.shape_parents.get(shape_id):
            children.append((shape_id, item))
        else:
            parents.append((shape_id, item))

    # --- children ---
    for shape_id, item in children:
        shape_rect = item.sceneBoundingRect().toRect()
        brush_color = item.brush().color().name()

        if shape_id is None:
            continue
        # ✅ пропускаем мусорные/нулевые фигуры (0x0), чтобы не ломать экспорт и рендер
        if shape_rect.width() < 2 or shape_rect.height() < 2:
            print(f'⚠ Пропуск слишком маленькой фигуры id={shape_id}: {shape_rect}')
            continue

        if isinstance(item, SelectableCircleItem):
            item_type = "Circle"
            path = QPainterPath()
            path.addEllipse(0, 0, shape_rect.width(), shape_rect.height())

            original_crop = original_image.copy(shape_rect)
            cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
            cut_image.fill(Qt.transparent)

            cut_painter = QPainter(cut_image)
            cut_painter.setRenderHint(QPainter.Antialiasing)
            cut_painter.setClipPath(path)
            cut_painter.drawImage(0, 0, original_crop)
            cut_painter.end()

            cut_image.save(os.path.join(pieces_dir, f"shape_{shape_id}.png"))

            # ВАЖНО: очистить круг с фона
            global_path = QPainterPath()
            global_path.addEllipse(item.sceneBoundingRect())
            for target in [without_shape_image, clean_parent_image]:
                painter_clear = QPainter(target)
                painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)
                painter_clear.setClipPath(global_path)
                painter_clear.fillPath(global_path, Qt.transparent)
                painter_clear.end()

            shape_data.append({
                "id": shape_id,
                "type": item_type,
                "x": int(shape_rect.x()),
                "y": int(shape_rect.y()),
                "width": int(shape_rect.width()),
                "height": int(shape_rect.height()),
                "color": brush_color,
                "parent_id": self.shape_parents.get(shape_id)
            })
            index += 1
            continue

        # Rectangle or Polygon
        if isinstance(item, ResizableRectItem):
            item_type = "Rectangle"
            path = QPainterPath()
            path.addRect(0, 0, shape_rect.width(), shape_rect.height())
        elif isinstance(item, SelectablePolygonItem):
            item_type = "Polygon"
            polygon = item.polygon()
            if polygon.count() < 3:
                print(f'⚠ Пропуск полигона с <3 точками id={shape_id}')
                continue
            path = QPainterPath()
            path.addPolygon(polygon.translated(-shape_rect.topLeft()))
        else:
            continue

        original_crop = original_image.copy(shape_rect)
        cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
        cut_image.fill(Qt.transparent)

        cut_painter = QPainter(cut_image)
        cut_painter.drawImage(0, 0, original_crop)
        cut_painter.setCompositionMode(QPainter.CompositionMode_Clear)

        mask = QPainterPath()
        mask.addRect(0, 0, shape_rect.width(), shape_rect.height())
        mask = mask.subtracted(path)

        cut_painter.fillPath(mask, Qt.transparent)
        cut_painter.end()

        cut_image.save(os.path.join(pieces_dir, f"shape_{shape_id}.png"))

        global_path = QPainterPath()
        if item_type == "Polygon":
            global_path.addPolygon(item.mapToScene(item.polygon()))
        else:
            global_path.addRect(shape_rect)

        for target in [without_shape_image, clean_parent_image]:
            painter_clear = QPainter(target)
            painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)
            painter_clear.setClipPath(global_path)
            painter_clear.fillPath(global_path, Qt.transparent)
            painter_clear.end()

        if item_type == "Polygon":
            scene_polygon = item.mapToScene(item.polygon())
            shape_data.append({
                "id": shape_id,
                "type": "Polygon",
                "points": [{"x": int(p.x()), "y": int(p.y())} for p in scene_polygon],
                "color": brush_color,
                "parent_id": self.shape_parents.get(shape_id)
            })
        else:
            shape_data.append({
                "id": shape_id,
                "type": item_type,
                "x": int(shape_rect.x()),
                "y": int(shape_rect.y()),
                "width": int(shape_rect.width()),
                "height": int(shape_rect.height()),
                "color": brush_color,
                "parent_id": self.shape_parents.get(shape_id)
            })

        index += 1

    # --- parents ---
    for shape_id, item in parents:
        shape_rect = item.sceneBoundingRect().toRect()
        brush_color = item.brush().color().name()

        if shape_id is None:
            continue
        # ✅ пропускаем мусорные/нулевые фигуры (0x0), чтобы не ломать экспорт и рендер
        if shape_rect.width() < 2 or shape_rect.height() < 2:
            print(f'⚠ Пропуск слишком маленькой фигуры id={shape_id}: {shape_rect}')
            continue

        if isinstance(item, SelectableCircleItem):
            item_type = "Circle"
            path = QPainterPath()
            path.addEllipse(0, 0, shape_rect.width(), shape_rect.height())

            original_crop = clean_parent_image.copy(shape_rect)
            cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
            cut_image.fill(Qt.transparent)

            cut_painter = QPainter(cut_image)
            cut_painter.setRenderHint(QPainter.Antialiasing)
            cut_painter.setClipPath(path)
            cut_painter.drawImage(0, 0, original_crop)
            cut_painter.end()

            cut_image.save(os.path.join(pieces_dir, f"shape_{shape_id}.png"))

            # ВАЖНО: удалить круг с общего фона
            global_path = QPainterPath()
            global_path.addEllipse(item.sceneBoundingRect())
            painter_clear = QPainter(without_shape_image)
            painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)
            painter_clear.setClipPath(global_path)
            painter_clear.fillPath(global_path, Qt.transparent)
            painter_clear.end()

            shape_data.append({
                "id": shape_id,
                "type": item_type,
                "x": int(shape_rect.x()),
                "y": int(shape_rect.y()),
                "width": int(shape_rect.width()),
                "height": int(shape_rect.height()),
                "color": brush_color,
                "parent_id": self.shape_parents.get(shape_id)
            })
            index += 1
            continue

        if isinstance(item, ResizableRectItem):
            item_type = "Rectangle"
            path = QPainterPath()
            path.addRect(0, 0, shape_rect.width(), shape_rect.height())
        elif isinstance(item, SelectablePolygonItem):
            item_type = "Polygon"
            polygon = item.polygon()
            if polygon.count() < 3:
                print(f'⚠ Пропуск полигона с <3 точками id={shape_id}')
                continue
            path = QPainterPath()
            path.addPolygon(polygon.translated(-shape_rect.topLeft()))
        else:
            continue

        original_crop = clean_parent_image.copy(shape_rect)
        cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
        cut_image.fill(Qt.transparent)

        cut_painter = QPainter(cut_image)
        cut_painter.drawImage(0, 0, original_crop)
        cut_painter.setCompositionMode(QPainter.CompositionMode_Clear)

        mask = QPainterPath()
        mask.addRect(0, 0, shape_rect.width(), shape_rect.height())
        mask = mask.subtracted(path)

        # вырезание вложенных
        for sid2, sub_item in self.shape_registry.items():
            if self.shape_parents.get(sid2) == shape_id:
                sub_path = QPainterPath()
                if isinstance(sub_item, SelectablePolygonItem):
                    translated_sub_polygon = sub_item.polygon().translated(
                        sub_item.scenePos() - item.scenePos()
                    )
                    sub_path.addPolygon(translated_sub_polygon)
                elif isinstance(sub_item, ResizableRectItem):
                    sub_rect = sub_item.sceneBoundingRect().translated(-shape_rect.topLeft())
                    sub_path.addRect(sub_rect)
                elif isinstance(sub_item, SelectableCircleItem):
                    sub_rect = sub_item.sceneBoundingRect().translated(-shape_rect.topLeft())
                    sub_path.addEllipse(sub_rect)
                mask = mask.subtracted(sub_path)

        cut_painter.fillPath(mask, Qt.transparent)
        cut_painter.end()

        cut_image.save(os.path.join(pieces_dir, f"shape_{shape_id}.png"))

        global_path = QPainterPath()
        if item_type == "Polygon":
            global_path.addPolygon(item.mapToScene(item.polygon()))
        else:
            global_path.addRect(shape_rect)

        painter_clear = QPainter(without_shape_image)
        painter_clear.setCompositionMode(QPainter.CompositionMode_Clear)
        painter_clear.setClipPath(global_path)
        painter_clear.fillPath(global_path, Qt.transparent)
        painter_clear.end()

        if item_type == "Polygon":
            scene_polygon = item.mapToScene(item.polygon())
            shape_data.append({
                "id": shape_id,
                "type": "Polygon",
                "points": [{"x": int(p.x()), "y": int(p.y())} for p in scene_polygon],
                "color": brush_color,
                "parent_id": self.shape_parents.get(shape_id)
            })
        else:
            shape_data.append({
                "id": shape_id,
                "type": item_type,
                "x": int(shape_rect.x()),
                "y": int(shape_rect.y()),
                "width": int(shape_rect.width()),
                "height": int(shape_rect.height()),
                "color": brush_color,
                "parent_id": self.shape_parents.get(shape_id)
            })

        index += 1

    without_shape_image.save(os.path.join(folder, "without_shape_area.png"))

    with open(os.path.join(folder, "shapes.json"), "w", encoding="utf-8") as f:
        if hasattr(self, "ai_window"):
            shape_cards_data = self.ai_window.collect_shape_cards_data()
        else:
            shape_cards_data = []
        # ✅ чистим shape_cards: оставляем только карточки реально сохранённых фигур
        valid_ids = set()
        for s in shape_data:
            try:
                valid_ids.add(int(s.get('id')))
            except Exception:
                pass

        filtered_cards = []
        for c in shape_cards_data:
            if not isinstance(c, dict):
                continue
            try:
                cid = int(c.get('id'))
            except Exception:
                continue
            if cid in valid_ids:
                filtered_cards.append(c)
        shape_cards_data = filtered_cards
        json.dump({
            'background': bg_for_json,
            'shapes': shape_data,
            'shape_cards': shape_cards_data
        }, f, indent=4)

    self.current_project_folder = folder
    self.current_shapes_json_path = os.path.join(folder, "shapes.json")

    # Передаём пути в AI panel, чтобы render работал без диалогов
    if hasattr(self, "ai_window"):
        try:
            self.ai_window.set_render_sources(
                shapes_json_path=os.path.join(folder, "shapes.json"),
                masks_dir=os.path.join(folder, "masks"),
                pieces_dir=pieces_dir,
                out_mp4_path=os.path.join(folder, "result.mp4"),
            )
        except Exception:
            pass

    print(f"✅ Сохранено {index - 1} фигур и итоговое изображение.")
