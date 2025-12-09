class IDataInterface:
    def save_data(self): pass
    def load_data(self): pass
    def connect_server(self): pass
    def draw_ui(self): pass
    def log_event(self): pass
    def delete_cache(self): pass

class MyClass(IDataInterface):
    def save_data(self): 
        pass
    def load_data(self):
        self.save_data()
