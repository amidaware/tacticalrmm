"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.core.management.base import BaseCommand
from django.conf import settings as djangosettings
from psycopg2 import connect, extensions, sql
from reporting.settings import settings as reportingsettings
from reporting.constants import REPORTING_MODELS


class Command(BaseCommand):
    help = "Setup reporting databases and users"

    def handle(self, *args, **kwargs) -> None:
        try:
            self.trmm_db_conn = djangosettings.DATABASES["default"]
            self.conn = connect(
                dbname=self.trmm_db_conn["NAME"],
                user=self.trmm_db_conn["USER"],
                host=self.trmm_db_conn["HOST"],
                password=self.trmm_db_conn["PASSWORD"],
                port=self.trmm_db_conn["PORT"],
            )
            self.cursor = self.conn.cursor()
            self.create_reporting_db_user()

            self.cursor.close()
            self.conn.close()
        except Exception as error:
            self.stderr.write(str(error))

    def create_reporting_db_user(self) -> None:
        role_name = "role_reporting"
        trmm_database_name = self.trmm_db_conn["NAME"]
        reporting_user = reportingsettings.REPORTING_DB_USER
        reporting_password = reportingsettings.REPORTING_DB_PASSWORD

        sql_commands = f"""CREATE ROLE {role_name};\n"""
        sql_commands += (
            f"""GRANT CONNECT ON DATABASE {trmm_database_name} TO {role_name};\n"""
        )
        sql_commands += f"""GRANT USAGE ON SCHEMA public TO {role_name};\n"""

        for model, app in REPORTING_MODELS:
            sql_commands += (
                f"""GRANT SELECT ON {app}_{model.lower()} TO {role_name};\n"""
            )

        sql_commands += (
            f"""CREATE USER {reporting_user} WITH PASSWORD {reporting_password};\n"""
        )

        self.cursor.execute(sql_commands)
