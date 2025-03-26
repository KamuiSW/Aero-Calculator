import sys
import os
import json
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QDockWidget, QTreeWidget, QTreeWidgetItem,
                           QSizePolicy, QDoubleSpinBox, QComboBox, QCheckBox,
                           QGroupBox, QPushButton, QFormLayout, QToolBar,
                           QToolButton, QMenu, QMessageBox, QTabWidget, QScrollArea)
from PyQt6.QtCore import Qt, QSize, QSettings, QPoint, QByteArray
from PyQt6.QtGui import QFont, QColor, QAction, QDrag
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL import shaders
from OpenGL.GL.ARB.vertex_buffer_object import *
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
import logging
from datetime import datetime
from typing import Dict
from dataclasses import dataclass

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
        self.current_model_path = None
        # Add transform mode attributes
        self.transform_mode = False
        self.selected_object = None
        self.selected_axis = None
        self.dragging = False
        self.drag_start_pos = None
        self.drag_start_transform = None
        # Camera control attributes
        self.orbiting = False
        self.panning = False
        self.pan_offset = [0.0, 0.0]
        # Vertex buffer objects
        self.vbo_vertices = None
        self.vbo_normals = None
        self.vertex_count = 0
        
        # Set up OpenGL format
        format = self.format()
        format.setDepthBufferSize(24)
        format.setStencilBufferSize(8)
        format.setVersion(2, 1)
        format.setProfile(format.OpenGLContextProfile.CompatibilityProfile)
        self.setFormat(format)
        
        # Set up logging
        self.setup_logging()
        
        # Add these new attributes for camera control
        self.orbiting = False
        self.zoom = 15.0
        self.min_zoom = 0.1
        self.max_zoom = 100.0
        self.pan_offset = [0.0, 0.0]
        self.rotation = [30, 45, 0]  # Initial rotation angles
        
    def setup_logging(self):
        """Set up logging configuration"""
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'aero_calculator_{timestamp}.log')
        
        # Configure logging
        self.logger = logging.getLogger('AeroCalculator')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Logging initialized. Log file: {log_file}")

    def initializeGL(self):
        try:
            print("INFO: Initializing OpenGL")
            # Initialize OpenGL context
            self.makeCurrent()
            
            # Print OpenGL version
            version = glGetString(GL_VERSION).decode()
            print(f"INFO: OpenGL Version: {version}")
            
            # Initialize OpenGL extensions and basic setup
            self.init_gl_resources()
            
            print("INFO: OpenGL extensions initialized successfully")
            
            # Load saved state if it exists
            self.load_saved_state()
            
        except Exception as e:
            print(f"ERROR: Failed to initialize OpenGL: {str(e)}")

    def init_gl_resources(self):
        # Set up basic OpenGL state
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
        
    def create_buffers(self):
        """Create OpenGL buffer objects"""
        self.logger.debug("Creating OpenGL buffers...")
        
        try:
            # Make sure we have the current context
            self.makeCurrent()
            
            # Check if VBO extension is available
            if not bool(glGenBuffers):
                self.logger.error("VBO extension not available")
                return False
            
            # Delete existing buffers
            self.cleanup()
            
            # Generate new buffers
            self.vbo_vertices = GLuint(0)
            self.vbo_normals = GLuint(0)
            glGenBuffers(1, self.vbo_vertices)
            glGenBuffers(1, self.vbo_normals)
            
            if self.vbo_vertices.value == 0 or self.vbo_normals.value == 0:
                self.logger.error("Failed to generate buffer objects")
                return False
                
            self.logger.debug(f"Created buffers - Vertices: {self.vbo_vertices.value}, Normals: {self.vbo_normals.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating buffers: {str(e)}")
            self.cleanup()
            return False

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

        try:
            glPushMatrix()
            
            # Enable states
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glEnable(GL_COLOR_MATERIAL)
            
            # Set material properties
            glColor4f(0.8, 0.8, 0.8, 1.0)
            glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
            glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50.0)
            
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
            
            # Cleanup states
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            
            glPopMatrix()
            
        except Exception as e:
            self.logger.error(f"Error drawing model: {str(e)}")

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Apply camera transformations
        gluLookAt(
            self.zoom * np.sin(np.radians(self.rotation[1])), 
            self.zoom * np.sin(np.radians(self.rotation[0])), 
            self.zoom * np.cos(np.radians(self.rotation[1])),
            0, 0, 0,
            0, 1, 0
        )
        
        # Apply panning transformation
        glTranslatef(self.pan_offset[0], self.pan_offset[1], 0)
        
        if self.show_grid:
            self.draw_grid()
        if self.show_axes:
            self.draw_axes()
        if self.model_loaded:
            self.draw_model()
            if hasattr(self, 'pressure_data'):
                self.draw_streamlines()
        if hasattr(self, 'wind_plate'):
            self.draw_wind_plate()
            
        # Draw transform gizmos if an object is selected
        self.draw_transform_gizmos()

    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        
        if event.button() == Qt.MouseButton.RightButton:
            # Orbit camera mode
            self.orbiting = True
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Pan camera mode
            self.panning = True
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.transform_mode:
                # Check for transform gizmo interaction
                self.check_gizmo_pick(event.pos())
                if self.selected_axis:
                    self.dragging = True
                    self.drag_start_pos = event.pos()
                    self.drag_start_transform = self.get_object_transform()
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                # Normal selection mode
                self.check_object_selection(event.pos())

    def check_object_selection(self, mouse_pos):
        """Check if an object was clicked"""
        # Convert mouse position to ray
        ray_start, ray_dir = self.get_ray_from_mouse(mouse_pos)
        
        # Check wind plate if it exists
        if hasattr(self, 'wind_plate'):
            pos = self.wind_plate['position']
            # Simple distance check to wind plate center
            distance = np.linalg.norm(ray_start - pos)
            if distance < 2.0:  # Selection threshold
                self.selected_object = 'wind_plate'
                self.update()
                return
        
        # Check model if loaded
        if self.model_loaded:
            # Simple distance check to model center
            distance = np.linalg.norm(ray_start)
            if distance < 2.0:  # Selection threshold
                self.selected_object = 'model'
                self.update()
                return
        
        # If nothing was selected, clear selection
        self.selected_object = None
        self.selected_axis = None
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.orbiting = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.transform_mode:
                self.dragging = False
                self.selected_axis = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseMoveEvent(self, event):
        if self.last_pos is None:
            self.last_pos = event.pos()
            return
        
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()
        
        if self.orbiting and event.buttons() & Qt.MouseButton.RightButton:
            # Orbit camera around target
            self.rotation[1] -= dx * 0.5
            self.rotation[0] += dy * 0.5
        
        elif self.panning and event.buttons() & Qt.MouseButton.MiddleButton:
            pan_speed = 0.01 * self.zoom
            
            # Get camera's view direction
            rot_y = np.radians(self.rotation[1])
            rot_x = np.radians(self.rotation[0])
            
            # Calculate camera's forward vector
            forward = np.array([
                np.sin(rot_y) * np.cos(rot_x),
                np.sin(rot_x),
                np.cos(rot_y) * np.cos(rot_x)
            ])
            
            # Calculate camera's right vector
            right = np.cross(forward, np.array([0, 1, 0]))
            right = right / np.linalg.norm(right)
            
            # Calculate camera's up vector
            up = np.cross(right, forward)
            up = up / np.linalg.norm(up)
            
            # Apply movement in camera space
            self.pan_offset[0] += (right[0] * dx + up[0] * -dy) * pan_speed
            self.pan_offset[1] += (right[1] * dx + up[1] * -dy) * pan_speed
        
        elif self.dragging and self.selected_axis and self.selected_object:
            # Handle transform dragging
            self.handle_transform_drag(dx, dy)
        
        self.update()
        self.last_pos = event.pos()

    def handle_transform_drag(self, dx, dy):
        """Handle dragging of transform gizmos in world space"""
        if not self.selected_object or not self.drag_start_transform:
            return
            
        # Calculate movement speed based on zoom level
        move_speed = 0.01 * self.zoom
        
        # Get camera's view direction
        rot_y = np.radians(self.rotation[1])
        rot_x = np.radians(self.rotation[0])
        
        # Calculate camera's view vectors
        forward = np.array([
            np.sin(rot_y) * np.cos(rot_x),
            np.sin(rot_x),
            np.cos(rot_y) * np.cos(rot_x)
        ])
        
        # Calculate camera's right vector
        right = np.cross(forward, np.array([0, 1, 0]))
        right = right / np.linalg.norm(right)
        
        # Calculate camera's up vector
        up = np.cross(right, forward)
        up = up / np.linalg.norm(up)
        
        # Calculate movement based on selected axis and screen movement
        if self.selected_axis == 'x':
            # Project screen movement onto the world X axis
            screen_movement = right * dx + up * -dy
            movement = np.array([1, 0, 0]) * np.dot(screen_movement, np.array([1, 0, 0])) * move_speed
        elif self.selected_axis == 'y':
            # Project screen movement onto the world Y axis
            screen_movement = right * dx + up * -dy
            movement = np.array([0, 1, 0]) * np.dot(screen_movement, np.array([0, 1, 0])) * move_speed
        elif self.selected_axis == 'z':
            # Project screen movement onto the world Z axis
            screen_movement = right * dx + up * -dy
            movement = np.array([0, 0, 1]) * np.dot(screen_movement, np.array([0, 0, 1])) * move_speed
        else:
            return
            
        # Update object position
        if self.selected_object == 'wind_plate':
            self.wind_plate['position'] = self.drag_start_transform['position'] + movement
            # Update UI controls if parent is EditorWindow
            if isinstance(self.parent(), EditorWindow):
                self.parent().update_transform_ui()
        elif self.selected_object == 'model':
            # For model, we'll need to update all vertices
            if hasattr(self, 'model_vertices'):
                vertices = np.array(self.model_vertices).reshape(-1, 3)
                vertices += movement
                self.model_vertices = vertices.flatten()
                # Update vertex buffer
                glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices.value)
                glBufferData(GL_ARRAY_BUFFER, self.model_vertices.nbytes, self.model_vertices, GL_STATIC_DRAW)
                glBindBuffer(GL_ARRAY_BUFFER, 0)

    def check_gizmo_pick(self, mouse_pos):
        """Check if a transform gizmo was clicked"""
        if not self.selected_object:
            return
            
        # Convert mouse position to ray
        ray_start, ray_dir = self.get_ray_from_mouse(mouse_pos)
        
        # Get object position
        obj_pos = self.get_object_position()
        
        # Check distance to each axis
        axes = {
            'x': (np.array([1, 0, 0]), (1, 0, 0)),
            'y': (np.array([0, 1, 0]), (0, 1, 0)),
            'z': (np.array([0, 0, 1]), (0, 0, 1))
        }
        
        closest_axis = None
        min_distance = 0.1  # Threshold for selection
        
        for axis_name, (axis_dir, color) in axes.items():
            distance = self.point_line_distance(
                ray_start, ray_dir,
                obj_pos,
                obj_pos + axis_dir * 2.0
            )
            if distance < min_distance:
                min_distance = distance
                closest_axis = axis_name
        
        self.selected_axis = closest_axis

    def get_object_position(self):
        """Get the current position of the selected object"""
        if self.selected_object == 'model':
            return np.array([0, 0, 0])  # Model is centered at origin
        elif self.selected_object == 'wind_plate':
            return self.wind_plate['position']
        return np.array([0, 0, 0])

    def get_object_transform(self):
        """Get the current transform of the selected object"""
        if self.selected_object == 'model':
            # For model, return center position and zero rotation
            if hasattr(self, 'model_vertices'):
                vertices = np.array(self.model_vertices).reshape(-1, 3)
                center = np.mean(vertices, axis=0)
                return {
                    'position': center,
                    'rotation': np.array([0.0, 0.0, 0.0])
                }
        elif self.selected_object == 'wind_plate':
            return {
                'position': self.wind_plate['position'].copy(),
                'rotation': self.wind_plate['rotation'].copy()
            }
        return None

    def update_object_position(self, movement):
        """Update the position of the selected object"""
        if self.selected_object == 'wind_plate':
            self.wind_plate['position'] += movement
            # Update UI controls
            if hasattr(self.parent(), 'wind_pos_x'):
                self.parent().wind_pos_x.setValue(self.wind_plate['position'][0])
                self.parent().wind_pos_y.setValue(self.wind_plate['position'][1])
                self.parent().wind_pos_z.setValue(self.wind_plate['position'][2])

    def draw_transform_gizmos(self):
        """Draw transform gizmos for the selected object"""
        if not self.selected_object:
            return
            
        try:
            glPushMatrix()
            
            # Get object position
            pos = self.get_object_position()
            if pos is None:
                return
                
            glTranslatef(pos[0], pos[1], pos[2])
            
            # Draw transform axes
            glDisable(GL_LIGHTING)
            glLineWidth(2.0)
            
            axis_length = 2.0
            
            # X axis (red)
            glBegin(GL_LINES)
            glColor3f(1, 0, 0)
            glVertex3f(0, 0, 0)
            glVertex3f(axis_length, 0, 0)
            # Arrow head
            glVertex3f(axis_length, 0, 0)
            glVertex3f(axis_length - 0.2, 0.1, 0)
            glVertex3f(axis_length, 0, 0)
            glVertex3f(axis_length - 0.2, -0.1, 0)
            glEnd()
            
            # Y axis (green)
            glBegin(GL_LINES)
            glColor3f(0, 1, 0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, axis_length, 0)
            # Arrow head
            glVertex3f(0, axis_length, 0)
            glVertex3f(0.1, axis_length - 0.2, 0)
            glVertex3f(0, axis_length, 0)
            glVertex3f(-0.1, axis_length - 0.2, 0)
            glEnd()
            
            # Z axis (blue)
            glBegin(GL_LINES)
            glColor3f(0, 0, 1)
            glVertex3f(0, 0, 0)
            glVertex3f(0, 0, axis_length)
            # Arrow head
            glVertex3f(0, 0, axis_length)
            glVertex3f(0.1, 0, axis_length - 0.2)
            glVertex3f(0, 0, axis_length)
            glVertex3f(-0.1, 0, axis_length - 0.2)
            glEnd()
            
            # Highlight selected axis
            if self.selected_axis:
                glLineWidth(3.0)
                if self.selected_axis == 'x':
                    glColor3f(1, 0.5, 0.5)
                    glBegin(GL_LINES)
                    glVertex3f(0, 0, 0)
                    glVertex3f(axis_length, 0, 0)
                    glEnd()
                elif self.selected_axis == 'y':
                    glColor3f(0.5, 1, 0.5)
                    glBegin(GL_LINES)
                    glVertex3f(0, 0, 0)
                    glVertex3f(0, axis_length, 0)
                    glEnd()
                else:  # z
                    glColor3f(0.5, 0.5, 1)
                    glBegin(GL_LINES)
                    glVertex3f(0, 0, 0)
                    glVertex3f(0, 0, axis_length)
                    glEnd()
            
            glEnable(GL_LIGHTING)
            glPopMatrix()
            
        except Exception as e:
            print(f"Error drawing transform gizmos: {str(e)}")

    def wheelEvent(self, event):
        # Smoother zoom with smaller steps
        zoom_factor = event.angleDelta().y() / 240.0  # Reduced from 120 to make zooming smoother
        new_zoom = self.zoom * (1 - zoom_factor)
        
        # Add minimum and maximum zoom constraints
        self.zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        self.update()
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(('.obj', '.fbx')):
                    event.accept()
                    return
        elif event.mimeData().hasText() and event.mimeData().text() == "wind_source":
            event.accept()
            return
        event.ignore()
            
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.obj', '.fbx')):
                    self.load_model(file_path)
                    break
        elif event.mimeData().hasText() and event.mimeData().text() == "wind_source":
            # Convert drop position to 3D space
            pos = event.pos()
            self.create_wind_source_at_position(pos)
                
    def cleanup(self):
        """Clean up OpenGL resources"""
        self.logger.debug("Cleaning up OpenGL resources...")
        try:
            if self.vbo_vertices is not None:
                self.logger.debug(f"Deleting vertex buffer: {self.vbo_vertices}")
                glDeleteBuffers(1, [self.vbo_vertices])
                self.vbo_vertices = None
                
            if self.vbo_normals is not None:
                self.logger.debug(f"Deleting normal buffer: {self.vbo_normals}")
                glDeleteBuffers(1, [self.vbo_normals])
                self.vbo_normals = None
                
            self.vertex_count = 0
            self.model_loaded = False
            self.logger.debug("Cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def save_state(self):
        try:
            state = {
                'last_model_path': self.current_model_path if hasattr(self, 'current_model_path') else None,
                # Add other state data as needed
            }
            
            with open(os.path.join(self.parent().project_path, 'editor_state.json'), 'w') as f:
                json.dump(state, f, indent=4)
                
        except Exception as e:
            print(f"Warning: Failed to save editor state: {str(e)}")

    def load_saved_state(self):
        try:
            state_file = os.path.join(self.parent().project_path, 'editor_state.json')
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                # Load the last model if path exists
                last_model = state.get('last_model_path')
                if last_model and os.path.exists(last_model):
                    self.load_model(last_model)
                    
        except Exception as e:
            print(f"Warning: Failed to load editor state: {str(e)}")

    def load_model(self, file_path):
        """Load a 3D model file."""
        try:
            # Clean up existing resources
            self.cleanup()
            
            if file_path.lower().endswith('.obj'):
                self.load_obj(file_path)
                self.current_model_path = file_path
            elif file_path.lower().endswith('.fbx'):
                QMessageBox.warning(self, "Warning", "FBX support coming soon!")
                return
                
            self.model_loaded = True
            if isinstance(self.parent(), EditorWindow):
                self.parent().update_scene_hierarchy(os.path.basename(file_path))
                self.parent().update_properties_panel(os.path.basename(file_path))
                self.parent().calculate_model_properties()
            
            self.update()
            QMessageBox.information(self, "Success", f"Model loaded: {os.path.basename(file_path)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model: {str(e)}")
            print(f"Error loading model: {str(e)}")
            self.current_model_path = None

    def load_obj(self, file_path):
        """Load an OBJ file."""
        self.logger.info(f"Loading OBJ file: {file_path}")
        
        try:
            vertices = []
            normals = []
            faces = []
            temp_vertices = []
            temp_normals = []
            
            # Read file
            self.logger.debug("Reading OBJ file...")
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
                        verts = []
                        norms = []
                        for v in values[1:]:
                            w = v.split('/')
                            # OBJ indices start at 1
                            verts.append(int(w[0]) - 1)
                            # Check if normal index exists
                            if len(w) > 2 and w[2]:
                                norms.append(int(w[2]) - 1)
                        faces.append((verts, norms))

            # Process faces into triangles
            vertices_list = []
            normals_list = []
            
            for face_verts, face_norms in faces:
                # Triangulate face
                for i in range(1, len(face_verts) - 1):
                    # Add vertices for triangle
                    for idx in [0, i, i + 1]:
                        vertices_list.append(temp_vertices[face_verts[idx]])
                        if face_norms and len(face_norms) > idx:
                            normals_list.append(temp_normals[face_norms[idx]])
                        else:
                            # Calculate face normal if not provided
                            v1 = np.array(temp_vertices[face_verts[0]])
                            v2 = np.array(temp_vertices[face_verts[i]])
                            v3 = np.array(temp_vertices[face_verts[i + 1]])
                            normal = np.cross(v2 - v1, v3 - v1)
                            normal = normal / np.linalg.norm(normal) if np.linalg.norm(normal) > 0 else np.array([0.0, 1.0, 0.0])
                            normals_list.append(normal)

            # Create buffers
            if not self.create_buffers():
                raise RuntimeError("Failed to create OpenGL buffers")

            # Convert to numpy arrays
            vertices_array = np.array(vertices_list, dtype=np.float32)
            normals_array = np.array(normals_list, dtype=np.float32)

            # Center and scale the model
            center = (vertices_array.max(axis=0) + vertices_array.min(axis=0)) / 2
            max_size = np.max(vertices_array.max(axis=0) - vertices_array.min(axis=0))
            scale = 5.0 / max_size if max_size > 0 else 1.0
            
            vertices_array = (vertices_array - center) * scale
            
            # Make arrays contiguous
            vertices_array = np.ascontiguousarray(vertices_array, dtype=np.float32)
            normals_array = np.ascontiguousarray(normals_array, dtype=np.float32)

            # Store the vertex data for later use
            self.model_vertices = vertices_array
            self.model_normals = normals_array
            
            # Upload vertex data
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices.value)
            glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
            
            # Upload normal data
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals.value)
            glBufferData(GL_ARRAY_BUFFER, normals_array.nbytes, normals_array, GL_STATIC_DRAW)
            
            # Unbind buffer
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            
            # Update vertex count and model state
            self.vertex_count = len(vertices_array)
            self.model_loaded = True
            self.current_model_path = file_path
            
            self.logger.info(f"Successfully loaded model with {self.vertex_count} vertices")
            self.update()
            
        except Exception as e:
            self.logger.error(f"Error loading OBJ file: {str(e)}")
            self.cleanup()
            raise

    def cleanup_gl_resources(self):
        try:
            # Make sure we have the OpenGL context
            self.makeCurrent()
            
            if hasattr(self, 'model_loader'):
                self.model_loader.cleanup_existing_buffers()
            
        except Exception as e:
            print(f"Warning: Error during cleanup: {str(e)}")
        finally:
            self.doneCurrent()

    def update_pressure_visualization(self, pressure_distribution: Dict[int, float]):
        """Update the model visualization with pressure data"""
        try:
            if not self.model_loaded:
                return

            # Create color array based on pressure coefficients
            colors = np.zeros((len(self.model_vertices), 3), dtype=np.float32)

            # Find min and max pressure for better color mapping
            min_cp = min(pressure_distribution.values())
            max_cp = max(pressure_distribution.values())
            cp_range = max_cp - min_cp if max_cp != min_cp else 1.0

            # Map pressure coefficients to colors using a better color scheme
            for vertex_id, cp in pressure_distribution.items():
                # Normalize cp value to 0-1 range
                normalized_cp = (cp - min_cp) / cp_range
                
                # Create a smooth transition from blue (low pressure) to red (high pressure)
                if normalized_cp < 0.5:
                    # Blue to white
                    t = normalized_cp * 2
                    colors[vertex_id] = [t, t, 1.0]
                else:
                    # White to red
                    t = (normalized_cp - 0.5) * 2
                    colors[vertex_id] = [1.0, 1.0 - t, 1.0 - t]

            # Create and bind color buffer
            if not hasattr(self, 'vbo_colors'):
                self.vbo_colors = GLuint(0)
                glGenBuffers(1, self.vbo_colors)

            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_colors.value)
            glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)

            # Store pressure data for streamline calculation
            self.pressure_data = pressure_distribution
            self.colors = colors

            self.update()

        except Exception as e:
            print(f"Error updating pressure visualization: {str(e)}")

    def draw_streamlines(self):
        """Draw flow streamlines around the model"""
        if not hasattr(self, 'pressure_data') or not self.model_loaded:
            return

        try:
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            glLineWidth(1.5)
            glBegin(GL_LINES)

            # Create streamlines starting points
            num_streamlines = 50
            start_points = self.generate_streamline_points(num_streamlines)

            # Draw each streamline
            for start_point in start_points:
                points = self.calculate_streamline(start_point)
                
                # Draw streamline segments with varying color and alpha
                for i in range(len(points) - 1):
                    alpha = 1.0 - (i / len(points))  # Fade out along the streamline
                    glColor4f(0.5, 0.8, 1.0, alpha * 0.6)  # Light blue with alpha
                    glVertex3f(*points[i])
                    glVertex3f(*points[i + 1])

            glEnd()
            glDisable(GL_BLEND)
            glEnable(GL_LIGHTING)

        except Exception as e:
            print(f"Error drawing streamlines: {str(e)}")

    def generate_streamline_points(self, num_points: int) -> list:
        """Generate starting points for streamlines"""
        points = []
        
        # Get model bounds
        vertices = np.array(self.model_vertices).reshape(-1, 3)
        min_bounds = np.min(vertices, axis=0)
        max_bounds = np.max(vertices, axis=0)
        
        # Generate points in a grid around the model
        margin = 2.0  # Distance from model
        for i in range(num_points):
            x = np.random.uniform(min_bounds[0] - margin, max_bounds[0] + margin)
            y = np.random.uniform(min_bounds[1] - margin, max_bounds[1] + margin)
            z = np.random.uniform(min_bounds[2] - margin, max_bounds[2] + margin)
            points.append(np.array([x, y, z]))
        
        return points

    def calculate_streamline(self, start_point: np.ndarray) -> list:
        """Calculate streamline path from starting point"""
        points = [start_point]
        max_steps = 50
        step_size = 0.1
        
        for _ in range(max_steps):
            current_point = points[-1]
            velocity = self.calculate_velocity_at_point(current_point)
            
            if np.all(velocity == 0):
                break
            
            # Normalize velocity and scale by step size
            velocity = velocity / np.linalg.norm(velocity) * step_size
            next_point = current_point + velocity
            points.append(next_point)
        
        return points

    def calculate_velocity_at_point(self, point: np.ndarray) -> np.ndarray:
        """Calculate velocity vector at a given point"""
        # Simple velocity field calculation based on pressure gradient
        velocity = np.zeros(3)
        
        # Find nearest vertices and interpolate velocity
        vertices = np.array(self.model_vertices).reshape(-1, 3)
        distances = np.linalg.norm(vertices - point, axis=1)
        nearest_indices = np.argsort(distances)[:4]  # Use 4 nearest points
        
        for idx in nearest_indices:
            if idx in self.pressure_data:
                pressure = self.pressure_data[idx]
                direction = vertices[idx] - point
                direction = direction / np.linalg.norm(direction)
                velocity += direction * pressure
        
        return velocity

    def create_wind_plate(self):
        """Create a wind source plate in the viewport"""
        try:
            # Get values directly from the spinboxes
            width = self.wind_size_x.value()
            height = self.wind_size_y.value()
            
            # Create the wind plate in the viewport
            self.viewport.create_simple_wind_plate(width, height)
            
            # Update transform UI
            self.update_wind_transform()
            
            self.statusBar().showMessage("Wind source plate created")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create wind plate: {str(e)}")

    def draw_wind_plate(self):
        """Draw the wind source plate"""
        if not hasattr(self, 'wind_plate'):
            return
        
        try:
            glPushMatrix()
            
            # Apply transformations
            pos = self.wind_plate['position']
            rot = self.wind_plate['rotation']
            glTranslatef(pos[0], pos[1], pos[2])
            
            # Apply rotations in order (X, Y, Z)
            glRotatef(rot['x'], 1, 0, 0)
            glRotatef(rot['y'], 0, 1, 0)
            glRotatef(rot['z'], 0, 0, 1)
            
            # Draw semi-transparent plate
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            glDisable(GL_LIGHTING)
            glColor4f(0.2, 0.6, 1.0, 0.3)  # Light blue, semi-transparent
            
            # Draw plate
            glBegin(GL_TRIANGLES)
            for i in self.wind_plate['indices']:
                glVertex3fv(self.wind_plate['vertices'][i])
            glEnd()
            
            # Draw outline
            glColor4f(0.2, 0.6, 1.0, 0.8)  # More opaque for outline
            glBegin(GL_LINE_LOOP)
            for i in range(4):
                glVertex3fv(self.wind_plate['vertices'][i])
            glEnd()
            
            # Draw wind direction arrows
            self.draw_wind_arrows()
            
            glEnable(GL_LIGHTING)
            glDisable(GL_BLEND)
            
            glPopMatrix()
            
        except Exception as e:
            print(f"Error drawing wind plate: {str(e)}")

    def draw_wind_arrows(self):
        """Draw arrows showing wind direction"""
        arrow_count = 5
        arrow_length = 1.0
        
        glColor4f(0.2, 0.6, 1.0, 0.8)
        glBegin(GL_LINES)
        
        width = self.wind_plate['size'][0]
        height = self.wind_plate['size'][1]
        
        for i in range(arrow_count):
            for j in range(arrow_count):
                # Calculate start position
                x = (i / (arrow_count - 1) - 0.5) * width
                y = (j / (arrow_count - 1) - 0.5) * height
                
                # Draw arrow body
                glVertex3f(x, y, 0)
                glVertex3f(x, y, arrow_length)
                
                # Draw arrow head
                glVertex3f(x, y, arrow_length)
                glVertex3f(x - 0.1, y, arrow_length - 0.2)
                glVertex3f(x, y, arrow_length)
                glVertex3f(x + 0.1, y, arrow_length - 0.2)
                
        glEnd()

    def create_simple_wind_plate(self, width, height):
        """Create a simple wind plate"""
        try:
            # Create plate vertices
            vertices = np.array([
                [-width/2, -height/2, -5.0],  # Start 5 units in front
                [width/2, -height/2, -5.0],
                [width/2, height/2, -5.0],
                [-width/2, height/2, -5.0]
            ], dtype=np.float32)
            
            # Create plate indices
            indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)
            
            # Store the wind plate data
            self.wind_plate = {
                'vertices': vertices,
                'indices': indices,
                'size': np.array([width, height]),
                'position': np.array([0.0, 0.0, -5.0]),  # Add position
                'rotation': {'x': 0.0, 'y': 0.0, 'z': 0.0}  # Add rotation
            }
            
            self.update()
            
        except Exception as e:
            print(f"Error creating wind plate: {str(e)}")

    def update_wind_transform(self):
        """Update wind plate transform based on UI controls"""
        if not hasattr(self, 'wind_plate'):
            return
        
        try:
            # Update position
            self.wind_plate['position'] = np.array([
                self.wind_pos_x.value(),
                self.wind_pos_y.value(),
                self.wind_pos_z.value()
            ])
            
            # Update rotation
            self.wind_plate['rotation'] = {
                'x': self.wind_rot_x.value(),
                'y': self.wind_rot_y.value(),
                'z': self.wind_rot_z.value()
            }
            
            self.update()
            
        except Exception as e:
            print(f"Error updating wind transform: {str(e)}")

    def calculate_model_properties(self):
        """Calculate model properties from vertices"""
        if not hasattr(self, 'model_vertices') or len(self.model_vertices) == 0:
            return
        
        try:
            vertices = np.array(self.model_vertices).reshape(-1, 3)
            
            # Calculate volume (approximate using bounding box)
            min_bounds = np.min(vertices, axis=0)
            max_bounds = np.max(vertices, axis=0)
            dimensions = max_bounds - min_bounds
            volume = np.prod(dimensions)
            
            # Calculate surface area (approximate using triangles)
            surface_area = 0
            for i in range(0, len(vertices), 3):
                if i + 2 < len(vertices):
                    v1, v2, v3 = vertices[i:i+3]
                    # Calculate triangle area
                    area = np.linalg.norm(np.cross(v2-v1, v3-v1)) / 2
                    surface_area += area
            
            # Update labels
            self.volume_label.setText(f"{volume:.3f} m³")
            self.surface_area_label.setText(f"{surface_area:.3f} m²")
            
            # Calculate mass based on density and volume
            mass = volume * self.density_input.value()
            self.mass_input.setValue(mass)
            
        except Exception as e:
            print(f"Error calculating model properties: {str(e)}")

    def draw_wind_plate_gizmos(self):
        """Draw transform gizmos for the wind plate"""
        if not hasattr(self, 'wind_plate'):
            return
        
        try:
            glPushMatrix()
            
            # Apply wind plate transform
            pos = self.wind_plate['position']
            rot = self.wind_plate['rotation']
            glTranslatef(pos[0], pos[1], pos[2])
            glRotatef(rot['x'], 1, 0, 0)
            glRotatef(rot['y'], 0, 1, 0)
            glRotatef(rot['z'], 0, 0, 1)
            
            # Draw transform axes
            glDisable(GL_LIGHTING)
            glLineWidth(2.0)
            
            axis_length = 2.0
            
            # X axis (red)
            glBegin(GL_LINES)
            glColor3f(1, 0, 0)
            glVertex3f(0, 0, 0)
            glVertex3f(axis_length, 0, 0)
            # Arrow head
            glVertex3f(axis_length, 0, 0)
            glVertex3f(axis_length - 0.2, 0.1, 0)
            glVertex3f(axis_length, 0, 0)
            glVertex3f(axis_length - 0.2, -0.1, 0)
            glEnd()
            
            # Y axis (green)
            glBegin(GL_LINES)
            glColor3f(0, 1, 0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, axis_length, 0)
            # Arrow head
            glVertex3f(0, axis_length, 0)
            glVertex3f(0.1, axis_length - 0.2, 0)
            glVertex3f(0, axis_length, 0)
            glVertex3f(-0.1, axis_length - 0.2, 0)
            glEnd()
            
            # Z axis (blue)
            glBegin(GL_LINES)
            glColor3f(0, 0, 1)
            glVertex3f(0, 0, 0)
            glVertex3f(0, 0, axis_length)
            # Arrow head
            glVertex3f(0, 0, axis_length)
            glVertex3f(0.1, 0, axis_length - 0.2)
            glVertex3f(0, 0, axis_length)
            glVertex3f(-0.1, 0, axis_length - 0.2)
            glEnd()
            
            glEnable(GL_LIGHTING)
            glPopMatrix()
            
        except Exception as e:
            print(f"Error drawing wind plate gizmos: {str(e)}")

    def get_clicked_axis(self, mouse_pos):
        """Determine which transform axis was clicked"""
        # Convert mouse position to ray
        ray_start, ray_dir = self.get_ray_from_mouse(mouse_pos)
        
        if not hasattr(self, 'wind_plate'):
            return None
        
        # Get wind plate position
        pos = self.wind_plate['position']
        
        # Check distance to each axis
        axes = {
            'x': (np.array([1, 0, 0]), (1, 0, 0)),
            'y': (np.array([0, 1, 0]), (0, 1, 0)),
            'z': (np.array([0, 0, 1]), (0, 0, 1))
        }
        
        closest_axis = None
        min_distance = 0.1  # Threshold for selection
        
        for axis_name, (axis_dir, color) in axes.items():
            distance = self.point_line_distance(
                ray_start, ray_dir,
                pos,
                pos + axis_dir * 2.0
            )
            if distance < min_distance:
                min_distance = distance
                closest_axis = axis_name
            
        return closest_axis

    def get_ray_from_mouse(self, mouse_pos):
        """Convert mouse position to 3D ray"""
        viewport = glGetIntegerv(GL_VIEWPORT)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        
        mouse_x = mouse_pos.x()
        mouse_y = viewport[3] - mouse_pos.y()
        
        near = gluUnProject(mouse_x, mouse_y, 0.0, modelview, projection, viewport)
        far = gluUnProject(mouse_x, mouse_y, 1.0, modelview, projection, viewport)
        
        ray_start = np.array(near)
        ray_dir = np.array(far) - ray_start
        ray_dir = ray_dir / np.linalg.norm(ray_dir)
        
        return ray_start, ray_dir

    def point_line_distance(self, ray_start, ray_dir, line_start, line_end):
        """Calculate distance from a point to a line segment"""
        line_dir = line_end - line_start
        line_length = np.linalg.norm(line_dir)
        line_dir = line_dir / line_length
        
        cross = np.cross(ray_dir, line_dir)
        return np.abs(np.dot(cross, (line_start - ray_start)))

    def reset_view(self):
        """Reset camera to default position"""
        self.rotation = [30, 45, 0]
        self.zoom = 15.0
        self.pan_offset = [0.0, 0.0]
        self.update()

class EditorWindow(QMainWindow):
    def __init__(self, project_path):
        super().__init__()
        self.project_path = project_path
        self.settings = QSettings('AeroCalculator', 'Editor')
        self.dock_widgets = {}  # Store references to dock widgets
        
        # Set minimum sizes for the window and dock widgets
        self.setMinimumSize(1200, 800)
        
        # Create UI first
        self.initUI()
        # Then setup physics panel
        self.setup_physics_panel()
        # Finally load settings
        self.loadSettings()
        
        # Ensure dock widgets have reasonable minimum sizes
        for dock in self.dock_widgets.values():
            dock.setMinimumWidth(250)
            dock.setMinimumHeight(300)

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

        # Reset view button
        self.reset_view_btn = QToolButton()
        self.reset_view_btn.setText("Reset View")
        self.reset_view_btn.setToolTip("Reset Camera View")
        self.reset_view_btn.clicked.connect(lambda: self.viewport.reset_view())
        toolbar.addWidget(self.reset_view_btn)

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
        
        # Add transform mode button to toolbar
        self.transform_mode_btn = QToolButton()
        self.transform_mode_btn.setText("Transform")
        self.transform_mode_btn.setToolTip("Toggle Transform Mode")
        self.transform_mode_btn.setCheckable(True)
        self.transform_mode_btn.setChecked(False)
        self.transform_mode_btn.toggled.connect(self.toggle_transform_mode)
        toolbar.addWidget(self.transform_mode_btn)

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
        """Save application settings"""
        try:
            # Save window state and geometry
            self.settings.setValue('geometry', self.saveGeometry())
            self.settings.setValue('windowState', self.saveState())
            
            # Save physics panel values
            if hasattr(self, 'density_input'):
                self.settings.setValue('density', self.density_input.findChild(QDoubleSpinBox).value())
            if hasattr(self, 'velocity_input'):
                self.settings.setValue('velocity', self.velocity_input.findChild(QDoubleSpinBox).value())
            if hasattr(self, 'temperature_input'):
                self.settings.setValue('temperature', self.temperature_input.findChild(QDoubleSpinBox).value())
            if hasattr(self, 'aoa_input'):
                self.settings.setValue('aoa', self.aoa_input.findChild(QDoubleSpinBox).value())
            
            # Save wind plate settings if it exists
            if hasattr(self, 'wind_size_x'):
                self.settings.setValue('wind_size_x', self.wind_size_x.value())
                self.settings.setValue('wind_size_y', self.wind_size_y.value())
                self.settings.setValue('wind_pos_x', self.wind_pos_x.value())
                self.settings.setValue('wind_pos_y', self.wind_pos_y.value())
                self.settings.setValue('wind_pos_z', self.wind_pos_z.value())
                self.settings.setValue('wind_rot_x', self.wind_rot_x.value())
                self.settings.setValue('wind_rot_y', self.wind_rot_y.value())
                self.settings.setValue('wind_rot_z', self.wind_rot_z.value())
            
            # Save physics panel visibility and position
            if 'physics' in self.dock_widgets:
                physics_dock = self.dock_widgets['physics']
                self.settings.setValue('physicsPanelVisible', physics_dock.isVisible())
                self.settings.setValue('physicsPanelFloating', physics_dock.isFloating())
                if physics_dock.isFloating():
                    self.settings.setValue('physicsPanelPos', physics_dock.pos())
            
        except Exception as e:
            print(f"Error saving settings: {str(e)}")

    def loadSettings(self):
        """Load application settings"""
        try:
            # Restore window state and geometry
            if self.settings.value('geometry'):
                self.restoreGeometry(self.settings.value('geometry'))
            if self.settings.value('windowState'):
                self.restoreState(self.settings.value('windowState'))
            
            # Restore physics panel values
            if hasattr(self, 'density_input') and self.settings.contains('density'):
                self.density_input.findChild(QDoubleSpinBox).setValue(float(self.settings.value('density')))
            if hasattr(self, 'velocity_input') and self.settings.contains('velocity'):
                self.velocity_input.findChild(QDoubleSpinBox).setValue(float(self.settings.value('velocity')))
            if hasattr(self, 'temperature_input') and self.settings.contains('temperature'):
                self.temperature_input.findChild(QDoubleSpinBox).setValue(float(self.settings.value('temperature')))
            if hasattr(self, 'aoa_input') and self.settings.contains('aoa'):
                self.aoa_input.findChild(QDoubleSpinBox).setValue(float(self.settings.value('aoa')))
            
            # Restore wind plate settings
            if hasattr(self, 'wind_size_x') and self.settings.contains('wind_size_x'):
                self.wind_size_x.setValue(float(self.settings.value('wind_size_x')))
                self.wind_size_y.setValue(float(self.settings.value('wind_size_y')))
                self.wind_pos_x.setValue(float(self.settings.value('wind_pos_x')))
                self.wind_pos_y.setValue(float(self.settings.value('wind_pos_y')))
                self.wind_pos_z.setValue(float(self.settings.value('wind_pos_z')))
                self.wind_rot_x.setValue(float(self.settings.value('wind_rot_x')))
                self.wind_rot_y.setValue(float(self.settings.value('wind_rot_y')))
                self.wind_rot_z.setValue(float(self.settings.value('wind_rot_z')))
                
                # Recreate wind plate with saved settings
                self.create_wind_plate()
            
            # Restore physics panel visibility and position
            if 'physics' in self.dock_widgets:
                physics_dock = self.dock_widgets['physics']
                if self.settings.contains('physicsPanelVisible'):
                    physics_dock.setVisible(self.settings.value('physicsPanelVisible', True, type=bool))
                if self.settings.contains('physicsPanelFloating'):
                    physics_dock.setFloating(self.settings.value('physicsPanelFloating', False, type=bool))
                if physics_dock.isFloating() and self.settings.contains('physicsPanelPos'):
                    physics_dock.move(self.settings.value('physicsPanelPos'))
            
        except Exception as e:
            print(f"Error loading settings: {str(e)}")

    def closeEvent(self, event):
        try:
            # Save settings and state before closing
            self.saveSettings()
            
            # Save viewport state if model is loaded
            if hasattr(self.viewport, 'current_model_path'):
                state = {
                    'last_model_path': self.viewport.current_model_path,
                    # Add other state data as needed
                }
                
                with open(os.path.join(self.project_path, 'editor_state.json'), 'w') as f:
                    json.dump(state, f, indent=4)
            
            # Cleanup OpenGL resources
            self.viewport.cleanup_gl_resources()
            
        except Exception as e:
            print(f"Warning: Error during editor shutdown: {str(e)}")
        finally:
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

    def setup_physics_panel(self):
        """Create physics control panel"""
        physics_dock = QDockWidget("Physics Controls", self)
        physics_dock.setObjectName("physicsPanel")
        physics_dock.setMinimumWidth(300)  # Set minimum width
        
        # Create a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
            }
        """)
        
        # Create the main widget that will be scrollable
        physics_widget = QWidget()
        layout = QVBoxLayout(physics_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Flow Properties Group
        flow_group = QGroupBox("Flow Properties")
        flow_layout = QVBoxLayout()
        self.density_input = self.create_parameter_input("Air Density (kg/m³):", 1.225)
        self.velocity_input = self.create_parameter_input("Velocity (m/s):", 100.0)
        self.temperature_input = self.create_parameter_input("Temperature (°C):", 20.0)
        self.aoa_input = self.create_parameter_input("Angle of Attack (°):", 0.0)
        flow_layout.addWidget(self.density_input)
        flow_layout.addWidget(self.velocity_input)
        flow_layout.addWidget(self.temperature_input)
        flow_layout.addWidget(self.aoa_input)
        flow_group.setLayout(flow_layout)
        
        # Wind Source Group
        wind_group = QGroupBox("Wind Source")
        wind_layout = QVBoxLayout()
        
        # Create wind plate button
        create_wind_btn = QPushButton("Create Wind Plate")
        create_wind_btn.clicked.connect(self.create_wind_plate)
        
        # Size controls
        size_group = QGroupBox("Size")
        size_layout = QFormLayout()
        self.wind_size_x = QDoubleSpinBox()
        self.wind_size_x.setRange(0.1, 100)
        self.wind_size_x.setValue(5.0)
        self.wind_size_x.setSuffix(" m")
        self.wind_size_y = QDoubleSpinBox()
        self.wind_size_y.setRange(0.1, 100)
        self.wind_size_y.setValue(5.0)
        self.wind_size_y.setSuffix(" m")
        size_layout.addRow("Width:", self.wind_size_x)
        size_layout.addRow("Height:", self.wind_size_y)
        size_group.setLayout(size_layout)

        # Transform controls
        transform_group = QGroupBox("Transform")
        transform_layout = QFormLayout()
        
        # Position controls
        self.wind_pos_x = QDoubleSpinBox()
        self.wind_pos_x.setRange(-100, 100)
        self.wind_pos_x.setValue(0.0)
        self.wind_pos_x.setSuffix(" m")
        self.wind_pos_x.valueChanged.connect(self.update_wind_transform)
        
        self.wind_pos_y = QDoubleSpinBox()
        self.wind_pos_y.setRange(-100, 100)
        self.wind_pos_y.setValue(0.0)
        self.wind_pos_y.setSuffix(" m")
        self.wind_pos_y.valueChanged.connect(self.update_wind_transform)
        
        self.wind_pos_z = QDoubleSpinBox()
        self.wind_pos_z.setRange(-100, 100)
        self.wind_pos_z.setValue(-5.0)
        self.wind_pos_z.setSuffix(" m")
        self.wind_pos_z.valueChanged.connect(self.update_wind_transform)
        
        # Rotation controls
        self.wind_rot_x = QDoubleSpinBox()
        self.wind_rot_x.setRange(-360, 360)
        self.wind_rot_x.setValue(0.0)
        self.wind_rot_x.setSuffix("°")
        self.wind_rot_x.valueChanged.connect(self.update_wind_transform)
        
        self.wind_rot_y = QDoubleSpinBox()
        self.wind_rot_y.setRange(-360, 360)
        self.wind_rot_y.setValue(0.0)
        self.wind_rot_y.setSuffix("°")
        self.wind_rot_y.valueChanged.connect(self.update_wind_transform)
        
        self.wind_rot_z = QDoubleSpinBox()
        self.wind_rot_z.setRange(-360, 360)
        self.wind_rot_z.setValue(0.0)
        self.wind_rot_z.setSuffix("°")
        self.wind_rot_z.valueChanged.connect(self.update_wind_transform)
        
        transform_layout.addRow("Position X:", self.wind_pos_x)
        transform_layout.addRow("Position Y:", self.wind_pos_y)
        transform_layout.addRow("Position Z:", self.wind_pos_z)
        transform_layout.addRow("Rotation X:", self.wind_rot_x)
        transform_layout.addRow("Rotation Y:", self.wind_rot_y)
        transform_layout.addRow("Rotation Z:", self.wind_rot_z)
        transform_group.setLayout(transform_layout)

        wind_layout.addWidget(create_wind_btn)
        wind_layout.addWidget(size_group)
        wind_layout.addWidget(transform_group)
        wind_group.setLayout(wind_layout)

        # Calculate button and results
        self.calc_button = QPushButton("Calculate Forces")
        self.calc_button.clicked.connect(self.calculate_aerodynamics)
        
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        self.lift_label = QLabel("Lift: -- N")
        self.drag_label = QLabel("Drag: -- N")
        self.moment_label = QLabel("Moment: -- N·m")
        self.cp_label = QLabel("Pressure Coefficient: --")
        
        results_layout.addWidget(self.lift_label)
        results_layout.addWidget(self.drag_label)
        results_layout.addWidget(self.moment_label)
        results_layout.addWidget(self.cp_label)
        results_group.setLayout(results_layout)
        
        layout.addWidget(flow_group)
        layout.addWidget(wind_group)
        layout.addWidget(self.calc_button)
        layout.addWidget(results_group)
        layout.addStretch()
        
        # Set minimum sizes for input widgets
        for widget in physics_widget.findChildren(QDoubleSpinBox):
            widget.setMinimumWidth(100)
        
        for widget in physics_widget.findChildren(QGroupBox):
            widget.setMinimumWidth(280)
            
        scroll.setWidget(physics_widget)
        physics_dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, physics_dock)
        self.dock_widgets["physics"] = physics_dock

    def create_parameter_input(self, label: str, default_value: float) -> QWidget:
        """Create a labeled parameter input widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        label_widget = QLabel(label)
        spinbox = QDoubleSpinBox()
        spinbox.setRange(-1000, 1000)
        spinbox.setValue(default_value)
        spinbox.setDecimals(3)
        
        layout.addWidget(label_widget)
        layout.addWidget(spinbox)
        widget.setLayout(layout)
        return widget

    def calculate_aerodynamics(self):
        """Calculate aerodynamic forces and update display"""
        try:
            if not hasattr(self.viewport, 'model_vertices'):
                QMessageBox.warning(self, "Warning", "Please load a model first")
                return

            # Get current flow conditions
            conditions = FlowConditions(
                density=self.density_input.findChild(QDoubleSpinBox).value(),
                velocity=self.velocity_input.findChild(QDoubleSpinBox).value(),
                temperature=self.temperature_input.findChild(QDoubleSpinBox).value(),
                viscosity=1.81e-5,  # Standard air viscosity at 20°C
                angle_of_attack=self.aoa_input.findChild(QDoubleSpinBox).value()
            )

            # Calculate forces
            forces = self.calculate_forces(conditions)

            # Update display
            self.lift_label.setText(f"Lift: {forces.lift:.2f} N")
            self.drag_label.setText(f"Drag: {forces.drag:.2f} N")
            self.moment_label.setText(f"Moment: {forces.moment:.2f} N·m")
            self.cp_label.setText(f"Pressure Coefficient: {forces.cp:.3f}")

            # Update visualization
            self.viewport.update_pressure_visualization(forces.pressure_distribution)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Calculation failed: {str(e)}")

    def calculate_forces(self, conditions: FlowConditions) -> AerodynamicForces:
        """Calculate aerodynamic forces"""
        try:
            if not self.viewport.model_loaded:
                raise RuntimeError("No model loaded")

            # Get vertices directly from the viewport's loaded model data
            vertices = np.array(self.viewport.model_vertices, dtype=np.float32).reshape(-1, 3)
            if len(vertices) == 0:
                raise RuntimeError("Model has no vertices")

            # Print debug info
            print(f"Number of vertices: {len(vertices)}")
            print(f"Vertex array shape: {vertices.shape}")
            
            # Calculate reference area (simplified - use bounding box)
            x_coords = vertices[:, 0]
            y_coords = vertices[:, 1]
            reference_area = abs((max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords)))
            print(f"Reference area: {reference_area}")

            # Calculate dynamic pressure
            q_inf = 0.5 * conditions.density * conditions.velocity ** 2

            # Simple force calculation based on angle of attack
            alpha = np.radians(conditions.angle_of_attack)

            # Basic lift and drag coefficients (simplified)
            cl = 2 * np.pi * alpha  # Simplified thin airfoil theory
            cd = 0.1 + 0.1 * alpha * alpha  # Simplified drag polar

            # Calculate forces
            lift = q_inf * reference_area * cl
            drag = q_inf * reference_area * cd
            moment = -0.25 * lift  # Simplified moment calculation

            # Generate simplified pressure distribution
            pressure_dist = {}
            for i in range(len(vertices)):
                # Simple pressure distribution based on height
                y_pos = vertices[i][1]  # Y coordinate
                cp = -2 * y_pos / reference_area
                pressure_dist[i] = cp

            return AerodynamicForces(
                lift=float(lift),
                drag=float(drag),
                moment=float(moment),
                pressure_distribution=pressure_dist,
                cp=float(cl)
            )

        except Exception as e:
            print(f"Debug - Calculation error: {str(e)}")
            print(f"Debug - Model loaded: {self.viewport.model_loaded}")
            if hasattr(self.viewport, 'model_vertices'):
                print(f"Debug - Vertices type: {type(self.viewport.model_vertices)}")
                print(f"Debug - Vertices length: {len(self.viewport.model_vertices)}")
            raise RuntimeError(f"Force calculation failed: {str(e)}")

    def create_wind_plate(self):
        """Create a wind source plate in the viewport"""
        try:
            # Get values directly from the spinboxes
            width = self.wind_size_x.value()
            height = self.wind_size_y.value()
            
            # Create the wind plate in the viewport
            self.viewport.create_simple_wind_plate(width, height)
            
            # Update transform UI
            self.update_wind_transform()
            
            self.statusBar().showMessage("Wind source plate created")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create wind plate: {str(e)}")

    def start_wind_source_drag(self, event):
        """Start dragging a wind source"""
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText("wind_source")
            drag.setMimeData(mime_data)
            
            # Create a pixmap for the drag icon
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor("#0078d4"))
            drag.setPixmap(pixmap)
            
            drag.exec()

    def update_properties_panel(self, model_name=None):
        """Update the properties panel with model information"""
        if "properties" not in self.dock_widgets:
            return
            
        properties_dock = self.dock_widgets["properties"]
        properties_dock.setMinimumWidth(250)  # Set minimum width
        
        # Create a scroll area for properties
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
            }
        """)
        
        properties_widget = QWidget()
        layout = QVBoxLayout(properties_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Model Properties Group
        model_group = QGroupBox("Model Properties")
        model_layout = QFormLayout()

        # Model name
        name_label = QLabel(model_name if model_name else "No Model Loaded")
        model_layout.addRow("Name:", name_label)

        # Physical properties with input fields
        self.mass_input = QDoubleSpinBox()
        self.mass_input.setRange(0.001, 10000)
        self.mass_input.setValue(1.0)
        self.mass_input.setSuffix(" kg")
        model_layout.addRow("Mass:", self.mass_input)

        self.density_input = QDoubleSpinBox()
        self.density_input.setRange(1, 20000)
        self.density_input.setValue(2700)  # Default aluminum density
        self.density_input.setSuffix(" kg/m³")
        model_layout.addRow("Material Density:", self.density_input)

        # Material type dropdown
        self.material_type = QComboBox()
        self.material_type.addItems(["Aluminum", "Steel", "Plastic", "Custom"])
        self.material_type.currentTextChanged.connect(self.on_material_changed)
        model_layout.addRow("Material:", self.material_type)

        # Calculated properties
        self.volume_label = QLabel("0.0 m³")
        model_layout.addRow("Volume:", self.volume_label)

        self.surface_area_label = QLabel("0.0 m²")
        model_layout.addRow("Surface Area:", self.surface_area_label)

        # Additional properties
        self.roughness_input = QDoubleSpinBox()
        self.roughness_input.setRange(0, 1)
        self.roughness_input.setSingleStep(0.01)
        self.roughness_input.setValue(0.0)
        model_layout.addRow("Surface Roughness:", self.roughness_input)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # Add a stretch to push everything to the top
        layout.addStretch()

        # Set the scroll area widget
        scroll.setWidget(properties_widget)
        properties_dock.setWidget(scroll)

    def on_material_changed(self, material):
        """Handle material type changes"""
        densities = {
            "Aluminum": 2700,
            "Steel": 7850,
            "Plastic": 1200,
            "Custom": self.density_input.value()
        }
        if material in densities:
            self.density_input.setValue(densities[material])

    def update_wind_transform(self):
        """Update wind plate transform based on UI controls"""
        if not hasattr(self.viewport, 'wind_plate'):
            return
        
        try:
            # Update position
            self.viewport.wind_plate['position'] = np.array([
                self.wind_pos_x.value(),
                self.wind_pos_y.value(),
                self.wind_pos_z.value()
            ])
            
            # Update rotation
            self.viewport.wind_plate['rotation'] = {
                'x': self.wind_rot_x.value(),
                'y': self.wind_rot_y.value(),
                'z': self.wind_rot_z.value()
            }
            
            self.viewport.update()
            
        except Exception as e:
            print(f"Error updating wind transform: {str(e)}")

    def calculate_model_properties(self):
        """Calculate model properties from vertices"""
        if not hasattr(self.viewport, 'model_vertices') or len(self.viewport.model_vertices) == 0:
            return
        
        try:
            vertices = np.array(self.viewport.model_vertices).reshape(-1, 3)
            
            # Calculate volume (approximate using bounding box)
            min_bounds = np.min(vertices, axis=0)
            max_bounds = np.max(vertices, axis=0)
            dimensions = max_bounds - min_bounds
            volume = np.prod(dimensions)
            
            # Calculate surface area (approximate using triangles)
            surface_area = 0
            for i in range(0, len(vertices), 3):
                if i + 2 < len(vertices):
                    v1, v2, v3 = vertices[i:i+3]
                    # Calculate triangle area
                    area = np.linalg.norm(np.cross(v2-v1, v3-v1)) / 2
                    surface_area += area
            
            # Update labels
            self.volume_label.setText(f"{volume:.3f} m³")
            self.surface_area_label.setText(f"{surface_area:.3f} m²")
            
            # Calculate mass based on density and volume
            mass = volume * self.density_input.value()
            self.mass_input.setValue(mass)
            
        except Exception as e:
            print(f"Error calculating model properties: {str(e)}")

    def update_transform_ui(self):
        """Update transform UI controls with current wind plate transform"""
        if not hasattr(self.viewport, 'wind_plate'):
            return
        
        # Update position spinboxes
        pos = self.viewport.wind_plate['position']
        self.wind_pos_x.setValue(pos[0])
        self.wind_pos_y.setValue(pos[1])
        self.wind_pos_z.setValue(pos[2])
        
        # Update rotation spinboxes
        rot = self.viewport.wind_plate['rotation']
        self.wind_rot_x.setValue(rot['x'])
        self.wind_rot_y.setValue(rot['y'])
        self.wind_rot_z.setValue(rot['z']) 

    def toggle_transform_mode(self, checked):
        """Toggle transform mode for the viewport"""
        self.viewport.transform_mode = checked
        if not checked:
            self.viewport.selected_object = None
            self.viewport.selected_axis = None
        self.viewport.update()