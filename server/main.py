# -*- coding: UTF-8 -*-
import tornado.web
import tornado.ioloop
import tornado.httpserver
import tornado.options
import os
import random
import datetime
import json
from tornado.web import RequestHandler
from tornado.options import define, options
from tornado.websocket import WebSocketHandler

define("port", default=443, type=int)

class connectHandler(WebSocketHandler):

    all_clients = set()
    rooms = {}
    def open(self):
        self.all_clients.add(self)
        print(self.request.remote_ip+' connected')

    def on_message(self,message):
        content = json.loads(message)
        if content['type']=='danmu':
            room = content['room']
            for client in self.rooms[room]:
                client.write_message(message)
        elif content['type']=='createroom':
            while True:
                n = str(random.randint(1,99999))
                if n in self.rooms:
                    continue
                else:
                    break
            message = {
                'type': 'room',
                'n': n,
            }
            message = json.dumps(message)
            self.write_message(message)
            self.rooms[n] = [self]
            self.write_message(message)
            message = {
                'type': 'informn',
                'n': str(len(self.rooms[n])),
                }
            message = json.dumps(message)
            for client in self.rooms[n]:
                client.write_message(message)
        elif content['type']=='joinroom':
            room = content['n']
            if room not in self.rooms:
                message = {
                'type': 'room',
                'n': 'err',
                }
                message = json.dumps(message)
                self.write_message(message)
            else:
                self.rooms[room].append(self)
                message = {
                'type': 'room',
                'n': room,
                }
                message = json.dumps(message)
                self.write_message(message)
                message = {
                    'type': 'informn',
                    'n': str(len(self.rooms[room])),
                    }
                message = json.dumps(message)
                for client in self.rooms[room]:
                    client.write_message(message)
        elif content['type']=='heartbeat':
            message = {
                'type': 'heartbeat',
                }
            message = json.dumps(message)
            self.write_message(message)

    def on_close(self):
        self.all_clients.remove(self)
        
        delete_room = False
        for room in self.rooms:
            for client in self.rooms[room]:
                if client==self:
                    self.rooms[room].remove(client)
                    if self.rooms[room] == []:
                        delete_room = True
                    break
        if delete_room:
            self.rooms.pop(room)
        else:
            message = {
            'type': 'informn',
            'n': str(len(self.rooms[room])),
            }
            message = json.dumps(message)
            for client in self.rooms[room]:
                client.write_message(message)


        print(self.request.remote_ip+' disconnected')

    def check_origin(self, origin):
        return True  # 允许WebSocket的跨域请求

class sendHandler(RequestHandler):
    def get(self):
        self.write('ok')
    def post(self):
        try:
            info = self.request.body
            message = info.decode('utf8')
            print(message)
            connectHandler.on_message(connectHandler,message)
            self.write("ok")
        except:
            self.write("err")

if __name__ == '__main__':
    print('Start service')
    tornado.options.parse_command_line()
    app = tornado.web.Application([
            (r"/connect", connectHandler),
            (r"/send", sendHandler),
        ],
        static_path = os.path.join(os.path.dirname(__file__), "static"),
        template_path = os.path.join(os.path.dirname(__file__), "template"),
        debug = True
        )
    ssl_options = {
            "certfile": os.path.join(os.path.abspath("."), "server.crt"),
            "keyfile": os.path.join(os.path.abspath("."), "server.key"),
        }
    http_server = tornado.httpserver.HTTPServer(app,ssl_options=ssl_options)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
