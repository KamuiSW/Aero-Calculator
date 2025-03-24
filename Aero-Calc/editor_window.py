import sys
import os
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QDockWidget, QTreeWidget, QTreeWidgetItem,
                           QSizePolicy, QDoubleSpinBox, QComboBox, QCheckBox,
                           QGroupBox, QPushButton, QFormLayout)
from PyQt6.QtCore import Qt, QSize, QSettings, QPoint, QByteArray
from PyQt6.QtGui import QFont, QColor
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

class Viewport(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.rotation = [0, 0, 0]
        self.last_pos = None
        self.show_grid = True
        self.show_axes = True
        self.grid_size = 10
        self.grid_spacing = 1.0
        
    def initializeGL(self):
        glClearColor(0.15, 0.15, 0.15, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glLight(GL_LIGHT0, GL_POSITION, (5.0, 5.0, 5.0, 1.0))
        
    def draw_grid(self):
        glLineWidth(1.0)
        glBegin(GL_LINES)
        glColor3f(0.2, 0.2, 0.2)  # Dark gray for grid
        
        for i in range(-self.grid_size, self.grid_size + 1):
            glVertex3f(i * self.grid_spacing, 0, -self.grid_size * self.grid_spacing)
            glVertex3f(i * self.grid_spacing, 0, self.grid_size * self.grid_spacing)
            glVertex3f(-self.grid_size * self.grid_spacing, 0, i * self.grid_spacing)
            glVertex3f(self.grid_size * self.grid_spacing, 0, i * self.grid_spacing)
        glEnd()
        
    def draw_axes(self):
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
        
    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
        
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0, 2, 5, 0, 0, 0, 0, 1, 0)
        
        glRotatef(self.rotation[0], 1, 0, 0)
        glRotatef(self.rotation[1], 0, 1, 0)
        
        if self.show_grid:
            self.draw_grid()
        if self.show_axes:
            self.draw_axes()
        
    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        
    def mouseMoveEvent(self, event):
        if self.last_pos is None:
            self.last_pos = event.pos()
            return
            
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()
        
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.rotation[1] += dx
            self.rotation[0] += dy
            self.update()
            
        self.last_pos = event.pos()
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.obj', '.fbx')):
                self.load_model(file_path)
                
    def load_model(self, file_path):
        # TODO: Implement model loading using Assimp
        print(f"Loading model: {file_path}")

class EditorWindow(QMainWindow):
    def __init__(self, project_path):
        super().__init__()
        self.project_path = project_path
        self.settings = QSettings('AeroCalculator', 'Editor')
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
        
        # Create Properties Panel (right dock)
        properties_dock = QDockWidget("Properties", self)
        properties_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        properties_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                  QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                  QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
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
        
        # Create Scene Hierarchy (left dock)
        hierarchy_dock = QDockWidget("Scene Hierarchy", self)
        hierarchy_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        hierarchy_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                 QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                 QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
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
        
        # Create Physics Panel (bottom dock)
        physics_dock = QDockWidget("Physics Properties", self)
        physics_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        physics_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                               QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                               QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
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
        
        # Add form to physics layout
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
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, physics_dock)
        
        # Create Viewport Controls Panel (top dock)
        viewport_dock = QDockWidget("Viewport Controls", self)
        viewport_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        viewport_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                               QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                               QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
        viewport_widget = QWidget()
        viewport_layout = QHBoxLayout(viewport_widget)
        
        # Grid controls
        grid_group = QGroupBox("Grid")
        grid_layout = QVBoxLayout()
        self.show_grid_cb = QCheckBox("Show Grid")
        self.show_grid_cb.setChecked(True)
        self.show_grid_cb.toggled.connect(self.toggle_grid)
        grid_layout.addWidget(self.show_grid_cb)
        grid_group.setLayout(grid_layout)
        viewport_layout.addWidget(grid_group)
        
        # Axes controls
        axes_group = QGroupBox("Axes")
        axes_layout = QVBoxLayout()
        self.show_axes_cb = QCheckBox("Show Axes")
        self.show_axes_cb.setChecked(True)
        self.show_axes_cb.toggled.connect(self.toggle_axes)
        axes_layout.addWidget(self.show_axes_cb)
        axes_group.setLayout(axes_layout)
        viewport_layout.addWidget(axes_group)
        
        viewport_layout.addStretch()
        viewport_dock.setWidget(viewport_widget)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, viewport_dock)
        
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
        
    def saveSettings(self):
        # Save window state and geometry
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        
        # Save physics settings
        self.settings.setValue('air_density', self.air_density.value())
        self.settings.setValue('temperature', self.temperature.value())
        self.settings.setValue('velocity', self.velocity.value())
        self.settings.setValue('angle_of_attack', self.angle_of_attack.value())
        self.settings.setValue('turbulence_model', self.turbulence_model.currentText())
        
        # Save viewport settings
        self.settings.setValue('show_grid', self.show_grid_cb.isChecked())
        self.settings.setValue('show_axes', self.show_axes_cb.isChecked())
        
    def loadSettings(self):
        # Restore window state and geometry
        if self.settings.value('geometry'):
            self.restoreGeometry(self.settings.value('geometry'))
        if self.settings.value('windowState'):
            self.restoreState(self.settings.value('windowState'))
            
        # Restore physics settings
        self.air_density.setValue(float(self.settings.value('air_density', 1.225)))
        self.temperature.setValue(float(self.settings.value('temperature', 20)))
        self.velocity.setValue(float(self.settings.value('velocity', 0)))
        self.angle_of_attack.setValue(float(self.settings.value('angle_of_attack', 0)))
        index = self.turbulence_model.findText(self.settings.value('turbulence_model', "None"))
        if index >= 0:
            self.turbulence_model.setCurrentIndex(index)
            
        # Restore viewport settings
        self.show_grid_cb.setChecked(self.settings.value('show_grid', True, type=bool))
        self.show_axes_cb.setChecked(self.settings.value('show_axes', True, type=bool))
        
    def closeEvent(self, event):
        self.saveSettings()
        super().closeEvent(event) 