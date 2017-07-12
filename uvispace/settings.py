import logging.config
import os
import time


# Logging configuration
parent_path = os.path.dirname(__file__)
log_path = ("{}/log".format(parent_path))

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)8s %(name)s '
                      '%(module)s:%(lineno)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)8s %(module)s:%(lineno)d %(message)s'
        },
        'thread_verbose': {
            'format': '%(asctime)s %(levelname)8s %(name)s '
                      '(%(threadName)-9s) %(module)s:%(lineno)d %(message)s'
        },
        'thread_simple': {
            'format': '%(levelname)8s (%(threadName)-9s) %(module)s:%(lineno)d '
                      '%(message)s'
        }
    },
    'handlers': {
        'file_controller': {
            'level': 'DEBUG',
            'formatter': 'verbose',
            'class': 'logging.FileHandler',
            'filename': '/'.join([log_path, 'controller_{}.log'.format(
                    time.strftime("%Y%m%d_%H%M%S"))]),
            'delay': True
        },
        'file_messenger': {
            'level': 'DEBUG',
            'formatter': 'verbose',
            'class': 'logging.FileHandler',
            'filename': '/'.join([log_path, 'messenger_{}.log'.format(
                    time.strftime("%Y%m%d_%H%M%S"))]),
            'delay': True
        },
        'file_sensor': {
            'level': 'DEBUG',
            'formatter': 'thread_verbose',
            'class': 'logging.FileHandler',
            'filename': os.path.join(log_path, 'sensor_{}.log'.format(
                    time.strftime("%Y%m%d_%H%M%S"))),
            'delay': True
        },
        'console': {
            'level': 'INFO',
            'formatter': 'simple',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'controller': {
            'handlers': ['file_controller', 'console'],
            'level': 'DEBUG'
        },
        'messenger': {
            'handlers': ['file_messenger', 'console'],
            'level': 'DEBUG'
        },
        'sensor': {
            'handlers': ['file_sensor', 'console'],
            'level': 'DEBUG'
        }
    }
}

logging.config.dictConfig(LOGGING)
