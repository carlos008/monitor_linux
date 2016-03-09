import gevent
from gevent.monkey import patch_all
patch_all()

from gevent.pywsgi import WSGIServer
import locale
import argparse
import logging
import socket
import urllib
import urllib2
from logging import getLogger
from flask import Flask
import zerorpc
from psdash import __version__
from psdash.node import LocalNode, RemoteNode
from psdash.web import fromtimestamp


logger = getLogger('monitorps.correr')


class monitorLinux(object):
    DEFAULT_INTERVALO_USUARIO = 60
    DEFAULT_INTERVALO_CONTORNO_RED_IO = 3
    DEFAULT_INTERVALO_REGISTRO = 60
    DEFAULT_ENLAZAR_HOST = '0.0.0.0'
    DEFAULT_PUERTO = 5000
    LOCAL_NODE = 'localhost'

    @classmethod
    def crear_args_de_cli(cls):
        return cls(args=None)

    def __init__(self, anualizaciones_config=None, args=tuple()):
        self._nodes = {}
        config = self._carga_config_args(args)
        if anualizaciones_config:
            config.update(anualizaciones_config)
        self.app = self._crea_app(config)

        self._config_nodos()
        self._config_usuarios()
        self._config_contexto()

    def _get_args(cls, args):
        parser = argparse.ArgumentParser(
            description='psdash %s - system information web dashboard' % __version__
        )
        parser.add_argument(
            '-l', '--log',
            action='append',
            dest='logs',
            default=None,
            metavar='path',
            help='log files to make available for psdash. Patterns (e.g. /var/log/**/*.log) are supported. '
                 'This option can be used multiple times.'
        )
        parser.add_argument(
            '-b', '--bind',
            action='store',
            dest='bind_host',
            default=None,
            metavar='host',
            help='host to bind to. Defaults to 0.0.0.0 (all interfaces).'
        )
        parser.add_argument(
            '-p', '--port',
            action='store',
            type=int,
            dest='port',
            default=None,
            metavar='port',
            help='port to listen on. Defaults to 5000.'
        )
        parser.add_argument(
            '-d', '--debug',
            action='store_true',
            dest='debug',
            help='enables debug mode.'
        )
        parser.add_argument(
            '-a', '--agent',
            action='store_true',
            dest='agent',
            help='Enables agent mode. This launches a RPC server, using zerorpc, on given bind host and port.'
        )
        parser.add_argument(
            '--register-to',
            action='store',
            dest='register_to',
            default=None,
            metavar='host:port',
            help='The psdash node running in web mode to register this agent to on start up. e.g 10.0.1.22:5000'
        )
        parser.add_argument(
            '--register-as',
            action='store',
            dest='register_as',
            default=None,
            metavar='name',
            help='The name to register as. (This will default to the node\'s hostname)'
        )

        return parser.parse_args(args)

    def _carga_config_args(self, args):
        config = {}
        for k, v in vars(self._get_args(args)).iteritems():
            if v:
                tecla = 'PSDASH_%s' % k.upper() if k != 'debug' else 'DEBUG'
                config[key] = v
        return config

    def _config_nodos(self):
        self.add_nodo(LocalNode())

        nodos = self.app.config.get('PSDASH_NODES', [])
        logger.info("Registering %d _nodes", len(nodos))
        for n in nodos:
            self.registrar_nodo(n['nombre'], n['host'], int(n['puerto']))

    def add_nodo(self, node):
        self._nodes[node.get_id()] = node

    def get_nodo_local(self):
        return self._nodes.get(self.LOCAL_NODE)

    def get_node(self, nombre):
        return self._nodes.get(nombre)

    def get_nodes(self):
        return self._nodes

    def registrar_nodo(self, nombre, host, puerto):
        n = NodoRemoto(nombre, host, puerto)
        nodo = self.get_node(n.get_id())
        if nodo:
            n = nodo
            logger.debug("Actualizando nodo registrado %s", n.get_id())
        else:
            logger.info("Registrando %s", n.get_id())
        n.actualizar_ultimo_registrado()
        self.add_nodo(n)
        return n

    def _crea_app(self, config=None):
        app = Flask(__name__)
        app.psdash = self
        app.config.from_envvar('PSDASH_CONFIG', silent=True)

        if config and isinstance(config, dict):
            app.config.update(config)

        self._cargar_direccciones_remotas_permitidas(app)

        # If the secret key is not read from the config just set it to something.
        if not app.secret_key:
            app.secret_key = 'whatisthissourcery'
        app.add_template_filter(fromtimestamp)

        from psdash.web import webapp
        prefix = app.config.get('PSDASH_URL_PREFIX')
        if prefix:
            prefix = '/' + prefix.strip('/')
        webapp.url_prefix = prefix
        app.register_blueprint(webapp)

        return app

    def _cargar_direccciones_remotas_permitidas(self, app):
        key = 'PSDASH_LLAMADA_DIRECCION_REMOTA'
        addrs = app.config.get(key)
        if not addrs:
            return

        if isinstance(addrs, (str, unicode)):
            app.config[key] = [a.strip() for a in addrs.split(',')]

    def _config_usuarios(self):
        level = self.app.config.get('PSDASH_NIVEL_USUARIO', logging.INFO) if not self.app.debug else logging.DEBUG
        format = self.app.config.get('PSDASH_FORMATO_USUARIO', '%(levelname)s | %(name)s | %(message)s')

        logging.basicConfig(
            level=level,
            format=format
        )
        logging.getLogger('werkzeug').setLevel(logging.WARNING if not self.app.debug else logging.DEBUG)
        
    def _config_trabajadores(self):
        net_io_interval = self.app.config.get('PSDASH_INTERVALO_CONTORNO_RED_IO', self.DEFAULT_INTERVALO_CONTORNO_RED_IO)
        gevent.spawn_later(net_io_interval, self._contadores_trabajador_red_io, net_io_interval)

        if 'PSDASH_LOGS' in self.app.config:
            logs_interval = self.app.config.get('PSDASH_LOGS_INTERVAL', self.DEFAULT_LOG_INTERVAL)
            gevent.spawn_later(logs_interval, self._logs_worker, logs_interval)

        if self.app.config.get('PSDASH_AGENT'):
            register_interval = self.app.config.get('PSDASH_INTERVALO_REGISTRO', self.DEFAULT_INTERVALO_REGISTRO)
            gevent.spawn_later(register_interval, self._register_agent_worker, register_interval)

    def _config_lugar(self):
        # This set locale to the user default (usually controlled by the LANG env var)
        locale.setlocale(locale.LC_ALL, '')

    def _config_contexto(self):
        self.get_nodo_local().net_io_counters.update()
        if 'PSDASH_LOGS' in self.app.config:
            self.get_nodo_local().logs.add_patterns(self.app.config['PSDASH_LOGS'])

    def _sesion_trabajador(self, sleep_interval):
        while True:
            logger.debug("Recargando usuarios...")
            self.get_nodo_local.logs.add_patterns(self.app.config['PSDASH_LOGS'])
            gevent.sleep(sleep_interval)

    def _registrar_trabajador_agent(self, sleep_interval):
        while True:
            logger.debug("Registrando agent...")
            self._registrar_agent()
            gevent.sleep(sleep_interval)

    def _contadores_trabajador_red_io(self, sleep_interval):
        while True:
            logger.debug("Subiendo red contadores io ...")
            self.get_nodo_local().net_io_counters.update()
            gevent.sleep(sleep_interval)

    def _registrar_agent(self):
        registrar_nombre = self.app.config.get('PSDASH_REGISTRAR_COMO')
        if not registrar_nombre:
            registrar_nombre = socket.gethostname()

        url_args = {
            'nombre': registrar_nombre,
            'puerto': self.app.config.get('PSDASH_PUERTO', self.DEFAULT_PUERTO),
        }
        register_url = '%s/register?%s' % (self.app.config['PSDASH_REGISTER_TO'], urllib.urlencode(url_args))

        if 'PSDASH_AUTH_USERNAME' in self.app.config and 'PSDASH_AUTH_PASSWORD' in self.app.config:
            auth_handler = urllib2.HTTPBasicAuthHandler()
            auth_handler.add_password(
                realm='psDash login required',
                uri=register_url,
                user=self.app.config['PSDASH_AUTH_USERNAME'],
                passwd=self.app.config['PSDASH_AUTH_PASSWORD']
            )
            opener = urllib2.build_opener(auth_handler)
            urllib2.install_opener(opener)

        try:
            urllib2.urlopen(register_url)
        except urllib2.HTTPError as e:
            logger.error('Fallo a registrar agente a "%s": %s', register_url, e)

    def _correr_rpc(self):
        logger.info("iniciando servidor RPC (modo agente)")

        if 'PSDASH_REGISTRAR A' in self.app.config:
            self._registrar_agent()

        service = self.get_nodo_local().get_service()
        self.server = zerorpc.Server(service)
        self.server.bind('tcp://%s:%s' % (self.app.config.get('PSDASH_ENLAZAR_HOST', self.DEFAULT_ENLAZAR_HOST),
                                          self.app.config.get('PSDASH_PUERTO', self.DEFAULT_PUERTO)))
        self.server.run()

    def _run_web(self):
        logger.info("Iniciando servidor web")
        log = 'default' if self.app.debug else None

        ssl_args = {}
        if self.app.config.get('PSDASH_HTTPS_KEYFILE') and self.app.config.get('PSDASH_HTTPS_CERTFILE'):
            ssl_args = {
                'keyfile': self.app.config.get('PSDASH_HTTPS_KEYFILE'),
                'certfile': self.app.config.get('PSDASH_HTTPS_CERTFILE')
            }

        listen_to = (
            self.app.config.get('PSDASH_ENLAZAR_HOST', self.DEFAULT_ENLAZAR_HOST),
            self.app.config.get('PSDASH_PUERTO', self.DEFAULT_PUERTO)
        )
        self.server = WSGIServer(
            listen_to,
            application=self.app,
            log=log,
            **ssl_args
        )
        self.server.serve_forever()

    def correr(self):
        logger.info('iniciando monitorPROCESOS v%s' % __version__)

        self._config_lugar()
        self._config_trabajadores()

        logger.info('Listando en %s:%s',
                    self.app.config.get('PSDASH_ENLAZAR_HOST', self.DEFAULT_ENLAZAR_HOST),
                    self.app.config.get('PSDASH_PUERTO', self.DEFAULT_PUERTO))

        if self.app.config.get('PSDASH_AGENTE'):
            return self._correr_rpc()
        else:
            return self._run_web()


def principal():
    r = monitorLinux.crear_args_de_cli()
    r.correr()
    

if __name__ == '__main__':
    principal()