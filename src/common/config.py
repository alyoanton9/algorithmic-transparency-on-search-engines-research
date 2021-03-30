import os

from common.util import separator


logs_dir = 'logs'

# logs
scrapping_log = logs_dir + separator + 'scrapping.json'
updating_log = logs_dir + separator + 'updating.json'
access_dir = logs_dir + separator + 'access'
fusion_dir = logs_dir + separator + 'fusion'

# gecko webdriver
gecko_path = 'gecko' + separator + 'geckodriver'
