import sys
from .mercado_play_addon import MercadoPlayAddon

if __name__ == '__main__':
    addon_handle = int(sys.argv[1])
    addon = MercadoPlayAddon(addon_handle)
    addon.run(sys.argv)