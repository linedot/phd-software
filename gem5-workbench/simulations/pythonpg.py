import psycopg2
from psycopg2 import sql
import socket
import shutil
import os
from subprocess import Popen, PIPE
from mpi4py import MPI

class resultdb:
    def __init__(self, basedir, hostname, port, tablename, resetdata):
        self.basedir=basedir
        self.hostname=hostname
        self.port=port
        self.tablename=tablename
        self.resetdata=resetdata

    def stoppg():
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

    def startpg():
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
            stoppg()
            raise e

    def connect():
        conn = psycopg2.connect(database="gem5stats", host=self.hostname, port=self.port)
        conn.set_session(autocommit=True)
        return conn

    def disconnect(conn):
        conn.close()

    def get_columns(cursor):
        cursor.execute(sql.SQL(
            "SELECT * FROM {} WHERE false;"
            ).format(
                sql.Identifier(tablename)
                ))
        return [desc[0] for desc in cursor.description]

    def add_columns(cursor, column_names):
        statement = sql.SQL(
            "ALTER TABLE {} {};").format(
                sql.Identifier(tablename),
                sql.SQL(", ").join([
                    sql.SQL("ADD COLUMN IF NOT EXISTS {} numeric DEFAULT 0").format(
                        sql.Identifier(cname))
                    for cname in column_names]))

        cursor.execute(statement)

    def add_row(cursor, row):

        columns = get_columns(cursor, tablename)

        missing_columns = [key for key in row.keys() if not key in columns]

        if missing_columns:
            add_columns(cursor, tablename, missing_columns)

        statement = sql.SQL(
            "INSERT INTO {} ({}) VALUES ({});").format(
                sql.Identifier(tablename),
                sql.SQL(", ").join(
                    [sql.Identifier(key) for key in row.keys()]),
                sql.SQL(", ").join(
                    [sql.Literal(row[key]) for key in row]
                    )
                )
        cursor.execute(statement)


    def get_row_count(cursor):

        statement = sql.SQL("SELECT count(*) FROM {};").format(
                sql.Identifier(tablename)
                )

        cursor.execute(statement)
        result = cursor.fetchone()

        return result[0]



def main():
    import argparse

    parser = argparse.ArgumentParser(prog="pythonpg",
                                     description="Python PostgreSQL test")

    parser.add_argument("--basedir", type=str, 
                        required=True,
                        help="Base directory of the PostgreSQL DB")
    parser.add_argument("--tablename", type=str, 
                        required=True,
                        help="Name of the table to write data to")
    parser.add_argument("--resetdata", action='store_true',
                        help="Reset already existing data in the DB")
    parser.add_argument("--jsc", action='store_true',
                        help="Running on JSC machines (add 'i' to hostname)")
    args = parser.parse_args()

    comm = MPI.COMM_WORLD
    size = comm.Get_size()
    rank = comm.Get_rank()

    if 0 == rank:
        s=socket.socket()
        s.bind(("",0))
        port = s.getsockname()[1]
        s.close()
        hostname = socket.gethostname()
        if args.jsc:
            hostname += 'i'
    else:
        hostname = None 
        port = None

    hostname = comm.bcast(hostname, root=0)
    port = comm.bcast(port, root=0)

    basedir = args.basedir

    if 0 == rank:
        try:
            startpg(basedir, hostname, port,
                    tablename=args.tablename, resetdata=args.resetdata)
        except:
            comm.Abort()

    comm.barrier()

    workererror=False
    if 0 != rank:
        try:
            conn = psycopg2.connect(database="gem5stats", host=hostname, port=port)
            conn.set_session(autocommit=True)
            cursor = conn.cursor()

            add_row(cursor, tablename=args.tablename)

            columns = get_columns(cursor, tablename=args.tablename)

            cstr = ",".join(columns)

            conn.commit()
            conn.close()
        except Exception as e:
            print(e)
            workererror=True

    comm.barrier()

    if 0 == rank:
        try:
            conn = psycopg2.connect(database="gem5stats", host=hostname, port=port)
            conn.set_session(autocommit=True)
            cursor = conn.cursor()

            count = get_row_count(cursor, tablename=args.tablename)
            print(f"Rows in table: {count}")

            conn.close()

        except Exception as e:
            print(e)
        stoppg(basedir, hostname, port)

    if workererror:
        print("Worker errors occured")
        exit(-1)

if __name__ == "__main__":
    main()
if __name__ == "__m5_main__":
    main()
