import json
import logging


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'severity': record.levelname,
            'message': super().format(record),
        })
