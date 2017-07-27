#!/usr/bin/env python
import os
import sys

import arrow
import whoosh
import whoosh.index
import whoosh.qparser

from IPython import embed

from .config import Configuration
from . import index
from . import utils
from .email_schema import email_schema


embed()
