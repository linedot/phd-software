import psycopg2
from psycopg2 import sql
import socket
import shutil
import os
from subprocess import Popen, PIPE

class resultdb:
    def __init__(self, basedir, hostname, port, tablename, resetdata):
        self.basedir=basedir
        self.hostname=hostname
        self.port=port
        self.tablename=tablename
        self.resetdata=resetdata

    def stoppg(self):
        dbdir = os.path.join(self.basedir,"db")
        logdir = os.path.join(self.basedir,"log")
        pg_ctl_exe = shutil.which("pg_ctl")
        if not None == pg_ctl_exe:
            cmd = f"{pg_ctl_exe}"
            p = Popen([cmd,
                       "-D",dbdir,
                       "-o",f"-p {self.port} -k {self.basedir}",
                       "-l",logdir,
                       "stop"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            communication = p.communicate()
            output = communication[0].decode()
            outerr = communication[1].decode()
            if 0 == p.returncode:
                print(f"Stopped PostgreSQL on port {self.port}")
            else:
                print(f"Error: {outerr}")
                raise RuntimeError("Error stopping PostgreSQL")
        else:
            raise RuntimeError("pg_ctl executable not found")

    def startpg(self):
        dbdir = os.path.join(self.basedir,"db")
        logdir = os.path.join(self.basedir,"log")

        if not os.path.exists(dbdir):
            initdb_exe = shutil.which("initdb")
            if not None == initdb_exe:
                cmd = f"{initdb_exe}"
                p = Popen([cmd,
                           "-D",dbdir], stdin=PIPE, stdout=PIPE, stderr=PIPE)
                communication = p.communicate()
                output = communication[0].decode()
                outerr = communication[1].decode()
                if 0 == p.returncode:
                    print(f"Created DB in {dbdir}")
                else:
                    print(f"Error: {outerr}")
                    raise RuntimeError("Error creating DB")
            else:
                raise RuntimeError("initdb executable not found")

        # Allow connections
        with open(os.path.join(self.basedir,"db","pg_hba.conf"), "w") as f:
            f.write("host    all             all             0.0.0.0/0            trust\n")
            f.write("host    all             all             ::0/0                trust\n")

        pg_ctl_exe = shutil.which("pg_ctl")
        if not None == pg_ctl_exe:
            cmd = f"{pg_ctl_exe}"
            p = Popen([cmd,
                       "-D",dbdir,
                       "-o",f"-p {self.port} -k {self.basedir} -h {self.hostname}",
                       "-l",logdir,
                       "start"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            communication = p.communicate()
            output = communication[0].decode()
            outerr = communication[1].decode()
            if 0 == p.returncode:
                print(f"Started PostgreSQL on self.port {self.port}")
            else:
                print(f"Error: {outerr}")
                raise RuntimeError("Error starting PostgreSQL")


        try:
            conn = psycopg2.connect(database="postgres", host=self.hostname, port=self.port)
            conn.set_session(autocommit=True)
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'gem5stats'")
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(sql.SQL("CREATE DATABASE {};").format(
                    sql.Identifier("gem5stats")))

            conn.commit()
            conn.close()

            conn = psycopg2.connect(database="gem5stats", host=self.hostname, port=self.port)
            conn.set_session(autocommit=True)
            cursor = conn.cursor()

            if self.resetdata:
                cursor.execute(sql.SQL(
                    "DROP TABLE IF EXISTS {};"
                    ).format(sql.Identifier(self.tablename)))

            cursor.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} (run int DEFAULT 0);").format(
                sql.Identifier(self.tablename)
                ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(e)
            self.stoppg()
            raise e

    def connect(self):
        conn = psycopg2.connect(database="gem5stats", host=self.hostname, port=self.port)
        conn.set_session(autocommit=True)
        return conn

    def disconnect(self, conn):
        conn.close()

    def get_columns(self, cursor):
        cursor.execute(sql.SQL(
            "SELECT * FROM {} WHERE false;"
            ).format(
                sql.Identifier(self.tablename)
                ))
        return [desc[0] for desc in cursor.description]

    def add_columns(self, cursor, column_names):
        statement = sql.SQL(
            "ALTER TABLE {} {};").format(
                sql.Identifier(self.tablename),
                sql.SQL(", ").join([
                    sql.SQL("ADD COLUMN IF NOT EXISTS {} numeric DEFAULT 0").format(
                        sql.Identifier(cname))
                    for cname in column_names]))

        cursor.execute(statement)

    def add_row(self, cursor, row):

        columns = self.get_columns(cursor)

        missing_columns = [key for key in row.keys() if not key in columns]

        if missing_columns:
            self.add_columns(cursor, missing_columns)

        statement = sql.SQL(
            "INSERT INTO {} ({}) VALUES ({});").format(
                sql.Identifier(self.tablename),
                sql.SQL(", ").join(
                    [sql.Identifier(key) for key in row.keys()]),
                sql.SQL(", ").join(
                    [sql.Literal(row[key]) for key in row]
                    )
                )
        cursor.execute(statement)

    def add_rows(self, cursor, rows):
        from psycopg2.extras import execute_values

        columns = self.get_columns(cursor)

        missing_columns = [key for key in rows.keys() if not key in columns]

        if missing_columns:
            self.add_columns(cursor, missing_columns)

        statement = sql.SQL(
            "INSERT INTO {} ({}) VALUES %s;").format(
                sql.Identifier(self.tablename),
                sql.SQL(", ").join(
                    [sql.Identifier(key) for key in rows.keys()])
            )

        firstkey = list(rows.keys())[0]
        num_vals = len(rows[firstkey])

        values = [[rows[key][i] for key in rows.keys()] for i in range(num_vals)]

        execute_values(cursor, statement, values)
                
        #cursor.execute(statement)


    def get_row_count(self, cursor):

        statement = sql.SQL("SELECT count(*) FROM {};").format(
                sql.Identifier(self.tablename)
                )

        cursor.execute(statement)
        result = cursor.fetchone()

        return result[0]

