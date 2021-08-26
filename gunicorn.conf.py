import multiprocessing

bind = '192.168.0.17:8000'
workers = multiprocessing.cpu_count() * 2 + 1

wsgi_app = 'slobsterble.wsgi:app'
