"""Simple config wrapper for loading `config.ini`.

The global `config` object behaves like a mapping and is used by other
modules to read settings (kafka, cache, dns sections).
"""

import configparser

config = configparser.ConfigParser()
