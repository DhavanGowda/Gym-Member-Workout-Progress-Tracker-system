import logging

def setup_logger(file_name,log_file_name):
    # creating a custom logger
    logger = logging.getLogger(file_name)
    # configuring the custom logger
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(log_file_name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
