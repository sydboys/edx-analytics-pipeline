"""Service for connecting acceptance tests to Vertica."""
import json

from contextlib import closing
from contextlib import contextmanager

import vertica_python

from edx.analytics.tasks.url import get_target_from_url


class VerticaService(object):
    """Service object to be used as a member of a class to enable that class to write to and read from Vertica."""

    def __init__(self, config, schema_name):
        self.vertica_creds_url = config['vertica_creds_url']
        self.schema_name = schema_name

    @property
    def credentials(self):
        """The credentials for connecting to the database, read from a URL."""
        if not hasattr(self, '_credentials'):
            target = get_target_from_url(self.vertica_creds_url)
            print "TARGET BUILT: ", target
            with get_target_from_url(self.vertica_creds_url).open('r') as credentials_file:
                self._credentials = json.load(credentials_file)

        return self._credentials

    @contextmanager
    def cursor(self):
        """A cursor for the database connection, as a context manager that can be opened and closed."""
        with self.connect() as conn:
            with closing(conn.cursor()) as cur:
                try:
                    yield cur
                except:
                    conn.rollback()
                    raise
                else:
                    conn.commit()

    def execute_sql_file(self, file_path):
        """
        Execute a file containing SQL statements.

        Note that this *does not* use Vertica native mechanisms for parsing *.sql files. Instead it very naively parses
        the statements out of the file itself.

        """
        with self.cursor() as cur:
            with open(file_path, 'r') as sql_file:
                for line in sql_file:
                    if line.startswith('--') or len(line.strip()) == 0:
                        continue

                    cur.execute(line)

    def connect(self):
        """
        Connect to the Vertica server.
        """
        return vertica_python.connect(self.credentials)

    def reset(self):
        """Create a testing schema on the Vertica replacing any existing content with an empty database."""
        # The testing Vertica user doesn't have create/delete schema privileges, so we pass here.
        with self.cursor() as cur:
            cur.execute('DROP SCHEMA IF EXISTS {0} CASCADE;'.format(self.schema_name))
            cur.execute('CREATE SCHEMA {0};'.format(self.schema_name))
