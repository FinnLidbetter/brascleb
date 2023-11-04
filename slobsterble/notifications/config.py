from flask import current_app


class _Config:
    @property
    def cert_file_path(self):
        return current_app.config["APNS_CERT_FILE_PATH"]

    @property
    def key_path(self):
        return current_app.config["APNS_KEY_PATH"]

    @property
    def key_id(self):
        return current_app.config["APNS_KEY_ID"]

    @property
    def team_id(self):
        return current_app.config["APNS_TEAM_ID"]

    @property
    def topic(self):
        return current_app.config["APNS_TOPIC"]

    @property
    def heartbeat_seconds(self):
        return current_app.config["APNS_HEARTBEAT_SECONDS"]

    @property
    def notification_retries_max(self):
        return current_app.config["APNS_NOTIFICATION_RETRIES_MAX"]

    @property
    def use_sandbox(self):
        return current_app.config["APNS_USE_SANDBOX"]


config = _Config()
