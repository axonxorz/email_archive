#!/usr/bin/env python
import os
import sys

import arrow
import whoosh
import whoosh.index
import whoosh.qparser

from IPython import embed

import config
import index
import utils
from email_schema import email_schema


embed()
