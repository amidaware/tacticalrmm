"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.core.management.base import BaseCommand
from django.conf import settings as djangosettings
from psycopg2 import connect
from ...constants import REPORTING_MODELS


class Command(BaseCommand):
    help = "Setup reporting databases and users"

    def handle(self, *args, **kwargs) -> None:
        try:
            trmm_db_conn = djangosettings.DATABASES["default"]
            trmm_reporting_conn = djangosettings.DATABASES["reporting"]
            conn = connect(
                dbname=trmm_db_conn["NAME"], # type: ignore
                user=trmm_db_conn["USER"], # type: ignore
                host=trmm_db_conn["HOST"], # type: ignore
                password=trmm_db_conn["PASSWORD"], # type: ignore
                port=trmm_db_conn["PORT"], # type: ignore
            )
            cursor = conn.cursor()
            sql_commands = ("""""")
            for model, app in REPORTING_MODELS:
                sql_commands += (
                    f"""GRANT SELECT ON {app}_{model.lower()} TO {trmm_reporting_conn["USER"]};\n""" # type: ignore
                )

            cursor.execute(sql_commands)
            cursor.execute("COMMIT")
            cursor.close()
            conn.close()
        except Exception as error:
            self.stderr.write(str(error))

