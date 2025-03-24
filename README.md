# Aero Calculator

A modern desktop application for aerodynamic analysis of 3D models with real-time visualization and engineering calculations.

## Features

### Project Management
- Unity-style project manager interface
- Create, open, and manage multiple projects
- Recent projects tracking with last opened times
- Project file organization with `.aero` format

### 3D Visualization
- OpenGL-powered 3D viewport
- Drag and drop support for 3D models (OBJ/FBX)
- Configurable grid and axis visualization
- Camera presets (Front, Top, Side views)
- Customizable viewport settings

### Physics Engine
- Real-time aerodynamic calculations
- Configurable physics parameters:
  - Air density
  - Temperature
  - Velocity
  - Angle of attack
- Multiple turbulence model support
- Force calculation capabilities

### User Interface
- Modern dark theme
- Dockable and resizable panels
- Customizable workspace layout
- Session state persistence
- Intuitive controls and navigation

## Setup Instructions

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Project Structure
```
Aero-Calculator/
├── main.py              # Project manager and application entry
├── editor_window.py     # 3D editor and physics engine
├── requirements.txt     # Python dependencies
└── README.md           # Documentation
```

## Usage Guide

### Creating a New Project
1. Click "New Project" in the project manager
2. Enter project name and select location
3. Click "Create Project" to open the editor

### Working with Models
1. Open a project from the recent projects list
2. Drag and drop 3D models (OBJ/FBX) into the viewport
3. Use viewport controls to adjust view settings
4. Configure physics parameters in the physics panel

### Physics Calculations
1. Set environmental parameters (air density, temperature)
2. Configure flow properties (velocity, angle of attack)
3. Select appropriate turbulence model
4. Click "Calculate Forces" to run simulation

## Development Status

### Completed Features
- [x] Project management system
- [x] Basic 3D viewport with OpenGL
- [x] Dock widget system with state saving
- [x] Physics parameter interface
- [x] Grid and axis visualization
- [x] Modern UI with dark theme

### In Progress
- [ ] 3D model loading and rendering
- [ ] Physics calculations implementation
- [ ] Force visualization
- [ ] Camera control improvements
- [ ] Additional viewport features

## Contributing
Feel free to contribute to the project by submitting issues or pull requests.

## License
[MIT License](LICENSE)

