import re
import sqlite3
import os
import abc


class DatabaseManager(object):
    location = None
    conn = None

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        pass

    def connect(self):
        self.conn = sqlite3.connect(self.location)

    def disconnect(self):
        self.conn.close()

    def execute(self, cmd):
        return self.conn.execute(cmd)

    def commit(self):
        self.conn.commit()

    def check_for_db(self):
        if not os.path.exists(self.location):
            with open(self.location, 'wb'):
                pass
            self.create_db()

    @abc.abstractmethod
    def create_db(self):
        pass


class ProxyDB(DatabaseManager):
    location = "badproxies.sqlite"
    conn = None

    def __init__(self):
        DatabaseManager.__init__(self)
        self.check_for_db()

    def create_db(self):
        self.connect()
        self.execute('CREATE TABLE HTTPS (SOCKET TEXT PRIMARY KEY NOT NULL);')
        self.execute('CREATE TABLE HTTP (SOCKET TEXT PRIMARY KEY NOT NULL);')
        self.disconnect()

    def prune_bad_proxies(self, socket_dict):
        self.connect()
        http_copied_list = list(socket_dict['http'])
        https_copied_list = list(socket_dict['https'])
        for protocol, proxies in socket_dict.iteritems():
            for proxy in proxies:
                cursor = self.execute('select socket from %s  where socket is "%s"' % (protocol.upper(), proxy))
                for row in cursor:
                    if protocol == 'http':
                        http_copied_list.remove(row[0])
                    else:
                        https_copied_list.remove(row[0])
        self.disconnect()
        return dict(http=http_copied_list, https=https_copied_list)

    def blacklist_socket(self, protocol, socket):
        if protocol and socket:
            self.connect()
            try:
                self.execute("INSERT into %s (socket) VALUES (\"%s\")" % (protocol.upper(), socket))
                self.commit()
            except sqlite3.IntegrityError:
                pass
            self.disconnect()
