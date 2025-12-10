class OrderManager:
    def createAndSendOrder(self, order, email_service):
        self.last_order = order
        order.save()
        email_service.send_email(order)

class UserManager:
    def create_user(self, name):
        self.user_name = name
        print(f"User {name} created")
