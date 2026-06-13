class Report:
    def __init__(self, data):
        self.data = data
    def total(self):
        return sum(self.data)
    def save(self):
        open('r.txt','w').write(str(self.total()))
    def show(self):
        print(self.total())