# Aerodynamics Simulation Tool Roadmap

## Project Overview
A desktop application for aerodynamic analysis of 3D models with real-time visualization and engineering data outputs.

## Core Components

language: Python
Project file: everything under 1 project

### 1. Project Management System
- **Project Wizard**: GUI for new project creation (geometry, simulation params)
- **Project Manager**: Load/save projects with `.aero` format
- **File I/O**: Support for OBJ/FBX via Assimp library

### 2. 3D Visualization Engine
- **Rendering Core**: OpenGL/GLFW implementation
- **Camera System**: Orbit/pan/zoom controls
- **Model Loading**: Assimp integration for mesh processing
- **Shaders**: GLSL for pressure/streamline visualization
- **Models**: Loading it by simply dragging the 3d model onto the 3d viewport

### 3. Physics Simulation Module
- **Simplified CFD**:
  - Panel method for potential flow
  - Vortex lattice method (VLM) for lift estimation
  - Boundary layer approximation
  - place to input specific paramiters
- **Environment System**:
  - Air density (ρ)
  - Velocity (v)
  - Gravity (g)
  - Turbulence models

### 4. Data Visualization System
- **Pressure Cloud**: Vertex coloring based on pressure values
- **Streamlines**: Particle tracing with Runge-Kutta integration
- **HUD Overlay**: Numerical readouts with IMGUI

### 5. Formula Documentation System
- LaTeX equation rendering
- Interactive formula explorer

---

## Key Formulas

### Aerodynamic Coefficients
1. **Drag Coefficient**  
   `C_d = 2F_d / (ρv²A)`  
   _Where F_d = drag force, A = reference area_

2. **Lift Coefficient**  
   `C_l = 2F_l / (ρv²A)`

3. **Pressure Coefficient**  
   `C_p = (p - p_∞)/(½ρv²)`  
   _Surface pressure visualization_

### Flow Properties
4. **Bernoulli's Principle**  
   `p + ½ρv² + ρgh = constant`

5. **Reynolds Number**  
   `Re = (ρvL)/μ`  
   _Flow regime determination_

### Force Calculations
6. **Drag Force**  
   `F_d = ½C_dρv²A`

7. **Lift Force**  
   `F_l = ½C_lρv²A`

### Geometric Calculations
8. **Frontal Area**  
   Projected area in flow direction

9. **Planform Area**  
   Wing surface area (top-down projection)

---

## Implementation Phases

### Phase 1: Core Framework (4 Weeks)
- [ ] Project wizard GUI (Qt)
- [ ] Basic 3D viewer (OpenGL)
- [ ] OBJ file importer
- [ ] Camera controls

### Phase 2: Physics Foundation (6 Weeks)
- [ ] Air properties system
- [ ] Basic force calculator
- [ ] Panel method implementation
- [ ] Pressure mapping

### Phase 3: Visualization (4 Weeks)
- [ ] Pressure color mapping
- [ ] Streamline generator
- [ ] HUD overlay (IMGUI)

### Phase 4: Advanced Features (6 Weeks)
- [ ] Vortex lattice method
- [ ] Noise simulation model
- [ ] Formula documentation tab
- [ ] Batch simulation mode

### Phase 5: Optimization (2 Weeks)
- [ ] GPU acceleration
- [ ] Multi-threading
- [ ] Memory management

---

## UI Layout Specification
```plaintext
+-----------------------------------+-----------------+
|                                   | Mode Selector   |
|                                   | (Radio Buttons) |
|        3D Viewport                +-----------------+
|                                   | Numerical Data  |
|                                   | (Lift/Drag/etc) |
+-----------------------------------+-----------------+