from zoneinfo import ZoneInfo


def as_tz(date_obj, tz, format="%b %d, %I:%M %p"):
    return date_obj.astimezone(ZoneInfo(tz)).strftime(format)
