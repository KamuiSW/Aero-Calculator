def load_model(self, filepath):
    try:
        # Check if OpenGL is initialized
        if not self.is_gl_initialized():
            print("Error: Attempting to load model before OpenGL initialization")
            return False
            
        # Cleanup any existing buffers first
        self.cleanup_existing_buffers()
        
        # Load and process the model
        vertices, normals, texcoords = self.process_obj_file(filepath)
        
        # Initialize new buffers
        self.init_buffers(vertices, normals, texcoords)
        
        return True
        
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        # Ensure cleanup happens even on error
        self.cleanup_existing_buffers()
        return False

def is_gl_initialized(self):
    try:
        # Try to get OpenGL version - this will fail if GL isn't initialized
        version = glGetString(GL_VERSION)
        return version is not None
    except:
        return False 

def cleanup_existing_buffers(self):
    try:
        if hasattr(self, 'vbo') and self.vbo is not None:
            # Convert buffer ID to proper type
            buffer_id = GLuint(self.vbo)
            glDeleteBuffers(1, [buffer_id])
            self.vbo = None
            
        if hasattr(self, 'vao') and self.vao is not None:
            vao_id = GLuint(self.vao)
            glDeleteVertexArrays(1, [vao_id])
            self.vao = None
            
        if hasattr(self, 'texture') and self.texture is not None:
            tex_id = GLuint(self.texture)
            glDeleteTextures(1, [tex_id])
            self.texture = None
            
    except Exception as e:
        print(f"Warning: Buffer cleanup error - {str(e)}") 