import sys
import os

import backend_client

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QMainWindow, QGraphicsScene,
)

from ai_panel_logic import AIWindow
from ui_editor import Ui_MainWindow

from import_image import import_image
from zoom import GraphicsViewWithZoom
from colors_menu import choose_color
from hide_or_unhide_panels import toggle_tools_panel, toggle_layers_panel

from draw_logic import DrawingToolController
from Activate_disconect_button import (
    activate_rectangle_mode, deactivate_drawing_mode, activate_circle_mode
)
from on_shape_selected import on_shape_selected
from save_logic import _save_outputs_impl, save_outputs
from show_all_handle import show_all_handles

from navigation_overlay import NavigationOverlay

from obj_list_logic import   on_list_item_selected

from hide_unhide import toggle_all_fill

from context_menu import on_key_press

from import_scene import load_scene
from Activate_disconect_button import activate_polygon_mode
from m_event import MouseMoveFilter
from effect_preview import start_effect_preview
from flow_direction_tool import FlowDirectionController
from effect_engine.project import normalize_direction


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Заменяем стандартный graphicsView на улучшенный
        self.graphics_view = GraphicsViewWithZoom(self)
        self.ui.horizontalLayout_9.removeWidget(self.ui.graphicsView)
        self.ui.horizontalLayout_9.addWidget(self.graphics_view)
        self.ui.graphicsView.hide()
        self.ui.graphicsView = self.graphics_view

        # Создаём сцену и устанавливаем в graphicsView
        self.scene = QGraphicsScene()

        # последний сохранённый проект (для передачи в AI panel)
        self.current_project_folder = None
        self.current_shapes_json_path = None
        self.ui.graphicsView.setScene(self.scene)

        # Панели скрыты при старте
        self.ui.frame_5.hide()
        self.ui.frame_4.hide()

        # Регистрация фигур
        self.shape_registry = {}  # {id: QGraphicsItem}
        self.shape_id_counter = 1
        self.flow_directions = {}  # {shape_id: normalized (x, y)}
        self.flow_guides = {}  # {shape_id: [{start: [x,y], end: [x,y]}]}
        self.effect_overrides = {}  # manual speed/obstacle/foam zones by shape

        # Кнопки UI
        self.ui.tools_Button.clicked.connect(lambda: toggle_tools_panel(self))
        self.ui.layers_batton.clicked.connect(lambda: toggle_layers_panel(self))
        self.ui.import_button.clicked.connect(lambda: import_image(self))
        self.ui.palette_Button.clicked.connect(lambda: choose_color(self))
        self.ui.Rectangle.clicked.connect(lambda: activate_rectangle_mode(self))
        self.ui.Cursor.clicked.connect(lambda: deactivate_drawing_mode(self))
        self.ui.cursor_Button.clicked.connect(lambda: deactivate_drawing_mode(self))
        self.ui.Circle.clicked.connect(lambda: activate_circle_mode(self))
        self.ui.save_button.setText("Save project")
        self.ui.save_button.setToolTip(
            "Save background, shapes, pieces, flow directions and AI effects"
        )
        self.ui.save_button.clicked.connect(lambda: save_outputs(self))
        self.ui.Resizable_button.clicked.connect(lambda: show_all_handles(self))
        self.ui.preview_button.setText("Local preview")
        self.ui.preview_button.setToolTip(
            "Deterministic preview; runs locally without AI backend"
        )
        self.ui.preview_button.clicked.connect(lambda: start_effect_preview(self))
        self.ai_prepare_checkbox = QCheckBox("AI prep")
        self.ai_prepare_checkbox.setToolTip(
            "Use optional SAM and Depth Anything proposals for mask/depth. "
            "Models are downloaded on first use; Local preview remains the fallback."
        )
        self.ui.horizontalLayout_4.insertWidget(
            max(0, self.ui.horizontalLayout_4.count() - 1),
            self.ai_prepare_checkbox,
        )

        # Подключение селектора
        self.scene.selectionChanged.connect(lambda: on_shape_selected(self))

        # Настройки рисования
        self.current_shape_color = QColor(255, 0, 0, 50)
        self.draw_controller = DrawingToolController(self.scene, self)
        self.flow_direction_controller = FlowDirectionController(self)
        self.ui.settings.setToolTip(
            "Edit flow curves and manual speed, obstacle, foam and mask zones"
        )
        self.ui.settings.clicked.connect(self.flow_direction_controller.toggle)
        self.scene.selectionChanged.connect(
            self.flow_direction_controller.refresh_for_selection
        )

        # 🧠 Важно: добавляем overlay после сцены
        self.navigation_overlay = NavigationOverlay(self.ui.graphicsView, self)



        self.ui.listWidget.itemClicked.connect(lambda item: on_list_item_selected(self, item))

        self.fill_hidden_global = False
        self.ui.eye_Button.clicked.connect(lambda: toggle_all_fill(self))


        self.ui.import_sceen.clicked.connect(lambda: load_scene(self))

        self.shape_parents = {}  # {child_id: parent_id}

        self.ui.by_point.clicked.connect(lambda: activate_polygon_mode(self))

        self.mouse_filter = MouseMoveFilter(self.navigation_overlay, self.scene)
        self.scene.installEventFilter(self.mouse_filter)

        self.ai_window = AIWindow()
        self.ai_window.motion_changed.connect(self._sync_ai_motion)
        self.ai_window.project_sync_callback = self._sync_current_project
        self.ai_window.hide()  # окно создано (для фантомов), но не показано
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(backend_client.shutdown_local_backend)

        def open_ai():
            # прокидываем пути проекта в AI panel, чтобы render не спрашивал диалоги
            try:
                if getattr(self, "current_shapes_json_path", None):
                    base_dir = os.path.dirname(self.current_shapes_json_path)
                    pieces_dir = os.path.join(base_dir, "pieces")
                    if not os.path.isdir(pieces_dir):
                        pieces_dir = base_dir
                    masks_dir = os.path.join(base_dir, "masks")
                    out_mp4 = os.path.join(base_dir, "result.mp4")
                    self.ai_window.set_render_sources(
                        shapes_json_path=self.current_shapes_json_path,
                        pieces_dir=pieces_dir,
                        masks_dir=masks_dir,
                        out_mp4_path=out_mp4,
                    )
            except Exception as _e:
                print("⚠️ Не удалось прокинуть пути в AI panel:", _e)

            self.ai_window.show()
            self.ai_window.raise_()
            self.ai_window.activateWindow()

        self.ui.ai_panel.clicked.connect(open_ai)

    def _sync_ai_motion(self, shape_id, motion):
        direction = normalize_direction((motion or {}).get("direction"))
        if direction is None or int(shape_id) not in self.shape_registry:
            return
        shape_id = int(shape_id)
        previous = normalize_direction(self.flow_directions.get(shape_id))
        if previous is not None and any(
            abs(previous[index] - direction[index]) > 1e-6 for index in (0, 1)
        ):
            self.flow_guides.pop(shape_id, None)
        self.flow_directions[shape_id] = direction
        self.flow_direction_controller.refresh_for_selection()

    def _sync_current_project(self):
        """Persist current geometry/effects silently before preview or rendering."""
        folder = getattr(self, "current_project_folder", None)
        if not folder:
            return getattr(self, "current_shapes_json_path", None)
        return _save_outputs_impl(self, folder=folder)

    def keyPressEvent(self, event):
        if not on_key_press(self, event):
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
