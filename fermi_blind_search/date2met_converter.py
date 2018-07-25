#!/usr/bin/env python

import dateutil
from fermi_blind_search.ltfException import ltfException


def convert_date(date):

    from GtBurst.dataHandling import date2met

    # Check that the date is a valid date
    try:
        validated = dateutil.parser.parse(date).isoformat().replace("T", " ")
    except:
        raise ltfException("The provided date is not a valid ISO date")
    pass

    met_start = date2met(validated)

    return met_start
