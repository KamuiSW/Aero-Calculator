import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QFileDialog, QMessageBox, QDialog, QScrollArea,
                           QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
from editor_window import EditorWindow
from OpenGL.GL import glGetString
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, List

# Global variable to store project directory
PROJECTS_DIR = os.path.expanduser("~/AeroProjects")

@dataclass
class FlowConditions:
    """Class to store flow conditions"""
    density: float  # Air density (kg/m³)
    velocity: float  # Flow velocity (m/s)
    temperature: float  # Temperature (°C)
    viscosity: float  # Dynamic viscosity (kg/m·s)
    angle_of_attack: float  # Angle of attack (degrees)

@dataclass
class AerodynamicForces:
    """Class to store calculated forces"""
    lift: float  # Lift force (N)
    drag: float  # Drag force (N)
    moment: float  # Pitching moment (N·m)
    pressure_distribution: Dict[int, float]  # Pressure at each vertex
    cp: float  # Pressure coefficient

class AeroPhysicsEngine:
    """Main class for aerodynamic calculations"""
    
    def __init__(self):
        self.vertices = None
        self.normals = None
        self.faces = None
        self.flow_conditions = None
        
    def set_mesh(self, vertices: np.ndarray, normals: np.ndarray, faces: np.ndarray):
        """Set the mesh data for calculations"""
        self.vertices = vertices
        self.normals = normals
        self.faces = faces
        
    def set_flow_conditions(self, conditions: FlowConditions):
        """Set the flow conditions"""
        self.flow_conditions = conditions
        
    def calculate_forces(self) -> AerodynamicForces:
        """Calculate aerodynamic forces"""
        if not all([self.vertices is not None, 
                   self.normals is not None,
                   self.flow_conditions is not None]):
            raise ValueError("Mesh data or flow conditions not set")
            
        try:
            # Calculate reference area
            reference_area = self.calculate_reference_area()
            
            # Calculate dynamic pressure
            q_inf = 0.5 * self.flow_conditions.density * self.flow_conditions.velocity ** 2
            
            # Simple force calculation based on angle of attack
            alpha = np.radians(self.flow_conditions.angle_of_attack)
            
            # Basic lift and drag coefficients (simplified)
            cl = 2 * np.pi * alpha  # Simplified thin airfoil theory
            cd = 0.1 + 0.1 * alpha * alpha  # Simplified drag polar
            
            # Calculate forces
            lift = q_inf * reference_area * cl
            drag = q_inf * reference_area * cd
            moment = -0.25 * lift  # Simplified moment calculation
            
            # Generate simplified pressure distribution
            pressure_dist = {}
            for i in range(len(self.vertices)):
                # Simple pressure distribution based on height
                y_pos = self.vertices[i][1]  # Y coordinate
                cp = -2 * y_pos / reference_area
                pressure_dist[i] = cp
            
            return AerodynamicForces(
                lift=float(lift),
                drag=float(drag),
                moment=float(moment),
                pressure_distribution=pressure_dist,
                cp=float(cl)  # Using lift coefficient as pressure coefficient
            )
            
        except Exception as e:
            raise RuntimeError(f"Force calculation failed: {str(e)}")
    
    def calculate_reference_area(self) -> float:
        """Calculate reference area for force coefficients"""
        if self.vertices is None:
            raise ValueError("Mesh data not set")
            
        # Project vertices onto XY plane for planform area
        xy_vertices = self.vertices[:, :2]
        # Calculate convex hull area as approximation
        from scipy.spatial import ConvexHull
        hull = ConvexHull(xy_vertices)
        return hull.area

class ProjectCard(QFrame):
    def __init__(self, project_name, project_path, last_opened, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.main_window = parent
        self.initUI(project_name, last_opened)
        
    def initUI(self, project_name, last_opened):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            ProjectCard {
                background-color: #2d2d2d;
                border-radius: 5px;
                padding: 20px;
                margin: 8px;
            }
            ProjectCard:hover {
                background-color: #3d3d3d;
            }
            QLabel {
                color: #ffffff;
                padding: 4px;
                margin: 2px;
            }
            QLabel[class="project-name"] {
                font-size: 14px;
                font-weight: bold;
                padding-bottom: 8px;
            }
            QLabel[class="project-info"] {
                color: #b0b0b0;
                font-size: 13px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 3px;
                font-size: 13px;
                margin: 4px;
            }
            QPushButton.delete-btn {
                background-color: #d42828;
                color: white;
                border: none;
            }
            QPushButton.delete-btn:hover {
                background-color: #e83333;
            }
            QPushButton.open-btn {
                background-color: #0078d4;
                color: white;
                border: none;
            }
            QPushButton.open-btn:hover {
                background-color: #1988d4;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)  # Increased spacing between widgets
        layout.setContentsMargins(15, 15, 15, 15)  # Increased margins
        
        # Project name in bold
        name_label = QLabel(project_name)
        name_label.setProperty('class', 'project-name')
        name_label.setWordWrap(True)
        
        # Path and last opened date
        path_label = QLabel(f"Path: {self.project_path}")
        path_label.setProperty('class', 'project-info')
        path_label.setWordWrap(True)
        path_label.setMinimumHeight(40)
        
        date_label = QLabel(f"Last opened: {last_opened}")
        date_label.setProperty('class', 'project-info')
        
        # Buttons layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Open button
        open_btn = QPushButton("Open Project")
        open_btn.setProperty('class', 'open-btn')
        open_btn.clicked.connect(self.open_project)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setProperty('class', 'delete-btn')
        delete_btn.clicked.connect(self.delete_project)
        
        button_layout.addWidget(open_btn)
        button_layout.addWidget(delete_btn)
        
        layout.addWidget(name_label)
        layout.addWidget(path_label)
        layout.addWidget(date_label)
        layout.addSpacing(8)  # Add space before buttons
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setMinimumWidth(350)  # Increased minimum width
        self.setMinimumHeight(220)  # Increased minimum height
    
    def open_project(self):
        try:
            # Verify project file exists
            project_file = os.path.join(self.project_path, "project.aero")
            if not os.path.exists(project_file):
                QMessageBox.critical(self, "Error", "Project file not found!")
                return
                
            # Update last opened time
            with open(project_file, 'r') as f:
                project_info = json.load(f)
            
            from datetime import datetime
            project_info['last_opened'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(project_file, 'w') as f:
                json.dump(project_info, f, indent=4)
            
            # Open editor window
            self.editor_window = EditorWindow(self.project_path)
            self.editor_window.show()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open project: {str(e)}")

    def delete_project(self):
        reply = QMessageBox.question(self, 'Delete Project',
                                   'Are you sure you want to delete this project?\nThis will remove the project from the list but keep the files.',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove the card widget from its parent layout
            if self.parent() and self.parent().layout():
                self.parent().layout().removeWidget(self)
                self.deleteLater()

class ProjectWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.editor_window = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('New Aero Project')
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
                font-size: 13px;
            }
            QLineEdit {
                padding: 8px;
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 3px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1988d4;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout()
        layout.setSpacing(15)  # Increase spacing between elements
        
        # Project Name
        name_layout = QHBoxLayout()
        name_label = QLabel('Project Name:')
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        
        # Project Location
        location_layout = QHBoxLayout()
        location_label = QLabel('Location:')
        self.location_input = QLineEdit()
        self.location_input.setReadOnly(True)
        browse_location_btn = QPushButton('Browse')
        browse_location_btn.clicked.connect(self.browse_location)
        location_layout.addWidget(location_label)
        location_layout.addWidget(self.location_input)
        location_layout.addWidget(browse_location_btn)
        
        # Info text about 3D models
        info_label = QLabel("Note: You can add 3D models later by dragging them into the viewport")
        info_label.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                font-style: italic;
                padding: 10px;
            }
        """)
        info_label.setWordWrap(True)
        
        # Buttons
        button_layout = QHBoxLayout()
        create_btn = QPushButton('Create Project')
        create_btn.clicked.connect(self.create_project)
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(create_btn)
        
        # Add all widgets to main layout
        layout.addLayout(name_layout)
        layout.addLayout(location_layout)
        layout.addWidget(info_label)
        layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def browse_location(self):
        # Create the AeroProjects directory if it doesn't exist
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Project Location",
            PROJECTS_DIR  # Set default directory to AeroProjects
        )
        if folder:
            self.location_input.setText(folder)
    
    def create_project(self):
        if not self.name_input.text():
            QMessageBox.warning(self, "Error", "Please enter a project name")
            return
            
        if not self.location_input.text():
            QMessageBox.warning(self, "Error", "Please select a project location")
            return
        
        # Create project directory and save project info
        try:
            project_path = os.path.join(self.location_input.text(), self.name_input.text())
            os.makedirs(project_path, exist_ok=True)
            
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            project_info = {
                "name": self.name_input.text(),
                "created_date": current_time,
                "last_opened": current_time
            }
            
            project_file = os.path.join(project_path, "project.aero")
            with open(project_file, "w") as f:
                json.dump(project_info, f, indent=4)
            
            # Create and show editor window
            self.editor_window = EditorWindow(project_path)
            self.editor_window.show()
            
            # Update recent projects list
            if self.main_window:
                self.main_window.refresh_recent_projects()
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Create the AeroProjects directory if it doesn't exist
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Aero Calculator - Project Manager')
        self.setMinimumSize(1000, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
        """)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setSpacing(0)  # Remove spacing between panels
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Left panel - New Project
        left_panel = QWidget()
        left_panel.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 5px;
                margin: 10px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        new_project_btn = QPushButton("New Project")
        new_project_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 20px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1988d4;
            }
        """)
        new_project_btn.clicked.connect(self.show_project_wizard)
        
        left_layout.addWidget(new_project_btn)
        left_layout.addStretch()
        left_panel.setFixedWidth(200)
        
        # Right panel - Recent Projects
        right_panel = QWidget()
        right_panel.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 5px;
                margin: 10px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)  # Add padding
        right_layout.setSpacing(15)  # Add spacing between elements
        
        # Header layout with refresh button
        header_layout = QHBoxLayout()
        
        # Recent Projects Header
        header = QLabel("Recent Projects")
        header.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_recent_projects)
        
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        
        right_layout.addLayout(header_layout)
        
        # Scrollable area for project cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area.setWidget(self.scroll_content)
        right_layout.addWidget(self.scroll_area)
        
        # Add panels to main layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        
        # Load recent projects
        self.refresh_recent_projects()
    
    def refresh_recent_projects(self):
        # Clear existing project cards
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Find and load all .aero project files (only in AeroProjects directory)
        projects = []
        for root, dirs, files in os.walk(PROJECTS_DIR):
            for file in files:
                if file.endswith(".aero"):
                    project_file = os.path.join(root, file)
                    try:
                        with open(project_file, 'r') as f:
                            project_info = json.load(f)
                            projects.append({
                                'name': project_info.get('name', 'Unknown Project'),
                                'path': os.path.dirname(project_file),
                                'last_opened': project_info.get('last_opened', 'Never')
                            })
                    except:
                        continue
        
        # Sort projects by last opened time (most recent first)
        projects.sort(key=lambda x: x['last_opened'], reverse=True)
        
        # Add project cards
        for project in projects:
            card = ProjectCard(
                project['name'],
                project['path'],
                project['last_opened'],
                self.scroll_content
            )
            self.scroll_layout.addWidget(card)
        
        # Add stretch at the end
        self.scroll_layout.addStretch()
    
    def show_project_wizard(self):
        wizard = ProjectWizard(self)
        wizard.exec()

    def init_application(self):
        # Initialize OpenGL first
        self.init_opengl()
        
        # Only then load models
        self.load_models()

    def init_opengl(self):
        # Make sure the OpenGL context is current
        self.makeCurrent()
        
        # Initialize OpenGL
        print(f"OpenGL Version: {glGetString(GL_VERSION).decode()}")
        
        # Check for required extensions
        if not gl_info.have_extension('GL_ARB_vertex_buffer_object'):
            raise RuntimeError("VBO extension not available")

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 