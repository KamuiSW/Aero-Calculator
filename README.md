# Aero Calculator

A desktop application for aerodynamic analysis of 3D models with real-time visualization and engineering data outputs.

## Prerequisites
- .NET 7.0 SDK or later
- Qt 6.5 or later (for GUI)
- OpenGL 4.5+ compatible graphics card
- Visual Studio 2022 or later (recommended IDE)

## Project Structure
```
Aero-Calculator/
├── src/
│   ├── AeroCalculator.Core/        # Core business logic
│   ├── AeroCalculator.GUI/         # Qt-based user interface
│   └── AeroCalculator.Rendering/   # OpenGL rendering engine
├── tests/                          # Unit tests
├── docs/                           # Documentation
└── assets/                         # 3D models and resources
```

## Setup Instructions
1. Install the .NET 7.0 SDK
2. Install Qt 6.5 or later
3. Clone this repository
4. Open the solution in Visual Studio
5. Restore NuGet packages
6. Build and run the project

## Development
This project follows the roadmap outlined in `roadmap.md`. Current phase: Phase 1 - Core Framework

## Dependencies
- QtCore (6.5+)
- OpenTK (OpenGL wrapper for .NET)
- Assimp.Net (3D model importing)
- ImGui.NET (GUI overlays)

## License
MIT License - See LICENSE file for details

## Features

- Project Wizard for new project creation
- Support for OBJ/FBX 3D model formats
- Real-time aerodynamic analysis
- Visualization of pressure distribution and streamlines

## Development Status

Currently in Phase 1: Core Framework implementation. See roadmap.md for detailed development plans.

## Features (Phase 1)
- Project creation wizard
- Support for OBJ and FBX 3D model formats
- Basic project management

## Project Structure
- `main.py` - Main application entry point
- `requirements.txt` - Python dependencies

## Development Status
Currently implementing Phase 1: Core Framework
- [x] Basic project structure
- [x] Project wizard GUI
- [ ] 3D viewer implementation
- [ ] Camera controls
- [ ] OBJ file importer

