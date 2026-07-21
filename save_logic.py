import os
import json
from PySide6.QtWidgets import QFileDialog, QGraphicsPixmapItem, QMessageBox
from PySide6.QtGui import QImage, QPainter, Qt, QPainterPath
from draw_tools import SelectableCircleItem, ResizableRectItem, ShapeItem
from draw_tools import SelectablePolygonItem
from effect_engine.project import PROJECT_SCHEMA_VERSION, serialize_flow_directions


def _shape_scene_rect(item):
    """Return geometry bounds in scene coordinates without selection pen/handles."""
    if isinstance(item, SelectablePolygonItem):
        return item.mapToScene(item.polygon()).boundingRect()
    mapped = item.mapRectToScene(item.rect())
    return mapped.boundingRect() if hasattr(mapped, "boundingRect") else mapped


def _shape_crop_rect(item):
    return _shape_scene_rect(item).toAlignedRect()


def _shape_color_name(item):
    """Preserve the configured overlay color even when its fill is hidden."""
    brush = getattr(item, "original_brush", None)
    if brush is None:
        brush = item.brush()
    return brush.color().name()


def _shape_local_path(item, crop_rect):
    """Build the exact shape path in crop-local coordinates."""
    path = QPainterPath()
    offset = -crop_rect.topLeft()
    if isinstance(item, SelectablePolygonItem):
        path.addPolygon(item.mapToScene(item.polygon()).translated(offset))
    elif isinstance(item, SelectableCircleItem):
        path.addEllipse(_shape_scene_rect(item).translated(offset))
    else:
        path.addRect(_shape_scene_rect(item).translated(offset))
    return path


def _refresh_shape_parents(window):
    """Recompute nesting from current geometry after moves and resizes."""
    entries = [
        (int(shape_id), item, _shape_scene_rect(item))
        for shape_id, item in window.shape_registry.items()
        if isinstance(item, ShapeItem) and item.scene() is window.scene
    ]
    for shape_id, item, bounds in entries:
        center = bounds.center()
        child_area = max(0.0, bounds.width() * bounds.height())
        candidates = []
        for other_id, other, other_bounds in entries:
            if other_id == shape_id:
                continue
            other_area = max(0.0, other_bounds.width() * other_bounds.height())
            if other_area <= child_area or not other_bounds.contains(center):
                continue
            if other.contains(other.mapFromScene(center)):
                candidates.append((other_area, other_id))
        window.shape_parents[shape_id] = (
            min(candidates)[1] if candidates else None
        )


def _write_json_atomic(path, data):
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as output:
            json.dump(data, output, ensure_ascii=False, indent=4)
            output.write("\n")
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _save_qimage_atomic(image, path):
    temp_path = f"{path}.tmp.png"
    try:
        if not image.save(temp_path, "PNG"):
            raise RuntimeError(f"Could not encode image: {path}")
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def save_outputs(self, folder=None):
    """Save the complete editor project and report success/failure in the UI."""
    try:
        shapes_json = _save_outputs_impl(self, folder=folder)
    except Exception as error:
        print(f"[SAVE] error: {error}")
        if hasattr(self, "statusBar"):
            self.statusBar().showMessage("Save project: ошибка", 8000)
        QMessageBox.critical(
            self,
            "Save project",
            f"Не удалось сохранить проект:\n{error}",
        )
        return None

    if not shapes_json:
        return None
    if hasattr(self, "statusBar"):
        self.statusBar().showMessage(f"Project saved: {shapes_json}", 8000)
    QMessageBox.information(
        self,
        "Save project",
        f"Проект сохранён:\n{shapes_json}",
    )
    return shapes_json


def _save_outputs_impl(self, folder=None):


    folder = folder or getattr(self, "current_project_folder", None)
    if not folder:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
    if not folder:
        print("❌ Сохранение отменено.")
        return

    pieces_dir = os.path.join(folder, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)

    background = next((item for item in self.scene.items() if isinstance(item, QGraphicsPixmapItem)), None)
    if not background:
        raise RuntimeError("Фон не найден. Сначала импортируйте изображение.")

    original_image_path = background.data(Qt.UserRole) if background.data(Qt.UserRole) else ""
    original_image = background.pixmap().toImage()
    # ✅ гарантируем альфа-канал: иначе CompositionMode_Clear даст чёрный цвет вместо прозрачности
    if original_image.format() != QImage.Format_ARGB32:
        original_image = original_image.convertToFormat(QImage.Format_ARGB32)
    without_shape_image = QImage(original_image)
    clean_parent_image = QImage(original_image)

    # ✅ сохраняем фон рядом с проектом (относительный путь в shapes.json)
    bg_out_path = os.path.join(folder, 'background.png')
    _save_qimage_atomic(original_image, bg_out_path)
    bg_for_json = 'background.png'

    shape_data = []
    index = 1

    children = []
    parents = []

    _refresh_shape_parents(self)

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
        shape_rect = _shape_crop_rect(item)
        brush_color = _shape_color_name(item)

        if shape_id is None:
            continue
        # ✅ пропускаем мусорные/нулевые фигуры (0x0), чтобы не ломать экспорт и рендер
        if shape_rect.width() < 2 or shape_rect.height() < 2:
            print(f'⚠ Пропуск слишком маленькой фигуры id={shape_id}: {shape_rect}')
            continue

        if isinstance(item, SelectableCircleItem):
            item_type = "Circle"
            path = _shape_local_path(item, shape_rect)

            original_crop = original_image.copy(shape_rect)
            cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
            cut_image.fill(Qt.transparent)

            cut_painter = QPainter(cut_image)
            cut_painter.setRenderHint(QPainter.Antialiasing)
            cut_painter.setClipPath(path)
            cut_painter.drawImage(0, 0, original_crop)
            cut_painter.end()

            _save_qimage_atomic(
                cut_image, os.path.join(pieces_dir, f"shape_{shape_id}.png")
            )

            # ВАЖНО: очистить круг с фона
            global_path = QPainterPath()
            global_path.addEllipse(_shape_scene_rect(item))
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
            path = _shape_local_path(item, shape_rect)
        elif isinstance(item, SelectablePolygonItem):
            item_type = "Polygon"
            polygon = item.polygon()
            if polygon.count() < 3:
                print(f'⚠ Пропуск полигона с <3 точками id={shape_id}')
                continue
            path = _shape_local_path(item, shape_rect)
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

        _save_qimage_atomic(
            cut_image, os.path.join(pieces_dir, f"shape_{shape_id}.png")
        )

        global_path = QPainterPath()
        if item_type == "Polygon":
            global_path.addPolygon(item.mapToScene(item.polygon()))
        else:
            global_path.addRect(_shape_scene_rect(item))

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
        shape_rect = _shape_crop_rect(item)
        brush_color = _shape_color_name(item)

        if shape_id is None:
            continue
        # ✅ пропускаем мусорные/нулевые фигуры (0x0), чтобы не ломать экспорт и рендер
        if shape_rect.width() < 2 or shape_rect.height() < 2:
            print(f'⚠ Пропуск слишком маленькой фигуры id={shape_id}: {shape_rect}')
            continue

        if isinstance(item, SelectableCircleItem):
            item_type = "Circle"
            path = _shape_local_path(item, shape_rect)

            original_crop = clean_parent_image.copy(shape_rect)
            cut_image = QImage(shape_rect.size(), QImage.Format_ARGB32)
            cut_image.fill(Qt.transparent)

            cut_painter = QPainter(cut_image)
            cut_painter.setRenderHint(QPainter.Antialiasing)
            cut_painter.setClipPath(path)
            cut_painter.drawImage(0, 0, original_crop)
            cut_painter.end()

            _save_qimage_atomic(
                cut_image, os.path.join(pieces_dir, f"shape_{shape_id}.png")
            )

            # ВАЖНО: удалить круг с общего фона
            global_path = QPainterPath()
            global_path.addEllipse(_shape_scene_rect(item))
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
            path = _shape_local_path(item, shape_rect)
        elif isinstance(item, SelectablePolygonItem):
            item_type = "Polygon"
            polygon = item.polygon()
            if polygon.count() < 3:
                print(f'⚠ Пропуск полигона с <3 точками id={shape_id}')
                continue
            path = _shape_local_path(item, shape_rect)
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
                    translated_sub_polygon = sub_item.mapToScene(
                        sub_item.polygon()
                    ).translated(-shape_rect.topLeft())
                    sub_path.addPolygon(translated_sub_polygon)
                elif isinstance(sub_item, ResizableRectItem):
                    sub_rect = _shape_scene_rect(sub_item).translated(-shape_rect.topLeft())
                    sub_path.addRect(sub_rect)
                elif isinstance(sub_item, SelectableCircleItem):
                    sub_rect = _shape_scene_rect(sub_item).translated(-shape_rect.topLeft())
                    sub_path.addEllipse(sub_rect)
                mask = mask.subtracted(sub_path)

        cut_painter.fillPath(mask, Qt.transparent)
        cut_painter.end()

        _save_qimage_atomic(
            cut_image, os.path.join(pieces_dir, f"shape_{shape_id}.png")
        )

        global_path = QPainterPath()
        if item_type == "Polygon":
            global_path.addPolygon(item.mapToScene(item.polygon()))
        else:
            global_path.addRect(_shape_scene_rect(item))

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

    without_shape_path = os.path.join(folder, "without_shape_area.png")
    _save_qimage_atomic(without_shape_image, without_shape_path)

    project_path = os.path.join(folder, "shapes.json")
    if hasattr(self, "ai_window"):
        shape_cards_data = self.ai_window.collect_shape_cards_data()
    else:
        shape_cards_data = []
    # Keep only cards belonging to shapes that were actually exported.
    valid_ids = set()
    for shape in shape_data:
        try:
            valid_ids.add(int(shape.get("id")))
        except (AttributeError, TypeError, ValueError):
            continue

    filtered_cards = []
    for card in shape_cards_data:
        if not isinstance(card, dict):
            continue
        try:
            card_id = int(card.get("id"))
        except (TypeError, ValueError):
            continue
        if card_id in valid_ids:
            filtered_cards.append(card)
    directions_for_save = dict(getattr(self, "flow_directions", {}))
    for card in filtered_cards:
        motion = card.get("motion")
        if not isinstance(motion, dict):
            continue
        try:
            card_id = int(card.get("id"))
        except (TypeError, ValueError):
            continue
        if motion.get("direction") is not None:
            directions_for_save[card_id] = motion["direction"]
    flow_directions = serialize_flow_directions(directions_for_save, valid_ids)
    _write_json_atomic(
        project_path,
        {
            "schema_version": PROJECT_SCHEMA_VERSION,
            "background": bg_for_json,
            "shapes": shape_data,
            "shape_cards": filtered_cards,
            "flow_directions": flow_directions,
        },
    )

    self.current_project_folder = folder
    self.current_shapes_json_path = project_path

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

    print(f"[SAVE] Сохранено {index - 1} фигур: {self.current_shapes_json_path}")
    return self.current_shapes_json_path
