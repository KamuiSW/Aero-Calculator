import sys
import os
import json
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QDockWidget, QTreeWidget, QTreeWidgetItem,
                           QSizePolicy, QDoubleSpinBox, QComboBox, QCheckBox,
                           QGroupBox, QPushButton, QFormLayout, QToolBar,
                           QToolButton, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QSettings, QPoint, QByteArray
from PyQt6.QtGui import QFont, QColor, QAction
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

class Viewport(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.rotation = [30, 45, 0]  # Initial rotation for better view
        self.last_pos = None
        self.show_grid = True
        self.show_axes = True
        self.grid_size = 10
        self.grid_spacing = 1.0
        self.zoom = 15.0
        self.zoom_speed = 0.1
        self.min_zoom = 0.1
        self.max_zoom = 100.0
        self.model_vertices = []
        self.model_normals = []
        self.model_loaded = False
        self.current_model_path = None  # Store the current model path
        # Vertex buffer objects
        self.vbo_vertices = None
        self.vbo_normals = None
        self.vertex_count = 0
        
    def initializeGL(self):
        glClearColor(0.15, 0.15, 0.15, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        
        # Set up lighting
        glLightfv(GL_LIGHT0, GL_POSITION, (5.0, 5.0, 5.0, 1.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1.0))
        
        # Create vertex buffer objects
        self.vbo_vertices = GLuint(0)
        self.vbo_normals = GLuint(0)
        glGenBuffers(1, self.vbo_vertices)
        glGenBuffers(1, self.vbo_normals)

    def resizeGL(self, w, h):
        if h == 0:
            h = 1
        
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
        
    def draw_grid(self):
        glDisable(GL_LIGHTING)  # Disable lighting for grid
        glLineWidth(1.0)
        glBegin(GL_LINES)
        glColor3f(0.3, 0.3, 0.3)  # Slightly brighter gray for grid
        
        for i in range(-self.grid_size, self.grid_size + 1):
            glVertex3f(i * self.grid_spacing, 0, -self.grid_size * self.grid_spacing)
            glVertex3f(i * self.grid_spacing, 0, self.grid_size * self.grid_spacing)
            glVertex3f(-self.grid_size * self.grid_spacing, 0, i * self.grid_spacing)
            glVertex3f(self.grid_size * self.grid_spacing, 0, i * self.grid_spacing)
        glEnd()
        glEnable(GL_LIGHTING)  # Re-enable lighting
        
    def draw_axes(self):
        glDisable(GL_LIGHTING)  # Disable lighting for axes
        glLineWidth(2.0)
        glBegin(GL_LINES)
        # X axis (red)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(self.grid_spacing * 2, 0, 0)
        # Y axis (green)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, self.grid_spacing * 2, 0)
        # Z axis (blue)
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, self.grid_spacing * 2)
        glEnd()
        glEnable(GL_LIGHTING)  # Re-enable lighting

    def draw_model(self):
        if not self.model_loaded or self.vertex_count == 0:
            return

        glEnable(GL_LIGHTING)
        
        # Set material properties
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 32.0)

        # Enable vertex arrays
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        # Bind vertex buffer
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices.value)
        glVertexPointer(3, GL_FLOAT, 0, None)

        # Bind normal buffer
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals.value)
        glNormalPointer(GL_FLOAT, 0, None)

        # Draw the model
        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)

        # Cleanup
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Set camera position using correct rotation direction
        gluLookAt(
            self.zoom * np.sin(np.radians(self.rotation[1])), 
            self.zoom * np.sin(np.radians(self.rotation[0])), 
            self.zoom * np.cos(np.radians(self.rotation[1])),
            0, 0, 0,  # Look at center
            0, 1, 0   # Up vector
        )
        
        if self.show_grid:
            self.draw_grid()
        if self.show_axes:
            self.draw_axes()
        if self.model_loaded:
            self.draw_model()
            
    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        
    def mouseMoveEvent(self, event):
        if self.last_pos is None:
            self.last_pos = event.pos()
            return
            
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()
        
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.rotation[1] += dx * 0.5  # Normal direction
            self.rotation[0] += dy * 0.5
            self.update()
            
        self.last_pos = event.pos()

    def wheelEvent(self, event):
        zoom_factor = event.angleDelta().y() / 120
        new_zoom = self.zoom - (zoom_factor * self.zoom_speed * self.zoom)
        self.zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        self.update()
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(('.obj', '.fbx')):
                    event.accept()
                    return
        event.ignore()
            
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.obj', '.fbx')):
                self.load_model(file_path)
                break
                
    def cleanup(self):
        """Clean up OpenGL resources"""
        if self.vbo_vertices is not None:
            glDeleteBuffers(1, [self.vbo_vertices.value])
            self.vbo_vertices = None
        if self.vbo_normals is not None:
            glDeleteBuffers(1, [self.vbo_normals.value])
            self.vbo_normals = None
        self.vertex_count = 0
        self.model_loaded = False

    def save_state(self):
        """Return current state for saving"""
        return {
            'rotation': self.rotation,
            'zoom': self.zoom,
            'show_grid': self.show_grid,
            'show_axes': self.show_axes,
            'grid_size': self.grid_size,
            'current_model_path': self.current_model_path
        }

    def restore_state(self, state):
        """Restore state from saved settings"""
        if not state:
            return
        self.rotation = state.get('rotation', [30, 45, 0])
        self.zoom = state.get('zoom', 15.0)
        self.show_grid = state.get('show_grid', True)
        self.show_axes = state.get('show_axes', True)
        self.grid_size = state.get('grid_size', 10)
        
        # Reload model if it was previously loaded
        model_path = state.get('current_model_path')
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)

    def load_model(self, file_path):
        """Load a 3D model file."""
        try:
            # Clean up existing resources
            self.cleanup()
            
            if file_path.lower().endswith('.obj'):
                self.load_obj(file_path)
                self.current_model_path = file_path  # Store the path
            elif file_path.lower().endswith('.fbx'):
                QMessageBox.warning(self, "Warning", "FBX support coming soon!")
                return
                
            self.model_loaded = True
            if isinstance(self.parent(), EditorWindow):
                self.parent().update_scene_hierarchy(os.path.basename(file_path))
            
            self.update()
            QMessageBox.information(self, "Success", f"Model loaded: {os.path.basename(file_path)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model: {str(e)}")
            print(f"Error loading model: {str(e)}")

    def load_obj(self, file_path):
        """Load an OBJ file."""
        vertices = []
        normals = []
        faces = []
        temp_vertices = []
        temp_normals = []
        
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith('#'): continue
                values = line.split()
                if not values: continue
                
                if values[0] == 'v':
                    temp_vertices.append([float(x) for x in values[1:4]])
                elif values[0] == 'vn':
                    temp_normals.append([float(x) for x in values[1:4]])
                elif values[0] == 'f':
                    # Handle different face formats
                    face_vertices = []
                    face_normals = []
                    for v in values[1:]:
                        w = v.split('/')
                        # OBJ indices start at 1
                        vertex_index = int(w[0]) - 1
                        face_vertices.append(vertex_index)
                        # Check if normal index exists
                        if len(w) > 2 and w[2]:
                            normal_index = int(w[2]) - 1
                            face_normals.append(normal_index)
                    faces.append((face_vertices, face_normals))

        if not temp_vertices:
            raise ValueError("No vertices found in the OBJ file")

        # Convert faces to triangles and build final vertex list
        vertices_list = []
        normals_list = []
        
        for face_vertices, face_normals in faces:
            # Triangulate face if it has more than 3 vertices
            for i in range(1, len(face_vertices) - 1):
                # Add vertices for triangle
                vertices_list.extend(temp_vertices[face_vertices[0]])
                vertices_list.extend(temp_vertices[face_vertices[i]])
                vertices_list.extend(temp_vertices[face_vertices[i + 1]])
                
                # Add corresponding normals if available
                if face_normals and len(face_normals) > i + 1:
                    normals_list.extend(temp_normals[face_normals[0]])
                    normals_list.extend(temp_normals[face_normals[i]])
                    normals_list.extend(temp_normals[face_normals[i + 1]])
                else:
                    # Calculate face normal if not provided
                    v1 = np.array(temp_vertices[face_vertices[0]])
                    v2 = np.array(temp_vertices[face_vertices[i]])
                    v3 = np.array(temp_vertices[face_vertices[i + 1]])
                    normal = np.cross(v2 - v1, v3 - v1)
                    norm = np.linalg.norm(normal)
                    if norm > 0:
                        normal = normal / norm
                    else:
                        normal = np.array([0.0, 1.0, 0.0])  # Default normal if calculation fails
                    normals_list.extend(normal)
                    normals_list.extend(normal)
                    normals_list.extend(normal)

        # Convert to numpy arrays for faster processing
        vertices_array = np.array(vertices_list, dtype=np.float32)
        normals_array = np.array(normals_list, dtype=np.float32)

        # Reshape arrays to ensure correct format
        vertices_array = vertices_array.reshape(-1, 3)
        normals_array = normals_array.reshape(-1, 3)

        # Center and scale the model
        min_coords = np.min(vertices_array, axis=0)
        max_coords = np.max(vertices_array, axis=0)
        center = (min_coords + max_coords) / 2
        size = np.max(max_coords - min_coords)
        scale = 5.0 / size if size > 0 else 1.0  # Scale to fit in a 5x5x5 box

        # Apply transformation
        vertices_array = (vertices_array - center) * scale

        # Update vertex count
        self.vertex_count = len(vertices_array)

        # Make sure arrays are contiguous and correct size
        vertices_array = np.ascontiguousarray(vertices_array, dtype=np.float32)
        normals_array = np.ascontiguousarray(normals_array, dtype=np.float32)

        # Upload data to GPU
        try:
            # Bind and upload vertex data
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices.value)
            glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array.tobytes(), GL_STATIC_DRAW)

            # Bind and upload normal data
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals.value)
            glBufferData(GL_ARRAY_BUFFER, normals_array.nbytes, normals_array.tobytes(), GL_STATIC_DRAW)

            # Unbind buffer
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            
        except Exception as e:
            raise RuntimeError(f"Failed to upload data to GPU: {str(e)}")

class EditorWindow(QMainWindow):
    def __init__(self, project_path):
        super().__init__()
        self.project_path = project_path
        self.settings = QSettings('AeroCalculator', 'Editor')
        self.dock_widgets = {}  # Store references to dock widgets
        self.initUI()
        self.loadSettings()
        
    def initUI(self):
        self.setWindowTitle('Aero Calculator - Editor')
        self.setMinimumSize(1200, 800)
        
        # Set the style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QDockWidget {
                color: white;
                font-size: 14px;
            }
            QDockWidget::title {
                background: #2d2d2d;
                padding: 8px;
                border: 1px solid #3d3d3d;
            }
            QLabel {
                color: white;
                font-size: 13px;
                padding: 4px;
            }
            QTreeWidget {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
            }
            QWidget {
                background-color: #252526;
            }
        """)
        
        # Create central widget with OpenGL viewport
        self.viewport = Viewport()
        self.setCentralWidget(self.viewport)
        
        # Create floating toolbar for viewport controls
        toolbar = QToolBar("Viewport Controls")
        toolbar.setObjectName("viewportControls")  # Add object name
        toolbar.setFloatable(True)
        toolbar.setMovable(True)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: rgba(45, 45, 45, 200);
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 6px;
                spacing: 4px;
            }
            QToolButton {
                color: white;
                background-color: rgba(60, 60, 60, 180);
                border: 1px solid #3d3d3d;
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 60px;
                font-size: 12px;
                font-weight: 500;
            }
            QToolButton:hover {
                background-color: rgba(70, 70, 70, 180);
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QToolButton:checked {
                background-color: rgba(0, 120, 212, 180);
                border: 1px solid rgba(255, 255, 255, 40);
            }
            QToolButton::menu-indicator {
                image: none;
            }
            QDoubleSpinBox {
                background-color: rgba(60, 60, 60, 180);
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 70px;
                font-size: 12px;
                selection-background-color: #0078d4;
            }
            QDoubleSpinBox:hover {
                background-color: rgba(70, 70, 70, 180);
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                border: none;
                background: transparent;
                width: 16px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: rgba(255, 255, 255, 20);
            }
            QMenu {
                background-color: rgba(45, 45, 45, 230);
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 28px 6px 12px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 120, 212, 180);
            }
            QMenu::separator {
                height: 1px;
                background: #3d3d3d;
                margin: 4px 8px;
            }
        """)

        # Create a widget for grid controls
        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(4)

        # Grid toggle button
        self.show_grid_btn = QToolButton()
        self.show_grid_btn.setText("Grid")
        self.show_grid_btn.setToolTip("Toggle Grid Visibility")
        self.show_grid_btn.setCheckable(True)
        self.show_grid_btn.setChecked(True)
        self.show_grid_btn.toggled.connect(self.toggle_grid)
        grid_layout.addWidget(self.show_grid_btn)

        # Grid size control
        self.grid_size_spin = QDoubleSpinBox()
        self.grid_size_spin.setRange(1, 50)
        self.grid_size_spin.setValue(10)
        self.grid_size_spin.setSuffix(" units")
        self.grid_size_spin.setToolTip("Adjust Grid Size")
        self.grid_size_spin.valueChanged.connect(lambda v: setattr(self.viewport, 'grid_size', int(v)))
        grid_layout.addWidget(self.grid_size_spin)

        toolbar.addWidget(grid_widget)
        toolbar.addSeparator()

        # Axes toggle button
        self.show_axes_btn = QToolButton()
        self.show_axes_btn.setText("Axes")
        self.show_axes_btn.setToolTip("Toggle Axes Visibility")
        self.show_axes_btn.setCheckable(True)
        self.show_axes_btn.setChecked(True)
        self.show_axes_btn.toggled.connect(self.toggle_axes)
        toolbar.addWidget(self.show_axes_btn)

        toolbar.addSeparator()

        # Windows dropdown button
        windows_btn = QToolButton()
        windows_btn.setText("Windows")
        windows_btn.setToolTip("Show/Hide Window Panels")
        windows_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        windows_menu = QMenu(windows_btn)
        
        # Add menu items for each dock widget
        scene_hierarchy_action = windows_menu.addAction("Scene Hierarchy")
        scene_hierarchy_action.setStatusTip("Show Scene Hierarchy panel")
        properties_action = windows_menu.addAction("Properties")
        properties_action.setStatusTip("Show Properties panel")
        windows_menu.addSeparator()
        physics_action = windows_menu.addAction("Physics Properties")
        physics_action.setStatusTip("Show Physics Properties panel")
        
        # Connect actions to show/hide functions
        scene_hierarchy_action.triggered.connect(lambda: self.show_dock_widget("hierarchy"))
        properties_action.triggered.connect(lambda: self.show_dock_widget("properties"))
        physics_action.triggered.connect(lambda: self.show_dock_widget("physics"))
        
        windows_btn.setMenu(windows_menu)
        toolbar.addWidget(windows_btn)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        toolbar.setAllowedAreas(Qt.ToolBarArea.AllToolBarAreas)
        
        # Create Scene Hierarchy (left dock)
        hierarchy_dock = QDockWidget("Scene Hierarchy", self)
        hierarchy_dock.setObjectName("sceneHierarchy")  # Add object name
        hierarchy_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        hierarchy_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                 QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                 QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.dock_widgets["hierarchy"] = hierarchy_dock
        
        hierarchy_widget = QTreeWidget()
        hierarchy_widget.setHeaderHidden(True)
        
        # Add some sample hierarchy items
        scene_root = QTreeWidgetItem(["Scene"])
        hierarchy_widget.addTopLevelItem(scene_root)
        scene_root.setExpanded(True)
        
        # Add some placeholder items
        camera = QTreeWidgetItem(scene_root, ["Camera"])
        lights = QTreeWidgetItem(scene_root, ["Lights"])
        models = QTreeWidgetItem(scene_root, ["Models"])
        
        hierarchy_dock.setWidget(hierarchy_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, hierarchy_dock)
        
        # Create Properties Panel (right dock)
        properties_dock = QDockWidget("Properties", self)
        properties_dock.setObjectName("propertiesPanel")  # Add object name
        properties_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        properties_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                  QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                  QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.dock_widgets["properties"] = properties_dock
        
        properties_widget = QWidget()
        properties_layout = QVBoxLayout(properties_widget)
        properties_layout.setContentsMargins(10, 10, 10, 10)
        properties_layout.setSpacing(8)
        
        # Add some sample properties
        title_label = QLabel("Model Properties")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        properties_layout.addWidget(title_label)
        
        # Add some placeholder properties
        properties_layout.addWidget(QLabel("Dimensions"))
        properties_layout.addWidget(QLabel("Material"))
        properties_layout.addWidget(QLabel("Mass"))
        properties_layout.addStretch()
        
        properties_dock.setWidget(properties_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, properties_dock)
        
        # Create Physics Panel (right dock)
        physics_dock = QDockWidget("Physics Properties", self)
        physics_dock.setObjectName("physicsProperties")  # Add object name
        physics_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        physics_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                               QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                               QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.dock_widgets["physics"] = physics_dock
        
        physics_widget = QWidget()
        physics_layout = QVBoxLayout(physics_widget)
        physics_layout.setContentsMargins(10, 10, 10, 10)
        physics_layout.setSpacing(8)
        
        physics_title = QLabel("Physics Settings")
        physics_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        physics_layout.addWidget(physics_title)
        
        # Create form layout for physics properties
        form_layout = QFormLayout()
        
        # Air properties
        self.air_density = QDoubleSpinBox()
        self.air_density.setRange(0, 10)
        self.air_density.setValue(1.225)
        self.air_density.setSuffix(" kg/m³")
        form_layout.addRow("Air Density:", self.air_density)
        
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(-50, 50)
        self.temperature.setValue(20)
        self.temperature.setSuffix(" °C")
        form_layout.addRow("Temperature:", self.temperature)
        
        # Flow properties
        self.velocity = QDoubleSpinBox()
        self.velocity.setRange(0, 1000)
        self.velocity.setValue(0)
        self.velocity.setSuffix(" m/s")
        form_layout.addRow("Velocity:", self.velocity)
        
        self.angle_of_attack = QDoubleSpinBox()
        self.angle_of_attack.setRange(-90, 90)
        self.angle_of_attack.setValue(0)
        self.angle_of_attack.setSuffix(" °")
        form_layout.addRow("Angle of Attack:", self.angle_of_attack)
        
        # Turbulence model
        self.turbulence_model = QComboBox()
        self.turbulence_model.addItems(["None", "k-epsilon", "k-omega", "Spalart-Allmaras"])
        form_layout.addRow("Turbulence Model:", self.turbulence_model)
        
        physics_layout.addLayout(form_layout)
        
        # Add calculate button
        calc_button = QPushButton("Calculate Forces")
        calc_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1988d4;
            }
        """)
        physics_layout.addWidget(calc_button)
        physics_layout.addStretch()
        
        physics_dock.setWidget(physics_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, physics_dock)
        
        # Status bar
        self.statusBar().setStyleSheet("""
            QStatusBar {
                color: white;
                background-color: #2d2d2d;
                padding: 4px;
                font-size: 13px;
            }
        """)
        self.statusBar().showMessage("Ready - Drag and drop 3D models to import") 
        
    def toggle_grid(self, state):
        self.viewport.show_grid = state
        self.viewport.update()
        
    def toggle_axes(self, state):
        self.viewport.show_axes = state
        self.viewport.update()
        
    def show_dock_widget(self, widget_name):
        """Show the specified dock widget if it exists."""
        if widget_name in self.dock_widgets:
            self.dock_widgets[widget_name].show()
            self.dock_widgets[widget_name].raise_()
        
    def saveSettings(self):
        # Save window state and geometry
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        
        # Save viewport state
        viewport_state = self.viewport.save_state()
        self.settings.setValue('viewport_state', viewport_state)
        
        # Save physics settings
        self.settings.setValue('air_density', self.air_density.value())
        self.settings.setValue('temperature', self.temperature.value())
        self.settings.setValue('velocity', self.velocity.value())
        self.settings.setValue('angle_of_attack', self.angle_of_attack.value())
        self.settings.setValue('turbulence_model', self.turbulence_model.currentText())
        
        # Save viewport settings
        self.settings.setValue('show_grid', self.show_grid_btn.isChecked())
        self.settings.setValue('show_axes', self.show_axes_btn.isChecked())
        
    def loadSettings(self):
        # Restore window state and geometry
        if self.settings.value('geometry'):
            self.restoreGeometry(self.settings.value('geometry'))
        if self.settings.value('windowState'):
            self.restoreState(self.settings.value('windowState'))
        
        # Restore viewport state
        viewport_state = self.settings.value('viewport_state')
        if viewport_state:
            self.viewport.restore_state(viewport_state)
            
        # Restore physics settings
        self.air_density.setValue(float(self.settings.value('air_density', 1.225)))
        self.temperature.setValue(float(self.settings.value('temperature', 20)))
        self.velocity.setValue(float(self.settings.value('velocity', 0)))
        self.angle_of_attack.setValue(float(self.settings.value('angle_of_attack', 0)))
        index = self.turbulence_model.findText(self.settings.value('turbulence_model', "None"))
        if index >= 0:
            self.turbulence_model.setCurrentIndex(index)
            
        # Restore viewport settings
        self.show_grid_btn.setChecked(self.settings.value('show_grid', True, type=bool))
        self.show_axes_btn.setChecked(self.settings.value('show_axes', True, type=bool))
        
    def closeEvent(self, event):
        self.viewport.cleanup()  # Clean up OpenGL resources
        self.saveSettings()
        super().closeEvent(event)

    def update_scene_hierarchy(self, model_name):
        """Update the scene hierarchy with the loaded model."""
        if "hierarchy" not in self.dock_widgets:
            return
            
        hierarchy_widget = self.dock_widgets["hierarchy"].widget()
        if not hierarchy_widget:
            return
            
        # Find the Models item
        root = hierarchy_widget.invisibleRootItem()
        scene_item = root.child(0)  # Get the Scene item
        models_item = None
        
        for i in range(scene_item.childCount()):
            if scene_item.child(i).text(0) == "Models":
                models_item = scene_item.child(i)
                break
        
        if models_item is None:
            return
            
        # Add the new model
        model_item = QTreeWidgetItem(models_item, [model_name])
        models_item.setExpanded(True) 