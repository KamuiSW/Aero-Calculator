def cleanup(self):
    try:
        # Convert buffer IDs to integers if needed
        if hasattr(self, 'vbo'):
            vbo_id = int(self.vbo) if self.vbo is not None else 0
            glDeleteBuffers(1, [vbo_id])
            
        if hasattr(self, 'texture'):
            tex_id = int(self.texture) if self.texture is not None else 0
            glDeleteTextures(1, [tex_id])
            
    except Exception as e:
        print(f"Warning: Cleanup error - {str(e)}")
        # Continue cleanup even if there's an error 

def init_buffers(self):
    # Initialize as numpy arrays
    self.vertex_buffer = np.array(self.vertices, dtype=np.float32)
    
    # Generate and bind buffers
    self.vbo = GLuint(0)  # Explicitly create as GLuint
    glGenBuffers(1, self.vbo)
    glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
    glBufferData(GL_ARRAY_BUFFER, self.vertex_buffer.nbytes, 
                 self.vertex_buffer, GL_STATIC_DRAW) 