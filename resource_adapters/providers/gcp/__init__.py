# import os
# from .container import Container
#
#
#
#
# cont = Container()
# cont.config.from_yaml(os.path.join(os.environ['BASEDIR'], 'configurations', f'terrastate_{os.environ["EXECFILE"]}.yml'))
#
#
# # PROXY OVERRIDING
# def __getattr__(name):
#     return getattr(cont, name)