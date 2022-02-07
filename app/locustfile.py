import time
from locust import HttpUser, task, between

class QuickstartUser(HttpUser):
    # wait_time = between(0.5, 1)

    @task
    def store_items(self):
        for item_id in range(1000):
            self.client.get(f"/store/{item_id}/{item_id}", name="/storeitem")
            time.sleep(1)

    # def on_start(self):
    #     self.client.get("/store/initialize")